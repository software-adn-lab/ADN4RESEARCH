# ADN4RESEARCH - Systematic Literature Review Platform

Plataforma Django para gestion de **Systematic Literature Reviews (SLR)** dividida en modulos independientes.

## Modulos del Sistema

- **Design** (Diseno) - Gestion de preguntas de investigacion
- **Interpretation** (Interpretacion) - Analisis e interpretacion de resultados
- **Extraction** (Extraccion) - Extraccion de datos de estudios
- **Selection** (Seleccion) - Seleccion de estudios relevantes
- **Acquisition** (Obtencion) - Busqueda y obtencion de estudios

## Tecnologias

- **Backend:** Django 5.2.7 + Python 3.13+
- **Base de datos:** PostgreSQL
- **Cache & Messaging:** Redis
- **Storage:** MinIO (S3-compatible) / AWS S3
- **Async Tasks:** Celery
- **Frontend:** TailwindCSS + DaisyUI
- **Testing:** Behave (BDD)
- **Container:** Docker + Docker Compose
- **Extra Dependency for spaCy:** download the spanish model with "python -m spacy download es_core_news_sm" command

---


## Inicio Rapido

### Opcion A: Con Docker (Recomendado) 🐳

```bash
# 1. Clonar repositorio
git clone <URL_DEL_REPOSITORIO>
cd ADN4RESEARCH

# 2. Iniciar con Docker
# Windows (PowerShell):
.\docker-start.ps1

# Linux/Mac:
chmod +x docker-start.sh
./docker-start.sh
```

Accede a:
- **Django:** http://localhost:8000
- **MinIO Console:** http://localhost:9001 (usuario: minioadmin, password: minioadmin)

**Ver guia completa:** [DOCKER.md](DOCKER.md)

---

### Opcion B: Instalacion Local

```bash
# 1. Clonar repositorio
git clone <URL_DEL_REPOSITORIO>
cd ADN4RESEARCH

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar base de datos
createdb adn4research
cp .env.example .env
# Editar .env con tus credenciales

# 5. Inicializar Django
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Accede a: http://localhost:8000

**Ver guia completa:** [SETUP.md](SETUP.md)

---

## Documentacion

- **[SETUP.md](SETUP.md)** - Guia completa de instalacion local
- **[DOCKER.md](DOCKER.md)** - Guia completa de Docker
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Estructura del proyecto y guia de desarrollo

## Estructura del Proyecto

```
ADN4RESEARCH/
├── config/              # Configuracion Django
├── design/              # Modulo de diseno (FUNCIONAL)
├── interpretation/      # Modulo de interpretacion
├── extraction/          # Modulo de extraccion
├── selection/           # Modulo de seleccion
├── acquisition/         # Modulo de obtencion
├── project/             # Gestion de proyectos
├── notification/        # Sistema de notificaciones
├── theme/               # Frontend (Tailwind)
├── tests/               # Tests BDD por modulo
└── shared/              # Templates compartidos
```

## Comandos Utiles

### Con Docker

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ejecutar comandos Django
docker-compose exec web python manage.py <comando>

# Ejecutar tests
docker-compose exec web python manage.py behave

# Detener servicios
docker-compose down
```

### Sin Docker (Local)

```bash
# Desarrollo
python manage.py runserver              # Iniciar servidor
python manage.py makemigrations         # Crear migraciones
python manage.py migrate                # Aplicar migraciones
python manage.py behave                 # Ejecutar tests BDD

# Frontend (Tailwind)
cd theme/static_src
npm install                             # Instalar dependencias
npm run dev                             # Modo desarrollo (watch)
npm run build                           # Build produccion
```

## Modulos Disponibles

- `/admin/` - Panel de administracion
- `/design/` - Modulo de diseno
- `/interpretation/` - Modulo de interpretacion
- `/extraction/` - Modulo de extraccion
- `/selection/` - Modulo de seleccion
- `/acquisition/` - Modulo de obtencion

## Testing

```bash
# Con Docker
docker-compose exec web python manage.py behave

# Sin Docker
python manage.py behave

# Ejecutar tests de un modulo especifico
python manage.py behave tests/design/
```

## Servicios Docker

Al usar Docker, tendras acceso a:

- **Django Web:** http://localhost:8000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379
- **MinIO Storage:** http://localhost:9000
- **MinIO Console:** http://localhost:9001
- **Celery Worker:** Tareas asincronas en background
- **Celery Beat:** Tareas programadas

## Contribuir

Cada equipo trabaja en su modulo respectivo. Lee `PROJECT_STRUCTURE.md` para entender como organizar tu codigo.

## Estado del Proyecto

- ✅ **Design:** Funcional y probado
- 🆕 **Interpretation:** Estructura basica lista
- 🆕 **Extraction:** Estructura basica lista
- 🆕 **Selection:** Estructura basica lista
- 🆕 **Acquisition:** Estructura basica lista

## Licencia

Proyecto academico - Universidad [Nombre Universidad]
