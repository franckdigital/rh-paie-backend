from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import ParametreHeures, RecapHeures
from .serializers import ParametreHeuresSerializer, RecapHeuresSerializer
from users.permissions import RBACPermission
from config.csv_utils import csv_response


class ParametreHeuresViewSet(viewsets.ModelViewSet):
    queryset = ParametreHeures.objects.all()
    serializer_class = ParametreHeuresSerializer
    rbac_module = 'heures'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['entreprise']


class RecapHeuresViewSet(viewsets.ModelViewSet):
    queryset = RecapHeures.objects.select_related('employe').all()
    serializer_class = RecapHeuresSerializer
    rbac_module = 'heures'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employe', 'annee', 'mois', 'valide']

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        recap = self.get_object()
        recap.valide = True
        recap.valide_par = request.user
        recap.save()
        return Response({'status': 'validé'})

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                r.employe.matricule,
                r.employe.nom_complet,
                f"{r.mois:02d}/{r.annee}",
                r.heures_normales,
                r.heures_nuit,
                r.heures_supp_25,
                r.heures_supp_50,
                r.jours_travailles,
                r.jours_absents,
                r.jours_conge,
                'Oui' if r.valide else 'Non',
            ]
            for r in qs.select_related('employe')
        ]
        return csv_response(
            f"heures_{timezone.now().strftime('%Y%m%d')}.csv",
            ['Matricule', 'Nom complet', 'Période', 'H. normales', 'H. nuit',
             'H. supp 25%', 'H. supp 50%', 'Jours travaillés', 'Jours absents',
             'Jours congé', 'Validé'],
            rows,
        )

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        from config.reports_pdf import pdf_table_response
        qs = self.filter_queryset(self.get_queryset())
        mois = request.query_params.get('mois')
        annee = request.query_params.get('annee')
        periode = f"{mois}/{annee}" if mois and annee else timezone.now().strftime('%m/%Y')
        rows = [
            [
                r.employe.matricule,
                r.employe.nom_complet,
                f"{r.mois:02d}/{r.annee}",
                f"{r.heures_normales}h",
                f"{r.heures_nuit}h",
                f"{r.heures_supp_25}h",
                f"{r.heures_supp_50}h",
                str(r.jours_absents),
                'Oui' if r.valide else 'Non',
            ]
            for r in qs.select_related('employe')
        ]
        return pdf_table_response(
            f"heures_{timezone.now().strftime('%Y%m%d')}.pdf",
            'Rapport des heures supplémentaires',
            f"Période : {periode} — {len(rows)} employé(s)",
            ['Matricule', 'Nom complet', 'Période', 'H. norm.', 'H. nuit', 'H. supp 25%', 'H. supp 50%', 'J. abs.', 'Validé'],
            rows,
            use_landscape=True,
        )

    @action(detail=False, methods=['post'])
    def calculer_mensuel(self, request):
        """Calcule les récaps heures pour tous les employés d'un mois donné."""
        annee = request.data.get('annee')
        mois = request.data.get('mois')
        site_id = request.data.get('site')
        if not (annee and mois):
            return Response({'error': 'annee et mois requis'}, status=status.HTTP_400_BAD_REQUEST)

        from presences.models import Presence
        from employes.models import Employe
        from django.db.models import Sum, Count, Q

        employes = Employe.objects.filter(statut='actif')
        if site_id:
            employes = employes.filter(site_id=site_id)

        resultats = []
        from presences.models import JourFerie
        feries = set(JourFerie.objects.filter(
            date__year=annee, date__month=mois
        ).values_list('date', flat=True))

        for emp in employes:
            presences = Presence.objects.filter(
                employe=emp, date__year=annee, date__month=mois
            )
            agg = presences.aggregate(
                h_norm=Sum('heures_travaillees'),
                h_nuit=Sum('heures_nuit'),
                h_supp=Sum('heures_supp'),
                jours_t=Count('id', filter=Q(statut__in=['present', 'retard'])),
                jours_a=Count('id', filter=Q(statut__in=['absent_non_justifie'])),
                jours_c=Count('id', filter=Q(statut='conge')),
                retards_c=Count('id', filter=Q(statut='retard')),
                retards_min=Sum('retard_minutes'),
            )
            # Heures dimanche et jours fériés
            h_dim = presences.filter(date__week_day=1).aggregate(s=Sum('heures_travaillees'))['s'] or 0
            h_ferie = presences.filter(date__in=feries).aggregate(s=Sum('heures_travaillees'))['s'] or 0
            recap, created = RecapHeures.objects.update_or_create(
                employe=emp, annee=annee, mois=mois,
                defaults={
                    'heures_normales': agg['h_norm'] or 0,
                    'heures_nuit': agg['h_nuit'] or 0,
                    'heures_supp_25': agg['h_supp'] or 0,
                    'heures_dimanche': h_dim,
                    'heures_ferie': h_ferie,
                    'jours_travailles': agg['jours_t'] or 0,
                    'jours_absents': agg['jours_a'] or 0,
                    'jours_conge': agg['jours_c'] or 0,
                    'retards_count': agg['retards_c'] or 0,
                    'retards_minutes_total': agg['retards_min'] or 0,
                }
            )
            recap.calculer_montants(emp.salaire_base)
            recap.save()
            resultats.append(recap.id)

        return Response({'calcule': len(resultats), 'ids': resultats})
