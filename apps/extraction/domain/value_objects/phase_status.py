from enum import Enum

class PhaseStatus(str, Enum):
    """Estados de la fase de extracción"""
    INACTIVE = 'Inactive'  # No iniciada
    ACTIVE = 'Active'  # En progreso
    PAUSED = 'Paused'  # Pausada temporalmente
    COMPLETED = 'Completed'  # Finalizada manualmente
    AUTO_CLOSED = 'AutoClosed'  # Cerrada automáticamente

    def __str__(self):
        return self.value