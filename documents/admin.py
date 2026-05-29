from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import CategorieDocument, Document


@admin.register(CategorieDocument)
class CategorieDocumentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'icone', 'description')
    search_fields = ('nom', 'code')
    list_per_page = 20


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'categorie', 'employe', 'entreprise',
        'statut_badge', 'expiration_col', 'confidentiel_col',
        'taille_col', 'ajoute_par', 'created_at',
    )
    list_filter = ('statut', 'categorie', 'est_confidentiel', 'entreprise')
    search_fields = ('nom', 'description', 'employe__nom', 'employe__prenom', 'employe__matricule')
    date_hierarchy = 'created_at'
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at', 'taille_fichier', 'type_mime')

    fieldsets = (
        ('Document', {
            'fields': ('nom', 'description', 'categorie', 'fichier', 'statut'),
        }),
        ('Association', {
            'fields': ('employe', 'entreprise'),
        }),
        ('Dates', {
            'fields': ('date_document', 'date_expiration'),
        }),
        ('Accès', {
            'fields': ('est_confidentiel', 'ajoute_par'),
        }),
        ('Méta fichier', {
            'fields': ('taille_fichier', 'type_mime', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['archiver_documents', 'marquer_expires']

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        colors = {
            'valide': '#059669', 'expire': '#dc2626',
            'en_attente': '#d97706', 'archive': '#6b7280',
        }
        c = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            c, obj.get_statut_display()
        )

    @admin.display(description='Expiration')
    def expiration_col(self, obj):
        if not obj.date_expiration:
            return '—'
        today = timezone.now().date()
        delta = (obj.date_expiration - today).days
        if delta < 0:
            return format_html('<span style="color:#dc2626;font-weight:700">Expiré</span>')
        if delta <= 30:
            return format_html('<span style="color:#d97706">⚠ {} j</span>', delta)
        return format_html('<span style="color:#059669">{}</span>', obj.date_expiration)

    @admin.display(description='Confidentiel')
    def confidentiel_col(self, obj):
        if obj.est_confidentiel:
            return format_html('<span style="color:#dc2626;font-weight:700">🔒 Oui</span>')
        return '—'

    @admin.display(description='Taille')
    def taille_col(self, obj):
        if obj.taille_fichier:
            kb = obj.taille_fichier / 1024
            if kb > 1024:
                return f"{kb/1024:.1f} MB"
            return f"{kb:.0f} KB"
        return '—'

    @admin.action(description='Archiver les documents sélectionnés')
    def archiver_documents(self, request, queryset):
        n = queryset.exclude(statut='archive').update(statut='archive')
        self.message_user(request, f"{n} document(s) archivé(s).")

    @admin.action(description='Marquer comme expirés')
    def marquer_expires(self, request, queryset):
        n = queryset.update(statut='expire')
        self.message_user(request, f"{n} document(s) marqué(s) expiré(s).")
