# apps/core/decorators.py
import functools
import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def require_user(task_label: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, user_id: int, *args, **kwargs):
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.warning(
                    f"{task_label} skipped — user not found",
                    extra={"user_id": user_id, "task": task_label},
                )
                return
            return func(self, user, *args, **kwargs)
        return wrapper
    return decorator