from apps.design.research_question.models.research_question import ResearchQuestion
import spacy
import logging
from spacy.matcher import Matcher

from apps.design.search_strategy.services.search_strategy_service import SearchStrategyService
logger = logging.getLogger(__name__)

class KeywordProcessorService:
    PATTERNS = [
        [{"POS": "NOUN"}, {"POS": "ADJ"}],              # e.g., "industria automotriz"
        [{"POS": "NOUN"}, {"POS": "ADP"}, {"POS": "NOUN"}], # e.g., "desarrollo de software"
        [{"POS": "NOUN"}, {"POS": "NOUN"}],             # e.g., "coche bomba"
        [{"POS": "PROPN"}],                             # e.g., "Python", "Django" (Nombres propios)
        # [{"POS": "NOUN"}]                             # e.g., "desarrollo" (Opcional, puede generar ruido)
    ]
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.search_strategy_service = SearchStrategyService()
        self._initialize_spacy()

    def _initialize_spacy(self):
        try:
            if not spacy.util.is_package("es_core_news_sm"):
                logger.warning("The model 'es_core_news_sm' is not installed.")
                return
            self.nlp = spacy.load("es_core_news_sm")
            self.matcher = Matcher(self.nlp.vocab)
            for idx, pattern in enumerate(self.PATTERNS):
                self.matcher.add(f"KEYWORD_PATTERN_{idx}", [pattern])   
        except Exception as e:
            logger.error(f"Error while loading spaCy model: {e}")
            self.nlp = None
        
    def process_key_terms(self, text: str) -> list[str]:
        if not self.nlp or not self.matcher or not text:
            return []
        doc = self.nlp(text)
        matches = self.matcher(doc)
        phrases = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            clean_term = span.text.strip().lower()
            if len(clean_term) > 2:
                phrases.add(clean_term)
                
        return list(phrases)
    
    def suggest_and_store_key_terms(self, research_question_id: int):
        try:
            research_question = ResearchQuestion.objects.get(id=research_question_id)
        except ResearchQuestion.DoesNotExist:
            logger.error(f"ResearchQuestion {research_question_id} not found during keyword processing.")
            return None

        suggested_terms = set()
        for field_key, field_value in research_question.framework_fields.items():
            if field_value and isinstance(field_value, str) and field_value.strip():
                terms_from_field = self.process_key_terms(field_value)
                suggested_terms.update(terms_from_field)
        strategy = self.search_strategy_service.sync_suggested_terms_with_strategy(
            research_question_id=research_question_id,
            suggested_terms=list(suggested_terms)
        )
        return strategy