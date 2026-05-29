from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime


@receiver(post_save, sender='planning.LignePlanning')
def recalculer_presence_apres_planning(sender, instance, **kwargs):
    """
    Quand une LignePlanning est créée ou modifiée, recalcule le retard et le statut
    de la Présence correspondante si l'employé a déjà pointé ce jour-là.
    """
    if not instance.shift:
        return
    from presences.models import Presence
    from django.utils import timezone as tz

    try:
        presence = Presence.objects.get(employe=instance.employe, date=instance.date)
    except Presence.DoesNotExist:
        return

    if not presence.calcul_automatique:
        return

    presence.shift = instance.shift

    if presence.heure_arrivee:
        arrivee_dt = datetime.combine(instance.date, presence.heure_arrivee)
        debut_dt = datetime.combine(instance.date, instance.shift.heure_debut)
        if arrivee_dt > debut_dt:
            delta_min = int((arrivee_dt - debut_dt).total_seconds() // 60)
            grace_min = 5
            presence.retard_minutes = delta_min
            presence.statut = 'retard' if delta_min > grace_min else 'present'
        else:
            presence.retard_minutes = 0
            presence.statut = 'present'
        presence.save(update_fields=['shift', 'retard_minutes', 'statut'])
    else:
        presence.save(update_fields=['shift'])
