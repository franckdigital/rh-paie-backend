from django.core.management.base import BaseCommand
from roles.models import Role, RolePermission

ROLES_CONFIG = {
    'super_admin': {
        'label': 'Super Administrateur',
        'couleur': '#ef4444',
        'description': 'Accès complet à toutes les fonctionnalités',
        'permissions': [('*', '*')],
    },
    'dg': {
        'label': 'Directeur Général',
        'couleur': '#7c3aed',
        'description': 'Lecture des tableaux de bord et rapports',
        'permissions': [
            ('dashboard', 'view'), ('rapports', 'view'),
            ('employes', 'view'), ('paie', 'view'), ('conges', 'view'),
        ],
    },
    'drh': {
        'label': 'Directeur RH',
        'couleur': '#2563eb',
        'description': 'Gestion complète des ressources humaines',
        'permissions': [
            ('employes', '*'), ('conges', '*'), ('carrieres', '*'),
            ('documents', '*'), ('dashboard', 'view'), ('rapports', 'view'),
            ('equipes', 'view'),
        ],
    },
    'responsable_rh': {
        'label': 'Responsable RH',
        'couleur': '#0891b2',
        'description': 'Gestion des employés et congés',
        'permissions': [
            ('employes', '*'), ('conges', '*'), ('documents', '*'),
            ('equipes', 'view'),
        ],
    },
    'gestionnaire_paie': {
        'label': 'Gestionnaire Paie',
        'couleur': '#059669',
        'description': 'Gestion de la paie et des heures',
        'permissions': [
            ('paie', '*'), ('heures', '*'), ('employes', 'view'),
        ],
    },
    'responsable_site': {
        'label': 'Responsable Site',
        'couleur': '#d97706',
        'description': 'Gestion du pointage et planning sur un site',
        'permissions': [
            ('pointage', '*'), ('planning', '*'), ('presences', '*'),
            ('employes', 'view'), ('equipes', '*'),
        ],
    },
    'chef_unite': {
        'label': "Chef d'Unité",
        'couleur': '#ea580c',
        'description': 'Gestion du planning et des présences',
        'permissions': [
            ('planning', '*'), ('presences', 'view'), ('employes', 'view'),
            ('equipes', 'view'), ('equipes', 'edit'),
        ],
    },
    'superviseur': {
        'label': 'Superviseur Sécurité',
        'couleur': '#0284c7',
        'description': 'Pointage et gestion de son équipe',
        'permissions': [
            ('pointage', 'create'), ('pointage', 'view'),
            ('planning', 'view'), ('employes', 'view'), ('presences', 'view'),
            ('equipes', 'view'), ('equipes', 'create'), ('equipes', 'edit'),
        ],
    },
    'chef_equipe': {
        'label': "Chef d'Équipe",
        'couleur': '#7c3aed',
        'description': "Gestion de l'équipe et du planning",
        'permissions': [
            ('pointage', 'create'), ('planning', 'view'),
            ('presences', 'view'), ('employes', 'view'),
            ('equipes', 'view'), ('equipes', 'edit'),
        ],
    },
    'secretaire_rh': {
        'label': 'Secrétaire RH',
        'couleur': '#be185d',
        'description': 'Consultation des données RH',
        'permissions': [
            ('employes', 'view'), ('conges', 'view'), ('documents', 'view'),
        ],
    },
    'employe': {
        'label': 'Employé / Agent',
        'couleur': '#64748b',
        'description': 'Accès à ses propres données uniquement',
        'permissions': [
            ('pointage', 'create'), ('pointage', 'self'),
            ('conges', 'self'), ('paie', 'self'), ('planning', 'self'),
        ],
    },
}


class Command(BaseCommand):
    help = 'Initialise les rôles système par défaut'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Réinitialiser les permissions des rôles système')

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        created_count = 0

        for code, cfg in ROLES_CONFIG.items():
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    'label':      cfg['label'],
                    'couleur':    cfg['couleur'],
                    'description': cfg['description'],
                    'is_systeme': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Créé: {role.label}')
            elif reset:
                role.permissions.all().delete()
                self.stdout.write(f'  ↺ Reset: {role.label}')

            if created or reset:
                for module, action in cfg['permissions']:
                    RolePermission.objects.get_or_create(role=role, module=module, action=action)

        self.stdout.write(self.style.SUCCESS(
            f'\n{created_count} rôle(s) créé(s), {len(ROLES_CONFIG)} rôles au total.'
        ))
        self.stdout.write(self.style.WARNING(
            '\nAssigner les rôles aux utilisateurs existants :\n'
            '  python manage.py shell -c "'
            'from roles.models import Role; from users.models import User; '
            '[u.update(role_obj=Role.objects.get(code=u.role)) for u in User.objects.filter(role_obj=None)]"'
        ))
