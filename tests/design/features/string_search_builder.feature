# language: es
Característica: Construir cadena de búsqueda
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas
    # Posteriormente puede ser para otra feature o escenario
    #determinar la mejor estrategia de busqueda que guiara mi investigacion

    # Como la construccion de la cadena de busqueda es manual (es parte del proceso) se asume como obvio que se puede crear
    Antecedentes:
        Dado que estoy asignado a un proyecto de investigación
        Y el proyecto tiene como framework investigativo a "PICO"

    Escenario: Probar sugerencia de cadena de busqueda
        Dado que tengo al menos una pregunta de investigación "READY_TO_SEND"
        Y he identificado las palabras clave de la pregunta
        Cuando pruebe una sugerencia de cadena de búsqueda para la pregunta
        Entonces obtendré los artículos resultantes de esa cadena de búsqueda    
