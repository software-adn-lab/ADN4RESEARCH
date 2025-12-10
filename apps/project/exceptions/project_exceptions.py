class ProjectError(Exception):
    """Base exception for Project app"""
    pass

class ProjectCreationError(ProjectError):
    """Raised when project creation fails"""
    pass

class FrameworkError(ProjectError):
    """Raised when there is an issue with the Research Framework"""
    pass

class FrameworkValidationError(FrameworkError):
    """Raised when framework data is invalid"""
    pass

class MembershipError(ProjectError):
    """Raised when there is an issue adding or managing members"""
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
