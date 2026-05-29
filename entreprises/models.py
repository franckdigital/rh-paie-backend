from django.db import models


class Entreprise(models.Model):
    SECTEUR_CHOICES = [
        ('securite', 'Sécurité / Gardiennage'),
        ('industrie', 'Industrie / Usine'),
        ('services', 'Services'),
        ('commerce', 'Commerce'),
        ('sante', 'Santé'),
        ('education', 'Éducation'),
        ('btp', 'BTP / Construction'),
        ('autre', 'Autre'),
    ]
    nom = models.CharField(max_length=200)
    sigle = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to='entreprises/logos/', blank=True, null=True)
    secteur = models.CharField(max_length=30, choices=SECTEUR_CHOICES, default='services')
    rccm = models.CharField(max_length=50, blank=True, verbose_name='N° RCCM')
    ncc = models.CharField(max_length=50, blank=True, verbose_name='N° NCC')
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    pays = models.CharField(max_length=100, default='Côte d\'Ivoire')
    est_actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entreprise'
        verbose_name_plural = 'Entreprises'
        ordering = ['nom']

    def __str__(self):
        return self.nom
