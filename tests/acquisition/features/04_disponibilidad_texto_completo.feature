# language: es
@modulo:busqueda @componente:texto-completo @mvp
Característica: Acceso al texto completo de estudios para análisis profundo
  Como investigador
  Quiero obtener el documento completo de los estudios relevantes
  Para poder leerlos, extraer datos y evaluar su calidad metodológica

  Antecedentes:
    Dado que existen estudios con metadatos consolidados de mi revisión sistemática

  @texto-completo @acceso-publico
  Escenario: Obtener texto completo cuando está disponible públicamente
    Dado que un estudio tiene el texto completo de acceso público
    Cuando solicito obtener el documento
    Entonces el sistema descarga automáticamente el archivo
    Y valida la integridad del documento
    Y el estudio queda marcado como "texto_completo_disponible"
    Y se registra el origen del texto como "automático"

  @texto-completo @busqueda-alternativa
  Escenario: Buscar en fuentes alternativas cuando no está público en la fuente original
    Dado que un estudio no tiene acceso público en su fuente original
    Cuando el sistema intenta obtener el texto completo
    Entonces si encuentra el documento en una fuente alternativa, lo descarga
    Y el estudio queda marcado como "texto_completo_disponible"
    Y se registra desde qué fuente alternativa se obtuvo el texto

  @texto-completo @manual
  Escenario: Cargar manualmente el texto completo cuando no está disponible automáticamente
    Dado que un estudio no pudo obtenerse automáticamente en ninguna fuente
    Cuando cargo manualmente el archivo del texto completo
    Entonces el sistema valida el formato e integridad del archivo
    Y vincula el documento al estudio correspondiente
    Y el estudio queda marcado como "texto_completo_disponible"
    Y se registra el origen del texto como "manual"




