
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static


from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt






urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('api/products/', include('apps.products.urls', namespace='products')),
    path('api/cart/', include('apps.cart.urls', namespace='cart')),
    path("api/orders/", include("apps.orders.urls", namespace="orders")), 
    path("api/logistics/", include("apps.logistics.urls", namespace="logistics")),
    path("api/reviews/",include('apps.products.urls',namespace='reviews')),
    path("api/returns/", include("apps.returns.urls", namespace="returns")),

     # Schema + Docs (global)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # graphQL
     path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    

]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]




