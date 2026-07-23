# apps/contact/urls.py
from __future__ import annotations

from django.urls import path

from apps.contact.views import ContactSubmitAPIView

app_name = "contact"

urlpatterns = [
    path(
        "",
        ContactSubmitAPIView.as_view(),
        name="contact-submit",
    ),
]