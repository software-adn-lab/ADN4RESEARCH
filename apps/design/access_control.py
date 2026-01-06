from typing import Optional
from django.contrib.auth.models import User
from apps.design.design_phase_logic.models.design_phase import DesignPhase


class DesignAccessPolicy:
    """
    Centralizes authorization logic for the Design Phase.
    Encapsulates rules based on User Role and Design Stage.
    """

    @staticmethod
    def is_owner(user: User, project) -> bool:
        return project.owner_id == user.id

    @staticmethod
    def can_edit_question(user: User, question) -> bool:
        """
        Determines if a user can edit a specific research question.
        Rule: 
        - If stage is RQ_EDITION (Creation/Discussion):
            - Owner can always edit.
            - Researcher can edit their own questions.
        - If stage is past RQ_EDITION:
            - Only Owner can edit (and usually they shouldn't, but system allows it for corrections).
        """
        phase = question.design_phase
        is_owner = DesignAccessPolicy.is_owner(user, phase.project)

        if phase.current_stage in DesignPhase.RQ_EDITION_STAGES:
            return is_owner or (question.researcher_id == user.id)

        # Locked stage
        return is_owner

    @staticmethod
    def can_review_question(user: User, phase: DesignPhase, question=None) -> bool:
        """
        Determines if a user can review (Approve/Reject) questions.
        Rule:
        - If stage is RQ_DISCUSSION:
            - Owner and Researchers can review (peer review).
            - Researchers CANNOT review their own questions.
        - If stage is past RQ_DISCUSSION:
            - Only Owner can review.
        """
        is_owner = DesignAccessPolicy.is_owner(user, phase.project)

        # If we are in the discussion phase, anyone assigned can review
        if phase.current_stage == DesignPhase.DesignStage.RQ_DISCUSSION:
            if question and question.researcher_id == user.id and not is_owner:
                return False
            return True

        # If discussion is over, only owner can make late changes
        return is_owner

    @staticmethod
    def can_consolidate_stage(user: User, phase: DesignPhase) -> bool:
        """
        Only the Project Owner can consolidate stages.
        """
        return DesignAccessPolicy.is_owner(user, phase.project)

    @staticmethod
    def can_delete_question(user: User, question) -> bool:
        """
        Rule: Same as edit.
        """
        return DesignAccessPolicy.can_edit_question(user, question)

    @staticmethod
    def can_create_criteria(user: User, phase: DesignPhase) -> bool:
        """
        Determines if a user can create criteria in this phase.
        Rule:
        - If stage is CRITERIA_DEFINITION:
            - Owner and Researchers can create.
        - If stage is past CRITERIA_DEFINITION:
            - Only Owner can create.
        """
        is_owner = DesignAccessPolicy.is_owner(user, phase.project)
        if phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION:
            return True
        return is_owner

    @staticmethod
    def can_edit_criteria(user: User, criterion) -> bool:
        """
        Determines if a user can edit a specific eligibility criterion.
        Rule:
        - If stage is CRITERIA_DEFINITION:
            - Owner can always edit.
            - Researcher can edit their own criteria.
        - If stage is past CRITERIA_DEFINITION:
            - Only Owner can edit.
        """
        phase = criterion.design_phase
        is_owner = DesignAccessPolicy.is_owner(user, phase.project)

        if phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION:
            return is_owner or (criterion.researcher_id == user.id)

        return is_owner

    @staticmethod
    def can_review_criteria(user: User, phase: DesignPhase) -> bool:
        """
        Determines if a user can review (Approve/Reject) criteria.
        Rule:
        - If stage is CRITERIA_DEFINITION:
            - Owner and Researchers can review (peer review).
        - If stage is past CRITERIA_DEFINITION:
            - Only Owner can review.
        """
        is_owner = DesignAccessPolicy.is_owner(user, phase.project)
        if phase.current_stage == DesignPhase.DesignStage.CRITERIA_DEFINITION:
            return True
        return is_owner
