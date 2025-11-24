from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.project.models import Project, ProjectPhase, ResearchFramework
from typing import List
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

    def get_project_by_id(self, project_id: int) -> Project:
        return Project.objects.get(id=project_id)


class ProjectPhaseService:

    @transaction.atomic
    def advance_current_stage(self, project_id, user):
        project = Project.objects.get(pk=project_id)
        phase = project.phases.filter(phase_type='DESIGN').first()

        # 1. Ejecutar lógica de la etapa actual (HOOK)
        if phase.current_stage == ProjectPhase.Stage.RQ_DISCUSSION:
            rq_service = ResearchQuestionService()
            # Aquí se hace la limpieza
            rq_service.consolidate_questions(project_id, user)

        # 2. Calcular Siguiente Etapa
        # (Si es el final, pasará a FINISHED, activando el bloqueo)
        flow = ProjectPhase.STAGES_FLOW[phase.phase_type]
        try:
            current_index = flow.index(phase.current_stage)
            next_stage = flow[current_index + 1]
        except IndexError:
            next_stage = ProjectPhase.Stage.FINISHED

        # 3. Guardar el cambio de fase (ESTO ES LO QUE ACTIVA EL BLOQUEO)
        phase.current_stage = next_stage
        phase.save()

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
