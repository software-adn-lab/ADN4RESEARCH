from enum import Enum

class TagVisibility(str, Enum):
    PRIVATE = 'Private'     # Solo lo ve el dueño
    PUBLIC = 'Public'       # Lo ve todo el equipo