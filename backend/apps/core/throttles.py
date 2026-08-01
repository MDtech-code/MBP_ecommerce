# apps/core/throttles.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle



class RegistrationRateThrottle(AnonRateThrottle):
    """
    Strict throttle for registration endpoint.
    5 attempts per hour per IP.
    Prevents mass account creation and email bombing.
    """
    scope = "registration"
class CustomAnonRateThrottle(AnonRateThrottle):
    scope = 'anon'

class CustomUserRateThrottle(UserRateThrottle):
    scope = 'user'