# apps/core/paginations.py
from __future__ import annotations

import logging
from typing import NamedTuple

from rest_framework.request import Request

logger = logging.getLogger(__name__)


class PaginationParams(NamedTuple):
    page: int
    page_size: int
    is_valid: bool


def get_pagination_params(
    request: Request,
    default_page_size: int = 20,
    max_page_size: int = 48,
) -> PaginationParams:
    
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
  
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    effective_page = page
    if clamp_page and total_pages > 0:
        effective_page = min(max(page, 1), total_pages)
    elif total_pages == 0:
        effective_page = 1

    showing_from = ((effective_page - 1) * page_size) + 1 if total > 0 else 0
    showing_to = min(effective_page * page_size, total)


    pagination = {
        "page": effective_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "showing_from": showing_from,
        "showing_to": showing_to,
        "has_next": effective_page < total_pages,
        "has_previous": effective_page > 1,
    }


    meta:dict = {"pagination": pagination}

    
    if source is not None:
        meta["source"] = source
    if sort is not None:
        meta["sort"] = sort
    if elapsed_ms is not None:
        meta["elapsed_ms"] = elapsed_ms

    return meta
