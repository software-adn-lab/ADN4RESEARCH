"""
Step definitions para Feature 4: Disponibilidad y descarga de texto completo.

ENFOQUE: Wishful Thinking + Alineado con Features 1-3

ARQUITECTURA (Clean Architecture + Hexagonal):
  Steps (BDD - Driver)
    → FullTextService        (Application Layer)
    → ManualUploadService    (Application Layer)
       → IDownloadConnector  (Port - Interface)
       → FileValidator       (Domain Service)

ESTRATEGIA DE STEPS (igual que Feature 3):
- GIVEN: Prepara estudios con Study.from_dict (sin lógica compleja)
- WHEN: Una sola acción que ejecuta el servicio de aplicación
- THEN: Verificaciones de RESULTADOS observables (no acciones)
"""

from behave import given, when, then

# Entidades compartidas (YA EXISTEN)
from apps.acquisition.shared.domain.entities.study import Study

# Value Objects de descargas (WISHFUL THINKING: se crearán)
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource

# Mocks compartidos (WISHFUL THINKING: se crearán en shared/testing/mocks)
from apps.acquisition.shared.testing.mocks.downloads import (
    build_fulltext_service_with_mocks,
    build_manual_upload_service_with_mocks,
)

# Constantes (extraídas de los VOs, igual que Feature 3)
STATUS_DISPONIBLE = DownloadStatus.DISPONIBLE.value
STATUS_NO_DISPONIBLE = DownloadStatus.NO_DISPONIBLE.value

ORIGIN_AUTO = PdfSource.AUTOMATICO.value
ORIGIN_MANUAL = PdfSource.MANUAL.value
ORIGIN_ALTERNATIVO = PdfSource.ALTERNATIVO.value

# Constante para archivo fake de carga manual
FAKE_UPLOADED_FILE = "/uploads/temp/usuario_paper.pdf"


# ============================================================================
# GIVEN - Background (igual que Feature 3: crea la lista completa)
# ============================================================================

@given('que existen estudios con metadatos consolidados de mi revisión sistemática')
def step_background_estudios_consolidados(context):
    """
    Prepara el estado inicial simulando el output del Feature 3 (Consolidación).

    Crea una lista de estudios consolidados con diferentes características
    para probar los 3 escenarios de descarga:
    1. Open Access (descarga directa)
    2. Paywall (requiere fuente alternativa)
    3. Failed automatic (requiere carga manual)

    Esto es análogo a Feature 3 que crea: completo, incompleto, sucio.
    """
    # 1. Estudio OPEN ACCESS
    study_oa = Study.from_dict({
        "title": "Open Access AI Paper",
        "link": "https://example.com/oa",
        "source": "Scopus",
        "doi": "10.1000/open.access",
        "year": 2024,
        "authors": ["Researcher, OA"],
        "status": "enriched",
        "consolidation_status": "completo",
    })

    # 2. Estudio PAYWALL (necesita fuente alternativa)
    study_paywall = Study.from_dict({
        "title": "Paywalled Paper",
        "link": "https://example.com/paywall",
        "source": "IEEE Xplore",
        "doi": "10.1000/paywall.123",
        "year": 2023,
        "authors": ["Dr. Private"],
        "status": "enriched",
        "consolidation_status": "completo",
    })

    # 3. Estudio FAILED (necesita carga manual)
    study_failed = Study.from_dict({
        "title": "Lost Paper",
        "link": "https://example.com/lost",
        "source": "Scopus",
        "doi": "10.1000/missing",
        "status": "enriched",
        "consolidation_status": "completo",
    })

    # Guardar en contexto (análogo a context.studies de Feature 3)
    context.consolidated_studies = {
        "open_access": study_oa,
        "paywall": study_paywall,
        "failed": study_failed,
    }


# ============================================================================
# GIVEN - Selección del estudio para cada escenario
# ============================================================================

@given('que un estudio tiene el texto completo de acceso público')
def step_estudio_open_access(context):
    """
    Selecciona el estudio OA de la lista creada en Background.

    GARANTIZA precondiciones verificables (NO es narrativo):
    - Tiene DOI (necesario para consultar APIs de Open Access)
    - Está consolidado (estado "completo")
    """
    context.study = context.consolidated_studies["open_access"]
    context.original_source = context.study.source

    # VERIFICAR precondiciones (garantiza que el estado es el correcto)
    assert context.study.doi is not None, \
        "El estudio debe tener DOI para verificar si es Open Access"
    assert context.study.consolidation_status == "completo", \
        "El estudio debe estar consolidado antes de intentar descargas"


@given('que un estudio no tiene acceso público en su fuente original')
def step_estudio_paywall(context):
    """
    Selecciona el estudio paywall de la lista creada en Background.

    GARANTIZA precondiciones verificables (NO es narrativo):
    - Tiene DOI (necesario para buscar en fuentes alternativas)
    - Está consolidado
    """
    context.study = context.consolidated_studies["paywall"]
    context.original_source = context.study.source

    # VERIFICAR precondiciones
    assert context.study.doi is not None, \
        "El estudio debe tener DOI para buscar en fuentes alternativas"
    assert context.study.consolidation_status == "completo", \
        "El estudio debe estar consolidado"


@given('que un estudio no pudo obtenerse automáticamente en ninguna fuente')
def step_estudio_failed_auto(context):
    """
    Selecciona el estudio failed de la lista creada en Background.

    GARANTIZA que el estudio está en estado de descarga fallida (NO es narrativo).
    """
    context.study = context.consolidated_studies["failed"]
    # WISHFUL THINKING: Atributo download_status en Study
    context.study.download_status = STATUS_NO_DISPONIBLE

    # VERIFICAR que realmente está marcado como fallido
    assert context.study.download_status == STATUS_NO_DISPONIBLE, \
        "El estudio debe tener estado de descarga fallida"


# ============================================================================
# WHEN - Acciones (igual que Feature 3: una sola acción por escenario)
# ============================================================================

@when('solicito obtener el documento')
def step_solicito_obtener(context):
    """
    Ejecuta el servicio de obtención de texto completo.

    El servicio internamente orquesta:
    1. Verificar si es Open Access
    2. Descargar desde fuente principal o alternativa
    3. Validar archivo
    4. Actualizar estado del estudio

    Esto es equivalente a 'solicito consolidar' en Feature 3.
    """
    # WISHFUL THINKING: Servicio de aplicación
    service = build_fulltext_service_with_mocks()
    context.result_study = service.obtain_fulltext(context.study)


@when('el sistema intenta obtener el texto completo')
def step_intenta_obtener(context):
    """Alias: Mismo comportamiento que 'solicito obtener el documento'."""
    context.execute_steps('Cuando solicito obtener el documento')


@when('cargo manualmente el archivo del texto completo')
def step_carga_manual(context):
    """
    Ejecuta el servicio de carga manual.

    El servicio internamente:
    1. Valida formato del archivo (magic bytes PDF)
    2. Vincula archivo al estudio
    3. Actualiza estado

    Esto es equivalente a 'ingreso manualmente metadatos' en Feature 3.
    """
    # WISHFUL THINKING: Servicio de aplicación
    service = build_manual_upload_service_with_mocks()

    context.result_study = service.attach_file(
        study=context.study,
        file_path=FAKE_UPLOADED_FILE,
    )


# ============================================================================
# THEN - Verificaciones de RESULTADOS (no de acciones)
# ============================================================================

@then('el sistema descarga automáticamente el archivo')
def step_descarga_automatica(context):
    """
    Verifica RESULTADO: El estudio tiene un archivo PDF asociado.

    Esto es equivalente a 'completa los metadatos faltantes' en Feature 3.
    """
    assert context.result_study.pdf_path is not None, \
        "El estudio no tiene pdf_path asignado"
    assert context.result_study.pdf_path.endswith(".pdf"), \
        f"El archivo no es PDF: {context.result_study.pdf_path}"


@then('valida la integridad del documento')
def step_valida_integridad(context):
    """
    Verifica RESULTADO: El archivo fue aceptado por el sistema.

    Evidencia implícita:
    - Si pdf_path existe, significa que FileValidator aprobó el archivo

    Esto es equivalente a 'normaliza los formatos' en Feature 3.
    """
    assert context.result_study.pdf_path is not None, \
        "No hay archivo vinculado; no se puede asumir validación"


@then('el estudio queda marcado como "{estado}"')
def step_verifica_estado(context, estado):
    """
    Verifica RESULTADO: El estudio tiene el estado correcto de descarga.

    Estados válidos:
    - texto_completo_disponible
    - no_disponible

    Esto es equivalente a 'queda marcado con su estado de consolidación' en Feature 3.
    """
    # WISHFUL THINKING: Atributo download_status en Study
    assert hasattr(context.result_study, 'download_status'), \
        "Study no tiene atributo download_status"

    expected = STATUS_DISPONIBLE if estado == "texto_completo_disponible" else estado

    assert context.result_study.download_status == expected, \
        f"Estado incorrecto. Esperado: {expected}, Actual: {context.result_study.download_status}"


@then('se registra el origen del texto como "{origen}"')
def step_verifica_origen(context, origen):
    """
    Verifica RESULTADO: El estudio tiene registrado el origen del PDF.

    Orígenes esperados:
    - automático
    - manual

    Esto es equivalente a 'se mantiene trazabilidad' en Feature 3.
    """
    # WISHFUL THINKING: Atributo pdf_source en Study
    assert hasattr(context.result_study, 'pdf_source'), \
        "Study no tiene atributo pdf_source"

    origin_map = {
        "automático": ORIGIN_AUTO,
        "manual": ORIGIN_MANUAL,
    }
    expected = origin_map.get(origen, origen)

    assert context.result_study.pdf_source == expected, \
        f"Origen incorrecto. Esperado: {expected}, Actual: {context.result_study.pdf_source}"


@then('si encuentra el documento en una fuente alternativa, lo descarga')
def step_descarga_alternativa(context):
    """
    Verifica RESULTADO: El PDF fue obtenido desde fuente alternativa.

    Evidencia:
    - Tiene pdf_path asignado
    """
    assert context.result_study.pdf_path is not None, \
        "No se obtuvo texto completo desde fuente alternativa"


@then('se registra desde qué fuente alternativa se obtuvo el texto')
def step_registra_fuente_alternativa(context):
    """
    Verifica RESULTADO: El origen indica que vino de una fuente alternativa.

    Evidencia:
    - pdf_source NO es la fuente original del estudio (Scopus, IEEE Xplore)
    - pdf_source indica origen alternativo
    """
    # WISHFUL THINKING: Atributo pdf_source en Study
    assert context.result_study.pdf_source is not None, \
        "No se registró la fuente del PDF"

    # Verificar que NO es la fuente original
    assert context.result_study.pdf_source not in ["Scopus", "IEEE Xplore"], \
        f"pdf_source '{context.result_study.pdf_source}' no debería ser la fuente original"

    # Verificar que es origen alternativo
    assert context.result_study.pdf_source == ORIGIN_ALTERNATIVO, \
        f"pdf_source debería ser '{ORIGIN_ALTERNATIVO}', es '{context.result_study.pdf_source}'"


@then('el sistema valida el formato e integridad del archivo')
def step_valida_formato_integridad(context):
    """
    Verifica RESULTADO: El archivo manual fue validado y aceptado.

    Evidencia:
    - Si attach_file completó sin excepción, FileValidator aprobó el archivo
    - pdf_path está asignado
    """
    assert context.result_study.pdf_path is not None, \
        "El archivo no fue aceptado (pdf_path es None)"


@then('vincula el documento al estudio correspondiente')
def step_vincula_documento(context):
    """
    Verifica RESULTADO: El archivo del usuario está vinculado al estudio.

    Evidencia:
    - pdf_path contiene el archivo subido
    """
    assert context.result_study.pdf_path is not None, \
        "No hay documento vinculado al estudio"
    assert FAKE_UPLOADED_FILE in context.result_study.pdf_path or \
           "usuario_paper.pdf" in context.result_study.pdf_path, \
        f"El documento vinculado no es el esperado: {context.result_study.pdf_path}"
