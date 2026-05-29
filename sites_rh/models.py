from django.db import models
from entreprises.models import Entreprise


class Site(models.Model):
    TYPE_CHOICES = [
        ('siege', 'Siège social'),
        ('usine', 'Usine / Production'),
        ('agence', 'Agence'),
        ('chantier', 'Chantier'),
        ('poste_securite', 'Poste de sécurité'),
        ('entrepot', 'Entrepôt'),
        ('autre', 'Autre'),
    ]
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='sites')
    nom = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    type_site = models.CharField(max_length=30, choices=TYPE_CHOICES, default='agence')
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    # Géolocalisation
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    rayon_geofence = models.IntegerField(default=100, help_text='Rayon autorisé en mètres pour le pointage GPS')
    telephone = models.CharField(max_length=20, blank=True)
    responsable = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sites_geres'
    )
    est_actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'
        ordering = ['entreprise', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.entreprise.sigle or self.entreprise.nom})"


class Unite(models.Model):
    TYPE_CHOICES = [
        ('departement', 'Département'),
        ('ligne_production', 'Ligne de production'),
        ('equipe', 'Équipe'),
        ('service', 'Service'),
        ('poste_garde', 'Poste de garde'),
    ]
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='unites')
    nom = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)
    type_unite = models.CharField(max_length=30, choices=TYPE_CHOICES, default='departement')
    description = models.TextField(blank=True)
    responsable = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='unites_gerees'
    )
    capacite_max = models.IntegerField(default=0, help_text='Nombre max d\'agents')
    est_actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Unité'
        verbose_name_plural = 'Unités'
        ordering = ['site', 'nom']

    def __str__(self):
        return f"{self.nom} — {self.site.nom}"
