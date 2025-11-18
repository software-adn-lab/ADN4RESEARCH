"""Test helpers: lightweight LLM clients for behave/unit tests.

Place test-only mocks/fakes here so step implementations can import them
from the `tests.interpretation.helpers` package without touching production
implementations.

Examples provided:
- MockLLMClient: returns pre-configured responses (good for assertions)
- FakeLLMClient: simple deterministic logic that combines inputs (useful for
  lightweight integration-style tests that don't call out to external APIs)
"""
from typing import Dict, Optional, Any


class MockLLMClient:
    """Mock client that returns pre-configured responses for tests."""

    def __init__(self, opening_message: Optional[Dict[str, str]] = None, draft_text: Optional[str] = None, refined_text: Optional[str] = None):
        self.opening_message = opening_message or {
            "title": "[MOCK] Apertura conversacional",
            "body": "[MOCK] Apertura conversacional.",
            "tags": "mock",
        }
        self.draft_text = draft_text or "[MOCK] Borrador de proposición."
        self.refined_text = refined_text or "[MOCK] Proposición refinada."
        # simple spy storage
        self.calls: Any = []

    def generate_opening_message(self, subtheme) -> Dict[str, str]:
        self.calls.append(("opening", getattr(subtheme, "name", None)))
        return self.opening_message

    def generate_draft_proposition(self, _, instruction) -> str:
        self.calls.append(("draft", instruction))
        return self.draft_text

    def generate_refined_proposition(self, _: str, refinement_instruction: str) -> str:
        self.calls.append(("refine", refinement_instruction))
        return self.refined_text


class FakeLLMClient:
    """Fake client with light deterministic logic for tests.

    This is more realistic than a stub because it composes inputs to produce
    responses, while remaining fast and network-free.
    """

    def __init__(self, seed_prefix: str = "[FAKE]"):
        self.seed_prefix = seed_prefix
        self.calls: Any = []

    def generate_opening_message(self, subtheme) -> Dict[str, str]:
        self.calls.append(("opening", getattr(subtheme, "name", None)))
        codes = getattr(subtheme, "central_codes", []) or []
        title = f"{self.seed_prefix} Apertura"
        body = f"{self.seed_prefix} Subtema: {getattr(subtheme, 'name', 'Subtema')}. Codes: {', '.join(codes)}"
        tags = ", ".join(filter(None, [getattr(subtheme, 'theme', None) and getattr(subtheme.theme, 'name', '').lower().replace(' ', '_'), getattr(subtheme, 'name', '').lower().replace(' ', '_')]))
        return {"title": title, "body": body, "tags": tags}

    def generate_draft_proposition(self, context, instruction) -> str:
        self.calls.append(("draft", instruction))
        rq = getattr(context, "research_question", "")
        codes = (getattr(context, "extractions_context", {}) or {}).get("central_codes", [])
        return f"{self.seed_prefix} RQ: {rq} | Instr: {instruction} | Codes: {', '.join(codes)}"

    def generate_refined_proposition(self, original_text: str, refinement_instruction: str) -> str:
        self.calls.append(("refine", refinement_instruction))
        return f"{self.seed_prefix} REFINED: {original_text} -- {refinement_instruction}"
