from typing import List, Dict, Any
from django.utils import timezone
from django.db import transaction
import logging

from apps.extraction.external.services import AcquisitionService
from apps.extraction.shared.exceptions import BusinessRuleViolation, ResourceNotFound
from apps.extraction.taxonomy.services import TagService
from apps.extraction.taxonomy.repositories import TagRepository
from .repositories import ExtractionRepository
from .models import ExtractionStatus, PaperExtraction, Quote, Comment
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)
class ExtractionService:
    def __init__(self):
        self.extraction_repo = ExtractionRepository()
        self.tag_service = TagService()
        self.tag_repo = TagRepository()

    def initialize_extraction(self, study_id: int) -> Dict[str, Any]:
        """
        Crea un registro de extracción para un paper existente.
        """
        study_data = AcquisitionService.get_study_details(study_id)
        if not study_data:
            raise ResourceNotFound(f"Study {study_id} no encontrado en Acquisition.")

        existing = self.extraction_repo.get_by_study_id(study_id)
        if existing:
            return self._serialize(existing, study_data)

        extraction = self.extraction_repo.create_extraction(
            study_id=study_id,
            project_id=study_data['project_id']
        )

        return self._serialize(extraction, study_data)

    def get_extraction_by_study(self, study_id: int) -> PaperExtraction:
        """Obtiene la extracción por study_id"""
        extraction = self.extraction_repo.get_by_study_id(study_id)
        if not extraction:
            raise ResourceNotFound(f"No existe extracción para el study {study_id}")
        return extraction

    def get_extraction_progress(self, extraction_id: int) -> Dict[str, Any]:
        """
        Calcula qué falta para completar la extracción.
        """
        extraction = self.extraction_repo.get_by_id(extraction_id)
        if not extraction:
            raise ResourceNotFound("Extraction not found")

        mandatory_tags_objs = self.tag_service.repository.get_mandatory_tags(extraction.project_id)
        mandatory_map = {t.id: t.name for t in mandatory_tags_objs}
        mandatory_ids = set(mandatory_map.keys())

        used_tag_ids = set(
            extraction.quotes.values_list('tags__id', flat=True)
        )
        used_tag_ids.discard(None)  # Remover None si no hay tags

        missing_ids = mandatory_ids - used_tag_ids
        missing_names = [mandatory_map[mid] for mid in missing_ids]

        status_label = "Completo" if extraction.status == ExtractionStatus.DONE else "Pendiente"
        is_ready_to_complete = len(missing_ids) == 0 and extraction.quotes.exists()

        return {
            "status": status_label,
            "is_ready_to_complete": is_ready_to_complete,
            "mandatory_tags_count": len(mandatory_ids),
            "extracted_tags_count": len(used_tag_ids & mandatory_ids),
            "missing_tags": missing_names
        }

    @transaction.atomic
    def create_quote(self, extraction_id: int, researcher_id: int,
                     text_portion: str, location: str = "",
                     tag_names: List[str] = None,
                     new_inductive_tag: str = None) -> Quote:
        """
        Crea una quote en una extracción.
        
        Args:
            extraction_id: ID de la extracción
            researcher_id: ID del researcher que crea la quote
            text_portion: Texto de la cita
            location: Ubicación en el documento (opcional)
            tag_names: Lista de nombres de tags existentes
            new_inductive_tag: Nombre de un nuevo tag inductivo a crear
        """
        extraction = self.extraction_repo.get_by_id(extraction_id)
        if not extraction:
            raise ResourceNotFound("Extraction not found")

        # Verificar que el researcher tiene permisos (está asignado)
        if extraction.assigned_to_id and extraction.assigned_to_id != researcher_id:
            raise BusinessRuleViolation("No tiene permisos para este paper")

        # Crear la quote
        quote = Quote.objects.create(
            paper_extraction=extraction,
            text_portion=text_portion,
            location=location,
            researcher_id=researcher_id
        )

        # Asociar tags existentes
        if tag_names:
            # Buscar tags disponibles para el usuario (públicos + privados propios)
            user_tags = self.tag_repo.get_tags_for_user(extraction.project_id, researcher_id)
            user_tag_map = {t.name: t for t in user_tags}
            
            for tag_name in tag_names:
                if tag_name in user_tag_map:
                    quote.tags.add(user_tag_map[tag_name])

        # Crear tag inductivo si se especificó
        if new_inductive_tag:
            new_tag = self.tag_service.create_inductive_tag(
                project_id=extraction.project_id,
                name=new_inductive_tag,
                user_id=researcher_id
            )
            quote.tags.add(new_tag)

        # Actualizar estado de la extracción a En Progreso si estaba Pendiente
        if extraction.status == ExtractionStatus.PENDING:
            extraction.status = ExtractionStatus.IN_PROGRESS
            self.extraction_repo.save(extraction)

        return quote

    def add_comment_to_quote(self, quote_id: int, user_id: int, text: str) -> Comment:
        """Agrega un comentario a una quote"""
        try:
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            raise ResourceNotFound("Quote not found")

        content_type = ContentType.objects.get_for_model(Quote)
        
        comment = Comment.objects.create(
            user_id=user_id,
            text=text,
            content_type=content_type,
            object_id=quote_id
        )

        return comment

    def get_quote_comments(self, quote_id: int) -> List[Dict[str, Any]]:
        """Obtiene los comentarios de una quote"""
        try:
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            raise ResourceNotFound("Quote not found")

        content_type = ContentType.objects.get_for_model(Quote)
        comments = Comment.objects.filter(
            content_type=content_type,
            object_id=quote_id
        ).order_by('created_at')

        return [{
            "id": c.id,
            "text": c.text,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat()
        } for c in comments]

    def get_quotes_by_extraction(self, extraction_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las quotes de una extracción"""
        extraction = self.extraction_repo.get_by_id(extraction_id)
        if not extraction:
            raise ResourceNotFound("Extraction not found")

        quotes = extraction.quotes.prefetch_related('tags').all()
        
        return [{
            "id": q.id,
            "text_portion": q.text_portion,
            "location": q.location,
            "tags": [{"id": t.id, "name": t.name} for t in q.tags.all()],
            "researcher_id": q.researcher_id,
            "validated": q.validated,
            "created_at": q.created_at.isoformat()
        } for q in quotes]

    def complete_extraction(self, extraction_id: int, user_id: int) -> PaperExtraction:
        """
        Intenta marcar una extracción como completada.
        """
        extraction = self.extraction_repo.get_by_id(extraction_id)
        if not extraction:
            raise ResourceNotFound("Extraction not found")

        progress = self.get_extraction_progress(extraction_id)

        if progress['missing_tags']:
            raise BusinessRuleViolation(
                f"No se puede completar. Faltan los siguientes tags obligatorios: {', '.join(progress['missing_tags'])}"
            )

        if not extraction.quotes.exists():
            raise BusinessRuleViolation("Debe extraer al menos una cita (Quote).")

        extraction.status = ExtractionStatus.DONE
        extraction.completed_at = timezone.now()

        return self.extraction_repo.save(extraction)

    def get_researcher_papers(self, project_id: int, researcher_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene los papers asignados a un researcher con su estado de extracción.
        """
        from apps.extraction.planning.repositories import PaperAssignmentRepository, ExtractionPhaseRepository

        # Asumimos que AcquisitionService es accesible globalmente o importado en el módulo

        phase_repo = ExtractionPhaseRepository()
        assignment_repo = PaperAssignmentRepository()

        # 1. Obtener Fase
        try:
            phase = phase_repo.get_by_project(project_id)
        except Exception:
            return []

        if not phase:
            return []

        # 2. Obtener Asignaciones
        try:
            assignments = assignment_repo.list_by_researcher(researcher_id, phase.id)
        except Exception:
            return []

        result = []

        # 3. Procesar cada asignación
        for assignment in assignments:
            try:
                extraction = self.extraction_repo.get_by_study_id(assignment.study_id)
                study_data = AcquisitionService.get_study_details(assignment.study_id)

                # --- DEFINICIÓN DE DATOS VISUALES Y DE ASIGNACIÓN ---

                pdf_url_data = study_data.get('pdf_url', f'/static/pdfs/paper_{assignment.study_id}.pdf')
                title_data = study_data.get('title', f'Paper #{assignment.study_id}: Título desconocido')
                authors_data = study_data.get('authors', 'Autor et al.')
                researcher_name_data = f"Researcher #{researcher_id}"

                if extraction:
                    progress = self.get_extraction_progress(extraction.id)
                    status_value = extraction.status.value if hasattr(extraction.status, 'value') else extraction.status
                else:
                    progress = None
                    status_value = "Pending"

                # --- CONSTRUCCIÓN DEL OUTPUT ---

                result.append({
                    "study_id": assignment.study_id,
                    "id": assignment.study_id,  # REPLICAMOS CLAVE ID

                    "extraction_id": extraction.id if extraction else None,
                    "status": status_value,
                    "progress": progress,

                    "title": title_data,
                    "authors": authors_data,
                    "pdf_url": pdf_url_data,
                    "researcher_id": researcher_id,
                    "researcher_name": researcher_name_data,

                    "assigned_at": assignment.assigned_at.isoformat()
                })

            except Exception:
                # Si falla un paper, lo omitimos (continue)
                continue

        return result

    def get_all_papers(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los papers (extractions) asociados a un proyecto,
        independientemente de la asignación o estado, para visualización de Owner.
        """
        try:
            from apps.extraction.core.models import PaperExtraction

            # 1. Obtener todas las extracciones para el proyecto
            extractions = PaperExtraction.objects.filter(project_id=project_id)

        except Exception:
            return []

        result = []

        # 2. Procesar cada extracción para obtener datos externos (Título, PDF, Progreso)
        for ext in extractions:
            try:
                study_data = AcquisitionService.get_study_details(ext.study_id)

                # Obtener progreso
                progress = self.get_extraction_progress(ext.id) if ext.id else None

                # Asumimos que el researcher_id está en ext.researcher_id o es None
                researcher_id = ext.researcher_id if hasattr(ext, 'researcher_id') else None

                # Datos visuales (Mock/real si AcquisitionService lo proporciona)
                pdf_url_data = study_data.get('pdf_url', f'/static/pdfs/paper_{ext.study_id}.pdf')
                title_data = study_data.get('title', f'Paper #{ext.study_id}: Título desconocido')
                authors_data = study_data.get('authors', 'Autor et al.')

                result.append({
                    "study_id": ext.study_id,
                    "extraction_id": ext.id,

                    "title": title_data,
                    "authors": authors_data,
                    "pdf_url": pdf_url_data,

                    "status": ext.status.value if hasattr(ext.status, 'value') else ext.status,
                    "progress": progress,

                    "researcher_id": researcher_id,
                    "researcher_name": f"Researcher #{researcher_id}" if researcher_id else "Sin asignar",
                })

            except Exception:
                # Si falla un paper, lo omitimos
                continue

        return result


    def _serialize(self, extraction, study_data=None):
        if not study_data:
            study_data = AcquisitionService.get_study_details(extraction.study_id) or {}

        return {
            "id": extraction.id,
            "status": extraction.status,
            "study_title": study_data.get('title', 'Unknown'),
            "study_authors": study_data.get('authors', 'Unknown'),
            "quote_count": extraction.quotes.count()
        }
