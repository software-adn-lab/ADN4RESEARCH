# 2.7 Estrategia de pruebas y verificación del módulo

Esta sección describe la estrategia de verificación aplicada al módulo de adquisición/descarga. Dado que el módulo depende de integraciones externas volátiles (proveedores, cuotas, credenciales y cambios en APIs/HTML), la verificación se diseñó priorizando reproducibilidad y aislamiento del dominio respecto a infraestructura. En consecuencia, las pruebas se organizan para validar contratos de comportamiento (BDD) con resultados deterministas y, adicionalmente, comprobar lógica por característica en pruebas por slice.

## 2.7.1 Niveles de prueba y alcance

La verificación del módulo se estructuró en tres niveles complementarios (Tabla 9). El objetivo es separar (i) validación contractual reproducible del comportamiento del módulo y (ii) validación opcional de compatibilidad con infraestructura real, sin convertir esta última en la base de la evidencia.

**Tabla 9.** Niveles de prueba aplicados al módulo de adquisición/descarga. Fuente: Elaboración propia (rutas del repositorio).

| Nivel | Alcance | Ubicación | Herramienta | Dependencias externas | Evidencia |
|-------|---------|-----------|-------------|----------------------|-----------|
| Nivel 1: BDD | Contratos de 4 características | `tests/acquisition/features/*.feature` | behave-django | No (mocks/fixtures) | Salida de ejecución (Anexo A: behave_output.txt) |
| Nivel 2: Pruebas por slice | Casos de uso con datos controlados | `tests/acquisition/integration/` | pytest | No | Resultados de ejecución pytest |
| Nivel 3: Smoke (opcional) | Adaptadores reales | Ejecución controlada | pytest | Sí (red/credenciales) | Logs / resultados de corrida |

## 2.7.2 Pipeline de verificación determinista

La verificación contractual se ejecuta bajo un pipeline determinista: los escenarios Gherkin (`.feature`) definen el contrato, los step definitions construyen el contexto controlado e inyectan dobles (mocks/fixtures), y la validación se realiza mediante aserciones sobre efectos observables del dominio (estados, conteos, deduplicación y advertencias). La Ilustración 12 resume este flujo.

**Ilustración 12.** Pipeline de verificación determinista (BDD). Fuente: Elaboración propia.

[INSERTAR IMAGEN: fig_2_7_pipeline_bdd.mmd renderizado]

```
.feature → Step Definitions → Mocks/Fixtures → Servicios de Dominio → Asserts → behave_output.txt
```

## 2.7.3 Resultados de ejecución BDD (evidencia real)

La evidencia de ejecución se obtuvo mediante la corrida de Behave sobre las features del módulo:

```
poetry run behave tests/acquisition/features/ --no-color
```

La salida completa del runner se conserva como evidencia verificable (Anexo A: behave_output.txt). En dicha ejecución se validaron 4/4 features, con 10 escenarios y 69 steps, todos aprobados. El tiempo total de ejecución fue 0,356 s (entorno controlado).

**Tabla 10.** Resultados reales de ejecución BDD. Fuente: behave_output.txt (Anexo A).

| Feature | Escenarios | Steps | Resultado |
|---------|------------|-------|-----------|
| 01_normalizacion_estrategia_busqueda.feature | 2 | 12 | ✅ Aprobado |
| 02_busqueda_descubrimiento_estudios.feature | 3 | 15 | ✅ Aprobado |
| 03_busqueda_de_metadatos_de_estudios.feature | 2 | 14 | ✅ Aprobado |
| 04_disponibilidad_texto_completo.feature | 3 | 28 | ✅ Aprobado |
| **TOTAL** | **10** | **69** | **4/4 features** |

A nivel de cobertura funcional, los escenarios verificados incluyen:
- (i) traducción ready con advertencias cuando aplica (IEEE)
- (ii) descubrimiento completo y parcial según fuentes habilitadas
- (iii) enriquecimiento automático y ajuste manual
- (iv) gestión de texto completo por acceso público, alternativa o carga manual

**Ilustración 13.** Salida del runner BDD. Fuente: Elaboración propia.

[INSERTAR CAPTURA DE PANTALLA DEL TERMINAL CON LA SALIDA:
```
4 features passed, 0 failed, 0 skipped
10 scenarios passed, 0 failed, 0 skipped
69 steps passed, 0 failed, 0 skipped
Took 0m0.356s
```
]

## 2.7.4 Dobles de prueba y control del determinismo

El determinismo de la suite se logra sustituyendo integraciones externas por dobles de prueba que implementan los mismos contratos. En particular, se emplean mocks para simular conectores y repositorios, garantizando que la suite no dependa de red ni credenciales:

- **MockScopusConnector** (`apps/acquisition/shared/testing/mocks/mock_scopus_connector.py`)
- **MockIeeeConnector** (`apps/acquisition/shared/testing/mocks/mock_ieee_connector.py`)
- **MockStudyRepository** (`apps/acquisition/shared/testing/mocks/mock_study_repository.py`)

Con esta estrategia, el módulo se valida como comportamiento de dominio (contratos BDD), y los efectos observables quedan plenamente verificables en un entorno controlado.

---

## Resumen de Numeración

- **Tabla 9**: Niveles de prueba aplicados al módulo
- **Tabla 10**: Resultados reales de ejecución BDD
- **Ilustración 12**: Pipeline de verificación determinista
- **Ilustración 13**: Salida del runner BDD (captura de terminal)
- **Anexo A**: behave_output.txt (salida completa)

---

## Archivos generados para esta sección

| Archivo | Ubicación | Uso |
|---------|-----------|-----|
| `fig_2_7_pipeline_bdd.mmd` | `evidencias_cap3/FIGURAS/` | Diagrama Mermaid para Ilustración 12 |
| `tabla_9_niveles_prueba.md` | `evidencias_cap3/FIGURAS/` | Tabla 9 en formato markdown |
| `behave_output.txt` | `evidencias_cap3/A_BDD/` | Anexo A - salida completa BDD |
| `COMANDOS_TESIS.md` | `evidencias_cap3/` | Guía de comandos para captura |
