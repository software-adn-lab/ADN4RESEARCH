# language: es
Característica: Construir cadena de búsqueda
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas
    # Posteriormente puede ser para otra feature o escenario
    #determinar la mejor estrategia de busqueda que guiara mi investigacion

    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a PICO

    Esquema del escenario: Proveer términos clave a partir de campos del framework
        Dado que he creado la "<pregunta_investigacion>" con los siguientes campos <framework_fields>
        Cuando el sistema procesa los campos del framework de la pregunta para sugerir términos clave
        Entonces la lista de términos clave del proyecto debe contener <expected_terms>
        Ejemplos:
        | pregunta_investigacion | framework_fields                                                                                                                                           | expected_terms |
        | ¿Cuál es la medicación tradicional que en conjunto con la terapia física mejora la movilidad en adultos mayores de 65 años?      | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | adultos mayores,terapia física,medicación tradicional,mejora en movilidad |
        
            
    Esquema del escenario: Generar sugerencia de estratégia de búsqueda de una pregunta de investigación
        Dado que he creado la "<pregunta_investigacion>" con los siguientes campos <framework_fields>
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
        | pregunta_investigacion | framework_fields                                                                                                                                           | expected_terms |
        | ¿Cuál es la medicación tradicional que en conjunto con la terapia física mejora la movilidad en adultos mayores de 65 años?      | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | adultos mayores,terapia física,medicación tradicional,mejora en movilidad |