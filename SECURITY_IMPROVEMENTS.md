# Mejoras de Seguridad - Control de Acceso a Extracción

## Resumen
Se han implementado limitaciones de seguridad para asegurar que solo los usuarios que son miembros de un proyecto puedan acceder a cualquier URL de extracción.

## Cambios Realizados

### 1. Nuevo Mixin: `ProjectMemberRequiredMixin`
**Archivo:** `apps/extraction/shared/mixins.py`

Se creó un nuevo mixin que verifica la membresía del proyecto antes de permitir el acceso:

```python
class ProjectMemberRequiredMixin(UserPassesTestMixin):
    """
    Mixin para asegurar que el usuario sea miembro del proyecto.
    
    Requisitos:
    - La vista debe tener project_id en kwargs o en URL
    - El usuario debe ser el owner del proyecto o estar en memberships
    """
    
    def test_func(self):
        """Verificar que el usuario es miembro del proyecto."""
        project_id = self.kwargs.get('project_id')
        
        if not project_id:
            raise PermissionDenied("project_id es requerido")
        
        provider = ProjectManagementProvider()
        return provider.is_project_member(project_id, self.request.user)
```

### 2. Integración con Provider Existente
Se utiliza `ProjectManagementProvider.is_project_member()` que ya existía en `apps/project/api/providers.py`.

**Lógica:**
- Retorna `True` si el usuario es el owner del proyecto
- Retorna `True` si el usuario está en `project.memberships`
- Retorna `False` en todos los otros casos

### 3. Vistas Actualizadas

#### Planning Views (`apps/extraction/planning/views.py`)
- `ExtractionPhaseDetailView` - Dashboard de extracción
- `PhaseConfigUpdateView` - Configuración de fase
- `PhaseOpenView` - Apertura de fase

**Patrón:**
```python
class ExtractionPhaseDetailView(LoginRequiredMixin, ProjectMemberRequiredMixin, DetailView):
    ...
```

#### Taxonomy Views (`apps/extraction/taxonomy/views.py`)
- `TagCreateView` - Crear tags deductivos
- `InductiveTagCreateView` - Crear tags inductivos
- `TagListView` - Listar tags
- `PendingTagsListView` - Tags pendientes de aprobación
- `TagApproveView` - Aprobar tags
- `TagRejectView` - Rechazar tags
- `BulkTagApproveView` - Aprobación masiva
- `UsableTagsAPIView` - API de tags disponibles

#### Core Views (`apps/extraction/core/views.py`)
- `PaperDetailView` - Detalle del paper
- `PaperPDFView` - Servir PDF
- `PaperCompleteView` - Marcar como completado
- `QuoteCreateView` - Crear quotes
- `QuoteDeleteView` - Eliminar quotes

## Flujo de Seguridad

### Antes
```
Usuario accede a /project/3/extraction/phases/1/
    ↓
¿Usuario logueado? (LoginRequiredMixin)
    ↓
Acceso permitido
```

### Después
```
Usuario accede a /project/3/extraction/phases/1/
    ↓
¿Usuario logueado? (LoginRequiredMixin)
    ↓
¿Usuario es miembro del proyecto 3? (ProjectMemberRequiredMixin)
    - ¿Es owner? Sí → Acceso permitido
    - ¿Está en memberships? Sí → Acceso permitido
    - No es miembro → PermissionDenied (403)
    ↓
Continuar
```

## Testing

Se verificó correctamente:

```
[OK] ProjectManagementProvider inicializado
[OK] ProjectMemberRequiredMixin disponible
[OK] ExtractionPhaseDetailView importada
[OK] ProjectMemberRequiredMixin en cadena de herencia
```

### Ejemplo de Comportamiento

```python
# Project 1, Owner: owner_user
provider = ProjectManagementProvider()

# El owner puede acceder
provider.is_project_member(1, owner_user)  # True

# Otros usuarios no pueden
provider.is_project_member(1, researcher_user)  # False
```

## Impacto

- **Seguridad:** Los usuarios no pueden acceder a datos de extracción de proyectos en los que no participan
- **Compatibilidad:** Las vistas existentes siguen funcionando para usuarios autorizados
- **Performance:** El check de membresía es una sola query optimizada

## URLs Protegidas

Todas estas URLs requieren que el usuario sea miembro del proyecto:

```
/project/<project_id>/extraction/phases/<phase_id>/
/project/<project_id>/extraction/phases/<phase_id>/config/
/project/<project_id>/extraction/phases/<phase_id>/open/
/project/<project_id>/extraction/phases/<phase_id>/tags/
/project/<project_id>/extraction/phases/<phase_id>/tags/create/
/project/<project_id>/extraction/phases/<phase_id>/tags/create-inductive/
/project/<project_id>/extraction/phases/<phase_id>/tags/pending/
/project/<project_id>/extraction/papers/<paper_id>/
/project/<project_id>/extraction/papers/<paper_id>/pdf/
/project/<project_id>/extraction/papers/<paper_id>/complete/
/project/<project_id>/extraction/papers/quotes/create/
/project/<project_id>/extraction/papers/quotes/<quote_id>/delete/
```

## Configuración Futura

Si se necesita permitir acceso más granular, se pueden crear mixins adicionales como:

- `ProjectOwnerRequiredMixin` - Solo owners
- `ProjectResearcherRequiredMixin` - Solo researchers
- `ProjectAdminRequiredMixin` - Solo admins del proyecto

## Referencias

- Django UserPassesTestMixin: https://docs.djangoproject.com/en/stable/topics/auth/default/#the-userpassestestmixin-mixin
- ProjectManagementProvider: `apps/project/api/providers.py`
