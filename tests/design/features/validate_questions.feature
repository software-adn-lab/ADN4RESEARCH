# language: es
Característica: Validar preguntas de investigación de los investigadores    
    Como owner de un proyecto de investigación
    Quiero validar las preguntas de investigación creadas por los investigadores
    Para asegurar una guía apropiada de la revisión sistemática de mi proyecto

    Antecedentes:
        Dado que el proyecto se encuentra en la fase de "Diseño" y etapa de "Discusión"
        
    Escenario: Consolidar la selección final de preguntas de investigación
        Dado que existen las siguientes preguntas en el proyecto:
            | pregunta      | estado    |
            | Pregunta A    | APPROVED  |
            | Pregunta B    | SUGGESTED |
            | Pregunta C    | REJECTED  |
        Cuando consolide el estado de las preguntas de investigación de mi proyecto
        Entonces las preguntas de investigación "APPROVED" deben ser parte del protocolo de diseño del proyecto
        Y las preguntas "SUGGESTED" deben cambiar automáticamente a "REJECTED"
        Y solo el owner del proyecto podrá editar las preguntas o su estado, bloqueando a los investigadores

