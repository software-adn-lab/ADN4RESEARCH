from typing import List, Dict, Any, Optional, Tuple, Literal
from datetime import datetime

from apps.interpretation.conclusion_assistant.services.interpretation_services import InterpretationService
from apps.interpretation.dtos import InterpretationFindingsDTO, ThemeDTO, PropositionDTO
from apps.interpretation.exporter.service import FindingsExportService
from apps.interpretation.visualization.engine import ResultsVisualizationEngine
from apps.interpretation.structured_data.manager import StructuredDataManager

class InterpretationFacade:
    """
    Fachada principal del módulo de Interpretation.
    Provee una API pública unificada para acceder a las funcionalidades del módulo.
    """
    
    def __init__(self):
        self._export_service = FindingsExportService()
        self._viz_engine = ResultsVisualizationEngine()
        self._data_manager = StructuredDataManager()
        self._conclusion_service = InterpretationService()
    
    def get_project_findings(self, project_id: str) -> InterpretationFindingsDTO:
        """
        Obtener hallazgos finales de un proyecto.
        
        Args:
            project_id: ID del proyecto
            
        Returns:
            InterpretationFindingsDTO con temas, proposiciones y matriz de síntesis
        """
        # 1. Obtener temas del proyecto
        themes = self._conclusion_service.get_all_themes(project_id)
        themes_data = [{'name': t.name, 'description': t.description} for t in themes]
        
        # 2. Recuperamos proposiciones finales
        final_propositions = self._conclusion_service.get_final_propositions(project_id)
        
        propositions_data = []
        for prop in final_propositions:
            propositions_data.append({
                'id': prop.id,
                'text': prop.proposition_text,
                'status': prop.status,
                'theme': prop.subtheme.theme.name,
                'subtheme': prop.subtheme.name,
                'supporting_narrative': prop.supporting_narrative
            })
            
        # 3. Recuperamos datos de visualización
        studies = self._data_manager.get_studies_for_interpretation(project_id)
        dashboard_data = self._viz_engine.generate_dashboard_data(studies)
        
        return InterpretationFindingsDTO(
            project_id=project_id,
            themes=themes_data,
            propositions=propositions_data,
            synthesis_matrix=dashboard_data.get('synthesis', {}).get('coverage', {}),
            generated_at=datetime.now()
        )
    
    def export_findings(
        self, 
        project_id: str, 
        export_format: Literal['pdf', 'csv', 'json']
    ) -> Tuple[Any, str, str]:
        """
        Exportar hallazgos en formato específico.
        
        Args:
            project_id: ID del proyecto
            export_format: Formato deseado ('pdf', 'csv', 'json')
            
        Returns:
            Tuple(contenido, mime_type, filename)
        """
        return self._export_service.export_findings(project_id, export_format)

# Instancia global
_facade_instance = None

def get_interpretation_facade() -> InterpretationFacade:
    """Obtener instancia global de la fachada de Interpretation."""
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = InterpretationFacade()
    return _facade_instance
