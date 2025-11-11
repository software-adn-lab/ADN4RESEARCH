"""
Excepciones de dominio para el módulo de adquisición.
"""


class DomainException(Exception):
    """Excepción base del dominio."""
    pass


class DomainValidationError(DomainException):
    """
    Se lanza cuando una validación de regla de negocio falla.

    Ejemplos:
    - strategy_id vacío
    - main_terms vacío
    - Año inválido (from > to)
    """

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")
