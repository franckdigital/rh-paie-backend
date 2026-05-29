from django.db import models
from django.conf import settings
from employes.models import Employe


class TypeConge(models.Model):
    nom = models.CharField(max_length=100)
    nombre_jours = models.IntegerField(default=0)
    est_paye = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Type de congé'
        verbose_name_plural = 'Types de congés'

    def __str__(self):
        return self.nom


class DemandeConge(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente chef'),
        ('valide_chef', 'Validé chef — Attente RH'),
        ('approuve', 'Approuvé RH'),
        ('refuse', 'Refusé'),
        ('annule', 'Annulé'),
    ]
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='demandes_conge')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.PROTECT)
    date_debut = models.DateField()
    date_fin = models.DateField()
    nombre_jours = models.IntegerField()
    motif = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    # Niveau 1 : Chef d'équipe
    chef_approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conges_valides_chef'
    )
    chef_date_approbation = models.DateTimeField(null=True, blank=True)
    chef_commentaire = models.TextField(blank=True)
    # Niveau 2 : RH
    approuve_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conges_approuves'
    )
    date_approbation = models.DateTimeField(null=True, blank=True)
    commentaire_approbation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande de congé'
        verbose_name_plural = 'Demandes de congés'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employe} - {self.type_conge} ({self.date_debut} → {self.date_fin})"


class SoldeConge(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='soldes_conge')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE)
    annee = models.IntegerField()
    jours_acquis = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    jours_pris = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    jours_restants = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Solde de congé'
        verbose_name_plural = 'Soldes de congés'
        unique_together = ('employe', 'type_conge', 'annee')

    def __str__(self):
        return f"{self.employe} - {self.type_conge} {self.annee}: {self.jours_restants}j"
