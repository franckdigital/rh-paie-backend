from django.db import models
from django.conf import settings
from employes.models import Employe


class ElementSalaire(models.Model):
    TYPE_CHOICES = [('gain', 'Gain'), ('retenue', 'Retenue')]
    CATEGORIE_CHOICES = [
        ('salaire_base', 'Salaire de base'),
        ('prime', 'Prime'),
        ('indemnite', 'Indemnité'),
        ('heure_supp', 'Heures supplémentaires'),
        ('heure_nuit', 'Heures de nuit'),
        ('heure_ferie', 'Heures fériées'),
        ('heure_dimanche', 'Heures dimanche'),
        ('transport', 'Transport'),
        ('panier', 'Panier repas'),
        ('logement', 'Logement'),
        ('conge_paye', 'Congé payé'),
        ('cnps', 'CNPS'),
        ('impot', 'Impôt (ITS/IRPP)'),
        ('cmu', 'CMU'),
        ('absence', 'Déduction absence'),
        ('avance', 'Avance sur salaire'),
        ('autre', 'Autre'),
    ]
    entreprise = models.ForeignKey(
        'entreprises.Entreprise', on_delete=models.CASCADE, null=True, blank=True
    )
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    categorie = models.CharField(max_length=30, choices=CATEGORIE_CHOICES, default='autre')
    taux = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, help_text='% sur salaire base ou taux horaire')
    montant_fixe = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    est_imposable = models.BooleanField(default=True)
    est_soumis_cnps = models.BooleanField(default=True)
    est_actif = models.BooleanField(default=True)
    ordre_affichage = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Élément de salaire'
        verbose_name_plural = 'Éléments de salaire'
        ordering = ['ordre_affichage', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.type})"


class BulletinPaie(models.Model):
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('paye', 'Payé'),
        ('annule', 'Annulé'),
    ]
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='bulletins')
    periode_debut = models.DateField()
    periode_fin = models.DateField()

    # Salaire de base
    salaire_base = models.DecimalField(max_digits=12, decimal_places=2)
    jours_travailles = models.IntegerField(default=26)
    jours_absents = models.IntegerField(default=0)
    deduction_absence = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Heures
    heures_normales = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_nuit = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_supp_25 = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_supp_50 = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_ferie = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    heures_dimanche = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    # Montants heures
    montant_heures_nuit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_heures_supp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_heures_ferie = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Totaux
    total_gains = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_retenues = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salaire_brut = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salaire_brut_imposable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salaire_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salaire_net_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Cotisations
    cotisation_cnps_employe = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cotisation_cnps_patronale = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    its = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='ITS/IRPP')
    cmu = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    date_paiement = models.DateField(null=True, blank=True)
    mode_paiement = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)

    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    recap_heures = models.OneToOneField(
        'heures.RecapHeures', on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bulletin de paie'
        verbose_name_plural = 'Bulletins de paie'
        unique_together = ('employe', 'periode_debut', 'periode_fin')
        ordering = ['-periode_fin']

    def __str__(self):
        return f"Bulletin {self.employe} — {self.periode_fin.strftime('%m/%Y')}"

    def _sync_prime_anciennete(self):
        """Crée ou met à jour la ligne prime d'ancienneté (1%/an, max 15%)."""
        from decimal import Decimal
        emp = self.employe
        if not emp.date_embauche or not self.periode_fin:
            return
        anciennete_ans = (self.periode_fin - emp.date_embauche).days / 365
        taux_anc = min(float(anciennete_ans) * 0.01, 0.15)
        montant_anc = round(float(self.salaire_base) * taux_anc, 2)
        if montant_anc <= 0:
            return
        elem_anc, _ = ElementSalaire.objects.get_or_create(
            code='PRIME_ANC',
            defaults={
                'nom': "Prime d'ancienneté", 'type': 'gain',
                'categorie': 'prime', 'est_imposable': True, 'est_soumis_cnps': True,
            }
        )
        LigneBulletin.objects.update_or_create(
            bulletin=self, element=elem_anc,
            defaults={
                'base': self.salaire_base,
                'taux': Decimal(str(round(taux_anc, 4))),
                'quantite': 1,
                'montant': Decimal(str(montant_anc)),
            }
        )

    def calculer_salaire_complet(self):
        """Calcul automatique du bulletin depuis les récaps d'heures."""
        # Ancienneté auto
        self._sync_prime_anciennete()

        taux_journalier = float(self.salaire_base) / 26
        taux_horaire = float(self.salaire_base) / (26 * 8)

        # Déduction absences
        self.deduction_absence = round(self.jours_absents * taux_journalier, 2)

        # Montants heures spéciales
        self.montant_heures_nuit = round(float(self.heures_nuit) * taux_horaire * 0.15, 2)
        self.montant_heures_supp = round(
            float(self.heures_supp_25) * taux_horaire * 0.25 +
            float(self.heures_supp_50) * taux_horaire * 0.50, 2
        )
        self.montant_heures_ferie = round(float(self.heures_ferie) * taux_horaire * 1.00, 2)

        # Gains des lignes (inclut maintenant prime ancienneté, transport, panier, etc.)
        gains_lignes = sum(
            float(l.montant) for l in self.lignes.filter(element__type='gain')
        )
        self.total_gains = round(
            gains_lignes + self.montant_heures_nuit + self.montant_heures_supp + self.montant_heures_ferie, 2
        )

        # Salaire brut
        self.salaire_brut = round(
            float(self.salaire_base) - float(self.deduction_absence) + float(self.total_gains), 2
        )
        self.salaire_brut_imposable = self.salaire_brut

        # Cotisations (taux Côte d'Ivoire)
        self.cotisation_cnps_employe = round(float(self.salaire_brut) * 0.036, 2)   # 3.6%
        self.cotisation_cnps_patronale = round(float(self.salaire_brut) * 0.16, 2)  # 16%
        self.cmu = round(float(self.salaire_brut) * 0.02, 2)                        # 2%

        # ITS (impôt barémique simplifié)
        base_its = float(self.salaire_brut_imposable) - float(self.cotisation_cnps_employe)
        self.its = self._calculer_its(base_its)

        retenues_lignes = sum(float(l.montant) for l in self.lignes.filter(element__type='retenue'))
        self.total_retenues = round(
            float(self.cotisation_cnps_employe) + float(self.its) + float(self.cmu) + retenues_lignes, 2
        )
        self.salaire_net = round(float(self.salaire_brut) - float(self.total_retenues), 2)
        self.salaire_net_paye = self.salaire_net
        self.save()

    @staticmethod
    def _calculer_its(base_mensuelle):
        """Barème ITS simplifié CI (annualisé / 12)."""
        base_annuelle = base_mensuelle * 12
        if base_annuelle <= 600000:
            its = 0
        elif base_annuelle <= 1500000:
            its = base_annuelle * 0.02
        elif base_annuelle <= 3000000:
            its = base_annuelle * 0.06
        elif base_annuelle <= 5000000:
            its = base_annuelle * 0.10
        elif base_annuelle <= 10000000:
            its = base_annuelle * 0.18
        else:
            its = base_annuelle * 0.25
        return round(its / 12, 2)


class LigneBulletin(models.Model):
    bulletin = models.ForeignKey(BulletinPaie, on_delete=models.CASCADE, related_name='lignes')
    element = models.ForeignKey(ElementSalaire, on_delete=models.PROTECT)
    base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taux = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    quantite = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    montant = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.element.nom}: {self.montant}"


class JournalPaie(models.Model):
    """Journal centralisé de toutes les paies d'une période."""
    entreprise = models.ForeignKey('entreprises.Entreprise', on_delete=models.CASCADE)
    periode_debut = models.DateField()
    periode_fin = models.DateField()
    bulletins = models.ManyToManyField(BulletinPaie, blank=True)
    total_salaires_bruts = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cotisations_patronales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_salaires_nets = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    nombre_bulletins = models.IntegerField(default=0)
    statut = models.CharField(
        max_length=20,
        choices=[('en_cours', 'En cours'), ('valide', 'Validé'), ('cloture', 'Clôturé')],
        default='en_cours'
    )
    cloture_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal de paie'
        verbose_name_plural = 'Journaux de paie'

    def __str__(self):
        return f"Journal paie {self.entreprise} {self.periode_fin.strftime('%m/%Y')}"
