# language: es
Característica: Construir cadena de búsqueda
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas

    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y que la fase de diseño esta activa
        Y el proyecto tiene como framework investigativo a PICO

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
            ("traditional medication" OR "tradition" OR "medicine") AND ("physical therapy" OR "rehabilitation" OR "recovery") AND ("older adults" OR "elderly" OR "old") AND ("improvement in mobility")
        """
        Ejemplos:
        | framework_fields                                                                                                                                           | expected_terms |
        | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | physical therapy,improvement in mobility,older adults,traditional medication |

    Esquema del escenario: Proveer términos clave a partir de campos del framework
        Dado que he redactado una pregunta de investigación completa para el proyecto:
            """
            {
                "question": "¿El uso de patrones de diseño de software mejora la calidad del proceso de desarrollo en proyectos académicos?",
                "motivation": "Con base en el objetivo 2 del proyecto, se plantea esta pregunta.",
                "framework_fields": {
                    "Population": "Software ",
                    "Intervention": "Design",
                    "Comparison": "Development",
                    "Outcome": "Quality Maintainability"
                }
            }
            """
        Cuando el sistema procesa los campos del framework de la pregunta para sugerir términos clave
        Entonces la lista de términos clave del proyecto debe contener "software,design,development,maintainability, quality"

    Escenario: Probar cadena de búsqueda generada
        Dado que la etapa de "estrategia" esta activa en la fase de diseño
        Y que selecciono una pregunta de investigación del protocolo de diseño del proyecto
        Y que tengo la lista de términos clave y sinónimos de dicha pregunta
        Cuando pruebo la cadena de búsqueda que he construido
        Y el sistema traduce la cadena de búsqueda a inglés
        Entonces se recibirán resultados de dicha búsqueda desde el módulo de adquisición
        Y se creará una versión borrador de la estratégia de busqueda