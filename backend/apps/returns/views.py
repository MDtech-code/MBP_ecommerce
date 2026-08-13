# apps/returns/views.py
from __future__ import annotations

"""
Return views — HTTP layer for the returns app.

Endpoints:
    POST /api/returns/         ReturnCreateAPIView
    GET  /api/returns/         ReturnListAPIView
    GET  /api/returns/<id>/    ReturnDetailAPIView

Design rules:
    - All views inherit from BaseAPIView — never raw APIView.
    - Views call service or selector, never query models directly.
    - Serializer validates input fields only — business logic in service.
    - DomainError raised in service propagates to custom_exception_handler.
    - Paginated list uses get_pagination_params() + build_pagination_meta().
    - Multipart form data supported on ReturnCreateAPIView via
      parser_classes — required for photo uploads.

Permission:
    All three endpoints require IsAuthenticated.
    ReturnCreateAPIView additionally requires IsVerified.
    Ownership is enforced in selectors (scoped by requested_by=user).

Dependency direction:
    models → selectors → services → serializers → views
"""

import logging

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.api.views import BaseAPIView
from apps.core.pagination import get_pagination_params, build_pagination_meta
from apps.core.permissions import IsVerified
from apps.returns.models import ReturnRequest
from apps.returns.selectors.return_selectors import (
    get_return_by_id,
    list_returns_for_user,
)
from apps.returns.serializers import (
    ReturnCreateSerializer,
    ReturnDetailSerializer,
    ReturnListSerializer,
)
from apps.returns.services.return_service import ReturnService

logger = logging.getLogger("apps.returns")


class ReturnCreateAPIView(BaseAPIView):
    """
    POST /api/returns/

    Customer submits a return request for a delivered order item.

    Accepts multipart/form-data to support photo uploads alongside
    the return fields. Also accepts JSON for requests without photos.

    Business validation (delivery status, window, uniqueness, photo
    requirement) is handled entirely in ReturnService — DomainErrors
    raised there propagate automatically to custom_exception_handler.
    """

    permission_classes = [IsAuthenticated, IsVerified]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request) -> Response:
        serializer = ReturnCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Return request submission failed.",
                errors=serializer.errors,
                status_code=400,
            )

        validated = serializer.validated_data
        photos    = validated.get("photos", [])

        return_request = ReturnService.create_return_request(
            user=request.user,
            order_item_id=validated["order_item_id"],
            reason=validated["reason"],
            reason_detail=validated.get("reason_detail", ""),
            resolution_requested=validated.get(
                "resolution_requested",
                ReturnRequest.Resolution.REFUND,
            ),
            photos=photos,
        )

        logger.info(
            "ReturnCreateAPIView.post: return request created | "
            "return_id=%s user=%s",
            return_request.pk,
            request.user.pk,
        )

        return self.created_response(
            data=ReturnDetailSerializer(
                return_request,
                context={"request": request},
            ).data,
            message="Return request submitted successfully. "
                    "Our team will review it within 1-2 business days.",
        )


class ReturnListAPIView(BaseAPIView):
    """
    GET /api/returns/

    Customer lists all their own return requests, paginated.

    Optionally filter by status via ?status=pending query param.
    Ownership is enforced in list_returns_for_user() selector —
    customers only see their own returns.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        params = get_pagination_params(request)
        if not params.is_valid:
            return self.error_response(
                message="Invalid pagination parameters.",
                status_code=400,
            )

        queryset = list_returns_for_user(request.user)

        # ── Optional status filter ─────────────────────────────────────────────
        status_filter = request.query_params.get("status")
        valid_statuses = {choice[0] for choice in ReturnRequest.Status.choices}
        if status_filter:
            if status_filter not in valid_statuses:
                return self.error_response(
                    message=(
                        f"Invalid status filter. "
                        f"Valid values: {', '.join(sorted(valid_statuses))}."
                    ),
                    status_code=400,
                )
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()

        offset = (params.page - 1) * params.page_size
        page_qs = queryset[offset : offset + params.page_size]

        serializer = ReturnListSerializer(
            page_qs,
            many=True,
            context={"request": request},
        )

        meta = build_pagination_meta(
            params.page,
            params.page_size,
            total,
        )

        logger.info(
            "ReturnListAPIView.get: listed | user=%s page=%s total=%s",
            request.user.pk,
            params.page,
            total,
        )

        return self.list_response(
            data=serializer.data,
            message="Return requests retrieved successfully.",
            meta=meta,
        )


class ReturnDetailAPIView(BaseAPIView):
    """
    GET /api/returns/<id>/

    Customer views a single return request with full detail and photos.

    Ownership enforced in get_return_by_id() selector — fetching
    another user's return raises DoesNotExist → 404, not 403.
    This prevents return request ID enumeration.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, return_id: int) -> Response:
        try:
            return_request = get_return_by_id(return_id, request.user)
        except ReturnRequest.DoesNotExist:
            return self.not_found_response(
                message="Return request not found.",
            )

        serializer = ReturnDetailSerializer(
            return_request,
            context={"request": request},
        )

        logger.info(
            "ReturnDetailAPIView.get: retrieved | "
            "return_id=%s user=%s",
            return_id,
            request.user.pk,
        )

        return self.success_response(
            data=serializer.data,
            message="Return request retrieved successfully.",
        )