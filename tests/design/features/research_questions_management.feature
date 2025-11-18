# language: es
Característica: Administrar el ciclo de vida de las preguntas de investigación
    Como investigador
    Quiero mantener control en la evolucion de mis preguntas de investigación 
    Para asegurar una apropiada validación de mi diseño en una RSL

    Esquema del escenario: Enviar una pregunta de investigación para su revision
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a <framework>
        Y la etapa de "sugerencias de pregunta de investigación" está abierta
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
        Ejemplos:
            | framework | fields                                                                                                           | suggested_question_text | motivation          |
            | "PICO"    | {"Population": "Students", "Intervention": "Gamification", "Context": "Online courses", "Outcome": "Motivation"} | "How does ...?"         | "To understand ..." |
            | "PEO"     | {"Population": "Nurses", "Exposure": "Night shifts", "Outcome": "Burnout levels"}                                | "What is ...?"          | "To improve ..."    |
            | "PCC"     | {"Population": "Remote workers", "Concept": "Digital nomadism", "Context": "Post-pandemic"}                      | "What are the ...?"     | "Exploring new ..." |
