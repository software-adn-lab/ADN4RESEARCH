from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.exceptions.project_exceptions import ConsolidationError, InvalidProjectStateError, ProjectPermissionError
from config.events import bus
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.design.exceptions.research_question_exceptions import InvalidFrameworkFieldsError, ProjectNotFoundError, QuestionReviewError, QuestionSubmissionError, QuestionNotFoundError, ResearchQuestionError
from apps.project.structure.models.project_models import Project
from django.contrib.auth.models import User
from apps.design.design_phase_logic.models.design_phase import DesignPhase
from django.utils import timezone
from apps.design.access_control import DesignAccessPolicy
from apps.design.research_question.selectors import ResearchQuestionSelector


class ResearchQuestionService:
    @transaction.atomic
    def add_research_question(self, project_id: int, question: str, motivation: str, researcher_id: int, framework_fields: dict) -> ResearchQuestion:
        try:
            design_phase = DesignPhase.objects.select_related('project__research_framework').get(pk=project_id)
        except DesignPhase.DoesNotExist:
            raise InvalidProjectStateError("The project does not have an initialized Design Phase.")
        project = design_phase.project
        user = User.objects.get(id=researcher_id)  # We need the user object for the policy

        # Authorization Check
        # Note: We are checking if they can *add*, which is similar to *edit* a new question.
        # Ideally we would have can_add_question(user, project), but reusing logic for now.
        if design_phase.current_stage not in DesignPhase.RQ_EDITION_STAGES:
            if not DesignAccessPolicy.is_owner(user, project):
                raise ValidationError(f"Locked Stage: Only the owner can add questions during '{design_phase.get_current_stage_display()}'.")

        if not self._is_valid_framework_fields(project.research_framework, framework_fields or {}):
            raise InvalidFrameworkFieldsError("The provided fields do not match the project's research framework structure.")

        new_question = ResearchQuestion.objects.create(
            design_phase=design_phase,
            researcher_id=researcher_id,
            question=question,
            motivation=motivation,
            framework_fields=framework_fields
        )

        return new_question

    @transaction.atomic
    def update_research_question(self, question_id, user, **data):
        try:
            question = ResearchQuestion.objects.select_related(
                'design_phase__project__owner',
                'design_phase__project__research_framework'
            ).get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError("Question not found.")

        # Authorization Check
        if not DesignAccessPolicy.can_edit_question(user, question):
            raise ValidationError("You do not have permission to edit this question.")

        updated_question = self._apply_updates(question, data)
        return updated_question

    @transaction.atomic
    def delete_research_question(self, question_id: int, user) -> int:
        try:
            question = ResearchQuestion.objects.select_related('design_phase__project').get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError("Question not found.")

        # Authorization Check
        if not DesignAccessPolicy.can_delete_question(user, question):
            raise ValidationError("You do not have permission to delete this question.")

        if question.status == ResearchQuestion.Status.APPROVED:
            raise ResearchQuestionError("Cannot delete an APPROVED question directly. Change its status first.")
        question.delete()

    @transaction.atomic
    def autosave_question(self, cleaned_data, user: User, project_id: int, question_id: int) -> ResearchQuestion:
        payload = {
            'question': cleaned_data.get('question', ''),
            'motivation': cleaned_data.get('motivation', ''),
            'framework_fields': cleaned_data.get('framework_fields', {})
        }
        if question_id:
            return self.update_research_question(question_id=question_id, user=user, **payload)
        else:
            return self.add_research_question(project_id=project_id, researcher_id=user.id, **payload)

    @transaction.atomic
    def submit_research_question_for_review(self, research_question_id: int):
        research_question = ResearchQuestion.objects.get(id=research_question_id)

        if not self.can_submit_question(research_question_id):
            raise QuestionSubmissionError(
                f"Question {research_question.id} cannot be submitted. "
                f"Current status: {research_question.get_status_display()}"
                f" in stage {research_question.design_phase.get_current_stage_display()}."
            )
        research_question.status = ResearchQuestion.Status.SUGGESTED
        research_question.save(update_fields=['status', 'modified_at'])

        bus.publish("research_question_submitted", {
            "question_id": research_question.id,
            "question_text": research_question.question
        })

    def can_submit_question(self, research_question_id: int) -> bool:
        try:
            research_question = ResearchQuestion.objects.select_related('design_phase').get(id=research_question_id)
        except ResearchQuestion.DoesNotExist:
            return False
        is_ready = research_question.status == ResearchQuestion.Status.READY_TO_SEND
        is_in_edition_stage = research_question.design_phase.current_stage in DesignPhase.RQ_EDITION_STAGES
        return is_ready and is_in_edition_stage

    def _is_valid_framework_fields(self, framework, fields):
        allowed_keys = set(framework.get_allowed_keys())
        input_keys = set(fields.keys())
        return allowed_keys == input_keys

    def _apply_updates(self, question, data):
        allowed_fields = {'question', 'motivation', 'framework_fields', 'justification'}
        fields_to_update = []
        for field, value in data.items():
            if field not in allowed_fields:
                continue
            if field == 'framework_fields':
                if not self._is_valid_framework_fields(question.research_framework, value):
                    raise ValidationError("Framework fields are not valid according to the methodology.")
            if getattr(question, field) != value:
                setattr(question, field, value)
                fields_to_update.append(field)
        if fields_to_update:
            fields_to_update.append('modified_at')
            fields_to_update.append('last_modified_by')
            fields_to_update.append('status')
            question.save(update_fields=fields_to_update)
        return question

    @transaction.atomic
    def review_research_question(self, question_id: int, verdict: str, justification: str, user_id: int) -> ResearchQuestion:
        allowed_verdicts = {
            ResearchQuestion.Status.APPROVED,
            ResearchQuestion.Status.REJECTED,
        }
        if verdict not in allowed_verdicts:
            raise ValidationError(f"Estado no válido para una revisión: {verdict}")

        question = ResearchQuestion.objects.select_related('design_phase__project').get(id=question_id)
        user = User.objects.get(id=user_id)

        # Authorization Check
        # Authorization Check
        if not DesignAccessPolicy.can_review_question(user, question.design_phase, question):
            if question.researcher_id == user_id and not DesignAccessPolicy.is_owner(user, question.design_phase.project):
                raise QuestionReviewError("Researchers cannot review their own questions.")
            raise ValidationError("You do not have permission to review questions in this stage.")

        question.status = verdict
        question.reviewed_by_id = user_id
        question.justification = justification
        question.reviewed_at = timezone.now()
        question.save(update_fields=['status', 'justification', 'reviewed_by', 'reviewed_at'])
        return question

    @transaction.atomic
    def finalize_questions_stage(self, project_id: int, user: User) -> dict:
        # This is a high-level orchestration method
        try:
            design_phase = DesignPhase.objects.select_related('project').get(pk=project_id)
        except DesignPhase.DoesNotExist:
            raise InvalidProjectStateError("Design Phase not found.")

        # Authorization Check
        if not DesignAccessPolicy.can_consolidate_stage(user, design_phase):
            raise ProjectPermissionError("Only the owner can consolidate this project.")

        # Business Logic Validation
        if design_phase.current_stage != DesignPhase.DesignStage.RQ_DISCUSSION:
            raise InvalidProjectStateError(
                f"Phase must be in 'Discussion' stage to consolidate, but is in '{design_phase.get_current_stage_display()}'."
            )
        if not design_phase.research_questions.filter(status=ResearchQuestion.Status.APPROVED).exists():
            raise ConsolidationError("Cannot consolidate without at least one APPROVED question.")

        affected_rows = design_phase.research_questions.filter(
            status=ResearchQuestion.Status.SUGGESTED
        ).update(
            status=ResearchQuestion.Status.REJECTED,
            justification="Rejected automatically via consolidation."
        )
        return {
            "rejected_automatically": affected_rows,
            "total_approved": design_phase.research_questions.filter(status=ResearchQuestion.Status.APPROVED).count()
        }
