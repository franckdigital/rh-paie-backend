from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from .models import Employe, Departement, Poste, FichePoste, AffectationHistorique
from .serializers import (
    EmployeListSerializer, EmployeDetailSerializer, DepartementSerializer,
    PosteSerializer, FichePosteSerializer, AffectationHistoriqueSerializer
)
from users.permissions import RBACPermission


class FichePosteViewSet(viewsets.ModelViewSet):
    queryset = FichePoste.objects.all()
    serializer_class = FichePosteSerializer
    rbac_module = 'employes'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['titre', 'niveau']

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from config.reports_pdf import pdf_fiche_poste_response
        fiche = self.get_object()
        return pdf_fiche_poste_response(fiche)


class DepartementViewSet(viewsets.ModelViewSet):
    queryset = Departement.objects.select_related('site').all()
    serializer_class = DepartementSerializer
    rbac_module = 'employes'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['site']
    search_fields = ['nom']


class PosteViewSet(viewsets.ModelViewSet):
    queryset = Poste.objects.select_related('departement').all()
    serializer_class = PosteSerializer
    rbac_module = 'employes'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filterset_fields = ['departement']


class EmployeViewSet(viewsets.ModelViewSet):
    rbac_module = 'employes'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['departement', 'statut', 'type_contrat', 'genre', 'site', 'unite', 'entreprise']
    search_fields = ['nom', 'prenom', 'matricule', 'email', 'telephone']
    ordering_fields = ['nom', 'date_embauche', 'salaire_base']

    def get_queryset(self):
        return Employe.objects.select_related(
            'departement', 'poste', 'site', 'unite', 'entreprise'
        ).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeListSerializer
        return EmployeDetailSerializer

    def _handle_validation(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as e:
            detail = e.message_dict if hasattr(e, 'message_dict') else {'non_field_errors': e.messages}
            raise DRFValidationError(detail=detail)

    def perform_create(self, serializer):
        self._handle_validation(serializer)

    def perform_update(self, serializer):
        self._handle_validation(serializer)

    @action(detail=True, methods=['post'])
    def muter(self, request, pk=None):
        """Mutation vers un nouveau site/poste avec historisation."""
        employe = self.get_object()
        # Sauvegarder l'ancienne affectation
        AffectationHistorique.objects.create(
            employe=employe,
            site=employe.site,
            departement=employe.departement,
            poste=employe.poste,
            unite=employe.unite,
            date_debut=employe.date_embauche,
            date_fin=timezone.now().date(),
            motif=request.data.get('motif', ''),
            created_by=request.user
        )
        # Appliquer nouvelle affectation
        for field in ['site', 'departement', 'poste', 'unite', 'salaire_base']:
            if field in request.data:
                setattr(employe, field + '_id' if field not in ['salaire_base'] else field,
                        request.data[field])
        employe.save()
        return Response(EmployeDetailSerializer(employe).data)

    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        employe = self.get_object()
        hist = employe.historique_affectations.all()
        return Response(AffectationHistoriqueSerializer(hist, many=True).data)

    @action(detail=True, methods=['post'], url_path='creer-compte')
    def creer_compte(self, request, pk=None):
        """Crée un compte utilisateur lié à cet employé."""
        from users.models import User
        employe = self.get_object()
        if employe.user_id:
            return Response({'detail': 'Cet employé a déjà un compte utilisateur.'}, status=status.HTTP_400_BAD_REQUEST)
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        role     = request.data.get('role', 'employe')
        if not username or not password:
            return Response({'detail': 'username et password sont requis.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({'detail': 'Le mot de passe doit contenir au moins 8 caractères.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Ce nom d\'utilisateur est déjà pris.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User(
            username=username, email=employe.email,
            first_name=employe.prenom, last_name=employe.nom,
            role=role, telephone=employe.telephone or '',
            site=employe.site, entreprise=employe.entreprise,
        )
        user.set_password(password)
        user.save()
        employe.user = user
        employe.save(update_fields=['user'])
        return Response({'detail': 'Compte créé avec succès.', 'username': username, 'user_id': user.id})

    @action(detail=False, methods=['get'], url_path='mon-site')
    def mon_site(self, request):
        """Retourne les employés du site de l'utilisateur connecté (app mobile superviseur)."""
        from django.db.models import Q

        site = request.user.site
        if not site:
            try:
                emp = Employe.objects.select_related('site').get(
                    email=request.user.email, statut='actif'
                )
                site = emp.site
            except Employe.DoesNotExist:
                pass

        if not site:
            return Response(
                {'detail': 'Aucun site affecté à cet utilisateur.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = Employe.objects.select_related(
            'departement', 'poste', 'site', 'unite', 'entreprise'
        ).filter(site=site)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(nom__icontains=search) |
                Q(prenom__icontains=search) |
                Q(matricule__icontains=search)
            )

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(EmployeListSerializer(page, many=True).data)
        return Response(EmployeListSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        from config.reports_pdf import pdf_table_response
        from django.utils import timezone
        qs = self.filter_queryset(self.get_queryset())
        rows = [
            [
                e.matricule,
                e.nom_complet,
                e.departement.nom if e.departement else '—',
                e.poste.titre if e.poste else '—',
                e.get_type_contrat_display(),
                e.get_statut_display(),
                e.date_embauche.strftime('%d/%m/%Y'),
                f"{e.salaire_base:,.0f} FCFA",
            ]
            for e in qs.select_related('departement', 'poste')
        ]
        return pdf_table_response(
            f"employes_{timezone.now().strftime('%Y%m%d')}.pdf",
            'Rapport des effectifs',
            f"Généré le {timezone.now().strftime('%d/%m/%Y')} — {qs.count()} employé(s)",
            ['Matricule', 'Nom complet', 'Département', 'Poste', 'Contrat', 'Statut', 'Embauche', 'Salaire base'],
            rows,
            use_landscape=True,
        )

    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        from django.db.models import Count, Avg
        stats = {
            'total_actif': Employe.objects.filter(statut='actif').count(),
            'par_contrat': list(
                Employe.objects.filter(statut='actif')
                .values('type_contrat').annotate(nb=Count('id'))
            ),
            'par_genre': list(
                Employe.objects.filter(statut='actif')
                .values('genre').annotate(nb=Count('id'))
            ),
            'salaire_moyen': float(
                Employe.objects.filter(statut='actif').aggregate(m=Avg('salaire_base'))['m'] or 0
            ),
        }
        return Response(stats)
