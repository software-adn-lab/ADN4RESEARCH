class ExtractionDomainException(Exception):
    """Base para excepciones del dominio de extracción."""
    pass


class ResourceNotFound(ExtractionDomainException):
    pass


class BusinessRuleViolation(ExtractionDomainException):
    """Violación de reglas como 'No cerrar sin quotes'."""
    pass
