from django.contrib import admin
from django.utils.html import format_html
from .models import Presence, JourFerie, RapportPresence


STATUT_COLORS = {
    'present': '#059669',
    'retard': '#d97706',
    'absent_justifie': '#2563eb',
    'absent_non_justifie': '#dc2626',
    'conge': '#7c3aed',
    'maladie': '#0891b2',
    'mission': '#ca8a04',
    'permission': '#6b7280',
    'formation': '#0e7490',
    'ferie': '#059669',
    'repos': '#6b7280',
    'suspension': '#dc2626',
}


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'date', 'statut_badge', 'heure_arrivee', 'heure_depart',
        'heures_travaillees', 'retard_col', 'heures_supp', 'site', 'shift',
    )
    list_filter = ('statut', 'date', 'site', 'shift', 'calcul_automatique')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    date_hierarchy = 'date'
    list_per_page = 40
    readonly_fields = ('created_at', 'updated_at', 'heures_travaillees', 'heures_nuit', 'heures_supp')

    fieldsets = (
        ('Présence', {
            'fields': ('employe', 'date', 'statut', 'shift', 'site'),
        }),
        ('Horaires', {
            'fields': ('heure_arrivee', 'heure_depart'),
        }),
        ('Calculs', {
            'fields': (
                'heures_travaillees', 'heures_nuit', 'heures_supp',
                'retard_minutes', 'depart_anticipe_minutes',
            ),
        }),
        ('Pointages liés', {
            'fields': ('pointage_entree', 'pointage_sortie'),
            'classes': ('collapse',),
        }),
        ('Justification', {
            'fields': ('justification', 'justifie_par', 'calcul_automatique'),
            'classes': ('collapse',),
        }),
        ('Méta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['justifier_absences', 'recalculer_heures']

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        c = STATUT_COLORS.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.display(description='Retard', ordering='retard_minutes')
    def retard_col(self, obj):
        if obj.retard_minutes:
            return format_html('<span style="color:#d97706">{}min</span>', obj.retard_minutes)
        return '—'

    @admin.action(description='Marquer les absences comme justifiées')
    def justifier_absences(self, request, queryset):
        n = queryset.filter(statut='absent_non_justifie').update(
            statut='absent_justifie', justifie_par=request.user
        )
        self.message_user(request, f"{n} absence(s) justifiée(s).")

    @admin.action(description='Recalculer les heures')
    def recalculer_heures(self, request, queryset):
        count = 0
        for presence in queryset:
            presence.calculer_heures()
            presence.save()
            count += 1
        self.message_user(request, f"{count} présence(s) recalculée(s).")


@admin.register(JourFerie)
class JourFerieAdmin(admin.ModelAdmin):
    list_display = ('date', 'nom', 'pays', 'est_national')
    list_filter = ('pays', 'est_national')
    search_fields = ('nom',)
    date_hierarchy = 'date'
    list_per_page = 30


@admin.register(RapportPresence)
class RapportPresenceAdmin(admin.ModelAdmin):
    list_display = (
        'site', 'periode', 'date_debut', 'date_fin',
        'total_employes', 'taux_col', 'heures_total', 'genere_le',
    )
    list_filter = ('periode', 'site', 'site__entreprise')
    date_hierarchy = 'date_debut'
    readonly_fields = ('genere_le',)
    list_per_page = 20

    @admin.display(description='Taux présence')
    def taux_col(self, obj):
        taux = float(obj.taux_presence)
        if taux >= 90:
            color = '#059669'
        elif taux >= 75:
            color = '#d97706'
        else:
            color = '#dc2626'
        return format_html(
            '<span style="color:{};font-weight:700">{:.1f}%</span>', color, taux
        )
