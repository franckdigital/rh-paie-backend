"""
Utilitaire partagé pour générer des rapports PDF tabulaires avec reportlab.
Usage : pdf_table_response(filename, title, subtitle, headers, rows)
"""
import datetime
from io import BytesIO

from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INDIGO = colors.HexColor('#4F46E5')
SLATE_100 = colors.HexColor('#f1f5f9')
SLATE_500 = colors.HexColor('#64748b')
WHITE = colors.white


def pdf_fiche_poste_response(fiche):
    """Generate a formatted PDF document for a single FichePoste."""
    from reportlab.platypus import KeepTogether
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ftitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16,
        textColor=INDIGO, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        'fsub', parent=styles['Normal'],
        fontSize=10, textColor=SLATE_500, spaceAfter=16,
    )
    section_style = ParagraphStyle(
        'fsec', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=INDIGO, spaceBefore=10, spaceAfter=3,
    )
    body_style = ParagraphStyle(
        'fbody', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#1e293b'),
        leading=13, spaceAfter=2,
    )
    footer_style = ParagraphStyle(
        'footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
    )

    niveau_display = dict([
        ('operateur', 'Opérateur'), ('technicien', 'Technicien'),
        ('agent', 'Agent'), ('superviseur', 'Superviseur'),
        ('chef_equipe', "Chef d'équipe"), ('chef_service', 'Chef de service'),
        ('responsable', 'Responsable'), ('directeur', 'Directeur'),
    ]).get(fiche.niveau, fiche.niveau)

    elements = [
        Paragraph(fiche.titre, title_style),
        Paragraph(f"Niveau : {niveau_display}  ·  Expérience min. : {fiche.experience_min_annees} an(s)", sub_style),
        HRFlowable(width='100%', thickness=1.5, color=INDIGO, spaceAfter=12),
    ]

    def add_section(label, text):
        if text and text.strip():
            elements.append(Paragraph(label.upper(), section_style))
            for line in text.strip().splitlines():
                if line.strip():
                    elements.append(Paragraph(f"• {line.strip()}", body_style))

    add_section('Missions principales', fiche.missions)
    add_section('Responsabilités', fiche.responsabilites)
    add_section('Compétences requises', fiche.competences_requises)
    if fiche.formation_requise:
        elements.append(Paragraph('FORMATION REQUISE', section_style))
        elements.append(Paragraph(fiche.formation_requise, body_style))
    add_section('EPI requis', fiche.epi_requis)
    add_section('Horaires applicables', fiche.horaires_applicables)

    generated = datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')
    elements += [
        Spacer(1, 1 * cm),
        HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=6),
        Paragraph(f"Document généré le {generated} — RH & Paie Pro", footer_style),
    ]

    doc.build(elements)
    buf.seek(0)
    filename = f"fiche_poste_{fiche.titre.replace(' ', '_').lower()}.pdf"
    return FileResponse(buf, as_attachment=True, filename=filename, content_type='application/pdf')


def pdf_table_response(filename, title, subtitle, headers, rows, use_landscape=False):
    """Build a PDF table and return a Django FileResponse."""
    buf = _build_pdf(title, subtitle, headers, rows, use_landscape)
    return FileResponse(buf, as_attachment=True, filename=filename, content_type='application/pdf')


def _build_pdf(title, subtitle, headers, rows, use_landscape=False):
    buf = BytesIO()
    pagesize = landscape(A4) if use_landscape else A4
    doc = SimpleDocTemplate(
        buf, pagesize=pagesize,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'title', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=INDIGO, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=9, textColor=SLATE_500, spaceAfter=10,
    )
    footer_style = ParagraphStyle(
        'footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
    )

    page_width = (landscape(A4)[0] if use_landscape else A4[0]) - 3 * cm
    n_cols = len(headers)
    col_w = page_width / n_cols if n_cols else page_width

    table_data = [headers] + (rows if rows else [['—'] * n_cols])
    t = Table(table_data, colWidths=[col_w] * n_cols, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INDIGO),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SLATE_100]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    generated = datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')
    elements = [
        Paragraph(title, title_style),
        Paragraph(subtitle, sub_style),
        HRFlowable(width='100%', thickness=1, color=INDIGO, spaceAfter=8),
        t,
        Spacer(1, 0.5 * cm),
        Paragraph(f"Généré le {generated} — RH & Paie Pro", footer_style),
    ]
    doc.build(elements)
    buf.seek(0)
    return buf
