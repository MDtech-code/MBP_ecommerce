import pytest
from django.http import HttpResponse
from apps.accounts.utils.cookie_utils import (
    EMAIL_COOKIE_NAME, clear_email_cookie, set_email_cookie,
)

pytestmark = pytest.mark.unit


def test_pending_email_cookie_is_short_lived_readable_and_secure():
    response = HttpResponse()
    set_email_cookie(response, "md@example.com")
    cookie = response.cookies[EMAIL_COOKIE_NAME]
    assert cookie.value == "md@example.com"
    assert cookie["path"] == "/"
    assert cookie["max-age"] == 900
    assert cookie["secure"] is True
    assert cookie["httponly"] == ""
    assert cookie["samesite"] == "Lax"


def test_clear_uses_same_name_and_path_as_set():
    response = HttpResponse()
    set_email_cookie(response, "md@example.com")
    path = response.cookies[EMAIL_COOKIE_NAME]["path"]
    clear_email_cookie(response)
    assert response.cookies[EMAIL_COOKIE_NAME]["path"] == path
    assert response.cookies[EMAIL_COOKIE_NAME]["max-age"] == 0
    assert response.cookies[EMAIL_COOKIE_NAME].value == ""
