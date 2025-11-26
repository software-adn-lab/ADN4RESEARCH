# language: es
@modulo:busqueda @componente:consolidacion @mvp
Característica: Consolidación y completado de metadatos de estudios
  Como investigador
  Quiero que los estudios descubiertos tengan metadatos completos y normalizados
  Para poder aplicar criterios de inclusión/exclusión con información confiable

  Antecedentes:
    Dado que existe un resultado de descubrimiento con estudios de múltiples fuentes

  @consolidacion @automatico
  Escenario: Consolidación automática de estudios con metadatos faltantes
    Cuando solicito consolidar los estudios descubiertos
    Entonces el sistema completa los metadatos faltantes consultando las fuentes académicas
    Y normaliza los formatos de DOI, autores y fechas
    Y cada estudio queda marcado con su estado de consolidación: completo, parcial o fallido
    Y se proporciona un resumen del proceso de consolidación

  @consolidacion @manual
  Escenario: Completar metadatos manualmente cuando la consolidación automática falla
    Dado que un estudio no pudo consolidarse completamente de forma automática
    Cuando ingreso manualmente los metadatos faltantes del estudio
    Entonces el sistema actualiza el registro, valida el formato y marca el estudio como consolidado
    Y se mantiene trazabilidad indicando qué campos son automáticos y cuáles manuales