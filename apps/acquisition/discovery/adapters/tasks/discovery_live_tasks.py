"""
Discovery Tasks con conectores REALES (IEEE + Scopus vía scrapers).

IMPORTANTE: Solo usar en producción/desarrollo local, NO en tests.

Uso:
    from apps.acquisition.discovery.adapters.tasks.discovery_live_tasks import execute_live_discovery

    result = execute_live_discovery(
        strategy=translated_strategy,
        sources=["IEEE Xplore", "Scopus"]
    )

Requisitos:
- Credenciales EPN_USER y EPN_PASS en .env
- Estar en red EPN o VPN institucional
- Playwright instalado: `playwright install chromium`
"""
import os
import logging
from typing import List, Optional

from apps.acquisition.discovery.application.discovery_service import DiscoveryService
from apps.acquisition.discovery.adapters.outbound.connectors.ieee_connector import IeeeConnector
from apps.acquisition.discovery.adapters.outbound.connectors.scopus_connector import ScopusConnector
from apps.acquisition.search_strategy.domain.models import SearchStrategy

logger = logging.getLogger(__name__)


def get_live_connectors() -> dict:
    """
    Retorna conectores REALES con scrapers via EZproxy.

    Returns:
        Diccionario con conectores instanciados
    """
    username = os.getenv('EPN_USER')
    password = os.getenv('EPN_PASS')

    if not username or not password:
        raise ValueError(
            "Credenciales no encontradas. "
            "Define EPN_USER y EPN_PASS en .env"
        )

    logger.info("Inicializando conectores reales...")

    connectors = {
        "IEEE Xplore": IeeeConnector(
            username=username,
            password=password,
            headless=True,  # Sin ventana visible
            rate_limit=2.0
        ),
        "Scopus": ScopusConnector(
            username=username,
            password=password,
            headless=True,
            rate_limit=2.0
        )
    }

    logger.info(f"✓ Conectores listos: {list(connectors.keys())}")

    return connectors


def execute_live_discovery(
    strategy: SearchStrategy,
    sources: Optional[List[str]] = None
) -> dict:
    """
    Ejecuta búsqueda con conectores REALES.

    Args:
        strategy: Estrategia de búsqueda traducida
        sources: Lista de fuentes a consultar (default: todas)

    Returns:
        Diccionario con resultados:
        {
            'total_results': int,
            'sources': {
                'IEEE Xplore': [...],
                'Scopus': [...]
            }
        }

    Raises:
        ValueError: Si credenciales no están configuradas
        Exception: Si falla autenticación o búsqueda
    """
    logger.info("=" * 70)
    logger.info("DISCOVERY SERVICE - MODO REAL (Scrapers)")
    logger.info("=" * 70)

    # Inicializar conectores reales
    connectors = get_live_connectors()

    # Filtrar por fuentes solicitadas
    if sources:
        connectors = {k: v for k, v in connectors.items() if k in sources}
        logger.info(f"Fuentes solicitadas: {sources}")

    # Crear servicio
    service = DiscoveryService(connectors=connectors)

    # Ejecutar búsqueda
    logger.info(f"Ejecutando búsqueda...")
    logger.info(f"Estrategia: {strategy.to_dict()}")

    result = service.execute(
        strategy=strategy,
        sources=list(connectors.keys())
    )

    logger.info("=" * 70)
    logger.info(f"✅ Búsqueda completada")
    logger.info(f"Total resultados: {result.get('total_results', 0)}")
    logger.info("=" * 70)

    return result


# Ejemplo de uso
if __name__ == "__main__":
    """
    Ejemplo standalone para probar discovery con scrapers reales.

    Uso:
        python -m apps.acquisition.discovery.adapters.tasks.discovery_live_tasks
    """
    import sys
    from pathlib import Path

    # Setup Django
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

    from dotenv import load_dotenv
    load_dotenv()

    # Crear estrategia de ejemplo
    from apps.acquisition.search_strategy.domain.models import SearchStrategy

    strategy = SearchStrategy(
        scopus_query="TITLE-ABS-KEY(machine AND learning)",
        ieee_query="machine learning"
    )

    print("\n" + "=" * 70)
    print("TEST: Discovery Service con Scrapers Reales")
    print("=" * 70)
    print()

    try:
        result = execute_live_discovery(
            strategy=strategy,
            sources=["IEEE Xplore"]  # Solo IEEE por ahora
        )

        print()
        print("RESULTADOS:")
        print(f"Total: {result.get('total_results', 0)}")
        print()

        for source, studies in result.get('sources', {}).items():
            print(f"{source}: {len(studies)} estudios")
            for i, study in enumerate(studies[:3], 1):  # Mostrar 3 primeros
                print(f"  {i}. {study['title']}")

        print()
        print("✅ Test exitoso")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
