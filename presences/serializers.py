from rest_framework import serializers
from .models import Presence, JourFerie, RapportPresence


class PresenceSerializer(serializers.ModelSerializer):
    employe = serializers.SerializerMethodField()
    employe_id = serializers.IntegerField(source='employe_id', read_only=True)
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    shift_nom = serializers.CharField(source='shift.nom', read_only=True)
    heure_arrivee = serializers.SerializerMethodField()
    heure_depart = serializers.SerializerMethodField()

    def get_employe(self, obj):
        e = obj.employe
        if not e:
            return None
        return {
            'id': e.id,
            'prenom': e.prenom,
            'nom': e.nom,
            'matricule': e.matricule,
            'nom_complet': e.nom_complet,
        }

    def get_heure_arrivee(self, obj):
        return obj.heure_arrivee.strftime('%H:%M') if obj.heure_arrivee else None

    def get_heure_depart(self, obj):
        return obj.heure_depart.strftime('%H:%M') if obj.heure_depart else None

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
