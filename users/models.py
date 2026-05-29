from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrateur'),
        ('dg', 'Directeur Général'),
        ('drh', 'Directeur RH'),
        ('responsable_rh', 'Responsable RH'),
        ('gestionnaire_paie', 'Gestionnaire Paie'),
        ('responsable_site', 'Responsable Site'),
        ('chef_unite', 'Chef Unité Production'),
        ('superviseur', 'Superviseur Sécurité'),
        ('chef_equipe', 'Chef Équipe'),
        ('secretaire_rh', 'Secrétaire RH'),
        ('employe', 'Employé / Agent'),
    ]
    PERMISSIONS_PAR_ROLE = {
        'super_admin': ['*'],
        'dg': ['dashboard.*', 'rapports.*', 'employes.view', 'paie.view', 'conges.view'],
        'drh': ['employes.*', 'conges.*', 'carrieres.*', 'documents.*', 'dashboard.rh'],
        'responsable_rh': ['employes.*', 'conges.*', 'documents.*'],
        'gestionnaire_paie': ['paie.*', 'heures.*', 'employes.view'],
        'responsable_site': ['pointage.*', 'planning.*', 'presences.*', 'employes.view'],
        'chef_unite': ['planning.*', 'presences.view', 'employes.view'],
        'superviseur': ['pointage.create', 'pointage.view', 'planning.view', 'employes.view', 'presences.view'],
        'chef_equipe': ['pointage.create', 'planning.view', 'presences.view', 'employes.view'],
        'secretaire_rh': ['employes.view', 'conges.view', 'documents.view'],
        'employe': ['pointage.create', 'pointage.view', 'profil.self', 'conges.self', 'bulletins.self', 'planning.self'],
    }

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='employe')
    # Rôle dynamique DB (prioritaire sur role CharField si défini)
    role_obj = models.ForeignKey(
        'roles.Role', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='utilisateurs',
        verbose_name='Rôle personnalisé',
    )
    telephone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='users/', blank=True, null=True)

    # Multi-entreprise : l'utilisateur est rattaché à une entreprise et un site
    entreprise = models.ForeignKey(
        'entreprises.Entreprise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='utilisateurs'
    )
    site = models.ForeignKey(
        'sites_rh.Site', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='utilisateurs'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def has_permission(self, permission):
        module, action = (permission.split('.') + ['*'])[:2]

        # Priorité au rôle dynamique DB
        if self.role_obj_id:
            from django.db.models import Q
            return self.role_obj.permissions.filter(
                Q(module='*', action='*') |
                Q(module=module, action__in=[action, '*'])
            ).exists()

        # Fallback : PERMISSIONS_PAR_ROLE statique
        role_perms = self.PERMISSIONS_PAR_ROLE.get(self.role, [])
        if '*' in role_perms:
            return True
        for perm in role_perms:
            p_module, p_action = (perm.split('.') + ['*'])[:2]
            if p_module in (module, '*') and p_action in (action, '*'):
                return True
        return False

    @property
    def role_label(self):
        if self.role_obj_id:
            return self.role_obj.label
        return self.get_role_display()

    @property
    def is_rh(self):
        return self.role in ('drh', 'responsable_rh', 'secretaire_rh', 'super_admin')

    @property
    def is_manager(self):
        return self.role in ('dg', 'drh', 'responsable_site', 'chef_unite', 'superviseur', 'chef_equipe', 'super_admin')

    @property
    def can_manage_payroll(self):
        return self.role in ('super_admin', 'drh', 'gestionnaire_paie')
