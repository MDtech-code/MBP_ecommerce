# common/tests/factories.py
from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import EmailVerificationToken, User, UserProfile



class UserFactory(DjangoModelFactory):
    """
    Base user factory.

    Traits:
        verified   → is_verified=True
        unverified → is_verified=False  (default)
        admin      → role=ADMIN, is_staff=True
    """

    class Meta:
        model = User
        skip_postgeneration_save = True

    email     = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    password  = factory.PostGenerationMethodCall("set_password", "StrongPass123!")
    is_active   = True
    is_verified = False

    class Params:
        verified = factory.Trait(is_verified=True)
        admin    = factory.Trait(
            role=User.Role.ADMIN if hasattr(User, "Role") else "AD",
            is_staff=True,
        )


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)


class EmailVerificationTokenFactory(DjangoModelFactory):
    class Meta:
        model = EmailVerificationToken

    user = factory.SubFactory(UserFactory)