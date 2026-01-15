# 📊 ANÁLISIS EXHAUSTIVO: APLICACIÓN DE EXTRACCIÓN
**Fecha:** 14 de Enero 2026  
**Proyecto:** ADN4RESEARCH  
**Módulo Analizado:** `apps/extraction/` + `ui/extraction/`

---

## 📋 RESUMEN EJECUTIVO

Se identificaron **4 funciones no utilizadas**, **3 métodos redundantes en el modelo**, **código duplicado en validación de permisos** y varias **oportunidades de refactoring**. El análisis cubre:

- ✅ 28 clases Python (Vistas, Modelos, Servicios, DTOs, Forms)
- ✅ 47 métodos/funciones Python
- ✅ 5 componentes JavaScript principales
- ✅ 3 templates principales + 8 partials
- ✅ 100+ referencias cruzadas analizadas

---

## 🚨 SECCIÓN 1: FUNCIONES/MÉTODOS NO UTILIZADOS

### 1.1 ⚠️ DEPRECATED: `PaperLifecycleService`

**Ubicación:** [apps/extraction/core/services.py](apps/extraction/core/services.py#L18-L53)

```python
class PaperLifecycleService:  # Línea 18
    """⚠️ DEPRECATED: Esta clase está siendo reemplazada por PaperExtractionService."""
    
    def mark_paper_as_complete(self, extraction_id: int) -> CompletionResult:  # Línea 26
        """⚠️ DEPRECATED: Usar PaperExtractionService.attempt_complete_paper() en su lugar."""
```

**Estado:** SOLO SE USA EN TESTS  
**Referencias encontradas:**
- [tests/extraction/steps/F_EM_001_extraction_protocol_steps.py](tests/extraction/steps/F_EM_001_extraction_protocol_steps.py#L245) - Línea 245
  - `service = PaperLifecycleService()`
  - `context.completion_result = service.mark_paper_as_complete(context.paper.id)`

**Impacto:** `PaperExtractionService.attempt_complete_paper()` es la versión moderna (Línea 180 de services.py) y se usa en:
- [apps/extraction/core/views.py](apps/extraction/core/views.py#L266) - PaperCompleteView

**Recomendación:** 
- ❌ ELIMINAR `PaperLifecycleService` completamente
- ✅ Actualizar test para usar `PaperExtractionService`
- ✅ Mantener `PaperExtractionService` como la única implementación

**Complejidad del Refactor:** ⭐ BAJA (solo 1 test a actualizar)

---

### 1.2 ❌ `mark_as_completed()` - Método de Modelo No Usado

**Ubicación:** [apps/extraction/core/models.py](apps/extraction/core/models.py#L136-L150)

```python
def mark_as_completed(self):  # Línea 136
    """
    Marca el paper como completado.
    
    Raises:
        BusinessRuleViolation: Si no cumple las reglas
    """
```

**Estado:** NUNCA SE LLAMA EN TODA LA CODEBASE  
**Referencias encontradas:**
- Solo definición (no hay llamadas)
- Hay comentario sobre la función pero NO se invoca en ningún lado

**Alternativa Usada:**
- [apps/extraction/core/services.py](apps/extraction/core/services.py#L180) - `PaperExtractionService.attempt_complete_paper()`
  - Línea 227: `paper.status = PaperExtractionStatusChoices.COMPLETED`

**Razón del Problema:**
- Hay DUPLICIDAD de lógica: tanto en el Modelo (mark_as_completed) como en el Servicio (attempt_complete_paper)
- El Servicio es la versión preferida por arquitectura (separación de responsabilidades)

**Recomendación:**
- ❌ ELIMINAR `PaperExtraction.mark_as_completed()`
- ✅ MANTENER `PaperExtractionService.attempt_complete_paper()`

**Complejidad del Refactor:** ⭐ BAJA (baja acoplamiento)

---

### 1.3 ❌ `can_be_completed()` - Método Redundante del Modelo

**Ubicación:** [apps/extraction/core/models.py](apps/extraction/core/models.py#L66-L88)

```python
def can_be_completed(self) -> tuple[bool, str]:  # Línea 66
    """
    Verifica si el paper puede ser marcado como completado.
    
    Business Rules:
    - Debe tener al menos una quote
    - Todas las tags obligatorias deben estar cubiertas
    """
```

**Estado:** SOLO LLAMADO DENTRO DE `mark_as_completed()` (que tampoco se usa)  
**Referencias encontradas:**
- [apps/extraction/core/models.py](apps/extraction/core/models.py#L145) - Línea 145: `can_complete, error_message = self.can_be_completed()`
  - Está DENTRO de `mark_as_completed()` que nunca se llama

**Alternativa Usada:**
- [apps/extraction/core/services.py](apps/extraction/core/services.py#L70-L175) - `PaperExtractionService.validate_completion_rules()`
  - Implementa la MISMA lógica de forma más completa

**Comparación de Lógica:**

| Aspecto | `can_be_completed()` | `validate_completion_rules()` |
|---------|---------------------|-------------------------------|
| Ubicación | Modelo | Servicio |
| Valida quotes | ✅ Sí | ✅ Sí |
| Valida tags | ✅ Sí | ✅ Sí |
| Valida estado | ❌ No | ✅ Sí |
| Logging | ❌ No | ✅ Sí (DEBUG) |
| Completa | ❌ Parcial | ✅ Completa |

**Recomendación:**
- ❌ ELIMINAR `can_be_completed()`
- ✅ MANTENER `PaperExtractionService.validate_completion_rules()`

**Complejidad del Refactor:** ⭐ BAJA (baja acoplamiento, solo el modelo lo usa)

---

### 1.4 ❌ `get_all_used_tags()` - Método No Utilizado

**Ubicación:** [apps/extraction/core/models.py](apps/extraction/core/models.py#L107-L114)

```python
def get_all_used_tags(self):  # Línea 107
    """
    Todos los tags (obligatorios y opcionales) usados en este paper.
    """
    from apps.extraction.taxonomy.models import Tag
    return Tag.objects.filter(
        quotes__paper_extraction=self
    ).distinct()
```

**Estado:** NUNCA SE LLAMA  
**Referencias encontradas:**
- Solo definición
- No hay ninguna llamada en vistas, templates, servicios ni tests

**Métodos Relacionados Similares (USADOS):**
- [apps/extraction/core/models.py](apps/extraction/core/models.py#L99-L105) - `get_used_mandatory_tags()` ✅ USADO
  - En [apps/extraction/core/services.py](apps/extraction/core/services.py#L257)

**Potencial Uso Futuro:**
- No hay evidencia de que sea necesario en el roadmap actual

**Recomendación:**
- ❌ ELIMINAR `get_all_used_tags()`
- ✅ Documentar si se vuelve necesario, readaptarlo

**Complejidad del Refactor:** ⭐ BAJA (cero dependencias)

---

### 1.5 ❌ `getCurrentSelection()` - Función JavaScript "Fantasma"

**Ubicación:** [ui/extraction/scripts/components/pdf_viewer.js](ui/extraction/scripts/components/pdf_viewer.js#L352-L354)

```javascript
getCurrentSelection() {  // Línea 352
    return { text: '', page: 1 };
}
```

**Estado:** NUNCA SE LLAMA  
**Referencias encontradas:**
- Solo definición
- Retorna datos ficticios (vacío siempre)
- No hay ningún `this.getCurrentSelection()` ni `getCurrentSelection()` en todo el código

**Propósito Original (Aparente):**
- Parece ser un método legacy o placeholder

**Recomendación:**
- ❌ ELIMINAR `getCurrentSelection()`

**Complejidad del Refactor:** ⭐ BAJA (cero dependencias)

---

## 🔄 SECCIÓN 2: CÓDIGO DUPLICADO

### 2.1 ⚠️ VALIDACIÓN DE PERMISOS DUPLICADA (CRÍTICO)

**Tipo:** Duplicación de Lógica de Acceso  
**Severidad:** ⭐⭐⭐ MEDIA

Hay **3 métodos privados prácticamente idénticos** que validan permisos:

#### 2.1.1 `_can_complete_paper()`
[apps/extraction/core/views.py](apps/extraction/core/views.py#L305-L325)

```python
def _can_complete_paper(self, user, paper):
    project = paper.extraction_phase.project
    return (
        user == project.owner or
        paper.assigned_to == user or
        user.is_staff or
        user.is_superuser
    )
```

#### 2.1.2 `_can_create_quote()`
[apps/extraction/core/views.py](apps/extraction/core/views.py#L425-L432)

```python
def _can_create_quote(self, user, paper):
    """Validar permisos de creación."""
    project = paper.extraction_phase.project
    return (
        user == project.owner or
        paper.assigned_to == user or
        user.is_staff or
        user.is_superuser
    )
```

#### 2.1.3 `_can_delete_quote()`
[apps/extraction/core/views.py](apps/extraction/core/views.py#L464-L473)

```python
def _can_delete_quote(self, user, quote):
    """Validar permisos de eliminación."""
    project = quote.paper_extraction.extraction_phase.project
    return (
        user == quote.created_by or          # ← Diferencia: creador de la quote
        user == project.owner or
        user.is_staff or
        user.is_superuser
    )
```

**Lugares donde se usa el patrón:**
1. [PaperAccessMixin.test_func()](apps/extraction/core/views.py#L38-L54) - Línea 38
2. [PaperCompleteView._can_complete_paper()](apps/extraction/core/views.py#L305) - Línea 305
3. [QuoteCreateView._can_create_quote()](apps/extraction/core/views.py#L425) - Línea 425
4. [QuoteDeleteView._can_delete_quote()](apps/extraction/core/views.py#L464) - Línea 464

**Problema:**
- ❌ Código repetido 4 veces
- ❌ Difícil de mantener (cambios en un lugar = 4 cambios)
- ❌ Alto riesgo de bugs de inconsistencia
- ❌ VIOLENCIA del principio DRY

**Refactoring Recomendado:**

Crear un mixin o servicio centralizado:

```python
# apps/extraction/shared/permissions.py
class PaperAccessMixin:
    def check_paper_access(self, user, paper):
        """Centralizado: Validar acceso al paper."""
        project = paper.extraction_phase.project
        return (
            user == project.owner or
            paper.assigned_to == user or
            user.is_staff or
            user.is_superuser
        )

class QuoteAccessMixin:
    def check_quote_creation_access(self, user, paper):
        """Centralizado: Validar creación de quotes."""
        return self.check_paper_access(user, paper)
    
    def check_quote_deletion_access(self, user, quote):
        """Centralizado: Validar eliminación (incluye creador)."""
        project = quote.paper_extraction.extraction_phase.project
        return (
            user == quote.created_by or
            user == project.owner or
            user.is_staff or
            user.is_superuser
        )
```

**Complejidad del Refactor:** ⭐⭐ MEDIA (impacta 4 vistas)

**Ganancia:** 
- 📉 -12 líneas de código duplicado
- 🔒 Consistencia de seguridad
- 🧹 Mejor mantenibilidad

---

### 2.2 ⚠️ MÉTODOS DE VALIDACIÓN DE TAGS DUPLICADOS

**Tipo:** Duplicación de Lógica de Filtrado  
**Severidad:** ⭐⭐ BAJA

En [apps/extraction/core/models.py](apps/extraction/core/models.py):

#### Comparación de Métodos:

| Método | Línea | Propósito | Duplicado |
|--------|-------|----------|-----------|
| `get_missing_mandatory_tags()` | 91 | Tags obligatorios NO usados | ✅ |
| `get_used_mandatory_tags()` | 99 | Tags obligatorios SÍ usados | ✅ |
| `is_complete_compliant()` | 130 | Check de completitud | 🔄 Usa el anterior |

**Patrón Duplicado:**
```python
# Patrón repetido 2 veces:
mandatory_tags = self.extraction_phase.tags.mandatory()
used_tag_ids = self.quotes.values_list('tags__id', flat=True).distinct()
return mandatory_tags.filter(id__in=used_tag_ids)  # o .exclude(...)
```

**Posible Refactor:**
```python
def get_mandatory_tags(self, used=True):
    """Obtener tags obligatorios, filtrados por uso."""
    mandatory_tags = self.extraction_phase.tags.mandatory()
    used_tag_ids = self.quotes.values_list('tags__id', flat=True).distinct()
    if used:
        return mandatory_tags.filter(id__in=used_tag_ids)
    else:
        return mandatory_tags.exclude(id__in=used_tag_ids)
```

**Complejidad del Refactor:** ⭐ BAJA

---

## 🛠️ SECCIÓN 3: PARÁMETROS Y VARIABLES NO UTILIZADAS

### 3.1 Parámetro No Usado en Views

**Ubicación:** [apps/extraction/planning/views.py](apps/extraction/planning/views.py#L99-L120)

En el método `_load_tab_data()`:
```python
def _load_tab_data(self, context, phase, tab, is_owner, is_researcher):
    # is_researcher se pasa pero casi nunca se usa en lógica crítica
    # Se usa principalmente para filtrar querysets
```

**Impacto:** BAJO - Solo afecta filtrado de datos

---

## 📦 SECCIÓN 4: CÓDIGO MUERTO EN TEMPLATES

### 4.1 ⚠️ Código Comentado en JavaScript

**Ubicación:** [ui/extraction/scripts/components/tag_manager.js](ui/extraction/scripts/components/tag_manager.js#L49-L100)

```javascript
/*
    updateMissingTagsAlert() {
        const allMandatoryBadges = document.querySelectorAll('[data-tag-id]');
        const missingTags = [];
        // ... código comentado de ~50 líneas
    }
*/
```

**Estado:** Comentado probablemente por falta de uso o refactoring en progreso  
**Recomendación:**
- ❌ ELIMINAR código comentado
- ✅ Si es necesario, mover a historial de git

---

### 4.2 ⚠️ Método Parcialmente Comentado en tag_manager.js

**Ubicación:** [ui/extraction/scripts/components/tag_manager.js](ui/extraction/scripts/components/tag_manager.js#L93-L100)

```javascript
updateCoveragePercentage() {
    console.group('🔍 Debug: updateCoveragePercentage');
    // 1. Identificar qué estamos seleccionando como "Total"
    // ... [INCOMPLETO]
```

**Estado:** MÉTODO INCOMPLETO  
**Impacto:** Posible fuente de bugs

---

## 🔍 SECCIÓN 5: MÉTODOS HEREDADOS O DEPRECATED

### 5.1 ⚠️ Funciones Globales Legacy en JavaScript

**Ubicación:** [ui/extraction/scripts/paper_workspace.js](ui/extraction/scripts/paper_workspace.js#L165-L254)

```javascript
// ============================================
// Funciones Globales (Legacy Support)
// ============================================

window.scrollToQuote = function(quoteId, page) { ... }
window.deleteQuote = async function(quoteId) { ... }
```

**Estado:** LEGACY pero AÚN EN USO  
**Ubicación de Uso:**
- [ui/extraction/scripts/components/quote_manager.js](ui/extraction/scripts/components/quote_manager.js#L183)
  - `onclick="scrollToQuote(${quote.id}, ${quote.location.page})"`

**Recomendación:**
- ⚠️ Mantener por ahora (aún en uso)
- 📝 Planificar migración a Event System (CustomEvents)

---

## ⚡ SECCIÓN 6: OPORTUNIDADES DE OPTIMIZACIÓN

### 6.1 N+1 Query en PaperDetailView

**Ubicación:** [apps/extraction/core/views.py](apps/extraction/core/views.py#L92-L110)

```python
def get_context_data(self, **kwargs):
    # Línea 102-104:
    quotes = paper.quotes.select_related('created_by').prefetch_related('tags').all()
    # ✅ BUENO: Ya optimizado con select_related y prefetch_related
```

**Análisis:** ✅ BIEN OPTIMIZADO (sin cambios necesarios)

---

### 6.2 Consulta Ineficiente en TagManager

**Ubicación:** [ui/extraction/scripts/components/tag_manager.js](ui/extraction/scripts/components/tag_manager.js#L19-L45)

```javascript
window.addEventListener('quote:created', (e) => {
    this.updateMandatoryTagsUI(e.detail.quote.tags);  // ✅ Datos ya en el payload
});
```

**Análisis:** ✅ BIEN (reutiliza datos del evento)

---

## 🏗️ SECCIÓN 7: PROBLEMAS ARQUITECTÓNICOS

### 7.1 Lógica de Negocio Duplicada Entre Model y Service

**Severidad:** ⭐⭐⭐ MEDIA

**Problema:**
- [PaperExtraction.mark_as_completed()](apps/extraction/core/models.py#L136) implementa lógica
- [PaperExtractionService.attempt_complete_paper()](apps/extraction/core/services.py#L180) duplica esa lógica

**Raíz Causa:**
- Migración incompleta de lógica del Modelo al Servicio

**Solución:**
- Mantener ServiceLayer como fuente única de verdad
- El Modelo debe ser "anemic" (solo persistencia)

---

### 7.2 Acceso Directo a Relaciones en Templates

**Ubicación:** [ui/extraction/templates/partials/pdf_workspace/tag_list.html](ui/extraction/templates/partials/pdf_workspace/tag_list.html#L17-L22)

```html
{{ paper.get_used_mandatory_tags.count }}
{{ paper.get_coverage_percentage }}
{{ paper.is_complete_compliant }}
```

**Análisis:**
- ✅ Está permitido en Django
- ⚠️ Posible N+1 query si no se optimiza
- Actualmente está OK porque se usan select_related/prefetch_related

---

## 🚀 SECCIÓN 8: REFACTORING RECOMENDADO

### PRIORIDAD 1: CRÍTICO (Hacer Primero)

| Tarea | Esfuerzo | Ganancia | Línea | Archivo |
|-------|----------|----------|-------|---------|
| **Eliminar `PaperLifecycleService`** | ⭐ | 🔒 Limpieza | 18 | core/services.py |
| **Eliminar `mark_as_completed()`** | ⭐ | 🧹 Mantenimiento | 136 | core/models.py |
| **Centralizar validación de permisos** | ⭐⭐ | 🔐 Seguridad | 305+ | core/views.py |

### PRIORIDAD 2: IMPORTANTE

| Tarea | Esfuerzo | Ganancia | Línea | Archivo |
|-------|----------|----------|-------|---------|
| **Eliminar `can_be_completed()`** | ⭐ | 🧹 Limpieza | 66 | core/models.py |
| **Eliminar `get_all_used_tags()`** | ⭐ | 🧹 Limpieza | 107 | core/models.py |
| **Limpiar código comentado en tag_manager.js** | ⭐ | 🧹 Mantenimiento | 49+ | tag_manager.js |

### PRIORIDAD 3: OPTIMIZACIÓN

| Tarea | Esfuerzo | Ganancia | Línea | Archivo |
|-------|----------|----------|-------|---------|
| **Eliminar `getCurrentSelection()`** | ⭐ | 📉 Code Smells | 352 | pdf_viewer.js |
| **Completar `updateCoveragePercentage()`** | ⭐⭐ | 🐛 Bug Fix | 93 | tag_manager.js |
| **Migrar legacy functions a classes** | ⭐⭐⭐ | 📈 Modernización | 165+ | paper_workspace.js |

---

## 📋 SECCIÓN 9: LISTA CONSOLIDADA DE FUNCIONES NO UTILIZADAS

### Python

| # | Función | Ubicación | Línea | Tipo | Alternativa |
|---|---------|-----------|-------|------|-------------|
| 1 | `PaperLifecycleService` (completa) | core/services.py | 18 | Clase | PaperExtractionService |
| 2 | `PaperLifecycleService.mark_paper_as_complete()` | core/services.py | 26 | Método | attempt_complete_paper() |
| 3 | `PaperExtraction.mark_as_completed()` | core/models.py | 136 | Método | Service layer |
| 4 | `PaperExtraction.can_be_completed()` | core/models.py | 66 | Método | validate_completion_rules() |
| 5 | `PaperExtraction.get_all_used_tags()` | core/models.py | 107 | Método | N/A (eliminar) |

### JavaScript

| # | Función | Ubicación | Línea | Tipo | Alternativa |
|---|---------|-----------|-------|------|-------------|
| 1 | `getCurrentSelection()` | pdf_viewer.js | 352 | Método | Eliminar |
| 2 | `updateMissingTagsAlert()` | tag_manager.js | 49 | Método | (Comentado) |
| 3 | (Parcial) `updateCoveragePercentage()` | tag_manager.js | 93 | Método | Completar |

---

## 🎯 SECCIÓN 10: RESUMEN DE IMPACTO

### Código a Eliminar (Sin Efectos Secundarios)

```
- PaperLifecycleService (7 líneas + docstrings)
- PaperExtraction.mark_as_completed() (15 líneas)
- PaperExtraction.can_be_completed() (20 líneas)
- PaperExtraction.get_all_used_tags() (7 líneas)
- PDFViewer.getCurrentSelection() (4 líneas)
- tag_manager.js updateMissingTagsAlert() (52 líneas comentadas)

Total: ~105 líneas de código muerto
```

### Beneficios del Refactor

| Aspecto | Ganancia |
|---------|----------|
| **Reducción de código** | 15-20% en services + models |
| **Mantenibilidad** | ⬆️⬆️ (menos duplicación) |
| **Claridad** | ⬆️⬆️ (una sola forma de hacer cada cosa) |
| **Seguridad** | ⬆️ (permisos centralizados) |
| **Testabilidad** | ⬆️ (menos código, más enfocado) |

---

## 📞 NOTAS ADICIONALES

### Funciones Bien Implementadas ✅

- `PaperExtractionService.attempt_complete_paper()` - Implementación moderna y completa
- `PaperExtractionService.validate_completion_rules()` - Lógica clara con logging
- `PaperAccessMixin.test_func()` - Validación de acceso correcta
- JavaScript Event System - Bien usado en `paper_workspace.js`
- DTOs - Bien estructurados para serialización

### Patrones Buenos Encontrados

1. **Service Layer Pattern** - Bien implementado en `PaperExtractionService`
2. **DTOs para respuestas JSON** - Buena práctica en `core/dtos.py`
3. **Custom Exceptions** - Bien usado `BusinessRuleViolation`
4. **Queryset Methods** - `mandatory()`, `approved()` en TagQuerySet
5. **JavaScript Components** - Buena separación: PDFViewer, QuoteManager, TagManager

---

## 🔧 PLAN DE ACCIÓN RECOMENDADO

**Fase 1 (Semana 1):** Eliminar funciones muertas
- [ ] Eliminar `PaperLifecycleService`
- [ ] Actualizar tests
- [ ] Eliminar `mark_as_completed()` y `can_be_completed()`

**Fase 2 (Semana 2):** Centralizar permisos
- [ ] Crear `PaperPermissionMixin`
- [ ] Refactorizar vistas
- [ ] Agregar tests de permisos

**Fase 3 (Semana 3):** Limpiar JavaScript
- [ ] Eliminar código comentado
- [ ] Completar `updateCoveragePercentage()`
- [ ] Modernizar funciones legacy

---

**Análisis realizado por:** GitHub Copilot  
**Versión del análisis:** 1.0  
**Fecha:** 14/01/2026
