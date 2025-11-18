# language: es
Característica: Construir cadena de búsqueda
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas
    # Posteriormente puede ser para otra feature o escenario
    #determinar la mejor estrategia de busqueda que guiara mi investigacion

    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a "PICO"

    Escenario: Sugerir términos clave a partir de una pregunta de investigación
        Dado que tengo la pregunta de investigación "¿Cuál es el impacto del desarrollo de software en la industria automotriz?"
        Cuando el sistema procesa la pregunta para sugerir términos clave
        Entonces la lista de términos clave sugeridos debe contener:
        | termino_clave          |
        | industria              | 
        | impacto del desarrollo | 
        | software               |
        | impacto                |
        | industria automotriz   |
        | desarrollo             |
        | desarrollo de software |

    Escenario: Generar sugerencia de estratégia de búsqueda
        Dado que tengo la pregunta de investigación "¿Cuál es el impacto del desarrollo de software en la industria automotriz?"
        Y se han identificado los siguientes términos clave con sus sinónimos:
        | termino_clave             | sinonimos                          |
        | "industria automotriz"    | "automóviles", "sector automotor"  |
        | "desarrollo de software"  |  ""                                |
        Cuando el sistema genere la sugerencia de estratégia de búsqueda
        Entonces la estratégia de búsqueda sugerida será:
        """
            ("industria automotriz" OR "automóviles" OR "sector automotor") AND ("desarrollo de software")
        """

