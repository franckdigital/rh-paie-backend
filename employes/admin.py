from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Departement, FichePoste, Poste, Employe, AffectationHistorique


class PosteInline(admin.TabularInline):
    model = Poste
    extra = 0
    fields = ('titre', 'fiche_poste', 'salaire_min', 'salaire_max')
    show_change_link = True


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'site', 'responsable', 'nb_employes')
    list_filter = ('site', 'site__entreprise')
    search_fields = ('nom',)
    inlines = [PosteInline]

    @admin.display(description='Employés')
    def nb_employes(self, obj):
        return obj.employes.filter(statut='actif').count()


@admin.register(FichePoste)
class FichePosteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'niveau', 'experience_min_annees', 'formation_requise')
    list_filter = ('niveau',)
    search_fields = ('titre', 'missions')


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'departement', 'salaire_min', 'salaire_max', 'nb_employes')
    list_filter = ('departement', 'departement__site')
    search_fields = ('titre',)

    @admin.display(description='Effectif')
    def nb_employes(self, obj):
        return obj.employes.filter(statut='actif').count()


STATUT_COLORS = {
    'actif': '#059669',
    'inactif': '#6b7280',
    'suspendu': '#d97706',
    'demissionnaire': '#2563eb',
    'licencie': '#dc2626',
    'retraite': '#7c3aed',
}


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = (
        'matricule', 'nom_complet_col', 'statut_badge', 'poste', 'departement',
        'site', 'type_contrat', 'salaire_base', 'date_embauche', 'anciennete_col',
    )
    list_filter = ('statut', 'type_contrat', 'genre', 'site', 'departement', 'site__entreprise')
    search_fields = ('matricule', 'nom', 'prenom', 'email', 'telephone', 'numero_cnps')
    list_per_page = 30
    date_hierarchy = 'date_embauche'
    readonly_fields = ('created_at', 'updated_at', 'anciennete_annees')

    fieldsets = (
        ('Identité', {
            'fields': (
                ('prenom', 'nom'), ('genre', 'date_naissance'),
                'situation_familiale', 'nombre_enfants',
                'photo', 'nationalite', 'numero_cnps',
            ),
        }),
        ('Contact', {
            'fields': ('telephone', 'email', 'adresse'),
        }),
        ('Poste & Affectation', {
            'fields': (
                'matricule', ('statut', 'type_contrat'),
                ('date_embauche', 'date_fin_contrat'),
                ('poste', 'departement', 'site', 'unite'),
                'manager', 'salaire_base',
            ),
        }),
        ('Banque & Paiement', {
            'fields': ('mode_paiement', 'banque', 'rib', 'numero_mobile_money'),
            'classes': ('collapse',),
        }),
        ('Appareil mobile (anti-fraude)', {
            'fields': ('device_id', 'device_imei'),
            'classes': ('collapse',),
        }),
        ('Méta', {
            'fields': ('anciennete_annees', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['marquer_actif', 'marquer_inactif', 'marquer_suspendu']

    @admin.display(description='Employé', ordering='nom')
    def nom_complet_col(self, obj):
        return f"{obj.prenom} {obj.nom}"

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        color = STATUT_COLORS.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_statut_display()
        )

    @admin.display(description='Ancienneté')
    def anciennete_col(self, obj):
        a = obj.anciennete_annees
        return f"{a} an{'s' if a > 1 else ''}"

    @admin.action(description='Marquer comme Actif')
    def marquer_actif(self, request, queryset):
        n = queryset.update(statut='actif')
        self.message_user(request, f"{n} employé(s) marqué(s) actif(s).")

    @admin.action(description='Marquer comme Inactif')
    def marquer_inactif(self, request, queryset):
        n = queryset.update(statut='inactif')
        self.message_user(request, f"{n} employé(s) marqué(s) inactif(s).")

    @admin.action(description='Marquer comme Suspendu')
    def marquer_suspendu(self, request, queryset):
        n = queryset.update(statut='suspendu')
        self.message_user(request, f"{n} employé(s) suspendu(s).")
