# Created by Sebastián Jiménez
# language: es
# Clickup task: https://app.clickup.com/t/86adrzehp

Característica: Inicio de fase de discusión
  Como director de un proyecto de investigación
  quiero monitorear el progreso de revisión y enviar recordatorios cuando sea necesario
  para asegurar que los investigadores mantengan el ritmo antes de iniciar la fase de discusión

  Esquema del escenario: La fase de selección terminó y el director visualiza los papers pendientes y toma una decisión
    Dado que la fase de "selección" inicia el "<fecha_inicio>" y finaliza el "<fecha_fin>"
    Y hoy es "<fecha_actual>"
    Cuando consulte la información del proyecto
    Entonces el sistema debe operar en modo "<modo>"
    Y deben estar habilitadas las acciones "<acciones_habilitadas>"

    Ejemplos:
      | fecha_inicio | fecha_fin  | fecha_actual | modo       | acciones_habilitadas                 |
      | 2024-11-01   | 2024-11-15 | 2024-11-14   | en_curso   | seguimiento_por_investigador         |
      | 2024-11-01   | 2024-11-15 | 2024-11-16   | finalizado | decisiones_sobre_estudios_pendientes |
