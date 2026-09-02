"""Shared rate-limiter instance.

Defined here to avoid circular imports between main.py and routes/*.py.
Import this module in routes that need @limiter.limit().
"""
import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address

from core import config

XFF_HEADER = "x-forwarded-for"


def client_identity(request) -> str:
    """The address a rate-limit budget belongs to.

    With `TRUSTED_PROXY_COUNT = 0` this is the connecting address, exactly as before: the app is
    reached directly and nothing needs to be trusted.

    With N > 0 it is the **Nth entry from the right** of ``X-Forwarded-For``. Each proxy appends
    the address it received from, so with ``client -> CDN -> nginx -> app`` the app sees
    ``X-Forwarded-For: <client>, <cdn>`` and ``request.client.host = nginx``. Reading from the
    right walks back exactly N hops we control; everything to the left of that boundary was
    supplied from outside and can say anything.

    Never read entry 0. That is the value most guides reach for and the one an attacker fully
    controls -- trusting it would trade "innocent users are blocked" for "rate limiting does
    nothing", on the endpoints that run a backtest.

    Fails closed: an absent header, a chain shorter than declared, or a value that is not an IP
    address all fall back to the connecting address. A request that did not arrive through the
    declared chain is not trusted to describe itself, and a short header is precisely what a
    spoofing attempt looks like.
    """
    hops = config.TRUSTED_PROXY_COUNT
    if hops <= 0:
        return get_remote_address(request)

    forwarded = request.headers.get(XFF_HEADER)
    if forwarded:
        chain = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(chain) >= hops:
            candidate = chain[-hops]
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass  # not an address -- fall through to the connecting peer

    return get_remote_address(request)


limiter = Limiter(key_func=client_identity)
