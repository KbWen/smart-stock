"""Shared rate-limiter instance.

Defined here to avoid circular imports between main.py and routes/*.py.
Import this module in routes that need @limiter.limit().
"""
import ipaddress
import logging
import re
import threading
import time
from collections import OrderedDict

from slowapi import Limiter
from slowapi.util import get_remote_address

from core import config

logger = logging.getLogger("sniper.limiter")

XFF_HEADER = "x-forwarded-for"

# A forwarded identity is chosen by whoever wrote the header, so the set of identities is not
# ours to trust. slowapi keeps one in-process counter per identity for the length of the window,
# and its expiry sweep is O(total keys) re-armed on a 0.01s timer -- so an unbounded key space is
# a way to stall the event loop, which the pre-change code could not have had (behind a proxy it
# produced exactly ONE key). Admit a bounded number of distinct forwarded identities per window;
# past that, new ones are limited as their connecting peer instead. Flooding then degrades to the
# old shared-bucket behaviour rather than to a memory and CPU sink.
MAX_TRACKED_FORWARDED_CLIENTS = 4096
FORWARDED_CLIENT_TTL_SECONDS = 120  # comfortably longer than the longest configured window

_seen_lock = threading.Lock()
_seen: "OrderedDict[str, float]" = OrderedDict()

# One warning per condition, not one per request. An operator who mis-declares the hop count gets
# no error from anywhere else: the app cannot verify who wrote the header, only how long it is.
_warned: set = set()

# Azure Application Gateway and some others append `<ip>:<port>` rather than a bare address.
_IPV4_WITH_PORT = re.compile(r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}):\d{1,5}$")
_IPV6_BRACKETED = re.compile(r"^\[(?P<ip>[^\]]+)\](?::\d{1,5})?$")


def _warn_once(key: str, message: str, *args) -> None:
    with _seen_lock:
        if key in _warned:
            return
        _warned.add(key)
    logger.warning(message, *args)


def _parse_address(value: str):
    """An IP address from one X-Forwarded-For entry, or None.

    Accepts the bare forms plus `<ipv4>:<port>` and `[<ipv6>]` / `[<ipv6>]:<port>`, because a
    proxy that appends a port would otherwise fail parsing and silently fall back -- the operator
    sets the variable, restarts, and nothing changes with nothing logged.
    """
    candidate = value
    bracketed = _IPV6_BRACKETED.match(candidate)
    if bracketed:
        candidate = bracketed.group("ip")
    else:
        with_port = _IPV4_WITH_PORT.match(candidate)
        if with_port:
            candidate = with_port.group("ip")
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _admit(identity: str, now: float) -> bool:
    """Whether this forwarded identity may have a counter of its own right now."""
    with _seen_lock:
        cutoff = now - FORWARDED_CLIENT_TTL_SECONDS
        while _seen:
            oldest_key, oldest_seen = next(iter(_seen.items()))
            if oldest_seen >= cutoff:
                break
            _seen.popitem(last=False)

        if identity in _seen:
            _seen[identity] = now
            _seen.move_to_end(identity)
            return True
        if len(_seen) < MAX_TRACKED_FORWARDED_CLIENTS:
            _seen[identity] = now
            return True
        return False


def client_identity(request) -> str:
    """The address a rate-limit budget belongs to.

    With ``TRUSTED_PROXY_COUNT = 0`` this is the connecting address, exactly as before: the app is
    reached directly and nothing needs to be trusted.

    With N > 0 it is the **Nth entry from the right** of ``X-Forwarded-For``. A proxy configured to
    do so appends the address it received from -- nginx only with
    ``proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;``, Caddy and Traefik by default --
    so with ``client -> CDN -> nginx -> app`` the app sees ``X-Forwarded-For: <client>, <cdn>`` and
    ``request.client.host = nginx``. Reading from the right walks back exactly N hops the operator
    says they run.

    Counting is always from the right, never from the left. Reaching for entry 0 -- which most
    guides do -- would read the one slot a caller fully controls whenever the chain runs longer
    than declared. (In a well-formed chain of exactly N entries the two coincide; the rule is the
    direction, not the index.)

    **What this cannot do.** It checks the chain's *length*, never who wrote it. If the declared
    count is higher than the number of proxies that actually append the header -- an operator
    typo, an nginx left on its default ``proxy_pass``, or a request reaching the origin without
    passing through the CDN at all -- then the entry read is one the caller wrote, and the caller
    picks its own identity. Nothing in this function can detect that; only verifying the peer
    could, and that is a different design. What it does instead is bound the damage: a flood of
    invented identities is admitted only up to ``MAX_TRACKED_FORWARDED_CLIENTS`` per window and
    then limited per connecting peer, so the failure mode is the old shared bucket rather than an
    unbounded key store.
    """
    hops = config.TRUSTED_PROXY_COUNT
    peer = get_remote_address(request)
    forwarded = ",".join(request.headers.getlist(XFF_HEADER))

    if hops <= 0:
        if forwarded:
            _warn_once(
                "xff_ignored",
                "X-Forwarded-For seen but TRUSTED_PROXY_COUNT=0, so every client shares one "
                "rate-limit bucket. If a reverse proxy is in front of this app, set it to the "
                "number of proxies you run (docs/CONFIGURATION.md).",
            )
        return peer

    # Every occurrence, joined in order. X-Forwarded-For is a list-typed field (RFC 7230 s3.2.2),
    # so repeated lines ARE one comma-joined value -- and `headers.get` returns only the first,
    # which is the line a caller can send ahead of the proxy's. HAProxy's `option forwardfor`
    # inserts its own field rather than merging, so this is not hypothetical: reading only the
    # first line let a caller pick a fresh identity per request and never be limited at all.
    chain = [part.strip() for part in forwarded.split(",") if part.strip()] if forwarded else []

    if len(chain) < hops:
        _warn_once(
            "xff_short",
            "TRUSTED_PROXY_COUNT=%d but requests arrive with %d X-Forwarded-For entr(y|ies); "
            "falling back to the connecting address. Either the count is too high or a proxy is "
            "not appending the header (nginx needs proxy_set_header X-Forwarded-For "
            "$proxy_add_x_forwarded_for).",
            hops, len(chain),
        )
        return peer

    address = _parse_address(chain[-hops])
    if address is None:
        _warn_once(
            "xff_unparseable",
            "X-Forwarded-For entry %d from the right is not an IP address (%r); falling back to "
            "the connecting address.", hops, chain[-hops],
        )
        return peer

    identity = str(address)
    if not _admit(identity, time.monotonic()):
        _warn_once(
            "xff_flood",
            "More than %d distinct X-Forwarded-For identities within %ds; new ones are being "
            "limited per connecting peer instead. Either traffic is genuinely that broad, or the "
            "chain is being forged because TRUSTED_PROXY_COUNT is higher than the number of "
            "proxies that actually append the header.",
            MAX_TRACKED_FORWARDED_CLIENTS, FORWARDED_CLIENT_TTL_SECONDS,
        )
        return peer

    return identity


def describe_configuration() -> str:
    """One line for the startup log, so 'did my setting take?' is a grep rather than a guess."""
    hops = config.TRUSTED_PROXY_COUNT
    if hops <= 0:
        return "rate limits keyed on the connecting address (TRUSTED_PROXY_COUNT=0)"
    return (
        f"rate limits keyed on X-Forwarded-For entry {hops} from the right "
        f"(TRUSTED_PROXY_COUNT={hops}); falls back to the connecting address when the chain is "
        f"shorter than that"
    )


limiter = Limiter(key_func=client_identity)
