"""Who a rate-limit budget belongs to.

Spec: docs/specs/trusted-proxy-client-identity.md (GH #16)

`get_remote_address` reads the connecting address, so behind a reverse proxy every user shares one
bucket and the second user gets a 429. The fix GH #16 asks for -- prefer `X-Forwarded-For` -- would
be worse than the bug: that header is set by the client, so trusting it lets anyone send a random
address per request and never be limited at all.
"""
import itertools
import sys

import httpx
import pytest

# tests/test_backend/test_backtest.py installs a fake `core.data` into sys.modules at import and
# never removes it. Importing backend.main below pulls in the real one, so without this guard the
# file passes only because its name sorts after test_backtest.py -- an order dependence that
# reports a pass depending on what else ran. Same guard as test_transparency.py.
sys.modules.pop("core.data", None)
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.limiter import client_identity, limiter
from core import config


@pytest.fixture(autouse=True)
def clean_limiter():
    """slowapi keeps its counters in process memory; leaking them across tests is order-dependence."""
    limiter.reset()
    yield
    limiter.reset()



def _request_with(xff_lines, peer="10.0.0.1"):
    """A minimal Starlette request carrying repeated X-Forwarded-For lines."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/probe",
        "headers": [(b"x-forwarded-for", v.encode()) for v in xff_lines],
        "client": (peer, 12345),
        "query_string": b"",
    }
    return Request(scope)


_probe_seq = itertools.count()


@pytest.fixture
def limited_app():
    """A route carrying the PRODUCTION limiter instance and its real key_func.

    Not a reimplementation: `limiter` is the object `backend/main.py` installs. The route exists
    only so a budget can be exhausted in two requests instead of thirty.

    The endpoint gets a unique name per test. slowapi keys `_route_limits` on the function's
    qualified name, so re-registering one name would STACK a fresh "1/minute" limit on every test
    and a single request would then count against all of them at once -- passing alone and failing
    in a full run. That is worse than a failing test: it reports a pass that depends on what else
    ran.
    """
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    async def probe(request: Request):
        return {"seen": client_identity(request)}

    unique = f"probe_{next(_probe_seq)}"
    probe.__name__ = unique
    probe.__qualname__ = unique
    app.get("/probe")(limiter.limit("1/minute")(probe))

    return TestClient(app)


class TestProductionWiring:
    def test_the_app_limits_on_this_key_func(self):
        """AC6: the identity below is what the real app actually keys on."""
        from backend.main import app

        assert app.state.limiter is limiter
        assert limiter._key_func is client_identity


class TestDirectDeploymentIsUnchanged:
    def test_default_is_zero(self):
        """AC2: doing nothing must not change behaviour, and 0 is the only value trusting nothing."""
        assert config.TRUSTED_PROXY_COUNT == 0

    def test_the_header_is_ignored_at_zero(self, limited_app, monkeypatch):
        """AC2: with no declared proxy, a client cannot buy itself a fresh budget with a header."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)

        first = limited_app.get("/probe", headers={"X-Forwarded-For": "203.0.113.1"})
        second = limited_app.get("/probe", headers={"X-Forwarded-For": "203.0.113.2"})

        assert first.status_code == 200
        assert second.status_code == 429, "a header from the caller bought a second budget"


class TestBehindOneProxy:
    def test_two_clients_get_separate_budgets(self, limited_app, monkeypatch):
        """AC3/AC6: the whole point. Today both of these share one bucket."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)

        alice = limited_app.get("/probe", headers={"X-Forwarded-For": "203.0.113.10"})
        bob = limited_app.get("/probe", headers={"X-Forwarded-For": "203.0.113.11"})

        assert alice.status_code == 200
        assert bob.status_code == 200, "a second user behind the same proxy was rate-limited"
        assert alice.json()["seen"] == "203.0.113.10"

        again = limited_app.get("/probe", headers={"X-Forwarded-For": "203.0.113.10"})
        assert again.status_code == 429, "the same client was not limited"

    def test_a_client_cannot_prepend_its_way_out(self, limited_app, monkeypatch):
        """AC3: entries left of the boundary are the caller's own words and carry no weight.

        The proxy appends what it saw, so the client's own value is always further left. Reading
        `X-Forwarded-For[0]` -- the value most guides reach for -- would make this pass, i.e. would
        let one caller mint unlimited identities.
        """
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)

        first = limited_app.get("/probe", headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.20"})
        assert first.json()["seen"] == "203.0.113.20"

        second = limited_app.get("/probe", headers={"X-Forwarded-For": "198.51.100.99, 203.0.113.20"})
        assert second.status_code == 429, "a caller changed its identity by editing the left of the chain"


class TestBehindTwoProxies:
    def test_the_boundary_moves_with_the_declared_hop_count(self, limited_app, monkeypatch):
        """AC3: client -> CDN -> nginx -> app leaves the client at index -2."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)

        r = limited_app.get(
            "/probe", headers={"X-Forwarded-For": "203.0.113.30, 198.51.100.7"})
        assert r.json()["seen"] == "203.0.113.30"

    def test_junk_outside_the_boundary_is_ignored_not_a_failure(self, limited_app, monkeypatch):
        """A longer-than-declared chain means the caller prepended something. That is the normal
        case the boundary exists for, not an error: entry -2 is still the client.

        This was first written as a fail-closed case and it failed — correctly. The premise was
        wrong, not the code. Falling back here would punish every client behind a proxy that
        forwards an existing header.
        """
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)

        r = limited_app.get(
            "/probe", headers={"X-Forwarded-For": "whatever-the-caller-wants, 203.0.113.31, 198.51.100.7"})
        assert r.json()["seen"] == "203.0.113.31"


class TestFailsClosed:
    @pytest.mark.parametrize("header", [
        None,                                   # no proxy in the path at all
        "",                                     # present but empty
        "203.0.113.40",                         # one hop declared as two -- a short chain
        "not-an-ip, 198.51.100.7",              # the SELECTED entry is not an address
    ])
    def test_an_unusable_chain_falls_back_to_the_connecting_peer(self, limited_app, monkeypatch, header):
        """AC4: a request that did not arrive through the declared chain does not describe itself.

        A short header is exactly what a spoofing attempt looks like, so the fallback must be the
        connecting address -- degraded to per-proxy limiting, never open.
        """
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)
        headers = {} if header is None else {"X-Forwarded-For": header}

        first = limited_app.get("/probe", headers=headers)
        assert first.status_code == 200
        assert first.json()["seen"] == "testclient", "an unusable chain was trusted anyway"

        second = limited_app.get("/probe", headers=headers)
        assert second.status_code == 429, "the fallback identity was not stable, so nothing is limited"


class TestConfigurationErrorsAreLoud:
    def test_a_negative_hop_count_refuses_to_start(self, monkeypatch):
        """AC5: a limiter that starts with a mis-parsed trust boundary offers protection it lacks."""
        import importlib

        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "-1")
        with pytest.raises(ValueError, match="TRUSTED_PROXY_COUNT"):
            importlib.reload(config)

        monkeypatch.delenv("TRUSTED_PROXY_COUNT")
        importlib.reload(config)  # leave the module as the rest of the suite expects it

    def test_a_non_integer_hop_count_refuses_to_start(self, monkeypatch):
        import importlib

        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "two")
        with pytest.raises(ValueError):
            importlib.reload(config)

        monkeypatch.delenv("TRUSTED_PROXY_COUNT")
        importlib.reload(config)


class TestRepeatedHeaderLines:
    """X-Forwarded-For is list-typed: repeated lines are one comma-joined value in order.

    `request.headers.get` returns only the FIRST line — the one a caller can send ahead of the
    proxy's. Reading it handed the caller an attacker-chosen identity and no limit at all.
    Review found this; four requests against a 1/minute budget all returned 200.

    `headers=` as a dict cannot express repeats, which is why the first round of tests missed it.
    """

    def _get(self, client, lines):
        request = client.build_request(
            "GET", "/probe",
            headers=httpx.Headers([("x-forwarded-for", v) for v in lines]),
        )
        return client.send(request)

    def test_a_caller_cannot_prepend_its_own_header_line(self, limited_app, monkeypatch):
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)

        first = self._get(limited_app, ["198.51.100.0", "203.0.113.77"])
        assert first.status_code == 200
        assert first.json()["seen"] == "203.0.113.77", (
            "the caller's own header line was read instead of the proxy's"
        )

        # A different forged line must not buy a fresh budget.
        second = self._get(limited_app, ["198.51.100.1", "203.0.113.77"])
        assert second.status_code == 429, "a caller minted a new identity by varying its own line"

    def test_repeated_lines_are_joined_in_order(self, limited_app, monkeypatch):
        """Two proxies that each emit their own line must read the same as one joined chain."""
        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)

        split = self._get(limited_app, ["203.0.113.30", "198.51.100.7"])
        assert split.json()["seen"] == "203.0.113.30"


class TestOnTheRealApp:
    """AC6 as written: a real limited endpoint on the real app, not the fixture's probe route.

    The probe route carries the production limiter, but "the same limiter" is an assumption about
    wiring; this exercises a route `backend/main.py` actually serves. `/api/transparency` is the
    tightest read-only limit (10/min), so a budget can be exhausted without side effects.
    """

    ENDPOINT = "/api/transparency"
    LIMIT = 10

    def test_two_clients_behind_one_proxy_do_not_share_a_budget(self, monkeypatch):
        from backend.main import app

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)
        client = TestClient(app)

        def hit(ip):
            return client.get(self.ENDPOINT, headers={"X-Forwarded-For": ip}).status_code

        alice = [hit("203.0.113.60") for _ in range(self.LIMIT + 1)]
        assert alice[-1] == 429, f"alice was never limited: {alice}"

        # Bob arrives after alice exhausted her budget. Before this change he inherited her 429.
        assert hit("203.0.113.61") != 429, "a second user was limited by someone else's traffic"

    def test_one_client_is_still_limited(self, monkeypatch):
        """The separation must not become 'nobody is limited'."""
        from backend.main import app

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)
        client = TestClient(app)

        codes = [client.get(self.ENDPOINT, headers={"X-Forwarded-For": "203.0.113.62"}).status_code
                 for _ in range(self.LIMIT + 1)]
        assert codes[-1] == 429, f"the same client was never limited: {codes}"


class TestTheKeySpaceIsBounded:
    """A forwarded identity is chosen by whoever wrote the header, so the key space is not ours.

    slowapi keeps one in-process counter per identity for the window, and its expiry sweep is
    O(total keys) on a 0.01s timer. Before this bound, a caller able to write the entry we read
    could mint a fresh key per request: the pre-mortem measured 2000 requests -> 2000 keys, all
    200, where the pre-change code produced exactly ONE key behind a proxy. That is a stall the
    old behaviour could not have had.

    The bound does not stop a forged chain -- nothing here can, since the app checks the chain's
    length and never who wrote it. It makes the failure mode the old shared bucket instead.
    """

    def test_a_flood_of_invented_identities_degrades_to_the_peer(self, monkeypatch):
        from backend import limiter as limiter_mod

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)
        monkeypatch.setattr(limiter_mod, "MAX_TRACKED_FORWARDED_CLIENTS", 8)
        monkeypatch.setattr(limiter_mod, "_seen", limiter_mod.OrderedDict())

        request = _request_with(["203.0.113.%d" % i for i in range(1)])
        admitted = []
        for i in range(40):
            req = _request_with(["198.51.100.%d" % i])
            admitted.append(limiter_mod.client_identity(req))

        distinct = set(admitted)
        assert len(distinct) <= 8 + 1, f"key space unbounded: {len(distinct)} distinct keys"
        assert admitted[-1] == "10.0.0.1", "past the cap, new identities must fall back to the peer"
        assert request is not None

    def test_a_known_client_keeps_its_own_budget_under_the_flood(self, monkeypatch):
        """The bound must not punish the clients already being tracked."""
        from backend import limiter as limiter_mod

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)
        monkeypatch.setattr(limiter_mod, "MAX_TRACKED_FORWARDED_CLIENTS", 4)
        monkeypatch.setattr(limiter_mod, "_seen", limiter_mod.OrderedDict())

        regular = _request_with(["203.0.113.9"])
        assert limiter_mod.client_identity(regular) == "203.0.113.9"

        for i in range(50):
            limiter_mod.client_identity(_request_with(["198.51.100.%d" % i]))

        assert limiter_mod.client_identity(regular) == "203.0.113.9", (
            "an established client lost its own budget because someone else flooded the table"
        )


class TestProxiesThatAppendAPort:
    """Azure Application Gateway appends `<ip>:<port>`. Failing to parse it is a silent no-op:
    the operator sets the variable, restarts, and nothing changes with nothing logged."""

    @pytest.mark.parametrize("entry,expected", [
        ("203.0.113.9:51234", "203.0.113.9"),
        ("[2001:db8::1]:443", "2001:db8::1"),
        ("[2001:db8::1]", "2001:db8::1"),
        ("203.0.113.9", "203.0.113.9"),
    ])
    def test_the_address_is_recovered(self, monkeypatch, entry, expected):
        from backend import limiter as limiter_mod

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)
        monkeypatch.setattr(limiter_mod, "_seen", limiter_mod.OrderedDict())
        assert limiter_mod.client_identity(_request_with([entry])) == expected


class TestStartupDisclosure:
    """Both error directions are silent, so the effective mode has to be greppable."""

    def test_it_names_the_mode(self, monkeypatch):
        from backend.limiter import describe_configuration

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)
        assert "connecting address" in describe_configuration()

        monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)
        described = describe_configuration()
        assert "X-Forwarded-For" in described and "2" in described
