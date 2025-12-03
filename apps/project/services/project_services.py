from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.project.models import Project, ResearchFramework
from typing import List
from django.db import transaction
from django.db.models import Q
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
        return list(ProjectKeyword.objects.by_project(project_id))

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
                ).distinct()
            return queryset.get(id=project_id)

        except Project.DoesNotExist:
            raise ProjectNotFoundError(f"Project {project_id} not found or access denied.")