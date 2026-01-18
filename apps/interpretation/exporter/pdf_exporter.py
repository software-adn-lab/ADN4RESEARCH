import io
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch, cm

from apps.interpretation.conclusion_assistant.models import Theme, ThemeDiscoveryProposal, NormalizedCode
from apps.extraction.taxonomy.models import Tag
from apps.extraction.core.models import Quote

from apps.project.structure.models.project_models import Project
from django.utils import timezone

logger = logging.getLogger(__name__)

class BasePdfExporter:
    """Base class for PDF exporters with shared styles and helpers."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = self.styles['Heading1']
        self.h2_style = self.styles['Heading2']
        self.h3_style = self.styles['Heading3']
        self.normal_style = self.styles['Normal']
        self.code_style = ParagraphStyle(
            'CodeStyle',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=10,
            textColor=colors.darkblue
        )
        self.quote_style = ParagraphStyle(
            'QuoteStyle',
            parent=self.styles['Italic'],
            leftIndent=20,
            textColor=colors.darkgreen
        )
        self.citation_style = ParagraphStyle(
            'CitationStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.gray,
            leftIndent=20
        )

    def _get_linked_codes(self, theme: Theme) -> list[NormalizedCode]:
        """
        Attempts to find normalized codes linked to this theme.
        Strategy 1: Check if there is a ThemeDiscoveryProposal linked to this theme.
        Strategy 2: If manual, parse subthemes 'central_codes'.
        """
        proposal = ThemeDiscoveryProposal.objects.filter(
            project=theme.project,
            theme_name=theme.name,
            status__in=['ACCEPTED', 'MODIFIED']
        ).first()
        
        if proposal:
            return list(proposal.codes_used.all())
            
        codes = set()
        for subtheme in theme.subthemes.all():
            for code_str in subtheme.central_codes:
                matches = NormalizedCode.objects.filter(code__iexact=code_str, project=theme.project)
                codes.update(matches)
        
        return list(codes)

    def _add_traceability_section(self, elements: list, theme: Theme):
        """Adds readability analysis for a theme to the elements list."""
        elements.append(Paragraph("Traceability Analysis", self.h2_style))
        elements.append(Paragraph("Evidence gathered from extraction module linking to this theme.", self.normal_style))
        elements.append(Spacer(1, 0.5*cm))

        normalized_codes = self._get_linked_codes(theme)
        
        if not normalized_codes:
            elements.append(Paragraph("No direct code traceability found.", self.normal_style))
        
        for n_code in normalized_codes:
            elements.append(Paragraph(f"Code: {n_code.code}", self.h3_style))
            elements.append(Paragraph(f"Original Tags: {', '.join(n_code.original_codes)}", self.code_style))
            elements.append(Spacer(1, 0.2*cm))
            
            evidence_found = False
            for tag_name in n_code.original_codes:
                tags = Tag.objects.filter(
                    name__iexact=tag_name, 
                    extraction_phase__project=theme.project
                )
                
                for tag in tags:
                    quotes = Quote.objects.filter(tags=tag).select_related('paper_extraction', 'paper_extraction__study')
                    
                    if quotes.exists():
                        evidence_found = True
                        for quote in quotes:
                            study = quote.paper_extraction.study
                            paper_title = study.title
                            authors = ", ".join(study.authors) if study.authors else "Unknown Authors"
                            year = study.publication_year or "n.d."
                            citation_ref = f"{authors} ({year})"
                            
                            elements.append(Paragraph(f"\"{quote.text_fragment}\"", self.quote_style))
                            elements.append(Paragraph(f"Source: {citation_ref} - {paper_title}", self.citation_style))
                            elements.append(Spacer(1, 0.1*cm))
            
            if not evidence_found:
                elements.append(Paragraph("No specific text quotes found linked to this code.", self.styles['Italic']))
            
            elements.append(Spacer(1, 0.5*cm))


class ThemePdfExporter(BasePdfExporter):
    """Service to export a single Theme data with full traceability to PDF."""
    
    def generate_pdf(self, theme: Theme) -> bytes:
        """Generates a PDF byte stream for the given theme."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        
        # --- HEADER ---
        elements.append(Paragraph(f"Theme Report: {theme.name}", self.title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # --- METADATA ---
        data = [
            ["Description:", Paragraph(theme.description, self.normal_style)],
            ["Research Question:", Paragraph(theme.research_question, self.normal_style)],
            ["Project:", theme.project.title if theme.project else "N/A"],
            ["Created By:", theme.created_by.get_full_name() or theme.created_by.username],
            ["Date:", theme.created_at.strftime("%Y-%m-%d")],
        ]
        
        active_phase = getattr(theme.project, "interpretation_phase", None)
        if active_phase and active_phase.is_active:
             data.append(["Status:", "Interpretation Active"])

        t = Table(data, colWidths=[4*cm, 11*cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 1*cm))
        
        # --- SUBTHEMES ---
        if theme.subthemes.exists():
            elements.append(Paragraph("Subthemes", self.h2_style))
            for sub in theme.subthemes.all():
                elements.append(Paragraph(f"• {sub.name}", self.normal_style))
            elements.append(Spacer(1, 0.5*cm))

        # --- TRACEABILITY ANALYSIS ---
        elements.append(PageBreak())
        self._add_traceability_section(elements, theme)
            
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


class ProjectPdfExporter(BasePdfExporter):
    """Service to export a full Project Interpretation Report to PDF."""

    def generate_project_pdf(self, project: Project) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        themes = Theme.objects.filter(project=project)
        
        # --- COVER PAGE ---
        elements.append(Paragraph("Interpretation Final Report", self.title_style))
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Project: {project.title}", self.h2_style))
        elements.append(Paragraph(f"Date: {timezone.now().strftime('%Y-%m-%d')}", self.normal_style))
        elements.append(Spacer(1, 2*cm))
        
        if project.summary:
            elements.append(Paragraph("Project Summary", self.h2_style))
            elements.append(Paragraph(project.summary, self.normal_style))
        
        elements.append(PageBreak())
        
        # --- THEMES ITERATION ---
        if not themes.exists():
            elements.append(Paragraph("No themes generated for this project.", self.normal_style))
        
        for i, theme in enumerate(themes):
            # Theme Title
            elements.append(Paragraph(f"Theme {i+1}: {theme.name}", self.title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Theme Description
            if theme.description:
                elements.append(Paragraph(f"<b>Description:</b> {theme.description}", self.normal_style))
            elements.append(Paragraph(f"<b>Research Question Focus:</b> {theme.research_question}", self.normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Subthemes
            if theme.subthemes.exists():
                elements.append(Paragraph("Subthemes & Findings", self.h2_style))
                for sub in theme.subthemes.all():
                    elements.append(Paragraph(f"• {sub.name}", self.h3_style))
                    # Check for finalized findings
                    # Note: We need to import InterpretativeProposition inside or at top. 
                    # Assuming it's imported or we lazily import to avoid circular dep if needed.
                    # Since models import is fine at top, let's assume it's there or we add it.
                    try:
                        from apps.interpretation.conclusion_assistant.models.proposition_models import InterpretativeProposition
                        propositions = InterpretativeProposition.objects.filter(
                            subtheme=sub, status='FINAL'
                        )
                        if propositions.exists():
                             elements.append(Paragraph("Key Findings:", self.styles['Italic']))
                             for prop in propositions:
                                 elements.append(Paragraph(f"- {prop.proposition_text}", self.normal_style))
                    except ImportError:
                        pass
                    
                    elements.append(Spacer(1, 0.2*cm))
            
            # Traceability for this theme
            elements.append(Spacer(1, 0.5*cm))
            self._add_traceability_section(elements, theme)
            
            # Page break after each theme (except the last one maybe, but logic is simpler with break)
            elements.append(PageBreak())
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
