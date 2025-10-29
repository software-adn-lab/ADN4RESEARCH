# ADN4Research - Módulo de Búsqueda y Obtención de Papers Académicos

@README.md
@config/urls.py
@config/settings/
@apps/busqueda/urls.py
@apps/busqueda/api/urls.py
@apps/busqueda/components/orchestrator/
@apps/busqueda/components/download/
@apps/busqueda/components/paper_state/
@apps/busqueda/external/
@apps/busqueda/models/
@apps/busqueda/tests/

---

## 🎯 Contexto del Proyecto

**Sistema:** ADN4Research — Plataforma para optimización del proceso de Revisión Sistemática de Literatura (SRL).  
**Arquitectura:** Monolito modular (cada módulo = 1 app Django).  
**Mi Módulo:** **Búsqueda** — Traducción de estrategias, descubrimiento multi-fuente, consolidación de metadatos y **obtención de texto completo** (automática y manual).  
**Objetivo Principal:** Automatizar la recuperación de papers y metadata con **trazabilidad end-to-end**, **alta disponibilidad** y **calidad** para habilitar Selección y Extracción.

### ✅ Alcance del MVP
- Traducción automática de estrategias normalizadas → sintaxis específica (Scopus, IEEE Xplore).
- Descubrimiento y consolidación desde múltiples fuentes (de-duplicación hard/soft).
- Enriquecimiento de metadatos (DOI, autores, afiliación, venue, año, palabras clave, enlaces).
- Obtención de texto completo (auto + manual con evidencia y permisos).
- Trazabilidad por operación (eventos y correlación por `SearchSession`).
- Manejo robusto de errores y reintentos (políticas idempotentes y backoff).

---

## 🏗️ Arquitectura y Estructura

**Stack**
- **Backend:** Django 4.x + DRF
- **DB:** PostgreSQL 14+ (ORM)
- **Storage:** MinIO/local (PDFs) con interfaz de almacenamiento.
- **Testing:** `pytest`, `pytest-django`, `pytest-bdd` (Gherkin)
- **Contenedores:** Docker + Compose

**Patrón**: Clean Architecture + DDD + mapeo C4 L3 → *apps* Django.  
**Boundary clave (busqueda):** `api/` (I/O), `components/*` (lógica de negocio), `models/` (persistencia), `external/` (integraciones), `storage/` (infra).

### Árbol del módulo (resumen)
adn4research/
├─ config/
├─ apps/
│ ├─ busqueda/
│ │ ├─ api/ (views/ serializers/ permissions.py urls.py)
│ │ ├─ components/
│ │ │ ├─ orchestrator/ (services/, domain/, ports/, adapters/)
│ │ │ ├─ paper_state/ (state machine, transitions, repo port)
│ │ │ └─ download/ (queue, retry, validators, storage adapters)
│ │ ├─ external/ (sources: scopus_client.py, ieee_client.py; llm/)
│ │ ├─ storage/ (base.py, minio_storage.py, local_storage.py)
│ │ ├─ models/ (estrategia.py, traduccion.py, estudio.py, ...)
│ │ └─ tests/ (features/, step_defs/, unit/, integration/, fixtures/)
│ ├─ seleccion/
│ ├─ extraccion/
│ └─ gestion_cuenta/
├─ shared/
└─ tests/integration/

markdown
