"""
Steps de BDD para Feature 1: Traducción de estrategias de búsqueda.

PRINCIPIOS:
- Comportamiento observable, NO implementación
- Wishful thinking: invocamos servicios/aserciones que NO existen aún
- Sin DB, sin eventos, sin cargar documentos en runtime
- Docs-Feature1 es referencia HUMANA, no se carga aquí

CONTRATO DEL RESULTADO (lo exigen los Then, NO lo fabrican):
{
    "query": str,           # Query traducida
    "status": str,          # "Done" para este feature
    "warnings": [str],      # Lista de advertencias (puede estar vacía)
    "trace": {
        "trace_id": str,
        "target": str,
        "steps_applied": [str],
        "rules_applied": [str],
        "timestamp": str
    },
    "target": str,          # "Scopus" / "IEEE Xplore"
    "metadata": dict        # Opcional
}
"""

from behave import given, when, then
import json


# ============================================================================
# GIVEN: Preparar entrada de negocio
# ============================================================================

@given('una estrategia de búsqueda normalizada estructurada')
def step_given_estrategia_normalizada(context):
    """
    OBJETIVO: Dejar lista la entrada de negocio para todo el escenario.

    INCLUYE:
    1. Parsear el JSON del docstring del Background a una entidad NormalizedStrategy
    2. Verificar existencia de strategy_id y main_terms no vacío
    3. Guardar la entidad en context.strategy
    4. Guardar copia en context.strategy_original (para verificar inmutabilidad)

    NO INCLUYE:
    - Cargar políticas/documentos
    - Traducir nada
    - Asserts complejos

    QUÉ LOGRA:
    - Entrada lista para el When
    - Compromiso de inmutabilidad establecido
    """
    # Parsear JSON del docstring
    strategy_json = json.loads(context.text)

    # Validar campos obligatorios (falla rápido si falta algo)
    assert "strategy_id" in strategy_json, "La estrategia debe tener strategy_id"
    assert "main_terms" in strategy_json, "La estrategia debe tener main_terms"
    assert len(strategy_json["main_terms"]) > 0, "main_terms no puede estar vacío"

    # WISHFUL THINKING: crear entidad de dominio que NO existe aún
    from apps.acquisition.domain.models import NormalizedStrategy

    context.strategy = NormalizedStrategy.from_dict(strategy_json)
    context.strategy_original = NormalizedStrategy.from_dict(strategy_json)


# ============================================================================
# WHEN: Ejecutar la acción principal
# ============================================================================

@when('solicito traducir mi estrategia de búsqueda para "{base_datos}"')
def step_when_solicito_traducir(context, base_datos):
    """
    OBJETIVO: Ejecutar la acción que el usuario hace - pedir la traducción.

    INCLUYE:
    1. Guardar base_datos en contexto
    2. Invocar caso de uso de traducción con strategy y target
    3. Guardar resultado completo (respeta contrato definido arriba)

    NO INCLUYE:
    - Asserts
    - Normalizaciones
    - Cargar políticas

    QUÉ LOGRA:
    - Fija entrada/salida del caso de uso
    - Si el servicio no existe, falla (rojo) → guía el diseño
    """
    context.base_datos = base_datos

    # WISHFUL THINKING: invocar servicio que NO existe aún
    from apps.acquisition.application.services import TranslationService

    service = TranslationService()

    context.result = service.translate(
        strategy=context.strategy,
        target=base_datos
    )


# ============================================================================
# THEN: Compatibilidad sintáctica con dialecto del target
# ============================================================================

@then('obtengo una consulta traducida compatible con la sintaxis de {base_datos}')
def step_then_consulta_compatible_sintaxis(context, base_datos):
    """
    OBJETIVO: Afirmar que la salida cumple el dialecto del target.

    CRITERIOS SCOPUS:
    - La query existe y no está vacía
    - Contiene TITLE-ABS-KEY(
    - Tiene filtro de año con PUBYEAR (2020-2024 como "> 2019 AND < 2025")
    - Operadores booleanos en MAYÚSCULAS (AND/OR/NOT)
    - Paréntesis balanceados

    CRITERIOS IEEE XPLORE:
    - La query existe y no está vacía
    - NO contiene TITLE-ABS-KEY ni PUBYEAR
    - Exclusiones con NOT (...) no "AND NOT"
    - Operadores booleanos en MAYÚSCULAS
    - Paréntesis balanceados

    NOTA: Comparación tolerante (no carácter a carácter).
    Si runner no interpola <consulta_traducida> del docstring,
    tomar de Examples.

    NO INCLUYE:
    - Parseos profundos en steps
    - Helpers de formateo aquí

    QUÉ LOGRA:
    - Barra clara de "compatible con dialecto" por base
    """
    # WISHFUL THINKING: usar módulo de aserciones que NO existe aún
    from apps.acquisition.testing.assertions import SyntaxValidator

    validator = SyntaxValidator()

    query = context.result["query"]

    # Validar que query existe y no está vacía
    assert query, "La query traducida no debe estar vacía"

    # Validar según target
    if base_datos == "Scopus":
        validator.assert_scopus_syntax(
            query=query,
            expected_field_code="TITLE-ABS-KEY",
            expected_year_filter={"from": 2020, "to": 2024},
            require_uppercase_operators=True,
            require_balanced_parentheses=True
        )
    elif base_datos == "IEEE Xplore":
        validator.assert_ieee_syntax(
            query=query,
            forbid_scopus_field_codes=True,
            forbid_year_in_query=True,
            exclusion_format="NOT (...)",
            require_uppercase_operators=True,
            require_balanced_parentheses=True
        )


# ============================================================================
# THEN: Preservación de lógica semántica
# ============================================================================

@then('la consulta traducida preserva la lógica de mi estrategia original')
def step_then_preserva_logica(context):
    """
    OBJETIVO: Afirmar equivalencia semántica (no solo sintaxis).

    CRITERIOS (de Docs-Feature1, pero NO se cargan aquí):
    1. Por cada main_term, aparece al menos una variante en la query
    2. Dentro de cada grupo, sinónimos unidos con OR
    3. Entre grupos (tres en el ejemplo), unidos con AND
    4. Exclusions aparecen negadas:
       - Scopus: AND NOT (...)
       - IEEE: NOT (...)
    5. Filtro de año:
       - Scopus: está en la query
       - IEEE: NO está (se cubre con warning en otro Then)
    6. Precedencia de operadores respetada:
       - Scopus actual: OR > W/PRE > AND > AND NOT
       - IEEE: NEAR/ONEAR > NOT > AND > OR
       (El verificador conoce esto, NO los steps)

    NO INCLUYE:
    - Cómputos ni análisis textual pesado aquí

    QUÉ LOGRA:
    - Blinda el significado de la estrategia en la traducción
    """
    # WISHFUL THINKING: usar verificador semántico que NO existe aún
    from apps.acquisition.testing.assertions import LogicPreservationChecker

    checker = LogicPreservationChecker()

    checker.assert_all_main_terms_present(
        strategy=context.strategy,
        query=context.result["query"]
    )

    checker.assert_synonyms_grouped_with_or(
        strategy=context.strategy,
        query=context.result["query"]
    )

    checker.assert_term_groups_joined_with_and(
        strategy=context.strategy,
        query=context.result["query"]
    )

    checker.assert_exclusions_negated(
        strategy=context.strategy,
        query=context.result["query"],
        target=context.result["target"]
    )

    checker.assert_year_filter_placement(
        strategy=context.strategy,
        query=context.result["query"],
        target=context.result["target"]
    )

    checker.assert_operator_precedence(
        query=context.result["query"],
        target=context.result["target"]
    )


# ============================================================================
# THEN: Estado observable del proceso
# ============================================================================

@then('el estado de la traducción es "{estado_esperado}"')
def step_then_estado_traduccion(context, estado_esperado):
    """
    OBJETIVO: Chequear estado observable del caso de uso.

    INCLUYE:
    - status del resultado es exactamente el esperado ("Done")

    NO INCLUYE:
    - Deducciones por inspección de la query

    QUÉ LOGRA:
    - Definición precisa del final feliz del caso de uso
    """
    actual_status = context.result["status"]

    assert actual_status == estado_esperado, \
        f"Se esperaba status '{estado_esperado}', pero se obtuvo '{actual_status}'"


# ============================================================================
# THEN: Auditoría y trazabilidad
# ============================================================================

@then('se registra la trazabilidad de la traducción')
def step_then_trazabilidad(context):
    """
    OBJETIVO: Exigir auditoría mínima (reproducible y defendible).

    INCLUYE:
    1. Existe trace
    2. trace_id no vacío (formato libre por ahora)
    3. trace.target == base_datos
    4. steps_applied o rules_applied con al menos un elemento
       Ejemplos: "group_synonyms", "apply_exclusions", "wrap_field_code",
                 "separate_year_filter", "apply_precedence"
    5. timestamp presente (ideal ISO-8601)
    6. INMUTABILIDAD: estrategia de entrada no fue modificada

    NO INCLUYE:
    - Persistencia real
    - Formato específico de trace_id (UUID, etc.)

    QUÉ LOGRA:
    - Explicabilidad y reproducibilidad sin tocar infraestructura
    """
    # WISHFUL THINKING: usar módulo de aserciones de traza que NO existe aún
    from apps.acquisition.testing.assertions import TraceValidator

    validator = TraceValidator()

    # Validar estructura de traza
    assert "trace" in context.result, "El resultado debe contener 'trace'"

    trace = context.result["trace"]

    validator.assert_trace_complete(
        trace=trace,
        expected_target=context.base_datos,
        require_trace_id=True,
        require_steps_or_rules=True,
        require_timestamp=True
    )

    # Validar inmutabilidad de la estrategia
    assert context.strategy == context.strategy_original, \
        "La estrategia original no debe modificarse durante la traducción"


# ============================================================================
# THEN: Advertencias (warnings)
# ============================================================================

@then('{advertencias}')
def step_then_advertencias(context, advertencias):
    """
    OBJETIVO: Chequear warnings según Examples.

    CASOS:
    1. Scopus: "no se emiten advertencias" → lista vacía
    2. IEEE: "se emite una advertencia... filtro de año 2020-2024 manualmente"
       → al menos una advertencia con "año/year" + "2020-2024"

    NO INCLUYE:
    - Frase exacta (basta palabras clave + rango)

    QUÉ LOGRA:
    - Cubre diferencia de capacidades entre targets (año en UI vs query)
    """
    # WISHFUL THINKING: usar módulo de validación de warnings que NO existe aún
    from apps.acquisition.testing.assertions import WarningValidator

    validator = WarningValidator()

    warnings = context.result["warnings"]

    if advertencias == "no se emiten advertencias":
        # Caso Scopus: lista vacía
        validator.assert_no_warnings(warnings)

    elif "filtro de año" in advertencias and "manualmente" in advertencias:
        # Caso IEEE: warning de año manual
        validator.assert_year_manual_warning_present(
            warnings=warnings,
            year_from=2020,
            year_to=2024
        )

    else:
        # Otros casos futuros
        raise NotImplementedError(
            f"Validación no implementada para: '{advertencias}'"
        )


# ============================================================================
# DOCUMENTACIÓN: QUÉ CONSTRUIR (mapa de diseño)
# ============================================================================

"""
INVENTARIO DE PIEZAS A CREAR (nacidas del rojo):

1. apps.acquisition.domain.models.NormalizedStrategy ✅ CREADO
   - Entidad inmutable
   - from_dict(data: dict) -> NormalizedStrategy
   - __eq__ para comparar inmutabilidad

2. apps.acquisition.application.services.TranslationService
   - translate(strategy, target) -> dict con contrato definido
   - Retorna: {query, status, warnings, trace, target, metadata}

3. apps.acquisition.testing.assertions.SyntaxValidator
   - assert_scopus_syntax(query, ...)
   - assert_ieee_syntax(query, ...)

4. apps.acquisition.testing.assertions.LogicPreservationChecker
   - assert_all_main_terms_present(strategy, query)
   - assert_synonyms_grouped_with_or(strategy, query)
   - assert_term_groups_joined_with_and(strategy, query)
   - assert_exclusions_negated(strategy, query, target)
   - assert_year_filter_placement(strategy, query, target)
   - assert_operator_precedence(query, target)

5. apps.acquisition.testing.assertions.TraceValidator
   - assert_trace_complete(trace, expected_target, ...)

6. apps.acquisition.testing.assertions.WarningValidator
   - assert_no_warnings(warnings)
   - assert_year_manual_warning_present(warnings, year_from, year_to)

REGLAS DE NEGOCIO (de Docs-Feature1, para implementar verificadores):

Scopus:
- Field wrapper: TITLE-ABS-KEY(...)
- Año: PUBYEAR > 2019 AND PUBYEAR < 2025 (para 2020-2024)
- Exclusión: AND NOT (...)
- Precedencia: OR > W/PRE > AND > AND NOT (actual, cambiará)

IEEE Xplore:
- Sin field wrapper en query
- Año: NO en query → warning + metadata
- Exclusión: NOT (...)
- Precedencia: NEAR/ONEAR > NOT > AND > OR

Validaciones:
- Scopus: máx 256 caracteres por línea
- IEEE: máx 8 comodines, máx 20-40 términos
"""
