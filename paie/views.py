from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from django.utils import timezone
from .models import BulletinPaie, ElementSalaire, LigneBulletin, JournalPaie
from .serializers import BulletinPaieSerializer, ElementSalaireSerializer, JournalPaieSerializer
from users.permissions import RBACPermission
from config.csv_utils import csv_response


class ElementSalaireViewSet(viewsets.ModelViewSet):
    queryset = ElementSalaire.objects.all()
    serializer_class = ElementSalaireSerializer
    rbac_module = 'paie'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['type', 'categorie', 'est_actif', 'entreprise']


class BulletinPaieViewSet(viewsets.ModelViewSet):
    queryset = BulletinPaie.objects.select_related(
        'employe', 'employe__poste', 'employe__departement'
    ).prefetch_related('lignes__element').all()
    serializer_class = BulletinPaieSerializer
    rbac_module = 'paie'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employe', 'statut', 'employe__site', 'employe__departement']
    ordering_fields = ['periode_fin', 'created_at', 'salaire_net']

    @action(detail=True, methods=['post'])
    def calculer(self, request, pk=None):
        """Recalcule automatiquement le bulletin (sync presences puis calcul complet)."""
        bulletin = self.get_object()
        bulletin.sync_depuis_presences()
        bulletin.calculer_salaire_complet()
        return Response(BulletinPaieSerializer(bulletin).data)

    @action(detail=True, methods=['post'], url_path='sync-presences')
    def sync_presences(self, request, pk=None):
        """Synchronise les absences et retards depuis les Présences réelles, puis recalcule."""
        bulletin = self.get_object()
        bulletin.sync_depuis_presences()
        bulletin.calculer_salaire_complet()
        return Response(BulletinPaieSerializer(bulletin).data)

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        bulletin = self.get_object()
        bulletin.statut = 'valide'
        bulletin.genere_par = request.user
        bulletin.save()
        return Response({'status': 'validé'})

    @action(detail=True, methods=['post'])
    def marquer_paye(self, request, pk=None):
        from django.utils import timezone
        bulletin = self.get_object()
        bulletin.statut = 'paye'
        bulletin.date_paiement = request.data.get('date_paiement', timezone.now().date())
        bulletin.mode_paiement = request.data.get('mode_paiement', 'virement')
        bulletin.save()
        return Response({'status': 'payé'})

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                b.employe.matricule,
                b.employe.nom_complet,
                b.periode_fin.strftime('%m/%Y'),
                b.salaire_base,
                b.salaire_brut,
                b.cotisation_cnps_employe,
                b.cotisation_cnps_patronale,
                b.its,
                b.cmu,
                b.total_retenues,
                b.salaire_net,
                b.statut,
                b.date_paiement.strftime('%d/%m/%Y') if b.date_paiement else '',
            ]
            for b in qs.select_related('employe')
        ]
        return csv_response(
            f"bulletins_paie_{timezone.now().strftime('%Y%m%d')}.csv",
            ['Matricule', 'Nom complet', 'Période', 'Salaire base', 'Salaire brut',
             'CNPS salarié', 'CNPS patronal', 'ITS', 'CMU', 'Total retenues',
             'Net à payer', 'Statut', 'Date paiement'],
            rows,
        )

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        from config.reports_pdf import pdf_table_response
        qs = self.filter_queryset(self.get_queryset())
        fmt = lambda v: f"{int(float(v or 0)):,}".replace(',', ' ')
        rows = [
            [
                b.employe.matricule,
                b.employe.nom_complet,
                b.periode_fin.strftime('%m/%Y'),
                fmt(b.salaire_brut),
                fmt(b.cotisation_cnps_employe),
                fmt(b.its),
                fmt(b.cmu),
                fmt(b.total_retenues),
                fmt(b.salaire_net),
                b.statut,
            ]
            for b in qs.select_related('employe')
        ]
        mois = request.query_params.get('mois')
        annee = request.query_params.get('annee')
        periode = f"{mois}/{annee}" if mois and annee else timezone.now().strftime('%m/%Y')
        return pdf_table_response(
            f"bulletins_paie_{timezone.now().strftime('%Y%m%d')}.pdf",
            'Rapport masse salariale',
            f"Période : {periode} — {len(rows)} bulletin(s)",
            ['Matricule', 'Nom', 'Période', 'Brut', 'CNPS sal.', 'ITS', 'CMU', 'Retenues', 'Net', 'Statut'],
            rows,
            use_landscape=True,
        )

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """Génère et retourne le bulletin de paie en PDF."""
        try:
            from .pdf import generer_bulletin_pdf
        except ImportError:
            return Response(
                {'detail': 'reportlab non installé (pip install reportlab).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        bulletin = self.get_object()
        buf = generer_bulletin_pdf(bulletin)
        filename = f"bulletin_{bulletin.employe.matricule or bulletin.employe.id}_{bulletin.periode_fin.strftime('%Y-%m')}.pdf"
        return FileResponse(buf, as_attachment=True, filename=filename, content_type='application/pdf')

    @action(detail=False, methods=['get'], url_path='mes-bulletins')
    def mes_bulletins(self, request):
        """Bulletins de paie de l'employé connecté (usage mobile)."""
        employe = None
        try:
            employe = request.user.employe
        except Exception:
            pass
        if not employe and request.user.email:
            from employes.models import Employe
            employe = Employe.objects.filter(email=request.user.email).first()
        if not employe:
            return Response([])
        qs = self.get_queryset().filter(employe=employe).order_by('-periode_fin')
        return Response(BulletinPaieSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'])
    def generer_masse(self, request):
        """Génère les bulletins pour tous les employés actifs d'un site/département."""
        from employes.models import Employe
        from heures.models import RecapHeures
        import datetime

        mois = request.data.get('mois')
        annee = request.data.get('annee')
        site_id = request.data.get('site')
        entreprise_id = request.data.get('entreprise')

        if not (mois and annee):
            return Response({'error': 'mois et annee requis'}, status=status.HTTP_400_BAD_REQUEST)

        employes = Employe.objects.filter(statut='actif')
        if site_id:
            employes = employes.filter(site_id=site_id)
        if entreprise_id:
            employes = employes.filter(entreprise_id=entreprise_id)

        date_debut = datetime.date(int(annee), int(mois), 1)
        import calendar
        last_day = calendar.monthrange(int(annee), int(mois))[1]
        date_fin = datetime.date(int(annee), int(mois), last_day)

        crees = []
        for emp in employes:
            bulletin, created = BulletinPaie.objects.get_or_create(
                employe=emp, periode_debut=date_debut, periode_fin=date_fin,
                defaults={
                    'salaire_base': emp.salaire_base,
                    'statut': 'brouillon',
                    'genere_par': request.user,
                }
            )
            if created:
                # Récupérer les récaps d'heures si disponibles
                try:
                    recap = RecapHeures.objects.get(employe=emp, annee=annee, mois=mois)
                    bulletin.heures_normales = recap.heures_normales
                    bulletin.heures_nuit = recap.heures_nuit
                    bulletin.heures_supp_25 = recap.heures_supp_25
                    bulletin.heures_supp_50 = recap.heures_supp_50
                    bulletin.jours_absents = recap.jours_absents
                    bulletin.retard_minutes_total = recap.retards_minutes_total
                    bulletin.recap_heures = recap
                    bulletin.save()
                except RecapHeures.DoesNotExist:
                    # Pas de récap heures → lire directement les présences
                    bulletin.sync_depuis_presences()
                # Auto-add transport / panier / prime poste from global ElementSalaire
                from django.db import models
                elements_auto = ElementSalaire.objects.filter(
                    est_actif=True,
                    montant_fixe__isnull=False,
                    categorie__in=['transport', 'panier', 'logement'],
                ).filter(models.Q(entreprise=emp.entreprise) | models.Q(entreprise__isnull=True))
                for elem in elements_auto:
                    LigneBulletin.objects.get_or_create(
                        bulletin=bulletin, element=elem,
                        defaults={'base': 0, 'taux': 0, 'quantite': 1, 'montant': elem.montant_fixe}
                    )
                bulletin.calculer_salaire_complet()
                crees.append(bulletin.id)

        return Response({'crees': len(crees), 'ids': crees})


class JournalPaieViewSet(viewsets.ModelViewSet):
    queryset = JournalPaie.objects.all()
    serializer_class = JournalPaieSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['entreprise', 'statut']
