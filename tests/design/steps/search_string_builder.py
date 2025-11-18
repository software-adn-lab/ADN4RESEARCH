from behave import given, then, when, step
from faker import Faker
from unittest.mock import Mock
from django.contrib.auth.models import User
from apps.project.services.project_services import ProjectService
from apps.design.research_question.services.question_services import ResearchQuestionService
from apps.design.search_strategy.services.keyword_processor_service import KeywordProcessorService
from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
from apps.design.search_strategy.models.search_strategy import SearchStrategy
from apps.design.eligibility_criteria.services.eligibility_criterion_services import EligibilityCriterionService
import logging
import json
fake = Faker()

project_service = ProjectService()
research_question_service = ResearchQuestionService()
keyword_processor_service = KeywordProcessorService()
search_strategy_service = SearchStrategyService()
eligibility_service = EligibilityCriterionService()
acquisition_service = Mock()  


@given('que tengo la pregunta de investigación {pregunta_de_investigacion}')
def step_dado_tengo_pregunta_investigacion(context, pregunta_de_investigacion):
    project_framework = context.project.research_framework
    context.research_question = research_question_service.add_research_question(
        project_id=context.project.id,
        research_framework=project_framework,
        suggested_question=pregunta_de_investigacion,
        motivation="Motivación de prueba",
        researcher=context.researcher,
        framework_fields=fields
    )

@when('el sistema procesa la pregunta para sugerir términos clave')
def step_cuando_sistema_procesa_terminos_clave(context):
    # Llama a tu función y captura el objeto SearchStrategy devuelto
    keyword_processor_service.suggest_and_store_key_terms(
        context.research_question
    )
    strategy = SearchStrategy.objects.get(research_question=context.research_question)
    context.strategy = strategy
    assert context.strategy is not None

@given('que existe una pregunta de investigación en estado {estado}')
def step_dado_existe_pregunta_investigacion(context, estado):
    assert context.research_question.status == estado

@step('se han identificado los siguientes términos clave con sus sinónimos:')
def step_se_identifican_terminos_clave(context):
    context.strategy = SearchStrategy.objects.create(
            research_question=context.research_question,
            name="Estrategia para Generar String",
            status=SearchStrategy.Status.DRAFT
        )
    keyword_data_list = []
    for row in context.table:
        sinonimos_str = row['sinonimos'] if row['sinonimos'] else ""
        
        termino_clave_str = row['termino_clave'].strip('"')
        sinonimos_str = sinonimos_str.replace('"', '')

        keyword_data_list.append({
            'term': termino_clave_str,
            'synonyms': sinonimos_str
        })
    search_strategy_service.populate_strategy_keywords(
            strategy=context.strategy,
            keyword_data=keyword_data_list
        )
    logging.info(f"Keywords added to strategy {context.strategy.id}: {keyword_data_list}")
    
    assert context.strategy.keywords.count() == len(keyword_data_list)
    
@when('el sistema genere la sugerencia de estratégia de búsqueda')
def step_cuando_sistema_genere_estrategia_busqueda(context):
    context.search_string = search_strategy_service.generate_and_save_search_string(context.strategy)
    assert context.search_string is not None

@then('la estratégia de búsqueda sugerida será:')
def step_entonces_estrategia_sugerida_sera(context):
    expected_string = context.text
    actual_string = context.strategy.final_search_string
    normalized_expected = " ".join(expected_string.split())
    normalized_actual = " ".join(actual_string.split())
    assert normalized_actual == normalized_expected
    
@given('que he identificado los campos {framework_fields} del framework {framework}')
def step_dado_tengo_pregunta_investigacion(context, framework, framework_fields):
    print("framework_fields", framework_fields)
    fields = json.loads(framework_fields)
    context.research_question = research_question_service.add_research_question(
        project=context.project,
        research_framework=context.project.research_framework,
        suggested_question="¿Cuál es el impacto del desarrollo de software en la industria automotriz?",
        motivation="Motivación de prueba",
        researcher=context.researcher,
        framework_fields=fields
    )
    research_question_service.submit_research_question_for_review(research_question=context.research_question)
    assert context.research_question.status == context.research_question.Status.SUGGESTED
    
@step('el sistema procesa las oraciones para sugerir términos clave')
def step_cuando_sistema_procesa_oraciones(context):
    # Llama a tu función y captura el objeto SearchStrategy devuelto
    keyword_processor_service.suggest_and_store_key_terms(research_question=context.research_question)
    strategy = SearchStrategy.objects.get(research_question=context.research_question)
    context.strategy = strategy
    assert context.strategy is not None
    
@then('la lista de términos clave sugeridos debe contener {expected_terms}')
def step_entonces_lista_terminos_clave(context, expected_terms):
    #evitar duplicados
    expected_terms_list = list(set(expected_terms.split(',')))
    key_word_stored = keyword_processor_service.get_keywords_for_strategy(context.strategy)
    assert set(expected_terms_list) == set(key_word_stored)