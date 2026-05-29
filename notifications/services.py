import logging
import requests
from .models import Notification, PushToken

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def creer_notification(user, titre, message, type='info', url=''):
    notif = Notification.objects.create(
        user=user, titre=titre, message=message, type=type, url=url
    )
    _envoyer_push(user, titre, message, data={'type': type, 'url': url})
    return notif


def creer_notification_masse(users, titre, message, type='info', url=''):
    notifications = [
        Notification(user=u, titre=titre, message=message, type=type, url=url)
        for u in users
    ]
    Notification.objects.bulk_create(notifications)
    for u in users:
        _envoyer_push(u, titre, message, data={'type': type, 'url': url})


def notifier_conge(demande, statut):
    employe_user = getattr(demande.employe, 'user', None)
    if not employe_user:
        return
    if statut == 'approuve':
        creer_notification(
            employe_user,
            '✅ Congé approuvé',
            f"Votre congé du {demande.date_debut} au {demande.date_fin} a été approuvé.",
            type='conge', url='/conges',
        )
    elif statut == 'refuse':
        creer_notification(
            employe_user,
            '❌ Congé refusé',
            f"Votre congé du {demande.date_debut} au {demande.date_fin} a été refusé.",
            type='conge', url='/conges',
        )


def notifier_bulletin(bulletin):
    employe_user = getattr(bulletin.employe, 'user', None)
    if not employe_user:
        return
    creer_notification(
        employe_user,
        '💰 Bulletin de paie disponible',
        f"Votre bulletin de {bulletin.periode_fin.strftime('%B %Y')} est prêt.",
        type='paie', url='/paie',
    )


def _envoyer_push(user, titre, message, data=None):
    tokens = list(
        PushToken.objects.filter(user=user, is_active=True).values_list('token', flat=True)
    )
    if not tokens:
        return
    messages = [
        {
            'to': t,
            'title': titre,
            'body': message,
            'sound': 'default',
            'data': data or {},
            'channelId': 'rh-paie',
        }
        for t in tokens
    ]
    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            timeout=8,
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Expo push failed for user {user.id}: {e}")
