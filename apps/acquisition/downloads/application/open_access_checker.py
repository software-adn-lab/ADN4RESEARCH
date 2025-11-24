"""
Composite checker to orchestrate Open Access verification from multiple sources.

Estrategia:
- Si el estudio ya viene marcado como OA, respeta ese hint (no llama APIs).
- Primer checker (ej. Unpaywall) decide si es OA y opcionalmente aporta pdf_url.
- Checker secundario (opcional) como respaldo (ej. Crossref u otro).

Nota: Mantiene compatibilidad con la interfaz IOpenAccessChecker (is_open_access(doi))
pero permite pasar el Study para enriquecerlo si el checker soporta más datos
(p. ej. get_oa_info).
"""
from typing import Optional, Any

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI


class CompositeOpenAccessChecker:
    """
    Orquesta múltiples checkers de OA:
    1) Respeta el hint existente (study.is_open_access == True)
    2) Primer checker (ej. Unpaywall)
    3) Checker secundario opcional (ej. Crossref)
    4) Checker terciario opcional (ej. Scopus institucional)
    """

    def __init__(
        self,
        primary_checker: Any,
        secondary_checker: Optional[Any] = None,
        tertiary_checker: Optional[Any] = None,
    ):
        self.checkers = tuple(
            checker for checker in (primary_checker, secondary_checker, tertiary_checker) if checker
        )

    def is_open_access(self, doi: DOI, study: Optional[Study] = None) -> bool:
        """
        Determinar si un DOI es OA usando la cascada definida.

        Args:
            doi: DOI a consultar
            study: opcional, se enriquece si el checker provee info extra
        """
        if study and study.is_open_access is True:
            return True

        if not doi or not doi.value:
            return False

        # Orden: primary -> secondary -> tertiary
        for checker in self.checkers:
            if not checker:
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
