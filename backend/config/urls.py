
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from .tasks import test_task

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def trigger_test(request):
    task = test_task.delay("Hello from Django to Celery!")
    return JsonResponse({'task_id': task.id, 'status': 'queued'})



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/test-celery/', trigger_test),
    path('api/integration/',include("integration_test.urls")),

     # Schema + Docs (global)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    

]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]




