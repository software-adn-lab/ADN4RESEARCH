"""
Shared Kernel: Mixins reutilizables
"""
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from apps.project.api.providers import ProjectManagementProvider


class OwnerRequiredMixin(UserPassesTestMixin):
    """
    Mixin para asegurar que solo el dueño del proyecto pueda ejecutar acciones.
    
    Uso:
        class MyView(LoginRequiredMixin, OwnerRequiredMixin, View):
            pass

    Requisitos:
        - La vista debe tener `project_id` en sus kwargs.
    
    Referencia: https://docs.djangoproject.com/en/stable/topics/auth/default/#the-userpassestestmixin-mixin
    """
    
    def test_func(self):
        project_id = self.kwargs.get('project_id')
        if not project_id:
            raise PermissionDenied("project_id es requerido")
        
        provider = ProjectManagementProvider()
        return provider.is_project_owner(project_id, self.request.user)


class ProjectMemberRequiredMixin(UserPassesTestMixin):
    """
    Mixin para asegurar que el usuario sea miembro del proyecto.
    
    Requisitos:
    - La vista debe tener project_id en kwargs o en URL
    - El usuario debe ser el owner del proyecto o estar en memberships
    
    Uso:
        class MyView(LoginRequiredMixin, ProjectMemberRequiredMixin, View):
            def get(self, request, project_id, ...):
                pass
    
    Referencia: https://docs.djangoproject.com/en/stable/topics/auth/default/#the-userpassestestmixin-mixin
    """
    
    def test_func(self):
        """Verificar que el usuario es miembro del proyecto."""
        project_id = self.kwargs.get('project_id')
        
        if not project_id:
            raise PermissionDenied("project_id es requerido")
        
        provider = ProjectManagementProvider()
        return provider.is_project_member(project_id, self.request.user)