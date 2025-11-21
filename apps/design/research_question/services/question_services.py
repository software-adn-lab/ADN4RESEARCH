import logging
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.project.models import ResearchFramework
from config.events import bus
from django.db.models import Q
from django.contrib.auth import get_user_model
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
        # project fields no debe ser vacio {}
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
        question.save()
        return question
    
    def _is_valid_framework_fields(self, framework, fields):
        if not fields:
            return True
        allowed_keys = set(framework.get_allowed_keys())
        input_keys = set(fields.keys())
        return allowed_keys == input_keys
        
    def update_research_question(self, question_id, user, suggested_question=None, motivation=None, framework_fields=None):
        question = self.get_research_question_by_id(question_id, user=user)
        update_fields = []
        # Solo actualizar campos permitidos si se proporcionan
        if suggested_question is not None:
            question.question = suggested_question
            update_fields.append('suggested_question')
        
        if motivation is not None:
            question.motivation = motivation
            update_fields.append('motivation')
        
        if framework_fields is not None:
            self._is_valid_framework_fields(question.research_framework, framework_fields)
            question.framework_fields = framework_fields
            update_fields.append('framework_fields')
        if update_fields:
            update_fields.extend(['status', 'modified_at'])
            question.save(update_fields=update_fields)
        return question
    
    @transaction.atomic
    def autosave_question(self, data, user, project_id):
        question_id = data.get('id') or None
        framework_fields_data = {
            key.replace('framework_fields[', '').replace(']', ''): value
            for key, value in data.items() if key.startswith('framework_fields[')
        }
        if question_id:
            # Actualizar la pregunta
            question = self.update_research_question(
                question_id=question_id,
                user=user,
                suggested_question=data.get('suggested_question', ''),
                motivation=data.get('motivation', ''),
                framework_fields=framework_fields_data
            )
        else:
            # crea la pregunta
            question = self.add_research_question(
                project_id=project_id,
                question=data.get('suggested_question', ''),
                motivation=data.get('motivation', ''),
                researcher_id=user.id, 
                framework_fields=framework_fields_data
            )
        
        return question
    
    def approve_research_question(self, question_id: int, justification: str) -> ResearchQuestion:
        question = ResearchQuestion.objects.get(id=question_id)
        question.status = ResearchQuestion.Status.APPROVED
        question.justification = justification
        question.save(update_fields=['status', 'justification', 'modified_at'])
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
    
    def get_questions_available_for_approval(self, project_id, reviewer_id):
        return ResearchQuestion.objects.filter(
            project_id=project_id,
            status=ResearchQuestion.Status.SUGGESTED,
        ).exclude(
        researcher_id=reviewer_id)
    
    def get_frameworks(self, request):
        frameworks = ResearchFramework.objects.filter(Q(is_global=True) | Q(assigned_by=request.user))
        return frameworks
    
    def get_strategy_by_question(self, research_question_id: int):
        try:
            strategy = SearchStrategy.objects.get(research_question_id=research_question_id)
            return strategy
        except SearchStrategy.DoesNotExist:
            return None