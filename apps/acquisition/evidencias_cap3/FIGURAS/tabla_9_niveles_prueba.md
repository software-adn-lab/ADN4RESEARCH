# Tabla 9. Niveles de prueba aplicados al módulo de adquisición/descarga

| Nivel | Alcance | Ubicación | Herramienta | Dependencias Externas | Evidencia |
|-------|---------|-----------|-------------|----------------------|-----------|
| **Nivel 1: BDD** | Contratos de 4 características | `tests/acquisition/features/*.feature` | behave-django | No (mocks/fixtures) | Anexo A: `behave_output.txt` |
| **Nivel 2: Slice** | Casos de uso con datos controlados | `tests/acquisition/integration/` | pytest | No | Resultados de ejecución pytest |
| **Nivel 3: Smoke** | Adaptadores reales (opcional) | Ejecución controlada | pytest | Sí (red/credenciales) | Logs de corrida |

**Fuente:** Elaboración propia (rutas del repositorio ADN4RESEARCH).

---

## Archivos de Feature BDD Verificados

| Feature | Archivo | Escenarios | Steps |
|---------|---------|------------|-------|
| Traducción automática de estrategias | `01_normalizacion_estrategia_busqueda.feature` | 2 | 12 |
| Descubrimiento y consolidación | `02_busqueda_descubrimiento_estudios.feature` | 3 | 15 |
| Consolidación de metadatos | `03_busqueda_de_metadatos_de_estudios.feature` | 2 | 14 |
| Acceso al texto completo | `04_disponibilidad_texto_completo.feature` | 3 | 28 |
| **TOTAL** | - | **10** | **69** |

---

## Dobles de Prueba (Mocks) Utilizados

| Mock | Ruta | Propósito |
|------|------|-----------|
| `MockScopusConnector` | `apps/acquisition/shared/testing/mocks/mock_scopus_connector.py` | Simula API Scopus con fixtures deterministas |
| `MockIeeeConnector` | `apps/acquisition/shared/testing/mocks/mock_ieee_connector.py` | Simula API IEEE Xplore con fixtures deterministas |
| `MockStudyRepository` | `apps/acquisition/shared/testing/mocks/mock_study_repository.py` | Repositorio en memoria para persistencia controlada |
