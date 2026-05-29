from rest_framework import serializers
from .models import Employe, Departement, Poste, FichePoste, AffectationHistorique


class FichePosteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FichePoste
        fields = '__all__'


class DepartementSerializer(serializers.ModelSerializer):
    nombre_employes = serializers.SerializerMethodField()
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)

    class Meta:
        model = Departement
        fields = '__all__'

    def get_nombre_employes(self, obj):
        return obj.employes.filter(statut='actif').count()


class PosteSerializer(serializers.ModelSerializer):
    departement_nom = serializers.CharField(source='departement.nom', read_only=True)

    class Meta:
        model = Poste
        fields = '__all__'


class AffectationHistoriqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffectationHistorique
        fields = '__all__'


class EmployeListSerializer(serializers.ModelSerializer):
    departement_nom = serializers.CharField(source='departement.nom', read_only=True)
    poste_titre = serializers.CharField(source='poste.titre', read_only=True)
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    anciennete_annees = serializers.ReadOnlyField()

    class Meta:
        model = Employe
        fields = [
            'id', 'matricule', 'nom', 'prenom', 'photo', 'email', 'telephone',
            'departement_nom', 'poste_titre', 'site_nom', 'type_contrat', 'statut',
            'date_embauche', 'anciennete_annees', 'salaire_base', 'genre',
        ]


class EmployeDetailSerializer(serializers.ModelSerializer):
    departement_nom = serializers.CharField(source='departement.nom', read_only=True)
    poste_titre = serializers.CharField(source='poste.titre', read_only=True)
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    unite_nom = serializers.CharField(source='unite.nom', read_only=True)
    nom_complet = serializers.ReadOnlyField()
    anciennete_annees = serializers.ReadOnlyField()
    historique_affectations = AffectationHistoriqueSerializer(many=True, read_only=True)
    fiche_poste_id = serializers.SerializerMethodField()

    def get_fiche_poste_id(self, obj):
        if obj.poste_id and obj.poste.fiche_poste_id:
            return obj.poste.fiche_poste_id
        return None

    class Meta:
        model = Employe
        fields = '__all__'
