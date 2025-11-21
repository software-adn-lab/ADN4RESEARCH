# language: es
Característica: Administrar el ciclo de vida de las preguntas de investigación
    Como investigador
    Quiero mantener control en la evolucion de las preguntas de investigación del proyecto 
    Para asegurar una apropiada validación de mi diseño en una RSL

    # CONSIDERACIONES: En mi modulo se prueba el comportamiento propio del modulo, por ende, no tiene sentido alguno
    # probar la misma cosa con diferentes frameworks, debido a que es practicamente lo mismo.
    # Es por ello que la precondicion principal es que haya proyecto y este este creado con x framework, en este caso
    # tomo como ejemplo a PICO.
    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a PICO
    
    Esquema del escenario: Sugerir pregunta para el proyecto de investigación
        Dado que he redactado una pregunta de investigación completa para el proyecto:
            """
            {
                "question": <question>,
                "motivation": <motivation>,
                "framework_fields": <framework_fields>
            }
            """
        Y que esta pregunta está "READY_TO_SEND"
        Cuando envíe la pregunta de investigación creada
        Entonces la pregunta estará "SUGGESTED" para el proyecto
        Y el sistema notificará al equipo investigador
        Ejemplos: 
            | framework_fields                                                                                                    |         question        | motivation          |
            | {"Population": "Students", "Intervention": "Gamification", "Comparison": "Online courses", "Outcome": "Motivation"} | "How does ...?"         | "To understand ..." |

    Escenario: Sugerir aprobación de pregunta de investigación del proyecto
        Dado que existen preguntas de investigación "SUGGESTED" por los investigadores para el proyecto
        Y selecciono una pregunta que no haya sido sugerida por mí
        Cuando sugiera aprobar la pregunta de investigación seleccionada con una justificación de mi decisión
        Entonces la pregunta estará "APPROVED" para el proyecto
        
