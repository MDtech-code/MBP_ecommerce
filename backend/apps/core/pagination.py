from __future__ import annotations

from rest_framework.request import Request


def get_pagination_params(
    request: Request, default_page_size: int = 20
) -> tuple[int, int]:
    """
    Extract and validate pagination params from request query string.

    :param request: DRF request object
    :param default_page_size: fallback page size if not provided
    :return: (page, page_size) tuple, both guaranteed valid positive ints
    """
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(
            100, max(1, int(request.query_params.get("page_size", default_page_size)))
        )
    except (ValueError, TypeError):
        page, page_size = 1, default_page_size
    return page, page_size


def build_pagination_meta(
    page: int,
    page_size: int,
    total: int,
    source: str | None = None,
) -> dict:
    """
    Build a consistent pagination meta dict for list responses.

    :param page: current page number
    :param page_size: items per page
    :param total: total items matching the query
    :param source: optional cache source label (database/l1_memory/l2_redis)
    :return: dict to be passed as `meta` in success_response()
    """
    meta = {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": -(-total // page_size) if page_size else 0,
    }
    if source:
        meta["source"] = source
    return meta