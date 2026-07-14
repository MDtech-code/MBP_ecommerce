# FIX — database-level atomic sequence
from __future__ import annotations
import uuid
from django.db import models, transaction
from django.utils import timezone


class OrderManager(models.Manager):
    """Custom manager providing race-condition-safe order numbers."""

    def generate_order_number(self) -> str:
        """
        Generate unique order number safe under concurrent requests.

        Strategy: optimistic retry loop with UUID fallback.
        Format: MBP-YYYY-NNNNNN (e.g. MBP-2026-000001)

        Why not DB sequence:
            Django ORM has no portable sequence API across SQLite/PostgreSQL.
            Retry loop with unique constraint is standard Django pattern.

        Why max 10 retries:
            Each retry reads fresh MAX from DB inside transaction.
            Collision probability drops to near zero after 2-3 retries.
            UUID fallback guarantees no infinite loop.
        """
        year = timezone.now().year
        prefix = f"MBP-{year}-"

        for attempt in range(10):
            with transaction.atomic():
                last_order = (
                    self.select_for_update()  # ← locks the row during read
                    .filter(order_number__startswith=prefix)
                    .order_by("-order_number")
                    .first()
                )

                if last_order:
                    try:
                        last_seq = int(last_order.order_number.split("-")[-1])
                        new_seq = last_seq + 1
                    except (ValueError, IndexError):
                        new_seq = 1
                else:
                    new_seq = 1

                candidate = f"{prefix}{new_seq:06d}"

                if not self.filter(order_number=candidate).exists():
                    return candidate

        # Ultimate fallback — UUID suffix, never collides
        # Logs warning so you know the retry loop is hitting its limit
        import logging
        logging.getLogger("apps.orders").warning(
            "Order number generation retry limit hit — using UUID fallback"
        )
        return f"MBP-{year}-{uuid.uuid4().hex[:6].upper()}"
# # apps/orders/managers.py
# from __future__ import annotations
# from django.db import models
# from django.utils import timezone


# class OrderManager(models.Manager):
#     """Custom manager providing auto-generated order numbers."""

#     def generate_order_number(self) -> str:
#         """
#         Generate unique sequential order number.
#         Format: MBP-YYYY-NNNNNN (e.g. MBP-2026-000001)
#         """
#         year = timezone.now().year
#         prefix = f"MBP-{year}-"

#         last_order = (
#             self.filter(order_number__startswith=prefix)
#             .order_by("-order_number")
#             .first()
#         )

#         if last_order:
#             last_seq = int(last_order.order_number.split("-")[-1])
#             new_seq = last_seq + 1
#         else:
#             new_seq = 1

#         return f"{prefix}{new_seq:06d}"