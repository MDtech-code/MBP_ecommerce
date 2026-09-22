from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.throttles import CustomAnonRateThrottle, RateLimitInfoMixin


@pytest.mark.unit
def test_real_throttle_blocks_then_resets_with_metadata(mocker):
    mocker.patch.object(CustomAnonRateThrottle, "THROTTLE_RATES", {"anon": "2/min"})
    now = mocker.Mock(return_value=1000)
    request = APIRequestFactory().post("/register/", REMOTE_ADDR="192.0.2.1")
    request.user = SimpleNamespace(is_authenticated=False)

    def attempt(req=request):
        # DRF creates a fresh throttle for every request.
        throttle = CustomAnonRateThrottle()
        throttle.timer = now
        return throttle.allow_request(req, None), throttle

    assert attempt()[0] is True
    assert request._rate_limit_info["remaining"] == 1
    assert attempt()[0] is True
    assert request._rate_limit_info["remaining"] == 0
    allowed, throttle = attempt()
    assert allowed is False
    assert throttle.wait() == 60
    assert request._rate_limit_info["reset_at"] == 1060

    other = APIRequestFactory().post("/register/", REMOTE_ADDR="192.0.2.2")
    other.user = request.user
    assert attempt(other)[0] is True

    # New request after the window expires (no metadata from a prior request).
    fresh = APIRequestFactory().post("/register/", REMOTE_ADDR="192.0.2.1")
    fresh.user = request.user
    now.return_value = 1060
    assert attempt(fresh)[0] is True
    assert fresh._rate_limit_info["remaining"] == 1


@pytest.mark.unit
def test_authenticated_anon_throttle_has_no_history():
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))
    assert CustomAnonRateThrottle().allow_request(request, None) is True
    assert not hasattr(request, "_rate_limit_info")


@pytest.mark.unit
def test_most_restrictive_metadata_wins():
    class Parent:
        def allow_request(self, request, view):
            return True

    class Throttle(RateLimitInfoMixin, Parent):
        history = [1000]
        rate = "5/min"
        scope = "test"
        parse_rate = staticmethod(lambda rate: (5, 60))

    request = SimpleNamespace(_rate_limit_info={"remaining": 1, "scope": "stricter"})
    assert Throttle().allow_request(request, None) is True
    assert request._rate_limit_info == {"remaining": 1, "scope": "stricter"}
