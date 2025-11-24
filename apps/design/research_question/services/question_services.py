from apps.design.research_question.models.research_question import ResearchQuestion
from apps.project.models import ProjectPhase
from config.events import bus
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.design.exceptions.research_question_exceptions import QuestionSubmissionError, QuestionNotFoundError
from apps.project.models import Project

# Modelo de Usuario activo en tu proyecto
User = get_user_model()

class ResearchQuestionService:
    def define_status(self, research_question: ResearchQuestion) -> str:
        if research_question.status in [
            ResearchQuestion.Status.SUGGESTED,
            ResearchQuestion.Status.APPROVED,
            ResearchQuestion.Status.REJECTED,
            ResearchQuestion.Status.SUGGEST_REJECT
        ]:
            return research_question.status

        calculated_status = research_question.calculate_status()
        if research_question.status != calculated_status:
            research_question.status = calculated_status
            research_question.save(update_fields=['status', 'modified_at'])

        return calculated_status

    def get_research_question_by_id(self, research_question_id, user):
        try:
            return ResearchQuestion.objects.get(id=research_question_id, researcher=user)
        except ResearchQuestion.DoesNotExist:
            raise QuestionNotFoundError(f"Question with id {research_question_id} not found")

    @transaction.atomic
    def submit_research_question_for_review(self, research_question_id: int):
        research_question = ResearchQuestion.objects.get(id=research_question_id)

        if not self.can_submit_question(research_question):
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

    def can_submit_question(self, research_question: ResearchQuestion) -> bool:
        return research_question.can_submit_for_review()

    def add_research_question(self, project_id, question, motivation, researcher_id, framework_fields) -> ResearchQuestion:
        if not framework_fields:
            raise ValueError("Framework fields cannot be empty")
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ValueError(f"Project with id {project_id} does not exist")

        if not self._is_valid_framework_fields(project.research_framework, framework_fields):
            raise ValueError("Invalid framework fields provided")
        question = ResearchQuestion.objects.create(
            project_id=project_id,
            research_framework_id=project.research_framework_id,
            researcher_id=researcher_id,
            question=question,
            motivation=motivation,
            framework_fields=framework_fields
        )
        return question

    def _is_valid_framework_fields(self, framework, fields):
        allowed_keys = set(framework.get_allowed_keys())
        input_keys = set(fields.keys())
        return allowed_keys == input_keys

    @transaction.atomic
    def update_research_question(self, question_id, user, **data):
        try:
            question = ResearchQuestion.objects.select_related('project__owner').get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise ValidationError("Question not found.")
        self._validate_edit_permissions(question, user)
        updated_question = self._apply_updates(question, data)
        return updated_question

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
            return self.update_research_question(
                question_id=question_id,
                user=user,
                **payload
            )
        else:

            return self.add_research_question(
                project_id=project_id,
                researcher_id=user.id,
                **payload
            )

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

    def get_all_questions_by_user_and_project(self, user, project_id: int):
        return ResearchQuestion.objects.filter(
            researcher=user,
            project__id=project_id
        ).order_by('-modified_at')

    def get_research_questions_by_status(self, project_id, status):
        return ResearchQuestion.objects.filter(
            project_id=project_id,
            status=status
        ).order_by('-modified_at')

    def select_question_to_suggest_action(self, question_id: int, suggester_id: int):
        try:
            question = ResearchQuestion.objects.get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise ValidationError("Question not found.")
        if question.researcher_id == suggester_id:
            raise ValidationError("Cannot suggest action on your own question.")
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
        project = Project.objects.select_related('owner').get(pk=project_id)

        if project.owner != user:
            raise ValidationError("Only the owner can consolidate.")
        try:
            phase = project.phases.get(phase_type=ProjectPhase.PhaseType.DESIGN, is_active=True)
        except ProjectPhase.DoesNotExist:
            raise ValidationError("Active Design phase not found.")
        if phase.current_stage != ProjectPhase.Stage.RQ_DISCUSSION:
            raise ValidationError("Phase must be in 'Discussion' stage.")
        if not project.research_questions.filter(status=ResearchQuestion.Status.APPROVED).exists():
            raise ValidationError("Must have at least one APPROVED question.")
        return project, phase
