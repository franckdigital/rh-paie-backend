from rest_framework import serializers
from .models import EvenementCarriere, RegleEvolutionCarriere


class EvenementCarriereSerializer(serializers.ModelSerializer):
    type_evenement_display = serializers.CharField(source='get_type_evenement_display', read_only=True)
    variation_salaire = serializers.SerializerMethodField()

    class Meta:
        model = EvenementCarriere
        fields = '__all__'

    def get_variation_salaire(self, obj):
        if obj.salaire_avant and obj.salaire_apres:
            diff = float(obj.salaire_apres) - float(obj.salaire_avant)
            pct = (diff / float(obj.salaire_avant)) * 100 if obj.salaire_avant else 0
            return {'montant': diff, 'pourcentage': round(pct, 2)}
        return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        emp = instance.employe
        rep['employe'] = {
            'id': emp.id,
            'nom': emp.nom,
            'prenom': emp.prenom,
            'matricule': emp.matricule,
        } if emp else None
        poste_avant = instance.poste_avant
        rep['poste_avant_nom'] = poste_avant.titre if poste_avant else None
        poste_apres = instance.poste_apres
        rep['poste_apres_nom'] = poste_apres.titre if poste_apres else None
        return rep


class RegleEvolutionCarriereSerializer(serializers.ModelSerializer):
    poste_actuel_nom = serializers.CharField(source='poste_actuel.titre', read_only=True)
    poste_cible_nom = serializers.CharField(source='poste_cible.titre', read_only=True, allow_null=True)

    class Meta:
        model = RegleEvolutionCarriere
        fields = '__all__'
