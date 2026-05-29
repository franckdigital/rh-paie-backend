from rest_framework import serializers
from .models import DemandeConge, TypeConge, SoldeConge


class TypeCongeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeConge
        fields = '__all__'


class SoldeCongeSerializer(serializers.ModelSerializer):
    type_conge_nom = serializers.CharField(source='type_conge.nom', read_only=True)

    class Meta:
        model = SoldeConge
        fields = '__all__'


class DemandeCongeSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    type_conge_nom = serializers.CharField(source='type_conge.nom', read_only=True)

    class Meta:
        model = DemandeConge
        fields = '__all__'
        read_only_fields = ['approuve_par', 'date_approbation']
