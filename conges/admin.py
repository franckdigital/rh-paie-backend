from django.contrib import admin
from django.utils.html import format_html
from .models import TypeConge, DemandeConge, SoldeConge


@admin.register(TypeConge)
class TypeCongeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'nombre_jours', 'paye_badge')
    list_filter = ('est_paye',)
    search_fields = ('nom',)

    @admin.display(description='Payé', ordering='est_paye')
    def paye_badge(self, obj):
        if obj.est_paye:
            return format_html('<span style="color:#059669;font-weight:700">✓ Payé</span>')
        return format_html('<span style="color:#6b7280">Non payé</span>')


@admin.register(DemandeConge)
class DemandeCongeAdmin(admin.ModelAdmin):
    list_display = (
        'employe', 'type_conge', 'date_debut', 'date_fin',
        'nombre_jours', 'statut_badge', 'approuve_par', 'date_approbation',
    )
    list_filter = ('statut', 'type_conge', 'date_debut')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule', 'motif')
    date_hierarchy = 'date_debut'
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at', 'date_approbation')

    fieldsets = (
        ('Demande', {
            'fields': ('employe', 'type_conge', ('date_debut', 'date_fin'), 'nombre_jours', 'motif'),
        }),
        ('Décision', {
            'fields': ('statut', 'approuve_par', 'date_approbation', 'commentaire_approbation'),
        }),
        ('Méta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['approuver_demandes', 'refuser_demandes', 'annuler_demandes']

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {
            'en_attente': '#d97706', 'approuve': '#059669',
            'refuse': '#dc2626', 'annule': '#6b7280',
        }
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.action(description='Approuver les demandes sélectionnées')
    def approuver_demandes(self, request, queryset):
        from django.utils import timezone
        n = queryset.filter(statut='en_attente').update(
            statut='approuve', approuve_par=request.user, date_approbation=timezone.now()
        )
        self.message_user(request, f"{n} demande(s) approuvée(s).")

    @admin.action(description='Refuser les demandes sélectionnées')
    def refuser_demandes(self, request, queryset):
        from django.utils import timezone
        n = queryset.filter(statut='en_attente').update(
            statut='refuse', approuve_par=request.user, date_approbation=timezone.now()
        )
        self.message_user(request, f"{n} demande(s) refusée(s).")

    @admin.action(description='Annuler les demandes sélectionnées')
    def annuler_demandes(self, request, queryset):
        n = queryset.filter(statut__in=['en_attente', 'approuve']).update(statut='annule')
        self.message_user(request, f"{n} demande(s) annulée(s).")


@admin.register(SoldeConge)
class SoldeCongeAdmin(admin.ModelAdmin):
    list_display = ('employe', 'type_conge', 'annee', 'jours_acquis', 'jours_pris', 'solde_col')
    list_filter = ('annee', 'type_conge')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    list_per_page = 40

    @admin.display(description='Solde restant', ordering='jours_restants')
    def solde_col(self, obj):
        val = float(obj.jours_restants)
        if val <= 0:
            color = '#dc2626'
        elif val <= 5:
            color = '#d97706'
        else:
            color = '#059669'
        return format_html('<span style="color:{};font-weight:700">{} j</span>', color, val)
