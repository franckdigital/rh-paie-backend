"""
Génération PDF du bulletin de paie avec reportlab.
Usage : generer_bulletin_pdf(bulletin) → BytesIO
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ─── Couleurs RH & Paie ─────────────────────────────────────────────────────
INDIGO = colors.HexColor('#4F46E5')
SLATE_800 = colors.HexColor('#1e293b')
SLATE_500 = colors.HexColor('#64748b')
SLATE_100 = colors.HexColor('#f1f5f9')
EMERALD = colors.HexColor('#059669')
ROSE = colors.HexColor('#e11d48')
WHITE = colors.white


def _fmt(montant):
    """Formate un montant en FCFA avec séparateur de milliers."""
    try:
        return f"{int(float(montant)):,}".replace(',', ' ') + " FCFA"
    except (ValueError, TypeError):
        return "—"


def _fmt_date(d):
    if not d:
        return '—'
    MOIS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    return f"{MOIS[d.month]} {d.year}"


def generer_bulletin_pdf(bulletin) -> BytesIO:
    """Retourne un BytesIO contenant le PDF du bulletin de paie."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    bold_style = ParagraphStyle('bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    title_style = ParagraphStyle('title', parent=styles['Normal'], fontName='Helvetica-Bold',
                                  fontSize=14, textColor=INDIGO, spaceAfter=4)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=9, textColor=SLATE_500)
    right_style = ParagraphStyle('right', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9)
    center_style = ParagraphStyle('center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)
    net_style = ParagraphStyle('net', parent=styles['Normal'], fontName='Helvetica-Bold',
                                fontSize=13, textColor=EMERALD, alignment=TA_CENTER)

    employe = bulletin.employe
    entreprise = getattr(employe, 'entreprise', None)
    periode = _fmt_date(bulletin.periode_fin)

    elements = []

    # ── En-tête : entreprise + titre ──
    header_data = [
        [
            Paragraph(f"<b>{entreprise.nom if entreprise else 'RH & Paie Pro'}</b>", bold_style),
            Paragraph("BULLETIN DE PAIE", title_style),
        ],
        [
            Paragraph(f"{entreprise.adresse if entreprise else ''}", sub_style),
            Paragraph(f"Période : <b>{periode}</b>", right_style),
        ],
    ]
    header_table = Table(header_data, colWidths=[9 * cm, 9 * cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width='100%', thickness=2, color=INDIGO, spaceAfter=8, spaceBefore=8))

    # ── Identité employé ──
    poste = getattr(employe, 'poste', None)
    departement = getattr(employe, 'departement', None)
    site = getattr(employe, 'site', None)

    emp_data = [
        ['Nom complet', f"{employe.prenom} {employe.nom}", 'Matricule', employe.matricule or '—'],
        ['Poste', poste.titre if poste else '—', 'Département', departement.nom if departement else '—'],
        ['Site', site.nom if site else '—', 'Date embauche', employe.date_embauche.strftime('%d/%m/%Y') if employe.date_embauche else '—'],
    ]
    emp_table = Table(emp_data, colWidths=[4 * cm, 6 * cm, 3 * cm, 5 * cm])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), SLATE_500),
        ('TEXTCOLOR', (2, 0), (2, -1), SLATE_500),
        ('BACKGROUND', (0, 0), (-1, -1), SLATE_100),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [SLATE_100, WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 0.4 * cm))

    # ── Tableau gains & retenues ──
    col_headers = ['Libellé', 'Base', 'Taux', 'Gain', 'Retenue']
    table_data = [col_headers]

    # Salaire de base
    table_data.append([
        'Salaire de base', _fmt(bulletin.salaire_base), '—', _fmt(bulletin.salaire_base), '',
    ])

    # Déduction absence
    if float(bulletin.deduction_absence or 0) > 0:
        table_data.append([
            f"Déduction absence ({bulletin.jours_absents} j.)",
            _fmt(bulletin.salaire_base), f"{bulletin.jours_absents}j",
            '', _fmt(bulletin.deduction_absence),
        ])

    # Heures spéciales
    if float(bulletin.heures_nuit or 0) > 0:
        table_data.append(['Heures de nuit', f"{bulletin.heures_nuit}h", '15%', _fmt(bulletin.montant_heures_nuit), ''])
    if float(bulletin.heures_supp_25 or 0) > 0 or float(bulletin.heures_supp_50 or 0) > 0:
        table_data.append(['Heures supplémentaires', f"{float(bulletin.heures_supp_25) + float(bulletin.heures_supp_50):.1f}h", '25-50%', _fmt(bulletin.montant_heures_supp), ''])
    if float(bulletin.heures_ferie or 0) > 0:
        table_data.append(['Heures fériées', f"{bulletin.heures_ferie}h", '100%', _fmt(bulletin.montant_heures_ferie), ''])

    # Lignes bulletin (gains/retenues)
    for ligne in bulletin.lignes.select_related('element').all():
        taux_str = f"{float(ligne.taux) * 100:.1f}%" if float(ligne.taux or 0) > 0 else '—'
        gain = _fmt(ligne.montant) if ligne.element.type == 'gain' else ''
        retenue = _fmt(ligne.montant) if ligne.element.type == 'retenue' else ''
        table_data.append([ligne.element.nom, _fmt(ligne.base), taux_str, gain, retenue])

    # Séparateur cotisations
    table_data.append(['COTISATIONS SOCIALES', '', '', '', ''])

    # CNPS salarié
    table_data.append(['CNPS salarié (3.6%)', _fmt(bulletin.salaire_brut), '3.6%', '', _fmt(bulletin.cotisation_cnps_employe)])
    # ITS
    table_data.append(['ITS / IRPP', _fmt(bulletin.salaire_brut_imposable), '—', '', _fmt(bulletin.its)])
    # CMU
    table_data.append(['CMU (2%)', _fmt(bulletin.salaire_brut), '2%', '', _fmt(bulletin.cmu)])

    # Total row
    table_data.append(['TOTAUX', '', '', _fmt(bulletin.total_gains), _fmt(bulletin.total_retenues)])

    col_w = [7 * cm, 3.5 * cm, 2.5 * cm, 3 * cm, 2.5 * cm]
    details_table = Table(table_data, colWidths=col_w, repeatRows=1)

    separator_rows = [i for i, row in enumerate(table_data) if row[0] in ('COTISATIONS SOCIALES', 'TOTAUX')]

    style = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), INDIGO),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SLATE_100]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 6),
    ]
    # Section headers
    for r in separator_rows:
        style += [
            ('BACKGROUND', (0, r), (-1, r), colors.HexColor('#e0e7ff')),
            ('FONTNAME', (0, r), (-1, r), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, r), (-1, r), INDIGO),
            ('SPAN', (0, r), (2, r)),
        ]
    # Totaux row (last separator)
    if separator_rows:
        last = separator_rows[-1]
        style += [
            ('BACKGROUND', (0, last), (-1, last), INDIGO),
            ('TEXTCOLOR', (0, last), (-1, last), WHITE),
            ('FONTNAME', (0, last), (-1, last), 'Helvetica-Bold'),
        ]

    details_table.setStyle(TableStyle(style))
    elements.append(details_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Résumé net ──
    net_data = [
        ['Salaire brut', _fmt(bulletin.salaire_brut), 'CNPS patronal (16%)', _fmt(bulletin.cotisation_cnps_patronale)],
        ['Total retenues', _fmt(bulletin.total_retenues), '', ''],
    ]
    net_table = Table(net_data, colWidths=[5 * cm, 4 * cm, 5 * cm, 4 * cm])
    net_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), SLATE_500),
        ('TEXTCOLOR', (2, 0), (2, 0), SLATE_500),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 0), (-1, -1), SLATE_100),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 0.4 * cm))

    # ── Net à payer (bandeau vert) ──
    net_box = Table(
        [[Paragraph(f"NET À PAYER : {_fmt(bulletin.salaire_net_paye)}", net_style)]],
        colWidths=[18 * cm],
    )
    net_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#d1fae5')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('BOX', (0, 0), (-1, -1), 1, EMERALD),
    ]))
    elements.append(net_box)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Pied de page ──
    footer_data = [
        [
            Paragraph("Document généré automatiquement — RH & Paie Pro", center_style),
            Paragraph(
                f"Statut : <b>{bulletin.statut.upper()}</b>"
                + (f" | Payé le {bulletin.date_paiement.strftime('%d/%m/%Y')}" if bulletin.date_paiement else ''),
                right_style,
            ),
        ]
    ]
    footer_table = Table(footer_data, colWidths=[11 * cm, 7 * cm])
    footer_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), SLATE_500),
    ]))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=SLATE_500, spaceBefore=4, spaceAfter=4))
    elements.append(footer_table)

    doc.build(elements)
    buf.seek(0)
    return buf
