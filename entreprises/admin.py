from django.contrib import admin
from django.utils.html import format_html
from .models import Entreprise


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('logo_thumb', 'nom', 'sigle', 'secteur', 'ville', 'telephone', 'nb_sites', 'est_actif')
    list_filter = ('secteur', 'est_actif', 'pays')
    search_fields = ('nom', 'sigle', 'rccm', 'ncc', 'email')
    list_per_page = 20
    readonly_fields = ('created_at', 'updated_at', 'logo_thumb')
    list_display_links = ('logo_thumb', 'nom')

    fieldsets = (
        ('Identité', {
            'fields': ('logo', 'logo_thumb', 'nom', 'sigle', 'secteur', 'est_actif'),
        }),
        ('Légal', {
            'fields': ('rccm', 'ncc'),
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'email', 'adresse', 'ville', 'pays'),
        }),
        ('Horodatage', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Logo')
    def logo_thumb(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height:36px;border-radius:4px" />', obj.logo.url)
        return '—'

    @admin.display(description='Sites')
    def nb_sites(self, obj):
        n = obj.sites.count()
        return format_html('<b>{}</b>', n) if n else '0'
