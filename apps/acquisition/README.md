# Acquisition Module - Clean Architecture

Módulo de adquisición de documentos científicos siguiendo **Clean Architecture** y principios de **C4 Model (Component level)**.

---

## 📐 Arquitectura

Este módulo implementa **Hexagonal Architecture** (Ports & Adapters) con capas claramente definidas:

```
apps/acquisition/
├─ domain/                      # ⭐ Capa de Dominio - Reglas de negocio puras
│  ├─ models.py                 # Entidades y Value Objects (NormalizedStrategy, MainTerm, YearFilter)
│  ├─ exceptions.py             # Excepciones de dominio (DomainValidationError)
│  ├─ interfaces/               # Puertos (contratos/interfaces)
│  │  ├─ i_academic_connector.py
│  │  ├─ i_document_storage.py
│  │  ├─ i_event_bus.py
│  │  └─ i_paper_repository.py
│  ├─ entities/                 # Entidades adicionales
│  │  ├─ paper.py
│  │  └─ search_strategy.py
│  ├─ events/                   # Eventos de dominio
│  │  └─ search_requested.py
│  └─ services/                 # Servicios de dominio
│     └─ translation/           # ⭐ Traductores de estrategias (reglas de negocio)
│        ├─ istrategy_translator.py     # Interfaz (puerto)
│        ├─ translation_result.py       # DTO
│        ├─ scopus_translator.py        # Implementación Scopus
│        └─ ieee_translator.py          # Implementación IEEE Xplore
│
├─ application/                 # ⭐ Capa de Aplicación - Casos de uso
│  ├─ services.py               # TranslationService (orquesta traductores, genera trace)
│  └─ exceptions.py             # Excepciones de aplicación (InvalidTargetError)
│
├─ adapters/                    # ⭐ Capa de Adaptadores - Infraestructura
│  ├─ inbound/                  # Adaptadores de entrada (API, CLI, Jobs, UI)
│  │  └─ (vacío - se poblará con endpoints REST, comandos CLI, etc.)
│  └─ outbound/                 # Adaptadores de salida (implementaciones de puertos)
│     ├─ connectors/            # Clientes de APIs externas
│     │  └─ base_connector.py
│     ├─ repositories/          # Implementaciones de persistencia
│     │  └─ mock_repository.py
│     ├─ storage/               # Almacenamiento de documentos
│     │  ├─ document_storage.py
│     │  └─ local_storage.py
│     ├─ messaging/             # Bus de eventos
│     │  ├─ event_bus.py
│     │  └─ mock_bus.py
│     ├─ download_manager/      # Gestor de descargas
│     └─ search_orchestrator/   # Orquestador de búsqueda
│
├─ tasks/                       # Tareas (Celery, cron) que llaman casos de uso
│  ├─ download_tasks.py
│  └─ search_tasks.py
│
├─ testing/                     # Utilidades de testing (assertions para BDD)
│  └─ assertions.py             # SyntaxValidator, LogicPreservationChecker, etc.
│
├─ migrations/                  # Migraciones de Django
├─ templates/                   # Templates de Django
├─ apps.py                      # Configuración de la app Django
├─ urls.py                      # URLs de la app
└─ README.md                    # Este archivo
```

---

## 🎯 Reglas de Dependencia (Dependency Rule)

**Fundamental**: Las dependencias apuntan **hacia adentro** (hacia el dominio).

```
┌─────────────────────────────────────────────────┐
│         Adapters (Inbound/Outbound)             │  ← Capa externa
│  Depende de: Application + Domain               │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│              Application (Casos de Uso)          │  ← Capa media
│  Depende de: Domain solamente                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│          Domain (Reglas de Negocio)             │  ← Núcleo
│  NO depende de NADA externo                     │
│  (ni Application, ni Adapters, ni Django)       │
└─────────────────────────────────────────────────┘
```

### ✅ Permitido

- `adapters/` → `application/` → `domain/`
- `tasks/` → `application/` → `domain/`
- `testing/` → cualquier capa (solo para tests)

### ❌ Prohibido

- `domain/` → `application/` (❌)
- `domain/` → `adapters/` (❌)
- `application/` → `adapters/` (❌)
- `domain/` → Django models, ORM, HTTP, etc. (❌)

---

## 🔄 Flujo de Ejecución - Caso de Uso: Traducción de Estrategia

### Diagrama de Secuencia (4 Pasos)

```
┌────────┐         ┌───────────────┐       ┌─────────────────┐      ┌──────────────────┐
│  Steps │         │  Application  │       │     Domain      │      │   Domain Service │
│  (BDD) │         │    Service    │       │   (Entities)    │      │   (Translator)   │
└───┬────┘         └───────┬───────┘       └────────┬────────┘      └─────────┬────────┘
    │                      │                        │                         │
    │ 1. translate()       │                        │                         │
    ├─────────────────────>│                        │                         │
    │                      │                        │                         │
    │                      │ 2. Selecciona traductor│                         │
    │                      │   según target         │                         │
    │                      ├────────────────────────┼─────────────────────────>
    │                      │                        │   3. translate(strategy)│
    │                      │                        │                         │
    │                      │                        │      (aplica reglas     │
    │                      │                        │       de negocio)       │
    │                      │                        │                         │
    │                      │<────────────────────────┼─────────────────────────┤
    │                      │   TranslationResult    │                         │
    │                      │   (query, warnings,    │                         │
    │                      │    steps, rules)       │                         │
    │                      │                        │                         │
    │  4. Retorna contrato │                        │                         │
    │     completo con     │                        │                         │
    │     trace            │                        │                         │
    │<─────────────────────┤                        │                         │
    │  {query, status,     │                        │                         │
    │   warnings, trace,   │                        │                         │
    │   target, metadata}  │                        │                         │
    │                      │                        │                         │
```

### Responsabilidades por Capa

| Capa | Componente | Responsabilidad |
|------|-----------|----------------|
| **Testing** | `traduccion_steps.py` | Orquesta el test (Given/When/Then) |
| **Application** | `TranslationService` | Selecciona traductor, genera trace, arma contrato |
| **Domain** | `ScopusTranslator` | Aplica reglas de negocio de Scopus (sintaxis, precedencia) |
| **Domain** | `NormalizedStrategy` | Representa estrategia inmutable validada |
| **Testing** | `SyntaxValidator`, etc. | Valida resultado observable |

---

## 🧩 Mapeo C3 → Carpetas

| Concepto C3 | Carpeta en este módulo | Descripción |
|------------|----------------------|-------------|
| **Use Cases** | `application/` | Servicios de aplicación (casos de uso) |
| **Domain Model** | `domain/` | Entidades, VOs, servicios de dominio, interfaces |
| **Infrastructure - Inbound** | `adapters/inbound/` | API, CLI, Jobs (entradas al sistema) |
| **Infrastructure - Outbound** | `adapters/outbound/` | Connectors, Repos, Storage, Messaging (salidas) |

---

## 📦 Componentes Principales

### 1. Domain Layer

#### `NormalizedStrategy` (Entidad)
- **Propósito**: Representar una estrategia de búsqueda normalizada e inmutable
- **Invariantes**:
  - `strategy_id` no vacío
  - `main_terms` ≥ 1
  - `year_filter.from <= year_filter.to`
  - Inmutabilidad (frozen dataclass)

#### `ScopusTranslator` (Servicio de Dominio)
- **Propósito**: Traducir estrategia normalizada a sintaxis de Scopus
- **Reglas**:
  - Wrapper `TITLE-ABS-KEY(...)`
  - Sinónimos con `OR`
  - Grupos con `AND`
  - Exclusiones con `AND NOT`
  - Año: `PUBYEAR > (from-1) AND PUBYEAR < (to+1)`
  - Operadores en MAYÚSCULAS

#### `IeeeTranslator` (Servicio de Dominio)
- **Propósito**: Traducir estrategia normalizada a sintaxis de IEEE Xplore
- **Reglas**:
  - Sin field wrapper (no TITLE-ABS-KEY)
  - Sinónimos con `OR`
  - Grupos con `AND`
  - Exclusiones con `NOT (...)` (sin "AND" antes)
  - Año: NO en query (genera warning + metadata para UI)
  - Operadores en MAYÚSCULAS

### 2. Application Layer

#### `TranslationService` (Caso de Uso)
- **Propósito**: Orquestar traducción de estrategias
- **Responsabilidades**:
  1. Validar target
  2. Seleccionar traductor (Scopus/IEEE/WoS)
  3. Ejecutar traducción
  4. Generar trace (UUID, timestamp, steps, rules)
  5. Armar contrato de respuesta

**Contrato de salida**:
```python
{
    "query": str,               # Query traducida
    "status": "Done",          # Estado del proceso
    "warnings": [str],         # Advertencias ([] si no hay)
    "trace": {
        "trace_id": str,       # UUID v4
        "target": str,         # "Scopus" / "IEEE Xplore"
        "steps_applied": [str],
        "rules_applied": [str],
        "timestamp": str       # ISO-8601 UTC
    },
    "target": str,             # Target de entrada
    "metadata": dict           # Info adicional
}
```

### 3. Testing Layer

#### `SyntaxValidator`
- Valida sintaxis por dialecto (field codes, operadores, paréntesis, año)

#### `LogicPreservationChecker`
- Valida equivalencia semántica (términos, OR, AND, exclusiones, precedencia)

#### `TraceValidator`
- Valida estructura de trace (trace_id, target, steps, rules, timestamp)

#### `WarningValidator`
- Valida presencia/ausencia de warnings

---

## 🧪 Testing (BDD)

### Feature: Traducción de Estrategias

**Ubicación**: `tests/acquisition/features/01_normalizacion_estrategia_busqueda.feature`

**Escenarios**:
- `@scopus`: Traducción a Scopus (✅ 100% passing)
- `@ieee`: Traducción a IEEE Xplore (✅ 100% passing)

### Ejecutar Tests

```bash
# Solo Scopus
behave tests/acquisition/features/01_normalizacion_estrategia_busqueda.feature --tags=@scopus

# Solo IEEE
behave tests/acquisition/features/01_normalizacion_estrategia_busqueda.feature --tags=@ieee

# Todos
behave tests/acquisition/features/01_normalizacion_estrategia_busqueda.feature
```

---

## 🚀 Próximos Pasos

### Funcionales
1. ✅ Implementar `NormalizedStrategy` (Domain)
2. ✅ Implementar `TranslationService` (Application)
3. ✅ Implementar `ScopusTranslator` (Domain Service)
4. ✅ Implementar `IeeeTranslator` (Domain Service)
5. ✅ Implementar Validators (Testing)
6. ✅ Feature @scopus 100% passing
7. ✅ Feature @ieee 100% passing
8. ⏸️ Implementar traductores adicionales (Web of Science, PubMed, etc.)

### Arquitecturales
1. ✅ Reestructurar `components/` → `adapters/` con `inbound/outbound`
2. ✅ Arreglar duplicados en `apps.py` y `urls.py`
3. ✅ Documentar arquitectura en README
4. ⏸️ Implementar adaptadores inbound (API endpoints)
5. ⏸️ Implementar conectores reales (Scopus API, IEEE API)

---

## 📚 Referencias

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [C4 Model](https://c4model.com/)
- [Domain-Driven Design](https://www.domainlanguage.com/ddd/)

---

## 🎓 Para la Defensa

### Puntos Clave a Destacar

1. **Separación de Responsabilidades**:
   - Domain = reglas de negocio puras (sin Django, sin I/O)
   - Application = casos de uso (orquestación)
   - Adapters = infraestructura (conectores, repos, storage)

2. **Dependency Rule**:
   - Las dependencias apuntan hacia adentro
   - El dominio NO conoce la infraestructura

3. **Testabilidad**:
   - BDD con Behave (comportamiento observable)
   - Tests sin tocar DB ni APIs externas (mocks)
   - Assertions reutilizables

4. **Extensibilidad**:
   - Agregar nuevo target (WoS, PubMed) = crear nuevo traductor
   - No tocar Application ni Domain existente
   - Principio Open/Closed

5. **Trazabilidad y Auditoría**:
   - Trace completo (UUID, timestamp, steps, rules)
   - Reproducibilidad de traducciones
   - Warnings explícitos

---

**Última actualización**: 2025-11-06
**Versión**: 1.0.0
**Estado**: Feature completo ✅ 100% passing (Scopus + IEEE Xplore)
