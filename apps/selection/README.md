# Modulo de seleccion

## Proposito y alcance
Este modulo implementa la fase de seleccion de estudios en el flujo de un SR
con tres funcionalidades principales: distribucion de estudios, screening de
informacion y discusion para resolucion de discrepancias. El enfoque prioriza
trazabilidad, consistencia de decisiones y avance controlado entre subfases.

El modulo se integra con:
- Disenio: criterios de inclusion/exclusion y protocolo.
- Adquisicion: metadatos y PDFs de estudios.
- Extraccion: entrega de la lista final de estudios aprobados.

## Estructura general
- Backend (Django): `apps/selection/`
  - `features/distribution/`: distribucion y overview.
  - `features/screening/`: revisiones de metadata y fulltext.
  - `features/discussion/`: conflictos y resolucion.
  - `services/`: facade para uso externo.
- UI: `ui/selection/templates/` y `ui/selection/scripts/`.
- Tests BDD: `tests/selection/features/` y `tests/selection/steps/`.

## Comunicacion con otros modulos
La comunicacion entre modulos se implementa como integracion directa a nivel
de servicios/facades, evitando acoplamientos en UI y manteniendo un contrato
de datos estable. Esto permite que seleccion consuma y exponga informacion
sin depender de detalles internos de diseno, adquisicion o extraccion.

### Diseno -> Seleccion
Seleccion requiere los criterios de inclusion/exclusion definidos en diseno
para justificar decisiones. La obtencion se realiza mediante el API del modulo
de diseno y se normaliza el formato para su uso consistente:
- Punto de integracion: `apps.design.api.get_design_protocol`.
- Uso principal: `apps/selection/features/screening/metadata/views.py` y
  `apps/selection/features/screening/fulltext/views.py` (lista de criterios),
  ademas de `apps/selection/features/discussion/views.py` (criterios para
  tercer revisor en discusion).
- Estrategia: normalizacion de identificador y etiqueta para tolerar cambios
  en el origen, con fallback a listas vacias si no hay disponibilidad.

### Adquisicion -> Seleccion
Seleccion consume metadatos y PDFs desde adquisicion para dos propósitos:
1) Distribucion y screening (metadata y abstract).
2) Fulltext review (acceso a PDF y conteo de paginas).
- Punto de integracion: `apps.project.facade.get_project_facade` para obtener
  estudios del proyecto (metadata), y `apps.acquisition.facade.get_acquisition_facade`
  para estado de PDFs y descargas.
- Uso principal: `apps/selection/features/distribution/services.py`,
  `apps/selection/features/distribution/fulltext_overview.py` y
  `apps/selection/features/screening/fulltext/views.py`.
- Estrategia: tolerancia a datos incompletos (fallback de metadatos y
  conteo por defecto cuando el PDF no esta disponible).

### Seleccion -> Extraccion
La salida de seleccion es la lista de estudios aprobados en fulltext, expuesta
de forma estable para ser consumida por extraccion:
- Punto de integracion: `apps/selection/services/facade.py`.
- Endpoint de apoyo: `apps/selection/features/distribution/screening.py`
  (API `approved_papers_api`).
- Estrategia: la lista se calcula considerando decisiones finales y conflictos
  resueltos, garantizando consistencia antes de iniciar extraccion.

## Modelo de datos (resumen)
Las entidades clave mantienen la trazabilidad entre asignacion, decision y
resolucion:
- `SelectionPhase`: fase y subfases (screening, fulltext, discussion).
- `PaperAssignment`: asignacion de estudio a investigador, por etapa, con
  bandera `is_third_reviewer` para discrepancias.
- `PaperReview`: decision individual (`INCLUDED`, `EXCLUDED`, `PENDING`) con
  notas y criterio.
- `ConflictResolution`: registro de discrepancia, metodo de resolucion, decision
  final y auditoria (resuelto por, fecha).

Estas entidades permiten separar: (a) asignacion, (b) decision individual, y
(c) decision final cuando existe conflicto.

## Funcionalidad 1: Distribucion de estudios

### Objetivo
Asignar estudios a investigadores de forma balanceada segun carga de trabajo,
manteniendo independencia de revisiones y evitando duplicidad por investigador.

### Estrategia implementada
Se usa un algoritmo voraz (greedy) con capacidad proporcional:
1) Se calcula la carga total: sumatoria de "peso" de estudios por numero de
   revisiones requeridas.
2) La capacidad de cada investigador es proporcional a sus horas de carga.
3) Se asignan primero los estudios mas pesados al investigador con mayor
   capacidad disponible, evitando asignar el mismo paper a la misma persona.

### Metricas de carga por etapa
- Screening: conteo de palabras del abstract (fallback al titulo si no hay
  abstract).
- Fulltext: conteo de paginas del PDF (fallback a valores por defecto cuando
  no existe pdf o metadato confiable).

### Decisiones de implementacion
- Se incluye al owner como posible revisor si tiene carga registrada.
- Se elimina toda asignacion previa al redistribuir, para evitar inconsistencias
  y facilitar reproducibilidad del estado.
- La cantidad de revisiones por paper se valida (valores permitidos: 2, 3, 4)
  y se normaliza ante valores invalidos.
- La distribucion se devuelve como mapa `username -> [paper_id]` para simplificar
  la creacion de `PaperAssignment`.

### Reglas y validaciones
- No se permiten asignaciones duplicadas del mismo paper al mismo investigador.
- La distribucion solo se ejecuta si existen investigadores con carga y papers
  disponibles.
- La subfase cambia a `IN_PROGRESS` tras distribucion exitosa.

### Evidencia en codigo
- Algoritmo: `apps/selection/features/distribution/services.py`.
- Distribucion fulltext: `apps/selection/features/distribution/services.py`.
- Vistas de distribucion: `apps/selection/features/distribution/screening.py`,
  `apps/selection/features/distribution/fulltext_overview.py`.

### Pruebas
BDD de distribucion: `tests/selection/features/f_sm_01_paper_distribution.feature`
con steps en `tests/selection/steps/f_sm_01_paper_distribution.py`.

## Funcionalidad 2: Screening de informacion

### Objetivo
Permitir decisiones de inclusion/exclusion basadas en metadata (abstract) y en
fulltext, con control de progreso y validaciones de consistencia.

### Flujo principal
1) El investigador accede a su lista de asignaciones.
2) Registra decision (`INCLUDED`/`EXCLUDED`) y criterio asociado.
3) El sistema almacena la decision y la muestra en el overview.

### Decisiones de implementacion
- Se exige criterio para decisiones finales (include/exclude). Esto refuerza la
  trazabilidad de por que un estudio fue aceptado o descartado.
- `PENDING` se mantiene como estado inicial, y se usa para calcular pendientes.
- Los criterios se consumen desde el protocolo de disenio con normalizacion de
  formato; se agregan criterios extra para exclusiones comunes.
- Se prioriza mostrar pendientes primero para mejorar eficiencia del usuario.

### Acciones del owner
En el overview, el owner puede:
- Enviar recordatorios a revisores con pendientes.
- Aplicar decisiones masivas (include/exclude) para pendientes.
- Pasar a discusion cuando existen discrepancias.

### Estado y control de avance
La finalizacion de screening requiere:
1) No tener revisiones pendientes.
2) No tener discrepancias sin resolver.

Esto protege la transicion a fulltext y evita sesgos por decisiones inconclusas.

### Evidencia en codigo
- Screening metadata: `apps/selection/features/screening/metadata/views.py`.
- Fulltext review: `apps/selection/features/screening/fulltext/views.py`.
- Control de avance: `apps/selection/features/distribution/screening.py`.

### Pruebas
BDD de modo/recordatorios: `tests/selection/features/f_sm_02_screening_reminder.feature`
con steps en `tests/selection/steps/f_sm_02_screening_reminder.py`.

## Funcionalidad 3: Discusion y resolucion de discrepancias

### Objetivo
Resolver inconsistencias entre revisores mediante mecanismos formales, con
registro de decision final y trazabilidad del proceso.

### Deteccion de conflictos
Un conflicto existe cuando, para un mismo paper y etapa, hay decisiones
diferentes entre revisores (excluyendo `PENDING`). La deteccion se realiza
dinamicamente y omite conflictos ya resueltos.

### Mecanismos de resolucion
Se implementan dos estrategias equivalentes:
- **Tercer revisor**: se asigna un nuevo revisor elegible; su decision desempata
  y se almacena como decision final.
- **Voto final del owner**: el director emite la decision final, quedando
  registrada con metodo `OWNER_VOTE`.

Ambos mecanismos actualizan `ConflictResolution` con decision final, metodo,
resuelto por y timestamp. El paper deja de aparecer en la lista de conflictos.

### Decisiones de implementacion
- El tercer revisor no puede haber revisado previamente ese paper.
- La resolucion queda registrada aunque el conflicto haya sido detectado
  previamente, lo que permite idempotencia en el flujo.
- Se usa el mismo servicio para screening y fulltext, con mapeo explicito de
  etapas (`SCREENING` vs `FULL_TEXT`).

### Integracion con el flujo
La resolucion de conflictos es condicion necesaria para:
- Finalizar screening y habilitar fulltext.
- Finalizar fulltext y emitir lista final de aprobados.

### Evidencia en codigo
- Servicio: `apps/selection/features/discussion/services.py`.
- Vistas: `apps/selection/features/discussion/views.py`.
- Templates: `ui/selection/templates/discussion/`.

### Pruebas
BDD de resolucion de discrepancias: `tests/selection/features/f_sm_03_discrepancy_resolution.feature`
con steps en `tests/selection/steps/f_sm_03_discrepancy_resolution.py`.

## Consideraciones transversales
- **Trazabilidad**: decisiones individuales y finales quedan persistidas en
  tablas separadas para auditoria.
- **Consistencia**: el sistema bloquea transiciones si existen pendientes o
  discrepancias sin resolver.
- **Extensibilidad**: el servicio de discrepancias es reutilizable para nuevas
  etapas, con mapeo de etapa y decision.
- **Integracion**: el facade `apps/selection/services/facade.py` expone la lista
  de estudios aprobados para el modulo de extraccion.

## Limitaciones y supuestos
- Se asume disponibilidad de metadatos y PDFs desde adquisicion.
- La distribucion usa un algoritmo voraz, que no garantiza optimos globales
  pero ofrece una solucion eficiente y razonable.
- Los criterios de inclusion/exclusion provienen del modulo de disenio; si
  fallan, se manejan como listas vacias para no bloquear el flujo.
