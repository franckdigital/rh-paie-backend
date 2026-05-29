from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import DemandeCongeViewSet, TypeCongeViewSet, SoldeCongeViewSet

router = DefaultRouter()
router.register('demandes', DemandeCongeViewSet, basename='demandes-conge')
router.register('types', TypeCongeViewSet, basename='types-conge')
router.register('soldes', SoldeCongeViewSet, basename='soldes-conge')

urlpatterns = [path('', include(router.urls))]
