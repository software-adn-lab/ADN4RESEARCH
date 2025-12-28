from behave import given, then, when, step
from django.contrib.auth.models import User
from apps.design.search_strategy.services.nlp.keyword_processor_service import KeywordProcessorService
from apps.project.structure.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService

from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.search_strategy.models.search_strategy import SearchStrategy
import logging
import json
from unittest.mock import patch, MagicMock

project_service = ProjectService()
research_question_service = ResearchQuestionService()
keyword_processor_service = KeywordProcessorService()
search_strategy_service = SearchStrategyService()

@given('que he creado la "{pregunta_investigacion}" con los siguientes campos {framework_fields}')
def step_dado_creo_pregunta_investigacion(context, pregunta_investigacion, framework_fields):
    fields = json.loads(framework_fields)
    context.research_question = research_question_service.add_research_question(
        project_id=context.project.id,
        question=pregunta_investigacion,
        researcher_id=context.researcher.id,
        motivation="Motivación de prueba",
        framework_fields=fields
    )
    assert context.research_question is not None

@when('el sistema procesa los campos del framework de la pregunta para sugerir términos clave')
def step_cuando_sistema_procesa_campos_framework_pregunta(context):
    keyword_processor_service.suggest_and_store_key_terms(research_question_id=context.research_question.id)


@then('la lista de términos clave del proyecto debe contener {expected_terms}')
def step_entonces_lista_terminos_clave(context, expected_terms):
    expected_terms_list = list(set(expected_terms.split(',')))
    project_keywords = project_service.get_project_keyterms(context.project.id)
    project_keyword_list = {kw.term for kw in project_keywords}
    logging.info(f"Expected terms: {expected_terms_list}")
    logging.info(f"Project keywords: {project_keyword_list}")
    assert set(expected_terms_list) == set(project_keyword_list)

@step('he identificado los sinónimos de los términos clave:')
def step_se_identifican_terminos_clave_con_sinonimos(context):
    keyword_data_list = []
    for row in context.table:
        sinonimos_str = row['sinonimos']
        termino_clave_str = row['termino_clave'].strip('"')
        keyword_data_list.append({
            'term': termino_clave_str,
            'synonyms': sinonimos_str
        })
    context.strategy = search_strategy_service.create_or_update_strategy_with_keywords(
        research_question_id=context.research_question.id,
        keyword_data=keyword_data_list,
        user=context.researcher
    )
    assert context.strategy.keywords.count() == len(keyword_data_list)


@when('el sistema genere la sugerencia de estratégia de búsqueda')
def step_cuando_sistema_genere_estrategia_busqueda(context):
    context.strategy = search_strategy_service.generate_and_save_search_string(context.strategy.id, context.researcher.id)
    assert context.strategy.final_search_string is not None

@then('la estratégia de búsqueda sugerida será:')
def step_entonces_estrategia_sugerida_sera(context):
    expected_string = context.text
    actual_string = context.strategy.final_search_string
    normalized_expected = " ".join(expected_string.split())
    normalized_actual = " ".join(actual_string.split())
    logging.info(f"Expected search string: {normalized_expected}")
    logging.info(f"Actual search string: {normalized_actual}")
    assert normalized_expected == normalized_actual

@given('que selecciono una pregunta de investigación del protocolo de diseño del proyecto')
def step_selecciono_pregunta_investigacion(context):
    context.research_question = research_question_service.add_research_question(
        project_id=context.project.id,
        question="Protocol Question?",
        researcher_id=context.researcher.id,
        motivation="Default Motivation",
        framework_fields={"Population": "Test", "Intervention": "Test", "Comparison": "Test", "Outcome": "Test"}
    )
    context.research_question.status = "APPROVED"
    context.research_question.save()
    assert context.research_question is not None
    assert context.research_question in context.project.protocol_questions


@step('que tengo la lista de términos clave y sinónimos de dicha pregunta')
def step_tengo_lista_terminos_sinonimos(context):
    keyword_data = [
        {'term': 'Term1', 'synonyms': 'Syn1, Syn2'},
        {'term': 'Term2', 'synonyms': ''}
    ]
    context.strategy = search_strategy_service.create_or_update_strategy_with_keywords(
        research_question_id=context.research_question.id,
        keyword_data=keyword_data,
        user=context.researcher
    )


@when('pruebo la cadena de búsqueda que he construido')
def step_pruebo_cadena_busqueda(context):
    # Suponiendo el drag and drop jeje
    context.visual_data = {
        "main_terms": [
            {"term": "Term1", "synonyms": ["Syn1", "Syn2"]},
            {"term": "Term2", "synonyms": []}
        ],
        "exclusions": []
    }
    mock_facade = MagicMock()
    mock_facade.preview_search.return_value = MagicMock(total_found=150)

@step('el sistema traduce la cadena de búsqueda a inglés')
def step_sistema_traduce_cadena(context):
    # Este paso se pasa porque estara dentro del paso anterior ya que la traduccion es dentro del save_strategy_from_visual_builder
    pass

@then('se recibirán resultados de dicha búsqueda desde el módulo de adquisición')
def step_recibiran_resultados_adquisicion(context):
    with patch('apps.design.search_strategy.services.search_strategy_service.get_acquisition_facade') as mock_get_facade:
        mock_facade = MagicMock()
        mock_facade.preview_search.return_value = MagicMock(total_found=150)
        mock_get_facade.return_value = mock_facade

        context.strategy = search_strategy_service.save_strategy_from_visual_builder(
            strategy_id=context.strategy.id,
            visual_data=context.visual_data,
            user_id=context.researcher.id
        )
        mock_facade.preview_search.assert_called_once()
        context.search_results_count = 150

@step('se creará una versión borrador de la estratégia de busqueda')
def step_creara_version_borrador(context):
    strategy = SearchStrategy.objects.get(id=context.strategy.id)
    assert strategy.status == SearchStrategy.Status.DRAFT
    latest_version = strategy.versions.latest('created_at')  # esto para el memento/snapshot que cree
    assert latest_version.total_found == 150
    assert latest_version.version_number > 0