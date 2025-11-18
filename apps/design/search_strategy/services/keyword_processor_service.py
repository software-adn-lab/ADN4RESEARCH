from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.keyword import Keyword, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy
import spacy
from typing import List

class KeywordProcessorService:
    PATTERNS = [
    ["NOUN", "ADJ"],       # e.g., "industria automotriz"
    ["NOUN", "ADP", "NOUN"], # e.g., "desarrollo de software"
    ["NOUN", "NOUN"],      # e.g., "coche bomba"
    ["NOUN"]
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
    
    def suggest_and_store_key_terms(self, research_question: ResearchQuestion):
        if not research_question.suggested_question or not research_question.suggested_question.strip():
            SearchStrategy.objects.filter(research_question=research_question).delete()
            return

        project = research_question.project
        suggested_terms = self.process_key_terms(research_question.suggested_question)

        # 1. Busca la estrategia para esta pregunta; si no existe, la crea. Es idempotente.
        strategy, created = SearchStrategy.objects.update_or_create(
            research_question=research_question,
            defaults={
                'name': f"Suggested Strategy for RQ-{research_question.id}",
                'status': SearchStrategy.Status.DRAFT
            }
        )

        # 2. Antes de añadir nuevas keywords, elimina las que ya estaban asociadas a ESTA estrategia.
        strategy.keywords.all().delete()

        keywords_to_link = []
        for term in suggested_terms:
            project_keyword, created = ProjectKeyword.objects.get_or_create(
                project=project,
                term=term
            )
            keywords_to_link.append(
                Keyword(strategy=strategy, project_keyword=project_keyword)
            )
        
        if keywords_to_link:
            Keyword.objects.bulk_create(keywords_to_link)
            
    
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