from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    TypeShiftViewSet, EquipeViewSet, RotationEquipeViewSet,
    PlanningMensuelViewSet, LignePlanningViewSet, MembreEquipeViewSet,
)

router = DefaultRouter()
router.register('shifts', TypeShiftViewSet, basename='shifts')
router.register('rotations', RotationEquipeViewSet, basename='rotations')
router.register('equipes', EquipeViewSet, basename='equipes')
router.register('membres', MembreEquipeViewSet, basename='membres-equipe')
router.register('plannings', PlanningMensuelViewSet, basename='plannings')
router.register('lignes', LignePlanningViewSet, basename='lignes-planning')
urlpatterns = [path('', include(router.urls))]
