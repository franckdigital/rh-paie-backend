from django.db import models
from django.conf import settings


class EvenementCarriere(models.Model):
    TYPE_CHOICES = [
        ('recrutement', 'Recrutement'),
        ('promotion', 'Promotion'),
        ('mutation', 'Mutation'),
        ('changement_poste', 'Changement de poste'),
        ('augmentation_salaire', 'Augmentation de salaire'),
        ('renouvellement_contrat', 'Renouvellement de contrat'),
        ('changement_contrat', 'Changement de type contrat'),
        ('suspension', 'Suspension'),
        ('reprise', 'Reprise de service'),
        ('demission', 'Démission'),
        ('licenciement', 'Licenciement'),
        ('depart_retraite', 'Départ à la retraite'),
        ('sanction', 'Sanction disciplinaire'),
        ('formation', 'Formation'),
        ('evaluation', 'Évaluation de performance'),
    ]
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='evenements_carriere')
    type_evenement = models.CharField(max_length=30, choices=TYPE_CHOICES)
    date_evenement = models.DateField()
    date_effet = models.DateField(help_text='Date d\'entrée en vigueur')
    description = models.TextField()

    # Avant
    poste_avant = models.ForeignKey(
        'employes.Poste', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    site_avant = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    salaire_avant = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Après
    poste_apres = models.ForeignKey(
        'employes.Poste', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    site_apres = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    salaire_apres = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    TYPE_CONTRAT_CHOICES = [
        ('essai', "Période d'essai"),
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
    ]
    type_contrat = models.CharField(
        max_length=10, choices=TYPE_CONTRAT_CHOICES, blank=True, null=True,
        verbose_name='Type de contrat'
    )
    duree_contrat_mois = models.IntegerField(
        null=True, blank=True, verbose_name='Durée du contrat (mois)'
    )
    duree_validite_jours = models.IntegerField(
        null=True, blank=True, verbose_name='Durée de validité (jours)',
        help_text='Durée d\'effet de l\'événement en jours (suspension, formation, sanction…)'
    )

    document = models.ForeignKey(
        'documents.Document', on_delete=models.SET_NULL, null=True, blank=True
    )
    approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='validations_carrieres'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Événement carrière'
        verbose_name_plural = 'Événements carrière'
        ordering = ['-date_evenement']

    def __str__(self):
        return f"{self.employe} — {self.type_evenement} ({self.date_evenement})"


class RegleEvolutionCarriere(models.Model):
    """Règles automatiques d'évolution (ex: après 5 ans → éligible superviseur)."""
    entreprise = models.ForeignKey('entreprises.Entreprise', on_delete=models.CASCADE)
    nom = models.CharField(max_length=150)
    poste_actuel = models.ForeignKey(
        'employes.Poste', on_delete=models.CASCADE, related_name='regles_evolution_depart'
    )
    poste_cible = models.ForeignKey(
        'employes.Poste', on_delete=models.SET_NULL, null=True, related_name='regles_evolution_cible'
    )
    anciennete_min_annees = models.IntegerField(default=0)
    est_actif = models.BooleanField(default=True)
    notification_auto = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Règle évolution carrière'
        verbose_name_plural = 'Règles évolution carrière'

    def __str__(self):
        return f"{self.nom} ({self.anciennete_min_annees} ans)"
