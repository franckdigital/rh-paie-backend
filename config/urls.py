from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Auth & Utilisateurs
    path('api/auth/', include('users.urls')),
    # Structure
    path('api/entreprises/', include('entreprises.urls')),
    path('api/sites/', include('sites_rh.urls')),
    # RH
    path('api/employes/', include('employes.urls')),
    path('api/carrieres/', include('carrieres.urls')),
    path('api/documents/', include('documents.urls')),
    # Planning & Pointage
    path('api/planning/', include('planning.urls')),
    path('api/pointage/', include('pointage.urls')),
    path('api/presences/', include('presences.urls')),
    path('api/heures/', include('heures.urls')),
    # Paie
    path('api/paie/', include('paie.urls')),
    # Congés
    path('api/conges/', include('conges.urls')),
    # Dashboards
    path('api/dashboard/', include('dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
