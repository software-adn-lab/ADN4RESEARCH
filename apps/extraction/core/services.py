
"""
Services - Core Bounded Context

Servicios de aplicación que orquestan casos de uso relacionados
con la extracción de papers y quotes.
"""
from typing import Dict
import logging
from typing import Tuple

from .dtos import CompletionResult
from .models import PaperExtraction, PaperExtractionStatusChoices
from apps.extraction.shared.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)

class PaperLifecycleService:
    """
    Servicio para manejar el ciclo de vida de un paper individual.
    """

    def mark_paper_as_complete(self, extraction_id: int) -> CompletionResult:
        """
        Intenta completar el paper. Retorna un objeto CompletionResult tipado.
        """
        paper = PaperExtraction.objects.get(id=extraction_id)

        missing_tags = paper.get_missing_mandatory_tags()

        if missing_tags.exists():
            return CompletionResult(
                success=False,
                paper=paper,
                errors=[tag.name for tag in missing_tags]
            )
        paper.status = PaperExtractionStatusChoices.COMPLETED
        paper.save()

        return CompletionResult(
            success=True,
            paper=paper
        )

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
        
        Business Rules:
        1. Debe tener al menos una quote extraída
        2. Todas las tags obligatorias deben estar cubiertas
        3. El paper debe estar en estado IN_PROGRESS o PENDING
        
        Args:
            paper: PaperExtraction a validar
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
            
        Referencia DDD:
        - Esta es lógica de dominio pura (invariants)
        - No tiene side effects
        - Retorna información, no modifica estado
        """
        # Regla 1: Al menos una quote
        if not paper.quotes.exists():
            return False, (
                "El paper debe tener al menos una extracción (quote). "
                "Selecciona texto del PDF y crea quotes antes de finalizar."
            )
        
        # Regla 2: Cobertura de tags obligatorios
        missing_tags = paper.get_missing_mandatory_tags()
        
        if missing_tags.exists():
            tag_names = ", ".join([tag.name for tag in missing_tags[:3]])
            
            if missing_tags.count() > 3:
                tag_names += f" (+{missing_tags.count() - 3} más)"
            
            return False, (
                f"Faltan tags obligatorios: {tag_names}. "
                f"Agrega quotes con estos tags antes de finalizar."
            )
        
        # Regla 3: Estado válido
        valid_statuses = [
            PaperExtractionStatusChoices.PENDING,
            PaperExtractionStatusChoices.IN_PROGRESS
        ]
        
        if paper.status not in valid_statuses:
            return False, (
                f"No se puede completar un paper en estado '{paper.get_status_display()}'. "
                f"Solo papers en progreso pueden ser completados."
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
            
        Referencia Django:
        https://docs.djangoproject.com/en/stable/topics/db/transactions/
        """
        logger.info(
            f"Attempting to complete paper: "
            f"paper_id={paper.id}, user={user.username}, "
            f"current_status={paper.status}"
        )
        
        # 1. Validar reglas de negocio
        is_valid, error_message = self.validate_completion_rules(paper)
        
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
        mandatory_tags = paper.extraction_phase.tags.filter(
            status='APPROVED',
            is_mandatory=True
        )
        
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