from ..shared.exceptions import BusinessRuleViolation
from apps.extraction.adapters.design import DesignAdapter
from ..planning.models import ExtractionPhase, ExtractionStatusChoices
from .dtos import ProtocolCoverageReport


class PhaseLifecycleService:
    
    def get_protocol_questions_for_display(self, project_id: int):
        """
        Obtiene las preguntas del protocolo para mostrar en la UI.
        Retorna List[ResearchQuestionDTO] a través del adapter.
        """
        adapter = DesignAdapter()
        return adapter.get_protocol_questions(project_id)
    
    def get_protocol_coverage(self, phase: ExtractionPhase) -> ProtocolCoverageReport:
        """
        Calcula la cobertura de RQs utilizando el DesignAdapter y lógica de conjuntos.
        """
        # 1. Obtener RQs del proyecto vía Adapter (Devuelve Lista de DTOs, NO QuerySet)
        adapter = DesignAdapter()
        protocol_rqs = adapter.get_protocol_questions(phase.project_id)
        
        if not protocol_rqs:
            return ProtocolCoverageReport(
                is_fully_covered=True, # Si no hay preguntas, técnicamente está cubierto
                missing_rqs=[],
                total_rqs=0,
                covered_count=0
            )

        # 2. Extraer IDs de las preguntas del protocolo (en memoria)
        # Asumimos que el DTO tiene un atributo .id
        protocol_rq_ids = {rq.id for rq in protocol_rqs}
        total_rqs = len(protocol_rqs)

        # 3. Consultar Tags Locales
        covered_rq_ids = set(phase.tags.filter(
            type='DEDUCTIVE',
            status='APPROVED',
            rq_related_id__in=protocol_rq_ids  # Filtramos por los IDs del protocolo
        ).values_list('rq_related_id', flat=True))

        # 4. Calcular métricas usando conjuntos (Sets)
        covered_count = len(covered_rq_ids)
        
        # Calculamos la diferencia de conjuntos: {IDs Protocolo} - {IDs Cubiertos}
        missing_rq_ids = protocol_rq_ids - covered_rq_ids
        
        # Reconstruimos la lista de objetos faltantes filtrando la lista original
        missing_rqs_dtos = [rq for rq in protocol_rqs if rq.id in missing_rq_ids]

        # 5. Determinar si está totalmente cubierto
        is_fully_covered = (total_rqs > 0) and (len(missing_rq_ids) == 0)

        return ProtocolCoverageReport(
            is_fully_covered=is_fully_covered,
            missing_rqs=missing_rqs_dtos, # Ahora pasamos una lista de DTOs, no un QuerySet
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
