from django.contrib import admin
from django.utils.html import format_html
from .models import TypeShift, RotationEquipe, Equipe, PlanningMensuel, LignePlanning


@admin.register(TypeShift)
class TypeShiftAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'horaires', 'duree_heures', 'couleur_badge', 'est_nuit')
    list_filter = ('est_nuit', 'traverse_minuit')
    search_fields = ('nom', 'code')

    @admin.display(description='Horaires')
    def horaires(self, obj):
        return f"{obj.heure_debut.strftime('%H:%M')} → {obj.heure_fin.strftime('%H:%M')}"

    @admin.display(description='Couleur')
    def couleur_badge(self, obj):
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 12px;border-radius:4px;font-size:12px">{}</span>',
            obj.couleur, obj.couleur
        )


@admin.register(RotationEquipe)
class RotationEquipeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_cycle', 'duree_cycle_jours')
    list_filter = ('type_cycle',)
    search_fields = ('nom',)


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'site', 'rotation', 'chef_equipe', 'est_actif')
    list_filter = ('site', 'site__entreprise', 'est_actif', 'rotation')
    search_fields = ('nom', 'code')


class LignePlanningInline(admin.TabularInline):
    model = LignePlanning
    extra = 0
    fields = ('employe', 'date', 'type_jour', 'shift', 'note')
    show_change_link = True
    max_num = 50


@admin.register(PlanningMensuel)
class PlanningMensuelAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'site', 'annee', 'mois', 'statut_badge', 'nb_lignes', 'cree_par', 'created_at')
    list_filter = ('statut', 'annee', 'mois', 'site__entreprise')
    search_fields = ('site__nom',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [LignePlanningInline]
    actions = ['publier', 'cloture']

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {'brouillon': '#6b7280', 'publie': '#059669', 'cloture': '#2563eb'}
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.display(description='Lignes')
    def nb_lignes(self, obj):
        return obj.lignes.count()

    @admin.action(description='Publier les plannings sélectionnés')
    def publier(self, request, queryset):
        n = queryset.filter(statut='brouillon').update(statut='publie')
        self.message_user(request, f"{n} planning(s) publié(s).")

    @admin.action(description='Clôturer les plannings sélectionnés')
    def cloture(self, request, queryset):
        n = queryset.update(statut='cloture')
        self.message_user(request, f"{n} planning(s) clôturé(s).")


@admin.register(LignePlanning)
class LignePlanningAdmin(admin.ModelAdmin):
    list_display = ('employe', 'date', 'type_jour_badge', 'shift', 'site_affecte', 'est_remplacement')
    list_filter = ('type_jour', 'shift', 'planning__site', 'date')
    search_fields = ('employe__nom', 'employe__prenom', 'employe__matricule')
    date_hierarchy = 'date'
    list_per_page = 40

    @admin.display(description='Type jour', ordering='type_jour')
    def type_jour_badge(self, obj):
        colors = {
            'travail': '#059669', 'repos': '#6b7280', 'conge': '#2563eb',
            'ferie': '#7c3aed', 'mission': '#d97706', 'formation': '#0891b2',
        }
        c = colors.get(obj.type_jour, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_type_jour_display()
        )
