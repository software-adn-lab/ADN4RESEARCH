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

    Esquema del escenario: Proveer términos clave a partir de campos del framework
        Dado que he identificado los campos <framework_fields> del framework <framework>
        Cuando el sistema procesa las oraciones para sugerir términos clave
        Entonces la lista de términos clave sugeridos debe contener <expected_terms>

        Ejemplos:
        | framework | framework_fields                                                                                                                                           | expected_terms |
        | PICO      | {"Population": "adultos mayores de 65 años", "Intervention": "terapia física", "Comparison": "medicación tradicional", "Outcome": "mejora en movilidad"}   | adultos mayores,terapia física,medicación tradicional,mejora en movilidad |
        | PEO       | {"Population": "adolescentes de 12 a 18 años", "Exposure": "uso de redes sociales por más de 4 horas diarias", "Outcome": "niveles de ansiedad y depresión"} | horas diarias,redes sociales,uso de redes,niveles de ansiedad |
        | PCC       | {"Population": "enfermeras de cuidados intensivos", "Concept": "burnout laboral", "Context": "hospitales públicos durante la pandemia COVID-19"}           | cuidados intensivos,burnout laboral,hospitales públicos,cuidados intensivos,burnout laboral,enfermeras de cuidados |
            
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