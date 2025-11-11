from behave import given, when, then
from django.contrib.auth.models import User
from tests.interpretation.helpers.data_provider import data_provider

from apps.interpretation.conclusion_assistant.models import (
    SubTheme,
    ConversationTrace,
)
from apps.interpretation.conclusion_assistant.services.interpretation_services import InterpretationService

interpretation_service = InterpretationService()


@given(
    'que el Investigador ha definido la Pregunta de Investigación: "{research_question}"'
)
def step_impl(context, research_question):
    """Define la pregunta de investigación en el contexto."""
    # Prefer loading from the configured data provider when available.
    questions = data_provider.get_questions()
    if questions:
        # Use the first question from the examples as the research question.
        context.research_question = questions[0]
    else:
        context.research_question = research_question

    # Crear un usuario investigador si no existe
    if not hasattr(context, "researcher"):
        context.researcher, _ = User.objects.get_or_create(
            username="test_researcher", defaults={"email": "researcher@test.com"}
        )


@given('se tiene el tema "{theme_name}" como foco de la interpretación actual')
def step_impl(context, theme_name):
    """Crea el tema principal de investigación."""
    context.theme = interpretation_service.create_theme(
        name=theme_name,
        research_question=context.research_question,
        description=f"Tema de investigación sobre {theme_name}",
        created_by=context.researcher,
    )


@given(
    'el Investigador selecciona el "{subtheme_name}" como objeto de la interpretación'
)
def step_impl(context, subtheme_name):
    """Crea el subtema con los datos de la tabla."""
    # Extraer datos de la tabla si existe
    if context.table:
        row = context.table[0]
        central_codes = [code.strip() for code in row["Códigos Centrales"].split(",")]
        key_citations = [row["Citas Clave de Estudios"]]
    else:
        # Obtain codes and citations from the configured data provider.
        parsed_codes, parsed_citations = data_provider.get_codes_and_citations()

        if parsed_codes:
            central_codes = parsed_codes
        else:
            # fallback defaults
            central_codes = [
                "Dependencia de zonas horarias",
                "Retraso en feedback",
                "Falta de confianza",
            ]

        if parsed_citations:
            key_citations = parsed_citations
        else:
            key_citations = ["Fragmentos de texto específicos"]

    context.subtheme = interpretation_service.create_subtheme(
        theme=context.theme,
        name=subtheme_name,
        central_codes=central_codes,
        key_citations=key_citations,
    )


@given(
    'que el Módulo de Interpretación está disponible para la Síntesis de Datos y las "extracciones" del "tema B" son parte del contexto activo'
)
def step_impl(context):
    """Verifica que el módulo de interpretación está disponible."""
    # Verificar que el subtema existe y tiene datos
    assert context.subtheme is not None
    assert len(context.subtheme.central_codes) > 0
    assert context.subtheme.status == SubTheme.Status.PENDING


@when(
    'el Investigador **inicia de la asistencia conversacional** sobre el "{subtheme_name}"'
)
def step_impl(context, subtheme_name):
    """Inicia la asistencia interpretativa conversacional."""
    # Iniciar el contexto de interpretación
    context.interpretation_context, context.opening_trace = (
        interpretation_service.initiate_interpretation_context(context.subtheme)
    )


@when(
    "**Establece la RQ, el subtema B y los códigos/citas de soporte como contexto activo** para la interacción."
)
def step_impl(context):
    """Verifica que el contexto activo está establecido."""
    # El contexto ya fue establecido en el paso anterior
    assert context.interpretation_context.is_active
    assert context.interpretation_context.research_question == context.research_question
    assert context.interpretation_context.theme_name == context.theme.name


@then("se genera un texto con la estructura:")
def step_impl(context):
    """Verifica que se genera un texto con la estructura Title, Body, Tags."""
    # Obtener el último mensaje del Copilot (apertura conversacional)
    opening_message = context.opening_trace

    assert opening_message is not None
    assert opening_message.role == ConversationTrace.MessageRole.COPILOT

    # Verificar estructura de la tabla
    if context.table:
        row = context.table[0]
        expected_title = row["Title"]
        expected_body_contains = "Subtema"  # Verificar que menciona el subtema
        expected_tags_present = True

        # Verificaciones
        assert (
            opening_message.title == expected_title
        ), f"Expected title '{expected_title}', got '{opening_message.title}'"
        assert (
            expected_body_contains in opening_message.body
        ), f"Body should mention the subtheme"
        assert len(opening_message.tags) > 0, "Tags should not be empty"

        # Guardar para uso posterior
        context.opening_message = {
            "title": opening_message.title,
            "body": opening_message.body,
            "tags": opening_message.tags,
        }


# @given(
#     "que la Asistencia Interpretativa Conversacional está activa y contextualizada con el Tema B"
# )
# def step_impl(context):
#     """Verifica que la asistencia interpretativa está activa."""
#     # Reutilizar el contexto del escenario anterior o crear uno nuevo
#     if (
#         not hasattr(context, "interpretation_context")
#         or not context.interpretation_context.is_active
#     ):
#         # Si no hay contexto activo, crear uno
#         context.interpretation_context, _ = (
#             interpretation_service.initiate_interpretation_context(context.subtheme)
#         )

#     assert context.interpretation_context.is_active


# @given("el Investigador ha mantenido la siguiente interacción con el Copilot:")
# def step_impl(context):
#     """Registra interacciones previas con el Copilot."""
#     if context.table:
#         for row in context.table:
#             instruction = row["Instrucción Investigador"]
#             _ = row["Respuesta Copilot (Borrador)"]

#             # Crear la proposición borrador
#             context.draft_proposition = interpretation_service.create_proposition_draft(
#                 context=context.interpretation_context,
#                 instruction=instruction,
#                 researcher=context.researcher,
#             )


# @when(
#     'el Investigador **proporciona la instrucción de refinamiento final**: "{refinement_instruction}"'
# )
# def step_impl(context, refinement_instruction):
#     """El investigador proporciona una instrucción de refinamiento."""
#     # Refinar la proposición
#     context.refined_proposition, context.refined_trace = (
#         interpretation_service.refine_proposition(
#             proposition=context.draft_proposition,
#             refinement_instruction=refinement_instruction,
#             researcher=context.researcher,
#         )
#     )


# @then("el sistema (Copilot) debería:")
# def step_impl(context):
#     """Placeholder para steps anidados con 'And'."""
#     pass


# @then('Generar una **Proposición Refinada** que incorpore el concepto de "{concept}".')
# def step_impl(context, concept):
#     """Verifica que la proposición refinada incorpore el concepto solicitado."""
#     refined_text = context.refined_proposition.proposition_text

#     # Verificar que la proposición fue refinada
#     assert (
#         context.refined_proposition.status
#         == InterpretativeProposition.PropositionStatus.REFINED
#     )

#     # Verificar que el concepto está presente (en este caso, 'comunicación asíncrona')
#     concept_lower = concept.lower()
#     assert (
#         concept_lower in refined_text.lower()
#     ), f"El concepto '{concept}' no está presente en la proposición refinada"


# @then(
#     "El Módulo de Interpretación debería **persistir** la Proposición Refinada y su narrativa de soporte como 'Hallazgo Final de la SLR'."
# )
# def step_impl(context):
#     """Verifica que la proposición se persiste como hallazgo final."""
#     # Finalizar la proposición
#     final_proposition = interpretation_service.finalize_proposition(
#         context.refined_proposition
#     )

#     # Verificar que se persistió correctamente
#     assert final_proposition.status == InterpretativeProposition.PropositionStatus.FINAL
#     assert final_proposition.id is not None

#     context.final_proposition = final_proposition


# @then(
#     "**Guardar la traza completa de la interacción conversacional** para fines de **Reflexividad metodológica**."
# )
# def step_impl(context):
#     """Verifica que la traza de conversación se guardó."""
#     conversation_trace = interpretation_service.get_conversation_trace(
#         context.interpretation_context
#     )

#     # Verificar que hay al menos una interacción registrada
#     assert conversation_trace.count() > 0, "La traza de conversación está vacía"

#     # Verificar que hay mensajes tanto del investigador como del Copilot
#     researcher_messages = conversation_trace.filter(
#         role=ConversationTrace.MessageRole.RESEARCHER
#     )
#     copilot_messages = conversation_trace.filter(
#         role=ConversationTrace.MessageRole.COPILOT
#     )

#     assert (
#         researcher_messages.count() > 0
#     ), "No hay mensajes del investigador en la traza"
#     assert copilot_messages.count() > 0, "No hay mensajes del Copilot en la traza"


# @then("Marcar el Tema B como **'Interpretación Finalizada'**.")
# def step_impl(context):
#     """Verifica que el subtema está marcado como interpretación finalizada."""
#     # Recargar el subtema de la base de datos
#     subtheme = interpretation_service.get_subtheme_by_id(context.subtheme.id)

#     # Verificar el estado
#     assert (
#         subtheme.status == SubTheme.Status.INTERPRETATION_COMPLETED
#     ), f"Expected status {SubTheme.Status.INTERPRETATION_COMPLETED}, got {subtheme.status}"
