# language: es
Característica: Refinamiento del protocolo de extracción
  Para garantizar que la extracción cubre todos los aspectos críticos del protocolo de extracción,
  Como Dueño de la investigación,
  Quiero definir y aprobar el conjunto de tags que serán utilizados obligatoriamente.

  Antecedentes:
    Dado que la fase de extracción está activa

  Esquema del escenario: Extracción obligatoria de Tags Deductivos acorde a su relación con Preguntas de Investigación
    Dadas las Preguntas de Investigación del proyecto son: <PIs_Existentes>
    Cuando el Owner define los Tags Deductivos y las PIs relacionadas: <Tags_Definidos>
    Entonces se debe marcar el conjunto de tags obligatorios como: <Tags_Obligatorios_Esperados>
    Y se debe determinar la visibilidad de la lista de tags para los Researchers como: <Visibilidad_Esperada>

    Ejemplos:
      | PIs_Existentes | Tags_Definidos | Tags_Obligatorios_Esperados | Visibilidad_Esperada |
      | ["Cómo afectan las nuevas tecnologías a la eficiencia operativa de las empresas?", "Cuáles son los costos asociados con la implementación de tecnologías emergentes?"] | [{"Tag": "Eficiencia", "PI_Relacionada": "<Ninguna>"}, {"Tag": "Costos", "PI_Relacionada": "<Ninguna>"}, {"Tag": "Tiempo", "PI_Relacionada": "<Ninguna>"}, {"Tag": "Impacto Ambiental", "PI_Relacionada": "<Ninguna>"}] | [] | No Pública |
      | ["Cómo afectan las nuevas tecnologías a la eficiencia operativa de las empresas?", "Cuáles son los costos asociados con la implementación de tecnologías emergentes?"] | [{"Tag": "Eficiencia", "PI_Relacionada": "Cómo afectan las nuevas tecnologías a la eficiencia operativa de las empresas?"}, {"Tag": "Costos", "PI_Relacionada": "Cuáles son los costos asociados con la implementación de tecnologías emergentes?"}, {"Tag": "Tiempo", "PI_Relacionada": "<Ninguna>"}, {"Tag": "Impacto Ambiental", "PI_Relacionada": "<Ninguna>"}] | ["Eficiencia", "Costos"] | Pública |

  Esquema del escenario: Validar que un paper no puede marcarse como "Completo" si faltan extracciones obligatorias
    Dada una lista de tags obligatorios para la extracción: <Tags_Obligatorios>
    Y se han registrado las extracciones para los siguientes tags: <Tags_Extraidos>
    Cuando el investigador intenta marcar el paper como "Completo"
    Entonces el estado del paper debe ser "<Estado_Esperado>"
    Y se debe notificar al investigador sobre los tags pendientes: <Tags_Pendientes_Esperados>

    Ejemplos:
      | Tags_Obligatorios | Tags_Extraidos | Estado_Esperado | Tags_Pendientes_Esperados |
      | ["Eficiencia", "Costos", "Tiempo", "Impacto Ambiental"] | ["Tiempo", "Impacto Ambiental"] | Pendiente | ["Eficiencia", "Costos"] |
      | ["Eficiencia", "Costos", "Tiempo"] | ["Eficiencia", "Costos", "Tiempo"] | Completo | [] |
