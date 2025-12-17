
from apps.design.shared.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
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

    def consolidate_search_strategy_stage(self, project_id: int, user):
        phase = DesignPhase.objects.get(pk=project_id)
        self._validate_all_questions_have_strategies(project_id)
        approved_strategy_ids = []
        with transaction.atomic():
            approved_strategy_ids = self._reject_draft_strategies(project_id)
            self._advance_project_stage(phase)
        self._persist_approved_search_results(approved_strategy_ids, user)
        return phase

    def _validate_all_questions_have_strategies(self, project_id: int):
        approved_questions = ResearchQuestion.objects.filter(
            design_phase_id=project_id,
            status=ResearchQuestion.Status.APPROVED
        )
        for question in approved_questions:
            if not SearchStrategy.objects.filter(research_question=question).exists():
                raise ValidationError(f"Research Question '{question.question[:50]}...' does not have a search strategy defined.")

    def _reject_draft_strategies(self, project_id: int) -> list[int]:
        """
        Rejects DRAFT versions of all strategies in the project.
        Returns a list of IDs of APPROVED strategies that need persistence.
        """
        approved_ids = []
        strategies = SearchStrategy.objects.filter(research_question__design_phase_id=project_id)
        for strategy in strategies:
            strategy.versions.filter(status=SearchStrategy.Status.DRAFT).update(status=SearchStrategy.Status.REJECTED)
            if strategy.status == SearchStrategy.Status.APPROVED:
                approved_ids.append(strategy.id)
        return approved_ids

    def _advance_project_stage(self, phase: DesignPhase):
        if phase.current_stage == DesignPhase.DesignStage.SEARCH_STRATEGY:
            phase.current_stage = DesignPhase.DesignStage.FINISHED
            phase.save()
        else:
            raise ValidationError("Project is not in Search Strategy stage.")

    def _persist_approved_search_results(self, strategy_ids: list[int], user):
        """
        Persists studies for approved strategies using the Acquisition Facade.
        Uses cached preview results to avoid re-fetching from external sources.
        """
        acquisition_facade = get_acquisition_facade()
        search_service = SearchStrategyService()
        
        for strategy_id in strategy_ids:
            try:
                preview_result = search_service.get_search_results_dto(strategy_id)
                acquisition_facade.finalize_search(
                    design_strategy_id=strategy_id,
                    preview_result=preview_result,
                    user=user
                )         
            except Exception as e:
                raise ValidationError(f"Error persisting strategy {strategy_id}: {str(e)}")
