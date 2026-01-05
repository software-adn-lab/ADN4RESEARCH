from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.design.design_phase_logic.models.design_phase import DesignPhase, DesignStageLog
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.acquisition.facade import get_acquisition_facade

class DesignPhaseService:

    def get_current_stage_deadline(self, project_id: int):
        try:
            phase = DesignPhase.objects.get(pk=project_id)
            return phase.end_date
        except DesignPhase.DoesNotExist:
            return None

    def get_design_timeline_context(self, project_id: int):
        """
        Retorna el estado de la línea de tiempo para el frontend.
        """
        try:
            phase = DesignPhase.objects.get(pk=project_id)
        except DesignPhase.DoesNotExist:
            return []

        current_stage = phase.current_stage
        design_flow = DesignPhase.DESIGN_FLOW
        timeline_stages = []
        is_past = True
        
        for stage_key in design_flow:
            status = 'upcoming'
            if stage_key == current_stage:
                is_past = False
                status = 'current'
            elif stage_key == DesignPhase.DesignStage.FINISHED:
                status = 'finished'
            elif is_past:
                status = 'completed'
            
            # Recuperamos la etiqueta legible del enum
            label = DesignPhase.DesignStage(stage_key).label

            timeline_stages.append({
                'key': stage_key,
                'label': label,
                'status': status
            })
        return timeline_stages

    @transaction.atomic
    def consolidate_research_question_stage(self, project_id: int, user):
        """
        Cierra la etapa de Preguntas e inicia Criterios.
        """
        phase = DesignPhase.objects.get(pk=project_id)
        
        if phase.current_stage != DesignPhase.DesignStage.RQ_DISCUSSION:
            raise ValidationError(f"Cannot consolidate Questions. Current stage is {phase.current_stage}")
        
        # 1. Ejecutar lógica de dominio específica del sub-módulo
        service = ResearchQuestionService()
        service.finalize_questions_stage(project_id, user)
        
        # 2. Transición de estado con auditoría
        self._transition_stage(phase, DesignPhase.DesignStage.CRITERIA_DEFINITION)
        
        return phase

    @transaction.atomic
    def consolidate_eligibility_criteria_stage(self, project_id: int, user):
        """
        Cierra la etapa de Criterios e inicia Estrategia de Búsqueda.
        """
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.CRITERIA_DEFINITION:
            raise ValidationError(f"Cannot consolidate Criteria. Current stage is {phase.current_stage}")
        # 1. Ejecutar lógica de dominio específica del sub-módulo
        service = EligibilityCriterionService()
        service.finalize_criteria_stage(project_id, user)
        # 2. Transición de estado con auditoría
        self._transition_stage(phase, DesignPhase.DesignStage.SEARCH_STRATEGY)
        
        return phase

    @transaction.atomic
    def consolidate_search_strategy_stage(self, project_id: int, user):
        """
        Cierra la etapa de Estrategia y Finaliza la Fase de Diseño.
        """
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.SEARCH_STRATEGY:
            raise ValidationError(f"Cannot consolidate Strategy. Current stage is {phase.current_stage}")
        # 1. Ejecutar lógica de dominio específica del sub-módulo
        search_service = SearchStrategyService()
        acquisition_facade = get_acquisition_facade()
        approved_strategy_ids = search_service.finalize_strategies_stage(project_id, user)
        # 2. Transición de estado con auditoría
        self._transition_stage(phase, DesignPhase.DesignStage.FINISHED)
        
        # 3. Disparar procesos externos (Acquisition)
        # Nota: Esto podría ir en un evento/señal para desacoplar más, pero por ahora es válido aquí.
        for strategy_id in approved_strategy_ids:
            try:
                preview_result = search_service.get_search_results_dto(strategy_id)
                acquisition_facade.finalize_search(
                    design_strategy_id=strategy_id,
                    preview_result=preview_result,
                    user=user
                )         
            except Exception as e:
                # Si falla la integración, hacemos rollback de toda la transacción
                raise ValidationError(f"Error persisting strategy {strategy_id}: {str(e)}")       
        return phase

    def _transition_stage(self, phase: DesignPhase, next_stage: str):
        """
        Método helper privado para manejar la lógica repetitiva de cerrar logs y abrir nuevos.
        Garantiza la trazabilidad (RNF-03).
        """
        # 1. Cerrar el log de la etapa actual
        # Buscamos el último log abierto para esta etapa
        current_log = DesignStageLog.objects.filter(
            phase=phase, 
            stage=phase.current_stage, 
            end_date__isnull=True
        ).last()
        
        if current_log:
            current_log.end_date = timezone.now()
            current_log.save()
        # 2. Actualizar la fase
        phase.current_stage = next_stage
        phase.save() # El método save() del modelo maneja el is_active = False si es FINISHED
        # 3. Crear el log para la nueva etapa (si no es el estado final de cierre)
        if next_stage != DesignPhase.DesignStage.FINISHED:
            DesignStageLog.objects.create(
                phase=phase,
                stage=next_stage,
                start_date=timezone.now()
            )