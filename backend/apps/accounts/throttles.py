# apps/accounts/throttles.py
from rest_framework.throttling import SimpleRateThrottle


class RegisterEmailRateThrottle(SimpleRateThrottle):
    """
    Caps attempts against one target email, independent of source IP.
    Runs alongside CustomAnonRateThrottle, not instead of it — this
    closes the gap IP throttling can't: someone rotating IPs but
    hammering the same email address.
    """
    scope = "register_email"

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}