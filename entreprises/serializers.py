from rest_framework import serializers
from .models import Entreprise


class EntrepriseSerializer(serializers.ModelSerializer):
    nombre_sites = serializers.SerializerMethodField()
    nombre_employes = serializers.SerializerMethodField()

    class Meta:
        model = Entreprise
        fields = '__all__'

    def get_nombre_sites(self, obj):
        return obj.sites.filter(est_actif=True).count()

    def get_nombre_employes(self, obj):
        return obj.employes.filter(statut='actif').count()
