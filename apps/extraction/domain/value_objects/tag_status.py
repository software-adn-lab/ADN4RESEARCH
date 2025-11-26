from enum import Enum

class TagStatus(str, Enum):
    PENDING = 'Pending'     # Propuesto por researcher
    APPROVED = 'Approved'   # Aceptado por Owner
    REJECTED = 'Rejected'   # Rechazado (solo visible para el creador)