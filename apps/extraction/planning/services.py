from ..shared.exceptions import BusinessRuleViolation
from ..planning.models import ExtractionPhase, ExtractionStatusChoices
from .dtos import ProtocolCoverageReport


class PhaseLifecycleService:
    
    def get_protocol_coverage(self, phase: ExtractionPhase) -> ProtocolCoverageReport:
        """
        Calcula la cobertura de RQs basado en tags DEDUCTIVOS aprobados.
        
        Business Rules:
        - Solo se consideran tags DEDUCTIVOS (type='DEDUCTIVE')
        - Solo se consideran tags APROBADOS (status='APPROVED')
        - Solo se consideran tags con RQ relacionada (rq_related__isnull=False)
        - Una RQ está cubierta si existe AL MENOS UN tag deductivo aprobado que la referencia
        
        Args:
            phase: Fase de extracción a evaluar
            
        Returns:
            ProtocolCoverageReport con el estado de cobertura
        """
        # 1. Obtener RQs del proyecto
        protocol_rqs = phase.project.design_phase.research_questions.only("id")
        protocol_rq_ids = protocol_rqs.values_list("id", flat=True)
        total_rqs = protocol_rqs.count()


        # 2. ✅ CORREGIDO: Filtrar solo tags DEDUCTIVOS aprobados con RQ
        covered_rq_ids = phase.tags.filter(
            type='DEDUCTIVE',              # ✅ Solo deductivos
            status='APPROVED',             # ✅ Solo aprobados
            rq_related__isnull=False       # ✅ Solo con RQ asignada
        ).values_list('rq_related_id', flat=True).distinct()

        covered_count = phase.tags.filter(
            type='DEDUCTIVE',
            status='APPROVED',
            rq_related__in=protocol_rq_ids
        ).values('rq_related_id').distinct().count()

        
        # 3. Una fase está completamente cubierta si:
        #    - Tiene al menos 1 RQ en el protocolo
        #    - Todas las RQs tienen al menos un tag deductivo aprobado
        is_fully_covered = (total_rqs > 0) and (total_rqs == covered_count)
        
        # 4. RQs faltantes (devolver QuerySet, no lista)
        missing_rqs = protocol_rqs.exclude(
            id__in=phase.tags.filter(
                    type='DEDUCTIVE',
                    status='APPROVED',
                    rq_related__in=protocol_rq_ids
                ).values('rq_related_id')
        )


        return ProtocolCoverageReport(
            is_fully_covered=is_fully_covered,
            missing_rqs=missing_rqs,  # QuerySet
            total_rqs=total_rqs,
            covered_count=covered_count
        )

    def attempt_open_phase(self, phase: ExtractionPhase) -> ExtractionPhase:
        """
        Orquesta la validación y la transición de estado.
        
        Business Rules:
        - Solo se puede abrir una fase si está en estado CONFIG
        - Todas las RQs del protocolo deben estar cubiertas por tags deductivos aprobados
        
        Args:
            phase: Fase de extracción a abrir
            
        Returns:
            Fase actualizada en estado OPEN
            
        Raises:
            BusinessRuleViolation: Si la cobertura es incompleta o el estado es incorrecto
        """
        # 1. Validar que la fase esté en CONFIG
        if phase.status != ExtractionStatusChoices.CONFIG:
            raise BusinessRuleViolation(
                f"No se puede abrir la fase. Estado actual: {phase.get_status_display()}. "
                f"Solo se pueden abrir fases en estado CONFIG."
            )
        
        # 2. Validar cobertura
        coverage = self.get_protocol_coverage(phase)
        
        if not coverage.is_fully_covered:
            missing_text = ", ".join([
                f"RQ #{rq.id}: {rq.question_text[:50]}" 
                for rq in coverage.missing_rqs
            ])
            raise BusinessRuleViolation(
                f"No se puede abrir la fase. Cobertura incompleta "
                f"({coverage.coverage_fraction_display} RQs cubiertas). "
                f"Faltan: {missing_text}"
            )
        
        # 3. Realizar transición
        phase.transition_to_open()
        
        return phase