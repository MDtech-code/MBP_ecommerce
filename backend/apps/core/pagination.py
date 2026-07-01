# apps/core/paginations.py
from __future__ import annotations

from rest_framework.request import Request


def get_pagination_params(
    request: Request,
    default_page_size: int = 20,
    max_page_size: int = 48,
) -> tuple[int, int, bool]:
    """
    Extract, validate, and bound pagination params from request query string.

    Args:
        request          : DRF request object
        default_page_size: fallback page size if not provided (default 20)
        max_page_size    : hard ceiling on page_size to prevent DB abuse (default 48)

    Returns:
        (page, page_size, is_valid)
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
    """
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (ValueError, TypeError):
        return 1, default_page_size, False

    try:
        page_size = min(
            max_page_size,
            max(1, int(request.query_params.get("page_size", default_page_size))),
        )
    except (ValueError, TypeError):
        return 1, default_page_size, False

    return page, page_size, True


def build_pagination_meta(
    page: int,
    page_size: int,
    total: int,
    *,
    source: str | None = None,
    sort: str | None = None,
    elapsed_ms: float | None = None,
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
    """
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    showing_from = ((page - 1) * page_size) + 1 if total > 0 else 0
    showing_to = min(page * page_size, total)

    meta = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "showing_from": showing_from,
        "showing_to": showing_to,
        "has_next": page < total_pages,
        "has_previous": page > 1,
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
# from __future__ import annotations

# from rest_framework.request import Request


# def get_pagination_params(
#     request: Request, default_page_size: int = 20
# ) -> tuple[int, int]:
#     """
#     Extract and validate pagination params from request query string.

#     :param request: DRF request object
#     :param default_page_size: fallback page size if not provided
#     :return: (page, page_size) tuple, both guaranteed valid positive ints
#     """
#     try:
#         page = max(1, int(request.query_params.get("page", 1)))
#         page_size = min(
#             100, max(1, int(request.query_params.get("page_size", default_page_size)))
#         )
#     except (ValueError, TypeError):
#         page, page_size = 1, default_page_size
#     return page, page_size


# def build_pagination_meta(
#     page: int,
#     page_size: int,
#     total: int,
#     source: str | None = None,
# ) -> dict:
#     """
#     Build a consistent pagination meta dict for list responses.

#     :param page: current page number
#     :param page_size: items per page
#     :param total: total items matching the query
#     :param source: optional cache source label (database/l1_memory/l2_redis)
#     :return: dict to be passed as `meta` in success_response()
#     """
#     meta = {
#         "page": page,
#         "page_size": page_size,
#         "total_items": total,
#         "total_pages": -(-total // page_size) if page_size else 0,
#     }
#     if source:
#         meta["source"] = source
#     return meta