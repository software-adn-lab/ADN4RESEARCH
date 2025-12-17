
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
        approved_questions = ResearchQuestion.objects.filter(
            design_phase_id=project_id,
            status=ResearchQuestion.Status.APPROVED
        )
        for question in approved_questions:
            if not SearchStrategy.objects.filter(research_question=question).exists():
                raise ValidationError(f"Research Question '{question.question[:50]}...' does not have a search strategy defined.")

        approved_strategy_ids = []

        with transaction.atomic():
            strategies = SearchStrategy.objects.filter(research_question__design_phase_id=project_id)
            print(f"DEBUG: Found {len(strategies)} strategies for project {project_id}")
            
            for strategy in strategies:
                print(f"DEBUG: Strategy {strategy.id} status: {strategy.status}")
                strategy.versions.filter(status=SearchStrategy.Status.DRAFT).update(status=SearchStrategy.Status.REJECTED)
                
                if strategy.status == SearchStrategy.Status.APPROVED:
                    approved_strategy_ids.append(strategy.id)

            if phase.current_stage == DesignPhase.DesignStage.SEARCH_STRATEGY:
                phase.current_stage = DesignPhase.DesignStage.FINISHED
                phase.save()
            else:
                raise ValidationError("Project is not in Search Strategy stage.")

        # Persist results using Acquisition Facade (leveraging Redis cache via Service)
        acquisition_facade = get_acquisition_facade()
        search_service = SearchStrategyService()
        
        for strategy_id in approved_strategy_ids:
            try:
                # This call handles cached retrieval internally
                preview_result = search_service.get_search_results_dto(strategy_id)
                
                print(f"DEBUG: Consolidating Strategy {strategy_id}")
                print(f"DEBUG: Preview Result Total Found: {preview_result.total_found}")
                print(f"DEBUG: Studies in DTO: {len(preview_result.studies)}")
                
                final_result = acquisition_facade.finalize_search(
                    design_strategy_id=strategy_id,
                    preview_result=preview_result,
                    user=user
                )
                print(f"DEBUG: Persisted studies: {len(final_result.studies_persisted)}")
                
            except Exception as e:
                # Log error but don't block the consolidation of other strategies?
                # Or raise to rollback? User preference implied synchronous success.
                # For now we'll allow it to fail hard (ValidationError) effectively rolling back if atomic wasn't closed
                # Wait, we are outside the atomic block for facade calls to allow partial progress? No, consistency is key.
                # Re-raising ensures the user knows something failed.
                raise ValidationError(f"Error persisting strategy {strategy_id}: {str(e)}")

        return phase
