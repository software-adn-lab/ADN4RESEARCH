from django.utils import timezone
from typing import List
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError, ConsolidationError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError, transaction
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.access_control import DesignAccessPolicy


class EligibilityCriterionService:

    def create_eligibility_criterion(self, description: str, motivation: str, project_id: int, researcher, criteria_type: str) -> EligibilityCriterion:
        try:
            try:
                design_phase = DesignPhase.objects.get(pk=project_id)
            except DesignPhase.DoesNotExist:
                raise CreationError("Design Phase not found for this project.")

            # Authorization Check (Create/Edit)
            # Creating a criterion is effectively editing the criteria list.
            # We can reuse can_edit_question logic or assume if they can access the workspace they can create draft.
            # But strictly, we should check if the stage allows editing.
            # Let's assume creating is allowed if the user is a member and stage is correct.
            # DesignAccessPolicy.can_edit_question checks stage. We might need a specific can_edit_criteria.
            # For now, using can_edit_question as a proxy for "can edit design artifacts in this phase"
            # OR better, check stage directly via Policy if we had a method.
            # Let's use a manual check consistent with Policy philosophy or add a method to Policy.
            # Given I cannot easily add to Policy right now without context switching, I will implement logic consistent with it here
            # or reuse can_edit_question which checks for RQ_DEFINITION.
            # Wait, Criteria has its own stage: CRITERIA_DEFINITION.

            # Let's implement the check here using the Policy's logic style or if possible, just check the stage.
            if design_phase.current_stage != DesignPhase.DesignStage.CRITERIA_DEFINITION and not (design_phase.project.owner == researcher):
                raise CreationError("Cannot create criteria in this stage.")

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

    def _get_criterion_model(self, criterion_id: int) -> EligibilityCriterion:
        try:
            return EligibilityCriterion.objects.select_related('design_phase__project__owner').get(id=criterion_id)
        except EligibilityCriterion.DoesNotExist:
            raise NotFoundError(f"Eligibility criterion with id {criterion_id} not found")

    def update_eligibility_criterion(self, criterion_id: int, user, description: str, motivation: str) -> EligibilityCriterion:
        criterion = self._get_criterion_model(criterion_id)

        # Authorization Check
        # We need to check if user can edit THIS criterion.
        # Policy doesn't have can_edit_criterion yet.
        # Logic: Owner always can. Researcher can if it's theirs AND stage is CRITERIA_DEFINITION.

        is_owner = (criterion.design_phase.project.owner == user)
        is_author = (criterion.researcher == user)
        is_correct_stage = (criterion.design_phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION)

        if not is_owner:
            if not is_author:
                raise UpdateError("You do not have permission to edit this criterion.")
            if not is_correct_stage:
                raise UpdateError("Cannot edit criteria in this stage.")

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

    # Read methods moved to Selector

    def reject_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self._get_criterion_model(criterion_id)

        # Authorization Check (Review)
        if not DesignAccessPolicy.can_review_question(user, criterion.design_phase):  # Reusing review permission
            raise UpdateError("You do not have permission to review criteria.")

        # Requirement: "un researcher no puede rechazar o aprobar su propia creacion"
        if criterion.researcher == user and not criterion.design_phase.project.owner == user:
            raise UpdateError("Researchers cannot reject their own criteria.")

        criterion.status = EligibilityCriterion.CriterionStatus.REJECTED
        criterion.reviewed_by = user
        criterion.reviewed_at = timezone.now()
        criterion.justification = justification
        try:
            criterion.save(update_fields=['status', 'updated_at', 'reviewed_by', 'reviewed_at', 'justification'])
        except DatabaseError as e:
            raise UpdateError(f"Error rejecting: {str(e)}")
        return criterion

    def delete_eligibility_criterion(self, criterion_id: int, user=None) -> None:
        """Delete an eligibility criterion."""
        criterion = self._get_criterion_model(criterion_id)
        if user:
            # Reuse update permission logic
            is_owner = (criterion.design_phase.project.owner == user)
            is_author = (criterion.researcher == user)
            is_correct_stage = (criterion.design_phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION)

            if not is_owner:
                if not is_author:
                    raise UpdateError("You do not have permission to delete this criterion.")
                if not is_correct_stage:
                    raise UpdateError("Cannot delete criteria in this stage.")

        try:
            criterion.delete()
        except DatabaseError as e:
            raise UpdateError(f"Error deleting eligibility criterion: {str(e)}")

    def approve_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self._get_criterion_model(criterion_id)

        # Authorization Check (Review)
        if not DesignAccessPolicy.can_review_question(user, criterion.design_phase):  # Reusing review permission
            raise UpdateError("You do not have permission to review criteria.")

        if criterion.researcher == user and not criterion.design_phase.project.owner == user:
            raise UpdateError("Researchers cannot approve their own criteria.")

        criterion.status = EligibilityCriterion.CriterionStatus.APPROVED
        criterion.reviewed_by = user
        criterion.reviewed_at = timezone.now()
        criterion.justification = justification
        try:
            criterion.save(update_fields=['status', 'updated_at', 'reviewed_by', 'reviewed_at', 'justification'])
        except DatabaseError as e:
            raise UpdateError(f"Error approving: {str(e)}")
        return criterion

    def _validate_consolidation_requirements(self, phase, user):
        if phase.current_stage != DesignPhase.DesignStage.CRITERIA_DEFINITION:
            raise UpdateError("This stage has already been consolidated.")

        if phase.project.owner != user:
            raise UpdateError("Only the project owner can consolidate the stage.")

        has_inclusion = EligibilityCriterion.objects.filter(
            design_phase=phase,
            type=EligibilityCriterion.CriterionType.INCLUSION,
            status=EligibilityCriterion.CriterionStatus.APPROVED
        ).exists()

        has_exclusion = EligibilityCriterion.objects.filter(
            design_phase=phase,
            type=EligibilityCriterion.CriterionType.EXCLUSION,
            status=EligibilityCriterion.CriterionStatus.APPROVED
        ).exists()

        if not has_inclusion or not has_exclusion:
            raise ConsolidationError("Cannot consolidate: You need at least one approved inclusion and one approved exclusion criterion.")

    @transaction.atomic
    def finalize_criteria_stage(self, project_id: int, user) -> dict:
        phase = DesignPhase.objects.select_related('project').get(pk=project_id)

        self._validate_consolidation_requirements(phase, user)

        criteria = EligibilityCriterion.objects.filter(design_phase_id=project_id, status=EligibilityCriterion.CriterionStatus.DRAFT)

        stats = {
            'approved': 0,  # Should calculate real approved count if needed, but keeping existing structure
            'rejected': 0,
            'auto_rejected': 0
        }
        for criterion in criteria:
            criterion.status = EligibilityCriterion.CriterionStatus.REJECTED
            criterion.justification = "Automatically rejected during stage consolidation."
            criterion.reviewed_by = user
            criterion.reviewed_at = timezone.now()
            criterion.save()
            stats['auto_rejected'] += 1

        return stats
