"""
Excepciones de la capa de aplicación para translation component.
"""


class ApplicationException(Exception):
    """Excepción base de la capa de aplicación."""
    pass


class InvalidTargetError(ApplicationException):
    """
    Se lanza cuando el target de traducción no es soportado.

    Targets válidos: "Scopus", "IEEE Xplore"
    """

    def __init__(self, target: str, valid_targets: list[str]):
        self.target = target
        self.valid_targets = valid_targets
        message = (
            f"Target '{target}' no es válido. "
            f"Targets soportados: {', '.join(valid_targets)}"
        )
        super().__init__(message)
