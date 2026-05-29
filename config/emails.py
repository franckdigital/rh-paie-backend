from django.core.mail import send_mail
from django.conf import settings


def _send(subject, message, recipients):
    """Wrapper silencieux — n'interrompt pas le flux si le serveur mail est absent."""
    if not recipients:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[r for r in recipients if r],
            fail_silently=True,
        )
    except Exception:
        pass


# ── Congés ────────────────────────────────────────────────────────────────────

def notifier_demande_conge(demande):
    """Alerte le responsable RH qu'une nouvelle demande de congé est en attente."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    rh_users = User.objects.filter(
        role__in=('drh', 'responsable_rh', 'super_admin'),
        is_active=True,
    ).values_list('email', flat=True)

    subject = f"[RH] Demande de congé — {demande.employe.nom_complet}"
    message = (
        f"Nouvelle demande de congé à traiter :\n\n"
        f"Employé  : {demande.employe.nom_complet} ({demande.employe.matricule})\n"
        f"Type     : {demande.type_conge.nom}\n"
        f"Période  : du {demande.date_debut} au {demande.date_fin} ({demande.nombre_jours} j)\n"
        f"Motif    : {demande.motif or '—'}\n\n"
        f"Connectez-vous à l'interface RH pour approuver ou refuser cette demande."
    )
    _send(subject, message, list(rh_users))


def notifier_decision_conge(demande):
    """Informe l'employé de la décision sur sa demande de congé."""
    if not demande.employe.email:
        return
    statut_label = 'APPROUVÉE' if demande.statut == 'approuve' else 'REFUSÉE'
    subject = f"[RH] Votre demande de congé a été {statut_label}"
    message = (
        f"Bonjour {demande.employe.prenom},\n\n"
        f"Votre demande de congé a été {statut_label} :\n\n"
        f"Type     : {demande.type_conge.nom}\n"
        f"Période  : du {demande.date_debut} au {demande.date_fin} ({demande.nombre_jours} j)\n"
        f"Décision : {statut_label}\n"
    )
    if demande.commentaire_approbation:
        message += f"Commentaire : {demande.commentaire_approbation}\n"
    message += "\nCordialement,\nLe service RH"
    _send(subject, message, [demande.employe.email])


# ── Anomalies pointage ────────────────────────────────────────────────────────

def notifier_anomalie_pointage(anomalie):
    """Alerte le responsable site et le superviseur d'une anomalie de pointage."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    site = anomalie.employe.site
    destinataires = list(
        User.objects.filter(
            role__in=('responsable_site', 'superviseur', 'super_admin'),
            site=site,
            is_active=True,
        ).values_list('email', flat=True)
    )

    subject = f"[Pointage] Anomalie détectée — {anomalie.employe.nom_complet}"
    message = (
        f"Une anomalie de pointage a été détectée :\n\n"
        f"Employé  : {anomalie.employe.nom_complet} ({anomalie.employe.matricule})\n"
        f"Site     : {site.nom if site else '—'}\n"
        f"Date     : {anomalie.date}\n"
        f"Type     : {anomalie.get_type_anomalie_display()}\n"
        f"Détail   : {anomalie.description}\n\n"
        f"Connectez-vous à l'interface de supervision pour traiter cette anomalie."
    )
    _send(subject, message, destinataires)


# ── Contrats expirant ─────────────────────────────────────────────────────────

def notifier_contrat_expirant(employe, jours_restants):
    """Alerte le DRH qu'un contrat expire dans N jours."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    rh_users = User.objects.filter(
        role__in=('drh', 'responsable_rh', 'super_admin'),
        is_active=True,
    ).values_list('email', flat=True)

    subject = f"[RH] Contrat expirant — {employe.nom_complet}"
    message = (
        f"Alerte expiration de contrat :\n\n"
        f"Employé        : {employe.nom_complet} ({employe.matricule})\n"
        f"Type contrat   : {employe.get_type_contrat_display()}\n"
        f"Date fin       : {employe.date_fin_contrat}\n"
        f"Jours restants : {jours_restants} j\n\n"
        f"Pensez à renouveler ou mettre fin au contrat."
    )
    _send(subject, message, list(rh_users))
