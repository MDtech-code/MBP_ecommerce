from django.conf import settings
from django.middleware.csrf import get_token
def set_csrf_cookie(request, response) -> None:
    
    csrf_token = get_token(request)
    print(csrf_token)
    response.set_cookie(
        "csrftoken",
        csrf_token,
        httponly=False,         # must be accessible to JS
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def clear_csrf_cookie(response) -> None:
    """
    Delete the CSRF cookie from the response.

    Scoped to root path — CSRF cookie is never path-scoped.

    Args:
        response: DRF Response object.
    """
    response.delete_cookie(
        "csrftoken",
        path="/",
    )