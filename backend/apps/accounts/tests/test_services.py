# apps/accounts/tests/test_services.py
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from django.db import IntegrityError

from apps.accounts.models import  EmailVerificationToken, User, UserProfile
from apps.cart.models import Cart
from apps.accounts.services.registration import register_user
from apps.core.exceptions import DomainError
from apps.common.tests.factories import UserFactory


VALID_PAYLOAD = {
    "email": "newuser@example.com",
    "full_name": "John Doe",
    "password": "StrongPass123!",
}


@pytest.mark.django_db
class TestRegisterUserHappyPath:

    def setup_method(self):
        # patch task dispatch for every test in this class
        self.task_patcher = patch(
            "apps.accounts.services.registration.send_verification_email_task"
        )
        self.mock_task = self.task_patcher.start()

    def teardown_method(self):
        self.task_patcher.stop()

    def test_returns_user_instance(self):
        user = register_user(**VALID_PAYLOAD)
        assert isinstance(user, User)

    def test_user_saved_to_db_with_correct_email(self):
        user = register_user(**VALID_PAYLOAD)
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_user_saved_with_correct_full_name(self):
        user = register_user(**VALID_PAYLOAD)
        assert user.full_name == "John Doe"

    def test_password_is_hashed(self):
        user = register_user(**VALID_PAYLOAD)
        assert user.password != "StrongPass123!"
        assert user.check_password("StrongPass123!")

    def test_user_profile_created_and_linked(self):
        user = register_user(**VALID_PAYLOAD)
        assert UserProfile.objects.filter(user=user).exists()

    def test_cart_created_and_linked(self):
        user = register_user(**VALID_PAYLOAD)
        assert Cart.objects.filter(user=user).exists()

    def test_email_verification_token_created_and_linked(self):
        user = register_user(**VALID_PAYLOAD)
        assert EmailVerificationToken.objects.filter(user=user).exists()

    def test_verification_task_dispatched(self):
        user = register_user(**VALID_PAYLOAD)
        self.mock_task.delay.assert_called_once()

    def test_email_normalized_to_lowercase(self):
        user = register_user(**{**VALID_PAYLOAD, "email": "UPPER@EXAMPLE.COM"})
        assert user.email == "upper@example.com"


@pytest.mark.django_db
class TestRegisterUserBusinessRules:

    def setup_method(self):
        self.task_patcher = patch(
            "apps.accounts.services.registration.send_verification_email_task"
        )
        self.task_patcher.start()

    def teardown_method(self):
        self.task_patcher.stop()

    def test_duplicate_email_raises_domain_error_409(self):
        UserFactory(email="newuser@example.com")
        with pytest.raises(DomainError) as exc_info:
            register_user(**VALID_PAYLOAD)
        assert exc_info.value.status_code == 409

    def test_duplicate_email_raises_correct_error_code(self):
        from apps.core.error_codes import ErrorCode
        UserFactory(email="newuser@example.com")
        with pytest.raises(DomainError) as exc_info:
            register_user(**VALID_PAYLOAD)
        assert exc_info.value.code == ErrorCode.EMAIL_ALREADY_EXISTS

    def test_race_condition_integrity_error_raises_domain_error_409(self):
        """
        Simulate two requests passing ensure_email_unique simultaneously.
        IntegrityError on create_user must be caught and raised as DomainError.
        """
        with patch(
            "apps.accounts.services.registration.ensure_email_unique"
        ):  # bypass first check
            with patch(
                "apps.accounts.models.User.objects.create_user",
                side_effect=IntegrityError,
            ):
                with pytest.raises(DomainError) as exc_info:
                    register_user(**VALID_PAYLOAD)
                assert exc_info.value.status_code == 409


@pytest.mark.django_db
class TestRegisterUserAtomicity:

    def setup_method(self):
        self.task_patcher = patch(
            "apps.accounts.services.registration.send_verification_email_task"
        )
        self.task_patcher.start()

    def teardown_method(self):
        self.task_patcher.stop()

    def test_cart_failure_rolls_back_entire_transaction(self):
        with patch(
            "apps.accounts.services.registration.Cart.objects.create",
            side_effect=Exception("DB failure"),
        ):
            with pytest.raises(Exception):
                register_user(**VALID_PAYLOAD)

        assert not User.objects.filter(email="newuser@example.com").exists()
        assert not UserProfile.objects.filter(
            user__email="newuser@example.com"
        ).exists()

    def test_token_failure_rolls_back_entire_transaction(self):
        with patch(
            "apps.accounts.services.registration.EmailVerificationToken.objects.create",
            side_effect=Exception("DB failure"),
        ):
            with pytest.raises(Exception):
                register_user(**VALID_PAYLOAD)

        assert not User.objects.filter(email="newuser@example.com").exists()


@pytest.mark.django_db
class TestRegisterUserTaskDispatch:

    def test_task_failure_does_not_raise(self):
        """
        Task dispatch failure must be swallowed.
        User account is committed and valid.
        """
        with patch(
            "apps.accounts.services.registration.send_verification_email_task"
        ) as mock_task:
            mock_task.delay.side_effect = Exception("Celery broker down")
            # must NOT raise
            user = register_user(**VALID_PAYLOAD)

        assert User.objects.filter(email="newuser@example.com").exists()

    def test_task_failure_does_not_roll_back_user(self):
        with patch(
            "apps.accounts.services.registration.send_verification_email_task"
        ) as mock_task:
            mock_task.delay.side_effect = Exception("Celery broker down")
            register_user(**VALID_PAYLOAD)

        assert User.objects.filter(email="newuser@example.com").exists()
        assert UserProfile.objects.filter(user__email="newuser@example.com").exists()
        assert Cart.objects.filter(user__email="newuser@example.com").exists()