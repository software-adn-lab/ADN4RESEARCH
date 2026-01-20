# Created by Sebastián Jiménez
# language: es
# Descripción:

Característica: Resolución de discrepancias
  Como director del proyecto
  quiero disponer de mecanismos formales para resolver discrepancias entre evaluadores sobre la inclusión o exclusión de un estudio
  para mantener la trazabilidad, consistencia y avance del proceso de selección del SR

  Esquema del escenario: Existe discrepancia y se resuelve mediante un mecanismo en "<etapa>"
    Dado un proyecto de seleccion con un paper en conflicto de "<etapa>"
    Cuando el director resuelve la discrepancia mediante "<mecanismo>" con decision "<decision_final>"
    Entonces el conflicto queda marcado como resuelto con metodo "<metodo_esperado>"
    Y la decision final del paper es "<decision_final>"
    Y el paper ya no aparece como conflicto pendiente para "<etapa>"

    Ejemplos:
      | etapa     | mecanismo      | decision_final | metodo_esperado |
      | SCREENING | tercer_revisor | INCLUDED       | THIRD_REVIEWER  |
      | SCREENING | voto_owner     | EXCLUDED       | OWNER_VOTE      |
      | FULL_TEXT | tercer_revisor | INCLUDED       | THIRD_REVIEWER  |
      | FULL_TEXT | voto_owner     | EXCLUDED       | OWNER_VOTE      |
