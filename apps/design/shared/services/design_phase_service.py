from apps.design.shared.models.design_phase import DesignPhase
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy, SearchStrategyVersion
from django.db import transaction
from django.core.exceptions import ValidationError


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
        approved_questions = ResearchQuestion.objects.filter(
            design_phase_id=project_id,
            status=ResearchQuestion.Status.APPROVED
        )
        for question in approved_questions:
            if not SearchStrategy.objects.filter(research_question=question).exists():
                raise ValidationError(f"Research Question '{question.question[:50]}...' does not have a search strategy defined.")

        with transaction.atomic():
            strategies = SearchStrategy.objects.filter(research_question__design_phase_id=project_id)
            for strategy in strategies:
                strategy.versions.filter(status=SearchStrategy.Status.DRAFT).update(status=SearchStrategy.Status.REJECTED)
            if phase.current_stage == DesignPhase.DesignStage.SEARCH_STRATEGY:
                phase.current_stage = DesignPhase.DesignStage.FINISHED
                phase.save()
            else:
                raise ValidationError("Project is not in Search Strategy stage.")
        return phase