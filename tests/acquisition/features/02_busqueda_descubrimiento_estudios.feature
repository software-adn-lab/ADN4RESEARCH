# language: es
@modulo:busqueda @componente:descubrimiento @mvp
Característica: Descubrimiento y consolidación de estudios desde múltiples fuentes
  Como investigador
  Quiero ejecutar el descubrimiento de estudios sobre una estrategia normalizada
  Para obtener un listado consolidado sin duplicados y conocer qué fuentes fueron consultadas

  Antecedentes:
    Dado que el sistema soporta las fuentes "Scopus" e "IEEE Xplore"

  @descubrimiento @mvp
  Esquema del escenario: El descubrimiento consulta solo fuentes ready y consolida resultados
    Dada una estrategia normalizada con id "<id>"
    Y las traducciones para esa estrategia tienen los siguientes estados:
      | fuente      | estado          |
      | Scopus      | <estado_scopus> |
      | IEEE Xplore | <estado_ieee>   |
    Cuando ejecuto el descubrimiento para la estrategia "<id>"
    Entonces obtengo un listado de estudios
    Y el listado no contiene duplicados
    Y cada estudio tiene título, enlace y fuente
    Y obtengo un resumen con id_estrategia "<id>" y resultado "<resultado>"

    Ejemplos:
      | id       | estado_scopus | estado_ieee   | resultado |
      | norm-001 | ready         | ready         | complete  |
      | norm-002 | ready         | not_supported | partial   |
      | norm-003 | not_supported | ready         | partial   |
