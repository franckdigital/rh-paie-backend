from django.contrib import admin
from django.utils.html import format_html
from .models import Pointage, AnomaliePointage


@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'date_pointage', 'type_badge', 'mode_badge', 'heure_col',
        'statut_badge', 'gps_col', 'selfie_thumb', 'pointe_par',
    )
    list_filter = ('type_pointage', 'mode', 'statut', 'date_pointage', 'site', 'dans_geofence', 'gps_mock_detecte')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    date_hierarchy = 'date_pointage'
    list_per_page = 40
    readonly_fields = (
        'created_at', 'distance_du_site', 'dans_geofence', 'device_correspond',
        'statut', 'anomalie_description', 'datetime_correction', 'correction_par',
    )

    fieldsets = (
        ('Pointage', {
            'fields': ('employe', 'type_pointage', 'mode', 'datetime_pointage', 'date_pointage', 'statut'),
        }),
        ('GPS & Géofencing', {
            'fields': ('latitude', 'longitude', 'precision_gps', 'site', 'distance_du_site', 'dans_geofence'),
        }),
        ('Anti-fraude', {
            'fields': ('device_id', 'device_imei', 'device_correspond', 'gps_mock_detecte', 'photo_selfie'),
        }),
        ('Supervision', {
            'fields': ('valide_par', 'anomalie_description', 'pointe_par', 'note_superviseur'),
            'classes': ('collapse',),
        }),
        ('Correction admin', {
            'fields': ('datetime_correction', 'note_correction', 'correction_par'),
            'classes': ('collapse',),
        }),
        ('Contexte planning', {
            'fields': ('shift_prevu', 'ligne_planning'),
            'classes': ('collapse',),
        }),
    )

    actions = ['valider_selection', 'rejeter_selection']

    @admin.display(description='Type', ordering='type_pointage')
    def type_badge(self, obj):
        if obj.type_pointage == 'entree':
            return format_html('<span style="color:#059669;font-weight:700">↓ Entrée</span>')
        return format_html('<span style="color:#6b7280;font-weight:700">↑ Sortie</span>')

    @admin.display(description='Mode')
    def mode_badge(self, obj):
        icons = {
            'smartphone': '📱', 'tablette_superviseur': '📋',
            'qrcode': '📷', 'biometrie': '🔏', 'manuel': '✏️',
        }
        return f"{icons.get(obj.mode, '?')} {obj.get_mode_display()}"

    @admin.display(description='Heure')
    def heure_col(self, obj):
        dt = obj.datetime_correction or obj.datetime_pointage
        h = dt.strftime('%H:%M')
        if obj.datetime_correction:
            return format_html(
                '{} <span style="color:#d97706;font-size:10px">(corrigé)</span>', h
            )
        return h

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {
            'valide': '#059669', 'anomalie': '#dc2626',
            'en_attente': '#d97706', 'rejete': '#6b7280',
        }
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.display(description='GPS')
    def gps_col(self, obj):
        if not obj.latitude:
            return '—'
        if obj.dans_geofence:
            return format_html('<span style="color:#059669">✓ {:.0f}m</span>', obj.distance_du_site or 0)
        return format_html('<span style="color:#dc2626">✗ {:.0f}m</span>', obj.distance_du_site or 0)

    @admin.display(description='Selfie')
    def selfie_thumb(self, obj):
        if obj.photo_selfie:
            return format_html('<img src="{}" style="height:32px;border-radius:4px" />', obj.photo_selfie.url)
        return '—'

    @admin.action(description='Valider les pointages sélectionnés')
    def valider_selection(self, request, queryset):
        n = queryset.update(statut='valide', valide_par=request.user)
        self.message_user(request, f"{n} pointage(s) validé(s).")

    @admin.action(description='Rejeter les pointages sélectionnés')
    def rejeter_selection(self, request, queryset):
        n = queryset.update(statut='rejete')
        self.message_user(request, f"{n} pointage(s) rejeté(s).")


@admin.register(AnomaliePointage)
class AnomaliePointageAdmin(admin.ModelAdmin):
    list_display = ('employe', 'date', 'type_anomalie_badge', 'description', 'statut_badge', 'traite_par')
    list_filter = ('type_anomalie', 'statut', 'date')
    search_fields = ('employe__nom', 'employe__prenom', 'description')
    date_hierarchy = 'date'
    list_per_page = 30
    readonly_fields = ('created_at',)
    actions = ['justifier', 'marquer_non_justifie']

    @admin.display(description='Type anomalie', ordering='type_anomalie')
    def type_anomalie_badge(self, obj):
        colors = {
            'hors_zone': '#dc2626', 'device_inconnu': '#7c3aed', 'gps_mock': '#dc2626',
            'double_pointage': '#d97706', 'retard': '#ca8a04', 'absence': '#6b7280',
            'depart_anticipe': '#2563eb',
        }
        c = colors.get(obj.type_anomalie, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_type_anomalie_display()
        )

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {'non_traite': '#dc2626', 'justifie': '#059669', 'non_justifie': '#6b7280'}
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.action(description='Marquer comme justifiées')
    def justifier(self, request, queryset):
        n = queryset.update(statut='justifie', traite_par=request.user)
        self.message_user(request, f"{n} anomalie(s) justifiée(s).")

    @admin.action(description='Marquer comme non justifiées')
    def marquer_non_justifie(self, request, queryset):
        n = queryset.update(statut='non_justifie', traite_par=request.user)
        self.message_user(request, f"{n} anomalie(s) marquée(s) non justifiées.")
