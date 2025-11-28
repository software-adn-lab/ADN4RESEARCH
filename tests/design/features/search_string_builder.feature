# language: es
Característica: Construir cadena de búsqueda
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas

    # CONSIDERACIONES: En mi modulo se prueba el comportamiento propio del modulo, por ende, no tiene sentido alguno
    # probar la misma cosa con diferentes frameworks, debido a que es practicamente lo mismo.
    # Es por ello que la precondicion principal es que haya proyecto y este este creado con x framework, en este caso
    # tomo como ejemplo a PICO.
    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y que la fase de diseño esta activa
        Y el proyecto tiene como framework investigativo a PICO

    Esquema del escenario: Proveer términos clave a partir de campos del framework
        Dado que he redactado una pregunta de investigación completa para el proyecto:
            """
            {
                "question": "¿Cuál es la medicación tradicional que en conjunto con la terapia física mejora la movilidad en adultos mayores de 65 años?",
                "motivation": "Es necesario para el proyecto",
                "framework_fields": <framework_fields>
            }
            """
        Cuando el sistema procesa los campos del framework de la pregunta para sugerir términos clave
        Entonces la lista de términos clave del proyecto debe contener <expected_terms>
        Ejemplos:
        | framework_fields                                                                                                                                           | expected_terms |
        | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | adultos mayores,terapia física,medicación tradicional,mejora en movilidad |
            
    Esquema del escenario: Generar sugerencia de estrategia de búsqueda de una pregunta de investigación
        Dado que he redactado una pregunta de investigación completa para el proyecto:
            """
            {
                "question": "¿Cuál es la medicación tradicional que en conjunto con la terapia física mejora la movilidad en adultos mayores de 65 años?",
                "motivation": "Es necesario para el proyecto",
                "framework_fields": <framework_fields>
            }
            """
        Y he identificado los sinónimos de los términos clave:
        | termino_clave             | sinonimos                          |
        | "medicación tradicional"  | tradición, medicina                |
        | "terapia física"          | rehabilitación, recuperación       |
        | "adultos mayores"         | ancianos, viejos                   |
        | "mejora en movilidad"     |                                    |
        Cuando el sistema genere la sugerencia de estratégia de búsqueda
        Entonces la estratégia de búsqueda sugerida será:
        """
            ("medicación tradicional" OR "tradición" OR "medicina") AND ("terapia física" OR "rehabilitación" OR "recuperación") AND ("adultos mayores" OR "ancianos" OR "viejos") AND ("mejora en movilidad")
        """
        Ejemplos:
        | framework_fields                                                                                                                                           | expected_terms |
        | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | adultos mayores,terapia física,medicación tradicional,mejora en movilidad |