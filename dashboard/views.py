from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

CONTRAT_COLORS = {
    'cdi':        '#6366f1',
    'cdd':        '#f59e0b',
    'stage':      '#10b981',
    'freelance':  '#8b5cf6',
    'interimaire':'#ec4899',
}
CONTRAT_LABELS = {
    'cdi': 'CDI', 'cdd': 'CDD', 'stage': 'Stage',
    'freelance': 'Freelance', 'interimaire': 'Intérimaire',
}
GENRE_COLORS = {'M': '#3b82f6', 'F': '#ec4899'}
GENRE_LABELS = {'M': 'Hommes', 'F': 'Femmes'}
JOURS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']


class DashboardRHView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from employes.models import Employe, Departement
        from carrieres.models import EvenementCarriere

        maintenant = timezone.now()
        annee, mois = maintenant.year, maintenant.month

        effectif_actif = Employe.objects.filter(statut='actif').count()
        effectif_total = Employe.objects.count()

        # Répartition contrats → format {name, value, color}
        par_contrat = [
            {
                'name': CONTRAT_LABELS.get(r['type_contrat'], r['type_contrat'].upper()),
                'value': r['nb'],
                'color': CONTRAT_COLORS.get(r['type_contrat'], '#94a3b8'),
            }
            for r in Employe.objects.filter(statut='actif')
            .values('type_contrat').annotate(nb=Count('id'))
        ]

        # Répartition genre → format {name, value, color}
        par_genre = [
            {
                'name': GENRE_LABELS.get(r['genre'], r['genre']),
                'value': r['nb'],
                'color': GENRE_COLORS.get(r['genre'], '#94a3b8'),
            }
            for r in Employe.objects.filter(statut='actif')
            .values('genre').annotate(nb=Count('id'))
        ]

        # Effectif par département → format {dept, count}
        par_dept = [
            {'dept': r['nom'], 'count': r['nb']}
            for r in Departement.objects.annotate(
                nb=Count('employes', filter=Q(employes__statut='actif'))
            ).values('nom', 'nb').order_by('-nb')[:8]
        ]

        # Recrutements récents (30 derniers jours)
        depuis_30j = (maintenant - timedelta(days=30)).date()
        recents = list(
            Employe.objects.filter(date_embauche__gte=depuis_30j)
            .select_related('poste')
            .order_by('-date_embauche')[:8]
            .values('nom', 'prenom', 'poste__titre', 'date_embauche', 'type_contrat')
        )
        recrutements_recents = [
            {
                'nom': f"{r['prenom']} {r['nom']}",
                'poste': r['poste__titre'] or '—',
                'date': str(r['date_embauche']),
                'type_contrat': r['type_contrat'],
            }
            for r in recents
        ]

        # Turnover annuel = départs / effectif moyen × 100
        departs_annee = EvenementCarriere.objects.filter(
            type_evenement__in=['demission', 'licenciement', 'depart_retraite'],
            date_evenement__year=annee,
        ).count()
        turnover = round(departs_annee / effectif_total * 100, 1) if effectif_total else 0

        # Ancienneté moyenne
        from django.utils.timezone import now as tz_now
        today = tz_now().date()
        employes_dates = Employe.objects.filter(statut='actif').values_list('date_embauche', flat=True)
        if employes_dates:
            moy_jours = sum((today - d).days for d in employes_dates) / len(employes_dates)
            anciennete_moyenne = round(moy_jours / 365, 1)
        else:
            anciennete_moyenne = 0.0

        # Contrats expirant dans 30 jours
        dans_30j = (maintenant + timedelta(days=30)).date()
        contrats_expirant = Employe.objects.filter(
            date_fin_contrat__lte=dans_30j,
            date_fin_contrat__gte=maintenant.date(),
            statut='actif',
        ).count()

        nouveaux = Employe.objects.filter(date_embauche__year=annee, date_embauche__month=mois).count()
        departs = EvenementCarriere.objects.filter(
            type_evenement__in=['demission', 'licenciement', 'depart_retraite'],
            date_evenement__year=annee, date_evenement__month=mois,
        ).count()

        # Agents sans promotion depuis 5 ans (avec liste détaillée)
        seuil_5ans = today - timedelta(days=5 * 365)
        anciens_qs = Employe.objects.filter(statut='actif', date_embauche__lte=seuil_5ans).select_related('poste', 'departement', 'site')
        agents_sans_promo_list = []
        for emp in anciens_qs:
            has_promo = EvenementCarriere.objects.filter(
                employe=emp, type_evenement='promotion',
                date_evenement__gte=seuil_5ans,
            ).exists()
            if not has_promo:
                anciennete = round((today - emp.date_embauche).days / 365, 1)
                last_event = EvenementCarriere.objects.filter(employe=emp).order_by('-date_evenement').first()
                agents_sans_promo_list.append({
                    'id': emp.id,
                    'matricule': emp.matricule,
                    'nom': f"{emp.prenom} {emp.nom}",
                    'poste': emp.poste.titre if emp.poste else '—',
                    'departement': emp.departement.nom if emp.departement else '—',
                    'site': emp.site.nom if emp.site else '—',
                    'date_embauche': str(emp.date_embauche),
                    'anciennete_ans': anciennete,
                    'dernier_evenement': last_event.type_evenement if last_event else None,
                    'date_dernier_evenement': str(last_event.date_evenement) if last_event else None,
                })

        # Promotions ce mois
        promotions_ce_mois = EvenementCarriere.objects.filter(
            type_evenement='promotion', date_evenement__year=annee, date_evenement__month=mois
        ).count()

        # Congés en attente
        from conges.models import DemandeConge
        conges_en_attente = DemandeConge.objects.filter(statut__in=['en_attente', 'valide_chef']).count()

        # Absentéisme ce mois
        from presences.models import Presence
        total_presences = Presence.objects.filter(date__year=annee, date__month=mois).count()
        absences = Presence.objects.filter(
            date__year=annee, date__month=mois,
            statut__in=['absent_non_justifie', 'absent_justifie']
        ).count()
        taux_absenteisme = round(absences / total_presences * 100, 1) if total_presences else 0

        # Effectif par site
        from sites_rh.models import Site
        par_site = [
            {'site': s.nom, 'count': Employe.objects.filter(site=s, statut='actif').count()}
            for s in Site.objects.filter(est_actif=True).order_by('nom')
        ]

        # Alertes
        alertes = []
        if contrats_expirant > 0:
            alertes.append({'message': f"{contrats_expirant} contrat(s) CDD expirent dans moins de 30 jours"})
        if agents_sans_promo_list:
            alertes.append({'message': f"{len(agents_sans_promo_list)} agent(s) avec plus de 5 ans sans promotion détectés", 'action': 'voir_agents_sans_promo'})

        return Response({
            'effectif_actif': effectif_actif,
            'effectif_total': effectif_total,
            'nouveaux_ce_mois': nouveaux,
            'departs_ce_mois': departs,
            'turnover_annuel': turnover,
            'anciennete_moyenne': anciennete_moyenne,
            'contrats_expirant_30j': contrats_expirant,
            'promotions_ce_mois': promotions_ce_mois,
            'conges_en_attente': conges_en_attente,
            'taux_absenteisme': taux_absenteisme,
            'repartition_contrats': par_contrat,
            'repartition_genres': par_genre,
            'effectif_par_dept': par_dept,
            'effectif_par_site': par_site,
            'recrutements_recents': recrutements_recents,
            'agents_sans_promo': agents_sans_promo_list,
            'alertes': alertes,
        })


class DashboardPresenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from presences.models import Presence
        from pointage.models import Pointage

        aujourd_hui = timezone.now().date()
        site_id = request.query_params.get('site')

        qs = Presence.objects.filter(date=aujourd_hui)
        qs_pt = Pointage.objects.filter(date_pointage=aujourd_hui)
        if site_id:
            qs = qs.filter(site_id=site_id)
            qs_pt = qs_pt.filter(site_id=site_id)

        stats = qs.aggregate(
            presents=Count('id', filter=Q(statut__in=['present', 'retard'])),
            retards=Count('id', filter=Q(statut='retard')),
            absents_nj=Count('id', filter=Q(statut='absent_non_justifie')),
            absents_j=Count('id', filter=Q(statut='absent_justifie')),
            conges=Count('id', filter=Q(statut='conge')),
            missions=Count('id', filter=Q(statut='mission')),
            total=Count('id'),
        )
        anomalies = qs_pt.filter(statut='anomalie').count()
        derniers = list(
            qs_pt.order_by('-datetime_pointage')[:10]
            .values('employe__nom', 'employe__prenom', 'type_pointage',
                    'datetime_pointage', 'statut', 'dans_geofence')
        )

        return Response({
            'date': aujourd_hui,
            'stats_presence': stats,
            'anomalies_pointage': anomalies,
            'derniers_pointages': derniers,
        })


class DashboardPaieView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from paie.models import BulletinPaie
        from heures.models import RecapHeures
        from employes.models import Departement
        from django.db.models import Sum

        maintenant = timezone.now()
        annee = int(request.query_params.get('annee', maintenant.year))
        mois = int(request.query_params.get('mois', maintenant.month))

        MOIS_FR = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                   'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        mois_courant_label = f"{MOIS_FR[mois - 1]} {annee}"

        qs = BulletinPaie.objects.filter(periode_fin__year=annee, periode_fin__month=mois)

        # Fallback: si aucun bulletin ce mois, utiliser le dernier mois avec données
        if not qs.exists():
            latest = BulletinPaie.objects.order_by('-periode_fin').first()
            if latest:
                annee = latest.periode_fin.year
                mois = latest.periode_fin.month
                mois_courant_label = f"{MOIS_FR[mois - 1]} {annee}"
                qs = BulletinPaie.objects.filter(periode_fin__year=annee, periode_fin__month=mois)

        agg = qs.aggregate(
            masse_brute=Sum('salaire_brut'),
            masse_nette=Sum('salaire_net'),
            total_its=Sum('its'),
            total_cnps_employe=Sum('cotisation_cnps_employe'),
            total_cnps_patronal=Sum('cotisation_cnps_patronale'),
            total_cmu=Sum('cmu'),
        )
        bulletins_valides = qs.filter(statut__in=['valide', 'paye']).count()
        bulletins_en_attente = qs.filter(statut='brouillon').count()
        bulletins_payes = qs.filter(statut='paye').count()

        # Heures supp du mois
        heures_agg = RecapHeures.objects.filter(annee=annee, mois=mois).aggregate(
            total_supp=Sum('montant_heures_supp'),
            total_nuit=Sum('montant_heures_nuit'),
        )
        total_heures_supp = float(heures_agg['total_supp'] or 0) + float(heures_agg['total_nuit'] or 0)

        # Évolution 6 mois
        evolution_6mois = []
        for i in range(5, -1, -1):
            d_ref = maintenant.replace(day=1) - timedelta(days=i * 28)
            m_agg = BulletinPaie.objects.filter(
                periode_fin__year=d_ref.year, periode_fin__month=d_ref.month
            ).aggregate(net=Sum('salaire_net'), brut=Sum('salaire_brut'))
            evolution_6mois.append({
                'mois': MOIS_FR[d_ref.month - 1],
                'brute': float(m_agg['brut'] or 0),
                'nette': float(m_agg['net'] or 0),
            })

        # Masse par département
        masse_par_dept = [
            {'dept': r['employe__departement__nom'] or 'Non affecté', 'montant': float(r['total'] or 0)}
            for r in qs.values('employe__departement__nom')
            .annotate(total=Sum('salaire_brut'))
            .order_by('-total')[:6]
        ]

        return Response({
            'mois_courant': mois_courant_label,
            'masse_brute':          float(agg['masse_brute'] or 0),
            'masse_nette':          float(agg['masse_nette'] or 0),
            'total_its':            float(agg['total_its'] or 0),
            'total_cnps_employe':   float(agg['total_cnps_employe'] or 0),
            'total_cnps_patronal':  float(agg['total_cnps_patronal'] or 0),
            'total_cmu':            float(agg['total_cmu'] or 0),
            'total_heures_supp':    total_heures_supp,
            'bulletins_valides':    bulletins_valides,
            'bulletins_en_attente': bulletins_en_attente,
            'bulletins_payes':      bulletins_payes,
            'evolution_6mois':      evolution_6mois,
            'masse_par_dept':       masse_par_dept,
        })


class DashboardGlobalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from employes.models import Employe
        from presences.models import Presence
        from paie.models import BulletinPaie
        from conges.models import DemandeConge
        from pointage.models import AnomaliePointage
        from sites_rh.models import Site
        from heures.models import RecapHeures

        maintenant = timezone.now()
        aujourd_hui = maintenant.date()
        annee, mois = maintenant.year, maintenant.month

        effectif_actif = Employe.objects.filter(statut='actif').count()

        presents = Presence.objects.filter(
            date=aujourd_hui, statut__in=['present', 'retard']
        ).count()
        absents = Presence.objects.filter(
            date=aujourd_hui, statut='absent_non_justifie'
        ).count()
        taux = round(presents / effectif_actif * 100, 1) if effectif_actif else 0

        masse_net = BulletinPaie.objects.filter(
            periode_fin__year=annee, periode_fin__month=mois
        ).aggregate(s=Sum('salaire_net'))['s']
        if masse_net is None:
            latest = BulletinPaie.objects.order_by('-periode_fin').first()
            if latest:
                masse_net = BulletinPaie.objects.filter(
                    periode_fin__year=latest.periode_fin.year,
                    periode_fin__month=latest.periode_fin.month,
                ).aggregate(s=Sum('salaire_net'))['s'] or 0
            else:
                masse_net = 0

        conges_attente = DemandeConge.objects.filter(statut='en_attente').count()
        anomalies = AnomaliePointage.objects.filter(statut='non_traite').count()
        nb_sites = Site.objects.filter(est_actif=True).count()

        heures_agg = RecapHeures.objects.filter(annee=annee, mois=mois).aggregate(
            s25=Sum('heures_supp_25'), s50=Sum('heures_supp_50'), nuit=Sum('heures_nuit'),
        )
        heures_supp = (heures_agg['s25'] or 0) + (heures_agg['s50'] or 0) + (heures_agg['nuit'] or 0)
        if not heures_supp:
            last_recap = RecapHeures.objects.order_by('-annee', '-mois').first()
            if last_recap:
                h2 = RecapHeures.objects.filter(annee=last_recap.annee, mois=last_recap.mois).aggregate(
                    s25=Sum('heures_supp_25'), s50=Sum('heures_supp_50'), nuit=Sum('heures_nuit'),
                )
                heures_supp = (h2['s25'] or 0) + (h2['s50'] or 0) + (h2['nuit'] or 0)

        # Tendance semaine (7 derniers jours)
        tendance_semaine = []
        for i in range(6, -1, -1):
            d = aujourd_hui - timedelta(days=i)
            day_agg = Presence.objects.filter(date=d).aggregate(
                presents=Count('id', filter=Q(statut__in=['present', 'retard'])),
                absents=Count('id', filter=Q(statut='absent_non_justifie')),
            )
            tendance_semaine.append({
                'jour': JOURS_FR[d.weekday()],
                'presents': day_agg['presents'] or 0,
                'absents': day_agg['absents'] or 0,
            })

        # Présence par site
        par_site = []
        for site in Site.objects.filter(est_actif=True).order_by('nom'):
            site_presents = Presence.objects.filter(
                date=aujourd_hui, site=site, statut__in=['present', 'retard']
            ).count()
            site_total = Employe.objects.filter(site=site, statut='actif').count()
            pct = round(site_presents / site_total * 100) if site_total else 0
            par_site.append({
                'site': site.nom,
                'present': site_presents,
                'total': site_total,
                'pct': pct,
            })

        # Alertes
        alertes = []
        if anomalies > 0:
            alertes.append({'type': 'warning', 'message': f"{anomalies} anomalie(s) de pointage non traitée(s)"})
        if absents > 3:
            alertes.append({'type': 'danger', 'message': f"{absents} absence(s) injustifiée(s) aujourd'hui"})
        if conges_attente > 0:
            alertes.append({'type': 'info', 'message': f"{conges_attente} demande(s) de congé en attente"})

        return Response({
            'effectif_actif':        effectif_actif,
            'presents_aujourd_hui':  presents,
            'absents_aujourd_hui':   absents,
            'taux_presence':         taux,
            'masse_salariale_nette': float(masse_net),
            'conges_en_attente':     conges_attente,
            'anomalies_pointage':    anomalies,
            'nb_sites':              nb_sites,
            'heures_supp_ce_mois':   float(heures_supp),
            'tendance_semaine':      tendance_semaine,
            'par_site':              par_site,
            'alertes':               alertes,
        })


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from employes.models import Employe, Departement
        from paie.models import BulletinPaie
        from conges.models import DemandeConge

        maintenant = timezone.now()
        total_employes = Employe.objects.filter(statut='actif').count()
        nouveaux_ce_mois = Employe.objects.filter(
            date_embauche__month=maintenant.month, date_embauche__year=maintenant.year
        ).count()
        masse_salariale = BulletinPaie.objects.filter(
            periode_fin__month=maintenant.month, periode_fin__year=maintenant.year
        ).aggregate(total=Sum('salaire_net'))['total'] or 0
        conges_en_attente = DemandeConge.objects.filter(statut='en_attente').count()
        employes_par_dept = [
            {'nom': r['nom'], 'nb': r['nb']}
            for r in Departement.objects.annotate(
                nb=Count('employes', filter=Q(employes__statut='actif'))
            ).values('nom', 'nb').order_by('-nb')[:6]
        ]
        return Response({
            'total_employes': total_employes,
            'nouveaux_ce_mois': nouveaux_ce_mois,
            'masse_salariale': float(masse_salariale),
            'conges_en_attente': conges_en_attente,
            'employes_par_departement': employes_par_dept,
        })
