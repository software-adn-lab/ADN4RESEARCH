from typing import Any, Dict, List, Optional
from django.contrib.auth.models import User
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.design.search_strategy.models.search_strategy import SearchStrategyVersion
from apps.design.search_strategy.dtos import SearchStrategyDTO, SearchStrategyVersionDTO

class SearchStrategySelector:
    @staticmethod
    def get_strategy_dto(strategy: SearchStrategy) -> SearchStrategyDTO:
        return SearchStrategyDTO(
            id=strategy.id,
            research_question_id=strategy.research_question_id,
            status=strategy.status,
            final_search_string=strategy.final_search_string,
            json_definition=strategy.json_definition,
            total_studies_found=strategy.total_studies_found,
            created_by_id=strategy.created_by_id,
            created_at=strategy.created_at,
            last_modified_by_id=strategy.last_modified_by_id,
            reviewed_by_id=strategy.reviewed_by_id
        )

    @staticmethod
    def get_version_dto(version: SearchStrategyVersion) -> SearchStrategyVersionDTO:
        return SearchStrategyVersionDTO(
            id=version.id,
            strategy_id=version.strategy_id,
            version_number=version.version_number,
            final_search_string=version.final_search_string,
            json_definition=version.json_definition,
            total_found=version.total_found,
            status=version.status,
            justification=version.justification,
            created_at=version.created_at,
            created_by_id=version.created_by_id
        )

    @staticmethod
    def get_by_id(strategy_id: int) -> Optional[SearchStrategyDTO]:
        try:
            strategy = SearchStrategy.objects.get(pk=strategy_id)
            return SearchStrategySelector.get_strategy_dto(strategy)
        except SearchStrategy.DoesNotExist:
            return None

    @staticmethod
    def get_by_question_id(question_id: int) -> Optional[SearchStrategyDTO]:
        try:
            strategy = SearchStrategy.objects.get(research_question_id=question_id)
            return SearchStrategySelector.get_strategy_dto(strategy)
        except SearchStrategy.DoesNotExist:
            return None

    @staticmethod
    def get_list_by_project(project_id: int) -> List[SearchStrategyDTO]:
        strategies = SearchStrategy.objects.filter(research_question__design_phase_id=project_id)
        return [SearchStrategySelector.get_strategy_dto(s) for s in strategies]

    @staticmethod
    def get_versions_for_strategy(strategy_id: int) -> List[Dict[str, Any]]:
        versions = SearchStrategyVersion.objects.filter(strategy_id=strategy_id).order_by('-version_number').values(
            'id',
            'strategy_id',
            'version_number',
            'final_search_string',
            'total_found',
            'status',
            'justification',
            'created_at'
        )
        return list(versions)

    @staticmethod
    def get_version_by_id(version_id: int) -> Optional[SearchStrategyVersionDTO]:
        try:
            version = SearchStrategyVersion.objects.get(pk=version_id)
            return SearchStrategySelector.get_version_dto(version)
        except SearchStrategyVersion.DoesNotExist:
            return None

    @staticmethod
    def count_approved(project_id: int) -> int:
        """Count approved search strategy versions for dashboard."""
        return SearchStrategyVersion.objects.filter(
            strategy__research_question__design_phase_id=project_id,
            status='APPROVED'
        ).count()
