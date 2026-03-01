"""Shared utility helpers used across multiple modules."""

from starlette.requests import Request

# X-Forwarded-For is only trusted when the direct TCP connection comes from
# one of these addresses (i.e. a local reverse-proxy such as Caddy/nginx).
# Any other client can spoof this header — do NOT use it to bypass auth limits.
_TRUSTED_PROXIES: frozenset[str] = frozenset({"127.0.0.1", "::1"})


def get_client_ip(request: Request) -> str:
    """Return the real client IP.

    Trusts ``X-Forwarded-For`` only when the direct connection comes from a
    known local reverse-proxy (``_TRUSTED_PROXIES``).  Otherwise returns the
    raw ``request.client.host`` to prevent spoofing of brute-force counters.
    """
    direct_ip = request.client.host if request.client else None
    if direct_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return direct_ip or "unknown"
