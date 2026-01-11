# Comandos para Captura de Evidencias - Tesis

Estos comandos te permiten capturar las salidas de PowerShell para incluir en tu tesis.

---

## 1. Ejecución BDD (Behave) - RECOMENDADO

### Comando para ejecutar y ver en pantalla:
```powershell
cd d:\Tesis\ADN4RESEARCH
poetry run behave tests/acquisition/features/ --no-color
```

### Salida esperada (últimas líneas):
```
4 features passed, 0 failed, 0 skipped
10 scenarios passed, 0 failed, 0 skipped
69 steps passed, 0 failed, 0 skipped
Took 0m0.356s
```

### Para guardar en archivo:
```powershell
poetry run behave tests/acquisition/features/ --no-color > evidencias_cap3\A_BDD\behave_output.txt 2>&1
```

---

## 2. Resumen Compacto (solo las últimas 5 líneas)

```powershell
poetry run behave tests/acquisition/features/ --no-color 2>&1 | Select-Object -Last 5
```

### Salida esperada:
```
4 features passed, 0 failed, 0 skipped
10 scenarios passed, 0 failed, 0 skipped
69 steps passed, 0 failed, 0 skipped
Took 0m0.356s
```

---

## 3. Verificar estructura de tests existente

```powershell
Get-ChildItem -Path tests/acquisition/features/*.feature | Select-Object Name
```

### Salida esperada:
```
01_normalizacion_estrategia_busqueda.feature
02_busqueda_descubrimiento_estudios.feature
03_busqueda_de_metadatos_de_estudios.feature
04_disponibilidad_texto_completo.feature
```

---

## 4. Verificar mocks existentes

```powershell
Get-ChildItem -Path apps/acquisition/shared/testing/mocks/*.py | Select-Object Name
```

### Salida esperada:
```
mock_ieee_connector.py
mock_scopus_connector.py
mock_study_repository.py
```

---

## Qué capturar para la tesis (mínimo)

Para la sección 2.7, solo necesitas **1 captura de pantalla** que muestre:

1. El comando ejecutado: `poetry run behave tests/acquisition/features/ --no-color`
2. El resumen final:
   ```
   4 features passed, 0 failed, 0 skipped
   10 scenarios passed, 0 failed, 0 skipped
   69 steps passed, 0 failed, 0 skipped
   Took 0m0.356s
   ```

Esta captura va en la sección 2.7 con el pie: "Ilustración 13. Salida del runner BDD. Fuente: Elaboración propia."

---

## Anexos

Para los anexos, incluye el archivo completo:
- `evidencias_cap3/A_BDD/behave_output.txt`

Renómbralo como `Anexo_A_behave_output.txt` o similar.
