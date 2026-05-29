from rest_framework import serializers
from .models import ParametreHeures, RecapHeures


class ParametreHeuresSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametreHeures
        fields = '__all__'


class RecapHeuresSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecapHeures
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        emp = instance.employe
        rep['employe'] = {
            'id': emp.id,
            'nom': emp.nom,
            'prenom': emp.prenom,
            'matricule': emp.matricule,
        } if emp else None
        rep['montant_total'] = (
            float(instance.montant_heures_normales or 0)
            + float(instance.montant_heures_nuit or 0)
            + float(instance.montant_heures_supp or 0)
        )
        rep['statut'] = 'valide' if instance.valide else 'calcule'
        return rep
