
"""
Services - Core Bounded Context

Servicios de aplicación que orquestan casos de uso relacionados
con la extracción de papers y quotes.
"""
from typing import Dict
import logging
from typing import Tuple

from .models import PaperExtraction, PaperExtractionStatusChoices
from apps.extraction.shared.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)

class PaperExtractionService:
    """
    Servicio de aplicación para gestión de extracciones de papers.
    
    Responsabilidades:
    - Orquestar validaciones de negocio
    - Gestionar transiciones de estado
    - Coordinar operaciones entre múltiples entidades
    """
    
    def validate_completion_rules(self, paper: PaperExtraction) -> Tuple[bool, str]:
        """
        Valida las reglas de negocio para completar un paper.
        """
        logger.debug(
            "Iniciando validación de reglas de completitud",
            extra={
                "paper_id": paper.id,
                "paper_status": paper.status,
            }
        )

        # Regla 1: Al menos una quote
        if not paper.quotes.exists():
            logger.info(
                "Validación fallida: paper sin quotes",
                extra={
                    "paper_id": paper.id,
                    "rule": "at_least_one_quote",
                }
            )
            return False, (
                "El paper debe tener al menos una extracción (quote). "
                "Selecciona texto del PDF y crea quotes antes de finalizar."
            )

        logger.debug(
            "Regla 1 OK: paper tiene al menos una quote",
            extra={"paper_id": paper.id}
        )

        # Regla 2: Cobertura de tags obligatorios
        missing_tags = paper.get_missing_mandatory_tags()
        mandatory_tags = paper.extraction_phase.tags.mandatory()
        logger.info(
            "Estado de tags obligatorios",
            extra={
                "paper_id": paper.id,
                "mandatory_total": mandatory_tags.count(),
                "used_tag_ids": list(
                    paper.quotes.values_list("tags__id", flat=True).distinct()
                ),
            }
        )

        if missing_tags.exists():
            missing_count = missing_tags.count()
            tag_names = ", ".join(tag.name for tag in missing_tags[:3])
            logger.info(
                "Detalle tags obligatorios faltantes",
                extra={
                    "paper_id": paper.id,
                    "missing_tag_ids": list(missing_tags.values_list("id", flat=True)),
                }
            )

            if missing_count > 3:
                tag_names += f" (+{missing_count - 3} más)"

            logger.info(
                "Validación fallida: faltan tags obligatorios",
                extra={
                    "paper_id": paper.id,
                    "rule": "mandatory_tags",
                    "missing_tags_count": missing_count,
                    "missing_tags_preview": tag_names,
                }
            )

            return False, (
                f"Faltan tags obligatorios: {tag_names}. "
                f"Agrega quotes con estos tags antes de finalizar."
            )

        logger.debug(
            "Regla 2 OK: todos los tags obligatorios están cubiertos",
            extra={"paper_id": paper.id}
        )

        # Regla 3: Estado válido
        valid_statuses = [
            PaperExtractionStatusChoices.PENDING,
            PaperExtractionStatusChoices.IN_PROGRESS,
        ]

        if paper.status not in valid_statuses:
            logger.warning(
                "Validación fallida: estado inválido para completar paper",
                extra={
                    "paper_id": paper.id,
                    "rule": "valid_status",
                    "current_status": paper.status,
                }
            )

            return False, (
                f"No se puede completar un paper en estado '{paper.get_status_display()}'. "
                f"Solo papers en progreso pueden ser completados."
            )

        logger.info(
            "Validación de completitud exitosa",
            extra={
                "paper_id": paper.id,
                "final_status": paper.status,
            }
        )

        return True, ""
    
    def attempt_complete_paper(self, paper: PaperExtraction, user) -> PaperExtraction:
        """
        Orquesta el proceso de completar un paper.
        
        Business Rules:
        - Ejecuta todas las validaciones
        - Registra la transición de estado
        - Genera eventos de dominio (futuro)
        
        Args:
            paper: PaperExtraction a completar
            user: Usuario que solicita la completación
            
        Returns:
            PaperExtraction actualizado
            
        Raises:
            BusinessRuleViolation: Si no cumple las reglas de negocio
            
        """
        logger.info(
            f"Attempting to complete paper: "
            f"paper_id={paper.id}, user={user.username}, "
            f"current_status={paper.status}"
        )
        
        # 1. Validar reglas de negocio
        is_valid, error_message = self.validate_completion_rules(paper)
        logger.debug(
            f"Completion validation result: "
            f"paper_id={paper.id}, is_valid={is_valid}, "
            f"error_message={error_message}"
        )
        
        if not is_valid:
            logger.warning(
                f"Paper completion validation failed: "
                f"paper_id={paper.id}, reason={error_message}"
            )
            raise BusinessRuleViolation(error_message)
        
        # 2. Realizar transición de estado
        previous_status = paper.status
        paper.status = PaperExtractionStatusChoices.COMPLETED
        paper.save(update_fields=['status', 'updated_at'])
        
        logger.info(
            f"Paper completed successfully: "
            f"paper_id={paper.id}, "
            f"previous_status={previous_status}, "
            f"new_status={paper.status}, "
            f"quotes_count={paper.quotes.count()}, "
            f"completed_by={user.username}"
        )
        
        # 3. (Futuro) Generar eventos de dominio
        # self._emit_paper_completed_event(paper, user)
        
        return paper
    
    def get_completion_summary(self, paper: PaperExtraction) -> dict:
        """
        Obtiene un resumen del estado de completitud del paper.
        
        Args:
            paper: PaperExtraction a analizar
            
        Returns:
            dict con información de completitud
        """
        logger.info(
            "Building completion summary: paper_id=%s, status=%s",
            paper.id,
            paper.status
        )
        mandatory_tags = paper.extraction_phase.tags.mandatory()
        
        used_mandatory_tags = paper.get_used_mandatory_tags()
        missing_mandatory_tags = paper.get_missing_mandatory_tags()
        
        total_mandatory = mandatory_tags.count()
        covered_mandatory = used_mandatory_tags.count()
        
        coverage_percent = (
            int((covered_mandatory / total_mandatory) * 100)
            if total_mandatory > 0
            else 100
        )
        
        is_valid, validation_message = self.validate_completion_rules(paper)
        logger.info(
            "Completion summary computed: paper_id=%s, can_complete=%s, "
            "coverage=%s/%s, missing=%s",
            paper.id,
            is_valid,
            covered_mandatory,
            total_mandatory,
            missing_mandatory_tags.count()
        )
        
        return {
            'can_complete': is_valid,
            'validation_message': validation_message,
            'quotes_count': paper.quotes.count(),
            'mandatory_tags_total': total_mandatory,
            'mandatory_tags_covered': covered_mandatory,
            'mandatory_tags_missing': missing_mandatory_tags.count(),
            'coverage_percentage': coverage_percent,
            'is_fully_compliant': missing_mandatory_tags.count() == 0,
            'missing_tags': [
                {'id': tag.id, 'name': tag.name}
                for tag in missing_mandatory_tags
            ]
        }
