import math
from django.db import models
from django.conf import settings


def distance_metres(lat1, lon1, lat2, lon2):
    """Calcul distance Haversine en mètres."""
    R = 6371000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Pointage(models.Model):
    TYPE_CHOICES = [
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
    ]
    MODE_CHOICES = [
        ('smartphone', 'Smartphone agent'),
        ('tablette_superviseur', 'Tablette superviseur'),
        ('qrcode', 'QR Code'),
        ('biometrie', 'Biométrie'),
        ('manuel', 'Saisie manuelle'),
    ]
    STATUT_CHOICES = [
        ('valide', 'Valide'),
        ('anomalie', 'Anomalie'),
        ('en_attente', 'En attente validation'),
        ('rejete', 'Rejeté'),
    ]

    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='pointages')
    type_pointage = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mode = models.CharField(max_length=30, choices=MODE_CHOICES, default='smartphone')
    datetime_pointage = models.DateTimeField()
    date_pointage = models.DateField()

    # GPS
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    precision_gps = models.FloatField(null=True, blank=True, help_text='Précision GPS en mètres')
    site = models.ForeignKey('sites_rh.Site', on_delete=models.SET_NULL, null=True, blank=True)
    distance_du_site = models.FloatField(null=True, blank=True, help_text='Distance calculée au site en mètres')
    dans_geofence = models.BooleanField(default=True)

    # Anti-fraude
    device_id = models.CharField(max_length=200, blank=True)
    device_imei = models.CharField(max_length=100, blank=True)
    device_correspond = models.BooleanField(default=True, help_text='L\'appareil correspond au device enregistré')
    gps_mock_detecte = models.BooleanField(default=False)
    photo_selfie = models.ImageField(upload_to='pointages/selfies/', null=True, blank=True)

    # Validation superviseur
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='valide')
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pointages_valides'
    )
    anomalie_description = models.TextField(blank=True)

    # Contexte planning
    shift_prevu = models.ForeignKey(
        'planning.TypeShift', on_delete=models.SET_NULL, null=True, blank=True
    )
    ligne_planning = models.ForeignKey(
        'planning.LignePlanning', on_delete=models.SET_NULL, null=True, blank=True
    )

    # Superviseur qui a pointé pour cet agent (mode superviseur)
    pointe_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pointages_effectues'
    )
    note_superviseur = models.TextField(blank=True, help_text='Note justificative du superviseur')

    # Correction horaire par admin
    datetime_correction = models.DateTimeField(null=True, blank=True, help_text='Heure corrigée par admin')
    note_correction = models.TextField(blank=True)
    correction_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='corrections_effectuees'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pointage'
        verbose_name_plural = 'Pointages'
        ordering = ['-datetime_pointage']
        indexes = [
            models.Index(fields=['employe', 'date_pointage']),
            models.Index(fields=['site', 'date_pointage']),
        ]

    def __str__(self):
        return f"{self.employe} — {self.type_pointage} {self.datetime_pointage.strftime('%d/%m/%Y %H:%M')}"

    def calculer_distance_site(self):
        if self.site and self.latitude and self.longitude and self.site.latitude and self.site.longitude:
            self.distance_du_site = distance_metres(
                self.latitude, self.longitude,
                self.site.latitude, self.site.longitude
            )
            self.dans_geofence = self.distance_du_site <= self.site.rayon_geofence
        return self.distance_du_site

    def verifier_device(self):
        employe = self.employe
        if employe.device_id and self.device_id:
            self.device_correspond = (employe.device_id == self.device_id)
        return self.device_correspond

    def detecter_anomalies(self):
        anomalies = []
        if not self.dans_geofence:
            anomalies.append(f"Hors zone géographique ({self.distance_du_site:.0f}m du site)")
        if not self.device_correspond:
            anomalies.append("Appareil non reconnu")
        if self.gps_mock_detecte:
            anomalies.append("GPS simulé détecté")
        if self.precision_gps and self.precision_gps > 200:
            anomalies.append(f"Précision GPS faible ({self.precision_gps:.0f}m)")
        if anomalies:
            self.statut = 'anomalie'
            self.anomalie_description = ' | '.join(anomalies)
        return anomalies


class AnomaliePointage(models.Model):
    TYPE_CHOICES = [
        ('hors_zone', 'Hors zone GPS'),
        ('device_inconnu', 'Appareil inconnu'),
        ('gps_mock', 'GPS simulé'),
        ('double_pointage', 'Double pointage'),
        ('retard', 'Retard'),
        ('absence', 'Absence'),
        ('depart_anticipe', 'Départ anticipé'),
    ]
    STATUT_CHOICES = [
        ('non_traite', 'Non traité'),
        ('justifie', 'Justifié'),
        ('non_justifie', 'Non justifié'),
    ]
    pointage = models.ForeignKey(
        Pointage, on_delete=models.CASCADE, null=True, blank=True, related_name='anomalies'
    )
    employe = models.ForeignKey('employes.Employe', on_delete=models.CASCADE, related_name='anomalies_pointage')
    type_anomalie = models.CharField(max_length=30, choices=TYPE_CHOICES)
    date = models.DateField()
    description = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='non_traite')
    justification = models.TextField(blank=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anomalie pointage'
        verbose_name_plural = 'Anomalies pointage'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employe} — {self.type_anomalie} ({self.date})"
