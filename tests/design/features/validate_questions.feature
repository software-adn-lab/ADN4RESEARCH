# language: es
Característica: Validar preguntas de investigación de los investigadores    
    Como owner de un proyecto de investigación
    Quiero validar las preguntas de investigación sugeridas por los investigadores
    Para asegurar una guía apropiada al proyecto de investigación

        
    Escenario: Aprobar el estado de las preguntas de investigación
        Dado la etapa de "discusión de preguntas de investigación" está abierta
        Y que existen preguntas de investigación sugeridas por los investigadores
        Cuando apruebe el estado general de las acciones sugeridas de las preguntas de investigación
        #Entonces la etapa se cerrará
        Y se mostrarán las preguntas de investigación que fueron aprobadas
