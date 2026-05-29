from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import PointageViewSet, AnomaliePointageViewSet

router = DefaultRouter()
router.register('anomalies', AnomaliePointageViewSet, basename='anomalies')
router.register('', PointageViewSet, basename='pointages')
urlpatterns = [path('', include(router.urls))]
