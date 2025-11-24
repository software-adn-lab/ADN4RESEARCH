"""
Test de integración para Alternative Source Finder.

Prueba búsqueda en fuentes alternativas:
1. LibGen (zona gris legal, OPT-IN)
2. Sci-Hub (zona gris legal, OPT-IN)

IMPORTANTE:
- LibGen y Sci-Hub están DESHABILITADOS por defecto
- Para habilitar: ENABLE_SCIHUB=true en .env
- Solo usar para investigación académica personal

Ejecutar con:
    python tests/acquisition/integration/test_alternative_sources.py
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
from apps.acquisition.downloads.adapters.outbound.connectors.alternative_source_finder import AlternativeSourceFinder

print("=" * 80)
print("TEST ALTERNATIVE SOURCE FINDER (LibGen + Sci-Hub)")
print("=" * 80)
print()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
ENABLE_SCIHUB = os.getenv("ENABLE_SCIHUB", "false").lower() == "true"

print("CONFIGURACIÓN:")
print(f"  ENABLE_SCIHUB: {ENABLE_SCIHUB}")
print()

if ENABLE_SCIHUB:
    print("⚠️  LibGen y Sci-Hub HABILITADOS - usar solo para investigación académica")
else:
    print("✅ LibGen y Sci-Hub DESHABILITADOS (por defecto)")

print()

# ============================================================================
# TEST 1: Fuentes alternativas deshabilitadas (comportamiento por defecto)
# ============================================================================
print("=" * 80)
print("TEST 1: Fuentes alternativas DESHABILITADAS (por defecto)")
print("=" * 80)
print()

study_disabled = Study.from_dict({
    "title": "Test Paper - Alternative Sources Disabled",
    "doi": "10.1109/TSE.2020.1234567",
    "source": "Manual",
    "link": "http://example.com"
})

print(f"📄 Paper: {study_disabled.title}")
print(f"   DOI: {study_disabled.doi.value if study_disabled.doi else 'N/A'}")
print()

finder_disabled = AlternativeSourceFinder(enable_scihub=False)

try:
    print("Intentando buscar con fuentes alternativas deshabilitadas...")
    pdf_path = finder_disabled.find_and_download(study_disabled)

    if pdf_path:
        print(f"❌ ERROR: No debería encontrar PDF con fuentes deshabilitadas")
    else:
        print(f"✅ Comportamiento correcto: No se buscó en fuentes alternativas")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# ============================================================================
# TEST 2: LibGen y Sci-Hub (solo si habilitados)
# ============================================================================
if ENABLE_SCIHUB:
    print("=" * 80)
    print("TEST 2: LibGen y Sci-Hub HABILITADOS")
    print("=" * 80)
    print()

    finder_enabled = AlternativeSourceFinder(enable_scihub=True)

    # Paper conocido que probablemente esté en LibGen/Sci-Hub
    study_enabled = Study.from_dict({
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "source": "Manual",
        "link": "http://example.com"
    })

    print(f"📄 Paper: {study_enabled.title}")
    print(f"   DOI: {study_enabled.doi.value if study_enabled.doi else 'N/A'}")
    print()

    print("⚠️  Buscando en LibGen y Sci-Hub...")
    print("   (Esto puede tardar ~10-15 segundos)")
    print()

    try:
        pdf_path = finder_enabled.find_and_download(study_enabled)

        if pdf_path:
            pdf_file = Path(pdf_path)
            if pdf_file.exists():
                size_kb = pdf_file.stat().st_size / 1024
                print(f"✅ PDF DESCARGADO")
                print(f"   Ruta: {pdf_path}")
                print(f"   Tamaño: {size_kb:.2f} KB")
                print(f"   Fuente: LibGen o Sci-Hub")
            else:
                print(f"⚠️  Ruta reportada pero archivo no existe")
        else:
            print(f"⚠️  No se encontró PDF en LibGen ni Sci-Hub")
            print(f"   (Dominios pueden estar bloqueados o paper no disponible)")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()

    # ====================================================================
    # TEST 3: Paper NO disponible (para ver flujo completo)
    # ====================================================================
    print("=" * 80)
    print("TEST 3: Paper NO disponible en ninguna fuente")
    print("=" * 80)
    print()

    # Paper con DOI inválido/no existente
    study_notfound = Study.from_dict({
        "title": "Test Paper - Not Found",
        "doi": "10.9999/notfound.2025.99999",
        "source": "Manual",
        "link": "http://example.com"
    })

    print(f"📄 Paper: {study_notfound.title}")
    print(f"   DOI: {study_notfound.doi.value if study_notfound.doi else 'N/A'}")
    print()

    try:
        print("Buscando en LibGen y Sci-Hub...")
        pdf_path = finder_enabled.find_and_download(study_notfound)

        if pdf_path:
            print(f"⚠️  PDF encontrado (inesperado): {pdf_path}")
        else:
            print(f"✅ Comportamiento esperado: No encontrado en ninguna fuente")

    except Exception as e:
        print(f"⚠️  Error esperado (DOI no válido): {e}")

    print()

else:
    print("=" * 80)
    print("TESTS 2-3 OMITIDOS")
    print("=" * 80)
    print()
    print("Para ejecutar tests completos, habilitar en .env:")
    print("  ENABLE_SCIHUB=true")
    print()

# ============================================================================
# RESUMEN
# ============================================================================
print("=" * 80)
print("RESUMEN")
print("=" * 80)
print()

print("FUENTES ALTERNATIVAS IMPLEMENTADAS:")
print("  ⚠️  LibGen - Library Genesis (~88M papers)")
print("  ⚠️  Sci-Hub - Último recurso (~88M papers)")
print()

print("ESTADO:")
if ENABLE_SCIHUB:
    print("  ⚠️  LibGen y Sci-Hub - HABILITADOS (zona gris legal)")
else:
    print("  ✅ LibGen y Sci-Hub - DESHABILITADOS")
print()

print("CASCADA COMPLETA EN PRODUCCIÓN:")
print("  1. Hint desde Discovery (IEEE/Scopus OA)")
print("  2. Unpaywall (API gratuita)")
print("  3. Crossref (API gratuita)")
print("  4. Scopus API (institucional)")
if ENABLE_SCIHUB:
    print("  5. LibGen (zona gris, habilitado)")
    print("  6. Sci-Hub (zona gris, habilitado)")
else:
    print("  5. LibGen (zona gris, DESHABILITADO)")
    print("  6. Sci-Hub (zona gris, DESHABILITADO)")
print("  7. Marcar como no_disponible (carga manual)")
print()

print("NOTAS:")
print("  - LibGen: ~88M artículos científicos (todas las disciplinas)")
print("  - Sci-Hub: ~88M papers (todas las disciplinas)")
print("  - Ambos operan en zona gris legal")
print()

print("CONSIDERACIONES LEGALES:")
print("  - LibGen y Sci-Hub están DESHABILITADOS por defecto")
print("  - Solo usar para investigación académica personal")
print("  - Citar apropiadamente todos los trabajos")
print("  - Verificar leyes locales antes de habilitar")
print()

print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
