from apps.design.research_question.models.research_question import ResearchQuestion
import spacy
import logging
from spacy.matcher import Matcher

from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
logger = logging.getLogger(__name__)

class KeywordProcessorService:
    PATTERNS = [
    ["NOUN", "ADJ"],       # e.g., "industria automotriz"
    ["NOUN", "ADP", "NOUN"], # e.g., "desarrollo de software"
    ["NOUN", "NOUN"],      # e.g., "coche bomba"
    ["NOUN"] # e.g., "desarrollo"
    ]
    try:
        # spacy install es_core_news_sm
        nlp = spacy.load("es_core_news_sm")
    except IOError:
        nlp = None
    search_strategy_service = SearchStrategyService()
        
    def process_key_terms(self, sentence: str) -> list[str]:
        if self.nlp is None:
            logger.error("El modelo de spaCy no está cargado.")
            return []

        doc = self.nlp(sentence)
        matcher = Matcher(self.nlp.vocab)
        for idx, pattern in enumerate(self.PATTERNS):
            spacy_pattern = [{'POS': pos_tag} for pos_tag in pattern]
            matcher.add(f"PATTERN_{idx}", [spacy_pattern])

        matches = matcher(doc)
        phrases = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            if span.text.strip():
                phrases.add(span.text.lower())
        return list(phrases)
    
    def suggest_and_store_key_terms(self, research_question_id:int):
        research_question = ResearchQuestion.objects.get(id=research_question_id)
        suggested_terms = set()
        for field_value in research_question.framework_fields.values():
            if field_value and field_value.strip():  
                terms_from_field = self.process_key_terms(field_value)
                suggested_terms.update(terms_from_field)
        strategy = self.search_strategy_service.sync_suggested_terms_with_strategy(
            research_question_id=research_question_id,
            suggested_terms=list(suggested_terms)
        )
        return strategy