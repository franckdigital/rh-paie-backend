from django.db import models
from django.conf import settings


class Presence(models.Model):
    STATUT_CHOICES = [
        ('present', 'Présent'),
        ('retard', 'Présent avec retard'),
        ('absent_justifie', 'Absent justifié'),
        ('absent_non_justifie', 'Absent non justifié'),
        ('conge', 'En congé'),
        ('maladie', 'Maladie'),
        ('mission', 'En mission'),
        ('permission', 'Permission'),
        ('formation', 'Formation'),
        ('ferie', 'Jour férié'),
        ('repos', 'Repos planifié'),
        ('suspension', 'Suspension'),
    ]
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='presences')
    date = models.DateField()
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='present')
    heure_arrivee = models.TimeField(null=True, blank=True)
    heure_depart = models.TimeField(null=True, blank=True)
    shift = models.ForeignKey('planning.TypeShift', on_delete=models.SET_NULL, null=True, blank=True)
    site = models.ForeignKey('sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True)

    # Calculs
    retard_minutes = models.IntegerField(default=0)
    depart_anticipe_minutes = models.IntegerField(default=0)
    heures_travaillees = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_nuit = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_supp = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Justification absence
    justification = models.TextField(blank=True)
    justifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Pointages liés
    pointage_entree = models.OneToOneField(
        'pointage.Pointage', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='presence_entree'
    )
    pointage_sortie = models.OneToOneField(
        'pointage.Pointage', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='presence_sortie'
    )

    calcul_automatique = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        unique_together = ('employe', 'date')
        ordering = ['-date', 'employe__nom']
        indexes = [
            models.Index(fields=['date', 'statut']),
            models.Index(fields=['employe', 'date']),
        ]

    def __str__(self):
        return f"{self.employe} — {self.date} ({self.statut})"

    def calculer_heures(self, heure_debut_nuit='18:00', heure_fin_nuit='06:00'):
        """Calcule heures travaillées, nuit et supp depuis les pointages."""
        if not (self.heure_arrivee and self.heure_depart):
            return
        from datetime import datetime, date, timedelta
        arrivee = datetime.combine(self.date, self.heure_arrivee)
        depart = datetime.combine(self.date, self.heure_depart)
        if depart <= arrivee:
            depart += timedelta(days=1)  # Shift traversant minuit
        total_minutes = (depart - arrivee).seconds // 60
        self.heures_travaillees = round(total_minutes / 60, 2)
        # Calcul heures nuit (22h-6h)
        debut_nuit = datetime.combine(self.date, datetime.strptime('22:00', '%H:%M').time())
        fin_nuit = datetime.combine(self.date + timedelta(days=1), datetime.strptime('06:00', '%H:%M').time())
        overlap_debut = max(arrivee, debut_nuit)
        overlap_fin = min(depart, fin_nuit)
        if overlap_fin > overlap_debut:
            self.heures_nuit = round((overlap_fin - overlap_debut).seconds / 3600, 2)
        # Heures supp (> 8h/jour)
        if float(self.heures_travaillees) > 8:
            self.heures_supp = round(float(self.heures_travaillees) - 8, 2)


class JourFerie(models.Model):
    date = models.DateField(unique=True)
    nom = models.CharField(max_length=100)
    pays = models.CharField(max_length=50, default="CI")
    est_national = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Jour férié'
        verbose_name_plural = 'Jours fériés'
        ordering = ['date']

    def __str__(self):
        return f"{self.nom} ({self.date})"


class RapportPresence(models.Model):
    PERIODE_CHOICES = [('jour', 'Journalier'), ('semaine', 'Hebdomadaire'), ('mois', 'Mensuel')]
    site = models.ForeignKey('sites_rh.Site', on_delete=models.CASCADE)
    periode = models.CharField(max_length=10, choices=PERIODE_CHOICES, default='mois')
    date_debut = models.DateField()
    date_fin = models.DateField()
    total_employes = models.IntegerField(default=0)
    presents = models.IntegerField(default=0)
    retards = models.IntegerField(default=0)
    absents_justifies = models.IntegerField(default=0)
    absents_non_justifies = models.IntegerField(default=0)
    taux_presence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    heures_nuit_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    heures_supp_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    genere_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Rapport de présence'
        verbose_name_plural = 'Rapports de présence'

    def __str__(self):
        return f"Rapport {self.site} {self.date_debut}→{self.date_fin}"
