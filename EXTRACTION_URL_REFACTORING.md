# Refactorización de URLs - App Extraction

## Resumen de Cambios

Se ha modificado la estructura de URLs de la app `extraction` para seguir el patrón de la app `design`, con `project_id` como parámetro principal en la ruta.

## Estructura Nueva

```
http://127.0.0.1:8000/project/<project_id>/extraction/
├── / (router)                                    → Redirige a fase abierta
├── /phases/<phase_id>/                          → Dashboard de fase
├── /phases/<phase_id>/config/                   → Configuración de fase
├── /phases/<phase_id>/open/                     → Abrir fase
├── /phases/<phase_id>/tags/<tag_id>/...         → Tags (taxonomy)
├── /papers/<paper_id>/                          → Detalle de paper
├── /papers/<paper_id>/pdf/                      → PDF del paper
├── /papers/<paper_id>/complete/                 → Marcar paper como completo
├── /papers/quotes/create/                       → Crear quote
└── /papers/quotes/<quote_id>/delete/            → Eliminar quote
```

## Cambios de Archivo

### 1. config/urls.py
- **Cambio**: URL de extraction ahora incluye `project_id`
- **De**: `path('extraction/', include('apps.extraction.urls'))`
- **A**: `path('project/<int:project_id>/extraction/', include('apps.extraction.urls'))`

### 2. apps/extraction/urls.py (REFACTORIZADO)
- Creado nuevo archivo principal con estructura clara
- Router centralizado: `extraction_phases_router`
- Namespaces definidos: `planning` y `core`
- Documentación clara de estructura

### 3. apps/extraction/design_phase_logic/views.py (NUEVO)
- Nueva carpeta para lógica de navegación (análoga a design)
- Router que redirige a fase abierta o primera disponible
- Usa decorador `@project_member_required`

### 4. apps/extraction/planning/urls.py
- Sin cambios de patrones, solo se quitó el `app_name` (ahora definido en include)

### 5. apps/extraction/core/urls.py
- Sin cambios de patrones, solo se quitó el `app_name` (ahora definido en include)

### 6. apps/extraction/planning/views.py
- Actualizado `get_success_url()` para incluir `project_id`
- Actualizado `PhaseOpenView.post()` para incluir `project_id` en redirects

### 7. apps/extraction/taxonomy/views.py
- Actualizado `get_success_url()` para incluir `project_id` en ambas vistas

### 8. apps/extraction/core/views.py
- Actualizado contexto de `PaperDetailView` para incluir `project_id` en URLs
- Ahora se pasan `project_id` y `pk` a todos los `reverse()`

### 9. Templates
- **pending_tags_list.html**: Actualizado para pasar `project_id` en URLs
- **_tab_studies.html**: Actualizado todos los links de papers para incluir `project_id`
- **paper_detail.html**: Actualizado para usar variable de contexto `paper_complete_url`

## Nombres de Rutas

Los nombres de rutas se actualizaron para usar namespaces anidados:

| Antigua | Nueva |
|---------|-------|
| `extraction:phase_detail` | `extraction:planning:phase_detail` |
| `extraction:paper_detail` | `extraction:core:paper_detail` |
| `extraction:paper_pdf` | `extraction:core:paper_pdf` |
| `extraction:paper_complete` | `extraction:core:paper_complete` |
| `extraction:quote_create` | `extraction:core:quote_create` |
| `extraction:quote_delete` | `extraction:core:quote_delete` |

## Parámetros de URL

Todas las vistas ahora requieren `project_id` además de sus parámetros específicos:

```python
# Ejemplo con reverse()
reverse('extraction:planning:phase_detail', kwargs={
    'project_id': 1,
    'pk': 123
})
# Resultado: /project/1/extraction/phases/123/
```

## Router Automático

El router en la raíz (`/project/<project_id>/extraction/`) automáticamente:
1. Busca una fase OPEN (abierta)
2. Si no existe, obtiene la primera fase disponible
3. Si no hay fases, redirige al proyecto

## Validación

Todas las rutas han sido validadas:
```
✅ /project/1/extraction/
✅ /project/1/extraction/phases/123/
✅ /project/1/extraction/phases/123/config/
✅ /project/1/extraction/phases/123/open/
✅ /project/1/extraction/papers/456/
✅ /project/1/extraction/papers/456/pdf/
✅ /project/1/extraction/papers/456/complete/
✅ /project/1/extraction/papers/quotes/create/
✅ /project/1/extraction/papers/quotes/789/delete/
```
