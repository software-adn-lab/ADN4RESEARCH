# language: es
@modulo:busqueda @componente:descubrimiento @mvp
Característica: Búsqueda y consolidación inicial de estudios desde múltiples fuentes
  Como investigador 
  Quiero ejecutar mi estrategia de búsqueda en diferentes bases de datos y obtener un listado unificado
  Para tener una vista consolidada de todos los estudios potencialmente relevantes

  Antecedentes:
    Dado que el sistema soporta las fuentes "Scopus" e "IEEE Xplore"
    Y existe una estrategia normalizada identificada como "<id_estrategia>"
    Y existen traducciones por fuente asociadas a esa estrategia

  @descubrimiento @mvp
  Esquema del escenario: Descubrimiento consolida resultados y resume el estado por fuente
    Dada una estrategia previamente normalizada con identificador "<id>"
    Y las traducciones preparadas tienen los siguientes estados:
      | fuente       | estado          |
      | Scopus       | <estado_scopus> |
      | IEEE Xplore  | <estado_ieee>   |
    Cuando ejecuto el descubrimiento
    Entonces obtengo un listado de estudios encontrados
    Y cada estudio incluye título, enlace y fuente de origen
    Y el sistema me proporciona un resumen con:
      """
      id_estrategia = "<id>",
      fuentes_consultadas = <consultadas>,
      fuentes_no_consideradas = <no_consideradas>,
      total_por_fuente = {...},
      total_bruto >= 0,
      total_unicos >= 0,
      resultado = "<resultado>"
      """

    Ejemplos:
      | id        | estado_scopus | estado_ieee   | consultadas                      | no_consideradas                                   | resultado  |
      | norm-001  | lista         | lista         | ["Scopus","IEEE Xplore"]         | []                                                | completo   |
      | norm-002  | lista         | no compatible | ["Scopus"]                       | [{"fuente":"IEEE Xplore","motivo":"no compatible"}] | parcial    |
      | norm-003  | lista         | lista         | ["Scopus","IEEE Xplore"]         | []                                                | completo   |
