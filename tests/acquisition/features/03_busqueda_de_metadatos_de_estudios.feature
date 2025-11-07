# language: es
@modulo:busqueda @componente:metadatos @mvp
Característica: Enriquecimiento de estudios con metadatos completos para análisis detallado
  Como investigador 
  Quiero obtener información detallada de cada estudio encontrado en el descubrimiento
  Para poder evaluar su relevancia y aplicar criterios de inclusión/exclusión informados

  Antecedentes:
    Dado que existe un resultado de descubrimiento previo con un listado de estudios
    Y cada estudio del listado incluye al menos: título, enlace y fuente de origen

  @metadatos @automatico
  Escenario: Enriquecimiento automático de metadatos desde las fuentes académicas
    Cuando solicito obtener los metadatos completos de los estudios
    Entonces el sistema consulta automáticamente las fuentes académicas para cada estudio
    Y genera un registro canónico con la información obtenida
    Y cada estudio queda marcado según la completitud de su información
    Y se registra la fuente de origen de cada metadato obtenido
    Y el sistema proporciona un resumen del proceso indicando cuántos estudios fueron consolidados

  @metadatos @manual
  Escenario: Completar metadatos manualmente cuando la obtención automática falla
    Dado que algunos estudios no pudieron consolidarse automáticamente
    Cuando ingreso manualmente la información faltante de un estudio
    Entonces el sistema actualiza el registro con los metadatos proporcionados
    Y el estudio queda marcado como consolidado
    Y se mantiene trazabilidad indicando qué campos son automáticos y cuáles manuales