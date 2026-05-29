from django.db import models

MODULES_CHOICES = [
    ('dashboard',     'Tableau de bord'),
    ('employes',      'Employés'),
    ('paie',          'Paie'),
    ('conges',        'Congés'),
    ('planning',      'Planning'),
    ('equipes',       'Équipes'),
    ('pointage',      'Pointage'),
    ('presences',     'Présences'),
    ('heures',        'Heures'),
    ('rapports',      'Rapports'),
    ('documents',     'Documents'),
    ('carrieres',     'Carrières'),
    ('sites',         'Sites'),
    ('entreprises',   'Entreprises'),
    ('users',         'Utilisateurs'),
    ('roles',         'Rôles'),
    ('notifications', 'Notifications'),
    ('*',             'Tous les modules'),
]

ACTIONS_CHOICES = [
    ('view',   'Voir'),
    ('create', 'Créer'),
    ('edit',   'Modifier'),
    ('delete', 'Supprimer'),
    ('self',   'Ses propres données'),
    ('*',      'Toutes les actions'),
]


class Role(models.Model):
    code        = models.CharField(max_length=50, unique=True)
    label       = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    couleur     = models.CharField(max_length=7, default='#6366f1')
    is_systeme  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['label']
        verbose_name = 'Rôle'
        verbose_name_plural = 'Rôles'

    def __str__(self):
        return self.label

    def has_permission(self, module, action):
        from django.db.models import Q
        return self.permissions.filter(
            Q(module='*', action='*') |
            Q(module=module, action__in=[action, '*'])
        ).exists()


class RolePermission(models.Model):
    role   = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    module = models.CharField(max_length=50, choices=MODULES_CHOICES)
    action = models.CharField(max_length=20, choices=ACTIONS_CHOICES)

    class Meta:
        unique_together     = ('role', 'module', 'action')
        verbose_name        = 'Permission de rôle'
        verbose_name_plural = 'Permissions de rôles'

    def __str__(self):
        return f"{self.role.code}: {self.module}.{self.action}"
