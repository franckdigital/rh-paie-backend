import os
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from .models import Document, CategorieDocument
from .serializers import DocumentSerializer, CategorieDocumentSerializer
from users.permissions import RBACPermission


class CategorieDocumentViewSet(viewsets.ModelViewSet):
    queryset = CategorieDocument.objects.all()
    serializer_class = CategorieDocumentSerializer
    rbac_module = 'documents'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('employe', 'categorie').all()
    serializer_class = DocumentSerializer
    rbac_module = 'documents'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employe', 'categorie', 'statut', 'est_confidentiel']
    search_fields = ['nom', 'description']

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}

    def _extra_from_fichier(self, fichier):
        if not fichier:
            return {}
        return {
            'taille_fichier': fichier.size,
            'type_mime': fichier.content_type or '',
        }

    def perform_create(self, serializer):
        fichier = self.request.FILES.get('fichier')
        extra = self._extra_from_fichier(fichier)
        extra['ajoute_par'] = self.request.user
        serializer.save(**{k: v for k, v in extra.items() if k not in serializer.validated_data})

    def perform_update(self, serializer):
        fichier = self.request.FILES.get('fichier')
        extra = self._extra_from_fichier(fichier)
        serializer.save(**{k: v for k, v in extra.items() if k not in serializer.validated_data})

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.fichier:
            return Response({'detail': 'Aucun fichier attaché.'}, status=404)
        try:
            file_handle = document.fichier.open('rb')
        except (FileNotFoundError, OSError):
            return Response({'detail': 'Fichier introuvable sur le serveur.'}, status=404)
        filename = os.path.basename(document.fichier.name)
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
            content_type=document.type_mime or 'application/octet-stream',
        )
