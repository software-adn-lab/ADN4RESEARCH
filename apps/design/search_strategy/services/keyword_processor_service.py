from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy
import spacy
import logging
from typing import List

from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService

class KeywordProcessorService:
    PATTERNS = [
    ["NOUN", "ADJ"],       # e.g., "industria automotriz"
    ["NOUN", "ADP", "NOUN"], # e.g., "desarrollo de software"
    ["NOUN", "NOUN"],      # e.g., "coche bomba"
    #["NOUN"] # e.g., "desarrollo"
    ]
    try:
        nlp = spacy.load("es_core_news_sm")
    except IOError:
        nlp = None
    
    search_strategy_service = SearchStrategyService()
        
    def process_key_terms(self, sentence: str) -> List[str]:
        """
        Extrae términos clave basados en sustantivos utilizando la librería spaCy.
        """
        if self.nlp is None:
            return ["Error: El modelo de spaCy no está cargado."]

        doc = self.nlp(sentence)
        phrases = set() # Usar un set para evitar duplicados
        for sent in doc.sents:
            num_tokens = len(sent) 
            for i in range(num_tokens):
                for pattern in self.PATTERNS:
                    if i + len(pattern) <= num_tokens:
                        sequence_to_check = sent[i : i + len(pattern)]
                        upos_sequence = [token.pos_ for token in sequence_to_check]
                        
                        if upos_sequence == pattern:
                            phrase_text = sequence_to_check.text
                            phrases.add(phrase_text.lower())
                            
        return list(phrases)
    
    def suggest_and_store_key_terms(self, research_question_id:int):
        research_question = ResearchQuestion.objects.get(id=research_question_id)
        question_framework_fields_complete = research_question.framework_fields
        # 1. Procesar cada campo del framework para extraer términos clave
        suggested_terms = set()
        for field_value in research_question.framework_fields.values():
            if field_value and field_value.strip():  # Solo procesar si el campo tiene contenido
                terms_from_field = self.process_key_terms(field_value)
                suggested_terms.update(terms_from_field)
        # 2. Delegar la creación/sincronización de la estrategia al servicio correcto.
        strategy = self.search_strategy_service.sync_suggested_terms_with_strategy(
            research_question_id=research_question_id,
            suggested_terms=list(suggested_terms)
        )
        return strategy
    
    def get_keywords_for_strategy(self, strategy: SearchStrategy) -> List[str]:
        """
        Retorna una lista de términos clave asociados a una estrategia de búsqueda dada.
        """
        keywords = Keyword.objects.filter(strategy=strategy).select_related('project_keyword')
        return [kw.project_keyword.term for kw in keywords]
    
    def get_keywords_for_questions(self, questions: List[ResearchQuestion]):
        """
        Dada una lista de preguntas de investigación, retorna los términos clave asociados a ellas.
        """
        # Devuelve los ProjectKeyword únicos asociados a las preguntas.
        return ProjectKeyword.objects.filter(keyword__strategy__research_question__in=questions).distinct()

    def get_project_keywords(self, project):
        """
        Obtiene todos los ProjectKeyword ("banco de términos") para un proyecto específico.
        """
        return ProjectKeyword.objects.filter(project=project).order_by('term')