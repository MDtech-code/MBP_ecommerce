# apps/core/paginations.py
from __future__ import annotations

import logging
from typing import NamedTuple

from rest_framework.request import Request

logger = logging.getLogger("apps.core")


class PaginationParams(NamedTuple):
    """
    Structured result for get_pagination_params.

    Why NamedTuple instead of a plain tuple:
        As this helper spreads across apps (orders, products, cart, accounts...),
        callers doing `page, page_size, is_valid = get_pagination_params(...)`
        is easy to get wrong (wrong order, forgetting to check is_valid).
        NamedTuple lets callers do `params.page`, `params.is_valid`, etc.,
        while still unpacking normally like a tuple for backward compatibility.
    """
    page: int
    page_size: int
    is_valid: bool


def get_pagination_params(
    request: Request,
    default_page_size: int = 20,
    max_page_size: int = 48,
) -> PaginationParams:
    """
    Extract, validate, and bound pagination params from request query string.

    Args:
        request          : DRF request object
        default_page_size: fallback page size if not provided (default 20)
        max_page_size    : hard ceiling on page_size to prevent DB abuse (default 48)

    Returns:
        PaginationParams(page, page_size, is_valid)
            page      : always >= 1
            page_size : always between 1 and max_page_size
            is_valid  : False if params were unparseable (caller should return 400)

    Why is_valid bool instead of raising exception:
        Views handle validation errors differently.
        Returning False lets the caller decide the response shape.
        Raising here would couple pagination logic to HTTP response logic.

    Why max_page_size=48 default:
        Frontend grid shows 12 per page.
        48 = 4 pages worth — generous for power users.
        100+ rows = heavy serialization + DB load per request.
        Caller can override for endpoints that need different limits.

    Why separate default and max:
        List endpoint: default=12, max=48  (grid layout)
        Admin export:  default=50, max=200 (bulk operations)
        Same function, different configs — no code duplication.

    Fixes applied:
        - max_page_size is floored to 1 to avoid a caller accidentally
          passing 0/negative and silently producing zero-item pages.
        - If `page` parses fine but `page_size` doesn't, we no longer
          discard the valid `page` — we keep it and only fall back
          page_size to the default.
        - Invalid input is logged (once) so bad client requests are
          visible in apps.core logs instead of failing silently.
    """
    max_page_size = max(1, max_page_size)

    raw_page = request.query_params.get("page", 1)
    try:
        page = max(1, int(raw_page))
    except (ValueError, TypeError):
        logger.warning(
            "Invalid 'page' query param received: %r (path=%s)",
            raw_page, request.path,
        )
        return PaginationParams(1, default_page_size, False)

    raw_page_size = request.query_params.get("page_size", default_page_size)
    try:
        page_size = min(max_page_size, max(1, int(raw_page_size)))
    except (ValueError, TypeError):
        logger.warning(
            "Invalid 'page_size' query param received: %r (path=%s)",
            raw_page_size, request.path,
        )
        # page was valid — keep it instead of resetting to 1.
        return PaginationParams(page, default_page_size, False)

    return PaginationParams(page, page_size, True)


def build_pagination_meta(
    page: int,
    page_size: int,
    total: int,
    *,
    source: str | None = None,
    sort: str | None = None,
    elapsed_ms: float | None = None,
    clamp_page: bool = True,
) -> dict:
    """
    Build a consistent, frontend-ready pagination meta dict.

    Args:
        page       : current page number
        page_size  : items per page
        total      : total items matching the query
        source     : cache source label — database / l1_memory / l2_redis
        sort       : active sort key — newest / price_asc / etc.
        elapsed_ms : full request timing in milliseconds
        clamp_page : if True (default), clamp `page` down to the last valid
                     page when it overshoots total_pages, so showing_from/
                     showing_to never produce nonsense like "19981-50 of 50".

    Returns:
        dict with all keys frontend needs to render pagination UI.

    Why showing_from / showing_to:
        Frontend shows "Showing 1–12 of 540 products".
        Pre-calculated here → frontend renders directly, no math needed.

    Why has_next / has_previous:
        Frontend enables/disables prev/next buttons based on these.
        Simpler than frontend computing page < total_pages itself.

    Why total not total_items:
        "total" is shorter and consistent with DRF conventions.
        "total_items" was the old name — unified here.

    Why keyword-only args for source/sort/elapsed_ms:
        These are optional observability fields.
        Keyword-only forces callers to be explicit — no positional confusion.
        None values are excluded from output to keep response clean.

    Fix applied:
        - page is clamped to [1, total_pages] before computing
          showing_from/showing_to/has_next/has_previous, when clamp_page
          is True. Without this, a client requesting page=999 on a
          3-page result set previously produced negative/garbage ranges.
    """
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    effective_page = page
    if clamp_page and total_pages > 0:
        effective_page = min(max(page, 1), total_pages)
    elif total_pages == 0:
        effective_page = 1

    showing_from = ((effective_page - 1) * page_size) + 1 if total > 0 else 0
    showing_to = min(effective_page * page_size, total)

    meta = {
        "page": effective_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "showing_from": showing_from,
        "showing_to": showing_to,
        "has_next": effective_page < total_pages,
        "has_previous": effective_page > 1,
    }

    # Why conditional inclusion:
    #   Not every endpoint uses cache or sorting.
    #   Including null values clutters response for simple endpoints.
    if source is not None:
        meta["source"] = source
    if sort is not None:
        meta["sort"] = sort
    if elapsed_ms is not None:
        meta["elapsed_ms"] = elapsed_ms

    return meta
# # apps/core/paginations.py
# from __future__ import annotations

# from rest_framework.request import Request


# def get_pagination_params(
#     request: Request,
#     default_page_size: int = 20,
#     max_page_size: int = 48,
# ) -> tuple[int, int, bool]:
#     """
#     Extract, validate, and bound pagination params from request query string.

#     Args:
#         request          : DRF request object
#         default_page_size: fallback page size if not provided (default 20)
#         max_page_size    : hard ceiling on page_size to prevent DB abuse (default 48)

#     Returns:
#         (page, page_size, is_valid)
#             page      : always >= 1
#             page_size : always between 1 and max_page_size
#             is_valid  : False if params were unparseable (caller should return 400)

#     Why is_valid bool instead of raising exception:
#         Views handle validation errors differently.
#         Returning False lets the caller decide the response shape.
#         Raising here would couple pagination logic to HTTP response logic.

#     Why max_page_size=48 default:
#         Frontend grid shows 12 per page.
#         48 = 4 pages worth — generous for power users.
#         100+ rows = heavy serialization + DB load per request.
#         Caller can override for endpoints that need different limits.

#     Why separate default and max:
#         List endpoint: default=12, max=48  (grid layout)
#         Admin export:  default=50, max=200 (bulk operations)
#         Same function, different configs — no code duplication.
#     """
#     try:
#         page = max(1, int(request.query_params.get("page", 1)))
#     except (ValueError, TypeError):
#         return 1, default_page_size, False

#     try:
#         page_size = min(
#             max_page_size,
#             max(1, int(request.query_params.get("page_size", default_page_size))),
#         )
#     except (ValueError, TypeError):
#         return 1, default_page_size, False

#     return page, page_size, True


# def build_pagination_meta(
#     page: int,
#     page_size: int,
#     total: int,
#     *,
#     source: str | None = None,
#     sort: str | None = None,
#     elapsed_ms: float | None = None,
# ) -> dict:
#     """
#     Build a consistent, frontend-ready pagination meta dict.

#     Args:
#         page       : current page number
#         page_size  : items per page
#         total      : total items matching the query
#         source     : cache source label — database / l1_memory / l2_redis
#         sort       : active sort key — newest / price_asc / etc.
#         elapsed_ms : full request timing in milliseconds

#     Returns:
#         dict with all keys frontend needs to render pagination UI.

#     Why showing_from / showing_to:
#         Frontend shows "Showing 1–12 of 540 products".
#         Pre-calculated here → frontend renders directly, no math needed.

#     Why has_next / has_previous:
#         Frontend enables/disables prev/next buttons based on these.
#         Simpler than frontend computing page < total_pages itself.

#     Why total not total_items:
#         "total" is shorter and consistent with DRF conventions.
#         "total_items" was the old name — unified here.

#     Why keyword-only args for source/sort/elapsed_ms:
#         These are optional observability fields.
#         Keyword-only forces callers to be explicit — no positional confusion.
#         None values are excluded from output to keep response clean.
#     """
#     total_pages = (total + page_size - 1) // page_size if page_size else 0
#     showing_from = ((page - 1) * page_size) + 1 if total > 0 else 0
#     showing_to = min(page * page_size, total)

#     meta = {
#         "page": page,
#         "page_size": page_size,
#         "total": total,
#         "total_pages": total_pages,
#         "showing_from": showing_from,
#         "showing_to": showing_to,
#         "has_next": page < total_pages,
#         "has_previous": page > 1,
#     }

#     # Why conditional inclusion:
#     #   Not every endpoint uses cache or sorting.
#     #   Including null values clutters response for simple endpoints.
#     if source is not None:
#         meta["source"] = source
#     if sort is not None:
#         meta["sort"] = sort
#     if elapsed_ms is not None:
#         meta["elapsed_ms"] = elapsed_ms

#     return meta
