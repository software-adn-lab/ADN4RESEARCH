import logging
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.project.models import ProjectPhase, ResearchFramework
from config.events import bus
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.design.exceptions.research_question_exceptions import QuestionSubmissionError, QuestionNotFoundError
from apps.project.models import Project

# Obtén el modelo de Usuario activo en tu proyecto
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
    
    def get_framework_by_id(self, framework_id):
        return ResearchFramework.objects.get(id=framework_id)
    
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
    
    #MEJORAR ESTE METODO VIBECODEADO
    @transaction.atomic
    def update_research_question(self, question_id, user, **data):
        try:
            question = ResearchQuestion.objects.select_related('project').get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise ValidationError("Question not found.")
        project = question.project
        is_owner = (project.owner == user)
        design_phase = project.phases.filter(phase_type=ProjectPhase.PhaseType.DESIGN).first()
        if design_phase and design_phase.current_stage == ProjectPhase.Stage.FINISHED:
            if not is_owner:
                raise ValidationError("The project is in FINISHED stage. Only the owner can edit questions.")
        if not is_owner and question.researcher != user:
            raise ValidationError("You do not have permission to edit this question.")
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
        # Usamos .get() para obtener la instancia única
            question = ResearchQuestion.objects.get(id=question_id)
        except ResearchQuestion.DoesNotExist:
            raise ValidationError("Question not found.")
        # Asegurarse de que la pregunta no es del mismo usuario
        if question.researcher_id == suggester_id:
            # Error porque no puede seleccionar una accion sobre su propia pregunta
            raise ValidationError("Cannot suggest action on your own question.")
        return question 
        
        

    
    def get_frameworks(self, user):
        frameworks = ResearchFramework.objects.filter(Q(is_global=True) | Q(assigned_by=user))
        return frameworks
    
    def get_strategy_by_question(self, research_question_id: int):
        try:
            strategy = SearchStrategy.objects.get(research_question_id=research_question_id)
            return strategy
        except SearchStrategy.DoesNotExist:
            return None
        
    @transaction.atomic
    def consolidate_questions(self, project_id: int, user):
        project = Project.objects.get(pk=project_id)
        if project.owner != user:
            raise ValidationError("Only the project owner can consolidate the discussion stage.")
        # Las suggested deben ser rechazadas automáticamente
        affected_rows = ResearchQuestion.objects.filter(
            project_id=project_id,
            status=ResearchQuestion.Status.SUGGESTED #
        ).update(
            status=ResearchQuestion.Status.REJECTED, #
            justification="Rejected automatically during discussion stage consolidation."
        )
        
        design_phase = project.phases.filter(phase_type='DESIGN').first() #
        
        if design_phase:
            # Asumiendo que ProjectPhase.Stage.FINISHED es lo que activa tu bloqueo
            design_phase.current_stage = 'FINISHED' 
            design_phase.save()
            
        stats = {
            "rejected_automatically": affected_rows,
            "total_approved": ResearchQuestion.objects.filter(project_id=project_id, status=ResearchQuestion.Status.APPROVED).count()
        }
        
        return stats