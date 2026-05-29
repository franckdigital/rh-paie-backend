from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from .models import Presence, JourFerie, RapportPresence
from .serializers import PresenceSerializer, JourFerieSerializer, RapportPresenceSerializer
from users.permissions import RBACPermission
from config.csv_utils import csv_response


class PresenceViewSet(viewsets.ModelViewSet):
    queryset = Presence.objects.select_related('employe', 'site', 'shift').all()
    serializer_class = PresenceSerializer
    rbac_module = 'presences'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employe', 'site', 'date', 'statut']

    @action(detail=False, methods=['get'])
    def aujourd_hui(self, request):
        date_param = request.query_params.get('date')
        if date_param:
            from datetime import date as _date
            try:
                jour = _date.fromisoformat(date_param)
            except ValueError:
                jour = timezone.now().date()
        else:
            jour = timezone.now().date()
        site_id = request.query_params.get('site')
        qs = Presence.objects.filter(date=jour)
        if site_id:
            qs = qs.filter(site_id=site_id)
        stats = qs.aggregate(
            presents=Count('id', filter=Q(statut__in=['present', 'retard'])),
            retards=Count('id', filter=Q(statut='retard')),
            absents=Count('id', filter=Q(statut__in=['absent_justifie', 'absent_non_justifie'])),
            conges=Count('id', filter=Q(statut='conge')),
        )
        serialized = PresenceSerializer(qs.select_related('employe'), many=True).data
        return Response(serialized)

    @action(detail=True, methods=['post'], url_path='changer_statut')
    def changer_statut(self, request, pk=None):
        """Change manuellement le statut d'une présence."""
        presence = self.get_object()
        nouveau_statut = request.data.get('statut')
        motif = request.data.get('motif', '')
        if not nouveau_statut:
            return Response({'detail': 'statut requis'}, status=400)
        presence.statut = nouveau_statut
        if motif:
            presence.justification = motif
            presence.justifie_par = request.user
        presence.calcul_automatique = False
        presence.save()
        return Response(PresenceSerializer(presence).data)

    @action(detail=False, methods=['get'], url_path='indicateurs')
    def indicateurs(self, request):
        """Indicateurs de présence pour une période."""
        from django.db.models import Count, Avg, Sum, Q
        annee = int(request.query_params.get('annee', timezone.now().year))
        mois = int(request.query_params.get('mois', timezone.now().month))
        site_id = request.query_params.get('site')

        qs = Presence.objects.filter(date__year=annee, date__month=mois)
        if site_id:
            qs = qs.filter(site_id=site_id)

        total = qs.count()
        agg = qs.aggregate(
            nb_present=Count('id', filter=Q(statut='present')),
            nb_retard=Count('id', filter=Q(statut='retard')),
            nb_abs_j=Count('id', filter=Q(statut='absent_justifie')),
            nb_abs_nj=Count('id', filter=Q(statut='absent_non_justifie')),
            nb_conge=Count('id', filter=Q(statut='conge')),
            nb_maladie=Count('id', filter=Q(statut='maladie')),
            nb_mission=Count('id', filter=Q(statut='mission')),
            nb_permission=Count('id', filter=Q(statut='permission')),
            nb_suspension=Count('id', filter=Q(statut='suspension')),
            total_h=Sum('heures_travaillees'),
            total_h_nuit=Sum('heures_nuit'),
            total_h_supp=Sum('heures_supp'),
            total_retard_min=Sum('retard_minutes'),
        )

        presents = (agg['nb_present'] or 0) + (agg['nb_retard'] or 0)
        absents = (agg['nb_abs_j'] or 0) + (agg['nb_abs_nj'] or 0)
        taux_presence = round(presents / total * 100, 1) if total else 0
        taux_absenteisme = round(absents / total * 100, 1) if total else 0

        # Taux par semaine du mois
        from datetime import date as _date
        import calendar
        jours_mois = calendar.monthrange(annee, mois)[1]
        par_semaine = []
        sem_courante = None
        sem_data = None
        for jour in range(1, jours_mois + 1):
            d = _date(annee, mois, jour)
            sem = d.isocalendar()[1]
            if sem != sem_courante:
                if sem_data:
                    par_semaine.append(sem_data)
                sem_courante = sem
                sem_data = {'semaine': sem, 'presents': 0, 'absents': 0, 'retards': 0}
            day_qs = qs.filter(date=d)
            sem_data['presents'] += day_qs.filter(statut__in=['present', 'retard']).count()
            sem_data['absents'] += day_qs.filter(statut__in=['absent_justifie', 'absent_non_justifie']).count()
            sem_data['retards'] += day_qs.filter(statut='retard').count()
        if sem_data:
            par_semaine.append(sem_data)

        # Top 5 absents
        from employes.models import Employe
        from employes.serializers import EmployeListSerializer
        top_absents = (
            qs.filter(statut__in=['absent_non_justifie', 'absent_justifie'])
            .values('employe')
            .annotate(nb=Count('id'))
            .order_by('-nb')[:5]
        )
        top_absents_detail = []
        for ta in top_absents:
            try:
                emp = Employe.objects.get(id=ta['employe'])
                top_absents_detail.append({
                    'employe': EmployeListSerializer(emp).data,
                    'nb_absences': ta['nb'],
                })
            except Employe.DoesNotExist:
                pass

        return Response({
            'total_lignes': total,
            'presents': presents,
            'retards': agg['nb_retard'] or 0,
            'absents_justifies': agg['nb_abs_j'] or 0,
            'absents_non_justifies': agg['nb_abs_nj'] or 0,
            'en_conge': agg['nb_conge'] or 0,
            'malades': agg['nb_maladie'] or 0,
            'en_mission': agg['nb_mission'] or 0,
            'en_permission': agg['nb_permission'] or 0,
            'en_suspension': agg['nb_suspension'] or 0,
            'taux_presence': taux_presence,
            'taux_absenteisme': taux_absenteisme,
            'heures_total': float(agg['total_h'] or 0),
            'heures_nuit_total': float(agg['total_h_nuit'] or 0),
            'heures_supp_total': float(agg['total_h_supp'] or 0),
            'retard_minutes_total': agg['total_retard_min'] or 0,
            'par_semaine': par_semaine,
            'top_absents': top_absents_detail,
        })

    @action(detail=True, methods=['post'])
    def justifier(self, request, pk=None):
        presence = self.get_object()
        motif = request.data.get('motif', '').strip()
        if not motif:
            return Response({'detail': 'Le motif est requis.'}, status=400)
        presence.statut = 'absent_justifie'
        presence.justification = motif
        presence.justifie_par = request.user
        presence.save(update_fields=['statut', 'justification', 'justifie_par'])
        return Response(PresenceSerializer(presence).data)

    @action(detail=True, methods=['post'])
    def corriger(self, request, pk=None):
        """Correction manuelle des heures d'arrivée / départ."""
        from django.utils.dateparse import parse_time
        presence = self.get_object()
        fields = []
        for field in ('heure_arrivee', 'heure_depart'):
            val = request.data.get(field)
            if val is not None:
                t = parse_time(val)
                if not t:
                    return Response({'detail': f'Format invalide pour {field} (HH:MM attendu).'}, status=400)
                setattr(presence, field, t)
                fields.append(field)
        if not fields:
            return Response({'detail': 'Aucun champ à corriger.'}, status=400)
        presence.calcul_automatique = False
        presence.calculer_heures()
        presence.save(update_fields=fields + ['heures_travaillees', 'heures_nuit', 'calcul_automatique'])
        return Response(PresenceSerializer(presence).data)

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                p.employe.matricule,
                p.employe.nom_complet,
                p.date.strftime('%d/%m/%Y'),
                p.statut,
                p.heure_arrivee.strftime('%H:%M') if p.heure_arrivee else '',
                p.heure_depart.strftime('%H:%M') if p.heure_depart else '',
                p.heures_travaillees,
                p.heures_supp,
                p.retard_minutes,
                p.site.nom if p.site else '',
            ]
            for p in qs.select_related('employe', 'site')
        ]
        return csv_response(
            f"presences_{timezone.now().strftime('%Y%m%d')}.csv",
            ['Matricule', 'Nom complet', 'Date', 'Statut', 'Arrivée', 'Départ',
             'Heures travaillées', 'Heures supp.', 'Retard (min)', 'Site'],
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
                p.employe.matricule,
                p.employe.nom_complet,
                p.date.strftime('%d/%m/%Y'),
                p.statut,
                p.heure_arrivee.strftime('%H:%M') if p.heure_arrivee else '—',
                p.heure_depart.strftime('%H:%M') if p.heure_depart else '—',
                f"{p.heures_travaillees}h",
                p.site.nom if p.site else '—',
            ]
            for p in qs.select_related('employe', 'site')
        ]
        return pdf_table_response(
            f"presences_{timezone.now().strftime('%Y%m%d')}.pdf",
            'Rapport des présences',
            f"Période : {periode} — {len(rows)} enregistrement(s)",
            ['Matricule', 'Nom complet', 'Date', 'Statut', 'Arrivée', 'Départ', 'H. travaillées', 'Site'],
            rows,
            use_landscape=True,
        )

    @action(detail=False, methods=['get'])
    def mensuel(self, request):
        annee = int(request.query_params.get('annee', timezone.now().year))
        mois = int(request.query_params.get('mois', timezone.now().month))
        employe_id = request.query_params.get('employe')
        qs = Presence.objects.filter(date__year=annee, date__month=mois)
        if employe_id:
            qs = qs.filter(employe_id=employe_id)
        return Response(PresenceSerializer(qs.select_related('employe'), many=True).data)


class JourFerieViewSet(viewsets.ModelViewSet):
    queryset = JourFerie.objects.all()
    serializer_class = JourFerieSerializer
    rbac_module = 'presences'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['pays']


class RapportPresenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RapportPresence.objects.select_related('site').all()
    serializer_class = RapportPresenceSerializer
    rbac_module = 'presences'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['site', 'periode']
