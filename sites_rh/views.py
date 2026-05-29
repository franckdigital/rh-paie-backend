from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Site, Unite
from .serializers import SiteSerializer, SiteListSerializer, UniteSerializer


class SiteViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['entreprise', 'type_site', 'est_actif']
    search_fields = ['nom', 'code', 'ville']

    def get_queryset(self):
        return Site.objects.select_related('entreprise').filter(est_actif=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return SiteListSerializer
        return SiteSerializer


class UniteViewSet(viewsets.ModelViewSet):
    queryset = Unite.objects.select_related('site').filter(est_actif=True)
    serializer_class = UniteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['site', 'type_unite']
