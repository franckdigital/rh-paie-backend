from django.db import models
from django.conf import settings


class ParametreHeures(models.Model):
    """Configuration des règles de calcul des heures par entreprise."""
    entreprise = models.OneToOneField('entreprises.Entreprise', on_delete=models.CASCADE, related_name='parametres_heures')
    # Seuils quotidiens
    heures_normales_jour = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    heures_max_journalier = models.DecimalField(max_digits=4, decimal_places=2, default=12)
    # Heures nuit (tranche horaire)
    heure_debut_nuit = models.TimeField(default='22:00')
    heure_fin_nuit = models.TimeField(default='06:00')
    # Majorations (en %)
    taux_majoration_nuit = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    taux_majoration_supp_25 = models.DecimalField(max_digits=5, decimal_places=2, default=25, help_text='Supp 1-8h')
    taux_majoration_supp_50 = models.DecimalField(max_digits=5, decimal_places=2, default=50, help_text='Supp >8h')
    taux_majoration_dimanche = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    taux_majoration_ferie = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    # Tolérance retard (minutes)
    tolerance_retard_minutes = models.IntegerField(default=5)

    class Meta:
        verbose_name = 'Paramètre heures'
        verbose_name_plural = 'Paramètres heures'

    def __str__(self):
        return f"Paramètres heures — {self.entreprise}"


class RecapHeures(models.Model):
    """Récapitulatif mensuel des heures par employé (calculé automatiquement)."""
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='recaps_heures')
    annee = models.IntegerField()
    mois = models.IntegerField()
    # Heures
    heures_normales = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_nuit = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_supp_25 = models.DecimalField(max_digits=7, decimal_places=2, default=0, help_text='Majorées à 25%')
    heures_supp_50 = models.DecimalField(max_digits=7, decimal_places=2, default=0, help_text='Majorées à 50%')
    heures_dimanche = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_ferie = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    # Jours
    jours_travailles = models.IntegerField(default=0)
    jours_absents = models.IntegerField(default=0)
    jours_conge = models.IntegerField(default=0)
    retards_count = models.IntegerField(default=0)
    retards_minutes_total = models.IntegerField(default=0)
    # Montants calculés
    montant_heures_normales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_heures_nuit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_heures_supp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_absences_deduites = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    calcule_le = models.DateTimeField(auto_now=True)
    valide = models.BooleanField(default=False)
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Récap heures'
        verbose_name_plural = 'Récaps heures'
        unique_together = ('employe', 'annee', 'mois')
        ordering = ['-annee', '-mois']

    def __str__(self):
        return f"Heures {self.employe} — {self.mois:02d}/{self.annee}"

    def calculer_montants(self, salaire_base):
        """Calcule les montants en fonction du salaire base."""
        taux_horaire = float(salaire_base) / (26 * 8)  # Base 26 jours × 8h
        self.montant_heures_normales = round(float(self.heures_normales) * taux_horaire, 2)
        self.montant_heures_nuit = round(float(self.heures_nuit) * taux_horaire * 0.15, 2)
        montant_supp_25 = float(self.heures_supp_25) * taux_horaire * 1.25
        montant_supp_50 = float(self.heures_supp_50) * taux_horaire * 1.50
        self.montant_heures_supp = round(montant_supp_25 + montant_supp_50, 2)
        taux_journalier = float(salaire_base) / 26
        self.montant_absences_deduites = round(self.jours_absents * taux_journalier, 2)
