import logging
from typing import Dict, List, Tuple

from django.contrib.auth.models import User
from django.db.models import Sum

from ..shared.exceptions import BusinessRuleViolation
from apps.extraction.adapters.design import DesignAdapter
from apps.project.structure.models.project_models import Membership
from ..planning.models import ExtractionPhase, ExtractionStatusChoices
from .dtos import ProtocolCoverageReport

logger = logging.getLogger(__name__)


class ApprovedPaperDistributionService:
    """
    Distributes approved papers from selection phase among researchers
    based on their workload capacity using a greedy algorithm.
    
    Similar to PaperDistributionService but:
    - Works with specific approved_paper_ids list
    - Doesn't calculate word count (uses simple count)
    - 1 reviewer per paper
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
    
    def distribute_approved_papers(
        self,
        approved_paper_ids: List[str]
    ) -> Dict[int, List[str]]:
        """
        Distribute approved papers among researchers.
        
        Args:
            approved_paper_ids: List of paper UUIDs to distribute
            
        Returns:
            Distribution dict: {user_id: [paper_ids]}
            
        Raises:
            ValueError: If insufficient researchers or no papers
        """
        logger.info(
            f"[EXTRACTION DISTRIBUTION] Starting for {len(approved_paper_ids)} papers "
            f"in project {self.project_id}"
        )
        
        if not approved_paper_ids:
            raise ValueError("No papers to distribute")
        
        # 1. Get researchers with workload
        researchers = self._get_researchers_with_workload()
        if not researchers:
            raise ValueError("No researchers with workload assigned to project")
        
        # 2. Distribute greedily: assign papers to researchers with most capacity
        distribution = self._greedy_distribution(
            approved_paper_ids,
            researchers
        )
        
        logger.info(
            f"[EXTRACTION DISTRIBUTION] Completed: "
            f"{len(approved_paper_ids)} papers to {len(researchers)} researchers"
        )
        
        return distribution
    
    def _get_researchers_with_workload(self) -> List[Tuple[int, str, int]]:
        """
        Get all team members with assigned workload for this project.
        
        Returns:
            List of tuples: (user_id, username, workload_hours)
        """
        memberships = Membership.objects.filter(
            project_id=self.project_id,
            role__in=['OWNER', 'RESEARCHER'],
            workload_hours__gt=0
        ).select_related('user')
        
        researchers = [
            (m.user.id, m.user.username, m.workload_hours)
            for m in memberships
        ]
        
        # Sort by workload descending
        researchers.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(
            f"[EXTRACTION DISTRIBUTION] Found {len(researchers)} team members with workload"
        )
        
        return researchers
    
    def _greedy_distribution(
        self,
        approved_paper_ids: List[str],
        researchers: List[Tuple[int, str, int]]
    ) -> Dict[int, List[str]]:
        """
        Greedy algorithm: assign papers to researchers with most remaining capacity.
        
        Args:
            approved_paper_ids: List of paper IDs to distribute
            researchers: List of (user_id, username, workload_hours)
            
        Returns:
            Distribution dict: {user_id: [paper_ids]}
        """
        # Create capacity tracker: {user_id: {'username': str, 'capacity': float, 'papers': []}}
        capacities = {}
        total_workload = sum(r[2] for r in researchers)
        total_papers = len(approved_paper_ids)
        
        for user_id, username, workload in researchers:
            # Proportional capacity (number of papers each researcher should get)
            proportion = workload / total_workload
            capacity = proportion * total_papers
            
            capacities[user_id] = {
                'username': username,
                'capacity': capacity,
                'remaining': capacity,
                'papers': []
            }
        
        logger.info(
            f"[EXTRACTION DISTRIBUTION] Total papers: {total_papers}, "
            f"Total workload: {total_workload} hours"
        )
        
        # Assign papers using greedy algorithm
        for paper_id in approved_paper_ids:
            # Find user with most remaining capacity who hasn't been assigned this paper
            best_user = max(
                capacities.keys(),
                key=lambda uid: capacities[uid]['remaining']
            )
            
            capacities[best_user]['papers'].append(str(paper_id))
            capacities[best_user]['remaining'] -= 1
            
            logger.debug(
                f"[EXTRACTION DISTRIBUTION] Assigned paper {paper_id} to "
                f"{capacities[best_user]['username']} "
                f"(remaining: {capacities[best_user]['remaining']:.1f})"
            )
        
        # Convert to output format
        distribution = {
            uid: data['papers']
            for uid, data in capacities.items()
        }
        
        # Log summary
        for uid, papers_list in distribution.items():
            if papers_list:
                logger.info(
                    f"[EXTRACTION DISTRIBUTION] "
                    f"{capacities[uid]['username']}: {len(papers_list)} papers assigned"
                )
        
        return distribution


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
