# apps/accounts/services/otp_service.py
import logging
import random

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

_PREFIX  = "phone_otp:"
_TTL_SEC = 300   # 5 minutes


def _cache_key(user_id: int) -> str:
    return f"{_PREFIX}{user_id}"


def send_phone_otp(*, user_id: int, phone: str) -> dict:
    """
    Generate a 6-digit OTP, store it in cache, and 'send' it.

    MOCK IMPLEMENTATION — logs OTP to console and returns it in
    the response under `debug_otp`. Replace the send block with a
    real SMS provider later; everything else stays the same.

    Returns:
        {"detail": "OTP sent.", "debug_otp": "123456"}
        Remove `debug_otp` key when going to production.
    """
    otp  = str(random.randint(100_000, 999_999))
    key  = _cache_key(user_id)

    cache.set(
        key,
        {"otp": otp, "phone": phone},
        timeout=_TTL_SEC,
    )

    # ── MOCK: replace this block with real SMS call ──────────────────
    logger.info(
        "[MOCK OTP] user_id=%s  phone=%s  otp=%s  (valid 5 min)",
        user_id, phone, otp,
    )
    # ─────────────────────────────────────────────────────────────────

    return {"detail": "OTP sent.", "debug_otp": otp}


def verify_phone_otp(*, user_id: int, phone: str, otp: str):
    """
    Validate OTP from cache.

    Returns:
        (True, None)           on success
        (False, error_message) on failure
    """
    key    = _cache_key(user_id)
    stored = cache.get(key)

    if not stored:
        return False, "OTP has expired. Please request a new one."

    if stored["phone"] != phone:
        return False, "Phone number does not match the one OTP was sent to."

    if stored["otp"] != otp:
        return False, "Invalid OTP. Please try again."

    cache.delete(key)   # single-use
    return True, None