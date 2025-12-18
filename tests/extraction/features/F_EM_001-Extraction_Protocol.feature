# language: es
Característica: Refinamiento del protocolo de extracción
  Para garantizar que la extracción cubre todos los aspectos críticos del protocolo de extracción,
  Como Dueño de la investigación,
  Quiero definir y aprobar el conjunto de tags que serán utilizados obligatoriamente.

#PROTOCOLO DE EXTRACCION
#Puede ser precondicion que la fase de extraccion haya terminado
  Esquema del escenario: Validación de cobertura de Preguntas de Investigación para visibilidad pública
    Dado que existe una Fase de Extracción en configuración
    Y las Preguntas de Investigación del proyecto son: <RQ_list>
    Cuando el Owner define los Tags Deductivos y las PIs relacionadas: <tag_list>
    Entonces se debe marcar el conjunto de tags obligatorios como: <mandatory_tags>
    Y el estado sugerido de la fase debe mantenerse en: <status_phase>

    Ejemplos:
      | RQ_list                                              | tag_list                                                                                                 | mandatory_tags                          | status_phase |
      | ["¿Cómo afecta la IA?", "¿Costo de implementación?"] | [{"Tag": "Tecnología", "PI": "¿Cómo afecta la IA?"}, {"Tag": "Presupuesto", "PI": "¿Costo de implementación?"}] | ["Tecnología", "Presupuesto"]           | OPEN         |
      | ["¿Cómo afecta la IA?", "¿Costo de implementación?"] | [{"Tag": "Tecnología", "PI": "¿Cómo afecta la IA?"}, {"Tag": "General", "PI": "<Ninguna>"}]                     | ["Tecnología"]                          | CONFIG       |
      | ["¿Cómo afecta la IA?"]                              | [{"Tag": "General", "PI": "<Ninguna>"}]                                                                         | []                                      | CONFIG       |


  Esquema del escenario: Validar que un paper no puede marcarse como "Completo" si faltan extracciones obligatorias
    Dado que existe una Fase de Extracción en estado "Abierta"
    Y una lista de tags obligatorios para la extracción: <mandatory_tags>
    Y se han registrado las extracciones para los siguientes tags: <extracteded_tags>
    Cuando el investigador intenta marcar el paper como "Completo"
    Entonces el estado del paper debe ser <paper_status>
    Y se debe notificar al investigador sobre los tags pendientes: <missing_tags>

    Ejemplos:
      | mandatory_tags                                          | extracteded_tags                   | paper_status | missing_tags             |
      | ["Eficiencia", "Costos", "Tiempo", "Impacto Ambiental"] | ["Tiempo", "Impacto Ambiental"]    | Pendiente    | ["Eficiencia", "Costos"] |
      | ["Eficiencia", "Costos", "Tiempo"]                      | ["Eficiencia", "Costos", "Tiempo"] | Completo     | []                       |


