from __future__ import annotations

from typing import Any
import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.common.choices.role import Role

User = get_user_model()
logger = logging.getLogger(__name__)








class IsAdmin(BasePermission):
    """
    Allows access to users with ADMIN role.
    """
    message = "You must be an admin to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        allowed: bool = getattr(request.user, "role", None) == Role.ADMIN
        if not allowed:
            logger.warning(
                "User %s denied admin access: role=%s",
                getattr(request.user, "username", "anonymous"),
                getattr(request.user, "role", None),
            )
        return allowed


class IsCustomer(BasePermission):
    """
    Allows access to verified customers only.
    """
    message = "You must be a verified customer to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        is_customer: bool = getattr(request.user, "role", None) == Role.CUSTOMER
        is_verified: bool = bool(getattr(request.user, "is_verified", False))

        allowed = is_customer and is_verified
        if not allowed:
            logger.warning(
                "User %s denied customer access: role=%s, is_verified=%s",
                getattr(request.user, "username", "anonymous"),
                getattr(request.user, "role", None),
                is_verified,
            )
        return allowed


class IsVerified(BasePermission):
    """
    Allows access to verified users.
    """
    message = "You are not verified to perform this action. Please verify your account."

    def has_permission(self, request: Request, view: APIView) -> bool:
        is_verified: bool = bool(getattr(request.user, "is_verified", False))
        if not is_verified:
            logger.warning(
                "User %s denied access: is_verified=%s",
                getattr(request.user, "username", "anonymous"),
                is_verified,
            )
        return is_verified


class IsNotAuthenticated(BasePermission):
    """
    Allows access only to non-authenticated users.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if getattr(request.user, "is_authenticated", False):
            logger.warning(
                "Authenticated user %s denied access to non-authenticated action",
                getattr(request.user, "username", "anonymous"),
            )
            return False
        return True


class RoleBasedProfilePermission(BasePermission):
    """
    Composite role-based permission for profile access.

    Rules:
        - User must be verified.
        - Customer: allowed if verified.
        - Admins: always allowed.
    """
    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not getattr(request.user, "is_verified", False):
            logger.warning(
                "User %s denied role access: not verified",
                getattr(request.user, "username", "anonymous"),
            )
            return False

        role = getattr(request.user, "role", None)

        if role == Role.CUSTOMER:
            logger.info("User %s granted CUSTOMER profile access", request.user.username)
            return True

      

        if role == Role.ADMIN:
            logger.info("User %s granted admin profile access", request.user.username)
            return True

        logger.warning(
            "User %s denied profile access: unknown role=%s",
            request.user.username,
            role,
        )
        return False

