from django.contrib import admin
from django.utils.html import format_html
from .models import ParametreHeures, RecapHeures


@admin.register(ParametreHeures)
class ParametreHeuresAdmin(admin.ModelAdmin):
    list_display = (
        'entreprise', 'heures_normales_jour', 'heures_max_journalier',
        'heure_debut_nuit', 'heure_fin_nuit', 'tolerance_retard_minutes',
        'taux_majoration_nuit', 'taux_majoration_supp_25', 'taux_majoration_ferie',
    )
    search_fields = ('entreprise__nom',)
    list_per_page = 20

    fieldsets = (
        ('Entreprise', {
            'fields': ('entreprise',),
        }),
        ('Seuils journaliers', {
            'fields': ('heures_normales_jour', 'heures_max_journalier', 'tolerance_retard_minutes'),
        }),
        ('Heures de nuit', {
            'fields': ('heure_debut_nuit', 'heure_fin_nuit', 'taux_majoration_nuit'),
        }),
        ('Majorations heures supplémentaires', {
            'fields': ('taux_majoration_supp_25', 'taux_majoration_supp_50'),
        }),
        ('Majorations jours spéciaux', {
            'fields': ('taux_majoration_dimanche', 'taux_majoration_ferie'),
        }),
    )


@admin.register(RecapHeures)
class RecapHeuresAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'periode_col', 'jours_travailles', 'heures_normales',
        'heures_supp_col', 'heures_nuit', 'retards_count',
        'montant_heures_supp', 'valide_col',
    )
    list_filter = ('valide', 'annee', 'mois')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    list_per_page = 40
    readonly_fields = ('calcule_le',)

    fieldsets = (
        ('Période', {
            'fields': ('employe', 'annee', 'mois'),
        }),
        ('Jours', {
            'fields': ('jours_travailles', 'jours_absents', 'jours_conge'),
        }),
        ('Heures', {
            'fields': (
                'heures_normales', 'heures_nuit',
                'heures_supp_25', 'heures_supp_50',
                'heures_dimanche', 'heures_ferie',
            ),
        }),
        ('Retards', {
            'fields': ('retards_count', 'retards_minutes_total'),
        }),
        ('Montants calculés', {
            'fields': (
                'montant_heures_normales', 'montant_heures_nuit',
                'montant_heures_supp', 'montant_absences_deduites',
            ),
        }),
        ('Validation', {
            'fields': ('valide', 'valide_par', 'calcule_le'),
        }),
    )

    actions = ['valider_recaps', 'invalider_recaps']

    @admin.display(description='Période', ordering='-annee')
    def periode_col(self, obj):
        return f"{obj.mois:02d}/{obj.annee}"

    @admin.display(description='H. supp')
    def heures_supp_col(self, obj):
        total = float(obj.heures_supp_25) + float(obj.heures_supp_50)
        if total > 0:
            return format_html('<span style="color:#d97706;font-weight:700">{:.2f}h</span>', total)
        return '—'

    @admin.display(description='Validé', ordering='valide')
    def valide_col(self, obj):
        if obj.valide:
            return format_html('<span style="color:#059669;font-weight:700">✓ Oui</span>')
        return format_html('<span style="color:#6b7280">En attente</span>')

    @admin.action(description='Valider les récaps sélectionnés')
    def valider_recaps(self, request, queryset):
        n = queryset.update(valide=True, valide_par=request.user)
        self.message_user(request, f"{n} récap(s) validé(s).")

    @admin.action(description='Invalider les récaps sélectionnés')
    def invalider_recaps(self, request, queryset):
        n = queryset.update(valide=False, valide_par=None)
        self.message_user(request, f"{n} récap(s) invalidé(s).")
