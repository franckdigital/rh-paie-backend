from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import EntrepriseViewSet

router = DefaultRouter()
router.register('', EntrepriseViewSet, basename='entreprises')
urlpatterns = [path('', include(router.urls))]
