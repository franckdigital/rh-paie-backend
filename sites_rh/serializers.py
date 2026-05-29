from rest_framework import serializers
from .models import Site, Unite


class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = '__all__'


class SiteSerializer(serializers.ModelSerializer):
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    nombre_employes = serializers.SerializerMethodField()
    unites = UniteSerializer(many=True, read_only=True)

    class Meta:
        model = Site
        fields = '__all__'

    def get_nombre_employes(self, obj):
        return obj.employes.filter(statut='actif').count()


class SiteListSerializer(serializers.ModelSerializer):
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    nombre_employes = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = ['id', 'nom', 'code', 'type_site', 'pays', 'ville', 'entreprise', 'entreprise_nom',
                  'nombre_employes', 'latitude', 'longitude', 'rayon_geofence', 'est_actif']

    def get_nombre_employes(self, obj):
        return obj.employes.filter(statut='actif').count()
