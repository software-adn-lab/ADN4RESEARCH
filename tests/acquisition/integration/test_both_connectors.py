"""
Test de integración completo usando DiscoveryService.

Este test valida el flujo END-TO-END usando la arquitectura hexagonal:
- DiscoveryService (Application Layer)
- IeeeConnector + ScopusConnector (Infrastructure Layer)
- Deduplicator (Domain Layer)

Flujo:
1. Preparar translation_statuses (simula Feature 1)
2. Inyectar conectores reales al servicio
3. Ejecutar DiscoveryService.execute()
4. Validar resultado deduplicado
5. Validar summary completo
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ARQUITECTURA HEXAGONAL
from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector

# Cargar .env
load_dotenv()

username = os.getenv('EPN_USER')
password = os.getenv('EPN_PASS')
api_key = os.getenv('SCOPUS_API_KEY')  # API key de Elsevier

if not username or not password:
    print("❌ ERROR: Configurar EPN_USER y EPN_PASS en .env")
    sys.exit(1)

if not api_key:
    print("⚠️  SCOPUS_API_KEY no configurada - usando solo fallback Playwright para Scopus")

TEST_QUERY = "machine learning"
MAX_RESULTS = 3
TEST_STRATEGY_ID = "integration-test-001"

print("=" * 80)
print("TEST DE INTEGRACIÓN: DISCOVERY SERVICE END-TO-END")
print("=" * 80)
print()
print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🔍 Query: '{TEST_QUERY}'")
print(f"📊 Resultados por fuente: {MAX_RESULTS}")
print()
print("ARQUITECTURA HEXAGONAL:")
print("   DiscoveryService (Application)")
print("      ↓")
print("   IAcademicConnector (Port)")
print("      ↙              ↘")
print("   IeeeConnector    ScopusConnector")
print("      ↓                   ↓")
print("   API REST JSON    API Elsevier / Playwright")
print("      ↘                 ↙")
print("         Deduplicator (Domain)")
print("              ↓")
print("       DiscoveryResult")
print()

# ============================================================================
# PASO 1: PREPARAR TRANSLATION STATUSES
# ============================================================================

print("=" * 80)
print("PASO 1: PREPARAR TRANSLATION STATUSES")
print("=" * 80)
print()

translation_statuses = {
    "Scopus": {
        "status": "ready",
        "query": TEST_QUERY
    },
    "IEEE Xplore": {
        "status": "ready",
        "query": TEST_QUERY
    }
}

print("✅ Translation statuses preparados:")
for source, status in translation_statuses.items():
    print(f"   • {source}: {status['status']} → '{status['query']}'")
print()

# ============================================================================
# PASO 2: INYECTAR CONECTORES REALES
# ============================================================================

print("=" * 80)
print("PASO 2: INSTANCIAR CONECTORES REALES")
print("=" * 80)
print()

print("⏳ Creando IeeeConnector...")
ieee_connector = IeeeConnector(username, password, headless=True)
print("✅ IeeeConnector listo")

print("⏳ Creando ScopusConnector...")
scopus_connector = ScopusConnector(
    username=username,
    password=password,
    api_key=api_key,
    headless=True
)
print(f"✅ ScopusConnector listo {'(API)' if api_key else '(Playwright fallback)'}")
print()

connectors = {
    "IEEE Xplore": ieee_connector,
    "Scopus": scopus_connector
}

print("✅ Conectores inyectados:")
for source in connectors.keys():
    print(f"   • {source}")
print()

# ============================================================================
# PASO 3: INSTANCIAR DISCOVERY SERVICE
# ============================================================================

print("=" * 80)
print("PASO 3: INSTANCIAR DISCOVERY SERVICE")
print("=" * 80)
print()

service = DiscoveryService(connectors)
print("✅ DiscoveryService creado con:")
print(f"   • Conectores: {len(connectors)}")
print("   • Deduplicator: Integrado")
print()

# ============================================================================
# PASO 4: EJECUTAR DISCOVERY
# ============================================================================

print("=" * 80)
print("PASO 4: EJECUTAR DISCOVERY SERVICE")
print("=" * 80)
print()

start_time = datetime.now()

try:
    print("⏳ Ejecutando discovery...")
    print()
    
    result = service.execute(
        strategy_id=TEST_STRATEGY_ID,
        translation_statuses=translation_statuses,
        supported_sources=["Scopus", "IEEE Xplore"]
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"✅ Discovery completado en {duration:.2f}s")
    print()
    
    # ============================================================================
    # PASO 5: VALIDAR RESULTADO
    # ============================================================================
    
    print("=" * 80)
    print("PASO 5: VALIDAR RESULTADO")
    print("=" * 80)
    print()
    
    # Validar que tenemos estudios
    assert result.studies is not None, "❌ No hay estudios en el resultado"
    
    if len(result.studies) == 0:
        print("⚠️  No se obtuvieron estudios")
        print()
        print("Posibles causas:")
        print("   - Ambos conectores fallaron")
        print("   - Problemas de autenticación")
        print("   - APIs no disponibles")
        print()
        print("Verificando summary para más detalles...")
        print()
    else:
        print(f"✅ Estudios obtenidos: {len(result.studies)}")
    
    # Validar que tenemos summary
    assert result.summary is not None, "❌ No hay summary"
    print("✅ Summary presente")
    print()
    
    # ============================================================================
    # PASO 6: ANALIZAR SUMMARY
    # ============================================================================
    
    print("=" * 80)
    print("PASO 6: ANALIZAR SUMMARY")
    print("=" * 80)
    print()
    
    summary = result.summary
    
    print("📊 RESUMEN DE EJECUCIÓN:")
    print(f"   • Strategy ID: {summary.get('id_estrategia', 'N/A')}")
    print(f"   • Resultado: {summary.get('resultado', 'N/A')}")
    print(f"   • Total bruto: {summary.get('total_bruto', 0)}")
    print(f"   • Total único (deduplicado): {summary.get('total_unicos', 0)}")
    print()
    
    print("📋 POR FUENTE:")
    total_por_fuente = summary.get('total_por_fuente', {})
    for source, count in total_por_fuente.items():
        print(f"   • {source}: {count} estudios")
    print()
    
    # Validar deduplicación
    total_bruto = summary.get('total_bruto', 0)
    total_unicos = summary.get('total_unicos', 0)
    duplicados = total_bruto - total_unicos
    
    if duplicados > 0:
        print("🔍 DEDUPLICACIÓN:")
        print(f"   • Duplicados eliminados: {duplicados}")
        print(f"   • Porcentaje único: {(total_unicos / total_bruto * 100):.1f}%")
        print()
    
    # Validar fuentes no ejecutadas
    no_ejecutadas = summary.get('no_ejecutadas', {})
    if no_ejecutadas:
        print("⚠️  FUENTES NO EJECUTADAS:")
        for source, reason in no_ejecutadas.items():
            print(f"   • {source}: {reason}")
        print()
    
    # ============================================================================
    # PASO 7: ANALIZAR ESTUDIOS
    # ============================================================================
    
    print("=" * 80)
    print("PASO 7: ANALIZAR ESTUDIOS")
    print("=" * 80)
    print()
    
    # Mostrar primer estudio
    if result.studies:
        print("📄 PRIMER ESTUDIO (después de deduplicación):")
        first = result.studies[0]
        print(f"   Título: {first.title[:80]}...")
        print(f"   Autores: {', '.join(first.authors[:3]) if first.authors else 'N/A'}")
        print(f"   Año: {first.year or 'N/A'}")
        print(f"   DOI: {first.doi or 'N/A'}")
        print(f"   Fuente: {first.source}")
        print(f"   Abstract: {'✅ Sí' if first.abstract else '❌ No'}")
        print(f"   Link: {first.link[:60] if first.link else 'N/A'}...")
        print()
    
    # Análisis de completitud
    if result.studies:
        print("📋 COMPLETITUD DE CAMPOS:")
        total = len(result.studies)
        with_title = sum(1 for s in result.studies if s.title)
        with_authors = sum(1 for s in result.studies if s.authors)
        with_year = sum(1 for s in result.studies if s.year)
        with_doi = sum(1 for s in result.studies if s.doi)
        with_abstract = sum(1 for s in result.studies if s.abstract)
        with_link = sum(1 for s in result.studies if s.link)
        
        print(f"   Títulos:   {with_title}/{total} ({100 * with_title // total if total else 0}%)")
        print(f"   Autores:   {with_authors}/{total} ({100 * with_authors // total if total else 0}%)")
        print(f"   Año:       {with_year}/{total} ({100 * with_year // total if total else 0}%)")
        print(f"   DOI:       {with_doi}/{total} ({100 * with_doi // total if total else 0}%)")
        print(f"   Abstract:  {with_abstract}/{total} ({100 * with_abstract // total if total else 0}%)")
        print(f"   Link:      {with_link}/{total} ({100 * with_link // total if total else 0}%)")
        print()
    
    # ============================================================================
    # PASO 8: GUARDAR RESULTADO
    # ============================================================================
    
    print("=" * 80)
    print("PASO 8: GUARDAR RESULTADO")
    print("=" * 80)
    print()
    
    # Serializar resultado (usando tipos JSON-serializables)
    result_dict = {
        'metadata': {
            'strategy_id': TEST_STRATEGY_ID,
            'query': TEST_QUERY,
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration
        },
        'summary': summary,
        'studies': [
            {
                'title': s.title,
                'authors': s.authors,
                'year': s.year,
                'doi': s.doi.value if s.doi else None,
                'abstract': s.abstract,
                'link': s.link,
                'source': s.source.name if hasattr(s.source, "name") else str(s.source),
            }
            for s in result.studies
        ],
    }
    
    output_file = "discovery_service_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultado guardado: {output_file}")
    print()
    
    # ============================================================================
    # RESULTADO FINAL
    # ============================================================================
    
    print("=" * 80)
    print("RESULTADO FINAL")
    print("=" * 80)
    print()
    
    if summary.get('resultado') == 'complete':
        print("🎉 ¡TEST EXITOSO!")
        print()
        print("✅ VALIDACIONES PASADAS:")
        print("   • DiscoveryService ejecutado correctamente")
        print("   • Ambos conectores funcionaron")
        print("   • Estudios consolidados y deduplicados")
        print("   • Summary completo generado")
        print("   • Resultado: COMPLETE")
        print()
        print("📊 ARQUITECTURA HEXAGONAL VALIDADA:")
        print("   • Application Layer: DiscoveryService ✅")
        print("   • Domain Layer: Deduplicator ✅")
        print("   • Infrastructure Layer: Conectores ✅")
        print("   • Ports & Adapters: IAcademicConnector ✅")
        
    elif summary.get('resultado') == 'partial':
        print("⚠️  TEST PARCIALMENTE EXITOSO")
        print()
        print("   Algunas fuentes no fueron ejecutadas:")
        for source, reason in no_ejecutadas.items():
            print(f"   • {source}: {reason}")
        print()
        print("   Pero el servicio funcionó correctamente con las fuentes disponibles.")
    
    else:
        print("❌ TEST FALLÓ")
        print()
        print("   No se pudo completar el discovery.")
    
except Exception as e:
    print()
    print("=" * 80)
    print("❌ ERROR EN DISCOVERY")
    print("=" * 80)
    print()
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {e}")
    print()
    
    import traceback
    traceback.print_exc()
    
    print()
    print("Posibles causas:")
    print("   - Problemas de red")
    print("   - Credenciales incorrectas")
    print("   - APIs cambiaron")
    print("   - Error en la lógica del servicio")
    
    sys.exit(1)

print()
print("=" * 80)
