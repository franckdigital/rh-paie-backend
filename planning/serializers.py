from rest_framework import serializers
from .models import TypeShift, Equipe, RotationEquipe, PlanningMensuel, LignePlanning, MembreEquipe


class TypeShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeShift
        fields = '__all__'


class RotationEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotationEquipe
        fields = '__all__'


class MembreEquipeSerializer(serializers.ModelSerializer):
    employe_nom = serializers.SerializerMethodField()
    employe_matricule = serializers.CharField(source='employe.matricule', read_only=True)
    employe_poste = serializers.SerializerMethodField()

    class Meta:
        model = MembreEquipe
        fields = '__all__'

    def get_employe_nom(self, obj):
        return f"{obj.employe.prenom} {obj.employe.nom}"

    def get_employe_poste(self, obj):
        return obj.employe.poste.titre if obj.employe.poste else None


class EquipeSerializer(serializers.ModelSerializer):
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    rotation_nom = serializers.CharField(source='rotation.nom', read_only=True, allow_null=True)
    rotation_type = serializers.CharField(source='rotation.type_cycle', read_only=True, allow_null=True)
    membres_count = serializers.SerializerMethodField()

    class Meta:
        model = Equipe
        fields = '__all__'

    def get_membres_count(self, obj):
        return obj.membres.filter(est_actif=True).count()


class LignePlanningSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    employe_prenom = serializers.CharField(source='employe.prenom', read_only=True)
    employe_matricule = serializers.CharField(source='employe.matricule', read_only=True)
    shift_nom = serializers.CharField(source='shift.nom', read_only=True)
    shift_couleur = serializers.CharField(source='shift.couleur', read_only=True)
    shift_heure_debut = serializers.TimeField(source='shift.heure_debut', read_only=True)
    shift_heure_fin = serializers.TimeField(source='shift.heure_fin', read_only=True)
    equipe_nom = serializers.CharField(source='equipe.nom', read_only=True, allow_null=True)
    remplace_nom = serializers.SerializerMethodField()

    class Meta:
        model = LignePlanning
        fields = '__all__'

    def get_remplace_nom(self, obj):
        if obj.remplace_employe:
            return f"{obj.remplace_employe.prenom} {obj.remplace_employe.nom}"
        return None


class PlanningMensuelSerializer(serializers.ModelSerializer):
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    total_lignes = serializers.SerializerMethodField()

    class Meta:
        model = PlanningMensuel
        fields = '__all__'

    def get_total_lignes(self, obj):
        return obj.lignes.count()
