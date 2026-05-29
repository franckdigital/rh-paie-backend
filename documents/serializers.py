from rest_framework import serializers
from .models import Document, CategorieDocument


class CategorieDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieDocument
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    est_expire = serializers.ReadOnlyField()
    taille_lisible = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['taille_fichier', 'type_mime', 'ajoute_par']

    def get_taille_lisible(self, obj):
        if obj.taille_fichier < 1024:
            return f"{obj.taille_fichier} o"
        elif obj.taille_fichier < 1024 * 1024:
            return f"{obj.taille_fichier / 1024:.1f} Ko"
        return f"{obj.taille_fichier / (1024*1024):.1f} Mo"

    def create(self, validated_data):
        request = self.context.get('request')
        fichier = validated_data.get('fichier')
        if fichier:
            validated_data['taille_fichier'] = fichier.size
            validated_data['type_mime'] = fichier.content_type
        if request:
            validated_data['ajoute_par'] = request.user
        return super().create(validated_data)
