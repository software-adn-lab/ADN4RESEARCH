# ADN4RESEARCH - Estructura del Proyecto

## Descripción General

Este proyecto Django está estructurado para soportar un sistema de **Systematic Literature Review (SLR)** dividido en 5 módulos principales, cada uno manejado por un equipo diferente.

## Módulos del Sistema

### 1. **Design** (Diseño) ✅ FUNCIONAL
- **Ruta:** `/design/`
- **App:** `design/`
- **Responsable:** Ya implementado y funcionando
- **Funcionalidad:** Gestión de preguntas de investigación, frameworks (PICO, PEO, PCC)

### 2. **Interpretation** (Interpretación) 🆕
- **Ruta:** `/interpretation/`
- **App:** `interpretation/`
- **Estado:** Estructura básica creada, lista para desarrollo

### 3. **Extraction** (Extracción) 🆕
- **Ruta:** `/extraction/`
- **App:** `extraction/`
- **Estado:** Estructura básica creada, lista para desarrollo

### 4. **Selection** (Selección) 🆕
- **Ruta:** `/selection/`
- **App:** `selection/`
- **Estado:** Estructura básica creada, lista para desarrollo

### 5. **Acquisition** (Obtención) 🆕
- **Ruta:** `/acquisition/`
- **App:** `acquisition/`
- **Estado:** Estructura básica creada, lista para desarrollo

---

## Estructura de Cada App

Cada módulo tiene la siguiente estructura básica:

```
module_name/
├── __init__.py
├── apps.py                    # Configuración de la app
├── models.py                  # Modelos de base de datos (agregar aquí)
├── views.py                   # Vistas (agregar aquí)
├── urls.py                    # URLs de la app (agregar rutas aquí)
├── admin.py                   # Configuración del admin (opcional)
├── migrations/                # Migraciones de base de datos
│   └── __init__.py
└── templates/module_name/     # Templates HTML de la app
    └── .gitkeep
```

---

## Cómo Trabajar en tu Módulo

### Paso 1: Configurar el Entorno

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar variables de entorno:**
   - Copiar `.env.example` a `.env`
   - Editar `.env` con tus credenciales de PostgreSQL

3. **Crear la base de datos PostgreSQL:**
   ```bash
   # En PostgreSQL
   CREATE DATABASE adn4research;
   ```

4. **Aplicar migraciones:**
   ```bash
   python manage.py migrate
   ```

### Paso 2: Desarrollar tu Módulo

1. **Definir modelos en `models.py`:**
   ```python
   from django.db import models

   class MiModelo(models.Model):
       nombre = models.CharField(max_length=100)
       # ... más campos
   ```

2. **Crear migraciones:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Crear vistas en `views.py`:**
   ```python
   from django.shortcuts import render

   def mi_vista(request):
       return render(request, 'module_name/template.html')
   ```

4. **Agregar URLs en `urls.py`:**
   ```python
   from django.urls import path
   from . import views

   app_name = 'module_name'

   urlpatterns = [
       path('', views.mi_vista, name='index'),
       # ... más rutas
   ]
   ```

5. **Crear templates en `templates/module_name/`:**
   ```html
   {% extends "theme/base.html" %}

   {% block content %}
       <h1>Mi Contenido</h1>
   {% endblock %}
   ```

### Paso 3: Testing con BDD (Behave)

Cada módulo tiene su propio directorio de tests BDD:

```
tests/module_name/
├── features/           # Archivos .feature (Gherkin)
└── steps/             # Definiciones de steps en Python
```

**Ejemplo de feature:**
```gherkin
# tests/module_name/features/mi_feature.feature
Feature: Mi funcionalidad

  Scenario: Hacer algo
    Given tengo datos iniciales
    When realizo una acción
    Then obtengo un resultado
```

**Ejecutar tests:**
```bash
python manage.py behave
```

---

## Configuraciones Importantes

### Base de Datos: PostgreSQL

El proyecto está configurado para usar PostgreSQL. Las credenciales se configuran vía variables de entorno en `.env`:

```env
DB_NAME=adn4research
DB_USER=postgres
DB_PASSWORD=tupassword
DB_HOST=localhost
DB_PORT=5432
```

Si prefieres usar SQLite para desarrollo local, puedes descomentar la configuración en `config/settings.py`.

### Storage de Archivos

- **Desarrollo:** Archivos se guardan en `media/` (local)
- **Producción:** Configurar cloud storage (AWS S3, Azure, etc.) en `config/settings.py`

### Frontend: TailwindCSS + DaisyUI

El proyecto usa `django-tailwind` con DaisyUI para estilos.

**Compilar estilos:**
```bash
cd theme/static_src
npm install
npm run dev  # Modo desarrollo (watch)
npm run build  # Producción
```

---

## URLs del Proyecto

- `/admin/` - Django Admin
- `/design/` - Módulo de Diseño
- `/interpretation/` - Módulo de Interpretación
- `/extraction/` - Módulo de Extracción
- `/selection/` - Módulo de Selección
- `/acquisition/` - Módulo de Obtención

---

## Apps Compartidas

### `project` - Gestión de Proyectos
Maneja proyectos, miembros, y etapas. Todos los módulos pueden usar estos modelos.

### `notification` - Sistema de Notificaciones
Sistema de notificaciones entre módulos y usuarios.

### `theme` - Frontend Theme
App de Tailwind para estilos globales.

---

## Buenas Prácticas

1. **No modificar otros módulos:** Cada equipo trabaja en su módulo exclusivamente
2. **Usar la app `design` como referencia:** Tiene una arquitectura limpia (models, services, views)
3. **Crear servicios:** Separar lógica de negocio en `services/`
4. **Testing BDD:** Escribir features antes de implementar
5. **Commits frecuentes:** Hacer commits pequeños y descriptivos
6. **Respetar PEP 8:** Estilo de código Python estándar

---

## Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Correr servidor
python manage.py runserver

# Correr tests BDD
python manage.py behave

# Compilar Tailwind (en theme/static_src/)
npm run dev
```

---

## Estructura de Archivos Completa

```
ADN4RESEARCH/
├── config/                    # Configuración del proyecto
│   ├── settings.py           # Settings principal
│   ├── urls.py               # URLs raíz
│   └── events.py             # Sistema de eventos
│
├── design/                   # Módulo de Diseño (FUNCIONAL)
├── interpretation/           # Módulo de Interpretación (NUEVO)
├── extraction/               # Módulo de Extracción (NUEVO)
├── selection/                # Módulo de Selección (NUEVO)
├── acquisition/              # Módulo de Obtención (NUEVO)
│
├── project/                  # App de gestión de proyectos
├── notification/             # App de notificaciones
├── theme/                    # App de Tailwind/Frontend
│
├── shared/                   # Templates compartidos
│   └── templates/
│
├── tests/                    # Tests BDD por módulo
│   ├── design/
│   ├── interpretation/
│   ├── extraction/
│   ├── selection/
│   └── acquisition/
│
├── media/                    # Archivos subidos por usuarios
├── staticfiles/              # Archivos estáticos recopilados
│
├── .env                      # Variables de entorno (crear desde .env.example)
├── .env.example              # Ejemplo de variables de entorno
├── manage.py
├── requirements.txt
└── PROJECT_STRUCTURE.md      # Este archivo
```

---

## Soporte

Si tienes dudas sobre la estructura o configuración, revisa el módulo `design/` como referencia funcional o consulta con el equipo.

**¡Listo para programar! 🚀**
