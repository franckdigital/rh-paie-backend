from rest_framework import serializers
from .models import Presence, JourFerie, RapportPresence


class PresenceSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    employe_matricule = serializers.CharField(source='employe.matricule', read_only=True)
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    shift_nom = serializers.CharField(source='shift.nom', read_only=True)

    class Meta:
        model = Presence
        fields = '__all__'


class JourFerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourFerie
        fields = '__all__'


class RapportPresenceSerializer(serializers.ModelSerializer):
    site_nom = serializers.CharField(source='site.nom', read_only=True)

    class Meta:
        model = RapportPresence
        fields = '__all__'
