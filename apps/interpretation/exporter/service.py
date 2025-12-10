from typing import Literal, Optional, Dict, Any
from datetime import datetime

from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.proposition_models import InterpretativeProposition
from apps.interpretation.structured_data.manager import StructuredDataManager
from apps.interpretation.visualization.engine import ResultsVisualizationEngine

from .models import ExportPackage
from .exporters import PDFExporter, CSVExporter, JSONExporter


class FindingsExportService:
    """
    Facade for the Findings Exporter component.
    Orchestrates data gathering and export format generation.
    """
    
    def __init__(self):
        self.data_manager = StructuredDataManager()
        self.viz_engine = ResultsVisualizationEngine()
        self.pdf_exporter = PDFExporter()
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
    
    def export_findings(
        self,
        project_id: str,
        export_format: Literal['pdf', 'csv', 'json'] = 'pdf',
        filters: Optional[Dict[str, Any]] = None
    ):
        """
        Exports findings for a project in the specified format.
        """
        # 1. Gather data
        package = self._build_export_package(project_id, filters)
        
        # 2. Generate export based on format
        if export_format == 'pdf':
            return self.pdf_exporter.export(package), 'application/pdf', 'findings.pdf'
        elif export_format == 'csv':
            return self.csv_exporter.export(package), 'text/csv', 'findings.csv'
        elif export_format == 'json':
            return self.json_exporter.export(package), 'application/json', 'findings.json'
        else:
            raise ValueError(f"Unsupported format: {export_format}")
    
    def _build_export_package(self, project_id: str, filters: Optional[Dict[str, Any]] = None) -> ExportPackage:
        """
        Builds an ExportPackage with all necessary data.
        """
        # Get studies
        studies = self.data_manager.get_studies_for_interpretation(project_id, filters)
        
        # Get dashboard data
        dashboard_data = self.viz_engine.generate_dashboard_data(studies)
        
        # Get propositions (findings)
        # Note: Propositions are linked to SubThemes, which are linked to Themes
        # We need to find a way to scope by project. For now, we get all.
        propositions = InterpretativeProposition.objects.filter(
            status=InterpretativeProposition.PropositionStatus.FINAL
        ).select_related('subtheme__theme')
        
        prop_list = []
        for prop in propositions:
            prop_list.append({
                'text': prop.proposition_text,
                'status': prop.status,
                'theme': prop.subtheme.theme.name,
                'subtheme': prop.subtheme.name
            })
        
        # Get themes
        themes = Theme.objects.all()
        theme_names = [t.name for t in themes]
        
        package = ExportPackage(
            project_title=f"Project {project_id}",
            generated_at=datetime.now(),
            total_studies=len(studies),
            themes=theme_names,
            propositions=prop_list,
            bibliometric_data=dashboard_data['bibliometrics'],
            synthesis_matrix=dashboard_data['synthesis']['coverage']
        )
        
        return package
