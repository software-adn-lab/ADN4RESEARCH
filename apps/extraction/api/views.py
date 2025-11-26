# apps/extraction/api/views.py
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action

from ..application.commands.activate_extraction_phase import ActivateExtractionPhaseCommand
from ..application.commands.configure_extraction_phase import ConfigureExtractionPhaseCommand
from ..container import container
from ..application.commands.create_extraction import CreateExtractionCommand
from ..application.commands.complete_extraction import CompleteExtractionCommand
from ..application.commands.create_quote import CreateQuoteCommand
from ..application.commands.create_tag import CreateTagCommand
from ..application.commands.moderate_tag import ModerateTagCommand
from ..application.commands.merge_tags import MergeTagsCommand
from ..application.queries.get_extraction import GetExtractionQuery
from ..application.queries.list_extractions import ListExtractionsQuery

from . import serializers as dtos
from ..domain.exceptions.extraction_exceptions import (  # ✅
    ExtractionException,
    ExtractionValidationError,
    ExtractionNotFound,
    UnauthorizedExtractionAccess,
    InvalidExtractionState,
    StudyNotFound,
    TagNotFound,
    ProjectAccessDenied,
)
from ..infrastructure.models import ExtractionModel
from apps.extraction.infrastructure.adapters.acquisition_service_adapter import (
    AcquisitionServiceAdapter)


class ExceptionHandlerMixin:
    """Mixin para estandarizar respuestas de error en todos los ViewSets"""

    def _handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, ExtractionNotFound):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, UnauthorizedExtractionAccess):
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, (StudyNotFound, TagNotFound)):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, (ExtractionValidationError, InvalidExtractionState)):
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif isinstance(exc, ExtractionException):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error inesperado en {self.__class__.__name__}")
            return Response(
                {"error": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ExtractionPhaseViewSet(ExceptionHandlerMixin, viewsets.ViewSet):
    """Gestión de la fase de extracción"""

    def retrieve(self, request, pk=None):
        """Obtener configuración de fase por project_id"""
        try:
            phase = container.phase_repository.get_by_project_id(int(pk))
            if not phase:
                return Response(
                    {"error": "Fase de extracción no configurada"},
                    status=status.HTTP_404_NOT_FOUND
                )

            data = {
                "id": phase.id,
                "project_id": phase.project_id,
                "mode": phase.mode.value,
                "status": phase.status.value,
                "start_date": phase.start_date,
                "end_date": phase.end_date,
                "auto_close": phase.auto_close,
                "allow_late_submissions": phase.allow_late_submissions,
                "min_quotes_required": phase.min_quotes_required,
                "max_quotes_per_extraction": phase.max_quotes_per_extraction,
                "requires_approval": phase.requires_approval,
                "is_open_for_extraction": phase.is_open_for_extraction(),
                "expected_extractions_per_study": phase.expected_extractions_per_study,
            }

            serializer = dtos.ExtractionPhaseResponseSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self._handle_exception(e)

    def create(self, request):
        """Configurar fase de extracción"""
        serializer = dtos.ConfigureExtractionPhaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        project_id = int(request.query_params.get('project_id'))

        command = ConfigureExtractionPhaseCommand(
            project_id=project_id,
            user_id=request.user.id,
            mode=data['mode'],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            auto_close=data['auto_close'],
            allow_late_submissions=data['allow_late_submissions'],
            min_quotes_required=data['min_quotes_required'],
            max_quotes_per_extraction=data['max_quotes_per_extraction'],
            requires_approval=data['requires_approval']
        )

        try:
            phase = container.configure_extraction_phase_handler.handle(command)

            response_data = {
                "id": phase.id,
                "project_id": phase.project_id,
                "mode": phase.mode.value,
                "status": phase.status.value,
                "message": "Fase configurada exitosamente"
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except ExtractionException as e:
            return self._handle_exception(e)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activar fase de extracción"""
        command = ActivateExtractionPhaseCommand(
            project_id=int(pk),
            user_id=request.user.id
        )

        try:
            container.activate_extraction_phase_handler.handle(command)
            return Response(
                {"status": "activated", "message": "Fase activada"},
                status=status.HTTP_200_OK
            )
        except ExtractionException as e:
            return self._handle_exception(e)


class ExtractionViewSet(ExceptionHandlerMixin, viewsets.ViewSet):
    """Maneja el Aggregate Root: Extraction"""

    def create(self, request):
        serializer = dtos.CreateExtractionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        command = CreateExtractionCommand(
            study_id=serializer.validated_data['study_id'],
            user_id=request.user.id
        )

        try:
            extraction = container.create_extraction_handler.handle(command)
            response_data = {
                "id": extraction.id,
                "study_id": extraction.study_id,
                "status": extraction.status.value,
                "assigned_to_user_id": extraction.assigned_to_user_id,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except ExtractionException as e:
            return self._handle_exception(e)


    def retrieve(self, request, pk=None):
        query = GetExtractionQuery(extraction_id=int(pk))
        try:
            extraction = container.get_extraction_handler.handle(query)

            if extraction.assigned_to_user_id != request.user.id:
                project_id = container.acquisition_adapter.get_project_context(
                    extraction.study_id
                )
                if project_id:
                    project = container.project_adapter.get_project_by_id(project_id)
                    if not project or project.owner_id != request.user.id:
                        raise UnauthorizedExtractionAccess(
                            "No tienes permiso para ver esta extracción"
                        )
                else:
                    raise UnauthorizedExtractionAccess(
                        "No tienes permiso para ver esta extracción"
                    )

            data = {
                "id": extraction.id,
                "study_id": extraction.study_id,
                "assigned_to_user_id": extraction.assigned_to_user_id,
                "status": extraction.status.value,
                "started_at": extraction.started_at,
                "completed_at": extraction.completed_at,
                "is_active": extraction.is_active,
                "quotes": [
                    {
                        "id": q.id,
                        "text": q.text,
                        "location": q.location,
                        "researcher_id": q.researcher_id,
                        "tags": [
                            {
                                "id": t.id,
                                "name": t.name,
                                "project_id": t.project_id,
                                "is_mandatory": t.is_mandatory,
                                "status": t.status.value,
                                "visibility": t.visibility.value,
                                "type": t.type.value,
                                "created_by_user_id": t.created_by_user_id,
                                "question_id": t.question_id,
                            }
                            for t in q.tags
                        ]
                    }
                    for q in extraction.quotes
                ]
            }
            serializer = dtos.ExtractionDetailSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ExtractionException as e:
            return self._handle_exception(e)


    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        command = CompleteExtractionCommand(
            extraction_id=int(pk),
            user_id=request.user.id
        )

        try:
            container.complete_extraction_handler.handle(command)
            return Response(
                {"status": "completed", "message": "Extracción completada exitosamente"},
                status=status.HTTP_200_OK
            )
        except ExtractionException as e:
            return self._handle_exception(e)


    def list(self, request):
        query = ListExtractionsQuery(
            user_id=request.user.id,
            include_quotes=False
        )
        extractions = container.list_extractions_handler.handle(query)

        data = [
            {
                "id": e.id,
                "study_id": e.study_id,
                "status": e.status.value,
                "started_at": e.started_at,
                "completed_at": e.completed_at,
                "quotes_count": len(e.quotes),
            }
            for e in extractions
        ]
        serializer = dtos.ExtractionListSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuoteViewSet(ExceptionHandlerMixin, viewsets.ViewSet):
    """Maneja la entidad secundaria: Quote"""

    def _handle_exception(self, exc: Exception) -> Response:
        """Reutiliza la misma lógica"""
        if isinstance(exc, ExtractionNotFound):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, UnauthorizedExtractionAccess):
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, (TagNotFound, InvalidExtractionState, ExtractionValidationError)):
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif isinstance(exc, ExtractionException):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error inesperado en QuoteViewSet")
            return Response(
                {"error": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        serializer = dtos.CreateQuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        location_data = data.get('location', {})

        command = CreateQuoteCommand(
            extraction_id=data['extraction_id'],
            text=data['text'],
            user_id=request.user.id,
            tag_ids=data['tag_ids'],
            page=location_data['page'],
            text_location=location_data.get('text_location', ''),
            x1=location_data.get('x1'),
            y1=location_data.get('y1'),
            x2=location_data.get('x2'),
            y2=location_data.get('y2')
        )

        try:
            quote = container.create_quote_handler.handle(command)

            response_data = {
                "id": quote.id,
                "text": quote.text,
                "location": quote.location.to_dict() if quote.location else None,
                "researcher_id": quote.researcher_id,
                "tags": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "color": t.color,
                        "project_id": t.project_id,
                        "is_mandatory": t.is_mandatory,
                        "status": t.status.value,
                        "visibility": t.visibility.value,
                        "type": t.type.value,
                        "created_by_user_id": t.created_by_user_id,
                        "question_id": t.question_id,
                    }
                    for t in quote.tags
                ]
            }
            response_serializer = dtos.QuoteResponseSerializer(response_data)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ExtractionException as e:
            return self._handle_exception(e)

    @action(detail=False, methods=['get'], url_path='extraction/(?P<extraction_id>[^/.]+)')
    def by_extraction(self, request, extraction_id=None):
        """
        Obtiene todos los quotes de una extracción con ubicaciones.

        GET /api/extraction/quotes/extraction/123/
        """
        from ..application.queries.get_extraction_quotes_with_locations import (
            GetExtractionQuotesWithLocationsQuery
        )

        query = GetExtractionQuotesWithLocationsQuery(
            extraction_id=int(extraction_id)
        )

        try:
            result = container.get_extraction_quotes_handler.handle(query)
            return Response(result, status=status.HTTP_200_OK)
        except ExtractionException as e:
            return self._handle_exception(e)


class TagViewSet(ExceptionHandlerMixin, viewsets.ViewSet):
    """Maneja la entidad: Tag (Propuesta y Moderación)"""

    def _handle_exception(self, exc: Exception) -> Response:
        """Reutiliza la misma lógica"""
        if isinstance(exc, ExtractionNotFound):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, UnauthorizedExtractionAccess):
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, (TagNotFound, InvalidExtractionState, ExtractionValidationError)):
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif isinstance(exc, ExtractionException):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error inesperado en QuoteViewSet")
            return Response(
                {"error": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        serializer = dtos.CreateTagInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        command = CreateTagCommand(
            name=data['name'],
            user_id=request.user.id,
            project_id=data['project_id'],
            is_inductive=data['is_inductive'],
            question_id=data.get('question_id')
        )

        try:
            tag = container.create_tag_handler.handle(command)

            response_data = {
                "id": tag.id,
                "name": tag.name,
                "project_id": tag.project_id,
                "is_mandatory": tag.is_mandatory,
                "status": tag.status.value,
                "visibility": tag.visibility.value,
                "type": tag.type.value,
                "created_by_user_id": tag.created_by_user_id,
                "question_id": tag.question_id,
            }
            response_serializer = dtos.TagResponseSerializer(response_data)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ExtractionException as e:
            return self._handle_exception(e)

    @action(detail=True, methods=['post'])
    def moderate(self, request, pk=None):
        """Aprobar o Rechazar Tag"""
        serializer = dtos.ModerateTagInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        command = ModerateTagCommand(
            tag_id=int(pk),
            action=serializer.validated_data['action'],
            owner_id=request.user.id
        )

        try:
            container.moderate_tag_handler.handle(command)
            return Response({"status": "Moderated"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return self._handle_exception(e)
        except ExtractionValidationError as e:
            return self._handle_exception(e)

    @action(detail=False, methods=['post'], url_path='merge')
    def merge(self, request):
        """Fusionar tags"""
        serializer = dtos.MergeTagInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        command = MergeTagsCommand(
            target_tag_id=serializer.validated_data['target_tag_id'],
            source_tag_id=serializer.validated_data['source_tag_id'],
            user_id=request.user.id
        )

        try:
            container.merge_tags_handler.handle(command)
            return Response({"status": "Merged"}, status=status.HTTP_200_OK)
        except ExtractionException as e:
            return self._handle_exception(e)


def pdf_viewer(request, extraction_id):
    """Vista para el visor de PDF con extracción de quotes"""
    try:
        query = GetExtractionQuery(extraction_id=int(extraction_id))
        extraction = container.get_extraction_handler.handle(query)

        study_details = container.acquisition_adapter.get_study_details(extraction.study_id)
        project_id = container.acquisition_adapter.get_project_context(extraction.study_id)

        pdf_url = study_details.get('file_url') if study_details else None

        context = {
            'extraction': extraction,
            'project_id': project_id,
            'pdf_url': pdf_url,
        }

        return render(request, 'extraction/pdf_viewer.html', context)

    except ExtractionNotFound:
        return render(request, '404.html', status=404)
    except Exception:
        return render(request, '500.html', status=500)