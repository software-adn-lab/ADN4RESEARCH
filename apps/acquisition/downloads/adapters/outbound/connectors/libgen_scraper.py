"""
LibGen Scraper - Búsqueda y descarga desde Library Genesis.

LibGen es un repositorio de libros y papers académicos.
Cobertura: ~88M artículos científicos.

IMPORTANTE: Zona gris legal, igual que Sci-Hub.
Solo usar para investigación académica personal.
"""
import logging
import requests
import time
from typing import Optional, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LibGenScraper:
    """
    Scraper para búsqueda en LibGen (Library Genesis).

    Busca papers por DOI y extrae enlace de descarga.
    """

    # Dominios de LibGen (actualizados a 2025)
    LIBGEN_DOMAINS = [
        'https://libgen.is',
        'https://libgen.rs',
        'https://libgen.st',
    ]

    def __init__(
        self,
        enabled: bool = False,
        timeout: int = 30,
        delay: float = 3.0
    ):
        """
        Args:
            enabled: Si True, permite búsqueda en LibGen
            timeout: Timeout en segundos
            delay: Espera entre requests
        """
        self.enabled = enabled
        self.timeout = timeout
        self.delay = delay

        # Session con headers realistas
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        if not enabled:
            logger.warning("LibGenScraper DESHABILITADO")
        else:
            logger.info("LibGenScraper HABILITADO")

    def search_by_doi(self, doi: str) -> Optional[Dict[str, str]]:
        """
        Busca paper por DOI en LibGen.

        Args:
            doi: DOI del paper

        Returns:
            Dict con 'download_url' y 'mirror_url', o None
        """
        if not self.enabled:
            logger.debug("LibGen deshabilitado, saltando")
            return None

        if not doi:
            return None

        # Limpiar DOI
        clean_doi = doi.strip().replace('https://doi.org/', '').replace('http://dx.doi.org/', '')

        logger.info(f"[LibGen] Buscando: {clean_doi}")

        # Intentar con múltiples dominios
        for domain in self.LIBGEN_DOMAINS:
            try:
                result = self._search_in_domain(domain, clean_doi)
                if result:
                    logger.info(f"✓ [LibGen] Encontrado en {domain}")
                    return result

            except Exception as e:
                logger.debug(f"Dominio {domain} falló: {e}")
                continue

            time.sleep(self.delay)

        logger.warning(f"[LibGen] No encontrado: {clean_doi}")
        return None

    def _search_in_domain(self, domain: str, doi: str) -> Optional[Dict[str, str]]:
        """
        Busca en un dominio específico de LibGen.

        Args:
            domain: URL base de LibGen
            doi: DOI limpio

        Returns:
            Dict con URLs o None
        """
        # Construir URL de búsqueda
        # LibGen busca por DOI en la columna 'doi'
        search_url = f"{domain}/scimag/"
        params = {
            'q': doi,
            's': 'def',  # Búsqueda por defecto
        }

        response = self.session.get(search_url, params=params, timeout=self.timeout)
        response.raise_for_status()

        # Parsear resultados
        soup = BeautifulSoup(response.content, 'lxml')

        # Buscar tabla de resultados
        # LibGen usa diferentes estructuras según el dominio
        # Intentar encontrar enlaces de descarga

        # Método 1: Buscar enlaces directos
        download_links = soup.find_all('a', href=True)

        for link in download_links:
            href = link.get('href', '')

            # Buscar enlaces que parezcan descargas
            if 'download' in href.lower() or 'get.php' in href or 'ads.php' in href:
                # Construir URL completa
                if href.startswith('http'):
                    download_url = href
                else:
                    download_url = domain + href

                return {
                    'download_url': download_url,
                    'mirror_url': download_url,
                    'source': 'LibGen'
                }

        return None

    def download_from_url(self, url: str, output_path: str) -> bool:
        """
        Descarga PDF desde URL de LibGen.

        Args:
            url: URL de descarga
            output_path: Ruta donde guardar

        Returns:
            True si se descargó correctamente
        """
        try:
            logger.info(f"[LibGen] Descargando desde: {url}")

            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Verificar que sea PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not response.content[:4] == b'%PDF':
                logger.warning(f"Respuesta no es PDF: {content_type}")
                return False

            # Guardar
            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verificar tamaño
            from pathlib import Path
            size_kb = Path(output_path).stat().st_size / 1024
            if size_kb < 10:
                logger.warning(f"PDF sospechosamente pequeño: {size_kb:.2f} KB")
                Path(output_path).unlink()
                return False

            logger.info(f"PDF guardado: {output_path} ({size_kb:.2f} KB)")
            return True

        except Exception as e:
            logger.error(f"Error descargando desde LibGen: {e}")
            return False
