from typing import List
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError


class EligibilityCriterionService:

    def create_eligibility_criterion(self, description: str, motivation: str, project, suggester, criteria_type: str) -> EligibilityCriterion:
        """Create a new eligibility criterion."""
        try:
            criterion = EligibilityCriterion(
                description=description,
                motivation=motivation,
                project=project,
                suggester=suggester,
                type=criteria_type
            )
            criterion.full_clean()  # Run model validation
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

    def get_criterion_by_project_and_type(self, project_id: int, criteria_type: str) -> List[EligibilityCriterion]:
        """Get all criteria for a project filtered by type."""
        return list(EligibilityCriterion.objects.filter(
            project_id=project_id,
            type=criteria_type
        ).order_by('created_at'))

    def update_eligibility_criterion(self, criterion_id: int, description: str, motivation: str) -> EligibilityCriterion:
        """Update the description and motivation of a criterion."""
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        criterion.description = description
        criterion.motivation = motivation
        try:
            criterion.full_clean()
            criterion.save(update_fields=['description', 'motivation', 'updated_at'])
            return criterion
        except ValidationError as e:
            raise UpdateError(f"Validation error: {str(e)}")
        except DatabaseError as e:
            raise UpdateError(f"Error updating eligibility criterion: {str(e)}")

    def reject_eligibility_criterion(self, criterion_id: int) -> EligibilityCriterion:
        """Change the status of a criterion to REJECTED."""
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        criterion.status = EligibilityCriterion.CriterionStatus.REJECTED
        try:
            criterion.save(update_fields=['status', 'updated_at'])
        except DatabaseError as e:
            raise UpdateError(f"Error rejecting eligibility criterion: {str(e)}")
        return criterion

    def delete_eligibility_criterion(self, criterion_id: int) -> None:
        """Delete an eligibility criterion."""
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        try:
            criterion.delete()
        except DatabaseError as e:
            raise UpdateError(f"Error deleting eligibility criterion: {str(e)}")

    def approve_eligibility_criterion(self, criterion_id: int) -> EligibilityCriterion:
        """Change the status of a criterion to APPROVED."""
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        criterion.status = EligibilityCriterion.CriterionStatus.APPROVED
        try:
            criterion.save(update_fields=['status', 'updated_at'])
        except DatabaseError as e:
            raise UpdateError(f"Error approving eligibility criterion: {str(e)}")
        return criterion

    def get_criteria_by_status(self, project_id: int, status: str) -> List[EligibilityCriterion]:
        """Get all criteria for a project filtered by status."""
        return list(EligibilityCriterion.objects.filter(
            project_id=project_id,
            status=status
        ).order_by('created_at'))
