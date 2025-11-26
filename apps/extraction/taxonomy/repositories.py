from typing import List, Optional
from django.db.models import Q
from .models import Tag


class TagRepository:
    def get_by_id(self, tag_id: int) -> Optional[Tag]:
        try:
            return Tag.objects.get(id=tag_id)
        except Tag.DoesNotExist:
            return None

    def get_by_name_and_project(self, name: str, project_id: int) -> Optional[Tag]:
        """Busca un tag por nombre dentro de un proyecto"""
        try:
            return Tag.objects.get(name=name, project_id=project_id, merged_into__isnull=True)
        except Tag.DoesNotExist:
            return None

    def list_by_project(self, project_id: int) -> List[Tag]:
        """Lista todos los tags activos de un proyecto"""
        return list(Tag.objects.filter(project_id=project_id, merged_into__isnull=True))

    def get_mandatory_tags(self, project_id: int) -> List[Tag]:
        """Retorna tags obligatorios (deductivos vinculados a PIs)"""
        return list(Tag.objects.filter(
            project_id=project_id, 
            is_mandatory=True,
            merged_into__isnull=True
        ))

    def get_tags_for_user(self, project_id: int, user_id: int) -> List[Tag]:
        """
        Retorna tags visibles para un usuario específico:
        - Tags públicos y aprobados
        - Tags privados creados por el usuario (incluso pendientes/rechazados)
        """
        return list(Tag.objects.filter(
            Q(project_id=project_id, merged_into__isnull=True) & (
                # Tags públicos y aprobados
                Q(is_public=True, approval_status=Tag.ApprovalStatus.APPROVED) |
                # Tags propios del usuario (cualquier estado)
                Q(created_by_id=user_id)
            )
        ).distinct())

    def get_pending_tags(self, project_id: int) -> List[Tag]:
        """Tags pendientes de aprobación para el Owner"""
        return list(Tag.objects.filter(
            project_id=project_id,
            approval_status=Tag.ApprovalStatus.PENDING,
            merged_into__isnull=True
        ))

    def get_tags_by_names(self, names: List[str], project_id: int) -> List[Tag]:
        """Obtiene tags por lista de nombres"""
        return list(Tag.objects.filter(
            name__in=names,
            project_id=project_id,
            merged_into__isnull=True
        ))

    def create(self, **kwargs) -> Tag:
        return Tag.objects.create(**kwargs)

    def update(self, tag: Tag, **kwargs) -> Tag:
        for key, value in kwargs.items():
            setattr(tag, key, value)
        tag.save()
        return tag

    def delete(self, tag: Tag):
        tag.delete()

    def save(self, tag: Tag) -> Tag:
        tag.save()
        return tag

    def merge_tags(self, source_tag: Tag, target_tag: Tag) -> Tag:
        """
        Fusiona source_tag en target_tag.
        - Marca source_tag como fusionado
        - Reasigna todas las quotes del source al target
        """
        # Reasignar quotes del source al target
        for quote in source_tag.quotes.all():
            quote.tags.remove(source_tag)
            quote.tags.add(target_tag)
        
        # Marcar como fusionado
        source_tag.merged_into = target_tag
        source_tag.save()
        
        return target_tag
