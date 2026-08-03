# apps/core/api/views.py (or apps/accounts/views.py, wherever makes sense)

from apps.core.api.views import BaseAPIView
from rest_framework.permissions import AllowAny
from apps.core.utils.csrf_cookie import set_csrf_cookie

class CSRFTokenView(BaseAPIView):
    """
    GET /api/csrf/

    
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        print("ma get ma hu")
        response = self.success_response(message="CSRF cookie set.")
        set_csrf_cookie(request, response)
        return response