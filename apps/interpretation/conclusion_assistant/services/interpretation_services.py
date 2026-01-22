from django.db import transaction
from apps.interpretation.conclusion_assistant.models import (
    Theme,
    SubTheme,
    InterpretationContext,
    ConversationTrace,
    InterpretativeProposition,
)
from apps.interpretation.conclusion_assistant.models.normalization_models import NormalizedCode
from apps.extraction.core.models import Quote
from apps.extraction.taxonomy.models import Tag
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
        # 1. Enriquecer el contexto con las extracciones (quotes) reales desde la base de datos
        # Esto es crucial para que el LLM tenga el contexto completo de los códigos y sus evidencias
        enriched_context_str = self._get_context_extractions(context.subtheme)
        
        # Registrar la instrucción del investigador
        ConversationTrace.objects.create(
            context=context,
            role=ConversationTrace.MessageRole.RESEARCHER,
            message=instruction,
            title="Instrucción de síntesis",
            body=instruction,
            tags="",
        )

        try:
            # Generar proposición borrador delegando a LLM client
            # Se pasa el contexto enriquecido (string) y la instrucción
            draft_text = self.llm_client.generate_draft_proposition(
                context=context, 
                instruction=instruction,
                extra_context=enriched_context_str
            )
        except ValueError as e:
            # El LLM determinó que la instrucción no es relevante
            error_msg = str(e)
            ConversationTrace.objects.create(
                context=context,
                role=ConversationTrace.MessageRole.COPILOT,
                message=error_msg,
                title="Input No Relevante",
                body=error_msg,
                tags="error, irrelevant",
            )
            # No creamos proposición, solo notificamos
            raise ValueError(error_msg)
        except Exception as e:
            # Manejo específico para errores de cuota o servicio
            if "Quota exceeded" in str(e) or "429" in str(e):
                friendly_msg = (
                    "⚠️ **Servicio no disponible temporalmente**\n\n"
                    "Se ha excedido la cuota de uso del modelo de IA (Gemini). "
                    "Por favor intenta nuevamente en unos minutos o verifica los límites de tu plan."
                )
                ConversationTrace.objects.create(
                    context=context,
                    role=ConversationTrace.MessageRole.COPILOT,
                    message=friendly_msg,
                    title="Error de Cuota",
                    body=friendly_msg,
                    tags="error, quota",
                )
            # Propagamos el error para que la vista también notifique
            raise e

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

    def _get_context_extractions(self, subtheme):
        """
        Recupera las citas (quotes) asociadas a los códigos centrales del subtema.
        """
        if not hasattr(subtheme, "central_codes") or not subtheme.central_codes:
            return "No hay códigos centrales asignados a este subtema."

        central_codes_names = subtheme.central_codes  # List of strings (NormalizedCode names)
        
        # 1. Encontrar los NormalizedCode para obtener los códigos originales
        # Nota: Asumimos que central_codes contiene nombres de NormalizedCodes
        normalized_codes = NormalizedCode.objects.filter(code__in=central_codes_names)
        
        if not normalized_codes.exists():
            return f"No se encontraron datos de normalización para los códigos: {', '.join(central_codes_names)}"

        # 2. Recopilar todos los códigos originales (Tags)
        all_original_codes = []
        code_mapping = {}  # normalized -> [original list]
        
        for nc in normalized_codes:
            originals = nc.original_codes if isinstance(nc.original_codes, list) else []
            all_original_codes.extend(originals)
            code_mapping[nc.code] = originals

        # 3. Buscar las Quotes que tengan tags con estos nombres
        # Buscamos Tags por nombre
        tags = Tag.objects.filter(name__in=all_original_codes)
        
        # Mapa de Original Tag Name -> Quote Texts
        quotes_by_tag = {}
        processed_quote_ids = set()

        # Iteramos tags para buscar sus quotes
        for tag in tags:
            quotes = Quote.objects.filter(tags=tag).select_related('paper_extraction__study')
            quote_list = []
            for q in quotes:
                if q.id in processed_quote_ids:
                    continue
                processed_quote_ids.add(q.id)
                
                source = "Desconocido"
                if q.paper_extraction and q.paper_extraction.study:
                    source = f"{q.paper_extraction.study.title} ({q.paper_extraction.study.year})"
                
                quote_list.append(f"\"{q.text_fragment}\" [{source}]")
            
            if quote_list:
                quotes_by_tag[tag.name] = quote_list

        # 4. Construir el string de contexto agrupado por Código Normalizado
        context_parts = []
        context_parts.append(f"Contexto de Evidencia para Subtema '{subtheme.name}':")
        
        for nc_name, originals in code_mapping.items():
            context_parts.append(f"\nCódigo Central (Normalizado): {nc_name}")
            has_evidence = False
            for orig in originals:
                if orig in quotes_by_tag:
                    for qt in quotes_by_tag[orig]:
                        context_parts.append(f"  - {qt}")
                        has_evidence = True
            
            if not has_evidence:
                context_parts.append("  (Sin evidencia directa extraída)")

        return "\n".join(context_parts)

    def _generate_draft_proposition(self, context, instruction):
        """
        Genera un borrador de proposición.
        En producción, esto se conectaría con un servicio de IA.
        """
        # Deprecated: use llm_client.generate_draft_proposition instead
        return self.llm_client.generate_draft_proposition(context, instruction)

    @transaction.atomic
    def refine_proposition(self, proposition, refinement_instruction, _=None):
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
