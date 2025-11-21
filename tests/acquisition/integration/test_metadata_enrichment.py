"""
Test de integracion para MetadataEnricher y ConsolidationService.

Prueba el enriquecimiento REAL de metadatos usando Crossref.
Crossref es gratuito y no requiere API key, ideal para tests.

Ejecutar con:
    python tests/acquisition/integration/test_metadata_enrichment.py
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

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.discovery.adapters.outbound.connectors.crossref_connector import CrossrefConnector
from apps.acquisition.metadata.application.consolidation_service import ConsolidationService
from apps.acquisition.metadata.domain.services.metadata_normalizer import MetadataNormalizer

print("=" * 80)
print("TEST METADATA ENRICHMENT (FEATURE 3)")
print("=" * 80)
print()

# Solo usamos Crossref (gratuito, sin API key)
print("Inicializando conectores...")
connectors = {
    "Crossref": CrossrefConnector()
}
print("OK Crossref inicializado")
print()

print("=" * 80)
print("TEST 1: Enriquecimiento con Crossref")
print("=" * 80)
print()

# Estudio incompleto pero conocido (paper famoso de Deep Learning)
study_incomplete = Study.from_dict({
    "title": "Deep Learning",
    "link": "https://example.com/deep-learning",
    "source": "Scopus",  # Fuente valida
    "status": "discovered",
    # Sin DOI, sin autores, sin abstract - debe encontrarlos
})

print(f"Estudio inicial:")
print(f"  Titulo: {study_incomplete.title}")
print(f"  DOI: {study_incomplete.doi}")
print(f"  Autores: {study_incomplete.authors}")
print(f"  Anio: {study_incomplete.year}")
print(f"  Abstract: {'Si' if study_incomplete.abstract else 'No'}")
print()

service = ConsolidationService(connectors=connectors)
result = service.consolidate([study_incomplete])

study_enriched = result.studies[0]

print(f"Estudio enriquecido:")
print(f"  Titulo: {study_enriched.title}")
print(f"  DOI: {study_enriched.doi.value if study_enriched.doi else 'N/A'}")
print(f"  Autores: {study_enriched.authors[:3] if study_enriched.authors else 'N/A'}...")
print(f"  Anio: {study_enriched.year}")
print(f"  Abstract: {'Si (' + str(len(study_enriched.abstract)) + ' chars)' if study_enriched.abstract else 'No'}")
print(f"  Status: {study_enriched.consolidation_status}")
print(f"  Field Origins: {study_enriched.field_origins}")
print()

# Validaciones
if study_enriched.doi:
    print("OK DOI encontrado via Crossref")
else:
    print("WARN: DOI no encontrado (puede que Crossref no tenga este paper)")

if study_enriched.authors:
    print("OK Autores encontrados")

print()
print("=" * 80)
print("TEST 2: Normalizacion de metadatos")
print("=" * 80)
print()

normalizer = MetadataNormalizer()

# Estudio con datos sucios
study_dirty = Study.from_dict({
    "title": "[::Machine::] Learning for Software [::Testing::]",
    "link": "https://example.com/paper",
    "source": "IEEE Xplore",
    "doi": "HTTPS://DOI.ORG/10.1234/DIRTY.DOI",
    "authors": ["  SMITH, John  ", "doe, jane"],
    "year": 2023,
    "status": "discovered",
})

print(f"Antes de normalizar:")
print(f"  Titulo: {study_dirty.title}")
print(f"  DOI: {study_dirty.doi.value if study_dirty.doi else 'N/A'}")
print(f"  Autores: {study_dirty.authors}")
print()

normalizer.normalize(study_dirty)

print(f"Despues de normalizar:")
print(f"  Titulo: {study_dirty.title}")
print(f"  DOI: {study_dirty.doi.value if study_dirty.doi else 'N/A'}")
print(f"  Autores: {study_dirty.authors}")
print()

# Validaciones
if "[::" not in study_dirty.title:
    print("OK Titulo IEEE limpiado")
else:
    print("FAIL: Titulo aun tiene marcadores IEEE")

if study_dirty.doi and study_dirty.doi.value.startswith("10."):
    print("OK DOI normalizado (sin prefijo URL)")
else:
    print("WARN: DOI no normalizado correctamente")

print()
print("=" * 80)
print("TEST 3: Consolidacion completa (varios estudios)")
print("=" * 80)
print()

studies = [
    Study.from_dict({
        "title": "Attention Is All You Need",
        "link": "https://arxiv.org/abs/1706.03762",
        "source": "Scopus",
        "status": "discovered",
    }),
    Study.from_dict({
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "link": "https://arxiv.org/abs/1810.04805",
        "source": "Scopus",
        "status": "discovered",
    }),
]

print(f"Consolidando {len(studies)} estudios...")
result = service.consolidate(studies)

print(f"\nResumen:")
print(f"  Total procesados: {result.summary['total_processed']}")
print(f"  Exitosos: {result.summary['successful']}")
print(f"  Fallidos: {result.summary['failed']}")
print(f"  Campos enriquecidos: {result.summary['enriched_fields']}")
print()

for i, study in enumerate(result.studies, 1):
    print(f"[{i}] {study.title[:50]}...")
    print(f"    DOI: {study.doi.value if study.doi else 'N/A'}")
    print(f"    Status: {study.consolidation_status}")
    print()

print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
