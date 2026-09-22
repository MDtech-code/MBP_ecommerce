import pytest
from apps.core.timing import normalize_response_time


@pytest.mark.unit
@pytest.mark.parametrize("elapsed,expected", [(0, 0.5), (0.2, 0.3), (0.5, None), (1, None)])
def test_padding_only_sleeps_for_remaining_duration(mocker, elapsed, expected):
    mocker.patch("apps.core.timing.time.monotonic", return_value=10 + elapsed)
    sleep = mocker.patch("apps.core.timing.time.sleep")
    normalize_response_time(10)
    if expected is None:
        sleep.assert_not_called()
    else:
        sleep.assert_called_once_with(pytest.approx(expected))


@pytest.mark.unit
def test_custom_minimum(mocker):
    mocker.patch("apps.core.timing.time.monotonic", return_value=10.25)
    sleep = mocker.patch("apps.core.timing.time.sleep")
    normalize_response_time(10, min_seconds=1)
    sleep.assert_called_once_with(0.75)
