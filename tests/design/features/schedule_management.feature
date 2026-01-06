# language: es
Característica: Gestión dinámica del cronograma 
  Como owner del proyecto de investigacion
  Quiero que el tiempo disponible para las etapas del diseño se ajuste a mi planificacion
  Para que el equipo cumpla con el cronograma programado

  Antecedentes:
    Dado que existe un plan de diseño aprobado con las siguientes fechas límite:
      | etapa               | fecha_inicio_plan | fecha_fin_plan | dias_planificados |
      | RQ_CREATION         | 2025-01-01        | 2025-01-05     | 5                 |
      | RQ_DISCUSSION         | 2025-01-06        | 2025-01-10     | 5                 |
      | CRITERIA_DEFINITION       | 2025-01-11        | 2025-01-15     | 5                 |

  # En esta de aqui se excluye a la etapa de RQ_CREATION porque si es obligado que se cierre si ya no hay tiempo
  Escenario: Reducción de tiempo disponible por retraso en etapa previa
    Dado que la fecha actual es "2025-01-12"
    Y que la etapa activa es "RQ_DISCUSSION"
    Y que se ha aprobado una pregunta
    Cuando el owner consolide la etapa "RQ_DISCUSSION"
    Entonces la etapa "CRITERIA_DEFINITION" inicia realmente el "2025-01-12"
    Y la fecha fin planificada de "CRITERIA_DEFINITION" se mantiene en "2025-01-15"
    Y el tiempo disponible restante para "CRITERIA_DEFINITION" debe ser de 3 días
    
  Esquema del escenario: Consolidación anticipada reprograma el inicio de la siguiente etapa
    Dado que la fecha actual es "2025-01-03"
    Y que la etapa activa es "<etapa_actual>"
    Y que se ha aprobado una pregunta
    Cuando el owner consolide la etapa "<etapa_actual>"
    Entonces la etapa "<siguiente_etapa>" inicia realmente el "2025-01-03"
    Y la etapa activa debe ser "<siguiente_etapa>"

    Ejemplos:
      | etapa_actual  | siguiente_etapa     |
      | RQ_CREATION   | RQ_DISCUSSION       |
      | RQ_DISCUSSION | CRITERIA_DEFINITION |

  Escenario: Cierre automático de RQ_CREATION cuando pasa la fecha límite
    Dado que la etapa activa es "RQ_CREATION"
    Y que la fecha actual es "2025-01-05"
    Cuando el sistema realice la verificación de fechas límite
    Entonces la etapa activa debe ser "RQ_DISCUSSION"
    Y la etapa "RQ_DISCUSSION" inicia realmente el "2025-01-05"