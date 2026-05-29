from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Pointage, AnomaliePointage
from .serializers import PointageSerializer, PointageEntreeSerializer, AnomaliePointageSerializer
from users.permissions import RBACPermission


class PointageViewSet(viewsets.ModelViewSet):
    queryset = Pointage.objects.select_related('employe', 'site').all()
    rbac_module = 'pointage'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employe', 'site', 'date_pointage', 'type_pointage', 'statut', 'mode']

    def get_serializer_class(self):
        if self.action == 'create':
            return PointageEntreeSerializer
        return PointageSerializer

    def perform_create(self, serializer):
        from employes.models import Employe
        from rest_framework.exceptions import ValidationError as DRFValidationError
        now = timezone.now()

        # 1. Via OneToOneField (si compte créé avec creer-compte)
        employe = None
        try:
            employe = self.request.user.employe
        except Exception:
            pass

        # 2. Fallback par email (seed / admin Django)
        if not employe and self.request.user.email:
            employe = Employe.objects.filter(email=self.request.user.email).first()

        if not employe:
            raise DRFValidationError({'detail': 'Aucun profil employé associé à ce compte.'})

        # Lier le compte pour les prochains appels
        if not employe.user_id:
            employe.user = self.request.user
            employe.save(update_fields=['user'])

        site = self.request.user.site or employe.site
        serializer.save(
            employe=employe,
            datetime_pointage=now,
            date_pointage=now.date(),
            site=site,
        )

    @action(detail=False, methods=['get'])
    def aujourd_hui(self, request):
        """Tous les pointages du jour courant pour un site."""
        aujourd_hui = timezone.now().date()
        site_id = request.query_params.get('site')
        qs = Pointage.objects.filter(date_pointage=aujourd_hui)
        if site_id:
            qs = qs.filter(site_id=site_id)
        return Response(PointageSerializer(qs.select_related('employe', 'site'), many=True).data)

    @action(detail=False, methods=['get'])
    def temps_reel(self, request):
        """Présents en temps réel sur un site (ont pointé entrée aujourd'hui, pas encore sortie)."""
        aujourd_hui = timezone.now().date()
        site_id = request.query_params.get('site')
        entrees = Pointage.objects.filter(
            date_pointage=aujourd_hui, type_pointage='entree', statut='valide'
        )
        sorties_employes = Pointage.objects.filter(
            date_pointage=aujourd_hui, type_pointage='sortie'
        ).values_list('employe_id', flat=True)
        presents = entrees.exclude(employe_id__in=sorties_employes)
        if site_id:
            presents = presents.filter(site_id=site_id)
        return Response({
            'total_presents': presents.count(),
            'pointages': PointageSerializer(presents.select_related('employe'), many=True).data
        })

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        pointage = self.get_object()
        pointage.statut = 'valide'
        pointage.valide_par = request.user
        pointage.save()
        return Response({'status': 'validé'})

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        pointage = self.get_object()
        pointage.statut = 'rejete'
        pointage.anomalie_description = request.data.get('raison', '')
        pointage.save()
        return Response({'status': 'rejeté'})

    @action(detail=False, methods=['post'], url_path='enregistrer-device')
    def enregistrer_device(self, request):
        """Enregistre l'appareil mobile de l'employé connecté."""
        from employes.models import Employe
        try:
            employe = Employe.objects.get(email=request.user.email)
        except Employe.DoesNotExist:
            return Response({'detail': 'Profil employé introuvable'}, status=status.HTTP_404_NOT_FOUND)
        device_id = request.data.get('device_id', '').strip()
        if not device_id:
            return Response({'detail': 'device_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        employe.device_id = device_id
        employe.save(update_fields=['device_id'])
        return Response({'status': 'device enregistré', 'device_id': device_id, 'employe_id': employe.id})

    @action(detail=False, methods=['get'], url_path='mon-statut')
    def mon_statut(self, request):
        """Statut de pointage du jour pour l'agent connecté."""
        from employes.models import Employe
        try:
            employe = Employe.objects.get(email=request.user.email)
        except Employe.DoesNotExist:
            return Response({'detail': 'Profil employé introuvable'}, status=status.HTTP_404_NOT_FOUND)
        aujourd_hui = timezone.now().date()
        pointages = Pointage.objects.filter(employe=employe, date_pointage=aujourd_hui).order_by('datetime_pointage')
        entree = pointages.filter(type_pointage='entree').first()
        sortie = pointages.filter(type_pointage='sortie').last()
        anomalies = AnomaliePointage.objects.filter(employe=employe, date=aujourd_hui)
        return Response({
            'employe_id': employe.id,
            'employe_nom': employe.nom_complet,
            'device_enregistre': bool(employe.device_id),
            'device_id': employe.device_id,
            'date': aujourd_hui.isoformat(),
            'entree': PointageSerializer(entree).data if entree else None,
            'sortie': PointageSerializer(sortie).data if sortie else None,
            'total_pointages': pointages.count(),
            'statut': 'sortie' if sortie else ('present' if entree else 'absent'),
            'anomalies': AnomaliePointageSerializer(anomalies, many=True).data,
        })

    @action(detail=True, methods=['post'], url_path='corriger-horaire')
    def corriger_horaire(self, request, pk=None):
        """Permet à un admin de corriger l'heure d'un pointage."""
        from django.utils.dateparse import parse_datetime
        if not request.user.has_permission('pointage.edit'):
            return Response({'detail': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

        pointage = self.get_object()
        nouvelle_heure = request.data.get('datetime_pointage')
        note = request.data.get('note_correction', '')

        if not nouvelle_heure:
            return Response({'detail': 'datetime_pointage requis.'}, status=status.HTTP_400_BAD_REQUEST)

        dt = parse_datetime(nouvelle_heure)
        if not dt:
            return Response({'detail': 'Format datetime invalide (ISO 8601 attendu).'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone as tz
        if tz.is_naive(dt):
            dt = tz.make_aware(dt)

        pointage.datetime_correction = dt
        pointage.note_correction = note
        pointage.correction_par = request.user
        pointage.save()  # déclenche le signal → resync Présence

        return Response({
            'status': 'corrigé',
            'datetime_correction': dt.isoformat(),
            'note_correction': note,
        })


class AnomaliePointageViewSet(viewsets.ModelViewSet):
    queryset = AnomaliePointage.objects.select_related('employe', 'pointage').all()
    serializer_class = AnomaliePointageSerializer
    rbac_module = 'pointage'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['employe', 'type_anomalie', 'statut', 'date']

    @action(detail=True, methods=['post'])
    def justifier(self, request, pk=None):
        anomalie = self.get_object()
        anomalie.statut = 'justifie'
        anomalie.justification = request.data.get('justification', '')
        anomalie.traite_par = request.user
        anomalie.save()
        return Response({'status': 'justifié'})
