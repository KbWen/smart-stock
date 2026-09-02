"""Who a rate-limit budget belongs to.

Spec: docs/specs/trusted-proxy-client-identity.md (GH #16)

`get_remote_address` reads the connecting address, so behind a reverse proxy every user shares one
bucket and the second user gets a 429. The fix GH #16 asks for -- prefer `X-Forwarded-For` -- would
be worse than the bug: that header is set by the client, so trusting it lets anyone send a random
address per request and never be limited at all.
"""
import itertools

import pytest
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
