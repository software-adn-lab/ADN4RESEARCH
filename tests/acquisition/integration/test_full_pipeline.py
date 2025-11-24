"""
Test de integracion END-TO-END del modulo de adquisicion.

Flujo completo:
    Estrategia -> Traduccion -> Discovery (Scopus/IEEE) -> Consolidacion

IMPORTANTE: Requiere credenciales reales en .env:
    - SCOPUS_API_KEY (para Scopus)
    - EPN_USER / EPN_PASS (para IEEE via EZproxy)

Ejecutar con:
    python tests/acquisition/integration/test_full_pipeline.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# Imports del sistema
from apps.acquisition.translation.domain.models import NormalizedStrategy
from apps.acquisition.translation.application.translation_service import TranslationService
from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector
from apps.acquisition.discovery.adapters.outbound.connectors.crossref_connector import CrossrefConnector
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.metadata.application.consolidation_service import ConsolidationService

print("=" * 80)
print("TEST FULL PIPELINE - END TO END")
print("=" * 80)
print()

# Verificar credenciales
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
EPN_USER = os.getenv("EPN_USER")

if not SCOPUS_API_KEY:
    print("WARN: SCOPUS_API_KEY no configurada - saltando Scopus")
if not EPN_USER:
    print("WARN: EPN_USER no configurada")

print()

# ============================================================================
# FASE 1: ESTRATEGIA NORMALIZADA
# ============================================================================
print("=" * 80)
print("FASE 1: ESTRATEGIA NORMALIZADA")
print("=" * 80)
print()

# Estrategia simple para test rapido
strategy_data = {
    "strategy_id": "pipeline_test_2024",
    "main_terms": [
        {
            "term": "machine learning",
            "synonyms": ["deep learning"]
        },
        {
            "term": "software testing",
            "synonyms": ["test automation"]
        }
    ],
    "exclusions": [],
    "filters": {
        "year": {
            "from": 2022,
            "to": 2024
        }
    }
}

strategy = NormalizedStrategy.from_dict(strategy_data)
print(f"Estrategia: {strategy.strategy_id}")
print(f"Terminos: {[t.term for t in strategy.main_terms]}")
print(f"Filtro anio: {strategy.year_filter.year_from}-{strategy.year_filter.year_to}" if strategy.year_filter else "Sin filtro")
print()
print("OK Estrategia creada")
print()

# ============================================================================
# FASE 2: TRADUCCION
# ============================================================================
print("=" * 80)
print("FASE 2: TRADUCCION")
print("=" * 80)
print()

translation_service = TranslationService()

# Traducir a Scopus
result_scopus = translation_service.translate(strategy, "Scopus")
print(f"Scopus Query ({result_scopus['status']}):")
print(f"  {result_scopus['query'][:100]}...")
print()

# Traducir a IEEE
result_ieee = translation_service.translate(strategy, "IEEE Xplore")
print(f"IEEE Query ({result_ieee['status']}):")
print(f"  {result_ieee['query'][:100]}...")
print()

print("OK Traducciones completadas")
print()

# ============================================================================
# FASE 3: DISCOVERY (Solo Scopus si hay API key)
# ============================================================================
print("=" * 80)
print("FASE 3: DISCOVERY")
print("=" * 80)
print()

all_studies = []
MAX_RESULTS = 3  # Pocos para test rapido

if SCOPUS_API_KEY:
    print("Buscando en Scopus...")
    try:
        scopus = ScopusConnector(
            username=EPN_USER,
            password=os.getenv("EPN_PASS"),
            api_key=SCOPUS_API_KEY,
            headless=True
        )
        scopus_results = list(scopus.search(result_scopus['query'], max_results=MAX_RESULTS))

        print(f"  Encontrados: {len(scopus_results)} resultados")

        for r in scopus_results:
            study = Study.from_dict({
                "title": r.get('title', 'N/A'),
                "link": r.get('link', ''),
                "source": "Scopus",
                "doi": r.get('doi'),
                "authors": r.get('authors'),
                "year": r.get('year'),
                "abstract": r.get('abstract'),
                "status": "discovered",
            })
            all_studies.append(study)

        scopus.close()
        print("  OK Scopus cerrado")

    except Exception as e:
        print(f"  ERROR Scopus: {e}")
else:
    print("Scopus SALTADO (sin API key)")

print()

# Si no tenemos estudios de Scopus, usar datos de prueba
if not all_studies:
    print("Usando estudios de prueba (sin discovery real)...")
    test_studies = [
        {
            "title": "Deep Learning for Software Defect Prediction",
            "link": "https://example.com/paper1",
            "source": "Scopus",  # Fuente valida
            "status": "discovered",
        },
        {
            "title": "Machine Learning in Software Testing: A Survey",
            "link": "https://example.com/paper2",
            "source": "Scopus",  # Fuente valida
            "status": "discovered",
        },
    ]
    all_studies = [Study.from_dict(s) for s in test_studies]

print(f"Total estudios para consolidar: {len(all_studies)}")
print()

# ============================================================================
# FASE 4: CONSOLIDACION (Enriquecimiento + Normalizacion)
# ============================================================================
print("=" * 80)
print("FASE 4: CONSOLIDACION")
print("=" * 80)
print()

# Usar Crossref para enriquecimiento (gratuito)
connectors = {
    "Crossref": CrossrefConnector()
}

consolidation_service = ConsolidationService(connectors=connectors)

print("Ejecutando consolidacion...")
result = consolidation_service.consolidate(all_studies)

print()
print("RESUMEN:")
print(f"  Total procesados: {result.summary['total_processed']}")
print(f"  Exitosos: {result.summary['successful']}")
print(f"  Fallidos: {result.summary['failed']}")
print(f"  Campos enriquecidos: {result.summary['enriched_fields']}")
print()

# ============================================================================
# RESULTADOS FINALES
# ============================================================================
print("=" * 80)
print("RESULTADOS FINALES")
print("=" * 80)
print()

for i, study in enumerate(result.studies, 1):
    print(f"[{i}] {study.title[:60]}...")
    print(f"    Fuente: {study.source}")
    print(f"    DOI: {study.doi.value if study.doi else 'N/A'}")
    print(f"    Anio: {study.year or 'N/A'}")
    print(f"    Autores: {len(study.authors) if study.authors else 0}")
    print(f"    Abstract: {'Si' if study.abstract else 'No'}")
    print(f"    Status: {study.consolidation_status}")
    print(f"    Origins: {list(study.field_origins.keys())}")
    print()

# ============================================================================
# VALIDACIONES
# ============================================================================
print("=" * 80)
print("VALIDACIONES")
print("=" * 80)
print()

checks_passed = 0
checks_total = 0

# Check 1: Todos los estudios tienen status
checks_total += 1
if all(s.consolidation_status for s in result.studies):
    print("OK Todos los estudios tienen consolidation_status")
    checks_passed += 1
else:
    print("FAIL: Algunos estudios sin consolidation_status")

# Check 2: Field origins marcados
checks_total += 1
if all(s.field_origins for s in result.studies):
    print("OK Todos los estudios tienen field_origins")
    checks_passed += 1
else:
    print("FAIL: Algunos estudios sin field_origins")

# Check 3: Al menos un estudio con DOI (si Crossref funciono)
checks_total += 1
studies_with_doi = [s for s in result.studies if s.doi]
if studies_with_doi:
    print(f"OK {len(studies_with_doi)} estudios tienen DOI")
    checks_passed += 1
else:
    print("WARN: Ningun estudio tiene DOI (Crossref no encontro matches)")

print()
print(f"Resultado: {checks_passed}/{checks_total} validaciones pasaron")
print()

# ============================================================================
# FASE 5: DESCARGAS (Feature 4)
# ============================================================================
print("=" * 80)
print("FASE 5: DESCARGAS DE TEXTO COMPLETO")
print("=" * 80)
print()

# Verificar que tengamos email configurado para Unpaywall
email_for_downloads = os.getenv("UNPAYWALL_EMAIL") or EPN_USER
if not email_for_downloads:
    print("WARN: UNPAYWALL_EMAIL no configurado, saltando descargas")
    print()
else:
    try:
        # Importar sin Django
        from apps.acquisition.downloads.application.fulltext_service import FullTextService
        from apps.acquisition.downloads.application.open_access_checker import CompositeOpenAccessChecker
        from apps.acquisition.downloads.adapters.outbound.connectors.unpaywall_checker import UnpaywallChecker
        from apps.acquisition.downloads.adapters.outbound.connectors.crossref_open_access_checker import CrossrefOpenAccessChecker
        from apps.acquisition.downloads.adapters.outbound.connectors.scopus_institutional_checker import ScopusInstitutionalChecker
        from apps.acquisition.downloads.adapters.outbound.connectors.http_downloader import HttpDownloader
        from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder
        from apps.acquisition.downloads.domain.services.file_validator import FileValidator

        print("Inicializando servicio de descargas (producción)...")

        # Construir servicio manualmente (sin Container/Django)
        unpaywall = UnpaywallChecker(email=email_for_downloads)
        crossref = CrossrefOpenAccessChecker(email=email_for_downloads)
        scopus_oa = ScopusInstitutionalChecker(api_key=SCOPUS_API_KEY) if SCOPUS_API_KEY else None

        oa_checker = CompositeOpenAccessChecker(
            primary_checker=unpaywall,
            secondary_checker=crossref,
            tertiary_checker=scopus_oa,
            skip_tertiary_for_sources=['Scopus']
        )

        downloader = HttpDownloader(base_dir="media/papers")
        alternative_finder = AlternativeSourceFinder()
        file_validator = FileValidator()

        download_service = FullTextService(
            oa_checker=oa_checker,
            downloader=downloader,
            alternative_finder=alternative_finder,
            file_validator=file_validator
        )

        print(f"  Email configurado: {email_for_downloads}")
        print()

        # Tomar solo estudios con DOI para intentar descarga
        studies_with_doi = [s for s in result.studies if s.doi]
        if not studies_with_doi:
            print("⚠️  No hay estudios con DOI, usando primer estudio de prueba")
            studies_to_download = result.studies[:1]
        else:
            # Tomar máximo 2 estudios para no saturar
            studies_to_download = studies_with_doi[:2]

        print(f"Intentando descargar {len(studies_to_download)} estudios...")
        print()

        download_results = {
            "disponible": 0,
            "no_disponible": 0,
            "errores": 0
        }

        for study in studies_to_download:
            print(f"  📄 {study.title[:50]}...")
            print(f"     DOI: {study.doi.value if study.doi else 'N/A'}")

            try:
                result_study = download_service.obtain_fulltext(study)

                if result_study.download_status == "texto_completo_disponible":
                    print(f"     ✅ Descargado: {result_study.pdf_path}")
                    print(f"        Fuente: {result_study.pdf_source}")
                    download_results["disponible"] += 1
                elif result_study.download_status == "no_disponible":
                    print(f"     ⚠️  No disponible (requiere carga manual)")
                    download_results["no_disponible"] += 1
                else:
                    print(f"     ⚠️  Estado desconocido: {result_study.download_status}")
                    download_results["errores"] += 1

            except Exception as e:
                print(f"     ❌ ERROR: {e}")
                download_results["errores"] += 1

            print()

        # Resumen de descargas
        print("RESUMEN DE DESCARGAS:")
        print(f"  Disponibles: {download_results['disponible']}")
        print(f"  No disponibles: {download_results['no_disponible']}")
        print(f"  Errores: {download_results['errores']}")
        print()

        # Validación adicional
        checks_total += 1
        if download_results["disponible"] > 0 or download_results["no_disponible"] > 0:
            print("OK El servicio de descargas está operativo")
            checks_passed += 1
        else:
            print("WARN: No se procesaron descargas exitosamente")

        print()
        print(f"Resultado actualizado: {checks_passed}/{checks_total} validaciones pasaron")
        print()

    except Exception as e:
        print(f"ERROR en fase de descargas: {e}")
        print()

print("=" * 80)
print("PIPELINE COMPLETADO")
print("=" * 80)
