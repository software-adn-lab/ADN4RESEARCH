"""
Step definitions para Feature 3: Consolidación de metadatos de estudios.

ENFOQUE: Wishful Thinking + Mejores Prácticas BDD
- Constantes importadas del dominio (simuladas hasta que existan)
- GIVEN: Solo prepara estado con from_dict (limpio)
- WHEN: Una sola acción clara con inyección de Mocks
- THEN: Solo verificaciones del resultado observable

ARQUITECTURA PROYECTADA:
  Steps (BDD)
    → ConsolidationService (Application)
       → MetadataEnricher (Domain Service)
       → MetadataNormalizer (Domain Service)
       → CompletenessValidator (Domain Service)
              ↓
       ConsolidationResult
"""

from behave import given, when, then

# Entidades del Shared Kernel (YA EXISTEN)
from apps.acquisition.shared.domain.entities.study import Study

# Mocks para testing (YA EXISTEN en shared/testing/mocks/)
from apps.acquisition.shared.testing.mocks.mock_scopus_connector import MockScopusConnector
from apps.acquisition.shared.testing.mocks.mock_ieee_connector import MockIeeeConnector

# WISHFUL THINKING: Enum para estado de calidad de metadatos (AÚN NO EXISTE)
# from apps.acquisition.metadata.domain.value_objects import ConsolidationStatus
# Por ahora usamos strings literales que coincidirán con el Enum futuro
STATUS_COMPLETO = "completo"
STATUS_PARCIAL = "parcial"
STATUS_FALLIDO = "fallido"


# ============================================================================
# GIVEN - Preparación del Estado Inicial
# ============================================================================

@given('que existe un resultado de descubrimiento con estudios de múltiples fuentes')
def step_resultado_descubrimiento(context):
    """
    Prepara el estado inicial simulando el output del Feature 2 (Descubrimiento).
    Usamos .from_dict() para una configuración limpia y atómica.
    """
    # 1. Estudio COMPLETO (IEEE): Tiene todos los metadatos requeridos
    study_complete = Study.from_dict({
        "title": "Machine Learning for Bug Prediction",
        "link": "https://ieeexplore.ieee.org/document/123456",
        "source": "IEEE Xplore",
        "doi": "10.1109/tse.2021.123456",
        "authors": ["Smith, J.", "García, A."],
        "abstract": "This paper presents a machine learning approach for bug prediction.",
        "year": 2021,
        "status": "discovered"
    })

    # 2. Estudio INCOMPLETO (Scopus): Falta DOI y Abstract (el sistema debe buscarlos)
    study_incomplete = Study.from_dict({
        "title": "Deep Learning in Software Testing",
        "link": "https://scopus.com/record/987654",
        "source": "Scopus",
        "doi": None,       # FALTANTE -> Target del enrichment
        "abstract": None,  # FALTANTE -> Target del enrichment
        "authors": ["Pérez, L."],
        "year": 2020,
        "status": "discovered"
    })

    # 3. Estudio SUCIO (Scopus): Datos presentes pero mal formateados
    study_dirty = Study.from_dict({
        "title": "Defect Prediction Using Neural Networks",
        "link": "https://scopus.com/record/555555",
        "source": "Scopus",
        "doi": "HTTPS://DX.DOI.ORG/10.1000/DIRTY.123",  # MAL FORMATO (Mayúsculas + Prefijo)
        "authors": ["LOPEZ, MARIA", "juan perez"],       # MAL FORMATO (Mayúsculas/Minúsculas)
        "abstract": "Analysis of defect prediction techniques.",
        "year": 2019,
        "status": "discovered"
    })

    context.studies = [study_complete, study_incomplete, study_dirty]


# ============================================================================
# WHEN - Acción Principal (Escenario Automático)
# ============================================================================

@when('solicito consolidar los estudios descubiertos')
def step_solicito_consolidar(context):
    """
    Ejecuta el servicio de consolidación automática.
    Inyecta Mocks para simular respuestas exitosas de las APIs académicas.
    """
    # WISHFUL THINKING: Importamos el servicio que vamos a crear
    from apps.acquisition.metadata.application.consolidation_service import ConsolidationService

    # Usar los mocks existentes (ya tienen find_metadata() configurado)
    connectors = {
        "Scopus": MockScopusConnector(),
        "IEEE Xplore": MockIeeeConnector(),
    }

    # Ejecutar caso de uso
    service = ConsolidationService(connectors=connectors)
    context.consolidation_result = service.consolidate(studies=context.studies)


# ============================================================================
# THEN - Verificaciones (Escenario Automático)
# ============================================================================

@then('el sistema completa los metadatos faltantes consultando las fuentes académicas')
def step_completa_metadatos(context):
    """Verifica que el estudio incompleto (índice 1) ahora tenga datos."""
    studies = context.consolidation_result.studies
    enriched_study = studies[1]  # El que estaba incompleto

    # Verificar DOI completado
    assert enriched_study.doi is not None, \
        f"El DOI no fue completado para '{enriched_study.title}'"
    assert enriched_study.doi.value == "10.1016/j.future.2020.001", \
        f"DOI incorrecto: {enriched_study.doi.value}"

    # Verificar Abstract completado
    assert enriched_study.abstract is not None, \
        f"El Abstract no fue completado para '{enriched_study.title}'"
    assert "recovered by automatic enrichment" in enriched_study.abstract, \
        f"Abstract incorrecto: {enriched_study.abstract}"


@then('normaliza los formatos de DOI, autores y fechas')
def step_normaliza_formatos(context):
    """Verifica que el estudio sucio (índice 2) ahora esté limpio."""
    studies = context.consolidation_result.studies
    clean_study = studies[2]  # El que estaba sucio

    # Verificar DOI normalizado (minúsculas, sin prefijos)
    assert clean_study.doi.value == "10.1000/dirty.123", \
        f"DOI no normalizado. Esperado '10.1000/dirty.123', obtenido '{clean_study.doi.value}'"

    # Verificar Autores normalizados (Title Case)
    # Asumimos normalización a "Apellido, N." o "Apellido, Nombre"
    authors = clean_study.authors
    # Verificamos que "LOPEZ, MARIA" ahora sea algo como "Lopez, Maria"
    assert any("Lopez" in a and "Maria" in a for a in authors), \
        f"Autor 'LOPEZ, MARIA' no normalizado: {authors}"

    # Verificar Año (tipo entero)
    assert isinstance(clean_study.year, int), \
        f"Año debe ser entero, es {type(clean_study.year)}"


@then('cada estudio queda marcado con su estado de consolidación: completo, parcial o fallido')
def step_estado_consolidacion(context):
    """Verifica que se calculó el estado de calidad de los metadatos."""
    studies = context.consolidation_result.studies
    valid_statuses = {STATUS_COMPLETO, STATUS_PARCIAL, STATUS_FALLIDO}

    for study in studies:
        # WISHFUL THINKING: Atributo nuevo en Study
        assert hasattr(study, 'consolidation_status'), \
            f"Estudio '{study.title}' no tiene consolidation_status"

        status = study.consolidation_status
        assert status in valid_statuses, \
            f"Estado inválido '{status}' para '{study.title}'"


@then('se proporciona un resumen del proceso de consolidación')
def step_resumen_consolidacion(context):
    """Verifica el objeto resumen."""
    summary = context.consolidation_result.summary
    assert isinstance(summary, dict), "El resumen debe ser un diccionario"

    # Verificar métricas clave
    assert summary["total_processed"] == 3
    assert "successful" in summary
    assert "failed" in summary


# ============================================================================
# GIVEN - Escenario Manual
# ============================================================================

@given('que un estudio no pudo consolidarse completamente de forma automática')
def step_estudio_fallido(context):
    """
    Prepara un estudio que 'falló' el proceso automático.
    Simulamos un estudio que ya tiene el flag 'fallido' y trazabilidad inicial.
    """
    context.estudio_manual = Study.from_dict({
        "title": "Ghost Paper Manual Edit",
        "link": "https://example.com/ghost",
        "source": "Scopus",
        "doi": None,
        "abstract": None,
        "authors": None,
        "year": None,
        "status": "enriched"  # Ya pasó por el proceso (aunque falló en calidad)
    })

    # Inyección directa de estado fallido (simulando resultado previo)
    # WISHFUL THINKING: Estos atributos serán agregados a Study
    context.estudio_manual.consolidation_status = STATUS_FALLIDO
    context.estudio_manual.field_origins = {
        "title": "discovery",
        "link": "discovery",
        "source": "discovery"
    }


# ============================================================================
# WHEN - Escenario Manual
# ============================================================================

@when('ingreso manualmente los metadatos faltantes del estudio')
def step_ingreso_manual(context):
    """El usuario envía los datos faltantes manualmente."""
    # WISHFUL THINKING: Servicio de edición manual
    from apps.acquisition.metadata.application.manual_edit_service import ManualEditService

    service = ManualEditService()

    user_input = {
        "doi": "10.5555/manual.entry",
        "year": 2024,
        "authors": ["Doe, John", "Smith, Jane"],
        "abstract": "Manually entered abstract content."
    }

    context.estudio_actualizado = service.edit_multiple(
        study=context.estudio_manual,
        edits=user_input
    )


# ============================================================================
# THEN - Escenario Manual
# ============================================================================

@then('el sistema actualiza el registro, valida el formato y marca el estudio como consolidado')
def step_actualiza_valida_marca(context):
    """Verifica persistencia, validación y cambio de estado."""
    s = context.estudio_actualizado

    # 1. Actualiza
    assert s.doi.value == "10.5555/manual.entry"
    assert s.year == 2024
    assert "Manually" in s.abstract

    # 2. Valida (DOI en minúsculas es prueba de normalización/validación)
    assert s.doi.value == s.doi.value.lower()

    # 3. Marca
    assert s.consolidation_status == STATUS_COMPLETO


@then('se mantiene trazabilidad indicando qué campos son automáticos y cuáles manuales')
def step_trazabilidad(context):
    """Verifica el origen de los datos."""
    s = context.estudio_actualizado
    origins = s.field_origins

    # Campos manuales
    assert origins.get("doi") == "manual"
    assert origins.get("year") == "manual"
    assert origins.get("abstract") == "manual"

    # Campos originales (no tocados)
    assert origins.get("title") == "discovery"


# ============================================================================
# INVENTARIO DE PIEZAS A CREAR
# ============================================================================

"""
=============================================================================
ARQUITECTURA A IMPLEMENTAR (nacida del rojo)
=============================================================================

Cuando ejecutes `behave`, los imports fallarán y te indicarán qué crear.

-----------------------------------------------------------------------------
1. DOMINIO - Value Objects
-----------------------------------------------------------------------------
apps/acquisition/metadata/domain/value_objects/consolidation_status.py
    class ConsolidationStatus(Enum):
        COMPLETO = "completo"
        PARCIAL = "parcial"
        FALLIDO = "fallido"

-----------------------------------------------------------------------------
2. DOMINIO - Extensión de Study (Shared Kernel)
-----------------------------------------------------------------------------
apps/acquisition/shared/domain/entities/study.py
    Agregar a la dataclass:
    - consolidation_status: Optional[str] = None
    - field_origins: Dict[str, str] = field(default_factory=dict)

-----------------------------------------------------------------------------
3. APPLICATION - Servicios
-----------------------------------------------------------------------------
apps/acquisition/metadata/application/consolidation_service.py
    class ConsolidationService:
        def __init__(self, connectors: Dict[str, Any])
        def consolidate(self, studies: List[Study]) -> ConsolidationResult

apps/acquisition/metadata/application/manual_edit_service.py
    class ManualEditService:
        def update_study(self, study: Study, updates: dict) -> Study

-----------------------------------------------------------------------------
4. DOMINIO - Entidades
-----------------------------------------------------------------------------
apps/acquisition/metadata/domain/entities/consolidation_result.py
    class ConsolidationResult:
        studies: List[Study]
        summary: dict  # {"total_processed": 3, "successful": 2, "failed": 1}

-----------------------------------------------------------------------------
5. DOMINIO - Servicios
-----------------------------------------------------------------------------
apps/acquisition/metadata/domain/services/metadata_enricher.py
    class MetadataEnricher:
        def enrich(self, study: Study, connectors: Dict) -> Study

apps/acquisition/metadata/domain/services/metadata_normalizer.py
    class MetadataNormalizer:
        def normalize(self, study: Study) -> Study
        def normalize_doi(self, doi: str) -> str
        def normalize_authors(self, authors: List[str]) -> List[str]

apps/acquisition/metadata/domain/services/completeness_validator.py
    class CompletenessValidator:
        def validate(self, study: Study) -> str  # completo/parcial/fallido
        def get_missing_fields(self, study: Study) -> List[str]

-----------------------------------------------------------------------------
REGLAS DE NEGOCIO
-----------------------------------------------------------------------------

COMPLETO requiere:
- title, link, source (obligatorios)
- doi, year, authors (requeridos)
- abstract (deseable, no bloquea)

PARCIAL:
- title, link, source (obligatorios)
- Al menos uno de: doi, year, authors

FALLIDO:
- Falta algún obligatorio O no tiene ningún requerido

NORMALIZACIÓN:
- DOI: minúsculas, sin https://doi.org/, sin dx.doi.org
- Autores: "Apellido, Nombre" en Title Case
- Año: entero

TRAZABILIDAD (field_origins):
- "discovery": Dato del Feature 2
- "automatic": Completado por MetadataEnricher
- "manual": Ingresado por usuario

=============================================================================
"""
