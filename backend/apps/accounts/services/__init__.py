# apps/accounts/services/__init__.py

from .registration import register_user
from .email_verification import verify_email, resend_verification
from .account_deletion import delete_user_account
from .password import (
    request_password_reset,
    confirm_password_reset,
    
)
from .email_change import (
    request_email_change,
    
)
from .auth import (
    login_user,
    logout_user,
    refresh_access_token,
)
from .profile import (
    get_user_profile,
    update_user_profile,
    update_user_avatar,
    get_user_addresses,
    create_user_address,
    get_user_addresses,
    update_user_address,
    delete_user_address,
    set_default_address,
)

__all__ = [
    "register_user",
    "verify_email",
    "resend_verification",
    "delete_user_account",
    "request_password_reset",
    "confirm_password_reset",
    
    "request_email_change",
    
    "login_user",
    "logout_user",
    "refresh_access_token",
    "get_user_profile",
    "update_user_profile",
    "update_user_avatar",
    "get_user_addresses",
    "create_user_address",
    "get_user_address",
    "update_user_address",
    "delete_user_address",
    "set_default_address",
]