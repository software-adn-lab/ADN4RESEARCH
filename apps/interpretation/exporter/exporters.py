import csv
import json
from io import BytesIO, StringIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from .models import ExportPackage


class PDFExporter:
    """
    Exports findings to PDF format using ReportLab.
    """
    
    def export(self, package: ExportPackage) -> BytesIO:
        """
        Generates a PDF document from the export package.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2086C9'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"Interpretation Report: {package.project_title}", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        story.append(Paragraph(f"<b>Generated:</b> {package.generated_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Studies:</b> {package.total_studies}", styles['Normal']))
        story.append(Paragraph(f"<b>Themes Identified:</b> {', '.join(package.themes)}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Propositions/Findings
        story.append(Paragraph("Interpretative Findings", styles['Heading2']))
        story.append(Spacer(1, 0.1 * inch))
        
        for idx, prop in enumerate(package.propositions, 1):
            story.append(Paragraph(f"<b>Finding {idx}:</b> {prop.get('text', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"<i>Status: {prop.get('status', 'N/A')}</i>", styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
        
        story.append(PageBreak())
        
        # Bibliometric Summary
        story.append(Paragraph("Bibliometric Analysis", styles['Heading2']))
        story.append(Spacer(1, 0.1 * inch))
        
        # Studies per Year Table
        years_data = package.bibliometric_data.get('years', {})
        if years_data.get('labels'):
            year_table_data = [['Year', 'Studies']]
            for year, count in zip(years_data['labels'], years_data['data']):
                year_table_data.append([str(year), str(count)])
            
            table = Table(year_table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2086C9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer


class CSVExporter:
    """
    Exports findings to CSV format.
    """
    
    def export(self, package: ExportPackage) -> StringIO:
        """
        Generates a CSV file with findings data.
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Interpretation Report', package.project_title])
        writer.writerow(['Generated', package.generated_at.strftime('%Y-%m-%d %H:%M')])
        writer.writerow(['Total Studies', package.total_studies])
        writer.writerow([])
        
        # Findings
        writer.writerow(['Finding ID', 'Text', 'Status', 'Theme'])
        for idx, prop in enumerate(package.propositions, 1):
            writer.writerow([
                idx,
                prop.get('text', ''),
                prop.get('status', ''),
                prop.get('theme', '')
            ])
        
        writer.writerow([])
        
        # Bibliometric Data
        writer.writerow(['Bibliometric Analysis'])
        writer.writerow(['Year', 'Count'])
        years_data = package.bibliometric_data.get('years', {})
        if years_data.get('labels'):
            for year, count in zip(years_data['labels'], years_data['data']):
                writer.writerow([year, count])
        
        output.seek(0)
        return output


class JSONExporter:
    """
    Exports findings to JSON format.
    """
    
    def export(self, package: ExportPackage) -> str:
        """
        Generates a JSON representation of the findings.
        """
        data = {
            'project_title': package.project_title,
            'generated_at': package.generated_at.isoformat(),
            'metadata': {
                'total_studies': package.total_studies,
                'themes': package.themes
            },
            'propositions': package.propositions,
            'bibliometric_data': package.bibliometric_data,
            'synthesis_matrix': package.synthesis_matrix
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
