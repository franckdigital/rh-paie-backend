"""
Commande à exécuter chaque matin (ex : cron 06h00).
Pour chaque employé actif, si aucune Présence n'existe pour hier,
crée une Présence avec statut='absent_non_justifie'.

Usage :
    python manage.py marquer_absents
    python manage.py marquer_absents --date 2026-05-27   # date manuelle
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from employes.models import Employe
from presences.models import Presence, JourFerie
from planning.models import LignePlanning


class Command(BaseCommand):
    help = 'Marque comme absents les employés sans pointage pour une date donnée'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Date à traiter (YYYY-MM-DD). Défaut : hier.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Affiche les absences sans les enregistrer.',
        )

    def handle(self, *args, **options):
        if options['date']:
            target_date = date.fromisoformat(options['date'])
        else:
            target_date = timezone.localdate() - timedelta(days=1)

        dry_run = options['dry_run']

        self.stdout.write(f"Traitement absences pour : {target_date}")

        # Jours fériés → on ne marque pas absent
        if JourFerie.objects.filter(date=target_date).exists():
            self.stdout.write(self.style.WARNING(f"{target_date} est un jour férié — aucun marquage."))
            return

        employes_actifs = Employe.objects.filter(statut='actif').select_related('site')

        created = 0
        skipped_repos = 0
        skipped_conge = 0

        for emp in employes_actifs:
            # Vérifie s'il y a déjà une Présence pour ce jour
            presence_exists = Presence.objects.filter(employe=emp, date=target_date).exists()
            if presence_exists:
                continue

            # Vérifie si le planning prévoit un jour de repos
            ligne = LignePlanning.objects.filter(employe=emp, date=target_date).first()
            if ligne and ligne.type_jour in ('repos', 'conge'):
                statut_auto = 'repos' if ligne.type_jour == 'repos' else 'conge'
                if not dry_run:
                    Presence.objects.create(
                        employe=emp,
                        date=target_date,
                        statut=statut_auto,
                        site=emp.site,
                        calcul_automatique=True,
                    )
                skipped_repos += 1
                continue

            # Pas de pointage, pas de repos planifié → absent
            if dry_run:
                self.stdout.write(f"  [DRY-RUN] Absent : {emp}")
            else:
                Presence.objects.create(
                    employe=emp,
                    date=target_date,
                    statut='absent_non_justifie',
                    site=emp.site,
                    calcul_automatique=True,
                )
            created += 1

        msg = (
            f"Terminé : {created} absent(s) marqué(s), "
            f"{skipped_repos} repos/congé planifié(s) sur {target_date}."
        )
        if dry_run:
            msg = f"[DRY-RUN] " + msg
        self.stdout.write(self.style.SUCCESS(msg))
