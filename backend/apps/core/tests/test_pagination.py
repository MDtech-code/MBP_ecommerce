# backend/apps/core/tests/test_pagination.py
"""
Tests for apps.core.pagination — get_pagination_params and build_pagination_meta.

These functions are used by EVERY list endpoint in the backend.
Products list, orders list, cart items — all use these helpers.

If get_pagination_params silently returns wrong page numbers,
users see wrong data with no error.
If build_pagination_meta computes wrong has_next, frontend
shows/hides the Next button incorrectly.

Test structure:

    Layer 1 — get_pagination_params()
        Extracts page and page_size from request query string.
        Tests: valid input, invalid input, boundary values,
               is_valid flag behavior.

    Layer 2 — build_pagination_meta()
        Builds the pagination dict for the response.
        Tests: correct calculations, page clamping, optional fields,
               edge cases (0 total, 1 item, exact page boundaries).
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.pagination import (
    PaginationParams,
    build_pagination_meta,
    get_pagination_params,
)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _make_request(query_string: str = ""):
    """
    Build a DRF request with query parameters.

    Args:
        query_string: URL query string e.g. "page=2&page_size=12"
    """
    factory = APIRequestFactory()
    raw = factory.get(f"/test/?{query_string}")
    from rest_framework.request import Request
    from rest_framework.parsers import JSONParser
    return Request(raw, parsers=[JSONParser()])


# ─── Layer 1: get_pagination_params() ────────────────────────────────────────

@pytest.mark.unit
class TestGetPaginationParams:
    """
    Unit tests for get_pagination_params().

    This function reads page and page_size from the request query string,
    validates them, and returns a PaginationParams NamedTuple.
    """

    # ── Return type ───────────────────────────────────────────────────────────

    def test_returns_pagination_params_namedtuple(self):
        """Return type must be PaginationParams NamedTuple."""
        request = _make_request("page=1&page_size=10")
        result = get_pagination_params(request)
        assert isinstance(result, PaginationParams)

    def test_namedtuple_has_three_fields(self):
        """PaginationParams must have page, page_size, is_valid fields."""
        request = _make_request()
        result = get_pagination_params(request)
        assert hasattr(result, "page")
        assert hasattr(result, "page_size")
        assert hasattr(result, "is_valid")

    # ── Valid input — happy path ───────────────────────────────────────────────

    def test_valid_page_and_page_size(self):
        """Valid page and page_size must be returned as-is."""
        request = _make_request("page=3&page_size=12")
        result = get_pagination_params(request)
        assert result.page == 3
        assert result.page_size == 12
        assert result.is_valid is True

    def test_default_page_is_1_when_not_provided(self):
        """When page is not in query string, default must be 1."""
        request = _make_request("page_size=12")
        result = get_pagination_params(request)
        assert result.page == 1

    def test_default_page_size_is_20_when_not_provided(self):
        """When page_size is not in query string, default must be 20."""
        request = _make_request("page=1")
        result = get_pagination_params(request)
        assert result.page_size == 20

    def test_both_defaults_when_no_params(self):
        """No query params → page=1, page_size=20, is_valid=True."""
        request = _make_request()
        result = get_pagination_params(request)
        assert result.page == 1
        assert result.page_size == 20
        assert result.is_valid is True

    def test_custom_default_page_size(self):
        """default_page_size parameter must override the default of 20."""
        request = _make_request()
        result = get_pagination_params(request, default_page_size=12)
        assert result.page_size == 12

    # ── Page number boundaries ────────────────────────────────────────────────

    def test_page_zero_clamped_to_1(self):
        """
        page=0 must be clamped to 1.

        page 0 would produce negative offset in SQL — must be prevented.
        """
        request = _make_request("page=0")
        result = get_pagination_params(request)
        assert result.page == 1
        assert result.is_valid is True

    def test_negative_page_clamped_to_1(self):
        """Negative page must be clamped to 1."""
        request = _make_request("page=-5")
        result = get_pagination_params(request)
        assert result.page == 1

    def test_large_page_number_accepted(self):
        """
        Large page numbers must be accepted without error.

        Caller is responsible for checking if page exceeds total_pages.
        build_pagination_meta handles clamping.
        """
        request = _make_request("page=9999")
        result = get_pagination_params(request)
        assert result.page == 9999
        assert result.is_valid is True

    # ── page_size boundaries ──────────────────────────────────────────────────

    def test_page_size_zero_clamped_to_1(self):
        """
        page_size=0 must be clamped to 1.

        0 items per page makes no sense and would cause division by zero
        in total_pages calculation.
        """
        request = _make_request("page_size=0")
        result = get_pagination_params(request)
        assert result.page_size == 1

    def test_page_size_negative_clamped_to_1(self):
        """Negative page_size must be clamped to 1."""
        request = _make_request("page_size=-10")
        result = get_pagination_params(request)
        assert result.page_size == 1

    def test_page_size_above_max_clamped_to_max(self):
        """
        page_size above max_page_size must be clamped to max_page_size.

        Prevents clients from requesting 10,000 items per page
        and overloading the database and serializer.
        """
        request = _make_request("page_size=9999")
        result = get_pagination_params(request, max_page_size=48)
        assert result.page_size == 48

    def test_page_size_at_max_is_accepted(self):
        """page_size equal to max_page_size must be accepted as-is."""
        request = _make_request("page_size=48")
        result = get_pagination_params(request, max_page_size=48)
        assert result.page_size == 48

    def test_page_size_below_max_is_accepted(self):
        """page_size below max_page_size must be accepted as-is."""
        request = _make_request("page_size=12")
        result = get_pagination_params(request, max_page_size=48)
        assert result.page_size == 12

    def test_custom_max_page_size_respected(self):
        """custom max_page_size parameter must be respected."""
        request = _make_request("page_size=150")
        result = get_pagination_params(request, max_page_size=200)
        assert result.page_size == 150

    def test_max_page_size_zero_floored_to_1(self):
        """
        Caller passing max_page_size=0 must be floored to 1.

        Prevents caller error from producing page_size=0 silently.
        """
        request = _make_request("page_size=10")
        result = get_pagination_params(request, max_page_size=0)
        assert result.page_size >= 1

    # ── Invalid input — is_valid=False ────────────────────────────────────────

    def test_invalid_page_string_returns_is_valid_false(self):
        """Non-numeric page must return is_valid=False."""
        request = _make_request("page=abc")
        result = get_pagination_params(request)
        assert result.is_valid is False

    def test_invalid_page_string_defaults_page_to_1(self):
        """Non-numeric page must default to page=1."""
        request = _make_request("page=abc")
        result = get_pagination_params(request)
        assert result.page == 1

    def test_invalid_page_size_string_returns_is_valid_false(self):
        """Non-numeric page_size must return is_valid=False."""
        request = _make_request("page_size=xyz")
        result = get_pagination_params(request)
        assert result.is_valid is False

    def test_invalid_page_size_preserves_valid_page(self):
        """
        When page is valid but page_size is invalid, page must be preserved.

        Early versions reset page to 1 when page_size was invalid.
        This was a bug — valid page should never be discarded.
        """
        request = _make_request("page=5&page_size=abc")
        result = get_pagination_params(request)
        assert result.page == 5
        assert result.is_valid is False

    def test_float_page_returns_is_valid_false(self):
        """Float page (e.g. 1.5) must be treated as invalid."""
        request = _make_request("page=1.5")
        result = get_pagination_params(request)
        assert result.is_valid is False

    def test_empty_page_uses_default(self):
        """
        Empty page param (page=) must use default, not crash.

        Query string "page=" passes empty string to int() → ValueError.
        Must return is_valid=False with page=1.
        """
        request = _make_request("page=")
        result = get_pagination_params(request)
        assert result.page == 1
        assert result.is_valid is False


# ─── Layer 2: build_pagination_meta() ────────────────────────────────────────

@pytest.mark.unit
class TestBuildPaginationMeta:
    """
    Unit tests for build_pagination_meta().

    This function builds the pagination dict that goes into response meta.
    Frontend reads these values to render pagination UI correctly.
    """

    # ── Required fields ───────────────────────────────────────────────────────

    def test_returns_dict(self):
        """Return type must be a dict."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert isinstance(result, dict)

    def test_contains_all_required_keys(self):
        """Result must contain all eight required pagination keys."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        required_keys = [
            "page", "page_size", "total", "total_pages",
            "showing_from", "showing_to", "has_next", "has_previous",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: '{key}'"

    # ── total_pages calculation ────────────────────────────────────────────────

    def test_total_pages_correct_for_exact_division(self):
        """120 items / 12 per page = exactly 10 pages."""
        result = build_pagination_meta(page=1, page_size=12, total=120)
        assert result["total_pages"] == 10

    def test_total_pages_rounds_up(self):
        """
        121 items / 12 per page = 11 pages (not 10.08).

        Ceiling division — partial last page counts as a full page.
        """
        result = build_pagination_meta(page=1, page_size=12, total=121)
        assert result["total_pages"] == 11

    def test_total_pages_one_item(self):
        """1 item must produce 1 page."""
        result = build_pagination_meta(page=1, page_size=12, total=1)
        assert result["total_pages"] == 1

    def test_total_pages_zero_items(self):
        """0 items must produce 0 pages."""
        result = build_pagination_meta(page=1, page_size=12, total=0)
        assert result["total_pages"] == 0

    def test_total_pages_exact_page_size(self):
        """Exactly page_size items must produce exactly 1 page."""
        result = build_pagination_meta(page=1, page_size=12, total=12)
        assert result["total_pages"] == 1

    # ── showing_from / showing_to ─────────────────────────────────────────────

    def test_showing_from_first_page(self):
        """Page 1 must show from item 1."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert result["showing_from"] == 1

    def test_showing_to_first_page(self):
        """Page 1 with 12 per page and 100 total must show to item 12."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert result["showing_to"] == 12

    def test_showing_from_second_page(self):
        """Page 2 with 12 per page must show from item 13."""
        result = build_pagination_meta(page=2, page_size=12, total=100)
        assert result["showing_from"] == 13

    def test_showing_to_second_page(self):
        """Page 2 with 12 per page must show to item 24."""
        result = build_pagination_meta(page=2, page_size=12, total=100)
        assert result["showing_to"] == 24

    def test_showing_to_capped_at_total_on_last_page(self):
        """
        Last page with fewer items must show_to = total, not page_size.

        100 items, 12 per page, page 9 → items 97-100 (not 97-108).
        Frontend shows "Showing 97–100 of 100" not "Showing 97–108 of 100".
        """
        result = build_pagination_meta(page=9, page_size=12, total=100)
        assert result["showing_to"] == 100

    def test_showing_from_zero_when_total_is_zero(self):
        """
        showing_from must be 0 when total is 0.

        "Showing 0–0 of 0" not "Showing 1–0 of 0".
        """
        result = build_pagination_meta(page=1, page_size=12, total=0)
        assert result["showing_from"] == 0
        assert result["showing_to"] == 0

    # ── has_next / has_previous ───────────────────────────────────────────────

    def test_has_next_true_when_more_pages(self):
        """has_next must be True when current page < total_pages."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert result["has_next"] is True

    def test_has_next_false_on_last_page(self):
        """has_next must be False on the last page."""
        result = build_pagination_meta(page=9, page_size=12, total=100)
        assert result["has_next"] is False

    def test_has_previous_false_on_first_page(self):
        """has_previous must be False on page 1."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert result["has_previous"] is False

    def test_has_previous_true_on_second_page(self):
        """has_previous must be True on page 2 and beyond."""
        result = build_pagination_meta(page=2, page_size=12, total=100)
        assert result["has_previous"] is True

    def test_has_next_false_when_total_is_zero(self):
        """No items → no next page."""
        result = build_pagination_meta(page=1, page_size=12, total=0)
        assert result["has_next"] is False

    def test_has_previous_false_when_total_is_zero(self):
        """No items → no previous page."""
        result = build_pagination_meta(page=1, page_size=12, total=0)
        assert result["has_previous"] is False

    def test_single_page_no_next_or_previous(self):
        """Single page result must have neither next nor previous."""
        result = build_pagination_meta(page=1, page_size=12, total=5)
        assert result["has_next"] is False
        assert result["has_previous"] is False

    # ── Page clamping ─────────────────────────────────────────────────────────

    def test_overshooting_page_clamped_to_last_page(self):
        """
        page=999 on 3-page result must be clamped to page 3.

        Without clamping:
            showing_from = (999-1)*12 + 1 = 11977 (nonsense for 30 items)
        With clamping:
            showing_from = (3-1)*12 + 1 = 25 (correct last page)
        """
        result = build_pagination_meta(page=999, page_size=12, total=30)
        assert result["page"] == 3
        assert result["showing_from"] == 25
        assert result["showing_to"] == 30

    def test_page_zero_clamped_to_1_in_meta(self):
        """Page 0 in meta must be clamped to 1."""
        result = build_pagination_meta(page=0, page_size=12, total=100)
        assert result["page"] == 1

    def test_clamp_page_false_does_not_clamp(self):
        """
        clamp_page=False must disable clamping.

        Allows callers to get raw unclamped values when they handle
        page validation themselves.
        """
        result = build_pagination_meta(
            page=999, page_size=12, total=30, clamp_page=False
        )
        assert result["page"] == 999

    # ── Optional fields ───────────────────────────────────────────────────────

    def test_source_included_when_provided(self):
        """source field must be present when passed."""
        result = build_pagination_meta(
            page=1, page_size=12, total=100, source="l1_memory"
        )
        assert result["source"] == "l1_memory"

    def test_source_excluded_when_not_provided(self):
        """source field must NOT be in result when not passed."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert "source" not in result

    def test_sort_included_when_provided(self):
        """sort field must be present when passed."""
        result = build_pagination_meta(
            page=1, page_size=12, total=100, sort="price_asc"
        )
        assert result["sort"] == "price_asc"

    def test_sort_excluded_when_not_provided(self):
        """sort field must NOT be in result when not passed."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert "sort" not in result

    def test_elapsed_ms_included_when_provided(self):
        """elapsed_ms field must be present when passed."""
        result = build_pagination_meta(
            page=1, page_size=12, total=100, elapsed_ms=42.5
        )
        assert result["elapsed_ms"] == 42.5

    def test_elapsed_ms_excluded_when_not_provided(self):
        """elapsed_ms field must NOT be in result when not passed."""
        result = build_pagination_meta(page=1, page_size=12, total=100)
        assert "elapsed_ms" not in result

    def test_all_optional_fields_included_together(self):
        """All three optional fields must coexist in the result."""
        result = build_pagination_meta(
            page=1, page_size=12, total=100,
            source="database",
            sort="newest",
            elapsed_ms=123.45,
        )
        assert result["source"]     == "database"
        assert result["sort"]       == "newest"
        assert result["elapsed_ms"] == 123.45

    # ── Correctness across multiple pages ─────────────────────────────────────

    @pytest.mark.parametrize("page,expected_from,expected_to", [
        (1,  1,   12),
        (2,  13,  24),
        (3,  25,  36),
        (8,  85,  96),
        (9,  97, 100),  # last page — capped at total
    ])
    def test_showing_from_to_across_pages(
        self, page, expected_from, expected_to
    ):
        """
        showing_from and showing_to must be correct on every page.

        100 items, 12 per page:
            Page 1: 1-12
            Page 2: 13-24
            ...
            Page 9: 97-100 (last page, partial)
        """
        result = build_pagination_meta(page=page, page_size=12, total=100)
        assert result["showing_from"] == expected_from, (
            f"Page {page}: showing_from {result['showing_from']} != {expected_from}"
        )
        assert result["showing_to"] == expected_to, (
            f"Page {page}: showing_to {result['showing_to']} != {expected_to}"
        )