# language: es
Característica: Validar preguntas de investigación de los investigadores    
    Como owner de un proyecto de investigación
    Quiero validar las preguntas de investigación creadas por los investigadores
    Para asegurar una guía apropiada de la revisión sistemática de mi proyecto

    Antecedentes:
        Dado que la etapa de "discusión" esta activa en la fase de diseño

    # Consolidar: Convertir algo en definitivo y estable.
    # En el negocio considero que consolidar es dejar las preguntas de investigacion aprobadas como guia
    # de mi proyecto de investigacion. Ademas, cambiamos una fase de diseno cuando consolidamos
    Escenario: Consolidar la selección final de preguntas de investigación
        Dado que existen preguntas en el proyecto como:
            | pregunta      | estado    |
            | Pregunta A    | APPROVED  |
            | Pregunta B    | SUGGESTED |
            | Pregunta C    | REJECTED  |
        Cuando consolide el estado de las preguntas de investigación de mi proyecto
        Entonces las preguntas de investigación "APPROVED" deben ser parte del protocolo de diseño del proyecto
        Y las preguntas "SUGGESTED" deben cambiar automáticamente a "REJECTED"
        Y solo el owner del proyecto podrá editar las preguntas o su estado, bloqueando a los investigadores

