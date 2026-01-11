# Created by Sebastián Jiménez
# language: es

Característica: Distribución aleatoria de estudios
  Como director de un proyecto de investigación
  quiero distribuir aleatoriamente y de forma balanceada los papers entre los investigadores,
  para garantizar revisión en paralelo y trazabilidad entre metadata y full text.

  Esquema del escenario: Distribución de papers tomando en cuenta carga horaria
    Dado investigadores con cargas horarias definidas:
      """
        <cargas_horarias>
      """
    Y papers con un número específico de hojas:
      """
        <hojas_por_paper>
      """
    Y que cada paper debe asignarse <total_revisiones_paper> veces a revisores distintos
    Entonces cada paper debe tener <total_revisiones_paper> revisores distintos
    Y ningún investigador debe recibir asignaciones repetidas del mismo paper
    Y la distribución resultante debe ser:
      """
        <distirbución_esperada>
      """

    Ejemplos:
      | cargas_horarias             | hojas_por_paper              | total_revisiones_paper | distirbución_esperada |
      | {"I1": 10,"I2": 2,"I3": 20} | {"P1":12, "P2": 6, "P3": 18} | 2                      |                       |



