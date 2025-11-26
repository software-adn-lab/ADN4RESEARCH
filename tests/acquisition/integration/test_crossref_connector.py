"""
Test de integración para CrossrefConnector.

Este test hace llamadas REALES a la API de Crossref (gratuita, sin API key).
Verifica que el conector funciona correctamente para enriquecer metadatos.

Ejecutar con:
    python tests/acquisition/integration/test_crossref_connector.py
"""
import sys
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.acquisition.discovery.adapters.outbound.connectors.crossref_connector import CrossrefConnector

print("=" * 80)
print("TEST CROSSREF CONNECTOR (API GRATUITA)")
print("=" * 80)
print()

# Inicializar conector
connector = CrossrefConnector(email="test@epn.edu.ec")

# Títulos de prueba (papers conocidos con metadatos para validación cruzada)
TEST_PAPERS = [
    {
        "title": "Deep Learning",
        "authors": ["LeCun", "Bengio", "Hinton"],  # Autores para validar
        "year": 2015,
        "expected_doi": "10.1038/nature14539",
    },
    {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani", "Shazeer", "Parmar"],
        "year": 2017,
        "expected_doi": None,
    },
    {
        "title": "A Survey on Machine Learning for Software Engineering",
        "authors": None,
        "year": None,
        "expected_doi": None,
    },
]

print("=" * 80)
print("TEST 1: find_metadata() - Búsqueda por título")
print("=" * 80)
print()

for i, paper in enumerate(TEST_PAPERS, 1):
    title = paper["title"]
    authors = paper.get("authors")
    year = paper.get("year")
    print(f"[{i}] Buscando: '{title}'")
    if authors:
        print(f"    Con autores: {authors}")
    if year:
        print(f"    Con año: {year}")
    print("-" * 60)

    try:
        result = connector.find_metadata(title, authors=authors, year=year)

        if result:
            print(f"   ✅ Encontrado! (score: {result.get('match_score', 'N/A')})")
            print(f"   DOI: {result.get('doi', 'N/A')}")
            print(f"   Título: {result.get('title', 'N/A')[:60]}...")
            print(f"   Año: {result.get('year', 'N/A')}")
            authors_list = result.get('authors') or []
            print(f"   Autores: {authors_list[:3]}{'...' if len(authors_list) > 3 else ''}")
            print(f"   Journal: {result.get('journal', 'N/A')}")
            print(f"   Abstract: {'Sí' if result.get('abstract') else 'No disponible'}")

            # Verificar DOI esperado si existe
            if paper["expected_doi"]:
                if result.get("doi", "").lower() == paper["expected_doi"].lower():
                    print(f"   ✅ DOI coincide con esperado!")
                else:
                    print(f"   ⚠️ DOI diferente: esperado={paper['expected_doi']}")
        else:
            print(f"   ❌ No encontrado")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()

print("=" * 80)
print("TEST 2: search() - Búsqueda general")
print("=" * 80)
print()

SEARCH_QUERY = "machine learning software testing"
MAX_RESULTS = 3

print(f"Query: '{SEARCH_QUERY}' (max: {MAX_RESULTS})")
print("-" * 60)

try:
    results = list(connector.search(SEARCH_QUERY, max_results=MAX_RESULTS))
    print(f"✅ Resultados: {len(results)}")
    print()

    for i, result in enumerate(results, 1):
        print(f"[{i}] {result.get('title', 'Sin título')[:70]}...")
        print(f"    DOI: {result.get('doi', 'N/A')}")
        print(f"    Año: {result.get('year', 'N/A')}")
        print()

except Exception as e:
    print(f"❌ Error en búsqueda: {e}")

print("=" * 80)
print("TEST 3: Validación de títulos similares")
print("=" * 80)
print()

# Test con título que NO debería coincidir (falso positivo)
WRONG_TITLE = "asdfghjkl qwertyuiop zxcvbnm"  # Título inventado
print(f"Buscando título inexistente: '{WRONG_TITLE}'")
print("-" * 60)

result = connector.find_metadata(WRONG_TITLE)
if result is None:
    print("✅ Correctamente retornó None (no encontrado)")
else:
    print(f"⚠️ Encontró algo (posible falso positivo): {result.get('title', 'N/A')[:50]}")

print()

print("=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
