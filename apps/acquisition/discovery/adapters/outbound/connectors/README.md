# Academic Connectors - IEEE Xplore & Scopus

Conectores para búsqueda en bases de datos académicas vía EZproxy institucional de la EPN.

## 🎯 Cómo Funciona (100% vía EZproxy)

**TODAS las peticiones van a través de EZproxy institucional:**
- IEEE: `https://bvirtual.epn.edu.ec:2097/...`
- Scopus: `https://bvirtual.epn.edu.ec:2057/...`

El **EZproxy detecta automáticamente** tu ubicación:

### ✅ Dentro de la Red EPN
- EZproxy detecta tu IP universitaria
- **Te deja pasar SIN login** (HTTP 200)
- **0 segundos** de autenticación
- No necesita cookies ni navegador

### 🌍 Fuera de la Red EPN
- EZproxy detecta IP externa
- **Te redirige al login** (HTTP 302)
- Login automático con credenciales del `.env` (usando Playwright)
- **Guarda cookies** en `.sessions/`
- Búsquedas subsecuentes usan cookies (sin navegador)

## 📁 Arquitectura

```
connectors/
├── session_manager.py              # Clase base abstracta
├── ieee_session_manager.py         # Session manager para IEEE
├── scopus_session_manager.py       # Session manager para Scopus
├── ieee_connector.py               # ✅ Conector principal IEEE (USAR ESTE)
├── scopus_connector.py             # ⚠️  Conector Scopus (TODO: implementar endpoint)
└── ieee_playwright_connector.py    # Legacy (solo para testing)
```

## 🚀 Uso

### IEEE Xplore

```python
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
import os

# Crear conector (lee credenciales del .env automáticamente)
connector = IeeeConnector(
    username=os.getenv('EPN_USER'),
    password=os.getenv('EPN_PASS'),
    headless=True,      # True en producción
    rate_limit=2.0      # Segundos entre búsquedas
)

# Buscar (detección automática de red)
results = connector.search('machine learning', max_results=50)

for study in results:
    print(f"Título: {study['title']}")
    print(f"DOI: {study['doi']}")
    print(f"Link: {study['link']}")
```

### Scopus

⚠️ **TODO**: Implementar endpoint de búsqueda de Scopus.

Para descubrir el endpoint:
1. Ejecutar script de captura XHR (similar a IEEE TEST 3)
2. Hacer búsqueda en Scopus
3. Identificar petición que retorna resultados en JSON
4. Actualizar `ScopusConnector._search_via_api()`

## ⚙️ Configuración (.env)

```bash
# Credenciales institucionales EPN
EPN_USER=tu.correo@epn.edu.ec
EPN_PASS=tu_contraseña

# IMPORTANTE:
# - Si estás EN LA RED: No se usan (acceso directo por IP)
# - Si estás FUERA: Login automático con estas credenciales
```

## 🔄 Flujo de Autenticación

```
┌─────────────────────┐
│  connector.search() │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│ session_manager.            │
│ ensure_authenticated()      │
└──────────┬──────────────────┘
           │
           ▼
    ¿Acceso por IP?
    (test_direct_access)
           │
      ┌────┴────┐
      │         │
     SÍ        NO
      │         │
      │         ▼
      │    ¿Cookies guardadas
      │     válidas?
      │         │
      │    ┌────┴────┐
      │    │         │
      │   SÍ        NO
      │    │         │
      │    │         ▼
      │    │   Autenticar con
      │    │   Playwright
      │    │   (guardar cookies)
      │    │         │
      └────┴─────────┘
           │
           ▼
    Ejecutar búsqueda
    con requests
```

## 📊 Endpoints Utilizados (VÍA EZPROXY)

### IEEE Xplore
- **URL de login**: `https://bvirtual.epn.edu.ec/login?url=http://ieeexplore.ieee.org/Xplore/home.jsp`
- **URL después del login**: `https://bvirtual.epn.edu.ec:2097/Xplore/home.jsp`
- **Endpoint de búsqueda**: `POST https://bvirtual.epn.edu.ec:2097/rest/search`
- **Payload**:
  ```json
  {
    "queryText": "machine learning",
    "highlight": true,
    "returnFacets": ["ALL"],
    "returnType": "SEARCH",
    "matchPubs": true,
    "pageNumber": 1,
    "rowsPerPage": 100
  }
  ```
- **Respuesta**: JSON con `records` array

### Scopus
- **URL de login**: `https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com`
- **URL después del login**: `https://bvirtual.epn.edu.ec:2057/pages/home?display=basic#basic`
- **Endpoint de búsqueda**: ⚠️ **TODO**: Descubrir endpoint mediante captura XHR

## 🧪 Testing

### Test en Red Universitaria
```bash
# Dentro de la EPN (con acceso por IP)
python scripts/test_ieee_connector.py
# Debería mostrar: "✅ Acceso directo por IP detectado"
```

### Test Fuera de Red
```bash
# En casa o fuera de la universidad
python scripts/test_ieee_connector.py
# Debería mostrar: "🔐 Autenticando con Playwright..."
```

## 🔍 Debugging

### Ver logs de detección de red
```python
import logging
logging.basicConfig(level=logging.INFO)

# Los logs mostrarán:
# 🔍 Verificando acceso directo por IP...
# ✅ Acceso directo por IP detectado
# O
# ⚠️  Sin acceso directo. Verificando cookies...
```

## ✨ Características

### IeeeConnector (Recomendado)
- ✅ Detección automática de red
- ✅ Session manager con cookies persistentes
- ✅ Rate limiting con variación aleatoria
- ✅ Retry automático con backoff exponencial
- ✅ Paginación automática
- ✅ Usa endpoint `/rest/search` (JSON, no scraping HTML)
- ✅ Re-autenticación automática si cookies expiran

### IeeePlaywrightConnector (Legacy)
- Solo para testing/debugging
- Abre navegador en CADA búsqueda
- Más lento
- No guarda cookies

## 📝 Notas

1. **Cookies guardadas en**: `.sessions/ieee_session.json` y `.sessions/scopus_session.json`
2. **Las cookies expiran**: Re-autenticación automática
3. **Rate limiting**: 2-4 segundos entre búsquedas (configurable)
4. **User-Agent**: Consistente entre Playwright y requests (anti-detección)

## 🎓 Para Scopus

Cuando se implemente el endpoint de Scopus, seguir mismo patrón que IEEE:

1. `ScopusSessionManager` ya tiene detección de red ✅
2. Solo falta implementar `ScopusConnector._search_via_api()` con el endpoint correcto
3. El resto de la arquitectura es idéntica a IEEE
