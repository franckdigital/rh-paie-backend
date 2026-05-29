"""
python manage.py seed
python manage.py seed --flush   # vide toutes les tables avant de seeder
"""
from decimal import Decimal
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Alimente toutes les tables avec des données de démonstration'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Vider les tables avant de seeder')

    def handle(self, *args, **options):
        if options['flush']:
            self._flush()
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS('\n✅  Seed terminé avec succès !'))

    # ─────────────────────────────────────────────────────────────────────────
    def _flush(self):
        self.stdout.write(self.style.WARNING('⚠️  Vidage des tables...'))
        from carrieres.models import EvenementCarriere, RegleEvolutionCarriere
        from documents.models import Document, CategorieDocument
        from conges.models import DemandeConge, SoldeConge, TypeConge
        from paie.models import LigneBulletin, BulletinPaie, JournalPaie, ElementSalaire
        from heures.models import RecapHeures, ParametreHeures
        from presences.models import Presence, JourFerie, RapportPresence
        from pointage.models import Pointage, AnomaliePointage
        from planning.models import LignePlanning, MembreEquipe, PlanningMensuel, Equipe, RotationEquipe, TypeShift
        from employes.models import AffectationHistorique, Employe, Poste, FichePoste, Departement
        from sites_rh.models import Unite, Site
        from entreprises.models import Entreprise
        from users.models import User

        for model in [
            EvenementCarriere, RegleEvolutionCarriere,
            Document, CategorieDocument,
            DemandeConge, SoldeConge, TypeConge,
            LigneBulletin, BulletinPaie, JournalPaie, ElementSalaire,
            RecapHeures, ParametreHeures,
            Presence, JourFerie, RapportPresence,
            Pointage, AnomaliePointage,
            LignePlanning, MembreEquipe, PlanningMensuel, Equipe, RotationEquipe, TypeShift,
            AffectationHistorique, Employe, Poste, FichePoste, Departement,
            Unite, Site, Entreprise,
        ]:
            model.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING('Tables vidées.\n'))

    # ─────────────────────────────────────────────────────────────────────────
    def _seed(self):
        self._seed_users_superadmin()
        entreprise = self._seed_entreprise()
        sites      = self._seed_sites(entreprise)
        unites     = self._seed_unites(sites)
        depts      = self._seed_departements(sites)
        fiches     = self._seed_fiches_poste()
        postes     = self._seed_postes(depts, fiches)
        users      = self._seed_users(entreprise, sites)
        employes   = self._seed_employes(entreprise, sites, unites, depts, postes, users)
        self._seed_users_employe_link(users, employes)
        self._seed_shifts()
        self._seed_rotations()
        self._seed_equipes(sites, unites, employes)
        self._seed_types_conge()
        self._seed_soldes_conge(employes)
        self._seed_elements_salaire(entreprise)
        self._seed_jours_feries()
        self._seed_parametres_heures(entreprise)
        self._seed_categories_documents()
        self.stdout.write('')

    # ── Super admin ──────────────────────────────────────────────────────────
    def _seed_users_superadmin(self):
        from users.models import User
        u, created = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@securix.ci',
            'first_name': 'Super',
            'last_name': 'Admin',
            'role': 'super_admin',
            'is_staff': True,
            'is_superuser': True,
            'telephone': '+22500000000',
        })
        if created:
            u.set_password('Admin@2025!')
            u.save()
        self._log('👑', 'Super Admin', 'admin / Admin@2025!')

    # ── Entreprise ───────────────────────────────────────────────────────────
    def _seed_entreprise(self):
        from entreprises.models import Entreprise
        e, _ = Entreprise.objects.get_or_create(nom='SECURIX CI', defaults={
            'sigle': 'SECURIX',
            'secteur': 'securite',
            'telephone': '+22521000001',
            'email': 'contact@securix.ci',
            'adresse': 'Cocody Riviera 3, Abidjan',
            'ville': 'Abidjan',
            'pays': "Côte d'Ivoire",
        })
        self._log('🏢', 'Entreprise', e.nom)
        return e

    # ── Sites ─────────────────────────────────────────────────────────────────
    def _seed_sites(self, entreprise):
        from sites_rh.models import Site
        data = [
            dict(nom='Siège Social Abidjan',     code='SIEGE',    type_site='siege',           ville='Abidjan',
                 adresse='Plateau, Immeuble NSIA', latitude='5.3544', longitude='-4.0018', rayon_geofence=150),
            dict(nom='Site Yopougon',             code='YOP01',    type_site='poste_securite',  ville='Yopougon',
                 adresse='Yopougon Maroc',         latitude='5.3482', longitude='-4.0742', rayon_geofence=100),
            dict(nom='Site Koumassi',             code='KOU01',    type_site='poste_securite',  ville='Koumassi',
                 adresse='Koumassi Zone 4',        latitude='5.3197', longitude='-3.9832', rayon_geofence=100),
            dict(nom='Chantier Grand-Bassam',     code='BASS01',   type_site='chantier',        ville='Grand-Bassam',
                 adresse='Zone industrielle',      latitude='5.2007', longitude='-3.7353', rayon_geofence=200),
        ]
        sites = {}
        for d in data:
            code = d.pop('code')
            s, _ = Site.objects.get_or_create(code=code, defaults={'entreprise': entreprise, **d})
            sites[code] = s
            self._log('📍', 'Site', s.nom)
        return sites

    # ── Unités ────────────────────────────────────────────────────────────────
    def _seed_unites(self, sites):
        from sites_rh.models import Unite
        data = [
            ('SIEGE',  'Unité Administration',   'ADM',  'service'),
            ('SIEGE',  'Unité Sécurité Siège',   'SEC',  'equipe'),
            ('YOP01',  'Équipe A - Yopougon',    'YOPA', 'equipe'),
            ('YOP01',  'Équipe B - Yopougon',    'YOPB', 'equipe'),
            ('KOU01',  'Équipe A - Koumassi',    'KOUA', 'equipe'),
            ('BASS01', 'Équipe Chantier',        'BASC', 'equipe'),
        ]
        unites = {}
        for site_code, nom, code, type_u in data:
            u, _ = Unite.objects.get_or_create(site=sites[site_code], nom=nom, defaults={
                'code': code, 'type_unite': type_u,
            })
            unites[code] = u
        self._log('🔧', 'Unités', f'{len(unites)} créées')
        return unites

    # ── Départements ─────────────────────────────────────────────────────────
    def _seed_departements(self, sites):
        from employes.models import Departement
        data = [
            ('Ressources Humaines',   'RH',    'SIEGE'),
            ('Direction Générale',    'DG',    'SIEGE'),
            ('Opérations Sécurité',   'OPS',   'SIEGE'),
            ('Finance & Comptabilité','FIN',   'SIEGE'),
            ('Site Yopougon',         'OPS-Y', 'YOP01'),
            ('Site Koumassi',         'OPS-K', 'KOU01'),
            ('Site Grand-Bassam',     'OPS-B', 'BASS01'),
        ]
        depts = {}
        for nom, code, site_code in data:
            d, _ = Departement.objects.get_or_create(nom=nom, defaults={
                'code': code, 'site': sites[site_code],
            })
            depts[code] = d
        self._log('🏬', 'Départements', f'{len(depts)} créés')
        return depts

    # ── Fiches de poste ───────────────────────────────────────────────────────
    def _seed_fiches_poste(self):
        from employes.models import FichePoste
        data = [
            ('Directeur RH',              'directeur',    4),
            ('Responsable RH',            'responsable',  3),
            ('Gestionnaire Paie',         'chef_service', 3),
            ('Responsable de Site',       'responsable',  5),
            ('Superviseur Sécurité',      'superviseur',  3),
            ('Chef d\'Équipe',            'chef_equipe',  2),
            ('Agent de Sécurité',         'agent',        1),
            ('Agent de Sécurité Senior',  'technicien',   3),
            ('Secrétaire RH',             'agent',        1),
        ]
        fiches = {}
        for titre, niveau, exp in data:
            f, _ = FichePoste.objects.get_or_create(titre=titre, defaults={
                'niveau': niveau,
                'experience_min_annees': exp,
                'missions': f'Missions liées au poste de {titre}.',
            })
            fiches[titre] = f
        self._log('📋', 'Fiches de poste', f'{len(fiches)} créées')
        return fiches

    # ── Postes ────────────────────────────────────────────────────────────────
    def _seed_postes(self, depts, fiches):
        from employes.models import Poste
        data = [
            ('Directeur RH',             'RH',  'Directeur RH',             600000, 1200000),
            ('Responsable RH',           'RH',  'Responsable RH',           400000,  800000),
            ('Gestionnaire Paie',        'RH',  'Gestionnaire Paie',        300000,  600000),
            ('Secrétaire RH',            'RH',  'Secrétaire RH',            150000,  250000),
            ('Directeur Général',        'DG',  'Directeur RH',             800000, 2000000),
            ('Responsable de Site',      'OPS', 'Responsable de Site',      350000,  600000),
            ('Superviseur',              'OPS', 'Superviseur Sécurité',     250000,  400000),
            ("Chef d'Équipe",            'OPS', "Chef d'Équipe",            200000,  350000),
            ('Agent de Sécurité',        'OPS', 'Agent de Sécurité',        120000,  180000),
            ('Agent Senior',             'OPS', 'Agent de Sécurité Senior', 180000,  280000),
            ('Resp. Site Yopougon',      'OPS-Y', 'Responsable de Site',    350000,  550000),
            ('Resp. Site Koumassi',      'OPS-K', 'Responsable de Site',    350000,  550000),
            ('Resp. Site Grand-Bassam',  'OPS-B', 'Responsable de Site',    350000,  550000),
        ]
        postes = {}
        for titre, dept_code, fiche_titre, sal_min, sal_max in data:
            p, _ = Poste.objects.get_or_create(titre=titre, departement=depts[dept_code], defaults={
                'fiche_poste': fiches.get(fiche_titre),
                'salaire_min': Decimal(sal_min),
                'salaire_max': Decimal(sal_max),
            })
            postes[titre] = p
        self._log('💼', 'Postes', f'{len(postes)} créés')
        return postes

    # ── Utilisateurs (hors super admin) ──────────────────────────────────────
    def _seed_users(self, entreprise, sites):
        from users.models import User
        USERS = [
            # username, email, first_name, last_name, role, password, site_code, tel
            ('dg_kouassi',    'dg@securix.ci',            'Koffi',      'KOUASSI',    'dg',               'Dg@2025!',      'SIEGE',  '+22507110001'),
            ('drh_konan',     'drh@securix.ci',           'Adjoua',     'KONAN',      'drh',              'Drh@2025!',     'SIEGE',  '+22507110002'),
            ('rh_traore',     'rh@securix.ci',            'Seydou',     'TRAORÉ',     'responsable_rh',   'Rh@2025!',      'SIEGE',  '+22507110003'),
            ('paie_bamba',    'paie@securix.ci',          'Mamadou',    'BAMBA',      'gestionnaire_paie','Paie@2025!',    'SIEGE',  '+22507110004'),
            ('resp_yop',      'resp.yop@securix.ci',      'Yao',        'KOUAMÉ',     'responsable_site', 'Resp@2025!',    'YOP01',  '+22507110005'),
            ('resp_kou',      'resp.kou@securix.ci',      'Aya',        'DIALLO',     'responsable_site', 'Resp@2025!',    'KOU01',  '+22507110006'),
            ('sup_yao',       'sup@securix.ci',           'Amara',      'YAO',        'superviseur',      'Sup@2025!',     'YOP01',  '+22507110007'),
            ('chef_kouame',   'chef@securix.ci',          'Gilles',     'KOUAMÉ',     'chef_equipe',      'Chef@2025!',    'YOP01',  '+22507110008'),
            ('sec_rh',        'secretaire@securix.ci',    'Fatoumata',  'COULIBALY',  'secretaire_rh',    'Sec@2025!',     'SIEGE',  '+22507110009'),
        ]
        users = {}
        for username, email, first, last, role, pwd, site_code, tel in USERS:
            u, created = User.objects.get_or_create(username=username, defaults={
                'email': email,
                'first_name': first,
                'last_name': last,
                'role': role,
                'telephone': tel,
                'entreprise': entreprise,
                'site': sites[site_code],
            })
            if created:
                u.set_password(pwd)
                u.save()
            users[username] = u
            self._log('👤', f'{role}', f'{username} / {pwd}')
        return users

    # ── Employés ──────────────────────────────────────────────────────────────
    def _seed_employes(self, entreprise, sites, unites, depts, postes, users):
        from employes.models import Employe
        today = date.today()

        EMPLOYES = [
            # mat, nom, prenom, genre, ddn, tel, email, site, dept, poste, salaire, contrat, date_emb, unite
            ('E001', 'KOUASSI',   'Koffi',     'M', date(1975,3,15), '+22507210001', 'dg@securix.ci',         'SIEGE', 'DG',    'Directeur Général',        1500000, 'cdi', date(2010,1,2),  'ADM'),
            ('E002', 'KONAN',     'Adjoua',    'F', date(1982,7,20), '+22507210002', 'drh@securix.ci',         'SIEGE', 'RH',    'Directeur RH',              800000, 'cdi', date(2012,3,1),  'ADM'),
            ('E003', 'TRAORÉ',    'Seydou',    'M', date(1988,11,5), '+22507210003', 'rh@securix.ci',          'SIEGE', 'RH',    'Responsable RH',            500000, 'cdi', date(2015,6,15), 'ADM'),
            ('E004', 'BAMBA',     'Mamadou',   'M', date(1990,4,12), '+22507210004', 'paie@securix.ci',        'SIEGE', 'RH',    'Gestionnaire Paie',         350000, 'cdi', date(2017,2,1),  'ADM'),
            ('E005', 'COULIBALY', 'Fatoumata', 'F', date(1992,9,8),  '+22507210005', 'secretaire@securix.ci',  'SIEGE', 'RH',    'Secrétaire RH',             180000, 'cdi', date(2019,4,1),  'ADM'),
            ('E006', 'KOUAMÉ',    'Yao',       'M', date(1985,2,28), '+22507210006', 'resp.yop@securix.ci',    'YOP01', 'OPS-Y', 'Resp. Site Yopougon',       450000, 'cdi', date(2014,8,1),  'YOPA'),
            ('E007', 'DIALLO',    'Aya',       'F', date(1987,6,3),  '+22507210007', 'resp.kou@securix.ci',    'KOU01', 'OPS-K', 'Resp. Site Koumassi',       450000, 'cdi', date(2013,5,15), 'KOUA'),
            ('E008', 'YAO',       'Amara',     'M', date(1991,1,17), '+22507210008', 'sup@securix.ci',         'YOP01', 'OPS-Y', 'Superviseur',               280000, 'cdi', date(2018,9,1),  'YOPA'),
            ('E009', 'KOUAMÉ',    'Gilles',    'M', date(1993,8,22), '+22507210009', 'chef@securix.ci',        'YOP01', 'OPS-Y', "Chef d'Équipe",             230000, 'cdi', date(2019,11,1), 'YOPA'),
            ('E010', 'GBAGBO',    'Serge',     'M', date(1995,5,10), '+22507210010', 'agent1@securix.ci',      'YOP01', 'OPS-Y', 'Agent de Sécurité',         145000, 'cdi', date(2020,1,15), 'YOPA'),
            ('E011', 'N\'GORAN',  'Alice',     'F', date(1996,3,25), '+22507210011', 'agent2@securix.ci',      'YOP01', 'OPS-Y', 'Agent de Sécurité',         145000, 'cdi', date(2020,3,1),  'YOPB'),
            ('E012', 'TOURÉ',     'Ibrahim',   'M', date(1994,12,1), '+22507210012', 'agent3@securix.ci',      'YOP01', 'OPS-Y', 'Agent de Sécurité',         145000, 'cdi', date(2020,5,1),  'YOPB'),
            ('E013', 'KONE',      'Mariam',    'F', date(1997,7,14), '+22507210013', 'agent4@securix.ci',      'KOU01', 'OPS-K', 'Agent de Sécurité',         145000, 'cdi', date(2021,2,1),  'KOUA'),
            ('E014', 'OUÉDRAOGO', 'Luc',       'M', date(1993,10,30),'+22507210014', 'agent5@securix.ci',      'KOU01', 'OPS-K', 'Agent de Sécurité',         145000, 'cdi', date(2021,4,1),  'KOUA'),
            ('E015', 'BALLO',     'Drissa',    'M', date(1990,6,18), '+22507210015', 'agent6@securix.ci',      'KOU01', 'OPS-K', 'Agent Senior',              200000, 'cdi', date(2016,7,1),  'KOUA'),
            ('E016', 'FOFANA',    'Issouf',    'M', date(1988,4,5),  '+22507210016', 'agent7@securix.ci',      'BASS01','OPS-B', 'Agent Senior',              200000, 'cdi', date(2015,3,1),  'BASC'),
            ('E017', 'DIABATÉ',   'Sita',      'F', date(1999,2,20), '+22507210017', 'agent8@securix.ci',      'BASS01','OPS-B', 'Agent de Sécurité',         145000, 'cdd', date(2023,1,15), 'BASC'),
            ('E018', 'SORO',      'Lacina',    'M', date(1998,9,9),  '+22507210018', 'agent9@securix.ci',      'BASS01','OPS-B', 'Agent de Sécurité',         145000, 'cdd', date(2023,6,1),  'BASC'),
        ]

        employes = {}
        user_map = {
            'E001': 'dg_kouassi',
            'E002': 'drh_konan',
            'E003': 'rh_traore',
            'E004': 'paie_bamba',
            'E005': 'sec_rh',
            'E006': 'resp_yop',
            'E007': 'resp_kou',
            'E008': 'sup_yao',
            'E009': 'chef_kouame',
        }

        for row in EMPLOYES:
            mat, nom, prenom, genre, ddn, tel, email, site_code, dept_code, poste_titre, salaire, contrat, emb, unite_code = row
            linked_user = users.get(user_map.get(mat))
            emp, _ = Employe.objects.get_or_create(matricule=mat, defaults={
                'nom': nom, 'prenom': prenom, 'genre': genre,
                'date_naissance': ddn, 'telephone': tel, 'email': email,
                'entreprise': entreprise,
                'site': sites[site_code],
                'unite': unites.get(unite_code),
                'departement': depts.get(dept_code),
                'poste': postes.get(poste_titre),
                'salaire_base': Decimal(salaire),
                'type_contrat': contrat,
                'date_embauche': emb,
                'statut': 'actif',
                'nationalite': "Ivoirienne",
                'user': linked_user,
            })
            employes[mat] = emp

        self._log('👷', 'Employés', f'{len(employes)} créés')
        return employes

    def _seed_users_employe_link(self, users, employes):
        """Crée les comptes utilisateur pour les agents de terrain."""
        from users.models import User
        from employes.models import Employe

        AGENTS = [
            ('E010', 'agent_gbagbo',  'agent1@securix.ci', 'Serge',   'GBAGBO',  'employe', 'Agent@2025!', 'YOP01'),
            ('E011', 'agent_ngoran',  'agent2@securix.ci', 'Alice',   "N'GORAN", 'employe', 'Agent@2025!', 'YOP01'),
            ('E012', 'agent_toure',   'agent3@securix.ci', 'Ibrahim', 'TOURÉ',   'employe', 'Agent@2025!', 'YOP01'),
            ('E013', 'agent_kone',    'agent4@securix.ci', 'Mariam',  'KONÉ',    'employe', 'Agent@2025!', 'KOU01'),
            ('E014', 'agent_ouedrao', 'agent5@securix.ci', 'Luc',     'OUÉDRAOGO','employe','Agent@2025!', 'KOU01'),
            ('E015', 'agent_ballo',   'agent6@securix.ci', 'Drissa',  'BALLO',   'employe', 'Agent@2025!', 'KOU01'),
            ('E016', 'agent_fofana',  'agent7@securix.ci', 'Issouf',  'FOFANA',  'employe', 'Agent@2025!', 'BASS01'),
            ('E017', 'agent_diabate', 'agent8@securix.ci', 'Sita',    'DIABATÉ', 'employe', 'Agent@2025!', 'BASS01'),
            ('E018', 'agent_soro',    'agent9@securix.ci', 'Lacina',  'SORO',    'employe', 'Agent@2025!', 'BASS01'),
        ]
        from sites_rh.models import Site
        for mat, username, email, first, last, role, pwd, site_code in AGENTS:
            site = Site.objects.filter(code=site_code).first()
            u, created = User.objects.get_or_create(username=username, defaults={
                'email': email, 'first_name': first, 'last_name': last,
                'role': role, 'site': site,
            })
            if created:
                u.set_password(pwd)
                u.save()
            emp = employes.get(mat)
            if emp and emp.user is None:
                emp.user = u
                emp.save()
            self._log('🔑', 'Agent', f'{username} / {pwd}')

    # ── Shifts ────────────────────────────────────────────────────────────────
    def _seed_shifts(self):
        from planning.models import TypeShift
        SHIFTS = [
            ('Matin',    'M',  time(6, 0),  time(14, 0), False, False, Decimal('8'),  '#10b981'),
            ('Après-midi','S', time(14, 0), time(22, 0), False, False, Decimal('8'),  '#f59e0b'),
            ('Nuit',     'N',  time(22, 0), time(6, 0),  True,  True,  Decimal('8'),  '#6366f1'),
            ('Journée',  'J',  time(7, 30), time(16, 30),False, False, Decimal('8'),  '#3b82f6'),
            ('Garde 12h','G12',time(6, 0),  time(18, 0), False, False, Decimal('12'), '#8b5cf6'),
        ]
        for nom, code, debut, fin, minuit, nuit, duree, couleur in SHIFTS:
            TypeShift.objects.get_or_create(code=code, defaults={
                'nom': nom, 'heure_debut': debut, 'heure_fin': fin,
                'traverse_minuit': minuit, 'est_nuit': nuit,
                'duree_heures': duree, 'couleur': couleur,
            })
        self._log('⏰', 'Shifts', f'{len(SHIFTS)} créés')

    # ── Rotations ─────────────────────────────────────────────────────────────
    def _seed_rotations(self):
        from planning.models import RotationEquipe
        ROTATIONS = [
            ('3×8 Standard',   '3x8',  21),
            ('2×12 Chantier',  '2x12', 14),
            ('5j/8h Bureau',   '5j8h',  5),
        ]
        for nom, cycle, duree in ROTATIONS:
            RotationEquipe.objects.get_or_create(nom=nom, defaults={
                'type_cycle': cycle, 'duree_cycle_jours': duree,
            })
        self._log('🔄', 'Rotations', f'{len(ROTATIONS)} créées')

    # ── Équipes ────────────────────────────────────────────────────────────────
    def _seed_equipes(self, sites, unites, employes):
        from planning.models import Equipe, MembreEquipe, RotationEquipe
        rot_3x8 = RotationEquipe.objects.filter(type_cycle='3x8').first()
        EQUIPES = [
            ('Équipe A Yopougon', 'EQY-A', 'YOP01', 'YOPA', '#10b981', 'E009'),
            ('Équipe B Yopougon', 'EQY-B', 'YOP01', 'YOPB', '#f59e0b', None),
            ('Équipe A Koumassi', 'EQK-A', 'KOU01', 'KOUA', '#6366f1', None),
            ('Équipe Bassam',     'EQB-A', 'BASS01','BASC', '#ef4444', None),
        ]
        for nom, code, site_c, unite_c, couleur, chef_mat in EQUIPES:
            chef = employes.get(chef_mat) if chef_mat else None
            eq, _ = Equipe.objects.get_or_create(code=code, site=sites[site_c], defaults={
                'nom': nom,
                'unite': unites.get(unite_c),
                'rotation': rot_3x8,
                'chef_equipe': chef,
                'couleur': couleur,
            })
        self._log('👥', 'Équipes', f'{len(EQUIPES)} créées')

    # ── Types de congé ────────────────────────────────────────────────────────
    def _seed_types_conge(self):
        from conges.models import TypeConge
        TYPES = [
            ('Congé Annuel',        26, True),
            ('Congé Maladie',       30, True),
            ('Congé Maternité',     98, True),
            ('Congé Paternité',      3, True),
            ('Congé Sans Solde',    30, False),
            ('Congé Exceptionnel',   5, True),
            ('Récupération',        10, True),
        ]
        for nom, jours, paye in TYPES:
            TypeConge.objects.get_or_create(nom=nom, defaults={
                'nombre_jours': jours, 'est_paye': paye,
            })
        self._log('🌴', 'Types de congé', f'{len(TYPES)} créés')

    # ── Soldes congés initiaux ────────────────────────────────────────────────
    def _seed_soldes_conge(self, employes):
        from conges.models import TypeConge, SoldeConge
        conge_annuel = TypeConge.objects.filter(nom='Congé Annuel').first()
        if not conge_annuel:
            return
        annee = date.today().year
        count = 0
        for emp in employes.values():
            _, created = SoldeConge.objects.get_or_create(
                employe=emp, type_conge=conge_annuel, annee=annee,
                defaults={'jours_acquis': Decimal('26'), 'jours_pris': Decimal('0'), 'jours_restants': Decimal('26')},
            )
            if created:
                count += 1
        self._log('📅', 'Soldes congés', f'{count} créés')

    # ── Éléments salaire ──────────────────────────────────────────────────────
    def _seed_elements_salaire(self, entreprise):
        from paie.models import ElementSalaire
        ELEMENTS = [
            # nom, code, type, categorie, taux, montant, imposable, cnps, ordre
            ('Salaire de Base',          'SB',    'gain',    'salaire_base',  None,    None,  True,  True,  1),
            ('Indemnité de Transport',   'IT',    'gain',    'transport',     None,    30000, False, False, 2),
            ('Indemnité de Panier',      'IP',    'gain',    'panier',        None,    10000, False, False, 3),
            ('Prime de Rendement',       'PR',    'gain',    'prime',         None,    20000, True,  True,  4),
            ('Heures Supplémentaires 25%','HS25', 'gain',    'heure_supp',    Decimal('0.25'), None, True, True, 5),
            ('Heures Supplémentaires 50%','HS50', 'gain',    'heure_supp',    Decimal('0.50'), None, True, True, 6),
            ('Majoration Nuit (15%)',    'HN',    'gain',    'heure_nuit',    Decimal('0.15'), None, True, True, 7),
            ('CNPS Employé (3.2%)',      'CNPS_E','retenue', 'cnps',          Decimal('0.032'),None, False,False, 10),
            ('CMU (2 000 F)',            'CMU',   'retenue', 'cmu',           None,    2000,  False, False, 11),
            ('ITS/Impôt',                'ITS',   'retenue', 'impot',         None,    None,  False, False, 12),
            ('Absence Non Justifiée',    'ABS',   'retenue', 'absence',       None,    None,  False, False, 13),
            ('Avance sur Salaire',       'AVS',   'retenue', 'avance',        None,    None,  False, False, 14),
        ]
        for nom, code, typ, cat, taux, montant, imposable, cnps, ordre in ELEMENTS:
            ElementSalaire.objects.get_or_create(code=code, defaults={
                'entreprise': entreprise, 'nom': nom,
                'type': typ, 'categorie': cat,
                'taux': taux, 'montant_fixe': Decimal(montant) if montant else None,
                'est_imposable': imposable, 'est_soumis_cnps': cnps,
                'ordre_affichage': ordre, 'est_actif': True,
            })
        self._log('💰', 'Éléments salaire', f'{len(ELEMENTS)} créés')

    # ── Jours fériés CI ───────────────────────────────────────────────────────
    def _seed_jours_feries(self):
        from presences.models import JourFerie
        annee = date.today().year
        FERIES = [
            (date(annee, 1,  1),  "Jour de l'An"),
            (date(annee, 4, 21),  "Lundi de Pâques"),
            (date(annee, 5,  1),  "Fête du Travail"),
            (date(annee, 5, 29),  "Ascension"),
            (date(annee, 6,  9),  "Lundi de Pentecôte"),
            (date(annee, 8,  7),  "Fête Nationale"),
            (date(annee, 8, 15),  "Assomption"),
            (date(annee, 11, 1),  "Toussaint"),
            (date(annee, 11, 15), "Fête Nationale (Paix)"),
            (date(annee, 12, 25), "Noël"),
        ]
        count = 0
        for d, nom in FERIES:
            _, created = JourFerie.objects.get_or_create(date=d, defaults={
                'nom': nom, 'pays': 'CI', 'est_national': True,
            })
            if created:
                count += 1
        self._log('🎉', 'Jours fériés', f'{count} créés')

    # ── Paramètres heures ─────────────────────────────────────────────────────
    def _seed_parametres_heures(self, entreprise):
        from heures.models import ParametreHeures
        ParametreHeures.objects.get_or_create(entreprise=entreprise, defaults={
            'heures_normales_jour':     Decimal('8'),
            'heures_max_journalier':    Decimal('12'),
            'heure_debut_nuit':         time(22, 0),
            'heure_fin_nuit':           time(6,  0),
            'taux_majoration_nuit':     Decimal('15'),
            'taux_majoration_supp_25':  Decimal('25'),
            'taux_majoration_supp_50':  Decimal('50'),
            'taux_majoration_dimanche': Decimal('30'),
            'taux_majoration_ferie':    Decimal('100'),
            'tolerance_retard_minutes': 5,
        })
        self._log('⚙️', 'Paramètres heures', 'créés')

    # ── Catégories documents ──────────────────────────────────────────────────
    def _seed_categories_documents(self):
        from documents.models import CategorieDocument
        CATS = [
            ('Contrat de Travail',    'CONTRAT',  'file-text'),
            ('Bulletin de Paie',      'BULLETIN',  'dollar-sign'),
            ('Pièce d\'Identité',     'CNI',       'credit-card'),
            ('Diplôme',               'DIPLOME',   'award'),
            ('Attestation',           'ATTEST',    'check-square'),
            ('Certificat Médical',    'MED',       'activity'),
            ('Décision RH',           'DECISION',  'clipboard'),
        ]
        for nom, code, icone in CATS:
            CategorieDocument.objects.get_or_create(code=code, defaults={
                'nom': nom, 'icone': icone,
            })
        self._log('📁', 'Catégories documents', f'{len(CATS)} créées')

    # ── Helper ────────────────────────────────────────────────────────────────
    def _log(self, icon, label, info):
        self.stdout.write(f'  {icon}  {label:<30} {self.style.SUCCESS(str(info))}')
