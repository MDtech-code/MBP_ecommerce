# apps/accounts/tests/test_serializers.py
from __future__ import annotations

import pytest

from apps.accounts.serializers import RegisterSerializer
from apps.core.error_codes import ErrorCode


def _errors(payload: dict) -> dict:
    """Return serializer errors for payload."""
    s = RegisterSerializer(data=payload)
    s.is_valid()
    return s.errors


def _valid(payload: dict) -> dict:
    """Return validated_data for a valid payload."""
    s = RegisterSerializer(data=payload)
    assert s.is_valid(), s.errors
    return s.validated_data


BASE = {
    "email": "test@example.com",
    "full_name": "John Doe",
    "password": "StrongPass123!",
    "confirm_password": "StrongPass123!",
}


class TestEmailValidation:

    def test_valid_email_passes_and_normalizes(self):
        data = _valid({**BASE, "email": "  TEST@EXAMPLE.COM  "})
        assert data["email"] == "test@example.com"

    def test_invalid_format_raises_400(self):
        errors = _errors({**BASE, "email": "not-an-email"})
        assert "email" in errors

    def test_blank_email_raises_400(self):
        errors = _errors({**BASE, "email": ""})
        assert "email" in errors

    def test_missing_email_raises_400(self):
        payload = {k: v for k, v in BASE.items() if k != "email"}
        errors = _errors(payload)
        assert "email" in errors


class TestFullNameValidation:

    def test_valid_two_word_name_passes(self):
        data = _valid({**BASE, "full_name": "John Doe"})
        assert data["full_name"] == "John Doe"

    def test_single_word_name_raises_400(self):
        errors = _errors({**BASE, "full_name": "John"})
        assert "full_name" in errors

    def test_blank_name_raises_400(self):
        errors = _errors({**BASE, "full_name": ""})
        assert "full_name" in errors

    def test_missing_name_raises_400(self):
        payload = {k: v for k, v in BASE.items() if k != "full_name"}
        errors = _errors(payload)
        assert "full_name" in errors


class TestPasswordValidation:

    def test_strong_password_passes(self):
        data = _valid(BASE)
        assert "password" in data

    def test_too_short_raises_400(self):
        errors = _errors({**BASE, "password": "Ab1!", "confirm_password": "Ab1!"})
        assert "password" in errors

    def test_blank_password_raises_400(self):
        errors = _errors({**BASE, "password": "", "confirm_password": ""})
        assert "password" in errors

    def test_missing_password_raises_400(self):
        payload = {k: v for k, v in BASE.items() if k != "password"}
        errors = _errors(payload)
        assert "password" in errors


class TestConfirmPasswordValidation:

    def test_matching_passwords_pass(self):
        data = _valid(BASE)
        # confirm_password must be popped from validated_data
        assert "confirm_password" not in data

    def test_mismatched_passwords_raise_400_with_correct_code(self):
        errors = _errors({**BASE, "confirm_password": "DifferentPass123!"})
        assert "confirm_password" in errors
        # error code must match ErrorCode.PASSWORD_MISMATCH
        detail = errors["confirm_password"]
        if isinstance(detail, list):
            detail = detail[0]
        assert str(getattr(detail, "code", "")) == ErrorCode.PASSWORD_MISMATCH

    def test_blank_confirm_password_raises_400(self):
        errors = _errors({**BASE, "confirm_password": ""})
        assert "confirm_password" in errors

    def test_validated_data_never_contains_confirm_password(self):
        data = _valid(BASE)
        assert "confirm_password" not in data