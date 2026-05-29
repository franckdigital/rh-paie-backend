from rest_framework import viewsets, permissions, filters
from .models import Entreprise
from .serializers import EntrepriseSerializer


class EntrepriseViewSet(viewsets.ModelViewSet):
    queryset = Entreprise.objects.filter(est_actif=True)
    serializer_class = EntrepriseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'sigle', 'secteur']
