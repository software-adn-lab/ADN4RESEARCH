from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from django.db import transaction
from django.core.exceptions import ValidationError

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
            label = DesignPhase.DesignStage(stage_key).label

            timeline_stages.append({
                'key': stage_key,
                'label': label,
                'status': status
            })
        return timeline_stages

    
    def consolidate_research_question_stage(self, project_id: int, user):
        
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.RQ_DISCUSSION:
            raise ValidationError(f"Cannot consolidate Questions. Current stage is {phase.current_stage}")
        service = ResearchQuestionService()
        service.finalize_questions_stage(project_id, user)
        phase.current_stage = DesignPhase.DesignStage.CRITERIA_DEFINITION
        phase.save()
        
        return phase

    def consolidate_eligibility_criteria_stage(self, project_id: int, user):
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.CRITERIA_DEFINITION:
            raise ValidationError(f"Cannot consolidate Criteria. Current stage is {phase.current_stage}")
        service = EligibilityCriterionService()
        service.finalize_criteria_stage(project_id, user)
        phase.current_stage = DesignPhase.DesignStage.SEARCH_STRATEGY
        phase.save()
        
        return phase

    def consolidate_search_strategy_stage(self, project_id: int, user):
        phase = DesignPhase.objects.get(pk=project_id)
        if phase.current_stage != DesignPhase.DesignStage.SEARCH_STRATEGY:
            raise ValidationError(f"Cannot consolidate Strategy. Current stage is {phase.current_stage}")

        search_service = SearchStrategyService()
        acquisition_facade = get_acquisition_facade()
        approved_strategy_ids = search_service.finalize_strategies_stage(project_id, user)
        phase.current_stage = DesignPhase.DesignStage.FINISHED
        phase.save()
        for strategy_id in approved_strategy_ids:
            try:
                preview_result = search_service.get_search_results_dto(strategy_id)
                acquisition_facade.finalize_search(
                    design_strategy_id=strategy_id,
                    preview_result=preview_result,
                    user=user
                )         
            except Exception as e:
                raise ValidationError(f"Error persisting strategy {strategy_id}: {str(e)}")
        return phase
