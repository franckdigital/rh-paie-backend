from django.contrib import admin
from django.utils.html import format_html
from .models import Site, Unite


class UniteInline(admin.TabularInline):
    model = Unite
    extra = 0
    fields = ('nom', 'code', 'type_unite', 'responsable', 'capacite_max', 'est_actif')
    show_change_link = True


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'entreprise', 'type_site', 'ville', 'rayon_geofence', 'gps_badge', 'responsable', 'est_actif')
    list_filter = ('type_site', 'est_actif', 'entreprise')
    search_fields = ('nom', 'code', 'ville', 'adresse')
    list_per_page = 25
    readonly_fields = ('created_at',)
    inlines = [UniteInline]

    fieldsets = (
        ('Identification', {
            'fields': ('entreprise', 'nom', 'code', 'type_site', 'est_actif'),
        }),
        ('Localisation', {
            'fields': ('adresse', 'ville', 'latitude', 'longitude', 'rayon_geofence'),
        }),
        ('Responsable', {
            'fields': ('responsable', 'telephone'),
        }),
    )

    @admin.display(description='GPS configuré')
    def gps_badge(self, obj):
        if obj.latitude and obj.longitude:
            return format_html('<span style="color:#059669;font-weight:bold">✓ GPS</span>')
        return format_html('<span style="color:#dc2626">✗ Manquant</span>')


@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'site', 'type_unite', 'responsable', 'capacite_max', 'est_actif')
    list_filter = ('type_unite', 'est_actif', 'site__entreprise')
    search_fields = ('nom', 'code', 'site__nom')
    list_per_page = 25
