from django.utils import timezone
from typing import List
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError, ConsolidationError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError, transaction
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from apps.design.access_control import DesignAccessPolicy
from django.contrib.auth.models import User


class EligibilityCriterionService:

    def create_eligibility_criterion(self, description: str, motivation: str, project_id: int, researcher, criteria_type: str) -> EligibilityCriterion:
        try:
            try:
                design_phase = DesignPhase.objects.get(pk=project_id)
            except DesignPhase.DoesNotExist:
                raise CreationError("Design Phase not found for this project.")

            if not DesignAccessPolicy.can_create_criteria(researcher, design_phase):
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
            
            # Notify if owner creates in closed stage
            self._notify_if_owner_action_in_closed_stage(criterion, researcher, is_creation=True)
            
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
        if not DesignAccessPolicy.can_edit_criteria(user, criterion):
            raise UpdateError("You do not have permission to edit this criterion.")

        # Check if need to notify before updating
        should_notify = self._should_notify_owner_modification(criterion, user)

        criterion.description = description
        criterion.motivation = motivation
        criterion.last_modified_by = user
        try:
            criterion.full_clean()
            criterion.save(update_fields=['description', 'motivation', 'updated_at', 'last_modified_by'])
            
            # Notify after successful update
            if should_notify:
                self._notify_if_owner_action_in_closed_stage(criterion, user, is_creation=False)
            
            return criterion
        except ValidationError as e:
            raise UpdateError(f"Validation error: {str(e)}")
        except DatabaseError as e:
            raise UpdateError(f"Error updating eligibility criterion: {str(e)}")

    # Read methods moved to Selector

    def reject_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self._get_criterion_model(criterion_id)

        # Authorization Check (Review)
        if not DesignAccessPolicy.can_review_criteria(user, criterion.design_phase):
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

    def delete_eligibility_criterion(self, criterion_id: int, user: User = None) -> None:
        """Delete an eligibility criterion."""
        criterion = self._get_criterion_model(criterion_id)
        if user:
            if not DesignAccessPolicy.can_edit_criteria(user, criterion):
                raise UpdateError("You do not have permission to delete this criterion.")

        try:
            criterion.delete()
        except DatabaseError as e:
            raise UpdateError(f"Error deleting eligibility criterion: {str(e)}")

    def approve_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self._get_criterion_model(criterion_id)

        # Authorization Check (Review)
        if not DesignAccessPolicy.can_review_criteria(user, criterion.design_phase):
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

    def _validate_consolidation_requirements(self, phase: DesignPhase, user: User) -> None:
        if phase.current_stage != DesignPhase.DesignStage.CRITERIA_DEFINITION:
            raise UpdateError("This stage has already been consolidated.")

        if not DesignAccessPolicy.can_consolidate_stage(user, phase):
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

    def _should_notify_owner_modification(self, criterion: EligibilityCriterion, user: User) -> bool:
        """Check if we should notify about owner modification in closed stage."""
        design_phase = criterion.design_phase
        project = design_phase.project
        
        # Only notify if user is owner
        if not DesignAccessPolicy.is_owner(user, project):
            return False
        
        # Only notify if stage is closed
        if design_phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION:
            return False
        
        # Only notify if criterion is approved
        if criterion.status != EligibilityCriterion.CriterionStatus.APPROVED:
            return False
        
        return True

    def _notify_if_owner_action_in_closed_stage(self, criterion: EligibilityCriterion, user: User, is_creation: bool):
        """Send notification if owner creates/edits in closed stage."""
        design_phase = criterion.design_phase
        project = design_phase.project
        
        # Only notify if owner
        if not DesignAccessPolicy.is_owner(user, project):
            return
        
        # Only notify if stage is closed
        if design_phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION:
            return
        
        # For creation, always notify in closed stage
        # For edit, only notify if approved
        if not is_creation and criterion.status != EligibilityCriterion.CriterionStatus.APPROVED:
            return
        
        try:
            from apps.notification.models import Notification
            from apps.project.api.providers import ProjectManagementProvider
            
            provider = ProjectManagementProvider()
            members = provider.get_project_member_users(project.id)
            
            action_text = "created" if is_creation else "modified"
            criterion_type = "inclusion" if criterion.type == EligibilityCriterion.CriterionType.INCLUSION else "exclusion"
            
            for member in members:
                Notification.objects.create(
                    recipient=member,
                    sender=user,
                    type='OWNER_MODIFIED_APPROVED_CRITERION',
                    title=f'Owner {action_text} {criterion_type} criterion in closed stage',
                    custom_message=f'The project owner has {action_text} an {criterion_type} criterion in a closed stage. Please review the changes for audit purposes.',
                    project=project
                )
        except Exception:
            pass  # Silent fail on notification errors
