from typing import List, Optional
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.eligibility_criteria.dtos import EligibilityCriterionDTO

class EligibilityCriterionSelector:
    @staticmethod
    def get_dto(criterion: EligibilityCriterion) -> EligibilityCriterionDTO:
        return EligibilityCriterionDTO(
            id=criterion.id,
            description=criterion.description,
            motivation=criterion.motivation,
            justification=criterion.justification,
            type=criterion.type,
            status=criterion.status,
            design_phase_id=criterion.design_phase_id,
            researcher_id=criterion.researcher_id,
            created_at=criterion.created_at,
            updated_at=criterion.updated_at,
            reviewed_by_id=criterion.reviewed_by_id,
            reviewed_at=criterion.reviewed_at
        )

    @staticmethod
    def get_by_id(criterion_id: int) -> Optional[EligibilityCriterionDTO]:
        try:
            criterion = EligibilityCriterion.objects.get(pk=criterion_id)
            return EligibilityCriterionSelector.get_dto(criterion)
        except EligibilityCriterion.DoesNotExist:
            return None

    @staticmethod
    def get_list_by_project(project_id: int, criteria_type: str = None, status_filter: str = None) -> List[EligibilityCriterionDTO]:

        qs = EligibilityCriterion.objects.filter(design_phase_id=project_id)

        if criteria_type:
            qs = qs.filter(type=criteria_type)

        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by('created_at')
        return [EligibilityCriterionSelector.get_dto(c) for c in qs]

    @staticmethod
    def get_inclusion_criteria(project_id: int, status_filter: str = None) -> List[EligibilityCriterionDTO]:
        return EligibilityCriterionSelector.get_list_by_project(
            project_id,
            criteria_type=EligibilityCriterion.CriterionType.INCLUSION,
            status_filter=status_filter
        )

    @staticmethod
    def get_exclusion_criteria(project_id: int, status_filter: str = None) -> List[EligibilityCriterionDTO]:
        return EligibilityCriterionSelector.get_list_by_project(
            project_id,
            criteria_type=EligibilityCriterion.CriterionType.EXCLUSION,
            status_filter=status_filter
        )
