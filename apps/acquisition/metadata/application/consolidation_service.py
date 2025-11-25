"""
ConsolidationService - Servicio de aplicación para consolidación de metadatos.

Este es el punto de entrada principal para el Feature 3.
Orquesta los servicios de dominio en un pipeline coherente:
    Enriquecimiento → Normalización → Validación

Responsabilidades:
- Coordinar el flujo de consolidación
- Manejar errores a nivel de estudio (no falla todo por uno)
- Generar métricas del proceso
- Marcar trazabilidad inicial de campos
"""

from typing import List, Dict, Any
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.metadata.domain.entities.consolidation_result import ConsolidationResult
from apps.acquisition.metadata.domain.services.metadata_enricher import MetadataEnricher
from apps.acquisition.metadata.domain.services.metadata_normalizer import MetadataNormalizer
from apps.acquisition.metadata.domain.services.completeness_validator import CompletenessValidator
from apps.acquisition.metadata.domain.value_objects.consolidation_status import ConsolidationStatus


class ConsolidationService:
    """
    Servicio de Aplicación para la consolidación automática de metadatos.

    Orquesta el flujo completo:
    1. Enriquecimiento: Buscar datos faltantes en fuentes externas
    2. Normalización: Estandarizar formatos (DOI, autores, etc.)
    3. Validación: Determinar estado final (completo/parcial/fallido)

    Principios:
    - Tolerante a fallos: Un estudio que falla no detiene el proceso
    - Idempotente: Puede ejecutarse múltiples veces sin efectos adversos
    - Trazable: Registra el origen de cada dato
    """

    def __init__(self, connectors: Dict[str, Any]):
        """
        Inicializa el servicio con conectores externos.

        Args:
            connectors: Diccionario de conectores por fuente
                       {"Scopus": ScopusConnector, "IEEE Xplore": IeeeConnector}
        """
        self.connectors = connectors

        # Servicios de dominio
        self.enricher = MetadataEnricher(connectors)
        self.normalizer = MetadataNormalizer()
        self.validator = CompletenessValidator()

    def consolidate(self, studies: List[Study]) -> ConsolidationResult:
        """
        Ejecuta el pipeline de consolidación sobre una lista de estudios.

        Args:
            studies: Lista de estudios descubiertos (del Feature 2)

        Returns:
            ConsolidationResult con estudios procesados y métricas

        Note:
            - No modifica la lista original, trabaja sobre los mismos objetos Study
            - Cada estudio se procesa independientemente
            - Los errores en un estudio no afectan a los demás
        """
        if not studies:
            return ConsolidationResult(
                studies=[],
                summary=self._create_empty_summary()
            )

        processed_studies = []
        metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "enriched_fields": 0,
            "normalized_fields": 0,
        }

        for study in studies:
            try:
                processed_study = self._process_single_study(study, metrics)
                processed_studies.append(processed_study)
            except Exception as e:
                # Tolerancia a fallos: marcar como fallido y continuar
                study.consolidation_status = ConsolidationStatus.FALLIDO.value
                study.failure_reason = f"Error en consolidación: {str(e)}"
                processed_studies.append(study)
                metrics["total_processed"] += 1
                metrics["failed"] += 1

        return ConsolidationResult(
            studies=processed_studies,
            summary=metrics
        )

    def _process_single_study(self, study: Study, metrics: Dict[str, int]) -> Study:
        """
        Procesa un único estudio a través del pipeline.

        Args:
            study: Estudio a procesar
            metrics: Diccionario de métricas a actualizar

        Returns:
            Estudio procesado con estado actualizado
        """
        # Marcar campos originales como "discovery" si no tienen origen
        self._mark_discovery_origins(study)

        # Obtener estado inicial
        initial_status = self.validator.validate(study)
        initial_missing = set(self.validator.get_missing_fields(study))

        # 1. ENRIQUECIMIENTO
        # Solo si no está completo
        if initial_status != ConsolidationStatus.COMPLETO:
            self.enricher.enrich(study)

        # Contar campos enriquecidos
        after_enrich_missing = set(self.validator.get_missing_fields(study))
        enriched_count = len(initial_missing - after_enrich_missing)
        metrics["enriched_fields"] += enriched_count

        # 2. NORMALIZACIÓN
        # Siempre se ejecuta para garantizar consistencia
        self.normalizer.normalize(study)

        # 3. VALIDACIÓN FINAL
        final_status = self.validator.validate(study)
        study.consolidation_status = final_status.value

        # Actualizar métricas
        metrics["total_processed"] += 1
        if final_status == ConsolidationStatus.FALLIDO:
            metrics["failed"] += 1
        else:
            metrics["successful"] += 1

        return study

    def _mark_discovery_origins(self, study: Study) -> None:
        """
        Marca los campos existentes como provenientes del descubrimiento.

        Solo marca campos que no tienen origen asignado previamente.
        Esto establece la trazabilidad inicial antes del enriquecimiento.

        Args:
            study: Estudio a marcar
        """
        # Campos que pueden tener trazabilidad
        field_checks = [
            ("title", study.title),
            ("link", study.link),
            ("source", study.source),
            ("doi", study.doi),
            ("authors", study.authors),
            ("abstract", study.abstract),
            ("year", study.year),
            ("journal", study.journal),
            ("keywords", study.keywords),
        ]

        for field_name, field_value in field_checks:
            # Si el campo tiene valor y no tiene origen, marcarlo como discovery
            if field_value and field_name not in study.field_origins:
                study.field_origins[field_name] = "discovery"

    def _create_empty_summary(self) -> Dict[str, Any]:
        """Crea un resumen vacío para cuando no hay estudios."""
        return {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "enriched_fields": 0,
            "normalized_fields": 0,
        }

    def consolidate_single(self, study: Study) -> Study:
        """
        Consolida un único estudio.

        Método de conveniencia para procesar un solo estudio
        sin necesidad de crear una lista.

        Args:
            study: Estudio a consolidar

        Returns:
            Estudio consolidado
        """
        result = self.consolidate([study])
        return result.studies[0] if result.studies else study
