"""
ProjectFacade - Fachada para comunicación entre módulos con Project.

Esta fachada expone operaciones que otros módulos necesitan relacionadas
con proyectos SLR, incluyendo acceso a estudios asociados.

Responsabilidades:
- Proveer API simple para otros módulos que necesiten datos de proyectos
- Orquestar llamadas a servicios internos y externos (como Acquisition)
- Ocultar complejidad de relaciones internas
"""

import logging
from typing import Dict, Any, List, Optional

from django.contrib.auth import get_user_model

from apps.project.structure.services.project_services import ProjectService

User = get_user_model()
logger = logging.getLogger(__name__)


class ProjectFacade:
    """
    Fachada principal del módulo de Project.

    Provee una API simple para que otros módulos puedan consultar 
    información de proyectos y sus recursos asociados (estudios, miembros, etc.).
    """

    def __init__(self):
        """Inicializar la fachada con los servicios necesarios."""
        self._project_service = ProjectService()
        logger.info("ProjectFacade initialized")

    # ==========================================================================
    # MÉTODOS DE CONSULTA DE PROYECTOS
    # ==========================================================================

    def get_project(self, project_id: int, user: Optional[User] = None) -> Dict[str, Any]:
        """
        Obtener información básica de un proyecto.

        Args:
            project_id: ID del proyecto
            user: Usuario para verificar permisos (opcional)

        Returns:
            Dict con datos del proyecto
        """
        project = self._project_service.get_project_by_id(project_id, user)
        return {
            "id": project.id,
            "title": project.title,
            "summary": project.summary,
            "owner": str(project.owner) if project.owner else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
        }

    def get_project_members(self, project_id: int, user: Optional[User] = None) -> List[Dict[str, Any]]:
        """
        Obtener miembros de un proyecto.

        Args:
            project_id: ID del proyecto
            user: Usuario para verificar permisos

        Returns:
            Lista de miembros con rol
        """
        project = self._project_service.get_project_by_id(project_id, user)
        members = self._project_service.get_members(project)
        return [
            {
                "user_id": m.user.id,
                "username": m.user.username,
                "role": m.role,
            }
            for m in members
        ]

    # ==========================================================================
    # MÉTODOS DE ESTUDIOS (delegados a AcquisitionFacade)
    # ==========================================================================

    def get_studies_by_project(
        self,
        project_id: int,
        include_metadata: bool = True,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener todos los estudios asociados a un proyecto.

        Los estudios se obtienen a través de la cadena:
        Project → DesignPhase → ResearchQuestion → SearchStrategy → SearchExecution → Study

        Args:
            project_id: ID del proyecto
            include_metadata: Si True, incluye metadatos completos (authors, abstract, etc.)
            status_filter: Opcional, filtrar por estado (discovered, enriched, downloaded, failed)

        Returns:
            Lista de dicts con datos de cada estudio:
            - id: UUID del estudio
            - title: Título
            - source: Fuente académica
            - status: Estado del workflow
            - doi: DOI (si existe)
            - year: Año de publicación
            - download_status: Estado de disponibilidad del PDF
            - (si include_metadata=True): authors, abstract, keywords, journal
        """
        logger.info(f"[PROJECT_FACADE] Getting studies for project {project_id}")

        # Delegar a AcquisitionFacade que ya implementa la lógica
        from apps.acquisition.facade import get_acquisition_facade
        
        acquisition_facade = get_acquisition_facade()
        return acquisition_facade.get_studies_by_project(
            project_id=project_id,
            include_metadata=include_metadata,
            status_filter=status_filter
        )

    def get_studies_count_by_status(self, project_id: int) -> Dict[str, int]:
        """
        Obtener conteo de estudios por estado para un proyecto.

        Útil para dashboards y reportes de progreso.

        Args:
            project_id: ID del proyecto

        Returns:
            Dict con conteos por estado, ej: {"discovered": 10, "enriched": 5, "downloaded": 3}
        """
        logger.info(f"[PROJECT_FACADE] Getting study counts for project {project_id}")

        studies = self.get_studies_by_project(project_id, include_metadata=False)
        
        counts = {}
        for study in studies:
            status = study.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        
        return counts

    def is_healthy(self) -> bool:
        """
        Verificar salud del módulo de Project.

        Returns:
            True si todos los servicios están disponibles
        """
        try:
            return self._project_service is not None
        except Exception as e:
            logger.error(f"[PROJECT_FACADE] Health check failed: {e}")
            return False

    def __str__(self):
        return "ProjectFacade(Project Module Interface)"


# ==============================================================================
# FUNCIÓN DE CONVENIENCIA - Instancia global
# ==============================================================================

_facade_instance = None


def get_project_facade() -> ProjectFacade:
    """
    Obtener instancia global de la fachada de Project.

    Returns:
        ProjectFacade: Instancia inicializada de la fachada
    """
    global _facade_instance

    if _facade_instance is None:
        _facade_instance = ProjectFacade()
        logger.info("Global ProjectFacade instance created")

    return _facade_instance


# ==============================================================================
# EJEMPLOS DE USO
# ==============================================================================

"""
EJEMPLOS DE USO desde otros módulos:

from apps.project.facade import get_project_facade

facade = get_project_facade()

# Obtener todos los estudios de un proyecto
studies = facade.get_studies_by_project(project_id=1)
print(f"El proyecto tiene {len(studies)} estudios")

# Filtrar solo estudios descargados
downloaded = facade.get_studies_by_project(
    project_id=1, 
    status_filter="downloaded"
)

# Obtener conteos para dashboard
counts = facade.get_studies_count_by_status(project_id=1)
print(f"Discovered: {counts.get('discovered', 0)}")
print(f"Enriched: {counts.get('enriched', 0)}")
print(f"Downloaded: {counts.get('downloaded', 0)}")

# Obtener info del proyecto
project_info = facade.get_project(project_id=1)
print(f"Proyecto: {project_info['title']}")
"""
