from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime


@receiver(post_save, sender='pointage.AnomaliePointage')
def notifier_anomalie(sender, instance, created, **kwargs):
    """Envoie un email au responsable site lors de la création d'une anomalie."""
    if created:
        from config.emails import notifier_anomalie_pointage
        notifier_anomalie_pointage(instance)


@receiver(post_save, sender='pointage.Pointage')
def sync_presence(sender, instance, created, **kwargs):
    """
    Crée ou met à jour la Présence correspondante à chaque Pointage sauvegardé.
    - Pointage entrée → crée/met à jour Presence, calcule retard
    - Pointage sortie → met à jour heure_depart et recalcule heures
    """
    from presences.models import Presence

    employe = instance.employe
    date = instance.date_pointage

    if instance.type_pointage == 'entree':
        presence, _ = Presence.objects.get_or_create(
            employe=employe,
            date=date,
            defaults={
                'site': instance.site,
                'shift': instance.shift_prevu,
            },
        )

        heure_arrivee = (instance.datetime_correction or instance.datetime_pointage).astimezone(
            timezone.get_current_timezone()
        ).time()

        presence.heure_arrivee = heure_arrivee
        presence.pointage_entree = instance

        # Calcul retard si un shift est prévu
        shift = instance.shift_prevu or (presence.shift)
        if shift and shift.heure_debut:
            debut_prevu = datetime.combine(date, shift.heure_debut)
            debut_prevu = timezone.make_aware(debut_prevu, timezone.get_current_timezone())
            arrivee_dt = instance.datetime_correction or instance.datetime_pointage
            if arrivee_dt > debut_prevu:
                retard = int((arrivee_dt - debut_prevu).total_seconds() / 60)
                presence.retard_minutes = retard
                presence.statut = 'retard'
            else:
                presence.statut = 'present'
        else:
            presence.statut = 'present'

        presence.save()

    elif instance.type_pointage == 'sortie':
        try:
            presence = Presence.objects.get(employe=employe, date=date)
        except Presence.DoesNotExist:
            return

        heure_depart = (instance.datetime_correction or instance.datetime_pointage).astimezone(
            timezone.get_current_timezone()
        ).time()

        presence.heure_depart = heure_depart
        presence.pointage_sortie = instance
        presence.calculer_heures()
        presence.save()
