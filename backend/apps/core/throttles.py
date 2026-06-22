# apps/core/throttles.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class CustomAnonRateThrottle(AnonRateThrottle):
    scope = 'anon'

class CustomUserRateThrottle(UserRateThrottle):
    scope = 'user'