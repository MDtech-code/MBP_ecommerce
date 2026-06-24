# apps/accounts/api/auth_views.py

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from apps.core.api.mixins import APIResponseMixin


class CustomTokenObtainPairView(TokenObtainPairView, APIResponseMixin):

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code != 200:
            return self.build_response(
                message="Login failed",
                errors=response.data,
                status_code=response.status_code,
            )

        refresh = response.data.pop("refresh")
        access = response.data.get("access")

        new_response = self.build_response(
            data={"access": access},
            message="Login successful",
            status_code=status.HTTP_200_OK,
        )

        new_response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            secure=True,
            samesite="Lax",
            path="/api/token/refresh/",
        )

        return new_response