from django.contrib import admin
from django.utils.html import format_html
from .models import EvenementCarriere, RegleEvolutionCarriere


TYPE_COLORS = {
    'recrutement': '#059669',
    'promotion': '#2563eb',
    'mutation': '#7c3aed',
    'changement_poste': '#0891b2',
    'augmentation_salaire': '#059669',
    'renouvellement_contrat': '#ca8a04',
    'changement_contrat': '#d97706',
    'suspension': '#dc2626',
    'reprise': '#059669',
    'demission': '#6b7280',
    'licenciement': '#dc2626',
    'depart_retraite': '#7c3aed',
    'sanction': '#dc2626',
    'formation': '#0e7490',
    'evaluation': '#2563eb',
}


@admin.register(EvenementCarriere)
class EvenementCarriereAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'type_badge', 'date_evenement', 'date_effet',
        'avant_col', 'apres_col', 'delta_salaire_col', 'approuve_par',
    )
    list_filter = ('type_evenement', 'date_evenement')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule', 'description')
    date_hierarchy = 'date_evenement'
    list_per_page = 30
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Événement', {
            'fields': ('employe', 'type_evenement', ('date_evenement', 'date_effet'), 'description'),
        }),
        ('Situation avant', {
            'fields': ('poste_avant', 'site_avant', 'salaire_avant'),
        }),
        ('Situation après', {
            'fields': ('poste_apres', 'site_apres', 'salaire_apres'),
        }),
        ('Validation', {
            'fields': ('approuve_par', 'document'),
        }),
        ('Méta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Type', ordering='type_evenement')
    def type_badge(self, obj):
        c = TYPE_COLORS.get(obj.type_evenement, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_type_evenement_display()
        )

    @admin.display(description='Avant')
    def avant_col(self, obj):
        parts = []
        if obj.poste_avant:
            parts.append(str(obj.poste_avant))
        if obj.salaire_avant:
            parts.append(f"{obj.salaire_avant:,.0f}")
        return ' / '.join(parts) or '—'

    @admin.display(description='Après')
    def apres_col(self, obj):
        parts = []
        if obj.poste_apres:
            parts.append(str(obj.poste_apres))
        if obj.salaire_apres:
            parts.append(f"{obj.salaire_apres:,.0f}")
        return ' / '.join(parts) or '—'

    @admin.display(description='Δ Salaire')
    def delta_salaire_col(self, obj):
        if obj.salaire_avant and obj.salaire_apres:
            delta = float(obj.salaire_apres) - float(obj.salaire_avant)
            if delta > 0:
                return format_html('<span style="color:#059669;font-weight:700">+{:,.0f}</span>', delta)
            if delta < 0:
                return format_html('<span style="color:#dc2626;font-weight:700">{:,.0f}</span>', delta)
        return '—'


@admin.register(RegleEvolutionCarriere)
class RegleEvolutionCarriereAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'entreprise', 'poste_actuel', 'poste_cible',
        'anciennete_min_annees', 'est_actif', 'notification_auto',
    )
    list_filter = ('est_actif', 'notification_auto', 'entreprise')
    search_fields = ('nom', 'poste_actuel__titre', 'poste_cible__titre')
    list_per_page = 20
    list_editable = ('est_actif', 'notification_auto')
