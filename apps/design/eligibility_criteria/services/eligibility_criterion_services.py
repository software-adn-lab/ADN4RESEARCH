from django.utils import timezone
from typing import List
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError

from apps.design.shared.models.design_phase import DesignPhase


class EligibilityCriterionService:

    def create_eligibility_criterion(self, description: str, motivation: str, project_id: int, researcher, criteria_type: str) -> EligibilityCriterion:
        try:
            try:
                design_phase = DesignPhase.objects.get(pk=project_id)
            except DesignPhase.DoesNotExist:
                raise CreationError("Design Phase not found for this project.")
            criterion = EligibilityCriterion(
                description=description,
                motivation=motivation,
                design_phase=design_phase,
                researcher=researcher,
                type=criteria_type
            )
            criterion.full_clean()
            criterion.save()
            return criterion

        except ValidationError as e:
            raise CreationError(f"Validation error: {str(e)}")
        except IntegrityError as e:
            raise CreationError(f"Database integrity error: {str(e)}")
        except DatabaseError as e:
            raise CreationError(f"Error creating eligibility criterion: {str(e)}")

    def get_eligibility_criterion_by_id(self, criterion_id: int) -> EligibilityCriterion:
        """Retrieve an eligibility criterion by its ID."""
        try:
            return EligibilityCriterion.objects.get(id=criterion_id)
        except EligibilityCriterion.DoesNotExist:
            raise NotFoundError(f"Eligibility criterion with id {criterion_id} not found")

    def get_criterion_by_project_and_type(self, project_id: int, criteria_type: str, status_filter: str = None) -> List[EligibilityCriterion]:
        qs = EligibilityCriterion.objects.by_project(project_id).by_type(criteria_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return list(qs.order_by('created_at'))

    def update_eligibility_criterion(self, criterion_id: int, user, description: str, motivation: str) -> EligibilityCriterion:
        try:
            criterion = EligibilityCriterion.objects.select_related(
                'design_phase__project__owner'
            ).get(id=criterion_id)
        except EligibilityCriterion.DoesNotExist:
            raise NotFoundError(f"Eligibility criterion with id {criterion_id} not found")
        is_owner = (criterion.design_phase.project.owner == user)
        is_suggester = (criterion.suggester == user)

        if not (is_owner or is_suggester):
            raise UpdateError("You do not have permission to edit this criterion.")
        criterion.description = description
        criterion.motivation = motivation
        criterion.last_modified_by = user
        try:
            criterion.full_clean()
            criterion.save(update_fields=['description', 'motivation', 'updated_at', 'last_modified_by'])
            return criterion
        except ValidationError as e:
            raise UpdateError(f"Validation error: {str(e)}")
        except DatabaseError as e:
            raise UpdateError(f"Error updating eligibility criterion: {str(e)}")
    
    def get_inclusion_criteria(self, project_id, status_filter=None):
        return self.get_criterion_by_project_and_type(
            project_id=project_id,
            criteria_type=EligibilityCriterion.CriterionType.INCLUSION,
            status_filter=status_filter
        )

    def get_exclusion_criteria(self, project_id, status_filter=None):
        return self.get_criterion_by_project_and_type(
            project_id=project_id,
            criteria_type=EligibilityCriterion.CriterionType.EXCLUSION,
            status_filter=status_filter
        )

    def reject_eligibility_criterion(self, criterion_id: int, user) -> EligibilityCriterion:
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        criterion.status = EligibilityCriterion.CriterionStatus.REJECTED
        criterion.reviewed_by = user
        criterion.reviewed_at = timezone.now()
        try:
            criterion.save(update_fields=['status', 'updated_at', 'reviewed_by', 'reviewed_at'])
        except DatabaseError as e:
            raise UpdateError(f"Error rejecting: {str(e)}")
        return criterion

    def delete_eligibility_criterion(self, criterion_id: int) -> None:
        """Delete an eligibility criterion."""
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        try:
            criterion.delete()
        except DatabaseError as e:
            raise UpdateError(f"Error deleting eligibility criterion: {str(e)}")

    def approve_eligibility_criterion(self, criterion_id: int, user) -> EligibilityCriterion:
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        criterion.status = EligibilityCriterion.CriterionStatus.APPROVED
        criterion.reviewed_by = user
        criterion.reviewed_at = timezone.now()
        try:
            criterion.save(update_fields=['status', 'updated_at', 'reviewed_by', 'reviewed_at'])
        except DatabaseError as e:
            raise UpdateError(f"Error approving: {str(e)}")
        return criterion

    def get_criteria_by_status(self, project_id: int, status: str) -> List[EligibilityCriterion]:
        return list(EligibilityCriterion.objects.filter(
            project_id=project_id,
            status=status
        ).order_by('created_at'))

    