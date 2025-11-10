from apps.design.models.research_question import ResearchFramework, ResearchQuestion
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
    def submit_research_question_for_review(self, research_question: ResearchQuestion):
        if not self.can_submit_question(research_question):
            raise QuestionSubmissionError(
                f"Question {research_question.id} cannot be submitted. "
                f"Current status: {research_question.get_status_display()}"
            )
        research_question.status = ResearchQuestion.Status.SUGGESTED
        research_question.save(update_fields=['status', 'modified_at'])
        
        bus.publish("research_question_submitted", {
            "question_id": research_question.id,
            "question_text": research_question.suggested_question
        })
        
    def suggest_rejecting_question(self, research_question: ResearchQuestion, suggester, justification: str):
        research_question.status = ResearchQuestion.Status.SUGGEST_REJECT
        research_question.suggester = suggester
        research_question.justification = justification
        research_question.save(update_fields=['status', 'suggester', 'justification', 'modified_at'])
    
    def can_submit_question(self, research_question: ResearchQuestion) -> bool:
        return research_question.can_submit_for_review()
    
    @transaction.atomic
    def autosave_question(self, data, user, project_id):
        question_id = data.get('id') or None
        framework_id = data.get('research_framework')
        researcher_instance = user
        
        framework = self.get_framework_by_id(framework_id)
        project = Project.objects.get(id=project_id) # Obtener el proyecto
        
        framework_fields_data = {
            key.replace('framework_fields[', '').replace(']', ''): value
            for key, value in data.items() if key.startswith('framework_fields[')
        }
        if question_id:
            question = self.get_research_question_by_id(question_id, user=researcher_instance)
            question.research_framework = framework
            question.researcher = researcher_instance
            question.motivation = data.get('motivation', '')
            question.framework_fields = framework_fields_data
            question.suggested_question = data.get('suggested_question', '')
            question.project = project # Asegurarse de que el proyecto esté asignado
            question.save()
        else: 
            question = ResearchQuestion.objects.create(
                project=project, # Asignar el proyecto en la creación
                research_framework=framework,
                suggested_question=data.get('suggested_question', ''),
                motivation=data.get('motivation', ''),
                researcher=researcher_instance,
                framework_fields=framework_fields_data,
                
            )
        return question
    
    def get_all_questions_by_user_and_project(self, user, project_id: int):
        return ResearchQuestion.objects.filter(
            researcher=user,
            project__id=project_id
        ).order_by('-modified_at')
    
    def get_research_questions_by_status(self, project, status):
        return ResearchQuestion.objects.filter(
            project=project,
            status=status
        ).order_by('-modified_at')
    
    def add_research_question(self, project: Project, suggested_question, suggester, status):
        # Implementation to add a research question to the project
        ResearchQuestion.objects.create(
            project=project,
            suggested_question=suggested_question,
            suggester=suggester,
            status=status
        )
    
    def get_frameworks(self, request):
        frameworks = ResearchFramework.objects.filter(Q(is_global=True) | Q(assigned_by=request.user))
        return frameworks