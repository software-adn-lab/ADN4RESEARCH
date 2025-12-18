from typing import List, Optional, Dict
from django.db import transaction

# Modelos y Opciones de Extracción
from .models import  Tag, TagTypeChoices, VisibilityChoices

class TagDefinitionService:
    """
    Servicio de Dominio para manejar la creación y gestión de Tags.
    """

    @transaction.atomic
    def define_deductive_tag(self, phase_id: int, name: str, rq_id: int = None, user=None) -> Tag:
        
        is_mandatory = True if rq_id else False
        
        visibility = VisibilityChoices.PUBLIC if is_mandatory else VisibilityChoices.PRIVATE

        tag = Tag.objects.create(
            extraction_phase_id=phase_id,
            name=name,
            rq_related_id=rq_id,
            type=TagTypeChoices.DEDUCTIVE,
            is_mandatory=is_mandatory,
            visibility=visibility,
            created_by=user,
            status='APROVED'
        )
        return tag