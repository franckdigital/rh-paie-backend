from django.contrib import admin
from django.utils.html import format_html
from .models import ElementSalaire, BulletinPaie, LigneBulletin, JournalPaie


@admin.register(ElementSalaire)
class ElementSalaireAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'code', 'type_badge', 'categorie', 'taux', 'montant_fixe',
        'est_imposable', 'est_soumis_cnps', 'est_actif', 'ordre_affichage',
    )
    list_filter = ('type', 'categorie', 'est_imposable', 'est_soumis_cnps', 'est_actif', 'entreprise')
    search_fields = ('nom', 'code')
    list_per_page = 30
    list_editable = ('ordre_affichage', 'est_actif')

    @admin.display(description='Type', ordering='type')
    def type_badge(self, obj):
        if obj.type == 'gain':
            return format_html('<span style="color:#059669;font-weight:700">+ Gain</span>')
        return format_html('<span style="color:#dc2626;font-weight:700">− Retenue</span>')


class LigneBulletinInline(admin.TabularInline):
    model = LigneBulletin
    extra = 0
    fields = ('element', 'base', 'taux', 'quantite', 'montant')
    readonly_fields = ('montant',)


@admin.register(BulletinPaie)
class BulletinPaieAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'periode_col', 'salaire_brut', 'total_retenues',
        'net_col', 'statut_badge', 'date_paiement', 'genere_par',
    )
    list_filter = ('statut', 'periode_fin', 'employe__site', 'employe__departement')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    date_hierarchy = 'periode_fin'
    list_per_page = 30
    readonly_fields = (
        'created_at', 'updated_at',
        'salaire_brut', 'salaire_brut_imposable', 'salaire_net', 'salaire_net_paye',
        'cotisation_cnps_employe', 'cotisation_cnps_patronale', 'its', 'cmu',
        'total_gains', 'total_retenues',
        'montant_heures_nuit', 'montant_heures_supp', 'montant_heures_ferie',
        'deduction_absence',
    )
    inlines = [LigneBulletinInline]
    actions = ['valider_bulletins', 'marquer_payes', 'recalculer_bulletins']

    fieldsets = (
        ('Employé & Période', {
            'fields': ('employe', ('periode_debut', 'periode_fin'), 'statut'),
        }),
        ('Base salariale', {
            'fields': (
                'salaire_base', ('jours_travailles', 'jours_absents'), 'deduction_absence',
            ),
        }),
        ('Heures', {
            'fields': (
                ('heures_normales', 'heures_nuit'),
                ('heures_supp_25', 'heures_supp_50'),
                ('heures_ferie', 'heures_dimanche'),
                ('montant_heures_nuit', 'montant_heures_supp', 'montant_heures_ferie'),
            ),
            'classes': ('collapse',),
        }),
        ('Totaux', {
            'fields': (
                ('total_gains', 'total_retenues'),
                ('salaire_brut', 'salaire_brut_imposable'),
                ('salaire_net', 'salaire_net_paye'),
            ),
        }),
        ('Cotisations', {
            'fields': (
                ('cotisation_cnps_employe', 'cotisation_cnps_patronale'),
                ('its', 'cmu'),
            ),
            'classes': ('collapse',),
        }),
        ('Paiement', {
            'fields': ('date_paiement', 'mode_paiement', 'note', 'genere_par', 'recap_heures'),
            'classes': ('collapse',),
        }),
        ('Méta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Période', ordering='-periode_fin')
    def periode_col(self, obj):
        return obj.periode_fin.strftime('%m/%Y')

    @admin.display(description='Net à payer', ordering='salaire_net_paye')
    def net_col(self, obj):
        return format_html(
            '<span style="color:#059669;font-weight:700">{:,.0f} FCFA</span>',
            obj.salaire_net_paye
        )

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {
            'brouillon': '#6b7280', 'valide': '#2563eb',
            'paye': '#059669', 'annule': '#dc2626',
        }
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.action(description='Valider les bulletins sélectionnés')
    def valider_bulletins(self, request, queryset):
        n = queryset.filter(statut='brouillon').update(statut='valide', genere_par=request.user)
        self.message_user(request, f"{n} bulletin(s) validé(s).")

    @admin.action(description='Marquer comme payés')
    def marquer_payes(self, request, queryset):
        from django.utils import timezone
        n = queryset.filter(statut='valide').update(statut='paye', date_paiement=timezone.now().date())
        self.message_user(request, f"{n} bulletin(s) marqué(s) payé(s).")

    @admin.action(description='Recalculer les bulletins sélectionnés')
    def recalculer_bulletins(self, request, queryset):
        count = 0
        for bulletin in queryset.filter(statut='brouillon'):
            bulletin.calculer_salaire_complet()
            count += 1
        self.message_user(request, f"{count} bulletin(s) recalculé(s).")


@admin.register(JournalPaie)
class JournalPaieAdmin(admin.ModelAdmin):
    list_display = (
        'entreprise', 'periode_col', 'nombre_bulletins',
        'total_salaires_bruts', 'total_salaires_nets',
        'total_cotisations_patronales', 'statut_badge', 'cloture_par',
    )
    list_filter = ('statut', 'entreprise', 'periode_fin')
    search_fields = ('entreprise__nom',)
    date_hierarchy = 'periode_fin'
    readonly_fields = ('created_at',)
    filter_horizontal = ('bulletins',)
    actions = ['valider_journaux', 'cloturer_journaux']

    @admin.display(description='Période', ordering='-periode_fin')
    def periode_col(self, obj):
        return obj.periode_fin.strftime('%m/%Y')

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {'en_cours': '#d97706', 'valide': '#2563eb', 'cloture': '#059669'}
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.action(description='Valider les journaux sélectionnés')
    def valider_journaux(self, request, queryset):
        n = queryset.filter(statut='en_cours').update(statut='valide')
        self.message_user(request, f"{n} journal(ux) validé(s).")

    @admin.action(description='Clôturer les journaux sélectionnés')
    def cloturer_journaux(self, request, queryset):
        n = queryset.filter(statut='valide').update(statut='cloture', cloture_par=request.user)
        self.message_user(request, f"{n} journal(ux) clôturé(s).")
