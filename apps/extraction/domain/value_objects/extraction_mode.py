from enum import Enum

class ExtractionMode(str, Enum):
    """Modo de extracción"""
    SINGLE = 'Single'  # Un investigador por estudio
    DOUBLE = 'Double'  # Dos investigadores (extracción por pares)

    def __str__(self):
        return self.value