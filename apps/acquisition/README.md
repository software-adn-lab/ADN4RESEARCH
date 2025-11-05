# Acquisition Module

**Módulo de adquisición de papers y metadatos para revisiones sistemáticas de literatura (SLR)**

## 🎯 Propósito

El módulo `acquisition` gestiona todo el proceso de obtención de estudios académicos:
- Traducción de estrategias de búsqueda a sintaxis nativa de cada fuente
- Descubrimiento y consolidación de estudios desde múltiples bases de datos
- Enriquecimiento automático con metadatos completos
- Descarga y almacenamiento de textos completos

## 📁 Estructura

```
acquisition/
├── domain/              # Entidades y contratos (interfaces)
├── components/          # Componentes del diagrama C4
│   ├── messaging/       # Event Bus (comunicación entre módulos)
│   ├── search_orchestrator/  # Orquestador de búsquedas
│   ├── paper_state_manager/  # Gestor de estados de papers
│   ├── download_manager/     # Gestor de descargas
│   ├── repositories/    # Acceso a datos (metadatos)
│   └── storage/         # Almacenamiento de PDFs
└── tasks/               # Tareas asíncronas (Celery)
```

## ✅ Validación rápida

```bash
# Verificar sintaxis
python -m compileall apps/acquisition

# Ejecutar tests
python manage.py behave tests/acquisition
```

## 🚀 Fases de desarrollo

**FASE 1 (actual):** Lógica de negocio con mocks
- ✅ Interfaces definidas
- ✅ Componentes scaffolded
- 🔄 Tests unitarios con mocks

**FASE 2:** Implementaciones reales
- Scrapers de Scopus e IEEE Xplore
- Tests de integración

**FASE 3:** Infraestructura completa
- PostgreSQL (metadatos)
- MinIO (PDFs)
- RabbitMQ (eventos)

## 📋 Features implementados

1. **Traducción de estrategias** - Adapta queries a sintaxis de cada fuente
2. **Descubrimiento** - Busca y consolida estudios de múltiples fuentes
3. **Enriquecimiento** - Obtiene metadatos completos automáticamente
4. **Texto completo** - Descarga PDFs desde fuentes públicas/alternativas

## 🔧 Desarrollo

```bash
# Crear rama por feature
git checkout -b feature/acquisition-search-discovery

# Ejecutar tests del módulo
behave tests/acquisition/features/02_descubrimiento.feature

# Ejecutar todos los tests
behave tests/acquisition
```

## 📖 Referencias

- Features: `tests/acquisition/features/`
- Diagrama C4: Ver documentación del proyecto
- Arquitectura: Monolito modular con comunicación por eventos