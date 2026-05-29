from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import EvenementCarriere, RegleEvolutionCarriere
from .serializers import EvenementCarriereSerializer, RegleEvolutionCarriereSerializer
from users.permissions import RBACPermission


class EvenementCarriereViewSet(viewsets.ModelViewSet):
    queryset = EvenementCarriere.objects.select_related('employe').all()
    serializer_class = EvenementCarriereSerializer
    rbac_module = 'carrieres'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employe', 'type_evenement']
    search_fields = ['employe__nom', 'employe__prenom', 'description']

    @action(detail=False, methods=['get'], url_path='historique_postes')
    def historique_postes(self, request):
        """Retourne l'historique de carrière groupé par employé avec ancienneté."""
        from employes.models import Employe
        from employes.serializers import EmployeListSerializer
        from django.db.models import Q

        aujourd_hui = timezone.now().date()
        employes_qs = Employe.objects.filter(statut='actif').select_related('poste', 'site', 'departement').order_by('nom')

        search = request.query_params.get('search', '')
        if search:
            employes_qs = employes_qs.filter(
                Q(nom__icontains=search) | Q(prenom__icontains=search) | Q(matricule__icontains=search)
            )

        resultats = []
        for emp in employes_qs:
            anciennete_jours = (aujourd_hui - emp.date_embauche).days
            anciennete_annees = anciennete_jours // 365
            anciennete_mois = (anciennete_jours % 365) // 30

            evenements = EvenementCarriere.objects.filter(employe=emp).order_by('date_evenement').select_related('poste_avant', 'poste_apres')

            # Get last contract info
            dernier_contrat = evenements.filter(type_contrat__isnull=False).order_by('-date_evenement').first()

            resultats.append({
                'employe': EmployeListSerializer(emp).data,
                'anciennete_annees': anciennete_annees,
                'anciennete_mois': anciennete_mois,
                'type_contrat_actuel': dernier_contrat.type_contrat if dernier_contrat else None,
                'duree_contrat_mois': dernier_contrat.duree_contrat_mois if dernier_contrat else None,
                'date_fin_contrat': _calc_fin_contrat(dernier_contrat) if dernier_contrat else None,
                'nb_evenements': evenements.count(),
                'evenements': EvenementCarriereSerializer(evenements, many=True).data,
            })

        return Response(resultats)


def _calc_fin_contrat(ev):
    if not ev or not ev.type_contrat or ev.type_contrat == 'CDI' or not ev.duree_contrat_mois:
        return None
    from dateutil.relativedelta import relativedelta
    try:
        fin = ev.date_effet + relativedelta(months=ev.duree_contrat_mois)
        return fin.isoformat()
    except Exception:
        return None


class RegleEvolutionCarriereViewSet(viewsets.ModelViewSet):
    queryset = RegleEvolutionCarriere.objects.select_related('poste_actuel', 'poste_cible').all()
    serializer_class = RegleEvolutionCarriereSerializer
    rbac_module = 'carrieres'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['entreprise', 'est_actif']

    @action(detail=False, methods=['get'], url_path='eligibles')
    def eligibles(self, request):
        """Retourne les employés éligibles à une évolution selon les règles actives."""
        from employes.models import Employe
        from employes.serializers import EmployeListSerializer

        regles = self.get_queryset().filter(est_actif=True)
        aujourd_hui = timezone.now().date()
        resultats = []

        for regle in regles:
            employes_qs = Employe.objects.filter(
                poste=regle.poste_actuel, statut='actif'
            ).select_related('departement', 'poste', 'site')
            for emp in employes_qs:
                anciennete = (aujourd_hui - emp.date_embauche).days // 365
                if anciennete >= regle.anciennete_min_annees:
                    resultats.append({
                        'employe': EmployeListSerializer(emp).data,
                        'regle': RegleEvolutionCarriereSerializer(regle).data,
                        'anciennete_annees': anciennete,
                    })

        return Response(resultats)
