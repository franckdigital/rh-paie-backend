from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import EmployeViewSet, DepartementViewSet, PosteViewSet, FichePosteViewSet

router = DefaultRouter()
# Specific prefixes BEFORE the empty-prefix viewset to avoid catch-all collision
router.register('departements', DepartementViewSet, basename='departements')
router.register('postes', PosteViewSet, basename='postes')
router.register('fiches-poste', FichePosteViewSet, basename='fiches-poste')
router.register('', EmployeViewSet, basename='employes')

urlpatterns = [path('', include(router.urls))]
