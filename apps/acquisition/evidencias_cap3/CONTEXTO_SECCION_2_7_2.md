# CONTEXTO PARA ESCRIBIR SECCIÓN 2.7.2 (TESIS)

## Información verificada del repositorio

### Archivo de evidencia
- **Ubicación**: `evidencias_cap3/B_PILOTOS/pilot_output.txt`
- **Fecha de ejecución**: 2025-12-28
- **Estado**: ✅ Ejecución exitosa

### Script que genera la evidencia
- **Script**: `evidencias_cap3/CONFIG/run_pilot.py`
- **Fachada utilizada**: `apps.acquisition.facade.get_acquisition_facade()`
- **Flujo ejecutado**: Creación estrategia → Preview → Finalize → Enrich → Download PDFs

---

## Datos reales de la ejecución (extraídos de pilot_output.txt)

### Estrategia 1: ML & SE (Recent)
- Strategy ID: 11
- Estudios encontrados: 5
- Fuentes: Scopus, IEEE Xplore
- Execution ID: `bad12477-31c4-4cad-b740-ae79a195d50e`
- Enriquecimiento: 5 exitosos, 0 fallidos
- PDFs disponibles: 0 (automático)

### Estrategia 2: DevOps (Very Recent)  
- Strategy ID: 12
- Estudios encontrados: 5
- Fuentes: Scopus, IEEE Xplore
- Execution ID: `b212990a-096c-4f9b-90e0-f536496aa2ec`
- Enriquecimiento: 5 exitosos, 0 fallidos
- PDFs disponibles: 0 (automático)

### Estudio de control manual
- Propósito: Garantizar evidencia en tabla de procedencia PDF
- Estado: `texto_completo_disponible`
- Origen PDF: `manual`

---

## Entornos de verificación (documentados)

### Entorno A (BDD - Determinista)
- Archivo: `evidencias_cap3/CONFIG/entorno_A.txt`
- Tipo: Verificación contractual
- Fuentes: Mocks (sin red)
- Salida: `behave_output.txt`

### Entorno B (Piloto - Real)
- Archivo: `evidencias_cap3/CONFIG/entorno_B.txt`
- Tipo: Validación operativa
- Fuentes: APIs/Web reales (Scopus, IEEE, Crossref)
- Salida: `pilot_output.txt`

---


}
