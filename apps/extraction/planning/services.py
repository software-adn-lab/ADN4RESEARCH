import random
from datetime import date
from typing import Dict, List, Any, Optional
from django.db import transaction
from django.utils import timezone

from .repositories import ExtractionPhaseRepository, PaperAssignmentRepository
from .models import ExtractionPhase, PaperAssignment, ExtractionPhaseStatus
from ..core.repositories import ExtractionRepository
from ..core.models import ExtractionStatus
from ..taxonomy.services import TagService
from ..shared.exceptions import BusinessRuleViolation, ResourceNotFound


class ExtractionPhaseService:
    """
    Servicio para gestionar la configuración y activación de la fase de extracción.
    Solo accesible por usuarios con rol de Owner.
    """

    def __init__(self):
        self.phase_repo = ExtractionPhaseRepository()
        self.assignment_repo = PaperAssignmentRepository()
        self.extraction_repo = ExtractionRepository()
        self.tag_service = TagService()

    def get_or_create_phase(self, project_id: int) -> ExtractionPhase:
        """Obtiene o crea la fase de extracción para un proyecto"""
        return self.phase_repo.get_or_create(project_id)

    def get_phase_status(self, project_id: int) -> Dict[str, Any]:
        """Obtiene el estado actual de la fase de extracción"""
        phase = self.phase_repo.get_by_project(project_id)
        if not phase:
            return {
                "exists": False,
                "status": None,
                "message": "No existe fase de extracción para este proyecto"
            }

        assignments = self.assignment_repo.list_by_phase(phase.id)
        
        return {
            "exists": True,
            "id": phase.id,
            "status": phase.status,
            "end_date": phase.end_date.isoformat() if phase.end_date else None,
            "auto_close": phase.auto_close,
            "is_active": phase.is_active,
            "is_configurable": phase.is_configurable,
            "total_assignments": len(assignments),
            "activated_at": phase.activated_at.isoformat() if phase.activated_at else None,
        }

    @transaction.atomic
    def configure_phase(self, project_id: int, owner_id: int, 
                        end_date: date = None, auto_close: bool = False) -> ExtractionPhase:
        """
        Configura los parámetros de la fase de extracción.
        Puede llamarse tanto en estado Configuración como Activa.
        """
        phase = self.get_or_create_phase(project_id)
        
        if phase.is_closed:
            raise BusinessRuleViolation("No se puede modificar una fase cerrada")

        if end_date:
            phase.end_date = end_date
        phase.auto_close = auto_close
        phase.configured_by_id = owner_id

        return self.phase_repo.save(phase)

    def validate_activation_requirements(self, project_id: int) -> Dict[str, Any]:
        """
        Valida si la fase cumple los requisitos para activarse.
        Retorna un diccionario con los requisitos y su estado.
        """
        phase = self.phase_repo.get_by_project(project_id)
        
        requirements = {
            "has_end_date": phase.end_date is not None if phase else False,
            "has_mandatory_tags": False,
            "has_papers": False,
            "has_researchers": False,
            "all_met": False
        }

        if not phase:
            return requirements

        # Verificar tags obligatorios
        mandatory_tags = self.tag_service.get_mandatory_tags(project_id)
        requirements["has_mandatory_tags"] = len(mandatory_tags) > 0

        # Para papers y researchers necesitamos datos externos (mock)
        # En producción esto vendría de Acquisition y Projects services
        requirements["has_papers"] = True  # Asumimos que hay papers
        requirements["has_researchers"] = True  # Asumimos que hay researchers

        requirements["all_met"] = all([
            requirements["has_end_date"],
            requirements["has_mandatory_tags"],
            requirements["has_papers"],
            requirements["has_researchers"]
        ])

        return requirements

    @transaction.atomic
    def activate_phase(self, project_id: int, owner_id: int,
                       paper_ids: List[int], researcher_ids: List[int]) -> ExtractionPhase:
        """
        Activa la fase de extracción y asigna papers a researchers aleatoriamente.
        
        Args:
            project_id: ID del proyecto
            owner_id: ID del usuario Owner
            paper_ids: Lista de IDs de papers a asignar
            researcher_ids: Lista de IDs de researchers disponibles
        """
        phase = self.phase_repo.get_by_project(project_id)
        
        if not phase:
            raise ResourceNotFound("No existe fase de extracción para este proyecto")

        if not phase.is_configurable:
            raise BusinessRuleViolation(
                f"La fase no puede activarse. Estado actual: {phase.status}"
            )

        # Validar requisitos
        if not phase.end_date:
            raise BusinessRuleViolation("Debe configurar la fecha de cierre")

        mandatory_tags = self.tag_service.get_mandatory_tags(project_id)
        if not mandatory_tags:
            raise BusinessRuleViolation("Debe definir al menos un tag obligatorio")

        if not paper_ids:
            raise BusinessRuleViolation("No hay papers para asignar")

        if not researcher_ids:
            raise BusinessRuleViolation("No hay researchers disponibles")

        # Asignar papers aleatoriamente
        self._assign_papers_randomly(phase, paper_ids, researcher_ids, owner_id)

        # Crear registros de PaperExtraction
        self._create_paper_extractions(phase, paper_ids)

        # Activar la fase
        phase.status = ExtractionPhaseStatus.ACTIVE
        phase.activated_at = timezone.now()

        return self.phase_repo.save(phase)

    def _assign_papers_randomly(self, phase: ExtractionPhase, paper_ids: List[int],
                                 researcher_ids: List[int], owner_id: int):
        """Asigna papers a researchers de forma aleatoria y balanceada"""
        # Eliminar asignaciones anteriores si existen
        self.assignment_repo.delete_by_phase(phase.id)

        # Mezclar papers aleatoriamente
        shuffled_papers = paper_ids.copy()
        random.shuffle(shuffled_papers)

        # Crear asignaciones balanceadas
        assignments = []
        for idx, paper_id in enumerate(shuffled_papers):
            researcher_id = researcher_ids[idx % len(researcher_ids)]
            assignment = PaperAssignment(
                extraction_phase=phase,
                study_id=paper_id,
                researcher_id=researcher_id,
                assigned_by_id=owner_id
            )
            assignments.append(assignment)

        self.assignment_repo.bulk_create(assignments)

    def _create_paper_extractions(self, phase: ExtractionPhase, paper_ids: List[int]):
        """Crea registros de PaperExtraction para cada paper"""
        for paper_id in paper_ids:
            # Verificar si ya existe
            existing = self.extraction_repo.get_by_study_id(paper_id)
            if not existing:
                self.extraction_repo.create_extraction(
                    study_id=paper_id,
                    project_id=phase.project_id
                )

    @transaction.atomic
    def reassign_paper(self, project_id: int, study_id: int, 
                       new_researcher_id: int, owner_id: int) -> PaperAssignment:
        """
        Reasigna un paper a otro researcher.
        Solo disponible cuando la fase está activa.
        """
        phase = self.phase_repo.get_by_project(project_id)
        
        if not phase:
            raise ResourceNotFound("No existe fase de extracción")

        if not phase.is_active:
            raise BusinessRuleViolation("Solo se pueden reasignar papers en fase activa")

        assignment = self.assignment_repo.get_by_study_and_phase(study_id, phase.id)
        if not assignment:
            raise ResourceNotFound(f"No existe asignación para el paper {study_id}")

        # Actualizar también el assigned_to en PaperExtraction
        extraction = self.extraction_repo.get_by_study_id(study_id)
        if extraction:
            extraction.assigned_to_id = new_researcher_id
            self.extraction_repo.save(extraction)

        return self.assignment_repo.update_assignment(
            assignment, new_researcher_id, owner_id
        )

    def get_assignments_by_researcher(self, project_id: int, 
                                       researcher_id: int) -> List[Dict[str, Any]]:
        """Obtiene los papers asignados a un researcher"""
        phase = self.phase_repo.get_by_project(project_id)
        if not phase:
            return []

        assignments = self.assignment_repo.list_by_researcher(researcher_id, phase.id)
        
        result = []
        for assignment in assignments:
            extraction = self.extraction_repo.get_by_study_id(assignment.study_id)
            result.append({
                "study_id": assignment.study_id,
                "assigned_at": assignment.assigned_at.isoformat(),
                "extraction_id": extraction.id if extraction else None,
                "extraction_status": extraction.status if extraction else None,
            })

        return result

    def get_all_assignments(self, project_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las asignaciones de la fase (para el Owner)"""
        phase = self.phase_repo.get_by_project(project_id)
        if not phase:
            return []

        assignments = self.assignment_repo.list_by_phase(phase.id)
        
        return [{
            "study_id": a.study_id,
            "researcher_id": a.researcher_id,
            "assigned_at": a.assigned_at.isoformat(),
        } for a in assignments]

    @transaction.atomic
    def close_phase(self, project_id: int, owner_id: int) -> ExtractionPhase:
        """Cierra manualmente la fase de extracción"""
        phase = self.phase_repo.get_by_project(project_id)
        
        if not phase:
            raise ResourceNotFound("No existe fase de extracción")

        if not phase.is_active:
            raise BusinessRuleViolation("Solo se puede cerrar una fase activa")

        phase.status = ExtractionPhaseStatus.CLOSED
        phase.closed_at = timezone.now()

        return self.phase_repo.save(phase)
