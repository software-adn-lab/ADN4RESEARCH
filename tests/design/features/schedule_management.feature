# language: es
Característica: Gestión dinámica del cronograma 

  Antecedentes:
    Dado que existe un plan de diseño aprobado con las siguientes fechas límite:
      | etapa               | fecha_inicio_plan | fecha_fin_plan | dias_planificados |
      | RQ_DISCUSSION         | 2025-01-01        | 2025-01-05     | 5                 |
      | CRITERIA_DEFINITION       | 2025-01-06        | 2025-01-10     | 5                 |

  Escenario: Reducción de tiempo disponible por retraso en etapa previa
    Dado que la fecha actual es "2025-01-07"
    Y que la etapa activa es "RQ_DISCUSSION"
    Y que se ha aprobado una pregunta
    Cuando el owner consolide la etapa "RQ_DISCUSSION"
    Entonces la etapa "CRITERIA_DEFINITION" inicia realmente el "2025-01-07"
    Y la fecha fin planificada de "CRITERIA_DEFINITION" se mantiene en "2025-01-10"
    Y el tiempo disponible restante para "CRITERIA_DEFINITION" debe ser de 3 días