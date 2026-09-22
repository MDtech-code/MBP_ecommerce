"""Rule matrices live here; serializers/workflows only prove their wiring."""
import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import (
    validate_email_format, validate_full_name,
    validate_passwords_match, validate_strong_password,
)
from apps.core.error_codes import ErrorCode

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("raw,expected", [
    (" MD@EXAMPLE.COM ", "md@example.com"),
    ("first.last+shop@example.co.uk", "first.last+shop@example.co.uk"),
])
def test_email_normalization(raw, expected):
    assert validate_email_format(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "missing-at", "a@b", "@example.com", "a b@example.com"])
def test_invalid_email_has_machine_code(raw):
    with pytest.raises(ValidationError) as error:
        validate_email_format(raw)
    assert error.value.code == ErrorCode.EMAIL_INVALID_FORMAT


@pytest.mark.parametrize("raw,expected", [
    ("  MD   Khan  ", "MD Khan"), ("Ali\tHassan\nKhan", "Ali Hassan Khan"),
])
def test_full_name_normalization(raw, expected):
    assert validate_full_name(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "MD"])
def test_full_name_requires_two_words(raw):
    with pytest.raises(ValidationError) as error:
        validate_full_name(raw)
    assert error.value.code == ErrorCode.INVALID_FULL_NAME


@pytest.mark.parametrize("password", ["x7!", "123456789012", "password"])
def test_configured_password_policy_rejects_weak_inputs(password):
    with pytest.raises(ValidationError) as error:
        validate_strong_password(password)
    assert error.value.messages
    # Django expands list messages into individual ValidationError objects.
    assert all(detail.code == ErrorCode.PASSWORD_TOO_WEAK for detail in error.value.error_list)


def test_valid_password_is_not_normalized():
    value = "  Distinctive-Phrase-593!  "
    assert validate_strong_password(value) == value


def test_matching_passwords_return_none():
    assert validate_passwords_match("ExactPass123!", "ExactPass123!") is None


@pytest.mark.parametrize("confirmation", ["ExactPass123! ", "exactpass123!", ""])
def test_password_match_is_exact(confirmation):
    with pytest.raises(ValidationError) as error:
        validate_passwords_match("ExactPass123!", confirmation)
    assert error.value.code == ErrorCode.PASSWORD_MISMATCH
