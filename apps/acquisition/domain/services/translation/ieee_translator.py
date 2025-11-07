"""
Traductor de estrategias para IEEE Xplore.
"""

from typing import List
from apps.acquisition.domain.models import NormalizedStrategy, MainTerm
from .istrategy_translator import IStrategyTranslator
from .translation_result import TranslationResult


class IeeeTranslator(IStrategyTranslator):
    """
    Traductor de estrategias normalizadas a IEEE Xplore.

    Reglas de IEEE Xplore (de Docs-Feature1):
    - SIN field wrapper (no TITLE-ABS-KEY como Scopus)
    - Sinónimos entre comillas unidos con OR
    - Grupos unidos con AND
    - Exclusiones: NOT (...) - IMPORTANTE: no "AND NOT" como Scopus
    - Año: NO en query (se aplica manualmente en UI) → genera warning
    - Operadores en MAYÚSCULAS
    - Paréntesis balanceados

    Precedencia IEEE: NEAR/ONEAR > NOT > AND > OR
    (No implementamos NEAR/ONEAR aún; agrupamos correctamente con paréntesis)

    Validaciones IEEE (de Docs-Feature1):
    - Máx 8 comodines (* / ?)
    - Máx 20-40 términos (varía por tipo de búsqueda)
    - Mínimo 3 caracteres antes de comodín
    """

    def translate(self, strategy: NormalizedStrategy) -> TranslationResult:
        """
        Traduce una estrategia normalizada a IEEE Xplore.

        Proceso:
        1. Agrupar sinónimos con OR
        2. Unir grupos con AND
        3. Aplicar exclusiones (NOT (...))
        4. Generar warning si hay filtro de año (IEEE no lo soporta en query)

        Args:
            strategy: Estrategia normalizada

        Returns:
            TranslationResult con query de IEEE Xplore
        """
        steps_applied = []
        rules_applied = []

        # 1. Construir grupos de sinónimos con OR
        main_groups = self._build_synonym_groups(strategy.main_terms)
        steps_applied.append("group_synonyms")
        rules_applied.append("ieee.boolean_uppercase")

        # 2. Unir grupos con AND
        main_query = self._join_groups_with_and(main_groups)
        steps_applied.append("join_groups_with_and")

        # 3. Aplicar exclusiones (formato IEEE: NOT (...))
        if strategy.exclusions:
            query_with_exclusions = self._apply_exclusions_ieee(
                main_query,
                strategy.exclusions
            )
            steps_applied.append("apply_exclusions_ieee")
            rules_applied.append("ieee.exclusions_not_group")
        else:
            query_with_exclusions = main_query

        # 4. Año fuera de la query → warning + metadata
        warnings = []
        metadata = {}

        if strategy.year_filter:
            year_from = strategy.year_filter.year_from
            year_to = strategy.year_filter.year_to

            # Generar warning para el usuario
            warnings.append(
                f"IEEE Xplore no soporta filtros de año en la query. "
                f"Aplicar manualmente el filtro de año {year_from}-{year_to} "
                f"en la interfaz de IEEE Xplore."
            )

            # Guardar metadata para que la UI pueda usarlo
            metadata["year_filter"] = {
                "from": year_from,
                "to": year_to
            }

            steps_applied.append("separate_year_filter")
            rules_applied.append("ieee.year_filter_outside_query")

        return TranslationResult(
            query=query_with_exclusions,
            warnings=warnings,
            steps_applied=steps_applied,
            rules_applied=rules_applied,
            metadata=metadata
        )

    def _build_synonym_groups(self, main_terms: List[MainTerm]) -> List[str]:
        """
        Construye grupos de sinónimos entre comillas unidos con OR.

        IEEE usa solo comillas dobles (no llaves como Scopus).

        Ejemplo:
            MainTerm(term="machine learning", synonyms=["deep learning", "ML"])
            → '("machine learning" OR "deep learning" OR "ML")'

        Args:
            main_terms: Lista de términos principales con sinónimos

        Returns:
            Lista de strings, cada uno es un grupo con OR
        """
        groups = []

        for main_term in main_terms:
            # Todas las variantes: término principal + sinónimos
            all_variants = [main_term.term] + main_term.synonyms

            # Envolver cada variante en comillas dobles
            quoted_variants = [f'"{variant}"' for variant in all_variants]

            # Unir con OR
            group = f"({' OR '.join(quoted_variants)})"
            groups.append(group)

        return groups

    def _join_groups_with_and(self, groups: List[str]) -> str:
        """
        Une grupos de sinónimos con AND.

        Ejemplo:
            ['("ML" OR "AI")', '("software" OR "code")']
            → '(("ML" OR "AI") AND ("software" OR "code"))'

        Args:
            groups: Lista de grupos ya formateados

        Returns:
            String con grupos unidos por AND, envuelto en paréntesis
        """
        joined = ' AND '.join(groups)
        return f"({joined})"

    def _apply_exclusions_ieee(self, main_query: str, exclusions: List[str]) -> str:
        """
        Aplica exclusiones con NOT (...) - formato IEEE.

        IMPORTANTE: IEEE usa "NOT (...)" NO "AND NOT" como Scopus.

        Ejemplo:
            main_query = '(("ML") AND ("software"))'
            exclusions = ["hardware", "gaming"]
            → '(("ML") AND ("software")) NOT ("hardware" OR "gaming")'

        Args:
            main_query: Query principal ya construida
            exclusions: Lista de términos a excluir

        Returns:
            Query con exclusiones aplicadas en formato IEEE
        """
        # Envolver cada exclusión en comillas y unir con OR
        quoted_exclusions = [f'"{exc}"' for exc in exclusions]
        exclusions_group = f"({' OR '.join(quoted_exclusions)})"

        # IEEE: usa "NOT (...)" sin "AND" antes
        return f"{main_query} NOT {exclusions_group}"
