from ..shared.exceptions import BusinessRuleViolation
from ..planning.models import ExtractionPhase, ExtractionStatusChoices
from .dtos import ProtocolCoverageReport


class PhaseLifecycleService:
    
    def get_protocol_coverage(self, phase: ExtractionPhase) -> ProtocolCoverageReport:
        """
        Calcula la cobertura. Esta es lógica pura de consulta/dominio.
        """
        project_rqs = phase.project.design_phase.research_questions.all()
        total_rqs = project_rqs.count()

        covered_rq_ids = phase.tags.filter(
            rq_related__isnull=False
        ).values_list('rq_related_id', flat=True).distinct()

        covered_count = len(covered_rq_ids)
        is_fully_covered = (total_rqs > 0) and (total_rqs == covered_count)
        
        missing_rqs = project_rqs.exclude(id__in=covered_rq_ids)

        return ProtocolCoverageReport(
            is_fully_covered=is_fully_covered,
            missing_rqs=list(missing_rqs),
            total_rqs=total_rqs,
            covered_count=covered_count
        )

    def attempt_open_phase(self, phase: ExtractionPhase) -> ExtractionPhase:
        """
        Orquesta la validación y la transición.
        """
        coverage = self.get_protocol_coverage(phase)
        
        if not coverage.is_fully_covered:
            missing_text = ", ".join([str(rq.question) for rq in coverage.missing_rqs])
            raise BusinessRuleViolation(
                f"No se puede abrir la fase. Cobertura incompleta. Faltan: {missing_text}"
            )
        phase.transition_to_open()
        
        return phase
