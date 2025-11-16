from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.keyword import Keyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy
import spacy
from typing import List

class KeywordProcessorService:
    PATTERNS = [
    ["NOUN", "ADJ"],       # e.g., "industria automotriz"
    ["NOUN", "ADP", "NOUN"], # e.g., "desarrollo de software"
    ["NOUN", "NOUN"],      # e.g., "coche bomba"
    ]
    try:
        nlp = spacy.load("es_core_news_sm")
    except IOError:
        nlp = None
        
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
    
    def suggest_and_store_key_terms(self, research_question: ResearchQuestion) -> SearchStrategy:

        # 1. Obtener la lista de strings (como ya tenías)
        suggested_terms = self.process_key_terms(research_question.suggested_question)
        # 2. Crear el objeto "contenedor" principal
        new_strategy = SearchStrategy.objects.create(
            research_question=research_question,
            name="Estrategia Sugerida (v1)", # Puedes hacer este nombre más dinámico
            status=SearchStrategy.Status.DRAFT
        )
        # 3. Preparar los objetos Keyword para la base de datos
        keywords_to_create = [
            Keyword(
                strategy=new_strategy,
                term=term,
                synonyms=""  # Se deja vacío para llenado manual, como definimos
            )
            for term in suggested_terms
        ]
        
        if keywords_to_create:
            Keyword.objects.bulk_create(keywords_to_create)
        return new_strategy
    
    def get_keywords_for_strategy(self, strategy: SearchStrategy) -> List[str]:
        """
        Retorna una lista de términos clave asociados a una estrategia de búsqueda dada.
        """
        keywords = Keyword.objects.filter(strategy=strategy)
        return [kw.term for kw in keywords]