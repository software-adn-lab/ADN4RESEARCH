from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.project.models import Project, ProjectPhase, ResearchFramework
from typing import List
from django.db import transaction

from apps.design.shared.models.design_phase import DesignPhase

from apps.project.exceptions import ProjectNotFoundError


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
        DesignPhase.objects.create(
            project=project,
            is_active=True,
            current_stage=DesignPhase.DesignStage.RQ_CREATION
        )

        self.add_member(project, owner, role="OWNER")
        return project
    
    def add_member(self, project: Project, user, role):
        project.add_member(user, role)
        
    def get_members(self, project: Project):
        return project.get_members()

    def get_questions_for_project(self, project_id: int):
        """
        Obtiene las preguntas buscando explícitamente la fase asociada al proyecto.
        """
        try:
            # SEMÁNTICA CLARA: "Dame la fase cuyo project_id sea X"
            design_phase = DesignPhase.objects.get(project_id=project_id)
            return design_phase.research_questions.all().order_by('-created_at')
        except DesignPhase.DoesNotExist:
            return []
    
    def get_project_framework(self, request):
        user = request.user
        project = Project.objects.filter(memberships__user=user).first()
        if project:
            return project.research_framework
        return None

    def get_project_members(self, project):
        return project.get_members()

    def get_project_keyterms(self, project_id: int) -> List[ProjectKeyword]:
        """
        Obtiene los keywords filtrando por la relación con el proyecto.
        Aqui si lo relaciono a disenio porque es la fase que posee los keywords
        """
        return list(ProjectKeyword.objects.filter(design_phase__project_id=project_id))

    def get_project_by_id(self, project_id: int, user=None, related_fields: list = None) -> Project:
        try:
            queryset = Project.objects.all()
            if related_fields:
                queryset = queryset.select_related(*related_fields)
            else:
                queryset = queryset.select_related('owner', 'research_framework')
            if user:
                queryset = queryset.filter(
                    Q(owner=user) | Q(memberships__user=user)
                ).distinct() # distinct() evita duplicados si el join se complica
            return queryset.get(id=project_id)

        except Project.DoesNotExist:
            raise ProjectNotFoundError(f"Project {project_id} not found or access denied.")
    
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