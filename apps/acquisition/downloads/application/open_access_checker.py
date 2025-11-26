"""
Composite checker to orchestrate Open Access verification from multiple sources.

Estrategia:
- Si el estudio ya viene marcado como OA, respeta ese hint (no llama APIs).
- Primer checker (ej. Unpaywall) decide si es OA y opcionalmente aporta pdf_url.
- Checker secundario (opcional) como respaldo (ej. Crossref u otro).
- Optimización: Si el estudio viene de Scopus, NO consulta Scopus API de nuevo (ahorro de cuota).

Nota: Mantiene compatibilidad con la interfaz IOpenAccessChecker (is_open_access(doi))
pero permite pasar el Study para enriquecerlo si el checker soporta más datos
(p. ej. get_oa_info).
"""
from typing import Optional, Any
import logging

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI

logger = logging.getLogger(__name__)


class CompositeOpenAccessChecker:
    """
    Orquesta múltiples checkers de OA con optimización de cuota:
    1) Respeta el hint existente (study.is_open_access == True)
    2) Primer checker (ej. Unpaywall)
    3) Checker secundario opcional (ej. Crossref)
    4) Checker terciario opcional (ej. Scopus institucional)
       - OPTIMIZACIÓN: Salta el terciario si el estudio ya viene de Scopus
         (para no gastar cuota API consultando dos veces)
    """

    def __init__(
        self,
        primary_checker: Any,
        secondary_checker: Optional[Any] = None,
        tertiary_checker: Optional[Any] = None,
        skip_tertiary_for_sources: Optional[list] = None,
    ):
        """
        Args:
            primary_checker: Checker principal (ej. Unpaywall)
            secondary_checker: Checker secundario (ej. Crossref)
            tertiary_checker: Checker terciario (ej. Scopus Institucional)
            skip_tertiary_for_sources: Lista de fuentes para las cuales NO consultar terciario
                                       (ej. ['Scopus'] para no re-consultar Scopus API)
        """
        self.primary_checker = primary_checker
        self.secondary_checker = secondary_checker
        self.tertiary_checker = tertiary_checker
        self.skip_tertiary_for_sources = skip_tertiary_for_sources or []

        self.checkers = tuple(
            checker for checker in (primary_checker, secondary_checker, tertiary_checker) if checker
        )

    def is_open_access(self, doi: DOI, study: Optional[Study] = None) -> bool:
        """
        Determinar si un DOI es OA usando la cascada definida.

        OPTIMIZACIÓN: Si el estudio viene de Scopus, NO consulta el tertiary_checker
        (ScopusInstitutionalChecker) para evitar gastar cuota API dos veces.

        Args:
            doi: DOI a consultar
            study: opcional, se enriquece si el checker provee info extra

        Returns:
            True si es Open Access, False en caso contrario
        """
        if study and study.is_open_access is True:
            return True

        if not doi or not doi.value:
            return False

        for i, checker in enumerate(self.checkers):
            if not checker:
                continue

            is_tertiary = (i == 2 and checker is self.tertiary_checker)
            if is_tertiary and study and study.source.name in self.skip_tertiary_for_sources:
                logger.info(
                    f"⚡ Saltando checker terciario para estudio de {study.source.name} "
                    f"(ya consultado en Discovery)"
                )
                continue

            try:
                result = checker.is_open_access(doi)
            except TypeError:
                # Checker espera también study (firma extendida)
                result = checker.is_open_access(doi, study)  # type: ignore[arg-type]

            # Enriquecer con info detallada si existe get_oa_info
            if hasattr(checker, "get_oa_info"):
                try:
                    info = checker.get_oa_info(doi)
                    if isinstance(info, dict):
                        if study and info.get("is_oa") is not None:
                            study.is_open_access = bool(info.get("is_oa"))
                        if study and info.get("pdf_url"):
                            study.pdf_url = info.get("pdf_url")
                except Exception:
                    # Silencioso: no debe romper el flujo si get_oa_info falla
                    pass

            if result:
                if study:
                    study.is_open_access = True
                return True

        return False
