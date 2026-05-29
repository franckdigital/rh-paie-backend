"""
Acquisition mensuelle des congés payés : 2.5 jours par mois par employé actif.
À exécuter le 1er de chaque mois (cron ou tâche planifiée).

Usage :
    python manage.py acquerir_conges
    python manage.py acquerir_conges --mois 5 --annee 2026
    python manage.py acquerir_conges --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from employes.models import Employe
from conges.models import TypeConge, SoldeConge

JOURS_PAR_MOIS = 2.5  # Légal CI : 2.5j/mois = 30j/an


class Command(BaseCommand):
    help = 'Attribue 2.5 jours de congés payés à chaque employé actif pour le mois courant'

    def add_arguments(self, parser):
        today = timezone.localdate()
        parser.add_argument('--mois', type=int, default=today.month)
        parser.add_argument('--annee', type=int, default=today.year)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        mois = options['mois']
        annee = options['annee']
        dry_run = options['dry_run']

        self.stdout.write(f"Acquisition congés — {mois:02d}/{annee} ({'DRY-RUN' if dry_run else 'LIVE'})")

        # Récupère ou crée le type "Congé payé"
        type_cp, _ = TypeConge.objects.get_or_create(
            nom='Congé payé',
            defaults={'nombre_jours': 30, 'est_paye': True, 'description': 'Congé légal CI : 30j/an'},
        )

        employes_actifs = Employe.objects.filter(statut='actif')
        maj = 0
        crees = 0

        for emp in employes_actifs:
            # Vérifie que l'employé était présent ce mois-là (embauche ≤ fin du mois)
            from calendar import monthrange
            last_day = monthrange(annee, mois)[1]
            from datetime import date
            fin_mois = date(annee, mois, last_day)
            if emp.date_embauche > fin_mois:
                continue  # Pas encore embauché ce mois

            solde, created = SoldeConge.objects.get_or_create(
                employe=emp,
                type_conge=type_cp,
                annee=annee,
                defaults={'jours_acquis': 0, 'jours_pris': 0, 'jours_restants': 0},
            )

            # On ne cumule qu'une fois par mois : on vérifie si déjà attribué
            # La clé d'idempotence est : jours_acquis augmenté d'exactement JOURS_PAR_MOIS
            # Pour une vraie idempotence, il faudrait un log d'acquisitions mensuel.
            # Ici, on utilise une convention simple : si jours_acquis >= mois * 2.5, on saute.
            expected_acquis = mois * JOURS_PAR_MOIS
            if float(solde.jours_acquis) >= expected_acquis:
                self.stdout.write(f"  [SKIP] {emp} — déjà acquis pour ce mois")
                continue

            increment = JOURS_PAR_MOIS

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] +{increment}j → {emp}")
            else:
                from decimal import Decimal
                solde.jours_acquis = Decimal(str(float(solde.jours_acquis) + increment))
                solde.jours_restants = solde.jours_acquis - solde.jours_pris
                solde.save()

            if created:
                crees += 1
            else:
                maj += 1

        self.stdout.write(self.style.SUCCESS(
            f"Terminé : {crees} solde(s) créé(s), {maj} solde(s) mis à jour."
        ))
