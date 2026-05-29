from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import DemandeConge, TypeConge, SoldeConge
from .serializers import DemandeCongeSerializer, TypeCongeSerializer, SoldeCongeSerializer
from users.permissions import RBACPermission
from config.csv_utils import csv_response


def _get_employe(request):
    """Retourne l'Employe lié au user connecté (via relation directe puis email)."""
    employe = None
    try:
        employe = request.user.employe
    except Exception:
        pass
    if not employe and request.user.email:
        from employes.models import Employe
        employe = Employe.objects.filter(email=request.user.email).first()
    return employe


class TypeCongeViewSet(viewsets.ModelViewSet):
    queryset = TypeConge.objects.all()
    serializer_class = TypeCongeSerializer
    rbac_module = 'conges'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]


class SoldeCongeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SoldeConge.objects.select_related('employe', 'type_conge').all()
    serializer_class = SoldeCongeSerializer
    rbac_module = 'conges'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['employe', 'annee']

    @action(detail=False, methods=['get'], url_path='mes-soldes')
    def mes_soldes(self, request):
        """Soldes de congé de l'employé connecté."""
        employe = _get_employe(request)
        if not employe:
            return Response([])
        annee = timezone.now().year
        qs = self.get_queryset().filter(employe=employe, annee=annee)
        return Response(SoldeCongeSerializer(qs, many=True).data)


class DemandeCongeViewSet(viewsets.ModelViewSet):
    queryset = DemandeConge.objects.select_related('employe', 'type_conge').all()
    serializer_class = DemandeCongeSerializer
    rbac_module = 'conges'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['employe', 'statut', 'type_conge']

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                d.employe.matricule,
                d.employe.nom_complet,
                d.type_conge.nom,
                d.date_debut.strftime('%d/%m/%Y'),
                d.date_fin.strftime('%d/%m/%Y'),
                d.nombre_jours,
                d.statut,
                d.motif,
                d.commentaire_approbation,
            ]
            for d in qs.select_related('employe', 'type_conge')
        ]
        return csv_response(
            f"conges_{timezone.now().strftime('%Y%m%d')}.csv",
            ['Matricule', 'Nom complet', 'Type congé', 'Début', 'Fin', 'Jours', 'Statut', 'Motif', 'Commentaire approbation'],
            rows,
        )

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        from config.reports_pdf import pdf_table_response
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                d.employe.matricule,
                d.employe.nom_complet,
                d.type_conge.nom,
                d.date_debut.strftime('%d/%m/%Y'),
                d.date_fin.strftime('%d/%m/%Y'),
                str(d.nombre_jours),
                d.statut,
            ]
            for d in qs.select_related('employe', 'type_conge')
        ]
        return pdf_table_response(
            f"conges_{timezone.now().strftime('%Y%m%d')}.pdf",
            'Rapport des congés',
            f"Généré le {timezone.now().strftime('%d/%m/%Y')} — {len(rows)} demande(s)",
            ['Matricule', 'Nom complet', 'Type', 'Début', 'Fin', 'Jours', 'Statut'],
            rows,
        )

    def perform_create(self, serializer):
        employe = serializer.validated_data.get('employe') or _get_employe(self.request)
        if not employe:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'employe': 'Profil employé introuvable pour cet utilisateur.'})
        # Calculer nombre_jours si absent
        nb_jours = serializer.validated_data.get('nombre_jours')
        if not nb_jours:
            from datetime import date as _date
            d1 = serializer.validated_data.get('date_debut')
            d2 = serializer.validated_data.get('date_fin')
            nb_jours = max(1, (d2 - d1).days + 1) if (d1 and d2) else 1
        demande = serializer.save(employe=employe, nombre_jours=nb_jours)
        from config.emails import notifier_demande_conge
        notifier_demande_conge(demande)

    @action(detail=False, methods=['get'], url_path='mes-demandes')
    def mes_demandes(self, request):
        """Demandes de congé de l'employé connecté."""
        employe = _get_employe(request)
        if not employe:
            return Response([])
        qs = self.get_queryset().filter(employe=employe).order_by('-created_at')
        return Response(DemandeCongeSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        demande = self.get_object()
        if demande.statut not in ('en_attente',):
            return Response({'detail': 'Seules les demandes en attente peuvent être annulées.'}, status=400)
        demande.statut = 'annule'
        demande.save(update_fields=['statut'])
        return Response({'status': 'annulé'})

    @action(detail=True, methods=['post'], url_path='approuver_chef')
    def approuver_chef(self, request, pk=None):
        """Validation niveau 1 : chef d'équipe."""
        demande = self.get_object()
        if demande.statut != 'en_attente':
            return Response({'detail': 'Seules les demandes en attente peuvent être validées par le chef.'}, status=400)
        demande.statut = 'valide_chef'
        demande.chef_approuve_par = request.user
        demande.chef_date_approbation = timezone.now()
        demande.chef_commentaire = request.data.get('commentaire', '')
        demande.save()
        return Response({'status': 'validé chef'})

    @action(detail=True, methods=['post'], url_path='refuser_chef')
    def refuser_chef(self, request, pk=None):
        """Refus niveau 1 par le chef."""
        demande = self.get_object()
        if demande.statut not in ('en_attente',):
            return Response({'detail': 'Seules les demandes en attente peuvent être refusées.'}, status=400)
        demande.statut = 'refuse'
        demande.chef_approuve_par = request.user
        demande.chef_date_approbation = timezone.now()
        demande.chef_commentaire = request.data.get('commentaire', '')
        demande.save()
        return Response({'status': 'refusé chef'})

    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        """Validation finale RH (niveau 2)."""
        demande = self.get_object()
        if demande.statut not in ('en_attente', 'valide_chef'):
            return Response({'detail': 'Statut incompatible pour approbation RH.'}, status=400)
        demande.statut = 'approuve'
        demande.approuve_par = request.user
        demande.date_approbation = timezone.now()
        demande.commentaire_approbation = request.data.get('commentaire', '')
        demande.save()
        # Déduire le solde de congé
        self._deduire_solde(demande)
        from config.emails import notifier_decision_conge
        notifier_decision_conge(demande)
        return Response({'status': 'approuvé'})

    def _deduire_solde(self, demande):
        annee = demande.date_debut.year
        solde, _ = SoldeConge.objects.get_or_create(
            employe=demande.employe,
            type_conge=demande.type_conge,
            annee=annee,
            defaults={
                'jours_acquis': demande.type_conge.nombre_jours,
                'jours_pris': 0,
                'jours_restants': demande.type_conge.nombre_jours,
            },
        )
        from decimal import Decimal
        jours = Decimal(str(demande.nombre_jours))
        solde.jours_pris = solde.jours_pris + jours
        solde.jours_restants = max(Decimal('0'), solde.jours_restants - jours)
        solde.save()

    @action(detail=True, methods=['post'])
    def refuser(self, request, pk=None):
        demande = self.get_object()
        demande.statut = 'refuse'
        demande.approuve_par = request.user
        demande.date_approbation = timezone.now()
        demande.commentaire_approbation = request.data.get('commentaire', '')
        demande.save()
        from config.emails import notifier_decision_conge
        notifier_decision_conge(demande)
        return Response({'status': 'refusé'})
