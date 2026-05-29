from rest_framework import serializers
from .models import Pointage, AnomaliePointage


class PointageSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    employe_matricule = serializers.CharField(source='employe.matricule', read_only=True)
    site_nom = serializers.CharField(source='site.nom', read_only=True)

    class Meta:
        model = Pointage
        fields = '__all__'
        read_only_fields = ['distance_du_site', 'dans_geofence', 'device_correspond', 'statut', 'anomalie_description']

    def create(self, validated_data):
        pointage = Pointage(**validated_data)
        # Calculs anti-fraude automatiques
        pointage.calculer_distance_site()
        pointage.verifier_device()
        pointage.detecter_anomalies()
        pointage.save()
        return pointage


class PointageEntreeSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour l'app mobile (pointage entrée)."""
    class Meta:
        model = Pointage
        fields = [
            'employe', 'type_pointage', 'mode', 'datetime_pointage', 'date_pointage',
            'latitude', 'longitude', 'precision_gps', 'site',
            'device_id', 'device_imei', 'gps_mock_detecte', 'photo_selfie',
            'shift_prevu', 'pointe_par', 'note_superviseur'
        ]

    def create(self, validated_data):
        pointage = Pointage(**validated_data)
        pointage.calculer_distance_site()
        pointage.verifier_device()
        pointage.detecter_anomalies()
        pointage.save()
        # Créer/màj la présence du jour
        self._maj_presence(pointage)
        return pointage

    def _maj_presence(self, pointage):
        from presences.models import Presence
        presence, _ = Presence.objects.get_or_create(
            employe=pointage.employe,
            date=pointage.date_pointage,
            defaults={'site': pointage.site, 'shift': pointage.shift_prevu}
        )
        if pointage.type_pointage == 'entree':
            presence.heure_arrivee = pointage.datetime_pointage.time()
            presence.pointage_entree = pointage
        else:
            presence.heure_depart = pointage.datetime_pointage.time()
            presence.pointage_sortie = pointage
            presence.calculer_heures()
        if presence.heure_arrivee and pointage.shift_prevu:
            debut_prevu = pointage.shift_prevu.heure_debut
            arrivee = presence.heure_arrivee
            if arrivee > debut_prevu:
                from datetime import datetime
                retard = (datetime.combine(pointage.date_pointage, arrivee) -
                         datetime.combine(pointage.date_pointage, debut_prevu))
                presence.retard_minutes = retard.seconds // 60
                if presence.retard_minutes > 5:
                    presence.statut = 'retard'
                else:
                    presence.statut = 'present'
            else:
                presence.statut = 'present'
        presence.save()


class AnomaliePointageSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)

    class Meta:
        model = AnomaliePointage
        fields = '__all__'
