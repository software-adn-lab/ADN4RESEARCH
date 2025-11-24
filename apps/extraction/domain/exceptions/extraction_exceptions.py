class ExtractionException(Exception):
    """Clase base para excepciones del dominio de extracción."""
    pass

class ExtractionValidationError(ExtractionException):
    """Error cuando una regla de negocio de validación falla."""
    pass

class ExtractionNotFound(ExtractionException):
    """Error cuando no se encuentra el recurso."""
    pass

class UnauthorizedExtractionAccess(ExtractionException):
    """Error de permisos a nivel de dominio."""
    pass

class InvalidExtractionState(ExtractionException):
    """Error cuando la extracción no está en el estado correcto."""
    pass

class StudyNotFound(ExtractionException):
    """Error cuando el estudio no existe."""
    pass

class TagNotFound(ExtractionException):
    """Error cuando un tag no existe."""
    pass

class ProjectAccessDenied(ExtractionException):
    """Error cuando el usuario no tiene acceso al proyecto."""
    pass

class QuoteValidationError(ExtractionException):
    """Error de validación en quotes."""
    pass