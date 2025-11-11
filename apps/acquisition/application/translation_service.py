"""
Servicios de aplicación para traducción de estrategias de búsqueda.

Este módulo contiene los casos de uso (Application Services) que orquestan
la traducción de estrategias normalizadas a diferentes bases de datos académicas.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from apps.acquisition.domain.models import NormalizedStrategy
from apps.acquisition.domain.services.translation import ScopusTranslator, IeeeTranslator
from apps.acquisition.domain.constants import SUPPORTED_SOURCES
from .exceptions import InvalidTargetError


class TranslationService:
    """
    Servicio de aplicación para traducción de estrategias de búsqueda.

    Responsabilidades:
    1. Validar el target de traducción
    2. Seleccionar el traductor apropiado (ScopusTranslator, IeeeTranslator)
    3. Orquestar la traducción
    4. Armar la respuesta con trace completo
    5. Gestionar warnings según capacidades del target

    Arquitectura futura:
        TranslationService (Application Layer)
            ↓
        ScopusTranslator / IeeeTranslator (Domain Services)
            ↓
        QueryBuilder + OperatorPolicy + FieldPolicy (Domain)
    """

    def translate(
        self,
        strategy: NormalizedStrategy,
        target: str
    ) -> Dict[str, Any]:
        """
        Traduce una estrategia normalizada al dialecto del target especificado.

        Args:
            strategy: Estrategia normalizada e inmutable
            target: Base de datos destino ("Scopus" o "IEEE Xplore")

        Returns:
            Diccionario con el siguiente contrato:
            {
                "query": str,               # Query traducida
                "status": str,              # "Done" en caso exitoso
                "warnings": List[str],      # Advertencias (puede estar vacía)
                "trace": {
                    "trace_id": str,        # ID único de esta traducción
                    "target": str,          # Target de destino
                    "steps_applied": List[str],  # Pasos ejecutados
                    "rules_applied": List[str],  # Reglas aplicadas
                    "timestamp": str        # ISO-8601
                },
                "target": str,              # Mismo target de entrada
                "metadata": Dict[str, Any]  # Info adicional (ej: year_filter)
            }

        Raises:
            InvalidTargetError: Si el target no es soportado
            DomainValidationError: Si la estrategia es inválida (no debería pasar)

        Ejemplo:
            >>> service = TranslationService()
            >>> result = service.translate(strategy, "Scopus")
            >>> print(result["query"])
            'TITLE-ABS-KEY(...) AND PUBYEAR > 2019'
        """
        # 1. Validar precondiciones
        self._validate_target(target)

        # 2. Seleccionar traductor según target
        if target == "Scopus":
            translator = ScopusTranslator()
        elif target == "IEEE Xplore":
            translator = IeeeTranslator()
        else:
            # No debería llegar aquí (la validación ya filtró)
            raise InvalidTargetError(target, SUPPORTED_SOURCES)

        # 3. Ejecutar traducción
        translation_result = translator.translate(strategy)

        # 4. Armar trace
        trace = self._build_trace(
            target=target,
            steps=translation_result.steps_applied,
            rules=translation_result.rules_applied
        )

        # 5. Armar respuesta final
        return {
            "query": translation_result.query,
            "status": "Done",
            "warnings": translation_result.warnings,
            "trace": trace,
            "target": target,
            "metadata": translation_result.metadata
        }

    def _validate_target(self, target: str) -> None:
        """
        Valida que el target sea soportado.

        Args:
            target: Target a validar

        Raises:
            InvalidTargetError: Si el target no está en SUPPORTED_SOURCES
        """
        if target not in SUPPORTED_SOURCES:
            raise InvalidTargetError(target, SUPPORTED_SOURCES)

    def _build_trace(
        self,
        target: str,
        steps: list[str],
        rules: list[str]
    ) -> Dict[str, Any]:
        """
        Construye el objeto trace con trace_id, timestamp, etc.

        Args:
            target: Target de la traducción
            steps: Pasos aplicados por el traductor
            rules: Reglas aplicadas por el traductor

        Returns:
            Dict con estructura de trace
        """
        return {
            "trace_id": str(uuid.uuid4()),
            "target": target,
            "steps_applied": steps,
            "rules_applied": rules,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
