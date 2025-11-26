# language: es
Característica: Gestión de Tags Inductivos (Propuesta y Moderación)
  Para capturar conceptos emergentes durante la lectura sin modificar el protocolo compartido,
  Como Investigador, quiero crear tags personales instantáneos.
  Como Dueño, quiero moderar estos tags para estandarizarlos si aportan valor a todo el equipo.

  Antecedentes:
    Dado que la fase de extracción está activa

  Escenario: Investigador crea un tag inductivo para uso personal inmediato
    Dado que el Investigador "Juan" está extrayendo datos de un estudio
    Cuando "Juan" crea un nuevo tag inductivo llamado "Resistencia al cambio"
    Entonces se debe registrar el tag con:
      | Nombre                | Propietario | Estado                  | Visibilidad |
      | Resistencia al cambio | Juan        | Pendiente de Aprobación | Privada     |
    Y el tag "Resistencia al cambio" debe estar disponible para ser usado por "Juan" en otros papers
    Pero el tag "Resistencia al cambio" NO debe aparecer en la lista de tags del Investigador "Ana"

  Esquema del escenario: Moderación de tags propuestos por el Owner
    Dado que existe un tag "<Nombre_Tag>" propuesto por "Juan" con estado "Pendiente de Aprobación"
    Cuando el Owner decide <Accion_Owner> la propuesta
    Entonces el estado del tag cambia a "<Estado_Final>"
    Y la visibilidad para el resto del equipo (ej. "Ana") pasa a ser "<Visibilidad_Equipo>"

    Ejemplos:
      | Nombre_Tag        | Accion_Owner | Estado_Final | Visibilidad_Equipo |
      | Gestión de Crisis | Aprobar      | Aprobado     | Pública            |
      | Datos confusos    | Rechazar     | Rechazado    | Privada            |

  Escenario: Fusión de tags inductivos duplicados al aprobar
    Dada la existencia de los siguientes tags propuestos pendientes:
      | Nombre_Tag   | Propietario |
      | Costo oculto | Juan        |
      | Costos oc.   | Ana         |
    Cuando el Owner aprueba "Costo oculto" y lo marca como equivalente a "Costos oc."
    Entonces ambos tags se fusionan en un único tag global "Costo oculto"
    Y las extracciones que "Ana" hizo con "Costos oc." ahora deben estar asociadas al tag aprobado "Costo oculto"
