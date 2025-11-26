from apps.extraction.domain.entities.extraction_phase import ExtractionPhase
from ...domain.entities.extraction import Extraction
from ...domain.entities.extraction_phase import ExtractionPhase
from ...domain.entities.quote import Quote
from ...domain.entities.tag import Tag
from ...domain.value_objects.extraction_mode import ExtractionMode
from ...domain.value_objects.extraction_status import ExtractionStatus
from ..models import ExtractionModel, QuoteModel, TagModel, ExtractionPhaseModel
from ...domain.value_objects.phase_status import PhaseStatus
from ...domain.value_objects.quote_location import QuoteLocation
from ...domain.value_objects.tag_status import TagStatus
from ...domain.value_objects.tag_type import TagType
from ...domain.value_objects.tag_visibility import TagVisibility


class ExtractionPhaseMapper:
    @staticmethod
    def to_domain(model: ExtractionPhaseModel) -> ExtractionPhase | None:
        if not model:
            return None

        return ExtractionPhase(
            id=model.id,
            project_id=model.project_id,
            mode=ExtractionMode(model.mode),
            status=PhaseStatus(model.status),
            start_date=model.start_date,
            end_date=model.end_date,
            auto_close=model.auto_close,
            allow_late_submissions=model.allow_late_submissions,
            min_quotes_required=model.min_quotes_required,
            max_quotes_per_extraction=model.max_quotes_per_extraction,
            requires_approval=model.requires_approval,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    @staticmethod
    def to_db(entity: ExtractionPhase) -> dict:
        """Retorna diccionario para crear/actualizar modelo Django"""
        return {
            'project_id': entity.project_id,
            'mode': entity.mode.value,
            'status': entity.status.value,
            'start_date': entity.start_date,
            'end_date': entity.end_date,
            'auto_close': entity.auto_close,
            'allow_late_submissions': entity.allow_late_submissions,
            'min_quotes_required': entity.min_quotes_required,
            'max_quotes_per_extraction': entity.max_quotes_per_extraction,
            'requires_approval': entity.requires_approval,
        }


class ExtractionMapper:
    @staticmethod
    def to_domain(model: ExtractionModel) -> Extraction:
        if not model:
            return None

        quotes_domain = [QuoteMapper.to_domain(q) for q in model.quotes.all()]

        return Extraction(
            id=model.id,
            study_id=model.study_id,
            assigned_to_user_id=model.assigned_to_id if model.assigned_to else None,
            status=ExtractionStatus(model.status),
            started_at=model.started_at,
            completed_at=model.completed_at,
            quotes=quotes_domain,
            extraction_order=model.extraction_order,
            max_quotes=100
        )

    @staticmethod
    def to_db(entity: Extraction) -> dict:
        """Retorna diccionario para crear/actualizar modelo Django"""
        return {
            'study_id': entity.study_id,
            'assigned_to_id': entity.assigned_to_user_id,
            'status': entity.status.value,
            'started_at': entity.started_at,
            'completed_at': entity.completed_at,
            'extraction_order': entity.extraction_order,
        }


class TagMapper:
    @staticmethod
    def to_domain(model: TagModel) -> Tag:
        return Tag(
            id=model.id,
            name=model.name,
            project_id=model.project_id,
            is_mandatory=model.is_mandatory,
            created_by_user_id=model.created_by_user_id,
            question_id=model.question_id,
            status=TagStatus(model.status),
            visibility=TagVisibility(model.visibility),
            type=TagType(model.type),
        )

    @staticmethod
    def to_db(entity: Tag) -> dict:  # ✅ Retorna dict
        """Retorna diccionario para crear/actualizar modelo Django"""
        return {
            'name': entity.name,
            'project_id': entity.project_id,
            'is_mandatory': entity.is_mandatory,
            'created_by_user_id': entity.created_by_user_id,
            'question_id': entity.question_id,
            'status': entity.status.value,
            'visibility': entity.visibility.value,
            'type': entity.type.value,
        }


class QuoteMapper:
    @staticmethod
    def to_domain(model: QuoteModel) -> Quote:
        tags_domain = [TagMapper.to_domain(t) for t in model.tags.all()]
        location = None
        if model.location_data:
            try:
                location = QuoteLocation.from_dict(model.location_data)
            except (KeyError, ValueError):
                location = None
        return Quote(
            id=model.id,
            extraction_id=model.extraction_id,
            text=model.text_portion,
            researcher_id=model.researcher_id,
            tags=tags_domain,
            location=location,
        )

    @staticmethod
    def to_db(entity: Quote) -> dict:  # ✅ Nuevo método
        """Retorna diccionario para crear/actualizar modelo Django"""
        location_data = None
        if entity.location:
            location_data = entity.location.to_dict()
        return {
            'extraction_id': entity.extraction_id,
            'text_portion': entity.text,
            'location': entity.location,
            'researcher_id': entity.researcher_id,
            'location_data': location_data,
        }