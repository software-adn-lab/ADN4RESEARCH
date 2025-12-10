from django.utils import timezone
from typing import List
from apps.design.exceptions.eligibility_criteria_exceptions import CreationError, NotFoundError, UpdateError, ConsolidationError
from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError, transaction
from apps.design.shared.models.design_phase import DesignPhase

class EligibilityCriterionService:

    def _validate_modification_permissions(self, criterion, user):
        phase = criterion.design_phase
        is_owner = (phase.project.owner == user)
        stages = [s for s, _ in DesignPhase.DesignStage.choices]
        try:
            current_idx = stages.index(phase.current_stage)
            criteria_idx = stages.index(DesignPhase.DesignStage.CRITERIA_DEFINITION)
            is_past_stage = current_idx > criteria_idx
        except ValueError:
            is_past_stage = False 
            
        if is_past_stage and not is_owner:
            raise UpdateError("The Eligibility Criteria stage is finished. You cannot modify criteria anymore.")

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
        is_researcher = (criterion.researcher == user)

        if not (is_owner or is_researcher):
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

    
    def reject_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        self._validate_modification_permissions(criterion, user)
        
        # Check if user is owner or it's their own suggestion (though usually users don't reject their own unless allowed)
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
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        if user:
            self._validate_modification_permissions(criterion, user)
            
        try:
            criterion.delete()
        except DatabaseError as e:
            raise UpdateError(f"Error deleting eligibility criterion: {str(e)}")

    def approve_eligibility_criterion(self, criterion_id: int, user, justification: str = '') -> EligibilityCriterion:
        criterion = self.get_eligibility_criterion_by_id(criterion_id)
        self._validate_modification_permissions(criterion, user)

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
    def consolidate_criteria(self, project_id: int, user) -> dict:
        phase = DesignPhase.objects.select_related('project').get(pk=project_id)
        
        self._validate_consolidation_requirements(phase, user)
            
        criteria = EligibilityCriterion.objects.filter(design_phase_id=project_id, status=EligibilityCriterion.CriterionStatus.DRAFT)
        
        stats = {
            'approved': 0,
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
        phase.current_stage = DesignPhase.DesignStage.SEARCH_STRATEGY
        phase.save()
        return stats

    def get_criteria_by_status(self, project_id: int, status: str) -> List[EligibilityCriterion]:
        return list(EligibilityCriterion.objects.filter(
            project_id=project_id,
            status=status
        ).order_by('created_at'))

    