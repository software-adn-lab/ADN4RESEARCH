# language: es
Feature: Managing the lifecycle of research questions
    As a researcher
    I want to maintain control over the evolution of my research questions
    So that I can ensure their proper validation throughout the systematic review.

    Scenario Outline: Submit a suggested research question for review
        Given the "Suggest Research Question" stage of the project is opened
        And I have written a question with the following content:
            """
            {
                "framework": <framework>,
                "fields": <fields>,
                "suggested_question": <suggested_question_text>,
                "motivation": <motivation>
            }
            """
        And the question is on a "READY_TO_SEND" status
        When I submit the question for review
        Then the question should change its status to "SUGGESTED"
        And a "RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW" notification should be sent to the research project team
        Examples:
            | framework | fields                                                                                                           | suggested_question_text | motivation          |
            | "PICO"    | {"Population": "Students", "Intervention": "Gamification", "Context": "Online courses", "Outcome": "Motivation"} | "How does ...?"         | "To understand ..." |
            | "PEO"     | {"Population": "Nurses", "Exposure": "Night shifts", "Outcome": "Burnout levels"}                                | "What is ...?"          | "To improve ..."    |
            | "PCC"     | {"Population": "Remote workers", "Concept": "Digital nomadism", "Context": "Post-pandemic"}                      | "What are the ...?"     | "Exploring new ..." |

    Escenario: Enviar una pregunta de investigacion para su revision
        Dado que estoy asignado a un proyecto de investigacion
        Y la etapa de "sugerencias de pregunta de investigacion" esta abierta
        Cuando envie una pregunta de investigacion para su revision
        Entonces el sistema notificara la creacion al equipo investigador
        Examples:
            | framework | fields                                                                                                           | suggested_question_text | motivation          |
            | "PICO"    | {"Population": "Students", "Intervention": "Gamification", "Context": "Online courses", "Outcome": "Motivation"} | "How does ...?"         | "To understand ..." |
            | "PEO"     | {"Population": "Nurses", "Exposure": "Night shifts", "Outcome": "Burnout levels"}                                | "What is ...?"          | "To improve ..."    |
            | "PCC"     | {"Population": "Remote workers", "Concept": "Digital nomadism", "Context": "Post-pandemic"}                      | "What are the ...?"     | "Exploring new ..." |'''
