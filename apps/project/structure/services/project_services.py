from apps.design.search_strategy.models.keyword import ProjectKeyword
from apps.project.exceptions.project_exceptions import ProjectCreationError, ProjectNotFoundError
from apps.project.structure.models.project_models import Project, ResearchFramework
from typing import List
from django.db import transaction
from django.db.models import Q
# REFACTORED: Design API factory function used INSIDE method (lazy init) to avoid circular import
# Circular broken: DesignPhase → BasePhase → Project API ✗→ ProjectService (uses factory at runtime)


class ProjectService:
    @transaction.atomic
    def create_project_with_framework(self, project_title, project_end_date, summary, motivation, general_objective, owner, framework_name, framework_fields, specific_objectives_data=None, expected_results_data=None, members_workload=None):
        try:
            framework, _ = ResearchFramework.objects.get_or_create(
                name=framework_name,
                assigned_by=owner,
                defaults={'fields_data': framework_fields or {}}
            )
            project = Project.objects.create(
                title=project_title,
                summary=summary,
                end_date=project_end_date,
                motivation=motivation,
                general_objective=general_objective,
                owner=owner,
                research_framework=framework
            )

            from apps.design.api import get_design_management
            design_mgmt = get_design_management()  # Factory returns IDesignManagement
            design_mgmt.initialize_design_phase(project.id)

            # Create Specific Objectives
            if specific_objectives_data:
                from apps.project.structure.models.project_models import SpecificObjective
                for obj_data in specific_objectives_data:
                    # obj_data can be a dict or a string if simple list
                    desc = obj_data.get('description') if isinstance(obj_data, dict) else str(obj_data)
                    if desc and desc.strip():
                        SpecificObjective.objects.create(project=project, description=desc)

            # Create Expected Results
            if expected_results_data:
                from apps.project.structure.models.project_models import ExpectedResult
                for res_data in expected_results_data:
                    desc = res_data.get('description') if isinstance(res_data, dict) else str(res_data)
                    if desc and desc.strip():
                        ExpectedResult.objects.create(project=project, description=desc)

            # Add Owner as member (with default workload of 0 if not specified)
            owner_workload = 0
            if members_workload:
                for member_data in members_workload:
                    if member_data['user_id'] == owner.id:
                        owner_workload = member_data['workload']
                        break
            self.add_member(project, owner, role="OWNER", workload=owner_workload)

            # Add other members with their workload
            if members_workload:
                from django.contrib.auth.models import User
                for member_data in members_workload:
                    user_id = member_data['user_id']
                    workload = member_data['workload']
                    if user_id != owner.id:
                        try:
                            member_user = User.objects.get(id=user_id)
                            self.add_member(project, member_user, role="RESEARCHER", workload=workload)
                        except User.DoesNotExist:
                            continue

            return project
        except Exception as e:
            raise ProjectCreationError(f"Failed to create project: {str(e)}") from e

    def add_member(self, project: Project, user, role, workload=0):
        project.add_member(user, role, workload)

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

    def get_members(self, project: Project):
        return project.get_members()

    # REMOVED: get_questions_for_project() method
    # This method imported DesignPhase directly causing circular import.
    # If needed, this should be in Design module's API (IDesignProtocol.get_protocol_questions)
    # Project module shouldn't know about Design internals.

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
