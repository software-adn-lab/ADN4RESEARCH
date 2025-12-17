from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.exceptions.project_exceptions import ConsolidationError, InvalidProjectStateError, ProjectPermissionError
from config.events import bus
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.design.exceptions.research_question_exceptions import InvalidFrameworkFieldsError, ProjectNotFoundError, QuestionReviewError, QuestionSubmissionError, QuestionNotFoundError, ResearchQuestionError
from apps.project.structure.models.project_models import Project
from django.contrib.auth.models import User
from apps.design.shared.models.design_phase import DesignPhase
from django.utils import timezone

class ResearchQuestionService:
    # METODOS CRUD - en una segunda version
    @transaction.atomic
    def add_research_question(self, project_id: int, question: str, motivation: str, researcher_id: int, framework_fields: dict) -> ResearchQuestion:
        try:
            design_phase = DesignPhase.objects.select_related('project__research_framework').get(pk=project_id)
        except DesignPhase.DoesNotExist:
            raise InvalidProjectStateError("The project does not have an initialized Design Phase.")
        project = design_phase.project

        # Validation: Check Stage Permissions
        if design_phase.current_stage not in DesignPhase.RQ_EDITION_STAGES:
            if project.owner_id != researcher_id:
                raise ValidationError(
                    f"Locked Stage: Only the owner can add questions during '{design_phase.get_current_stage_display()}'."
                )

        if not self._is_valid_framework_fields(project.research_framework, framework_fields or {}):
            raise InvalidFrameworkFieldsError("The provided fields do not match the project's research framework structure.")

        question = ResearchQuestion.objects.create(
            design_phase=design_phase,
            researcher_id=researcher_id,
            question=question,
            motivation=motivation,
            framework_fields=framework_fields
        )

        return question

    @transaction.atomic
    def update_research_question(self, question_id, user, **data):
        try:
            question = ResearchQuestion.objects.select_related(
                'design_phase__project__owner',
                'design_phase__project__research_framework'
            ).get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError("Question not found.")
        self._validate_edit_permissions(question, user)
        updated_question = self._apply_updates(question, data)
        return updated_question

    @transaction.atomic
    def delete_research_question(self, question_id: int, user) -> int:
        question = self.get_research_question_by_id(question_id, user)
        if question.status == ResearchQuestion.Status.APPROVED:
            raise ResearchQuestionError("Cannot delete an APPROVED question directly. Change its status first.")
        question.delete()

    def get_research_question_by_id(self, research_question_id: int, user: User):
        try:
            qs = ResearchQuestion.objects.select_related('design_phase__project__research_framework', 'design_phase__project__owner')
            question = qs.get(id=research_question_id)
            is_author = question.researcher == user
            is_owner = question.design_phase.project.owner == user
            if not (is_author or is_owner):
                raise QuestionNotFoundError(f"Question not found or access denied.")
            return question
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError(f"Question with id {research_question_id} not found")

    def get_questions_for_workspace(self, project_id: int, user, status_filter: str = None):
        try:
            owner_id = Project.objects.values_list('owner_id', flat=True).get(pk=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError(f"Project with id {project_id} not found.")
        qs = ResearchQuestion.objects.by_project(project_id)
        is_owner = (user.id == owner_id)
        if not is_owner:
            qs = qs.by_researcher(user)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-modified_at')

    def get_all_questions_by_user_and_project(self, project_id: int, user):
        return ResearchQuestion.objects.by_project(project_id).by_researcher(user).order_by('-modified_at')

    def get_discussion_research_questions_by_project(self, project_id: int, status_filter: str = None):
        qs = ResearchQuestion.objects.by_project(project_id).in_discussion_phase()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-modified_at')

    # Logica de negocio
    @transaction.atomic
    def autosave_question(self, cleaned_data, user, project_id, question_id) -> ResearchQuestion:
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

    def _validate_edit_permissions(self, question, user):
        """Valida fase del proyecto y propiedad de la pregunta."""
        design_phase = question.design_phase
        project_owner = design_phase.project.owner
        is_owner = (project_owner == user)
        if design_phase.current_stage not in DesignPhase.RQ_EDITION_STAGES:
            if not is_owner:
                raise ValidationError(
                    f"Locked Stage: Only the owner can edit questions during '{design_phase.get_current_stage_display()}'."
                )
        if not is_owner and question.researcher != user:
            raise ValidationError("You do not have permission to edit this question.")

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

        question = ResearchQuestion.objects.get(id=question_id)
        self._validate_stage_modification_permissions(question.design_phase, user_id)

        question.status = verdict
        question.reviewed_by_id = user_id
        question.justification = justification
        question.reviewed_at = timezone.now()
        question.save(update_fields=['status', 'justification', 'reviewed_by', 'reviewed_at'])
        return question

    def _validate_stage_modification_permissions(self, design_phase, user_id):
        # Validate Stage Permissions
        # Logic: If stage > RQ_DISCUSSION, only owner can review.
        stages = [s for s, _ in DesignPhase.DesignStage.choices]
        try:
            current_idx = stages.index(design_phase.current_stage)
            discussion_idx = stages.index(DesignPhase.DesignStage.RQ_DISCUSSION)
            is_past_stage = current_idx > discussion_idx
        except ValueError:
            is_past_stage = False

        is_owner = (design_phase.project.owner.id == user_id)

        if is_past_stage and not is_owner:
            raise ValidationError("The Discussion stage is finished. You cannot review questions anymore.")

    def validate_reviewer_eligibility(self, question_id: int, user_id: int) -> ResearchQuestion:
        try:
            question = ResearchQuestion.objects.select_related(
                'design_phase__project__owner'
            ).get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError("Question not found.")
        is_author = (question.researcher_id == user_id)
        is_owner = (question.design_phase.project.owner.id == user_id)
        if is_author and not is_owner:
            raise QuestionReviewError("Researchers cannot review their own questions. Wait for the Owner or a peer.")
        return question

    def select_question_to_suggest_action(self, question_id: int, suggester_id: int):
        try:
            question = ResearchQuestion.objects.get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise QuestionReviewError("Question not found.")
        if question.researcher_id == suggester_id:  # La regla que le puse: si eres el autor no puedes sugerir acciones sobre tu misma pregunta
            raise QuestionReviewError("Cannot suggest action on your own question.")
        return question

    def process_suggestion_action(self, question_id: int, user_id: int, action: str):
        try:
            question = ResearchQuestion.objects.get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            # Lanzamos nuestra excepción propia para no exponer errores de ORM a la vista
            raise QuestionReviewError("Question not found.")

        # 1. Regla: No puedes revisarte a ti mismo
        if question.researcher_id == user_id:
            raise QuestionReviewError("Cannot suggest action on your own question.")

        # 2. Validar acción
        if action not in ['APPROVED', 'REJECTED']:
            raise QuestionReviewError("Invalid action provided.")

        # 3. Aplicar cambios
        question.status = action  # O el campo correspondiente
        question.save()

        return question

    @transaction.atomic
    def finalize_questions_stage(self, project_id: int, user):
        project, design_phase = self._validate_consolidation_prerequisites(project_id, user)
        
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

    def _validate_consolidation_prerequisites(self, project_id, user):
        try:
            project = Project.objects.select_related('owner', 'design_phase').get(pk=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError(f"Project with id {project_id} not found.")

        if project.owner != user:
            raise ProjectPermissionError("Only the owner can consolidate this project.")

        try:
            phase = project.design_phase
        except DesignPhase.DoesNotExist:
            raise InvalidProjectStateError("Active Design phase not found.")
        if not phase.is_active:
            raise InvalidProjectStateError("Design phase is not active.")
        if phase.current_stage != DesignPhase.DesignStage.RQ_DISCUSSION:
            raise InvalidProjectStateError(
                f"Phase must be in 'Discussion' stage to consolidate, but is in '{phase.get_current_stage_display()}'."
            )
        if not phase.research_questions.filter(status=ResearchQuestion.Status.APPROVED).exists():
            raise ConsolidationError("Cannot consolidate without at least one APPROVED question.")

        return project, phase
