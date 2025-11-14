"""Flexible LLM client implementations and mocks for InterpretationService.

This module defines a small interface and a couple of implementations:
- LLMClient: abstract interface
- DefaultLLMClient: placeholder implementation (no external calls)
- MockLLMClient: deterministic mock useful for tests

You can add adapters here for OpenAI, Anthropic, local LLMs, etc., following
the same interface.
"""
from typing import Dict
import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


class LLMClient:
    """Interface for LLM clients used by InterpretationService."""

    def generate_opening_message(self, subtheme) -> Dict[str, str]:
        raise NotImplementedError()

    def generate_draft_proposition(self, context, instruction) -> str:
        raise NotImplementedError()

    def generate_refined_proposition(self, original_text: str, refinement_instruction: str) -> str:
        raise NotImplementedError()
    
    def propose_code_normalization(self, codes_data: list) -> list:
        """Propose normalization of initial codes by merging similar ones."""
        raise NotImplementedError()
    
    def propose_theme_structure(self, codes_data: list) -> list:
        """Propose high-level theme structure from normalized codes."""
        raise NotImplementedError()


class DefaultLLMClient(LLMClient):
    """Default placeholder client used when no real LLM is configured.

    Returns deterministic, human-readable placeholders. Safe for tests
    that don't need external network calls.
    """

    def generate_opening_message(self, subtheme):
        # Generate tags from theme, subtheme, and central codes
        tag_list = []

        if hasattr(subtheme, "theme") and subtheme.theme:
            theme_tag = subtheme.theme.name.lower().replace(" ", "_")
            tag_list.append(theme_tag)

        if hasattr(subtheme, "name") and subtheme.name:
            # Extract key words from subtheme name
            subtheme_words = [
                word.lower().replace(":", "").strip()
                for word in subtheme.name.split()
                if len(word) > 3 and word.lower() not in ["subtema", "retos", "tema"]
            ]
            tag_list.extend(subtheme_words[:2])  # Add first 2 relevant words

        # Add a tag from central codes if available
        if hasattr(subtheme, "central_codes") and subtheme.central_codes:
            # Use first central code as a tag (simplified)
            first_code = subtheme.central_codes[0].lower().replace(" ", "_")
            # Extract main concept (first word if multi-word)
            code_tag = first_code.split("_")[0] if "_" in first_code else first_code
            if code_tag not in tag_list:
                tag_list.append(code_tag)

        tags = ", ".join(tag_list) if tag_list else "interpretation"

        body = (
            f"Asistiendo en la interpretación del Subtema: {getattr(subtheme, 'name', 'Subtema')}. "
            f"Este subtema está relacionado con el tema principal '{getattr(subtheme.theme, 'name', '')}'. "
            f"Los códigos centrales identificados son: {', '.join(getattr(subtheme, 'central_codes', []))}. "
            f"¿Cuál es la proposición preliminar o enfoque deseado?"
        )

        return {"title": "Apertura conversacional del Copilot", "body": body, "tags": tags}

    def generate_draft_proposition(self, context, instruction) -> str:
        # Simple deterministic draft for testing/development
        return (
            "La principal barrera organizacional es la disrupción de la colaboración "
            "sincrónica causada por la dependencia de zonas horarias, lo que se traduce "
            "en un retraso crítico en los bucles de feedback de DevOps."
        )

    def generate_refined_proposition(self, original_text: str, refinement_instruction: str) -> str:
        # Deterministic refinement placeholder
        return (
            "La principal barrera organizacional identificada es la disrupción de la "
            "comunicación asíncrona necesaria para DevOps, causada por la dependencia "
            "de zonas horarias geográficamente distribuidas, resultando en retrasos "
            "críticos en los bucles de feedback según el marco teórico de la SLR."
        )
    
    def propose_code_normalization(self, codes_data: list) -> list:
        """Propose normalization of initial codes - deterministic placeholder."""
        # Group similar codes for demonstration
        proposals = []
        
        # Merge repository mining codes
        if any(c['code'] in ['#repository_mining', '#github'] for c in codes_data):
            proposals.append({
                'normalized_code': '#extracción_de_repositorios_SWH',
                'original_codes': ['#repository_mining', '#github'],
                'rationale': 'Ambos códigos se refieren al proceso de extracción de datos de repositorios.'
            })
        
        # Merge qualitative method codes
        if any(c['code'] in ['#qualitative_method', '#thematic_analysis'] for c in codes_data):
            proposals.append({
                'normalized_code': '#análisis_temático_cualitativo',
                'original_codes': ['#qualitative_method', '#thematic_analysis'],
                'rationale': 'Estos códigos describen métodos cualitativos relacionados.'
            })
        
        # Merge inheritance-related codes
        if any(c['code'] in ['#vague_inheritance', '#inherited_debt'] for c in codes_data):
            proposals.append({
                'normalized_code': '#deuda_heredada_de_framework',
                'original_codes': ['#vague_inheritance', '#inherited_debt'],
                'rationale': 'Ambos códigos se relacionan con problemas de herencia y deuda técnica.'
            })
        
        return proposals
    
    def propose_theme_structure(self, codes_data: list) -> list:
        """Propose Level 1 theme structure - deterministic placeholder."""
        # Group codes by RQ focus
        rq1_codes = [c for c in codes_data if c.get('rq_focus', '').startswith('RQ1')]
        rq2_codes = [c for c in codes_data if c.get('rq_focus', '').startswith('RQ2')]
        
        proposals = []
        
        if rq1_codes:
            proposals.append({
                'theme_name': 'Métodos de Descubrimiento de Anti-Patrones',
                'description': 'Técnicas y metodologías para identificar anti-patrones en software',
                'rq_focus': 'RQ1',
                'codes': [c['code'] for c in rq1_codes],
                'subthemes': [],  # Level 1: No subthemes
                'rationale': 'Agrupa los códigos relacionados con métodos de identificación'
            })
        
        if rq2_codes:
            proposals.append({
                'theme_name': 'Factores Determinantes de Anti-Patrones',
                'description': 'Factores que causan o contribuyen a la aparición de anti-patrones',
                'rq_focus': 'RQ2',
                'codes': [c['code'] for c in rq2_codes],
                'subthemes': [],  # Level 1: No subthemes
                'rationale': 'Agrupa los códigos relacionados con causas de anti-patrones'
            })
        
        return proposals


class GeminiLLMClient(LLMClient):
    """Adapter to Google Gemini (Google Generative AI).

    This implementation expects the environment variable `GEMINI_API_KEY` to be set
    (or you can pass api_key to the constructor) and optionally `GEMINI_MODEL` for
    the model name (defaults to a sensible value). It tries to import
    `google.generativeai` and raises a helpful error if it's not installed.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.genai = genai
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")

        # Configure the client
        try:
            # The library exposes a configure helper
            self.genai.configure(api_key=key)
        except Exception:
            # Some versions might require a different call; try setting env as fallback
            os.environ.setdefault("GOOGLE_API_KEY", key)

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.0")

    def _generate(self, prompt: str, max_output_tokens: int = 512) -> str:
        # Use the generate_text API; wrap errors into RuntimeError to keep service layering simple
        try:
            resp = self.genai.generate_text(model=self.model, prompt=prompt, max_output_tokens=max_output_tokens)
            # The response object typically has a `text` attribute
            text = getattr(resp, "text", None) or resp.get("output", {}).get("text") if isinstance(resp, dict) else None
            if not text:
                # Fallback: try stringifying the whole response
                text = str(resp)
            return text
        except Exception as e:
            logger.exception("Error calling Gemini generate_text: %s", e)
            raise RuntimeError("Error generating text with Gemini LLM: %s" % e)

    def generate_opening_message(self, subtheme) -> Dict[str, str]:
        tags = (
            (subtheme.theme.name.lower().replace(" ", "_") + ", " + subtheme.name.lower().replace(" ", "_"))
            if hasattr(subtheme, "theme") else "interpretation"
        )

        prompt = (
            "Eres un asistente experto que ayuda a investigadores a redactar proposiciones interpretativas "
            "(conclusiones preliminares) para una revisión sistemática. Genera un breve texto de apertura que: "
            "1) Reconozca el tema y la pregunta de investigación; 2) Liste los códigos centrales y citas clave; "
            "3) Invite al investigador a suministrar la proposición preliminar o el enfoque deseado.\n\n"
            f"Tema: {getattr(subtheme, 'theme', {}).name if hasattr(subtheme, 'theme') else ''}\n"
            f"Subtema: {getattr(subtheme, 'name', '')}\n"
            f"Códigos centrales: {', '.join(getattr(subtheme, 'central_codes', []) or [])}\n"
        )

        body = self._generate(prompt, max_output_tokens=256)
        return {"title": "Apertura conversacional del Copilot", "body": body, "tags": tags}

    def generate_draft_proposition(self, context, instruction) -> str:
        # Compose a prompt using context and the researcher's instruction
        sub = getattr(context, "subtheme", None)
        extractions = getattr(context, "extractions_context", {}) or {}
        prompt = (
            "Eres un asistente para síntesis interpretativa en revisiones sistemáticas. "
            "A partir del siguiente contexto (tema, subtema, códigos centrales y citas) y la instrucción del investigador, "
            "genera una proposición interpretativa clara y concisa (1-3 oraciones) que responda a la pregunta de investigación.\n\n"
            f"Contexto del tema: {getattr(sub, 'theme',  '') if sub else ''}\n"
            f"Subtema: {getattr(sub, 'name', '') if sub else ''}\n"
            f"Códigos centrales: {', '.join(extractions.get('central_codes', []) or [])}\n"
            f"Citas clave: {', '.join(extractions.get('key_citations', []) or [])}\n\n"
            f"Instrucción del investigador: {instruction}\n\n"
            "Devuelve solo la proposición, sin explicaciones adicionales."
        )

        return self._generate(prompt, max_output_tokens=256)

    def generate_refined_proposition(self, original_text: str, refinement_instruction: str) -> str:
        prompt = (
            "Refina la siguiente proposición interpretativa según la instrucción dada. Mantén la voz académica y la concisión.\n\n"
            f"Proposición original: {original_text}\n"
            f"Instrucción de refinamiento: {refinement_instruction}\n\n"
            "Devuelve solo la proposición refinada."
        )

        return self._generate(prompt, max_output_tokens=256)
    
    def propose_code_normalization(self, codes_data: list) -> list:
        """Use Gemini to propose code normalization."""
        codes_str = "\n".join([f"- {c['code']} (frecuencia: {c['frequency']})" for c in codes_data])
        
        prompt = (
            "Eres un experto en análisis cualitativo y codificación temática. "
            "Analiza los siguientes códigos (tags) de una revisión sistemática y propón fusiones "
            "de códigos similares o relacionados para reducir redundancia.\n\n"
            f"Códigos iniciales:\n{codes_str}\n\n"
            "Para cada propuesta de fusión, devuelve en formato JSON:\n"
            "[\n"
            '  {"normalized_code": "nuevo_codigo", "original_codes": ["codigo1", "codigo2"], '
            '"rationale": "explicación breve"}\n'
            "]\n\n"
            "Devuelve solo el JSON, sin explicaciones adicionales."
        )
        
        try:
            response_text = self._generate(prompt, max_output_tokens=512)
            # Parse JSON response
            import json
            proposals = json.loads(response_text)
            return proposals
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response for code normalization: {e}")
            # Fallback to default implementation
            return DefaultLLMClient().propose_code_normalization(codes_data)
    
    def propose_theme_structure(self, codes_data: list) -> list:
        """Use Gemini to propose Level 1 theme structure (no subthemes)."""
        codes_str = "\n".join([
            f"- {c['code']} (frecuencia: {c['frequency']}, RQ: {c.get('rq_focus', 'N/A')})"
            for c in codes_data
        ])
        
        prompt = (
            "Eres un experto en Teoría Fundamentada y análisis temático cualitativo. "
            "A partir de los siguientes códigos normalizados de una revisión sistemática, "
            "propón una estructura de Temas de Nivel 1 (SIN SUBTEMAS) que sintetice los hallazgos "
            "agrupando códigos por coherencia semántica.\n\n"
            f"Códigos normalizados:\n{codes_str}\n\n"
            "Para cada tema, devuelve en formato JSON:\n"
            "[\n"
            '  {\n'
            '    "theme_name": "Nombre del Tema",\n'
            '    "description": "Descripción del tema",\n'
            '    "rq_focus": "RQ1 o RQ2",\n'
            '    "codes": ["codigo1", "codigo2"],\n'
            '    "subthemes": [],\n'
            '    "rationale": "Justificación de la agrupación"\n'
            '  }\n'
            "]\n\n"
            "IMPORTANTE: No incluyas subtemas, solo temas de Nivel 1 con sus códigos asociados.\n"
            "Devuelve solo el JSON, sin explicaciones adicionales."
        )
        
        try:
            response_text = self._generate(prompt, max_output_tokens=1024)
            # Parse JSON response
            import json
            proposals = json.loads(response_text)
            return proposals
        except Exception as e:
            logger.warning("Failed to parse Gemini response for theme structure: %s", e)
            # Fallback to default implementation
            return DefaultLLMClient().propose_theme_structure(codes_data)


def get_default_client() -> LLMClient:
    """Factory to return the default LLM client.

    Use the `INTERPRETATION_LLM` env var to select a backend, e.g.:
      INTERPRETATION_LLM=gemini

    If not set, fall back to DefaultLLMClient.
    """
    backend = os.getenv("INTERPRETATION_LLM", "default").strip().lower()
    if backend == "gemini":
        try:
            return GeminiLLMClient()
        except Exception as e:
            logger.warning("Failed to instantiate GeminiLLMClient, falling back to DefaultLLMClient: %s", e)
            return DefaultLLMClient()
    else:
        return DefaultLLMClient()
