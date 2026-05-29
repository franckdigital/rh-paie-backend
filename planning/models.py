from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class TypeShift(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    traverse_minuit = models.BooleanField(default=False, help_text='Vrai si shift 18h→06h')
    duree_heures = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    est_nuit = models.BooleanField(default=False)
    couleur = models.CharField(max_length=7, default='#6366f1', help_text='Couleur hex pour calendrier')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Type de shift'
        verbose_name_plural = 'Types de shifts'

    def __str__(self):
        return f"{self.nom} ({self.heure_debut.strftime('%H:%M')}→{self.heure_fin.strftime('%H:%M')})"


class RotationEquipe(models.Model):
    CYCLE_CHOICES = [
        ('3x8', '3×8 (rotation tri-équipe)'),
        ('2x12', '2×12 (rotation bi-équipe)'),
        ('5j8h', '5 jours / 8h'),
        ('6j8h', '6 jours / 8h'),
        ('personnalise', 'Personnalisé'),
    ]
    nom = models.CharField(max_length=100)
    type_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default='3x8')
    description = models.TextField(blank=True)
    duree_cycle_jours = models.IntegerField(default=21, help_text='Durée du cycle de rotation en jours')

    class Meta:
        verbose_name = 'Rotation d\'équipe'
        verbose_name_plural = 'Rotations d\'équipes'

    def __str__(self):
        return f"{self.nom} ({self.type_cycle})"


class Equipe(models.Model):
    site = models.ForeignKey('sites_rh.Site', on_delete=models.CASCADE, related_name='equipes')
    unite = models.ForeignKey('sites_rh.Unite', on_delete=models.SET_NULL, null=True, blank=True)
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    rotation = models.ForeignKey(
        RotationEquipe, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipes'
    )
    chef_equipe = models.ForeignKey(
        'employes.Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='equipes_dirigees'
    )
    couleur = models.CharField(max_length=7, default='#10b981')
    est_actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Équipe'
        verbose_name_plural = 'Équipes'

    def __str__(self):
        return f"{self.nom} — {self.site.nom}"


class PlanningMensuel(models.Model):
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('publie', 'Publié'),
        ('cloture', 'Clôturé'),
    ]
    site = models.ForeignKey('sites_rh.Site', on_delete=models.CASCADE, related_name='plannings')
    annee = models.IntegerField()
    mois = models.IntegerField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Planning mensuel'
        verbose_name_plural = 'Plannings mensuels'
        unique_together = ('site', 'annee', 'mois')

    def __str__(self):
        return f"Planning {self.site.nom} {self.mois:02d}/{self.annee}"


class MembreEquipe(models.Model):
    equipe = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name='membres')
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='equipes_appartenues')
    date_debut = models.DateField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Membre d'équipe"
        verbose_name_plural = "Membres d'équipe"
        unique_together = ('equipe', 'employe')
        ordering = ['employe__nom']

    def __str__(self):
        return f"{self.employe} → {self.equipe}"


class LignePlanning(models.Model):
    TYPE_JOUR_CHOICES = [
        ('travail', 'Jour travaillé'),
        ('repos', 'Repos'),
        ('conge', 'Congé'),
        ('ferie', 'Jour férié'),
        ('mission', 'Mission'),
        ('formation', 'Formation'),
    ]
    planning = models.ForeignKey(PlanningMensuel, on_delete=models.SET_NULL, null=True, blank=True, related_name='lignes')
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='lignes_planning')
    date = models.DateField()
    type_jour = models.CharField(max_length=20, choices=TYPE_JOUR_CHOICES, default='travail')
    shift = models.ForeignKey(TypeShift, on_delete=models.SET_NULL, null=True, blank=True)
    equipe = models.ForeignKey(Equipe, on_delete=models.SET_NULL, null=True, blank=True)
    site_affecte = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.CharField(max_length=200, blank=True)
    est_remplacement = models.BooleanField(default=False)
    remplace_employe = models.ForeignKey(
        'employes.Employe', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='remplacements_recus'
    )

    class Meta:
        verbose_name = 'Ligne planning'
        verbose_name_plural = 'Lignes planning'
        unique_together = ('employe', 'date')
        ordering = ['date', 'employe__nom']

    def __str__(self):
        return f"{self.employe} — {self.date} ({self.type_jour})"
