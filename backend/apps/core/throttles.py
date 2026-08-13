# apps/core/throttles.py
import time
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class RateLimitInfoMixin:
  

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)


        if not hasattr(self, "history"):
            return allowed

        num_requests, duration = self.parse_rate(self.rate)
        remaining = max(num_requests - len(self.history), 0)
        reset_at = self.history[-1] + duration if self.history else self.timer() + duration

        info = {
            "limit": num_requests,
            "remaining": remaining,
            "reset_at": reset_at,
            "scope": self.scope,
        }

        existing = getattr(request, "_rate_limit_info", None)
        if existing is None or remaining < existing["remaining"]:
            request._rate_limit_info = info

        return allowed


class CustomAnonRateThrottle(RateLimitInfoMixin, AnonRateThrottle):
    scope = "anon"


class CustomUserRateThrottle(RateLimitInfoMixin, UserRateThrottle):
    scope = "user"
