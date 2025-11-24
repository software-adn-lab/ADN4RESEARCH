from dataclasses import dataclass
from typing import Optional

from ..value_objects.tag_status import TagStatus
from ..value_objects.tag_type import TagType
from ..value_objects.tag_visibility import TagVisibility


@dataclass
class Tag:
    """
    Entidad.
    Los Tags suelen ser definidos a nivel de Proyecto/Estudio,
    pero se usan aquí. Frozen para simular inmutabilidad en este contexto.
    """
    id: int
    name: str
    project_id: int
    is_mandatory: bool
    created_by_user_id: int
    question_id: Optional[int] = None
    status: TagStatus = TagStatus.PENDING
    visibility: TagVisibility = TagVisibility.PRIVATE
    type: TagType = TagType.DEDUCTIVE

    def approve(self):
        self.status = TagStatus.APPROVED
        self.visibility = TagVisibility.PUBLIC

    def reject(self):
        self.status = TagStatus.REJECTED
        self.visibility = TagVisibility.PRIVATE