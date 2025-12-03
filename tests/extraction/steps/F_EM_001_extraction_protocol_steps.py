"""
Step definitions for F_EM_001-Extraction_Protocol.feature
"""
import json
from behave import given, when, then, step

use_step_matcher("re")


# =============================================================================
# ANTECEDENTES
# =============================================================================

@step("que la fase de extracción está activa")
def step_extraction_phase_active(context):
    """
    Precondición: La fase de extracción está activa.
    En este mock, simplemente asumimos que está activa.
    """
    from apps.extraction.external.services import ProjectService
    
    stage = ProjectService.get_current_stage(context.project_id)
    assert stage is not None, "No hay fase activa"
    assert stage['name'] == 'EXTRACTION', f"Se esperaba fase EXTRACTION, pero es {stage['name']}"
    assert stage['status'] == 'OPENED', f"La fase no está abierta: {stage['status']}"


# =============================================================================
# ESCENARIO 1: Tags Deductivos y Visibilidad
# =============================================================================

@step("las Preguntas de Investigación del proyecto son: (?P<PIs_Existentes>.+)")
def step_define_research_questions(context, PIs_Existentes):
    """
    Define las Preguntas de Investigación del proyecto.
    El mock de DesignService retorna PIs predefinidas, pero aquí las parseamos
    para validar el escenario.
    """
    # Parsear las PIs del feature
    pis_list = json.loads(PIs_Existentes)
    
    # Guardar en context para uso posterior
    context.expected_pis = pis_list
    context.pi_map = {}
    
    # Crear mapeo de texto a ID (simulado)
    for idx, pi_text in enumerate(pis_list, start=101):
        context.pi_map[pi_text] = idx


@step("el Owner define los Tags Deductivos y las PIs relacionadas: (?P<Tags_Definidos>.+)")
def step_owner_defines_tags(context, Tags_Definidos):
    """
    El Owner crea tags y los vincula (o no) a PIs.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    tags_data = json.loads(Tags_Definidos)
    
    context.created_tags = []
    
    for tag_def in tags_data:
        tag_name = tag_def['Tag']
        pi_relacionada = tag_def['PI_Relacionada']
        
        # Determinar question_id
        if pi_relacionada == '<Ninguna>':
            question_id = None
        else:
            # Buscar el ID de la PI en el mapeo
            question_id = context.pi_map.get(pi_relacionada)
        
        # Crear el tag
        tag = service.create_tag(
            project_id=context.project_id,
            name=tag_name,
            question_id=question_id,
            user_id=1  # Owner ID
        )
        context.created_tags.append(tag)
        context.tags[tag_name] = tag


@step("se debe marcar el conjunto de tags obligatorios como: (?P<Tags_Obligatorios_Esperados>.+)")
def step_verify_mandatory_tags(context, Tags_Obligatorios_Esperados):
    """
    Verifica que los tags obligatorios sean los esperados.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    
    # Parsear lista esperada
    expected_names = json.loads(Tags_Obligatorios_Esperados)
    
    # Obtener tags obligatorios reales
    mandatory_tags = service.get_mandatory_tag_names(context.project_id)
    
    # Verificar
    assert set(mandatory_tags) == set(expected_names), \
        f"Tags obligatorios esperados: {expected_names}, obtenidos: {mandatory_tags}"


@step("se debe determinar la visibilidad de la lista de tags para los Researchers como: (?P<Visibilidad_Esperada>.+)")
def step_verify_visibility(context, Visibilidad_Esperada):
    """
    Verifica la visibilidad de la lista de tags.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    
    # Obtener estado de configuración
    status = service.get_tag_configuration_status(context.project_id)
    
    # Normalizar valores (quitar comillas si las hay)
    expected = Visibilidad_Esperada.strip('"').strip()
    actual = status['visibility']
    
    assert actual == expected, \
        f"Visibilidad esperada: '{expected}', obtenida: '{actual}'"


# =============================================================================
# ESCENARIO 2: Validar completitud de extracción
# =============================================================================

@step("una lista de tags obligatorios para la extracción: (?P<Tags_Obligatorios>.+)")
def step_setup_mandatory_tags(context, Tags_Obligatorios):
    """
    Configura los tags obligatorios para el escenario.
    Crea tags vinculados a PIs ficticias para que sean obligatorios.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    
    # Parsear lista de tags obligatorios
    tag_names = json.loads(Tags_Obligatorios)
    
    # Crear cada tag como obligatorio (vinculado a una PI)
    for idx, name in enumerate(tag_names, start=101):
        tag = service.create_tag(
            project_id=context.project_id,
            name=name,
            question_id=idx,  # PI ficticia
            user_id=1
        )
        context.tags[name] = tag


@step("se han registrado las extracciones para los siguientes tags: (?P<Tags_Extraidos>.+)")
def step_register_extractions(context, Tags_Extraidos):
    """
    Registra extracciones (quotes) con los tags indicados.
    """
    from apps.extraction.core.models import PaperExtraction, Quote
    from apps.extraction.taxonomy.models import Tag
    
    # Parsear tags extraídos
    extracted_tag_names = json.loads(Tags_Extraidos)
    
    # Crear una extracción de prueba
    extraction = PaperExtraction.objects.create(
        study_id=1,
        project_id=context.project_id,
        assigned_to_id=2  # Researcher ID
    )
    context.current_extraction = extraction
    
    # Crear quotes con los tags indicados
    for tag_name in extracted_tag_names:
        tag = context.tags.get(tag_name)
        if tag:
            quote = Quote.objects.create(
                paper_extraction=extraction,
                text_portion=f"Cita de prueba para {tag_name}",
                researcher_id=2
            )
            quote.tags.add(tag)
            context.quotes[tag_name] = quote


@step('el investigador intenta marcar el paper como "Completo"')
def step_attempt_complete(context):
    """
    El investigador intenta marcar la extracción como completada.
    """
    from apps.extraction.core.services import ExtractionService
    from apps.extraction.shared.exceptions import BusinessRuleViolation
    
    service = ExtractionService()
    
    try:
        result = service.complete_extraction(
            extraction_id=context.current_extraction.id,
            user_id=2  # Researcher ID
        )
        context.last_result = result
        context.last_error = None
    except BusinessRuleViolation as e:
        context.last_error = str(e)
        context.last_result = None


@step('el estado del paper debe ser "(?P<Estado_Esperado>.+)"')
def step_verify_paper_status(context, Estado_Esperado):
    """
    Verifica el estado del paper después del intento de completar.
    """
    from apps.extraction.core.models import PaperExtraction, ExtractionStatus
    
    # Refrescar el objeto desde la BD
    extraction = PaperExtraction.objects.get(id=context.current_extraction.id)
    
    # Mapear estado esperado
    status_map = {
        'Pendiente': ExtractionStatus.PENDING,
        'Completo': ExtractionStatus.DONE,
        'En Progreso': ExtractionStatus.IN_PROGRESS
    }
    
    expected_status = status_map.get(Estado_Esperado)
    
    assert extraction.status == expected_status, \
        f"Estado esperado: {Estado_Esperado} ({expected_status}), obtenido: {extraction.status}"


@step("se debe notificar al investigador sobre los tags pendientes: (?P<Tags_Pendientes_Esperados>.+)")
def step_verify_pending_notification(context, Tags_Pendientes_Esperados):
    """
    Verifica que se notifique al investigador sobre los tags faltantes.
    """
    from apps.extraction.core.services import ExtractionService
    
    service = ExtractionService()
    
    # Parsear tags pendientes esperados
    expected_pending = json.loads(Tags_Pendientes_Esperados)
    
    # Obtener progreso real
    progress = service.get_extraction_progress(context.current_extraction.id)
    actual_missing = progress.get('missing_tags', [])
    
    # Verificar
    assert set(actual_missing) == set(expected_pending), \
        f"Tags pendientes esperados: {expected_pending}, obtenidos: {actual_missing}"
