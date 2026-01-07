"""
Bounded Context: Taxonomy
Servicios de Dominio para gestión de Tags

Los servicios encapsulan la lógica de negocio compleja y
coordinan operaciones que involucran múltiples entidades.

Referencia Django Transactions:
https://docs.djangoproject.com/en/stable/topics/db/transactions/
"""
from typing import Optional, List
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError

from .models import Tag, TagTypeChoices, VisibilityChoices, ApprovalStatusChoices


class TagDefinitionService:
    """
    Servicio de Dominio para manejar la creación y gestión de Tags.
    
    Responsabilidades:
    - Crear tags deductivos (definidos a priori)
    - Crear tags inductivos (emergentes durante extracción)
    - Coordinar la lógica de creación con las reglas de negocio
    """

    @transaction.atomic
    def define_deductive_tag(
        self, 
        phase_id: int, 
        name: str, 
        rq_id: Optional[int] = None, 
        user=None,
        color: Optional[str] = None
    ) -> Tag:
        """
        Crea un tag deductivo.
        
        Tags deductivos:
        - Son definidos por el líder del proyecto antes de la extracción
        - Estado: APPROVED (no requieren aprobación)
        - Visibilidad: PUBLIC (todos los researchers pueden usarlos)
        - Pueden estar vinculados a una pregunta de investigación
        
        Args:
            phase_id: ID de la fase de extracción
            name: Nombre del tag
            rq_id: ID de la pregunta de investigación (opcional)
            user: Usuario que crea el tag
            color: Color hexadecimal (opcional)
        
        Returns:
            Tag: Instancia del tag creado
        
        Raises:
            ValidationError: Si ya existe un tag con el mismo nombre en la fase
        """
        # Verificar unicidad
        if Tag.objects.filter(extraction_phase_id=phase_id, name__iexact=name).exists():
            raise ValidationError(f'Ya existe un tag con el nombre "{name}" en esta fase.')
        
        # Tags vinculados a RQ son obligatorios
        is_mandatory = True if rq_id else False
        
        tag = Tag.objects.create(
            extraction_phase_id=phase_id,
            name=name,
            color=color,
            rq_related_id=rq_id,
            type=TagTypeChoices.DEDUCTIVE,
            is_mandatory=is_mandatory,
            visibility=VisibilityChoices.PUBLIC,
            created_by=user,
            status=ApprovalStatusChoices.APPROVED  # Deductivos nacen aprobados
        )
        
        return tag

    @transaction.atomic
    def define_inductive_tag(
        self,
        phase_id: int,
        name: str,
        user,
        color: Optional[str] = None
    ) -> Tag:
        """
        Crea un tag inductivo durante el proceso de extracción.
        
        Tags inductivos:
        - Emergen durante la extracción cuando un researcher
          identifica un patrón o tema no previsto
        - Estado inicial: PENDING (requieren aprobación del líder)
        - Visibilidad inicial: PRIVATE (solo el creador puede usarlo)
        - Al ser aprobados: PUBLIC y APPROVED
        
        Args:
            phase_id: ID de la fase de extracción
            name: Nombre del tag emergente
            user: Usuario (researcher) que crea el tag
            color: Color hexadecimal (opcional)
        
        Returns:
            Tag: Instancia del tag inductivo creado
        
        Raises:
            ValidationError: Si ya existe un tag con el mismo nombre en la fase
            ValueError: Si no se proporciona un usuario
        """
        if not user:
            raise ValueError('Se requiere un usuario para crear tags inductivos.')
        
        # Verificar unicidad (incluyendo tags de otros usuarios)
        if Tag.objects.filter(extraction_phase_id=phase_id, name__iexact=name).exists():
            raise ValidationError(
                f'Ya existe un tag con el nombre "{name}" en esta fase. '
                f'Puedes usar el tag existente si está disponible.'
            )
        
        # Generar color si no se proporciona
        if not color:
            import random
            color = '#{:06x}'.format(random.randint(0, 0xFFFFFF)).upper()
        
        tag = Tag.objects.create(
            extraction_phase_id=phase_id,
            name=name,
            color=color,
            type=TagTypeChoices.INDUCTIVE,
            is_mandatory=False,  # Inductivos nunca son obligatorios
            visibility=VisibilityChoices.PRIVATE,  # Solo el creador puede usarlo
            created_by=user,
            status=ApprovalStatusChoices.PENDING,  # Requiere aprobación
            rq_related=None  # Los inductivos no tienen RQ inicialmente
        )
        
        return tag


class TagApprovalService:
    """
    Servicio de Dominio para aprobar/rechazar tags inductivos.
    
    Responsabilidades:
    - Aprobar tags inductivos (cambiar a PUBLIC + APPROVED)
    - Rechazar tags inductivos
    - Verificar permisos de aprobación
    """
    
    def get_pending_tags_for_phase(self, phase_id: int) -> List[Tag]:
        """
        Obtiene todos los tags inductivos pendientes de una fase.
        
        Args:
            phase_id: ID de la fase de extracción
        
        Returns:
            QuerySet de tags pendientes
        """
        return Tag.objects.filter(
            extraction_phase_id=phase_id,
            type=TagTypeChoices.INDUCTIVE,
            status=ApprovalStatusChoices.PENDING
        ).select_related('created_by').order_by('-created_at')
    
    @transaction.atomic
    def approve_tag(self, tag_id: int, approved_by) -> Tag:
        """
        Aprueba un tag inductivo.
        
        Al aprobar:
        - Estado: APPROVED
        - Visibilidad: PUBLIC
        
        Args:
            tag_id: ID del tag a aprobar
            approved_by: Usuario que aprueba (debe tener permisos)
        
        Returns:
            Tag: Tag actualizado
        
        Raises:
            Tag.DoesNotExist: Si el tag no existe
            ValueError: Si el tag no puede ser aprobado
        """
        tag = Tag.objects.select_for_update().get(pk=tag_id)
        
        if not tag.can_be_approved_by(approved_by):
            raise ValueError(
                f'El tag "{tag.name}" no puede ser aprobado. '
                f'Solo tags inductivos pendientes pueden aprobarse.'
            )
        
        tag.approve(approved_by=approved_by)
        
        return tag
    
    @transaction.atomic
    def reject_tag(self, tag_id: int, rejected_by, reason: Optional[str] = None) -> Tag:
        """
        Rechaza un tag inductivo.
        
        Args:
            tag_id: ID del tag a rechazar
            rejected_by: Usuario que rechaza
            reason: Motivo del rechazo (opcional)
        
        Returns:
            Tag: Tag actualizado
        
        Raises:
            Tag.DoesNotExist: Si el tag no existe
            ValueError: Si el tag no puede ser rechazado
        """
        tag = Tag.objects.select_for_update().get(pk=tag_id)
        
        tag.reject(rejected_by=rejected_by, reason=reason)
        
        return tag
    
    @transaction.atomic
    def bulk_approve_tags(self, tag_ids: List[int], approved_by) -> List[Tag]:
        """
        Aprueba múltiples tags inductivos.
        
        Args:
            tag_ids: Lista de IDs de tags a aprobar
            approved_by: Usuario que aprueba
        
        Returns:
            Lista de tags aprobados
        """
        approved_tags = []
        
        for tag_id in tag_ids:
            try:
                tag = self.approve_tag(tag_id, approved_by)
                approved_tags.append(tag)
            except (Tag.DoesNotExist, ValueError):
                # Continuar con el siguiente tag si hay error
                continue
        
        return approved_tags


class TagUsageService:
    """
    Servicio para consultar tags disponibles para un usuario.
    
    Responsabilidades:
    - Obtener tags que un usuario puede usar en una Quote
    - Filtrar tags según permisos y estado
    """
    
    def get_usable_tags_for_user(self, phase_id: int, user) -> List[Tag]:
        """
        Obtiene los tags que un usuario puede usar en una Quote.
        
        Reglas:
        - Tags deductivos aprobados: todos
        - Tags inductivos aprobados: todos  
        - Tags inductivos pendientes: solo del usuario
        
        Args:
            phase_id: ID de la fase de extracción
            user: Usuario que va a usar los tags
        
        Returns:
            QuerySet de tags usables
        """
        return (
            Tag.objects
            .for_phase(phase_id)
            .usable_by(user)
            .select_related('rq_related', 'created_by')
            .order_by('type', 'name')
        )
    
    def get_tags_grouped_by_type(self, phase_id: int, user) -> dict:
        """
        Obtiene tags agrupados por tipo para mostrar en UI.
        
        Returns:
            {
                'deductive': QuerySet de tags deductivos,
                'inductive_approved': QuerySet de tags inductivos aprobados,
                'inductive_pending': QuerySet de tags inductivos pendientes (propios),
            }
        """
        base_qs = Tag.objects.for_phase(phase_id)
        
        return {
            'deductive': base_qs.filter(
                type=TagTypeChoices.DEDUCTIVE,
                status=ApprovalStatusChoices.APPROVED
            ),
            'inductive_approved': base_qs.filter(
                type=TagTypeChoices.INDUCTIVE,
                status=ApprovalStatusChoices.APPROVED
            ),
            'inductive_pending': base_qs.filter(
                type=TagTypeChoices.INDUCTIVE,
                status=ApprovalStatusChoices.PENDING,
                created_by=user
            ),
        }