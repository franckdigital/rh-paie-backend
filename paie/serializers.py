from rest_framework import serializers
from .models import BulletinPaie, ElementSalaire, LigneBulletin, JournalPaie


class ElementSalaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementSalaire
        fields = '__all__'


class LigneBulletinSerializer(serializers.ModelSerializer):
    element_nom = serializers.CharField(source='element.nom', read_only=True)
    element_type = serializers.CharField(source='element.type', read_only=True)
    element_categorie = serializers.CharField(source='element.categorie', read_only=True)

    class Meta:
        model = LigneBulletin
        fields = '__all__'


class BulletinPaieSerializer(serializers.ModelSerializer):
    lignes = LigneBulletinSerializer(many=True, read_only=True)
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    employe_matricule = serializers.CharField(source='employe.matricule', read_only=True)
    employe_poste = serializers.CharField(source='employe.poste.titre', read_only=True)
    employe_departement = serializers.CharField(source='employe.departement.nom', read_only=True)

    class Meta:
        model = BulletinPaie
        fields = '__all__'


class JournalPaieSerializer(serializers.ModelSerializer):
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)

    class Meta:
        model = JournalPaie
        fields = '__all__'
