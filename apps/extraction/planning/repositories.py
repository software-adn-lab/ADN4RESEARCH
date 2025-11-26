from typing import List, Optional
from .models import ExtractionPhase, PaperAssignment, ExtractionPhaseStatus


class ExtractionPhaseRepository:
    """Repository para ExtractionPhase"""

    def get_by_project(self, project_id: int) -> Optional[ExtractionPhase]:
        try:
            return ExtractionPhase.objects.get(project_id=project_id)
        except ExtractionPhase.DoesNotExist:
            return None

    def get_by_id(self, phase_id: int) -> Optional[ExtractionPhase]:
        try:
            return ExtractionPhase.objects.get(id=phase_id)
        except ExtractionPhase.DoesNotExist:
            return None

    def create(self, project_id: int, **kwargs) -> ExtractionPhase:
        return ExtractionPhase.objects.create(project_id=project_id, **kwargs)

    def save(self, phase: ExtractionPhase) -> ExtractionPhase:
        phase.save()
        return phase

    def get_or_create(self, project_id: int) -> ExtractionPhase:
        phase, created = ExtractionPhase.objects.get_or_create(
            project_id=project_id,
            defaults={'status': ExtractionPhaseStatus.CONFIGURATION}
        )
        return phase


class PaperAssignmentRepository:
    """Repository para PaperAssignment"""

    def get_by_study_and_phase(self, study_id: int, phase_id: int) -> Optional[PaperAssignment]:
        try:
            return PaperAssignment.objects.get(
                study_id=study_id,
                extraction_phase_id=phase_id
            )
        except PaperAssignment.DoesNotExist:
            return None

    def list_by_researcher(self, researcher_id: int, phase_id: int) -> List[PaperAssignment]:
        return list(PaperAssignment.objects.filter(
            researcher_id=researcher_id,
            extraction_phase_id=phase_id
        ))

    def list_by_phase(self, phase_id: int) -> List[PaperAssignment]:
        return list(PaperAssignment.objects.filter(extraction_phase_id=phase_id))

    def create(self, phase: ExtractionPhase, study_id: int, researcher_id: int, 
               assigned_by_id: int = None) -> PaperAssignment:
        return PaperAssignment.objects.create(
            extraction_phase=phase,
            study_id=study_id,
            researcher_id=researcher_id,
            assigned_by_id=assigned_by_id
        )

    def bulk_create(self, assignments: List[PaperAssignment]) -> List[PaperAssignment]:
        return PaperAssignment.objects.bulk_create(assignments)

    def update_assignment(self, assignment: PaperAssignment, 
                          new_researcher_id: int, assigned_by_id: int = None) -> PaperAssignment:
        assignment.researcher_id = new_researcher_id
        assignment.assigned_by_id = assigned_by_id
        assignment.save()
        return assignment

    def delete_by_phase(self, phase_id: int):
        PaperAssignment.objects.filter(extraction_phase_id=phase_id).delete()

    def get_researcher_for_study(self, study_id: int, phase_id: int) -> Optional[int]:
        """Retorna el researcher_id asignado a un study"""
        assignment = self.get_by_study_and_phase(study_id, phase_id)
        return assignment.researcher_id if assignment else None
