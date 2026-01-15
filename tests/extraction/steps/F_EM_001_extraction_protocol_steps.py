import json
from behave import *
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

# Modelos apps externas
from apps.project.structure.models.project_models import Project
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.shared.models.design_phase import DesignPhase
from apps.acquisition.models import StudyModel

#Modelos extraction
from apps.extraction.planning.models import ExtractionPhase, ExtractionStatusChoices
from apps.extraction.taxonomy.models import Tag, TagTypeChoices
from apps.extraction.core.models import PaperExtraction, PaperExtractionStatusChoices, Quote

# Importamos Servicios y DTOs
from apps.extraction.taxonomy.services import TagDefinitionService
from apps.extraction.core.services import PaperExtractionService
from apps.extraction.planning.services import PhaseLifecycleService

use_step_matcher("re")

User = get_user_model()
fake = Faker()


# ==============================================================================
# UTILIDADES
# ==============================================================================

def get_or_create_owner(context):
    """Obtiene o crea el usuario con rol de Owner."""
    if not hasattr(context, 'owner'):
        context.owner = User.objects.create_user(
            username=f'owner_{fake.user_name()}',
            email=fake.email(),
            password='password123'
        )
    return context.owner

def get_or_create_researcher(context):
    """Obtiene o crea el usuario con rol de Researcher."""
    if not hasattr(context, 'researcher'):
        context.researcher = User.objects.create_user(
            username=f'rsrch_{fake.user_name()}',
            email=fake.email(),
            password='password123'
        )
    return context.researcher

def setup_manual_project_context(context, stage=None):
    """
    Crea la jerarquía base: Owner -> Project -> DesignPhase.
    Guarda los objetos en 'context' para ser usados en los steps.
    """
    user = get_or_create_owner(context)

    if not hasattr(context, 'project'):
        context.project = Project.objects.create(
            title=fake.sentence(nb_words=5)[:99],
            summary=fake.paragraph(),
            motivation=fake.paragraph(),
            general_objective=fake.sentence(),
            owner=user
        )

    if not hasattr(context, 'design_phase'):
        initial_stage = stage if stage else DesignPhase.DesignStage.FINISHED
        
        context.design_phase = DesignPhase.objects.create(
            project=context.project,
            current_stage=initial_stage
        )
    
    return context.project, context.design_phase

def create_manual_rq(context, researcher=None, status='DRAFT'):
    """
    Crea una Research Question dentro de la DesignPhase actual.
    Requiere que setup_manual_project_context haya corrido antes.
    """
    if not researcher and hasattr(context, 'researcher'):
        researcher = context.researcher
        
    context.rq = ResearchQuestion.objects.create(
        design_phase=context.design_phase,
        question=fake.sentence(),
        researcher=researcher,
        status=status,
    )
    return context.rq

def create_manual_study(context):
    """
    Crea un Study asociado al proyecto actual.
    """
    if not hasattr(context, 'project'):
        setup_manual_project_context(context)

    context.study = StudyModel.objects.create(
        project=context.project,
        title=fake.sentence(),
        link=fake.url(),
        source=fake.word()
    )
    return context.study


def parse_list(text):
    """Convierte string '[A, B]' de Gherkin en lista Python."""
    try:
        # Reemplazamos comillas simples por dobles para JSON estándar
        return json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        return []


# ==============================================================================
# STEPS: ESCENARIO 1 - COBERTURA DE PROTOCOLO
# ==============================================================================

@step('que existe una Fase de Extracción en configuración')
def step_impl(context):
    setup_manual_project_context(context)
    
    context.phase = ExtractionPhase.objects.create(
        project=context.project,
        status=ExtractionStatusChoices.CONFIG
    )

@step("las Preguntas de Investigación del proyecto son: (?P<RQ_list>.+)")
def step_impl(context, RQ_list):
    rq_texts = parse_list(RQ_list)
    context.rq_map = {}

    for text in rq_texts:
        rq = ResearchQuestion.objects.create(
            design_phase=context.design_phase,
            question=text,
            status='APPROVED' 
        )
        context.rq_map[text] = rq.id


@step("el Owner define los Tags Deductivos y las PIs relacionadas: (?P<tag_list>.+)")
def step_impl(context, tag_list):
    tags_data = parse_list(tag_list)

    owner = get_or_create_owner(context)

    tag_service = TagDefinitionService()

    with transaction.atomic():
        for item in tags_data:
            tag_name = item.get("Tag")
            pi_text = item.get("PI")
            rq_id = context.rq_map.get(pi_text)
            tag_service.define_deductive_tag(
                phase_id=context.phase.id,
                name=tag_name,
                rq_id=rq_id,
                user=owner
            )


@step("se debe marcar el conjunto de tags obligatorios como: (?P<expected_tags>.+)")
def step_impl(context, expected_tags):
    expected_list = parse_list(expected_tags)
    mandatory_tags = context.phase.tags.mandatory().values_list('name', flat=True)
    assert set(mandatory_tags) == set(expected_list), \
        f"Esperado: {expected_list}, Obtenido: {list(mandatory_tags)}"


@step("el estado sugerido de la fase debe mantenerse en: (?P<expected_status>.+)")
def step_impl(context, expected_status):
    service = PhaseLifecycleService()
    coverage_report = service.get_protocol_coverage(context.phase)
    current_suggestion = "OPEN" if coverage_report.is_fully_covered else "CONFIG"
    assert current_suggestion == expected_status, \
        f"Sugerido: {current_suggestion}, Esperado: {expected_status}. Missing: {coverage_report.missing_rqs}"


# ==============================================================================
# STEPS: ESCENARIO 2 - VALIDACIÓN PAPER COMPLETO
# ==============================================================================

@step("una lista de tags obligatorios para la extracción: (?P<mandatory_tags>.+)")
def step_impl(context, mandatory_tags):
    tag_names = parse_list(mandatory_tags)
    user = get_or_create_context_user(context)

    # 1. Asegurar fase abierta si no existe (reutilizamos lógica si ya existe)
    if not hasattr(context, 'phase'):
        context.project = Project.objects.create(name="Proyecto Validation", status='ACTIVE')
        context.phase = ExtractionPhase.objects.create(
            project=context.project, status=ExtractionStatusChoices.OPEN
        )

    # 2. Crear Tags Obligatorios
    for name in tag_names:
        Tag.objects.create(
            extraction_phase=context.phase,
            name=name,
            is_mandatory=True,  # Forzamos para el test
            type=TagTypeChoices.DEDUCTIVE,
            visibility='PUBLIC',
            status='APROVED'
        )

    # 3. Crear el PaperExtraction (Aggregate Root para este escenario)
    context.study = Study.objects.create(
        title="Estudio de Prueba", authors="Test", project=context.project
    )
    context.paper = PaperExtraction.objects.create(
        study=context.study,
        extraction_phase=context.phase,
        status=PaperExtractionStatusChoices.PENDING,
        assigned_to=user
    )


@step("se han registrado las extracciones para los siguientes tags: (?P<extracted_tags>.+)")
def step_impl(context, extracted_tags):
    tag_names = parse_list(extracted_tags)
    user = get_or_create_context_user(context)

    # Obtener objetos Tag
    tags_objects = Tag.objects.filter(extraction_phase=context.phase, name__in=tag_names)

    if tags_objects.exists():
        # Crear una Quote que usa estos tags
        quote = Quote.objects.create(
            paper_extraction=context.paper,
            text_fragment="Texto simulado...",
            created_by=user
        )
        quote.tags.set(tags_objects)


@step('el investigador intenta marcar el paper como "Completo"')
def step_impl(context):
    # Instanciamos el Servicio de Dominio (Core)
    service = PaperExtractionService()
    user = get_or_create_context_user(context)

    # Ejecutamos la acción y guardamos el resultado en el contexto
    try:
        context.paper = service.attempt_complete_paper(context.paper, user)
        context.completion_success = True
        context.completion_error = None
    except Exception as e:
        context.completion_success = False
        context.completion_error = str(e)


@step("el estado del paper debe ser (?P<paper_status>.+)")
def step_impl(context, paper_status):
    status_map = {
        "Pendiente": PaperExtractionStatusChoices.PENDING,
        "Completo": PaperExtractionStatusChoices.COMPLETED
    }
    expected_db_status = status_map.get(paper_status)

    # Verificamos el estado en el DTO de respuesta
    assert context.completion_result.paper.status == expected_db_status, \
        f"Estado esperado {expected_db_status}, obtenido {context.completion_result.paper.status}"

    # Doble verificación: Consultar DB para asegurar consistencia
    context.paper.refresh_from_db()
    assert context.paper.status == expected_db_status


@step("se debe notificar al investigador sobre los tags pendientes: (?P<missing_tags>.+)")
def step_impl(context, missing_tags):
    expected_missing = parse_list(missing_tags)

    # Obtenemos los errores del DTO
    actual_missing = context.completion_result.errors

    # Comparamos listas (ordenadas para evitar falsos negativos)
    assert sorted(actual_missing) == sorted(expected_missing), \
        f"Se esperaban faltantes: {expected_missing}, se obtuvieron: {actual_missing}"