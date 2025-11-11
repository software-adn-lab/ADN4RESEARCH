"""Flexible LLM client implementations and mocks for InterpretationService.

This module defines a small interface and a couple of implementations:
- LLMClient: abstract interface
- DefaultLLMClient: placeholder implementation (no external calls)
- MockLLMClient: deterministic mock useful for tests

You can add adapters here for OpenAI, Anthropic, local LLMs, etc., following
the same interface.
"""
from typing import Dict


class LLMClient:
    """Interface for LLM clients used by InterpretationService."""

    def generate_opening_message(self, subtheme) -> Dict[str, str]:
        raise NotImplementedError()

    def generate_draft_proposition(self, context, instruction) -> str:
        raise NotImplementedError()

    def generate_refined_proposition(self, original_text: str, refinement_instruction: str) -> str:
        raise NotImplementedError()


class DefaultLLMClient(LLMClient):
    """Default placeholder client used when no real LLM is configured.

    Returns deterministic, human-readable placeholders. Safe for tests
    that don't need external network calls.
    """

    def generate_opening_message(self, subtheme):
        tags = (
            (subtheme.theme.name.lower().replace(" ", "_") + ", " + subtheme.name.lower().replace(" ", "_"))
            if hasattr(subtheme, "theme") else "interpretation"
        )

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
