from typing import List, Optional
from ...domain.repositories.i_tag_repository import ITagRepository
from ...domain.entities.tag import Tag
from ..models import TagModel
from ..mappers.domain_mappers import TagMapper
from django.db.models import Q

from ...domain.value_objects.tag_status import TagStatus
from ...domain.value_objects.tag_visibility import TagVisibility


class DjangoTagRepository(ITagRepository):
    def __init__(self, acquisition_adapter):
        self.acquisition_adapter = acquisition_adapter

    def get_by_ids(self, tag_ids: List[int]) -> List[Tag]:
        qs = TagModel.objects.filter(pk__in=tag_ids)
        return [TagMapper.to_domain(m) for m in qs]

    def get_by_id(self, tag_id: int) -> Tag:
        model = TagModel.objects.get(pk=tag_id)
        return TagMapper.to_domain(model)

    def save(self, tag: Tag) -> Tag:
        data = TagMapper.to_db(tag)

        if tag.id:
            TagModel.objects.filter(pk=tag.id).update(**data)
            model = TagModel.objects.get(pk=tag.id)
        else:
            model = TagModel.objects.create(**data)
            tag.id = model.id

        return TagMapper.to_domain(model)

    def delete(self, tag: Tag) -> None:
        TagModel.objects.filter(pk=tag.id).delete()

    def get_mandatory_tags_for_project_context(self, study_id: int) -> List[Tag]:
        project_id = self.acquisition_adapter.get_project_context(study_id)
        if not project_id:
            return []

        qs = TagModel.objects.filter(
            project_id=project_id,
            is_mandatory=True,
            status=TagStatus.APPROVED.value
        )
        return [TagMapper.to_domain(t) for t in qs]

    def list_available_tags_for_user(
            self,
            user_id: int,
            project_id: int
    ) -> List[Tag]:
        qs = TagModel.objects.filter(
            project_id=project_id
        ).filter(
            Q(visibility=TagVisibility.PUBLIC.value) |
            Q(created_by_user_id=user_id)
        ).filter(
            status=TagStatus.APPROVED.value
        ).distinct()

        return [TagMapper.to_domain(m) for m in qs]