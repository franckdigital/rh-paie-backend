import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

TODAY = date(2026, 5, 28)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prev_month(d, n=1):
    m = d.month - n
    y = d.year + m // 12 if m <= 0 else d.year
    m = m % 12 or 12
    return date(y, m, 1)


def month_range(first_day):
    import calendar
    _, last = calendar.monthrange(first_day.year, first_day.month)
    return first_day, date(first_day.year, first_day.month, last)


class Command(BaseCommand):
    help = 'Seed complet — entreprise, RH, paie, présences, congés, documents, carrières'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('Démarrage du seed...'))

        entreprise = self._seed_entreprise()
        users_map = self._seed_users(entreprise)
        sites = self._seed_sites(entreprise, users_map)
        self._assign_users_sites(users_map, sites)
        unites = self._seed_unites(sites)
        deps, postes = self._seed_org(sites, users_map)
        employes = self._seed_employes(entreprise, sites, unites, deps, postes, users_map)
        self._link_equipe_chefs(users_map, employes)
        shifts = self._seed_shifts()
        equipes = self._seed_equipes(sites, unites, employes, shifts)
        self._seed_planning(sites, employes, shifts, equipes, users_map)
        self._seed_pointage_presences(employes, sites, shifts)
        self._seed_recaps_heures(employes)
        self._seed_paie(employes, entreprise, users_map)
        self._seed_conges(employes, users_map)
        self._seed_documents(employes, entreprise, users_map)
        self._seed_carrieres(employes, postes, sites, users_map)
        self._seed_jours_feries()
        self._seed_parametres_heures(entreprise)

        self.stdout.write(self.style.SUCCESS('Seed terminé avec succès !'))

    # -----------------------------------------------------------------------
    # Entreprise
    # -----------------------------------------------------------------------
    def _seed_entreprise(self):
        from entreprises.models import Entreprise
        ent, created = Entreprise.objects.get_or_create(
            nom='Sécurité Plus CI',
            defaults=dict(
                sigle='SPCI',
                secteur='securite',
                rccm='CI-ABJ-2018-B-12345',
                ncc='0123456789',
                telephone='+225 27 22 00 11 00',
                email='contact@securiteplus-ci.com',
                adresse='Rue du Commerce, Plateau',
                ville='Abidjan',
                pays="Côte d'Ivoire",
                est_actif=True,
            )
        )
        self.stdout.write(f'  Entreprise: {ent}')
        return ent

    # -----------------------------------------------------------------------
    # Utilisateurs
    # -----------------------------------------------------------------------
    def _seed_users(self, entreprise):
        users = {}

        specs = [
            ('admin',       'admin@secplus.ci',       'Admin',      'Système',    'super_admin',      'Admin123!'),
            ('drh',         'drh@secplus.ci',          'Koné',       'Béatrice',   'drh',              'Drh12345!'),
            ('paie',        'paie@secplus.ci',         'Bah',        'Moussa',     'gestionnaire_paie','Paie1234!'),
            ('resp_site1',  'rsite1@secplus.ci',       'Yao',        'Arsène',     'responsable_site', 'Site1234!'),
            ('resp_site2',  'rsite2@secplus.ci',       'Coulibaly',  'Awa',        'responsable_site', 'Site1234!'),
            ('sup1',        'sup1@secplus.ci',         'Traoré',     'Mamadou',    'superviseur',      'Sup12345!'),
            ('sup2',        'sup2@secplus.ci',         'Diomandé',   'Ibrahima',   'superviseur',      'Sup12345!'),
            ('chef1',       'chef1@secplus.ci',        'Bamba',      'Adama',      'chef_equipe',      'Chef1234!'),
            ('ag01',        'agent01@secplus.ci',      'Konan',      'Kouassi',    'employe',          'Agent123!'),
            ('ag02',        'agent02@secplus.ci',      'Yao',        'Akissi',     'employe',          'Agent123!'),
            ('ag03',        'agent03@secplus.ci',      "N'Goran",    'Kobenan',    'employe',          'Agent123!'),
            ('ag04',        'agent04@secplus.ci',      'Coulibaly',  'Seydou',     'employe',          'Agent123!'),
            ('ag05',        'agent05@secplus.ci',      'Ouattara',   'Fatoumata',  'employe',          'Agent123!'),
            ('ag06',        'agent06@secplus.ci',      'Assi',       'Jean-Marie', 'employe',          'Agent123!'),
            ('ag07',        'agent07@secplus.ci',      'Gbagbo',     'Henriette',  'employe',          'Agent123!'),
            ('ag08',        'agent08@secplus.ci',      'Kone',       'Aminata',    'employe',          'Agent123!'),
            ('ag09',        'agent09@secplus.ci',      'Cissé',      'Mariam',     'employe',          'Agent123!'),
            ('ag10',        'agent10@secplus.ci',      'Diarrassouba','Hamidou',   'employe',          'Agent123!'),
        ]

        for key, email, last, first, role, pwd in specs:
            u, created = User.objects.get_or_create(
                username=email,
                defaults=dict(
                    email=email,
                    first_name=first,
                    last_name=last,
                    role=role,
                    entreprise=entreprise,
                    is_active=True,
                    is_staff=(role == 'super_admin'),
                    is_superuser=(role == 'super_admin'),
                )
            )
            if created:
                u.set_password(pwd)
                u.save()
            users[key] = u

        self.stdout.write(f'  Utilisateurs: {len(users)}')
        return users

    def _assign_users_sites(self, users_map, sites):
        mapping = {
            'resp_site1': sites['siege'],
            'resp_site2': sites['sec01'],
            'sup1':       sites['sec01'],
            'sup2':       sites['sec02'],
            'chef1':      sites['usine'],
        }
        for key, site in mapping.items():
            u = users_map[key]
            if u.site != site:
                u.site = site
                u.save(update_fields=['site'])

    def _link_equipe_chefs(self, users_map, employes):
        # Superviseur users linked to supervisor employes
        for key, emp_key in [('sup1', 'sup1'), ('sup2', 'sup2'), ('chef1', 'chef1')]:
            u = users_map[key]
            emp = employes.get(emp_key)
            if emp and emp.user != u:
                emp.user = u
                # bypass full_clean for this update only
                from django.db.models import Model
                Model.save(emp, update_fields=['user'])

    # -----------------------------------------------------------------------
    # Sites
    # -----------------------------------------------------------------------
    def _seed_sites(self, entreprise, users_map):
        from sites_rh.models import Site
        specs = [
            ('siege',  'Siège Social Plateau',        'SIEGE', 'siege',          'Plateau, Abidjan',     5.3217,  -4.0228, 200),
            ('sec01',  'Poste Sécurité Cocody',        'SEC01', 'poste_securite', 'Cocody, Abidjan',      5.3560,  -3.9762, 150),
            ('sec02',  'Poste Sécurité Yopougon',      'SEC02', 'poste_securite', 'Zone Ind. Yopougon',   5.3297,  -4.0922, 150),
            ('usine',  'Site Usine Koumassi',          'USINE', 'usine',          'Zone Ind. Koumassi',   5.2897,  -3.9703, 300),
            ('entrt',  'Entrepôt Marcory',             'ENTRT', 'entrepot',       'Marcory, Abidjan',     5.2984,  -3.9968, 200),
        ]
        sites = {}
        for key, nom, code, type_site, adresse, lat, lon, rayon in specs:
            s, _ = Site.objects.get_or_create(
                code=code,
                defaults=dict(
                    entreprise=entreprise,
                    nom=nom,
                    type_site=type_site,
                    adresse=adresse,
                    ville='Abidjan',
                    latitude=Decimal(str(lat)),
                    longitude=Decimal(str(lon)),
                    rayon_geofence=rayon,
                    est_actif=True,
                )
            )
            sites[key] = s
        self.stdout.write(f'  Sites: {len(sites)}')
        return sites

    # -----------------------------------------------------------------------
    # Unités
    # -----------------------------------------------------------------------
    def _seed_unites(self, sites):
        from sites_rh.models import Unite
        specs = [
            ('siege',  'Service Administration',   'ADM',  'service'),
            ('siege',  'Service RH',               'RH',   'service'),
            ('sec01',  'Poste de Garde Cocody',    'PGC',  'poste_garde'),
            ('sec02',  'Poste de Garde Yopougon',  'PGY',  'poste_garde'),
            ('usine',  'Ligne Production A',       'LPA',  'ligne_production'),
            ('usine',  'Ligne Production B',       'LPB',  'ligne_production'),
            ('entrt',  'Zone Stockage',            'ZST',  'departement'),
        ]
        unites = {}
        for site_key, nom, code, type_unite in specs:
            site = sites[site_key]
            u, _ = Unite.objects.get_or_create(
                site=site,
                code=code,
                defaults=dict(nom=nom, type_unite=type_unite, capacite_max=20, est_actif=True)
            )
            unites[f'{site_key}_{code}'] = u
        self.stdout.write(f'  Unités: {len(unites)}')
        return unites

    # -----------------------------------------------------------------------
    # Départements, FichePoste, Postes
    # -----------------------------------------------------------------------
    def _seed_org(self, sites, users_map):
        from employes.models import Departement, FichePoste, Poste

        deps_specs = [
            ('securite',  'Sécurité & Gardiennage'),
            ('admin',     'Administration'),
            ('logistique','Logistique'),
            ('rh',        'Ressources Humaines'),
            ('direction', 'Direction Générale'),
        ]
        deps = {}
        for key, nom in deps_specs:
            d, _ = Departement.objects.get_or_create(
                nom=nom,
                defaults=dict(
                    site=sites.get('siege'),
                    description=f'Département {nom}',
                )
            )
            deps[key] = d

        fiches_specs = [
            ('agent_sec',   'Agent de sécurité',        'agent',       2, 'Surveillance et contrôle d\'accès'),
            ('sup_sec',     'Superviseur sécurité',      'superviseur', 3, 'Supervision des équipes de sécurité'),
            ('chef_eq',     'Chef d\'équipe',            'chef_equipe', 2, 'Management d\'équipe sur le terrain'),
            ('resp_rh',     'Responsable RH',            'responsable', 5, 'Gestion des ressources humaines'),
            ('gest_admin',  'Gestionnaire administratif','technicien',  2, 'Gestion administrative'),
            ('chauffeur',   'Chauffeur / Agent logistique','agent',     1, 'Transport et logistique'),
        ]
        fiches = {}
        for key, titre, niveau, exp, desc in fiches_specs:
            f, _ = FichePoste.objects.get_or_create(
                titre=titre,
                defaults=dict(
                    niveau=niveau,
                    missions=desc,
                    experience_min_annees=exp,
                    epi_requis='Tenue réglementaire, badge' if 'agent' in key or 'sup' in key or 'chef' in key else '',
                )
            )
            fiches[key] = f

        postes_specs = [
            ('agent_sec',   'Agent de Sécurité',           'securite',  'agent_sec',   75_000,  95_000),
            ('sup_sec',     'Superviseur Sécurité',         'securite',  'sup_sec',    120_000, 180_000),
            ('chef_eq',     'Chef d\'Équipe Sécurité',      'securite',  'chef_eq',    100_000, 140_000),
            ('resp_rh',     'Responsable Ressources Humaines','rh',      'resp_rh',    200_000, 350_000),
            ('gest_paie',   'Gestionnaire Paie',            'rh',        'gest_admin',  150_000, 220_000),
            ('gest_admin',  'Gestionnaire Administratif',   'admin',     'gest_admin',  130_000, 200_000),
            ('chauffeur',   'Chauffeur Logistique',         'logistique','chauffeur',    80_000, 110_000),
        ]
        postes = {}
        for key, titre, dep_key, fiche_key, sal_min, sal_max in postes_specs:
            p, _ = Poste.objects.get_or_create(
                titre=titre,
                departement=deps[dep_key],
                defaults=dict(
                    fiche_poste=fiches[fiche_key],
                    salaire_min=Decimal(str(sal_min)),
                    salaire_max=Decimal(str(sal_max)),
                )
            )
            postes[key] = p

        self.stdout.write(f'  Départements: {len(deps)}, Postes: {len(postes)}')
        return deps, postes

    # -----------------------------------------------------------------------
    # Employés
    # -----------------------------------------------------------------------
    def _seed_employes(self, entreprise, sites, unites, deps, postes, users_map):
        from employes.models import Employe

        specs = [
            # key, mat, nom, prenom, genre, ddn, tel, email, dep, poste, site_key, sal, contrat, embauche, user_key
            ('sup1',  'EMP001', 'Traoré',      'Mamadou Salifou', 'M', date(1985, 3, 12), '0701234501', 'sup1@secplus.ci',   'securite',  'sup_sec',   'sec01',  130_000, 'cdi', date(2018, 1, 15), 'sup1'),
            ('sup2',  'EMP002', 'Diomandé',    'Ibrahima Hamidou','M', date(1982, 7, 24), '0701234502', 'sup2@secplus.ci',   'securite',  'sup_sec',   'sec02',  135_000, 'cdi', date(2019, 3, 10), 'sup2'),
            ('chef1', 'EMP003', 'Bamba',       'Adama Mamadou',   'M', date(1988, 11, 5), '0701234503', 'chef1@secplus.ci',  'securite',  'chef_eq',   'usine',  110_000, 'cdi', date(2020, 6, 1),  'chef1'),
            ('resp_rh','EMP004','Cissé',       'Mariam Coulibaly','F', date(1979, 5, 18), '0701234504', 'ag09@secplus.ci',   'rh',        'resp_rh',   'siege',  220_000, 'cdi', date(2016, 9, 1),  'ag09'),
            ('gest',  'EMP005', 'Koné',        'Aminata Soro',    'F', date(1991, 8, 30), '0701234505', 'ag08@secplus.ci',   'rh',        'gest_paie', 'siege',  165_000, 'cdi', date(2021, 2, 15), 'ag08'),
            ('ag01',  'EMP006', 'Konan',       'Kouassi Brou',    'M', date(1994, 2, 20), '0701234506', 'agent01@secplus.ci','securite',  'agent_sec', 'sec01',   82_000, 'cdi', date(2022, 4, 1),  'ag01'),
            ('ag02',  'EMP007', 'Yao',         'Akissi Kouamé',   'F', date(1996, 6, 14), '0701234507', 'agent02@secplus.ci','securite',  'agent_sec', 'sec01',   80_000, 'cdd', date(2023, 1, 16), 'ag02'),
            ('ag03',  'EMP008', "N'Goran",     'Kobenan Yves',    'M', date(1993, 9, 3),  '0701234508', 'agent03@secplus.ci','securite',  'agent_sec', 'sec02',   82_000, 'cdi', date(2022, 7, 11), 'ag03'),
            ('ag04',  'EMP009', 'Coulibaly',   'Seydou Ibrahim',  'M', date(1990, 12, 8), '0701234509', 'agent04@secplus.ci','securite',  'agent_sec', 'sec02',   80_000, 'cdi', date(2021, 10, 3), 'ag04'),
            ('ag05',  'EMP010', 'Ouattara',    'Fatoumata Diallo','F', date(1997, 4, 25), '0701234510', 'agent05@secplus.ci','securite',  'agent_sec', 'usine',   80_000, 'cdd', date(2024, 1, 8),  'ag05'),
            ('ag06',  'EMP011', 'Assi',        'Jean-Marie Akpa', 'M', date(1992, 1, 17), '0701234511', 'agent06@secplus.ci','securite',  'agent_sec', 'usine',   82_000, 'cdi', date(2021, 5, 20), 'ag06'),
            ('ag07',  'EMP012', 'Gbagbo',      'Adjoa Henriette', 'F', date(1995, 10, 11),'0701234512', 'agent07@secplus.ci','securite',  'agent_sec', 'entrt',   80_000, 'cdi', date(2023, 3, 6),  'ag07'),
        ]

        employes = {}
        for key, mat, nom, prenom, genre, ddn, tel, email, dep_key, poste_key, site_key, sal, contrat, embauche, user_key in specs:
            user = users_map.get(user_key)
            emp, created = Employe.objects.get_or_create(
                matricule=mat,
                defaults=dict(
                    user=user,
                    nom=nom,
                    prenom=prenom,
                    genre=genre,
                    date_naissance=ddn,
                    telephone=tel,
                    email=email,
                    nationalite="Ivoirienne",
                    situation_familiale='marie' if genre == 'M' and sal > 100_000 else 'celibataire',
                    nombre_enfants=random.randint(0, 3),
                    entreprise=entreprise,
                    site=sites[site_key],
                    departement=deps[dep_key],
                    poste=postes[poste_key],
                    type_contrat=contrat,
                    date_embauche=embauche,
                    salaire_base=Decimal(str(sal)),
                    statut='actif',
                    mode_paiement='virement',
                    banque='SGBCI',
                    rib=f'CI{mat[-3:]}0000000000000{mat[-3:]}',
                )
            )
            employes[key] = emp
        self.stdout.write(f'  Employés: {len(employes)}')
        return employes

    # -----------------------------------------------------------------------
    # TypeShifts
    # -----------------------------------------------------------------------
    def _seed_shifts(self):
        from planning.models import TypeShift
        specs = [
            ('MATIN', 'Shift Matin',  time(6, 0),  time(18, 0), False, True,  Decimal('12'), '#f59e0b'),
            ('SOIR',  'Shift Soir',   time(14, 0), time(22, 0), False, False, Decimal('8'),  '#8b5cf6'),
            ('NUIT',  'Shift Nuit',   time(18, 0), time(6, 0),  True,  True,  Decimal('12'), '#1e40af'),
            ('JOUR8', 'Journée 8h',   time(8, 0),  time(17, 0), False, False, Decimal('8'),  '#10b981'),
        ]
        shifts = {}
        for code, nom, hdeb, hfin, traverse, est_nuit, duree, couleur in specs:
            s, _ = TypeShift.objects.get_or_create(
                code=code,
                defaults=dict(
                    nom=nom,
                    heure_debut=hdeb,
                    heure_fin=hfin,
                    traverse_minuit=traverse,
                    est_nuit=est_nuit,
                    duree_heures=duree,
                    couleur=couleur,
                )
            )
            shifts[code] = s
        self.stdout.write(f'  TypeShifts: {len(shifts)}')
        return shifts

    # -----------------------------------------------------------------------
    # Équipes
    # -----------------------------------------------------------------------
    def _seed_equipes(self, sites, unites, employes, shifts):
        from planning.models import RotationEquipe, Equipe

        rotation, _ = RotationEquipe.objects.get_or_create(
            nom='Rotation 3×8 Sécurité CI',
            defaults=dict(type_cycle='3x8', duree_cycle_jours=21,
                          description='Rotation triéquipe standard sécurité')
        )

        equipes_specs = [
            ('EQA', 'Équipe Alpha', sites['sec01'], '#ef4444', employes.get('sup1')),
            ('EQB', 'Équipe Bêta',  sites['sec02'], '#3b82f6', employes.get('sup2')),
            ('EQC', 'Équipe Gamma', sites['usine'], '#10b981', employes.get('chef1')),
        ]
        equipes = {}
        for code, nom, site, couleur, chef in equipes_specs:
            eq, _ = Equipe.objects.get_or_create(
                code=code,
                site=site,
                defaults=dict(
                    nom=nom,
                    rotation=rotation,
                    chef_equipe=chef,
                    couleur=couleur,
                    est_actif=True,
                )
            )
            equipes[code] = eq
        self.stdout.write(f'  Équipes: {len(equipes)}')
        return equipes

    # -----------------------------------------------------------------------
    # Planning mensuel + lignes
    # -----------------------------------------------------------------------
    def _seed_planning(self, sites, employes, shifts, equipes, users_map):
        from planning.models import PlanningMensuel, LignePlanning

        admin_user = users_map['admin']
        current_month_start = TODAY.replace(day=1)

        # Create plannings for 2 months: current and previous
        for month_offset in range(2):
            first = date(current_month_start.year, current_month_start.month, 1)
            if month_offset == 1:
                first = prev_month(first)
            _, last_day_num = __import__('calendar').monthrange(first.year, first.month)
            last = date(first.year, first.month, last_day_num)

            for site_key, site in sites.items():
                planning, _ = PlanningMensuel.objects.get_or_create(
                    site=site,
                    annee=first.year,
                    mois=first.month,
                    defaults=dict(statut='publie', cree_par=admin_user)
                )

                # Assign employees to sites
                site_employes = [e for e in employes.values() if e.site == site]
                # Also add supervisors from any site to cover all sites
                if not site_employes:
                    continue

                equipe_map = {
                    sites['sec01'].pk: equipes.get('EQA'),
                    sites['sec02'].pk: equipes.get('EQB'),
                    sites['usine'].pk: equipes.get('EQC'),
                }
                equipe = equipe_map.get(site.pk)
                shift = shifts['MATIN'] if site_key in ('sec01', 'sec02') else shifts['JOUR8']

                current_date = first
                while current_date <= last:
                    weekday = current_date.weekday()  # 0=Mon, 6=Sun
                    for emp in site_employes:
                        if weekday == 6:  # Sunday = repos
                            type_jour = 'repos'
                            shift_use = None
                        else:
                            type_jour = 'travail'
                            shift_use = shift
                        LignePlanning.objects.get_or_create(
                            planning=planning,
                            employe=emp,
                            date=current_date,
                            defaults=dict(
                                type_jour=type_jour,
                                shift=shift_use,
                                equipe=equipe,
                                site_affecte=site,
                            )
                        )
                    current_date += timedelta(days=1)

        self.stdout.write('  Planning mensuel + lignes créés')

    # -----------------------------------------------------------------------
    # Pointages + Présences (14 derniers jours)
    # -----------------------------------------------------------------------
    def _seed_pointage_presences(self, employes, sites, shifts):
        from pointage.models import Pointage
        from presences.models import Presence
        from django.utils import timezone as tz

        all_emps = list(employes.values())
        statuts_pool = ['present'] * 7 + ['retard'] * 2 + ['absent_non_justifie'] * 1

        for day_offset in range(14, 0, -1):
            d = TODAY - timedelta(days=day_offset)
            if d.weekday() == 6:
                continue  # skip Sunday

            for emp in all_emps:
                statut = random.choice(statuts_pool)
                site = emp.site
                shift = shifts['MATIN'] if site and site.type_site == 'poste_securite' else shifts['JOUR8']

                if statut == 'present':
                    heure_arrivee = time(6, random.randint(0, 5)) if shift.code == 'MATIN' else time(8, random.randint(0, 5))
                    heure_depart = time(18, random.randint(0, 10)) if shift.code == 'MATIN' else time(17, random.randint(0, 10))
                    retard = 0
                elif statut == 'retard':
                    heure_arrivee = time(6, random.randint(15, 45)) if shift.code == 'MATIN' else time(8, random.randint(15, 45))
                    heure_depart = time(18, random.randint(0, 10)) if shift.code == 'MATIN' else time(17, random.randint(0, 10))
                    retard = random.randint(15, 45)
                else:
                    # Absent — no pointage
                    Presence.objects.get_or_create(
                        employe=emp,
                        date=d,
                        defaults=dict(
                            statut='absent_non_justifie',
                            site=site,
                            shift=shift,
                            heures_travaillees=Decimal('0'),
                        )
                    )
                    continue

                # Entrée
                dt_entree = tz.make_aware(
                    __import__('datetime').datetime.combine(d, heure_arrivee)
                )
                pt_entree, _ = Pointage.objects.get_or_create(
                    employe=emp,
                    type_pointage='entree',
                    date_pointage=d,
                    defaults=dict(
                        mode='smartphone',
                        datetime_pointage=dt_entree,
                        site=site,
                        latitude=site.latitude,
                        longitude=site.longitude,
                        precision_gps=random.uniform(5.0, 25.0),
                        dans_geofence=True,
                        statut='valide',
                        shift_prevu=shift,
                    )
                )

                # Sortie
                dt_sortie = tz.make_aware(
                    __import__('datetime').datetime.combine(d, heure_depart)
                )
                pt_sortie, _ = Pointage.objects.get_or_create(
                    employe=emp,
                    type_pointage='sortie',
                    date_pointage=d,
                    defaults=dict(
                        mode='smartphone',
                        datetime_pointage=dt_sortie,
                        site=site,
                        latitude=site.latitude,
                        longitude=site.longitude,
                        precision_gps=random.uniform(5.0, 25.0),
                        dans_geofence=True,
                        statut='valide',
                        shift_prevu=shift,
                    )
                )

                heures_travaillees = Decimal(str(
                    round((dt_sortie - dt_entree).seconds / 3600, 2)
                ))

                Presence.objects.get_or_create(
                    employe=emp,
                    date=d,
                    defaults=dict(
                        statut=statut,
                        heure_arrivee=heure_arrivee,
                        heure_depart=heure_depart,
                        shift=shift,
                        site=site,
                        retard_minutes=retard,
                        heures_travaillees=heures_travaillees,
                        heures_nuit=Decimal('0'),
                        heures_supp=max(Decimal('0'), heures_travaillees - Decimal('8')),
                        pointage_entree=pt_entree,
                        pointage_sortie=pt_sortie,
                    )
                )

        self.stdout.write('  Pointages + Présences créés')

    # -----------------------------------------------------------------------
    # Récaps heures (2 mois passés)
    # -----------------------------------------------------------------------
    def _seed_recaps_heures(self, employes):
        from heures.models import RecapHeures

        for month_offset in range(1, 3):
            first = prev_month(TODAY.replace(day=1), month_offset)
            annee, mois = first.year, first.month
            for emp in employes.values():
                h_norm = Decimal(str(random.randint(170, 208)))
                h_nuit = Decimal(str(random.randint(0, 24)))
                h_supp25 = Decimal(str(random.randint(0, 12)))
                h_supp50 = Decimal(str(random.randint(0, 4)))
                jours_t = random.randint(22, 26)
                jours_a = random.randint(0, 2)

                recap, _ = RecapHeures.objects.get_or_create(
                    employe=emp,
                    annee=annee,
                    mois=mois,
                    defaults=dict(
                        heures_normales=h_norm,
                        heures_nuit=h_nuit,
                        heures_supp_25=h_supp25,
                        heures_supp_50=h_supp50,
                        heures_dimanche=Decimal('0'),
                        heures_ferie=Decimal('0'),
                        jours_travailles=jours_t,
                        jours_absents=jours_a,
                        jours_conge=0,
                        retards_count=random.randint(0, 3),
                        retards_minutes_total=random.randint(0, 60),
                        valide=month_offset == 2,  # older month is validated
                    )
                )
                recap.calculer_montants(emp.salaire_base)
                recap.save()

        self.stdout.write('  Récaps heures créés')

    # -----------------------------------------------------------------------
    # Éléments salaire + Bulletins de paie (3 mois)
    # -----------------------------------------------------------------------
    def _seed_paie(self, employes, entreprise, users_map):
        from paie.models import ElementSalaire, BulletinPaie, LigneBulletin, JournalPaie

        elements_specs = [
            ('PRIME_SEC',  'Prime de sécurité',       'gain',    'prime',       None,           Decimal('15000'), True,  True,  1),
            ('IND_TRANSP', 'Indemnité de transport',  'gain',    'transport',   None,           Decimal('15000'), False, False, 2),
            ('IND_LOG',    'Indemnité de logement',   'gain',    'logement',    None,           Decimal('20000'), False, False, 3),
            ('PANIER',     'Panier repas',            'gain',    'panier',      None,           Decimal('5000'),  False, False, 4),
            ('ANC',        'Prime d\'ancienneté',     'gain',    'prime',       Decimal('0.02'),None,            True,  True,  5),
        ]

        elements = {}
        for code, nom, typ, cat, taux, montant_fixe, imposable, cnps, ordre in elements_specs:
            el, _ = ElementSalaire.objects.get_or_create(
                code=code,
                entreprise=entreprise,
                defaults=dict(
                    nom=nom,
                    type=typ,
                    categorie=cat,
                    taux=taux,
                    montant_fixe=montant_fixe,
                    est_imposable=imposable,
                    est_soumis_cnps=cnps,
                    est_actif=True,
                    ordre_affichage=ordre,
                )
            )
            elements[code] = el

        admin_user = users_map['admin']

        for month_offset in range(1, 4):  # 3 months
            first = prev_month(TODAY.replace(day=1), month_offset)
            _, last_day_num = __import__('calendar').monthrange(first.year, first.month)
            last = date(first.year, first.month, last_day_num)
            annee, mois = first.year, first.month

            journals = {}

            for emp in employes.values():
                jours_abs = random.randint(0, 2)
                bulletin, created = BulletinPaie.objects.get_or_create(
                    employe=emp,
                    periode_debut=first,
                    periode_fin=last,
                    defaults=dict(
                        salaire_base=emp.salaire_base,
                        jours_travailles=26 - jours_abs,
                        jours_absents=jours_abs,
                        heures_normales=Decimal('208'),
                        heures_nuit=Decimal(str(random.randint(0, 24))),
                        heures_supp_25=Decimal(str(random.randint(0, 12))),
                        heures_supp_50=Decimal(str(random.randint(0, 4))),
                        statut='paye' if month_offset >= 2 else 'valide',
                        date_paiement=last if month_offset >= 2 else None,
                        mode_paiement='virement',
                        genere_par=admin_user,
                    )
                )

                if created:
                    # Lignes de gains
                    LigneBulletin.objects.create(
                        bulletin=bulletin,
                        element=elements['PRIME_SEC'],
                        base=emp.salaire_base,
                        taux=Decimal('0'),
                        quantite=Decimal('1'),
                        montant=Decimal('15000'),
                    )
                    LigneBulletin.objects.create(
                        bulletin=bulletin,
                        element=elements['IND_TRANSP'],
                        base=Decimal('0'),
                        taux=Decimal('0'),
                        quantite=Decimal('1'),
                        montant=Decimal('15000'),
                    )
                    # Ancienneté
                    anciennete = emp.anciennete_annees
                    if anciennete > 0:
                        montant_anc = round(float(emp.salaire_base) * 0.02 * min(anciennete, 10), 2)
                        LigneBulletin.objects.create(
                            bulletin=bulletin,
                            element=elements['ANC'],
                            base=emp.salaire_base,
                            taux=Decimal('0.02'),
                            quantite=Decimal(str(min(anciennete, 10))),
                            montant=Decimal(str(montant_anc)),
                        )
                    bulletin.calculer_salaire_complet()

                # Journal de paie
                journal_key = f'{annee}-{mois}'
                if journal_key not in journals:
                    journal, _ = JournalPaie.objects.get_or_create(
                        entreprise=entreprise,
                        periode_debut=first,
                        periode_fin=last,
                        defaults=dict(statut='cloture' if month_offset >= 2 else 'valide')
                    )
                    journals[journal_key] = journal
                journals[journal_key].bulletins.add(bulletin)

            # Update journal totals
            for journal in journals.values():
                bulletins_qs = journal.bulletins.all()
                journal.nombre_bulletins = bulletins_qs.count()
                journal.total_salaires_bruts = sum(b.salaire_brut for b in bulletins_qs)
                journal.total_cotisations_patronales = sum(b.cotisation_cnps_patronale for b in bulletins_qs)
                journal.total_salaires_nets = sum(b.salaire_net for b in bulletins_qs)
                journal.save(update_fields=[
                    'nombre_bulletins', 'total_salaires_bruts',
                    'total_cotisations_patronales', 'total_salaires_nets'
                ])

        self.stdout.write(f'  Bulletins de paie créés (3 mois × {len(employes)} employés)')

    # -----------------------------------------------------------------------
    # Congés
    # -----------------------------------------------------------------------
    def _seed_conges(self, employes, users_map):
        from conges.models import TypeConge, SoldeConge, DemandeConge

        types_specs = [
            ('Congé annuel payé',       18, True,  'Congé annuel légal CI (18 jours ouvrables)'),
            ('Congé maladie',           30, True,  'Congé pour raison médicale'),
            ('Congé de maternité',      98, True,  'Congé maternité 14 semaines (Code du travail CI)'),
            ('Congé sans solde',        30, False, 'Congé accordé sans maintien de salaire'),
            ('Récupération / repos compensateur', 7, True, 'Repos suite à heures supplémentaires'),
        ]
        types = {}
        for nom, jours, paye, desc in types_specs:
            tc, _ = TypeConge.objects.get_or_create(
                nom=nom,
                defaults=dict(nombre_jours=jours, est_paye=paye, description=desc)
            )
            types[nom] = tc

        annee = TODAY.year
        for emp in employes.values():
            for tc in types.values():
                jours_acquis = Decimal(str(tc.nombre_jours))
                jours_pris = Decimal(str(random.randint(0, min(5, int(tc.nombre_jours)))))
                SoldeConge.objects.get_or_create(
                    employe=emp,
                    type_conge=tc,
                    annee=annee,
                    defaults=dict(
                        jours_acquis=jours_acquis,
                        jours_pris=jours_pris,
                        jours_restants=jours_acquis - jours_pris,
                    )
                )

        drh_user = users_map['drh']
        type_annuel = types['Congé annuel payé']

        all_emps = list(employes.values())
        # Approved leave in the past
        for emp in all_emps[:4]:
            debut = date(annee, 2, 10)
            fin = date(annee, 2, 17)
            DemandeConge.objects.get_or_create(
                employe=emp,
                type_conge=type_annuel,
                date_debut=debut,
                defaults=dict(
                    date_fin=fin,
                    nombre_jours=6,
                    motif='Congé annuel planifié',
                    statut='approuve',
                    approuve_par=drh_user,
                    date_approbation=timezone.make_aware(
                        __import__('datetime').datetime(annee, 2, 1, 9, 0)
                    ),
                    commentaire_approbation='Approuvé selon planning annuel',
                )
            )

        # Pending leave (current month)
        for emp in all_emps[4:7]:
            debut = TODAY + timedelta(days=10)
            fin = debut + timedelta(days=4)
            DemandeConge.objects.get_or_create(
                employe=emp,
                type_conge=type_annuel,
                date_debut=debut,
                defaults=dict(
                    date_fin=fin,
                    nombre_jours=5,
                    motif='Congé familial',
                    statut='en_attente',
                )
            )

        # Refused leave
        emp_ref = all_emps[7]
        DemandeConge.objects.get_or_create(
            employe=emp_ref,
            type_conge=type_annuel,
            date_debut=date(annee, 3, 1),
            defaults=dict(
                date_fin=date(annee, 3, 10),
                nombre_jours=8,
                motif='Congé personnel',
                statut='refuse',
                approuve_par=drh_user,
                date_approbation=timezone.make_aware(
                    __import__('datetime').datetime(annee, 2, 25, 14, 0)
                ),
                commentaire_approbation='Effectif insuffisant sur le site durant cette période',
            )
        )

        self.stdout.write(f'  Congés créés ({len(types)} types, soldes + demandes)')

    # -----------------------------------------------------------------------
    # Documents
    # -----------------------------------------------------------------------
    def _seed_documents(self, employes, entreprise, users_map):
        from documents.models import CategorieDocument, Document

        cats_specs = [
            ('CNI',        'CNI / Passeport',              'id-card'),
            ('CONTRAT',    'Contrat de travail',            'file-text'),
            ('BULLETIN',   'Bulletin de paie',              'receipt'),
            ('ATTEST',     'Attestation de travail',        'award'),
            ('DIPLOME',    'Diplôme / Certificat',          'graduation-cap'),
            ('MEDICAL',    'Certificat médical',            'heart-pulse'),
            ('CV',         'CV / Curriculum Vitae',         'user'),
            ('FICHE_POSTE','Fiche de poste',                'briefcase'),
            ('SANCTION',   'Sanction disciplinaire',        'alert-triangle'),
            ('EVALUATION', 'Évaluation de performance',     'bar-chart-2'),
        ]
        cats = {}
        for code, nom, icone in cats_specs:
            c, _ = CategorieDocument.objects.get_or_create(
                code=code,
                defaults=dict(nom=nom, icone=icone)
            )
            cats[code] = c

        admin_user = users_map['admin']
        all_emps = list(employes.values())

        doc_templates = [
            ('CNI',     'Carte Nationale d\'Identité',  'application/pdf', False),
            ('CONTRAT', 'Contrat de travail CDI',       'application/pdf', True),
            ('ATTEST',  'Attestation de travail',       'application/pdf', False),
            ('DIPLOME', 'Diplôme BEP / Baccalauréat',  'application/pdf', False),
        ]

        dummy_pdf = b'%PDF-1.4 1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n%%EOF'

        for emp in all_emps:
            for cat_code, nom_doc, mime, confidentiel in doc_templates:
                doc_nom = f'{nom_doc} — {emp.prenom} {emp.nom}'
                if Document.objects.filter(employe=emp, categorie=cats[cat_code]).exists():
                    continue
                doc = Document(
                    employe=emp,
                    entreprise=entreprise,
                    categorie=cats[cat_code],
                    nom=doc_nom,
                    description=f'{nom_doc} de {emp.nom_complet}',
                    taille_fichier=len(dummy_pdf),
                    type_mime=mime,
                    statut='valide',
                    date_document=emp.date_embauche,
                    est_confidentiel=confidentiel,
                    ajoute_par=admin_user,
                )
                filename = f'{emp.matricule}_{cat_code.lower()}.pdf'
                doc.fichier.save(filename, ContentFile(dummy_pdf), save=False)
                doc.save()

        self.stdout.write(f'  Documents créés ({len(cats)} catégories)')

    # -----------------------------------------------------------------------
    # Carrières
    # -----------------------------------------------------------------------
    def _seed_carrieres(self, employes, postes, sites, users_map):
        from carrieres.models import EvenementCarriere

        admin_user = users_map['admin']
        drh_user = users_map['drh']

        all_emps = list(employes.items())  # (key, emp)

        for key, emp in all_emps:
            # Recrutement initial
            EvenementCarriere.objects.get_or_create(
                employe=emp,
                type_evenement='recrutement',
                date_evenement=emp.date_embauche,
                defaults=dict(
                    date_effet=emp.date_embauche,
                    description=f'Recrutement de {emp.nom_complet} au poste {emp.poste}',
                    poste_apres=emp.poste,
                    site_apres=emp.site,
                    salaire_apres=emp.salaire_base,
                    approuve_par=drh_user,
                )
            )

        # Promotions pour superviseurs et chefs
        promo_specs = [
            ('sup1',  'promotion',       'augmentation_salaire', date(2021, 7, 1),  date(2021, 7, 1),  'agent_sec', 'sup_sec',  100_000, 130_000),
            ('sup2',  'promotion',       'augmentation_salaire', date(2022, 1, 15), date(2022, 2, 1),  'agent_sec', 'sup_sec',  100_000, 135_000),
            ('chef1', 'changement_poste','augmentation_salaire', date(2023, 6, 1),  date(2023, 7, 1),  'agent_sec', 'chef_eq',   85_000, 110_000),
        ]
        for emp_key, type1, type2, date_ev, date_effet, poste_av, poste_ap, sal_av, sal_ap in promo_specs:
            emp = employes.get(emp_key)
            if not emp:
                continue
            EvenementCarriere.objects.get_or_create(
                employe=emp,
                type_evenement=type1,
                date_evenement=date_ev,
                defaults=dict(
                    date_effet=date_effet,
                    description=f'Promotion de {emp.nom_complet}',
                    poste_avant=postes.get(poste_av),
                    poste_apres=postes.get(poste_ap),
                    salaire_avant=Decimal(str(sal_av)),
                    salaire_apres=Decimal(str(sal_ap)),
                    approuve_par=drh_user,
                )
            )

        # Renouvellements CDD
        for key, emp in all_emps:
            if emp.type_contrat == 'cdd':
                EvenementCarriere.objects.get_or_create(
                    employe=emp,
                    type_evenement='renouvellement_contrat',
                    date_evenement=emp.date_embauche + timedelta(days=365),
                    defaults=dict(
                        date_effet=emp.date_embauche + timedelta(days=366),
                        description=f'Renouvellement CDD — {emp.nom_complet}',
                        salaire_avant=emp.salaire_base,
                        salaire_apres=emp.salaire_base,
                        approuve_par=drh_user,
                    )
                )

        # Évaluations annuelles
        for key, emp in random.sample(all_emps, min(6, len(all_emps))):
            EvenementCarriere.objects.get_or_create(
                employe=emp,
                type_evenement='evaluation',
                date_evenement=date(TODAY.year - 1, 12, 15),
                defaults=dict(
                    date_effet=date(TODAY.year - 1, 12, 15),
                    description=f'Évaluation annuelle {TODAY.year - 1} — résultat satisfaisant',
                    approuve_par=admin_user,
                )
            )

        self.stdout.write('  Événements carrière créés')

    # -----------------------------------------------------------------------
    # Jours fériés CI
    # -----------------------------------------------------------------------
    def _seed_jours_feries(self):
        from presences.models import JourFerie

        feries = [
            # 2025
            (date(2025, 1, 1),   "Jour de l'An"),
            (date(2025, 3, 31),  'Lundi de Pâques'),
            (date(2025, 5, 1),   'Fête du Travail'),
            (date(2025, 5, 29),  'Jeudi de l\'Ascension'),
            (date(2025, 6, 9),   'Lundi de Pentecôte'),
            (date(2025, 6, 6),   'Aïd el-Fitr (Korité)'),
            (date(2025, 8, 7),   'Fête Nationale'),
            (date(2025, 8, 15),  'Assomption'),
            (date(2025, 9, 5),   'Aïd el-Adha (Tabaski)'),
            (date(2025, 11, 1),  'Toussaint'),
            (date(2025, 11, 15), 'Fête de la Paix'),
            (date(2025, 12, 25), 'Noël'),
            # 2026
            (date(2026, 1, 1),   "Jour de l'An"),
            (date(2026, 4, 6),   'Lundi de Pâques'),
            (date(2026, 5, 1),   'Fête du Travail'),
            (date(2026, 5, 14),  "Jeudi de l'Ascension"),
            (date(2026, 5, 25),  'Lundi de Pentecôte'),
            (date(2026, 8, 7),   'Fête Nationale'),
            (date(2026, 8, 15),  'Assomption'),
            (date(2026, 11, 1),  'Toussaint'),
            (date(2026, 11, 15), 'Fête de la Paix'),
            (date(2026, 12, 25), 'Noël'),
        ]
        for d, nom in feries:
            JourFerie.objects.get_or_create(date=d, defaults=dict(nom=nom, pays='CI', est_national=True))

        self.stdout.write(f'  Jours fériés CI: {len(feries)}')

    # -----------------------------------------------------------------------
    # Paramètres heures
    # -----------------------------------------------------------------------
    def _seed_parametres_heures(self, entreprise):
        from heures.models import ParametreHeures
        ParametreHeures.objects.get_or_create(
            entreprise=entreprise,
            defaults=dict(
                heures_normales_jour=Decimal('8'),
                heures_max_journalier=Decimal('12'),
                heure_debut_nuit=time(22, 0),
                heure_fin_nuit=time(6, 0),
                taux_majoration_nuit=Decimal('15'),
                taux_majoration_supp_25=Decimal('25'),
                taux_majoration_supp_50=Decimal('50'),
                taux_majoration_dimanche=Decimal('30'),
                taux_majoration_ferie=Decimal('100'),
                tolerance_retard_minutes=5,
            )
        )
        self.stdout.write('  Paramètres heures créés')
