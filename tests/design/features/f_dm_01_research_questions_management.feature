# language: es
# F-DM-01
Característica: Administrar el ciclo de vida de las preguntas de investigación
    Como investigador
    Quiero mantener control en la evolucion de las preguntas de investigación del proyecto 
    Para asegurar una apropiada validación de mi diseño en una RSL

    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a PICO
    
    Esquema: Sugerir pregunta para el proyecto de investigación
        Dado que la etapa de "creación" esta activa en la fase de diseño
        Y que he redactado una pregunta de investigación completa para el proyecto:
            """
            {
                "question": "¿Los patrones de diseño de software ayudan a mejorar el desarrollo?",
                "motivation": "En base al objetivo 2 del proyecto, se plantea esta pregunta.",
                "framework_fields": {"Population": "Students", "Intervention": "Gamification", "Comparison": "Online courses", "Outcome": "Motivation"}
            }
            """
        Y que esta pregunta está "READY_TO_SEND"
        Cuando envíe la pregunta de investigación creada
        Entonces la pregunta estará "SUGGESTED" para el proyecto
        Y el sistema notificará al equipo investigador

    Esquema del escenario: Sugerir accion ante una pregunta de investigacion del proyecto
        Dado que la etapa de "discusión" esta activa en la fase de diseño
        Y que existen preguntas de investigación "SUGGESTED" por los investigadores para el proyecto
        Y selecciono una pregunta que no haya sido sugerida por mí
        Cuando la revise y sugiera <action> la pregunta de investigación seleccionada con la justificación de mi decisión
        Entonces la pregunta estará "<expected_status>" para el proyecto
        Ejemplos:
            | action   | expected_status |  
            | approve  |     APPROVED    |
            | reject   |     REJECTED    |
            