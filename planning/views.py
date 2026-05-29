from datetime import date, timedelta
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import TypeShift, Equipe, RotationEquipe, PlanningMensuel, LignePlanning, MembreEquipe
from .serializers import (
    TypeShiftSerializer, EquipeSerializer, RotationEquipeSerializer,
    PlanningMensuelSerializer, LignePlanningSerializer, MembreEquipeSerializer,
)
from users.permissions import RBACPermission


class TypeShiftViewSet(viewsets.ModelViewSet):
    queryset = TypeShift.objects.all()
    serializer_class = TypeShiftSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]


class RotationEquipeViewSet(viewsets.ModelViewSet):
    queryset = RotationEquipe.objects.all()
    serializer_class = RotationEquipeSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]


class EquipeViewSet(viewsets.ModelViewSet):
    queryset = Equipe.objects.select_related('site', 'chef_equipe', 'rotation').filter(est_actif=True)
    serializer_class = EquipeSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['site', 'rotation']

    @action(detail=True, methods=['get'])
    def membres(self, request, pk=None):
        equipe = self.get_object()
        membres = MembreEquipe.objects.filter(equipe=equipe, est_actif=True).select_related('employe', 'employe__poste')
        return Response(MembreEquipeSerializer(membres, many=True).data)

    @action(detail=True, methods=['post'], url_path='ajouter_membre')
    def ajouter_membre(self, request, pk=None):
        equipe = self.get_object()
        employe_id = request.data.get('employe_id')
        if not employe_id:
            return Response({'detail': 'employe_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        membre, created = MembreEquipe.objects.get_or_create(equipe=equipe, employe_id=employe_id)
        if not created and not membre.est_actif:
            membre.est_actif = True
            membre.save()
        return Response(MembreEquipeSerializer(membre).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='retirer_membre')
    def retirer_membre(self, request, pk=None):
        equipe = self.get_object()
        employe_id = request.data.get('employe_id')
        MembreEquipe.objects.filter(equipe=equipe, employe_id=employe_id).update(est_actif=False)
        return Response({'status': 'membre retiré'})


class MembreEquipeViewSet(viewsets.ModelViewSet):
    queryset = MembreEquipe.objects.select_related('equipe', 'employe').filter(est_actif=True)
    serializer_class = MembreEquipeSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['equipe', 'employe']


class PlanningMensuelViewSet(viewsets.ModelViewSet):
    queryset = PlanningMensuel.objects.select_related('site').all()
    serializer_class = PlanningMensuelSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['site', 'annee', 'mois', 'statut']

    @action(detail=False, methods=['post'], url_path='creer_ou_trouver')
    def creer_ou_trouver(self, request):
        site_id = request.data.get('site_id')
        annee = request.data.get('annee')
        mois = request.data.get('mois')
        if not all([site_id, annee, mois]):
            return Response({'detail': 'site_id, annee, mois requis'}, status=status.HTTP_400_BAD_REQUEST)
        planning, created = PlanningMensuel.objects.get_or_create(
            site_id=site_id, annee=annee, mois=mois,
            defaults={'cree_par': request.user, 'statut': 'brouillon'},
        )
        return Response(PlanningMensuelSerializer(planning).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def publier(self, request, pk=None):
        planning = self.get_object()
        planning.statut = 'publie'
        planning.save()
        return Response({'status': 'publié'})

    @action(detail=True, methods=['get'])
    def calendrier(self, request, pk=None):
        planning = self.get_object()
        lignes = planning.lignes.select_related('employe', 'shift', 'equipe').all()
        return Response(LignePlanningSerializer(lignes, many=True).data)


class LignePlanningViewSet(viewsets.ModelViewSet):
    queryset = LignePlanning.objects.select_related('employe', 'shift', 'planning', 'equipe').all()
    serializer_class = LignePlanningSerializer
    rbac_module = 'planning'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['planning', 'employe', 'date', 'type_jour', 'shift', 'equipe']

    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        lignes_data = request.data.get('lignes', [])
        created_count = 0
        updated_count = 0
        for data in lignes_data:
            employe_id = data.get('employe')
            date_val = data.get('date')
            if not employe_id or not date_val:
                continue
            ligne, created = LignePlanning.objects.update_or_create(
                employe_id=employe_id,
                date=date_val,
                defaults={k: v for k, v in data.items() if k not in ('employe', 'date')},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        return Response({'created': created_count, 'updated': updated_count})

    @action(detail=False, methods=['post'], url_path='generer_rotation')
    def generer_rotation(self, request):
        equipe_id = request.data.get('equipe_id')
        annee = int(request.data.get('annee', date.today().year))
        mois = int(request.data.get('mois', date.today().month))
        planning_id = request.data.get('planning_id')
        pattern = request.data.get('pattern', [])
        cycle_semaines = int(request.data.get('cycle_semaines', 2))
        jours_repos = request.data.get('jours_repos', [7])  # isoweekday: 1=lun, 7=dim

        if not equipe_id or not pattern:
            return Response({'detail': 'equipe_id et pattern requis'}, status=status.HTTP_400_BAD_REQUEST)

        membres_ids = list(
            MembreEquipe.objects.filter(equipe_id=equipe_id, est_actif=True).values_list('employe_id', flat=True)
        )
        if not membres_ids:
            return Response({'detail': 'Aucun membre dans cette équipe'}, status=status.HTTP_400_BAD_REQUEST)

        # Build shift map: week_in_cycle (1-based) → shift_id or None
        shift_map = {int(p['semaine_dans_cycle']): p.get('shift_id') for p in pattern}

        # Date range for the month
        premier_jour = date(annee, mois, 1)
        if mois == 12:
            dernier_jour = date(annee + 1, 1, 1) - timedelta(days=1)
        else:
            dernier_jour = date(annee, mois + 1, 1) - timedelta(days=1)

        # Reference Monday (week 1 = week containing premier_jour)
        delta = premier_jour.weekday()
        ref_lundi = premier_jour - timedelta(days=delta)

        created_count = 0
        jour = premier_jour
        while jour <= dernier_jour:
            is_repos = jour.isoweekday() in [int(j) for j in jours_repos]
            semaines_depuis_ref = (jour - ref_lundi).days // 7
            semaine_dans_cycle = (semaines_depuis_ref % cycle_semaines) + 1
            shift_id = None if is_repos else shift_map.get(semaine_dans_cycle)
            type_jour = 'repos' if is_repos or not shift_id else 'travail'

            for emp_id in membres_ids:
                defaults = {
                    'shift_id': shift_id,
                    'equipe_id': equipe_id,
                    'type_jour': type_jour,
                }
                if planning_id:
                    defaults['planning_id'] = planning_id
                LignePlanning.objects.update_or_create(
                    employe_id=emp_id,
                    date=jour,
                    defaults=defaults,
                )
                created_count += 1
            jour += timedelta(days=1)

        return Response({'lignes_generees': created_count, 'membres': len(membres_ids)})

    @action(detail=False, methods=['post'], url_path='permuter_equipes')
    def permuter_equipes(self, request):
        """Permute les shifts de deux équipes sur une période donnée."""
        equipe1_id = request.data.get('equipe1_id')
        equipe2_id = request.data.get('equipe2_id')
        date_debut = request.data.get('date_debut')
        date_fin = request.data.get('date_fin')

        if not all([equipe1_id, equipe2_id, date_debut, date_fin]):
            return Response({'detail': 'equipe1_id, equipe2_id, date_debut, date_fin requis'}, status=400)

        lignes1 = list(LignePlanning.objects.filter(equipe_id=equipe1_id, date__gte=date_debut, date__lte=date_fin))
        lignes2 = list(LignePlanning.objects.filter(equipe_id=equipe2_id, date__gte=date_debut, date__lte=date_fin))

        # Swap shifts
        for l1 in lignes1:
            matching = next((l for l in lignes2 if l.date == l1.date), None)
            if matching:
                l1.shift_id, matching.shift_id = matching.shift_id, l1.shift_id
                l1.type_jour, matching.type_jour = matching.type_jour, l1.type_jour
                l1.save()
                matching.save()

        return Response({'permutations': len(lignes1)})

    @action(detail=False, methods=['get'], url_path='mon-planning')
    def mon_planning(self, request):
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
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        if not date_debut:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            date_debut = monday.isoformat()
        if not date_fin:
            d = date.fromisoformat(date_debut)
            date_fin = (d + timedelta(days=6)).isoformat()
        qs = self.get_queryset().filter(employe=employe, date__gte=date_debut, date__lte=date_fin).order_by('date')
        return Response(LignePlanningSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='planning-equipe')
    def planning_equipe(self, request):
        """Planning de tous les agents du site du superviseur connecté."""
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        if not date_debut:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            date_debut = monday.isoformat()
        if not date_fin:
            d = date.fromisoformat(date_debut)
            date_fin = (d + timedelta(days=6)).isoformat()
        site = request.user.site
        if not site:
            try:
                from employes.models import Employe
                emp = Employe.objects.get(email=request.user.email)
                site = emp.site
            except Exception:
                pass
        qs = self.get_queryset().filter(date__gte=date_debut, date__lte=date_fin)
        if site:
            qs = qs.filter(employe__site=site)
        qs = qs.select_related('employe', 'shift').order_by('date', 'employe__nom')
        return Response(LignePlanningSerializer(qs, many=True).data)
