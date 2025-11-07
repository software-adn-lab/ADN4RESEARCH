"""
Traductor de estrategias para Scopus.
"""

from typing import List
from apps.acquisition.domain.models import NormalizedStrategy, MainTerm
from .istrategy_translator import IStrategyTranslator
from .translation_result import TranslationResult


class ScopusTranslator(IStrategyTranslator):
    """
    Traductor de estrategias normalizadas a Scopus.

    Reglas de Scopus (de Docs-Feature1):
    - Field wrapper: TITLE-ABS-KEY(...)
    - Sinónimos entre comillas unidos con OR
    - Grupos unidos con AND
    - Exclusiones: AND NOT (...)
    - Año: PUBYEAR > (from-1) AND PUBYEAR < (to+1)
    - Operadores en MAYÚSCULAS
    - Paréntesis balanceados

    Precedencia Scopus (actual): OR > W/PRE > AND > AND NOT
    """

    def translate(self, strategy: NormalizedStrategy) -> TranslationResult:
        """
        Traduce una estrategia normalizada a Scopus.

        Proceso:
        1. Agrupar sinónimos con OR
        2. Unir grupos con AND
        3. Aplicar exclusiones (AND NOT)
        4. Envolver en TITLE-ABS-KEY
        5. Agregar filtro de año (si existe)

        Args:
            strategy: Estrategia normalizada

        Returns:
            TranslationResult con query de Scopus
        """
        steps_applied = []
        rules_applied = []

        # 1. Construir grupos de sinónimos con OR
        main_groups = self._build_synonym_groups(strategy.main_terms)
        steps_applied.append("group_synonyms")
        rules_applied.append("scopus.boolean_uppercase")

        # 2. Unir grupos con AND
        main_query = self._join_groups_with_and(main_groups)
        steps_applied.append("join_groups_with_and")

        # 3. Aplicar exclusiones
        if strategy.exclusions:
            query_with_exclusions = self._apply_exclusions(main_query, strategy.exclusions)
            steps_applied.append("apply_exclusions")
            rules_applied.append("scopus.exclusions_and_not")
        else:
            query_with_exclusions = main_query

        # 4. Envolver en TITLE-ABS-KEY
        wrapped_query = f"TITLE-ABS-KEY({query_with_exclusions})"
        steps_applied.append("wrap_scopus_field")
        rules_applied.append("scopus.field_title_abs_key")

        # 5. Agregar filtro de año
        if strategy.year_filter:
            final_query = self._apply_year_filter(wrapped_query, strategy.year_filter.year_from, strategy.year_filter.year_to)
            steps_applied.append("apply_year_filter")
            rules_applied.append("scopus.year_pubyear_range")
        else:
            final_query = wrapped_query

        # Metadata
        metadata = {}
        if strategy.year_filter:
            metadata["year_filter"] = {
                "from": strategy.year_filter.year_from,
                "to": strategy.year_filter.year_to
            }

        return TranslationResult(
            query=final_query,
            warnings=[],  # Scopus no genera warnings (tiene año en query)
            steps_applied=steps_applied,
            rules_applied=rules_applied,
            metadata=metadata
        )

    def _build_synonym_groups(self, main_terms: List[MainTerm]) -> List[str]:
        """
        Construye grupos de sinónimos entre comillas unidos con OR.

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

            # Envolver cada variante en comillas
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

    def _apply_exclusions(self, main_query: str, exclusions: List[str]) -> str:
        """
        Aplica exclusiones con AND NOT.

        Ejemplo:
            main_query = '(("ML") AND ("software"))'
            exclusions = ["hardware", "gaming"]
            → '(("ML") AND ("software")) AND NOT ("hardware" OR "gaming")'

        Args:
            main_query: Query principal ya construida
            exclusions: Lista de términos a excluir

        Returns:
            Query con exclusiones aplicadas
        """
        # Envolver cada exclusión en comillas y unir con OR
        quoted_exclusions = [f'"{exc}"' for exc in exclusions]
        exclusions_group = f"({' OR '.join(quoted_exclusions)})"

        return f"{main_query} AND NOT {exclusions_group}"

    def _apply_year_filter(self, query: str, year_from: int, year_to: int) -> str:
        """
        Aplica filtro de año con PUBYEAR.

        Formato Scopus: PUBYEAR > (from-1) AND PUBYEAR < (to+1)
        Ejemplo: 2020-2024 → PUBYEAR > 2019 AND PUBYEAR < 2025

        Args:
            query: Query ya construida
            year_from: Año inicial (inclusivo)
            year_to: Año final (inclusivo)

        Returns:
            Query con filtro de año
        """
        return f"{query} AND PUBYEAR > {year_from - 1} AND PUBYEAR < {year_to + 1}"
