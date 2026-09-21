import pytest
from apps.common.utils.email_utils import mask_email


@pytest.mark.unit
@pytest.mark.parametrize("email,expected", [
    ("md@example.com", "m***@example.com"),
    ("m@example.com", "m***@example.com"),
    ("first.last+shop@example.co.uk", "f***@example.co.uk"),
])
def test_mask_email_hides_local_part(email, expected):
    assert mask_email(email) == expected
