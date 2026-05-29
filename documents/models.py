from django.db import models
from django.conf import settings


class CategorieDocument(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, default='file-text')

    class Meta:
        verbose_name = 'Catégorie document'
        verbose_name_plural = 'Catégories documents'

    def __str__(self):
        return self.nom


class Document(models.Model):
    STATUT_CHOICES = [
        ('valide', 'Valide'),
        ('expire', 'Expiré'),
        ('en_attente', 'En attente validation'),
        ('archive', 'Archivé'),
    ]
    employe = models.ForeignKey(
        'employes.Employe', on_delete=models.CASCADE, related_name='documents',
        null=True, blank=True
    )
    entreprise = models.ForeignKey(
        'entreprises.Entreprise', on_delete=models.SET_NULL, null=True, blank=True
    )
    categorie = models.ForeignKey(CategorieDocument, on_delete=models.SET_NULL, null=True)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    fichier = models.FileField(upload_to='documents/%Y/%m/')
    taille_fichier = models.IntegerField(default=0, help_text='Taille en octets')
    type_mime = models.CharField(max_length=100, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='valide')
    date_document = models.DateField(null=True, blank=True)
    date_expiration = models.DateField(null=True, blank=True, help_text='Pour CNI, permis, etc.')
    est_confidentiel = models.BooleanField(default=False)
    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='documents_ajoutes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.employe or self.entreprise}"

    @property
    def est_expire(self):
        from django.utils import timezone
        return self.date_expiration and self.date_expiration < timezone.now().date()
