from behave import given, then, when, step
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.shared.models.design_phase import DesignPhase
import logging
import json
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
    context.strategy = search_strategy_service.generate_and_save_search_string(context.strategy.id)
    assert context.strategy.final_search_string is not None

@then('la estratégia de búsqueda sugerida será:')
def step_entonces_estrategia_sugerida_sera(context):
    expected_string = context.text
    actual_string = context.strategy.final_search_string
    normalized_expected = " ".join(expected_string.split())
    normalized_actual = " ".join(actual_string.split())
    assert normalized_expected == normalized_actual