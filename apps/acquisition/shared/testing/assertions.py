"""
Assertions y validators para steps de BDD.

Este módulo contiene las clases que validan los Then de los features.
"""

import re
from typing import Dict, Any, List
from apps.acquisition.translation.domain.models import NormalizedStrategy


class SyntaxValidator:
    """Valida sintaxis de queries por dialecto."""

    def assert_scopus_syntax(
        self,
        query: str,
        expected_field_code: str,
        expected_year_filter: Dict[str, int],
        require_uppercase_operators: bool,
        require_balanced_parentheses: bool
    ) -> None:
        """
        Valida sintaxis de Scopus.

        Checks:
        - Contiene field code (TITLE-ABS-KEY)
        - Tiene filtro de año con PUBYEAR
        - Operadores en MAYÚSCULAS
        - Paréntesis balanceados
        """
        # 1. Field code
        assert expected_field_code in query, \
            f"Query debe contener '{expected_field_code}'"

        # 2. Filtro de año
        year_from = expected_year_filter["from"]
        year_to = expected_year_filter["to"]

        # Scopus usa PUBYEAR > (from-1) AND PUBYEAR < (to+1)
        assert f"PUBYEAR > {year_from - 1}" in query, \
            f"Query debe contener 'PUBYEAR > {year_from - 1}'"
        assert f"PUBYEAR < {year_to + 1}" in query, \
            f"Query debe contener 'PUBYEAR < {year_to + 1}'"

        # 3. Operadores en MAYÚSCULAS
        if require_uppercase_operators:
            self._assert_uppercase_operators(query)

        # 4. Paréntesis balanceados
        if require_balanced_parentheses:
            self._assert_balanced_parentheses(query)

    def assert_ieee_syntax(
        self,
        query: str,
        forbid_scopus_field_codes: bool,
        forbid_year_in_query: bool,
        exclusion_format: str,
        require_uppercase_operators: bool,
        require_balanced_parentheses: bool
    ) -> None:
        """
        Valida sintaxis de IEEE Xplore.

        Checks:
        - NO contiene field codes de Scopus (TITLE-ABS-KEY, PUBYEAR)
        - Exclusiones con formato "NOT (...)" no "AND NOT"
        - Operadores en MAYÚSCULAS
        - Paréntesis balanceados

        Args:
            query: Query a validar
            forbid_scopus_field_codes: Si True, verifica que NO haya TITLE-ABS-KEY
            forbid_year_in_query: Si True, verifica que NO haya PUBYEAR
            exclusion_format: Formato esperado (ej: "NOT (...)")
            require_uppercase_operators: Si True, valida operadores en mayúsculas
            require_balanced_parentheses: Si True, valida paréntesis balanceados
        """
        # 1. Verificar que NO use field codes de Scopus
        if forbid_scopus_field_codes:
            assert "TITLE-ABS-KEY" not in query, \
                "IEEE Xplore no debe usar TITLE-ABS-KEY (es específico de Scopus)"

        # 2. Verificar que NO haya filtro de año en la query
        if forbid_year_in_query:
            assert "PUBYEAR" not in query, \
                "IEEE Xplore no debe incluir PUBYEAR en la query (se aplica en UI)"

        # 3. Verificar formato de exclusiones
        # IEEE usa "NOT (...)" NO "AND NOT"
        if exclusion_format == "NOT (...)":
            assert " AND NOT " not in query, \
                "IEEE no debe usar 'AND NOT' para exclusiones (usar 'NOT (...)')"

            # Si hay NOT, debe tener el formato correcto
            if " NOT " in query:
                assert " NOT (" in query, \
                    "IEEE debe usar 'NOT (...)' para exclusiones (sin 'AND' antes)"

        # 4. Operadores en MAYÚSCULAS
        if require_uppercase_operators:
            self._assert_uppercase_operators(query)

        # 5. Paréntesis balanceados
        if require_balanced_parentheses:
            self._assert_balanced_parentheses(query)

    def _assert_uppercase_operators(self, query: str) -> None:
        """Valida que AND/OR/NOT estén en MAYÚSCULAS."""
        # Buscar operadores en minúsculas (palabra completa)
        lowercase_and = re.search(r'\band\b', query)
        lowercase_or = re.search(r'\bor\b', query)
        lowercase_not = re.search(r'\bnot\b', query)

        assert not lowercase_and, "Operador 'and' debe estar en MAYÚSCULAS (AND)"
        assert not lowercase_or, "Operador 'or' debe estar en MAYÚSCULAS (OR)"
        assert not lowercase_not, "Operador 'not' debe estar en MAYÚSCULAS (NOT)"

    def _assert_balanced_parentheses(self, query: str) -> None:
        """Valida que los paréntesis estén balanceados."""
        count = 0
        for char in query:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            if count < 0:
                raise AssertionError("Paréntesis desbalanceados: ')' sin '(' correspondiente")

        assert count == 0, f"Paréntesis desbalanceados: {count} paréntesis sin cerrar"


class LogicPreservationChecker:
    """Verifica preservación de lógica semántica."""

    def assert_all_main_terms_present(
        self,
        strategy: NormalizedStrategy,
        query: str
    ) -> None:
        """Verifica que cada main_term aparece (al menos una variante)."""
        for main_term in strategy.main_terms:
            # Verificar término principal O al menos un sinónimo
            all_variants = [main_term.term] + main_term.synonyms

            found = any(variant.lower() in query.lower() for variant in all_variants)

            assert found, \
                f"Ninguna variante de '{main_term.term}' encontrada en query"

    def assert_synonyms_grouped_with_or(
        self,
        strategy: NormalizedStrategy,
        query: str
    ) -> None:
        """Verifica OR entre sinónimos dentro de cada grupo."""
        # Verificar que existe " OR " en la query (simplificado)
        if any(len(mt.synonyms) > 0 for mt in strategy.main_terms):
            assert " OR " in query, \
                "Query debe contener ' OR ' para unir sinónimos"

    def assert_term_groups_joined_with_and(
        self,
        strategy: NormalizedStrategy,
        query: str
    ) -> None:
        """Verifica AND entre grupos de términos."""
        if len(strategy.main_terms) > 1:
            assert " AND " in query, \
                "Query debe contener ' AND ' para unir grupos de términos"

    def assert_exclusions_negated(
        self,
        strategy: NormalizedStrategy,
        query: str,
        target: str
    ) -> None:
        """Verifica que exclusiones aparecen negadas."""
        if not strategy.exclusions:
            return

        if target == "Scopus":
            # Scopus usa AND NOT
            assert " AND NOT " in query, \
                "Scopus debe usar ' AND NOT ' para exclusiones"

            # Verificar que al menos una exclusión aparece
            found = any(exc.lower() in query.lower() for exc in strategy.exclusions)
            assert found, "Al menos una exclusión debe aparecer en query"

        elif target == "IEEE Xplore":
            # IEEE usa NOT (...)
            assert " NOT " in query, \
                "IEEE debe usar ' NOT ' para exclusiones"

    def assert_year_filter_placement(
        self,
        strategy: NormalizedStrategy,
        query: str,
        target: str
    ) -> None:
        """Verifica ubicación del filtro de año según target."""
        if not strategy.year_filter:
            return

        if target == "Scopus":
            # Año debe estar EN la query
            assert "PUBYEAR" in query, \
                "Scopus debe incluir PUBYEAR en la query"

        elif target == "IEEE Xplore":
            # Año NO debe estar en la query
            assert "PUBYEAR" not in query, \
                "IEEE no debe incluir PUBYEAR en la query"

    def assert_operator_precedence(
        self,
        query: str,
        target: str
    ) -> None:
        """Verifica que precedencia de operadores se respeta (simplificado)."""
        # Por ahora, verificar que hay paréntesis agrupando correctamente
        # (validación completa requeriría parsear la query)
        assert "(" in query and ")" in query, \
            "Query debe tener paréntesis para agrupar operadores"


class TraceValidator:
    """Valida trazabilidad."""

    def assert_trace_complete(
        self,
        trace: Dict[str, Any],
        expected_target: str,
        require_trace_id: bool,
        require_steps_or_rules: bool,
        require_timestamp: bool
    ) -> None:
        """
        Valida que trace esté completo.

        Checks:
        - trace_id no vacío
        - target coincide
        - steps_applied o rules_applied no vacíos
        - timestamp presente
        """
        # 1. trace_id
        if require_trace_id:
            assert "trace_id" in trace, "Trace debe tener 'trace_id'"
            assert trace["trace_id"], "trace_id no debe estar vacío"

        # 2. target
        assert "target" in trace, "Trace debe tener 'target'"
        assert trace["target"] == expected_target, \
            f"target en trace debe ser '{expected_target}', no '{trace['target']}'"

        # 3. steps o rules
        if require_steps_or_rules:
            has_steps = "steps_applied" in trace and len(trace["steps_applied"]) > 0
            has_rules = "rules_applied" in trace and len(trace["rules_applied"]) > 0

            assert has_steps or has_rules, \
                "Trace debe tener 'steps_applied' o 'rules_applied' no vacíos"

        # 4. timestamp
        if require_timestamp:
            assert "timestamp" in trace, "Trace debe tener 'timestamp'"
            assert trace["timestamp"], "timestamp no debe estar vacío"
            # Validar formato ISO-8601 (simplificado)
            assert "T" in trace["timestamp"] or "-" in trace["timestamp"], \
                "timestamp debe estar en formato ISO-8601"


class WarningValidator:
    """Valida warnings."""

    def assert_no_warnings(self, warnings: List[str]) -> None:
        """Valida que no hay warnings."""
        assert len(warnings) == 0, \
            f"No se esperaban warnings, pero se encontraron: {warnings}"

    def assert_year_manual_warning_present(
        self,
        warnings: List[str],
        year_from: int,
        year_to: int
    ) -> None:
        """Valida presencia de warning de año manual (IEEE)."""
        assert len(warnings) > 0, \
            "Se esperaba al menos un warning sobre filtro de año manual"

        # Buscar warning que mencione año y el rango
        found = False
        for warning in warnings:
            lower_warning = warning.lower()
            has_year_keyword = ("año" in lower_warning or "year" in lower_warning)
            has_range = (str(year_from) in warning and str(year_to) in warning)

            if has_year_keyword and has_range:
                found = True
                break

        assert found, \
            f"No se encontró warning con 'año/year' y rango '{year_from}-{year_to}'. " \
            f"Warnings: {warnings}"
