import logging
from googletrans import Translator
from asgiref.sync import async_to_sync

class TranslationService:
    def translate_json_definition(self, json_definition: dict) -> dict:
        """
        Translates the terms and synonyms in the JSON definition from Spanish to English.
        Uses async_to_sync to handle the asynchronous googletrans library.
        """
        async def _do_translate():
            translator = Translator()
            translated_main_terms = []
            
            # Translate main terms
            for item in json_definition.get('main_terms', []):
                term = item.get('term', '')
                synonyms = item.get('synonyms', [])
                
                translated_term = term
                if term:
                    try:
                        t = await translator.translate(term, src='es', dest='en')
                        translated_term = t.text
                    except Exception as e:
                        logging.error(f"Error translating term '{term}': {e}")
                
                translated_synonyms = []
                for syn in synonyms:
                    try:
                        t = await translator.translate(syn, src='es', dest='en')
                        translated_synonyms.append(t.text)
                    except Exception as e:
                        logging.error(f"Error translating synonym '{syn}': {e}")
                        translated_synonyms.append(syn)
                
                translated_main_terms.append({
                    "term": translated_term,
                    "synonyms": translated_synonyms
                })
            
            # Translate exclusions
            translated_exclusions = []
            for exc in json_definition.get('exclusions', []):
                try:
                    t = await translator.translate(exc, src='es', dest='en')
                    translated_exclusions.append(t.text)
                except Exception as e:
                    logging.error(f"Error translating exclusion '{exc}': {e}")
                    translated_exclusions.append(exc)
            
            return {
                "main_terms": translated_main_terms,
                "exclusions": translated_exclusions
            }

        return async_to_sync(_do_translate)()
