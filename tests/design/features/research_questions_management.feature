# language: es
Característica: Administrar el ciclo de vida de las preguntas de investigación
    Como investigador
    Quiero mantener control en la evolucion de mis preguntas de investigación 
    Para asegurar una apropiada validación de mi diseño en una RSL
'''
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
            | "PCC"     | {"Population": "Remote workers", "Concept": "Digital nomadism", "Context": "Post-pandemic"}                      | "What are the ...?"     | "Exploring new ..." |'''

    Esquema del escenario: Enviar una pregunta de investigación para su revision
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a <framework>
        Y la etapa de "sugerencias de pregunta de investigación" esta abierta
        Cuando envie una pregunta de investigación para su revision:
            """
            {
                "framework": <framework>,
                "fields": <fields>,
                "suggested_question": <suggested_question_text>,
                "motivation": <motivation>
            }
            """
        Entonces el sistema notificara la creacion al equipo investigador
        Y la etapa se cerrará
        Ejemplos:
            | framework | fields                                                                                                           | suggested_question_text | motivation          |
            | "PICO"    | {"Population": "Students", "Intervention": "Gamification", "Context": "Online courses", "Outcome": "Motivation"} | "How does ...?"         | "To understand ..." |
            | "PEO"     | {"Population": "Nurses", "Exposure": "Night shifts", "Outcome": "Burnout levels"}                                | "What is ...?"          | "To improve ..."    |
            | "PCC"     | {"Population": "Remote workers", "Concept": "Digital nomadism", "Context": "Post-pandemic"}                      | "What are the ...?"     | "Exploring new ..." |
