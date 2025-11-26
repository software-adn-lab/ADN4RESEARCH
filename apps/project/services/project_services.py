from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.project.models import Project, ProjectPhase, ResearchFramework
from typing import List
from django.core.exceptions import ValidationError
from django.db import transaction


class ProjectService:
    @transaction.atomic
    def create_project_with_framework(self, name, description, owner, framework_name, framework_fields):
        framework, _ = ResearchFramework.objects.get_or_create(
            name=framework_name,
            assigned_by=owner,
            defaults={'fields_data': framework_fields or {}}
        )
        project = Project.objects.create(
            name=name,
            description=description,
            owner=owner,
            research_framework=framework
        )
        self.add_member(project, owner, role="OWNER")
        return project

    def add_member(self, project: Project, user, role):
        # Implementation to add a member to the project with a specific role
        project.add_member(user, role)

    def get_members(self, project: Project):
        return project.get_members()

    def get_questions_for_project(self, project_id: int):
        project = Project.objects.get(id=project_id)
        return project.research_questions.all().order_by('-created_at')
    
    def get_project_framework(self, request):
        # Implementation to get the research framework associated with the project
        user = request.user
        project = Project.objects.filter(memberships__user=user).first()
        if project:
            return project.research_framework
        return None

    def get_project_members(self, project):
        return project.get_members()

    def get_project_keyterms(self, project_id: int) -> List[ProjectKeyword]:
        return list(ProjectKeyword.objects.filter(project_id=project_id))

    def get_project_by_id(self, project_id) -> Project:
        try:
            # Trae el proyecto Y su framework en UN solo viaje a la DB
            return Project.objects.select_related('research_framework', 'owner').get(id=project_id)
        except Project.DoesNotExist:
            # 
            pass
    
    def get_current_stage_deadline(self, project_id: int):
        try:
            phase = ProjectPhase.objects.get(
                project_id=project_id, 
                phase_type=ProjectPhase.PhaseType.DESIGN
            )
            return phase.end_date
        except ProjectPhase.DoesNotExist:
            return None
    
    def get_design_timeline_context(self, project_id):
        """
        Genera la estructura de datos para el Timeline (Completed, Current, Upcoming).
        """
        project = self.get_project_by_id(project_id)
        phase = project.phases.filter(phase_type=ProjectPhase.PhaseType.DESIGN).first()
        if not phase: return []

        current_stage = phase.current_stage
        design_flow = ProjectPhase.STAGES_FLOW[ProjectPhase.PhaseType.DESIGN]
        
        timeline_stages = []
        is_past = True 

        for stage_key in design_flow:
            status = 'upcoming'
            if stage_key == current_stage:
                is_past = False
                status = 'current'
            elif stage_key == 'FINISHED':
                status = 'finished'
            elif is_past:
                status = 'completed'

            # Usamos el label del Enum para mostrar texto bonito
            label = ProjectPhase.Stage(stage_key).label 

            timeline_stages.append({
                'key': stage_key,
                'label': label,
                'status': status
            })
        
        return timeline_stages
        
class ProjectPhaseService:
    
    @transaction.atomic
    def open_stage_phase(self, project_id, phase_type, target_stage):
        phase, created = ProjectPhase.objects.update_or_create(
            project_id=project_id,
            phase_type=phase_type,
            defaults={
                'current_stage': target_stage,
                'is_active': True
            }
        )
        return phase

    def get_phase_end_date(self, project_id: int, phase_type: str) -> str:
        try:
            phase = ProjectPhase.objects.get(project_id=project_id, phase_type=phase_type)
            return phase.end_date
        except ProjectPhase.DoesNotExist:
            return None