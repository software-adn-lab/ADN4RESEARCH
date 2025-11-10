"""
Step definitions para Feature 2: Descubrimiento de estudios.

ENFOQUE: Wishful Thinking - Los steps declaran TODO el contrato.
- Imports de clases que aún no existen (para "clic derecho → generar")
- Inyección completa de mocks
- Firmas de métodos esperadas
- Sin lógica temporal (el servicio hace TODO)
- SIN reglas de negocio locales (se importan del dominio)

ARQUITECTURA DECLARADA:
  Steps (BDD)
    → DiscoveryService (Application)
       → IAcademicConnector (Interface/Puerto)
          ↙                ↘
   MockScopusConnector  MockIeeeConnector
          ↓                   ↓
      List[Study]         List[Study]
          ↘                 ↙
           Deduplicator (usa normalizers del dominio)
                ↓
          DiscoveryResult
"""

from behave import given, when, then
from typing import Dict, List, Any

# IMPORTS WISHFUL: Normalizadores del DOMINIO (una sola fuente de verdad)
from apps.acquisition.domain.services.deduplication.normalizers import (
    normalize_title,
    normalize_doi,
)


# ============================================================================
# GIVEN - Precondiciones
# ============================================================================

@given('que el sistema soporta las fuentes "{fuente1}" e "{fuente2}"')
def step_sistema_soporta_fuentes(context, fuente1: str, fuente2: str):
    """Define las fuentes válidas del sistema."""
    context.supported_sources = [fuente1, fuente2]


@given('una estrategia normalizada con id "{strategy_id}"')
def step_estrategia_con_id(context, strategy_id: str):
    """Registra el ID de la estrategia (sin consultar almacenamiento en fase mock)."""
    context.strategy_id = strategy_id


@given('las traducciones para esa estrategia tienen los siguientes estados')
def step_traducciones_con_estados(context):
    """
    Carga estados de traducciones por fuente desde la tabla del escenario.

    Estados válidos: 'ready', 'not_supported'

    Formato resultante:
    {
        "Scopus":      {"status": "ready",         "query": "MOCK_QUERY_SCOPUS"},
        "IEEE Xplore": {"status": "not_supported", "query": None}
    }
    """
    context.translation_statuses: Dict[str, Dict[str, Any]] = {}
    valid_statuses = {"ready", "not_supported"}

    for row in context.table:
        fuente = row["fuente"]
        estado = row["estado"]

        assert estado in valid_statuses, \
            f"Estado inválido '{estado}' para {fuente}. Válidos: {sorted(valid_statuses)}"

        # Mock: generar query ficticia para estados ready
        mock_query = f"MOCK_QUERY_{fuente.replace(' ', '_').upper()}" if estado == "ready" else None

        context.translation_statuses[fuente] = {
            "status": estado,
            "query": mock_query
        }


# ============================================================================
# WHEN - Acción: Orquestación completa (wishful thinking)
# ============================================================================

@when('ejecuto el descubrimiento para la estrategia "{strategy_id}"')
def step_ejecutar_descubrimiento(context, strategy_id: str):
    """
    Ejecuta el caso de uso de descubrimiento con inyección de mocks.

    CONTRATOS DECLARADOS (para generar con IDE):

    1. DiscoveryService (apps.acquisition.application.discovery_service)
       - __init__(self, connectors: Dict[str, IAcademicConnector])
       - execute(self, strategy_id: str, translation_statuses: dict, supported_sources: list) -> DiscoveryResult

    2. IAcademicConnector (apps.acquisition.domain.interfaces.i_academic_connector)
       - search(self, query: str) -> List[Study]

    3. MockScopusConnector (apps.acquisition.testing.mocks.mock_scopus_connector)
       - Implementa IAcademicConnector
       - search(self, query: str) -> List[Study] con fixtures deterministas

    4. MockIeeeConnector (apps.acquisition.testing.mocks.mock_ieee_connector)
       - Implementa IAcademicConnector
       - search(self, query: str) -> List[Study] con fixtures deterministas (incluir duplicado)

    5. Study (apps.acquisition.domain.entities.study)
       - Dataclass con: title, link, source, doi (opcional)

    6. DiscoveryResult (apps.acquisition.domain.entities.discovery_result)
       - studies: List[Study]
       - summary: dict
       - to_dict() -> dict  ← Convierte estudios a dicts

    7. Deduplicator (apps.acquisition.domain.services.deduplication.deduplicator)
       - deduplicate(self, studies: List[Study]) -> List[Study]
       - USA normalize_title y normalize_doi del dominio

    8. Normalizers (apps.acquisition.domain.services.deduplication.normalizers)
       - normalize_title(title: str) -> str
       - normalize_doi(raw: str) -> str
    """
    # Validaciones de contexto
    assert hasattr(context, "strategy_id"), "Falta strategy_id en contexto"
    assert context.strategy_id == strategy_id, "strategy_id inconsistente"
    assert hasattr(context, "supported_sources"), "Faltan supported_sources"
    assert hasattr(context, "translation_statuses"), "Faltan translation_statuses"

    # IMPORTS WISHFUL: Clases que se generarán con el IDE
    from apps.acquisition.application.discovery_service import DiscoveryService
    from apps.acquisition.testing.mocks.mock_scopus_connector import MockScopusConnector
    from apps.acquisition.testing.mocks.mock_ieee_connector import MockIeeeConnector

    # Inyección de conectores mock (contrato explícito)
    connectors = {
        "Scopus": MockScopusConnector(),
        "IEEE Xplore": MockIeeeConnector(),
    }

    # Crear servicio con inyección de dependencias
    service = DiscoveryService(connectors=connectors)

    # Ejecutar caso de uso (firma esperada)
    result = service.execute(
        strategy_id=context.strategy_id,
        translation_statuses=context.translation_statuses,
        supported_sources=context.supported_sources,
    )

    # Convertir resultado a dict para verificaciones en Then
    # Ahora TODOS los estudios son dicts (no mezcla dict/objeto)
    context.discovery_result = result.to_dict()


# ============================================================================
# THEN - Verificaciones de aceptación
# ============================================================================

@then('obtengo un listado de estudios')
def step_verificar_listado(context):
    """Verifica existencia de la colección de estudios."""
    assert hasattr(context, "discovery_result"), "Falta discovery_result"
    assert "studies" in context.discovery_result, "Falta 'studies' en resultado"
    assert isinstance(context.discovery_result["studies"], list), "'studies' debe ser lista"


@then('el listado no contiene duplicados')
def step_sin_duplicados(context):
    """
    Valida deduplicación correcta usando LAS MISMAS reglas del dominio.

    Regla: DOI normalizado (prioritario) > título normalizado
    Mantener primera ocurrencia.

    IMPORTANTE: Usa normalize_title y normalize_doi importados del DOMINIO.
    NO reimplementa la lógica aquí (una sola fuente de verdad).
    """
    studies = context.discovery_result["studies"]
    seen = set()

    for idx, study in enumerate(studies):
        # Todos son dicts ahora (gracias a to_dict())
        doi = study.get("doi", "")
        title = study.get("title", "")

        # Usar MISMAS reglas que el Deduplicator del dominio
        if doi:
            key = f"doi::{normalize_doi(doi)}"
        else:
            key = f"title::{normalize_title(title)}"

        assert key not in seen, f"Duplicado detectado en estudio {idx}: {key}"
        seen.add(key)


@then('cada estudio tiene título, enlace y fuente')
def step_campos_minimos(context):
    """
    Valida estructura mínima de Study (convertido a dict):
    - title no vacío
    - link no vacío
    - source no vacío y pertenece a supported_sources
    """
    studies = context.discovery_result["studies"]
    supported = {s.strip() for s in context.supported_sources}

    for idx, study in enumerate(studies):
        # Acceso directo a dict (to_dict() unificó el formato)
        title = study.get("title", "")
        link = study.get("link", "")
        source = study.get("source", "")

        assert title and title.strip(), f"Estudio {idx}: 'title' vacío"
        assert link and link.strip(), f"Estudio {idx}: 'link' vacío"
        assert source and source.strip(), f"Estudio {idx}: 'source' vacío"
        assert source in supported, f"Estudio {idx}: source '{source}' no soportada"


@then('obtengo un resumen con id_estrategia "{strategy_id}" y resultado "{expected_resultado}"')
def step_resumen_minimo(context, strategy_id: str, expected_resultado: str):
    """
    Valida resumen de ejecución (aceptación, no exhaustivo).

    Verificaciones clave:
    - id_estrategia coincide
    - resultado coincide y es válido ('complete' | 'partial')
    - total_bruto = suma(total_por_fuente)
    - total_unicos ≤ total_bruto
    """
    assert "summary" in context.discovery_result, "Falta 'summary' en resultado"
    summary = context.discovery_result["summary"]

    # id_estrategia
    assert summary.get("id_estrategia") == strategy_id, \
        f"id_estrategia: esperado '{strategy_id}', recibido '{summary.get('id_estrategia')}'"

    # resultado
    assert summary.get("resultado") == expected_resultado, \
        f"resultado: esperado '{expected_resultado}', recibido '{summary.get('resultado')}'"
    assert summary["resultado"] in {"complete", "partial"}, \
        f"resultado debe ser 'complete' o 'partial', no '{summary['resultado']}'"

    # Coherencias numéricas
    total_por_fuente = summary.get("total_por_fuente", {})
    assert isinstance(total_por_fuente, dict), "total_por_fuente debe ser dict"

    suma = sum(total_por_fuente.values())
    assert summary.get("total_bruto") == suma, \
        f"total_bruto ({summary.get('total_bruto')}) != suma(total_por_fuente) ({suma})"

    total_unicos = summary.get("total_unicos", -1)
    total_bruto = summary.get("total_bruto", -1)
    assert total_unicos <= total_bruto, \
        f"total_unicos ({total_unicos}) no puede ser mayor que total_bruto ({total_bruto})"
