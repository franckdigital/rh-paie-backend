from django.db import models
from django.conf import settings
from django.utils import timezone


class Departement(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    site = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='departements'
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='departements_geres'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Département'
        verbose_name_plural = 'Départements'

    def __str__(self):
        return self.nom


class FichePoste(models.Model):
    NIVEAU_CHOICES = [
        ('operateur', 'Opérateur'),
        ('technicien', 'Technicien'),
        ('agent', 'Agent'),
        ('superviseur', 'Superviseur'),
        ('chef_equipe', 'Chef d\'équipe'),
        ('chef_service', 'Chef de service'),
        ('responsable', 'Responsable'),
        ('directeur', 'Directeur'),
    ]
    titre = models.CharField(max_length=150)
    niveau = models.CharField(max_length=30, choices=NIVEAU_CHOICES, default='agent')
    missions = models.TextField(blank=True)
    responsabilites = models.TextField(blank=True)
    competences_requises = models.TextField(blank=True)
    formation_requise = models.CharField(max_length=200, blank=True)
    experience_min_annees = models.IntegerField(default=0)
    epi_requis = models.TextField(blank=True, verbose_name='EPI requis')
    horaires_applicables = models.TextField(blank=True, verbose_name='Horaires applicables')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fiche de poste'
        verbose_name_plural = 'Fiches de poste'

    def __str__(self):
        return f"{self.titre} ({self.niveau})"


class Poste(models.Model):
    titre = models.CharField(max_length=100)
    departement = models.ForeignKey(Departement, on_delete=models.CASCADE, related_name='postes')
    fiche_poste = models.ForeignKey(
        FichePoste, on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True)
    salaire_min = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salaire_max = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Poste'
        verbose_name_plural = 'Postes'

    def __str__(self):
        return f"{self.titre} - {self.departement}"


class Employe(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('suspendu', 'Suspendu'),
        ('demissionnaire', 'Démissionnaire'),
        ('licencie', 'Licencié'),
        ('retraite', 'Retraité'),
    ]
    CONTRAT_CHOICES = [
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('freelance', 'Freelance'),
        ('interimaire', 'Intérimaire'),
    ]
    GENRE_CHOICES = [('M', 'Masculin'), ('F', 'Féminin')]
    SITUATION_CHOICES = [
        ('celibataire', 'Célibataire'),
        ('marie', 'Marié(e)'),
        ('divorce', 'Divorcé(e)'),
        ('veuf', 'Veuf/Veuve'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='employe', null=True, blank=True
    )
    # Identité
    matricule = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    genre = models.CharField(max_length=1, choices=GENRE_CHOICES)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=100, blank=True)
    nationalite = models.CharField(max_length=50, default="Ivoirienne")
    situation_familiale = models.CharField(max_length=20, choices=SITUATION_CHOICES, default='celibataire')
    nombre_enfants = models.IntegerField(default=0)

    # Contact
    telephone = models.CharField(max_length=20)
    telephone2 = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    adresse = models.TextField(blank=True)
    photo = models.ImageField(upload_to='employes/', blank=True, null=True)

    # Contact urgence
    contact_urgence_nom = models.CharField(max_length=150, blank=True)
    contact_urgence_telephone = models.CharField(max_length=20, blank=True)
    contact_urgence_lien = models.CharField(max_length=50, blank=True)

    # Documents identité
    num_cni = models.CharField(max_length=30, blank=True, verbose_name='N° CNI/Passeport')
    date_expiration_cni = models.DateField(null=True, blank=True)
    num_cnps = models.CharField(max_length=50, blank=True)
    num_cmu = models.CharField(max_length=50, blank=True)
    groupe_sanguin = models.CharField(max_length=5, blank=True)

    # Affectation organisationnelle
    entreprise = models.ForeignKey(
        'entreprises.Entreprise', on_delete=models.SET_NULL, null=True, blank=True, related_name='employes'
    )
    site = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='employes'
    )
    unite = models.ForeignKey(
        'sites_rh.Unite', on_delete=models.SET_NULL, null=True, blank=True, related_name='employes'
    )
    departement = models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, related_name='employes')
    poste = models.ForeignKey(Poste, on_delete=models.SET_NULL, null=True, related_name='employes')
    manager = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordonnes'
    )

    # Contrat
    type_contrat = models.CharField(max_length=20, choices=CONTRAT_CHOICES, default='cdi')
    date_embauche = models.DateField()
    date_fin_contrat = models.DateField(null=True, blank=True)
    salaire_base = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')

    # Banque
    banque = models.CharField(max_length=100, blank=True)
    rib = models.CharField(max_length=50, blank=True)
    mode_paiement = models.CharField(
        max_length=20,
        choices=[('virement', 'Virement'), ('especes', 'Espèces'), ('mobile_money', 'Mobile Money')],
        default='virement'
    )
    numero_mobile_money = models.CharField(max_length=20, blank=True)

    # Appareil mobile lié (anti-fraude pointage)
    device_id = models.CharField(max_length=200, blank=True, verbose_name='ID appareil mobile')
    device_imei = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Employé'
        verbose_name_plural = 'Employés'
        ordering = ['nom', 'prenom']

    # SMIG CI en vigueur
    SMIG_CI = 75_000  # FCFA/mois

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.salaire_base is not None and float(self.salaire_base) < self.SMIG_CI:
            raise ValidationError({
                'salaire_base': f"Le salaire de base ({self.salaire_base} FCFA) est inférieur au SMIG CI ({self.SMIG_CI:,} FCFA)."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricule} - {self.nom} {self.prenom}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    @property
    def anciennete_annees(self):
        return (timezone.now().date() - self.date_embauche).days // 365


class AffectationHistorique(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='historique_affectations')
    site = models.ForeignKey('sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True)
    departement = models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, blank=True)
    poste = models.ForeignKey(Poste, on_delete=models.SET_NULL, null=True, blank=True)
    unite = models.ForeignKey('sites_rh.Unite', on_delete=models.SET_NULL, null=True, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    motif = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historique affectation'
        verbose_name_plural = 'Historiques affectations'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.employe} → {self.site} ({self.date_debut})"
