from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'get_full_name', 'role_badge', 'email', 'entreprise', 'site', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'entreprise', 'site')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telephone')
    ordering = ('last_name', 'first_name')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profil RH', {
            'fields': ('role', 'telephone', 'photo', 'entreprise', 'site'),
        }),
        ('Horodatage', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profil RH', {
            'fields': ('role', 'first_name', 'last_name', 'email', 'telephone', 'entreprise', 'site'),
        }),
    )

    ROLE_COLORS = {
        'super_admin': '#dc2626',
        'dg': '#7c3aed',
        'drh': '#2563eb',
        'responsable_rh': '#0891b2',
        'gestionnaire_paie': '#059669',
        'responsable_site': '#d97706',
        'chef_unite': '#ca8a04',
        'superviseur': '#65a30d',
        'chef_equipe': '#16a34a',
        'secretaire_rh': '#6b7280',
        'employe': '#9ca3af',
    }

    @admin.display(description='Rôle', ordering='role')
    def role_badge(self, obj):
        color = self.ROLE_COLORS.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_role_display()
        )
