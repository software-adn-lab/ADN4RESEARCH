from django.db import transaction
from apps.interpretation.conclusion_assistant.models import (
    Theme,
    SubTheme,
    InterpretationContext,
    ConversationTrace,
    InterpretativeProposition,
)
from . import llm_clients as _llm_mod


class InterpretationService:
    """
    Servicio para manejar la lógica de negocio del módulo de interpretación.
    """

    def __init__(self, llm_client=None):
        """Create a service instance.
        llm_client: optional object implementing the LLMClient interface.
        If None, a DefaultLLMClient (placeholder responses) is used.
        """
        # Use the factory so the backend can be selected via env var (INTERPRETATION_LLM)
        self.llm_client = llm_client or _llm_mod.get_default_client()

    def create_theme(self, name, research_question, description="", created_by=None):
        """Crea un nuevo tema de investigación."""
        theme = Theme.objects.create(
            name=name,
            description=description,
            research_question=research_question,
            created_by=created_by,
        )
        return theme

    def create_subtheme(self, theme, name, central_codes=None, key_citations=None):
        """Crea un nuevo subtema dentro de un tema."""
        subtheme = SubTheme.objects.create(
            theme=theme,
            name=name,
            central_codes=central_codes or [],
            key_citations=key_citations or [],
        )
        return subtheme

    @transaction.atomic
    def initiate_interpretation_context(self, subtheme):
        """
        Inicia el contexto de interpretación para un subtema.
        Establece el contexto activo y genera la apertura conversacional.
        """
        # Crear o actualizar el contexto de interpretación
        context, _ = InterpretationContext.objects.update_or_create(
            subtheme=subtheme,
            defaults={
                "research_question": subtheme.theme.research_question,
                "theme_name": subtheme.theme.name,
                "extractions_context": {
                    "central_codes": subtheme.central_codes,
                    "key_citations": subtheme.key_citations,
                },
                "is_active": True,
            },
        )
        # Generar apertura conversacional delegando al cliente LLM
        opening_message = self.llm_client.generate_opening_message(subtheme)

        # Registrar la apertura en la traza de conversación
        trace = ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.COPILOT,
            message=opening_message["body"],
            title=opening_message["title"],
            body=opening_message["body"],
            tags=opening_message["tags"],
        )

        # Actualizar estado del subtema
        subtheme.status = SubTheme.Status.IN_PROGRESS
        subtheme.save(update_fields=["status", "modified_at"])

        return context, trace

    def _generate_opening_message(self, subtheme):
        # Deprecated: kept for backward compatibility but prefer LLM client.
        tags = self._generate_tags(subtheme)

        body = (
            f"Asistiendo en la interpretación del Subtema: {subtheme.name}. "
            f"Este subtema está relacionado con el tema principal '{subtheme.theme.name}'. "
            f"Los códigos centrales identificados son: {', '.join(subtheme.central_codes)}. "
            f"¿Cuál es la proposición preliminar o enfoque deseado?"
        )

        return {
            "title": "Apertura conversacional del Copilot",
            "body": body,
            "tags": tags,
        }

    def _generate_tags(self, subtheme):
        """Genera tags basados en el subtema."""
        # Convertir nombre del tema a snake_case para tags
        theme_tag = subtheme.theme.name.lower().replace(" ", "_")
        subtheme_tag = subtheme.name.lower().replace(" ", "_")

        # Agregar algunos códigos centrales como tags
        code_tags = [
            code.lower().replace(" ", "_") for code in subtheme.central_codes[:2]
        ]

        all_tags = [theme_tag, subtheme_tag] + code_tags
        return ", ".join(all_tags)

    @transaction.atomic
    def create_proposition_draft(self, context, instruction, researcher=None):
        """
        Crea un borrador de proposición interpretativa basado en la instrucción del investigador.
        """
        # Registrar la instrucción del investigador
        ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.RESEARCHER,
            message=instruction,
            title="Instrucción de síntesis",
            body=instruction,
            tags="",
        )

        # Generar proposición borrador delegando a LLM client
        draft_text = self.llm_client.generate_draft_proposition(context, instruction)

        # Crear la proposición
        proposition = InterpretativeProposition.objects.create(
            subtheme=context.subtheme,
            proposition_text=draft_text,
            status=InterpretativeProposition.PropositionStatus.DRAFT,
            researcher=researcher,
        )

        # Registrar la respuesta del Copilot
        ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.COPILOT,
            message=draft_text,
            title="Proposición Interpretativa Borrador",
            body=draft_text,
            tags="borrador, proposicion",
        )

        return proposition

    def _generate_draft_proposition(self, context, instruction):
        """
        Genera un borrador de proposición.
        En producción, esto se conectaría con un servicio de IA.
        """
        # Deprecated: use llm_client.generate_draft_proposition instead
        return self.llm_client.generate_draft_proposition(context, instruction)

    @transaction.atomic
    def refine_proposition(self, proposition, refinement_instruction, researcher=None):
        """
        Refina una proposición existente basada en nueva instrucción.
        """
        context = InterpretationContext.objects.get(subtheme=proposition.subtheme)

        # Registrar instrucción de refinamiento
        ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.RESEARCHER,
            message=refinement_instruction,
            title="Instrucción de refinamiento",
            body=refinement_instruction,
            tags="refinamiento",
        )

        # Generar texto refinado delegando al cliente LLM
        refined_text = self.llm_client.generate_refined_proposition(
            proposition.proposition_text, refinement_instruction
        )

        # Actualizar proposición
        proposition.proposition_text = refined_text
        proposition.status = InterpretativeProposition.PropositionStatus.REFINED
        proposition.save(update_fields=["proposition_text", "status", "modified_at"])

        # Registrar respuesta refinada
        trace = ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.COPILOT,
            message=refined_text,
            title="Proposición Refinada",
            body=refined_text,
            tags="refinado, proposicion",
        )

        return proposition, trace

    def _generate_refined_proposition(self, original_text, refinement_instruction):
        """
        Genera una versión refinada de la proposición.
        En producción, esto se conectaría con un servicio de IA.
        """
        # Deprecated: use llm_client.generate_refined_proposition instead
        return self.llm_client.generate_refined_proposition(
            original_text, refinement_instruction
        )

    @transaction.atomic
    def finalize_proposition(self, proposition):
        """
        Finaliza una proposición como hallazgo final de la SLR.
        """
        context = InterpretationContext.objects.get(subtheme=proposition.subtheme)

        # Actualizar estado de la proposición
        proposition.status = InterpretativeProposition.PropositionStatus.FINAL
        proposition.save(update_fields=["status", "modified_at"])

        # Marcar el subtema como interpretación finalizada
        subtheme = proposition.subtheme
        subtheme.status = SubTheme.Status.INTERPRETATION_COMPLETED
        subtheme.save(update_fields=["status", "modified_at"])

        # Desactivar el contexto
        context.is_active = False
        context.save(update_fields=["is_active", "modified_at"])

        return proposition

    def get_conversation_trace(self, context):
        """Obtiene la traza completa de conversación para un contexto."""
        return ConversationTrace.objects.filter(context=context).order_by("created_at")

    def get_subtheme_by_id(self, subtheme_id):
        """Obtiene un subtema por su ID."""
        try:
            return SubTheme.objects.get(id=subtheme_id)
        except SubTheme.DoesNotExist as e:
            raise ValueError(f"SubTheme with id {subtheme_id} not found") from e

    def get_theme_by_name(self, name):
        """Obtiene un tema por su nombre."""
        try:
            return Theme.objects.get(name=name)
        except Theme.DoesNotExist as e:
            raise ValueError(f"Theme with name '{name}' not found") from e
