class ProjectError(Exception):
    """Base para errores del módulo de proyectos."""
    pass

class ProjectNotFoundError(ProjectError):
    """404: El proyecto no existe."""
    pass

class ProjectPermissionError(ProjectError):
    """403: El usuario no tiene permisos para esta acción."""
    pass

class InvalidProjectStateError(ProjectError):
    """409: El estado actual (Fase/Etapa) no permite esta acción."""
    pass

class ConsolidationError(ProjectError):
    """400/422: No se cumplen los requisitos de datos para consolidar."""
    pass