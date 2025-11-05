# language: es
Caracteristica: Build Search String
    Como investigador
    Quiero construir cadenas de busqueda basado en sugerencias
    Para optimizar el tiempo que gasto en construirlas
    # Posteriormente puede ser para otra feature o escenario
    determinar la mejor estrategia de busqueda que guiara mi investigacion

    # Como la construccion de la cadena de busqueda es manual (es parte del proceso) se asume como obvio que se puede crear
    Escenario: Probar sugerencia de cadena de busqueda
        Dado que tengo al menos una pregunta de investigacion
        Y he identificado los sinonimos de cada palabra clave de la pregunta
        Cuando pruebe una sugerencia de cadena de busqueda para la pregunta
        Entonces obtendre los articulos resultantes de esa cadena de busqueda    
