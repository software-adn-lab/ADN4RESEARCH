from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.exceptions import ConsolidationError, InvalidProjectStateError, ProjectPermissionError
from apps.project.models import ProjectPhase
from config.events import bus
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.design.exceptions.research_question_exceptions import InvalidFrameworkFieldsError, ProjectNotFoundError, QuestionReviewError, QuestionSubmissionError, QuestionNotFoundError
from apps.project.models import Project
from django.contrib.auth.models import User

from apps.design.shared.models.design_phase import DesignPhase
# user de django


class ResearchQuestionService:
    # METODOS CRUD - de DAO en una segunda version
    @transaction.atomic
    def add_research_question(self, project_id: int, question: str, motivation: str, researcher_id: int, framework_fields: dict) -> ResearchQuestion:
        if not framework_fields:
            raise InvalidFrameworkFieldsError("Framework fields cannot be empty")
        try:
            project = Project.objects.select_related('research_framework').get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError(f"Project with id {project_id} does not exist")
        if not DesignPhase.objects.filter(pk=project_id).exists():
             raise InvalidProjectStateError("The project does not have an initialized Design Phase.")
        if not self._is_valid_framework_fields(project.research_framework, framework_fields):
            raise InvalidFrameworkFieldsError("The provided fields do not match the project's research framework structure.")

        question = ResearchQuestion.objects.create(
            design_phase_id=project_id,   
            researcher_id=researcher_id,
            question=question,
            motivation=motivation,
            framework_fields=framework_fields
        )

        return question

    @transaction.atomic
    def update_research_question(self, question_id, user, **data):
        try:
            question = ResearchQuestion.objects.select_related('project__owner').get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise ValidationError("Question not found.")
        self._validate_edit_permissions(question, user)
        updated_question = self._apply_updates(question, data)
        return updated_question

    @transaction.atomic
    def delete_research_question(self, research_question_id: int, user: User):
        try:
            question = self.get_research_question_by_id(research_question_id, user)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError(f"Question with id {research_question_id} not found")
        question.delete()

    @transaction.atomic
    def get_research_question_by_id(self, research_question_id: int, user: User):
        try:
            return ResearchQuestion.objects.get(id=research_question_id, researcher=user)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError(f"Question with id {research_question_id} not found")

    def get_all_questions_by_user_and_project(self, project_id: int, user):
        return ResearchQuestion.objects.filter(
            researcher=user,
            project__id=project_id
        ).order_by('-modified_at')
    
    def filter_questions_by_status(self, questions_queryset, status):
        return questions_queryset.filter(status=status)

    def get_research_questions_by_project_and_status(self, project_id, status):
        return ResearchQuestion.objects.filter(
            design_phase_id=project_id, 
            status=status
        ).order_by('-modified_at')
        
    def get_discussion_research_questions_by_project(self, project_id: int):
        return ResearchQuestion.objects.by_project(project_id).in_discussion_phase().order_by('-modified_at')
        
    def get_research_questions_by_status(self, project_id, status):
        return ResearchQuestion.objects.by_project(project_id).by_status(status).order_by('-modified_at')

    # Logica de negocio
    # TODO: La limpieza de los datos es en el formulario, no en el servicio
    @transaction.atomic
    def autosave_question(self, cleaned_data, user, project_id, question_id) -> ResearchQuestion:
        # Extraemos los datos ya limpios y tipados
        framework_data = cleaned_data.get('framework_fields', {})
        question_text = cleaned_data.get('question', '')
        motivation = cleaned_data.get('motivation', '')
        payload = {
            'question': question_text,
            'motivation': motivation,
            'framework_fields': framework_data
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
            )
        research_question.status = ResearchQuestion.Status.SUGGESTED
        research_question.save(update_fields=['status', 'modified_at'])

        bus.publish("research_question_submitted", {
            "question_id": research_question.id,
            "question_text": research_question.question
        })

    def can_submit_question(self, research_question_id: int) -> bool:
        research_question = ResearchQuestion.objects.get(id=research_question_id)
        if research_question.status == ResearchQuestion.Status.READY_TO_SEND:
            return True
        return False

    def _is_valid_framework_fields(self, framework, fields):
        allowed_keys = set(framework.get_allowed_keys())
        input_keys = set(fields.keys())
        return allowed_keys == input_keys

    def _validate_edit_permissions(self, question, user):
        """Valida fase del proyecto y propiedad de la pregunta."""
        project = question.project
        is_owner = (project.owner == user)
        design_phase = project.phases.filter(phase_type=ProjectPhase.PhaseType.DESIGN).first()
        if design_phase:
            open_stages = [ProjectPhase.Stage.RQ_CREATION, ProjectPhase.Stage.RQ_DISCUSSION]
            if design_phase.current_stage not in open_stages and not is_owner:
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
            question.save(update_fields=fields_to_update)
        return question

    @transaction.atomic
    def review_research_question(self, question_id: int, verdict: str, justification: str) -> ResearchQuestion:
        allowed_verdicts = {
            ResearchQuestion.Status.APPROVED,
            ResearchQuestion.Status.REJECTED,
        }
        if verdict not in allowed_verdicts:
            raise ValidationError(f"Estado no válido para una revisión: {verdict}")
        question = ResearchQuestion.objects.get(id=question_id)
        question.status = verdict
        question.justification = justification
        question.save(update_fields=['status', 'justification', 'modified_at'])
        # Para la comunicacion, un ejemplo
        # self.notification_service.notify_researcher(question)
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
        question.status = action # O el campo correspondiente
        question.save()

        return question

    @transaction.atomic
    def consolidate_questions(self, project_id: int, user):
        project, design_phase = self._validate_consolidation_prerequisites(project_id, user)
        affected_rows = ResearchQuestion.objects.filter(
            project_id=project.id,
            status=ResearchQuestion.Status.SUGGESTED
        ).update(
            status=ResearchQuestion.Status.REJECTED,
            justification="Rejected automatically via consolidation."
        )
        design_phase.current_stage = ProjectPhase.Stage.CRITERIA_DEFINITION
        design_phase.save()

        return {
            "rejected_automatically": affected_rows,
            "total_approved": project.research_questions.filter(status=ResearchQuestion.Status.APPROVED).count()
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
        except DesignPhase.DoesNotExist: # O la excepción genérica ObjectDoesNotExist
             raise InvalidProjectStateError("Active Design phase not found.")

        if not phase.is_active:
            raise InvalidProjectStateError("Design phase is not active.")

        if phase.current_stage != DesignPhase.DesignStage.RQ_DISCUSSION:
            raise InvalidProjectStateError(
                f"Phase must be in 'Discussion' stage, but is in '{phase.get_current_stage_display()}'."
            )

        if not phase.research_questions.filter(status=ResearchQuestion.Status.APPROVED).exists():
            raise ConsolidationError("Cannot consolidate without at least one APPROVED question.")

        return project, phase
