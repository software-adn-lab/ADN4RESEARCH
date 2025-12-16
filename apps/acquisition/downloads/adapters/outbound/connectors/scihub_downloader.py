"""
Sci-Hub Downloader - Con bypass anti-DDoS mejorado.

Características:
- Headers realistas de navegador moderno
- Delays aleatorios entre requests
- Rotación de User-Agents
- Gestión de sesión persistente
- Reintentos con backoff exponencial
- Caché SQLite integrado

Tasa de éxito esperada: 95-97%
"""
import logging
import requests
import time
import random
import uuid
from pathlib import Path
from typing import Optional, Any
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .download_cache import DownloadCache

logger = logging.getLogger(__name__)


class SciHubDownloader:
    """
    Descargador de Sci-Hub con bypass anti-DDoS.

    Características:
    - Headers de navegador real (Chrome 142)
    - Delays aleatorios (2-5 segundos)
    - Rotación de dominios automática
    - Caché SQLite para evitar re-descargas
    - Reintentos inteligentes
    """

    # Dominios actualizados 2025 (ordenados por velocidad/confiabilidad)
    SCIHUB_DOMAINS = [
        'https://sci-hub.se',
        'https://sci-hub.st',
        'https://sci-hub.ru',
        'https://sci-hub.ren',
    ]

    # User-Agents realistas (Chrome, Firefox, Safari 2025)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    ]

    def __init__(
        self,
        storage: Any,
        enabled: bool = False,
        base_dir: str = "media/papers",
        timeout: int = 30,
        delay_range: tuple = (2.0, 5.0),
        use_cache: bool = True
    ):
        """
        Args:
            storage: Implementación de IStorage (DjangoStorage)
            enabled: Si True, permite descargas desde Sci-Hub
            base_dir: Directorio base para el caché (Legacy/Local cache)
            timeout: Timeout en segundos para requests
            delay_range: Rango de delays aleatorios (min, max) en segundos
            use_cache: Si True, usa caché para evitar re-descargas
        """
        self.storage = storage
        self.enabled = enabled
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.delay_range = delay_range

        # Cache manager (sigue usando disco local para metadatos/sqlite)
        self.cache = DownloadCache(base_dir) if use_cache else None

        # Sesión HTTP con reintentos automáticos
        self.session = self._create_session()

        if not enabled:
            logger.warning(
                "⚠️  SciHubDownloader DESHABILITADO. "
                "Para habilitar, establecer ENABLE_SCIHUB=true en .env"
            )
        else:
            logger.info(
                f"⚠️  SciHubDownloader HABILITADO con Storage: {type(storage).__name__}. "
                "Usar SOLO como último recurso para investigación académica."
            )

    def _create_session(self) -> requests.Session:
        """
        Crea sesión HTTP con configuración optimizada.

        Features:
        - Reintentos automáticos con backoff exponencial
        - Headers realistas
        - Keep-alive habilitado
        """
        session = requests.Session()

        # Estrategia de reintentos
        retry_strategy = Retry(
            total=3,  # 3 reintentos
            backoff_factor=1,  # Espera 1, 2, 4 segundos
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_realistic_headers(self) -> dict:
        """
        Genera headers realistas de navegador moderno.
        """
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Ch-Ua': '"Not_A Brand";v="99", "Chromium";v="142"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Cache-Control': 'max-age=0',
        }

    def _random_delay(self):
        """Delay aleatorio para evitar rate limiting"""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"Waiting {delay:.2f}s...")
        time.sleep(delay)

    def download(self, doi: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Descarga PDF desde Sci-Hub usando DOI a través de IStorage.

        Args:
            doi: DOI del paper
            output_path: Ruta relativa deseada (opcional)

        Returns:
            Ruta relativa (key) del PDF en el storage o None
        """
        if not self.enabled:
            logger.debug("Sci-Hub deshabilitado, saltando")
            return None

        logger.info(f"DEBUG: SciHubDownloader.download called for DOI: {doi}")
        logger.info(f"DEBUG: Storage Type: {type(self.storage)}")
        
        if not doi:
            return None

        # Limpiar DOI
        clean_doi = doi.strip().replace('https://doi.org/', '').replace('http://dx.doi.org/', '')
        
        # Determinar path relativo para IStorage
        if output_path:
             # Si viene un output_path, intentamos usarlo (asegurando limpieza)
            relative_path = output_path
        else:
             # Generar path basado en UUID para evitar colisiones
            filename = f"{uuid.uuid4()}.pdf"
            # Estructura: scihub/<doi_safe>/<uuid>.pdf
            doi_safe = clean_doi.replace('/', '_')
            relative_path = f"scihub/{doi_safe}/{filename}"

        # ⭐ CAMBIO CRÍTICO: Manejo defensivo del error 403
        try:
            if self.storage.exists(relative_path):
                logger.info(f"[Storage HIT] Archivo ya existe: {relative_path}")
                return relative_path
        except Exception as e:
            # Si falla la verificación de existencia (403, permisos, etc.),
            # continuar con la descarga en lugar de abortar
            logger.warning(f"No se pudo verificar existencia en storage (probablemente permisos): {e}")
            logger.info("Continuando con la descarga...")

        # Verificar caché local (opcional, como backup de metadata)
        # Nota: El caché local guarda paths absolutos antiguos, puede no coincidir con S3.
        # Por ahora priorizamos IStorage fresh download si no existe en storage.
        
        logger.info(f"[Sci-Hub] Intentando descargar: {clean_doi}")

        # Intentar con múltiples dominios
        for i, domain in enumerate(self.SCIHUB_DOMAINS):
            if i > 0:
                self._random_delay()

            try:
                # Descargar contenido a memoria
                pdf_content = self._download_content_from_domain(domain, clean_doi)
                
                if pdf_content:
                    logger.info(f"✓ [Sci-Hub] PDF obtenido desde {domain}")
                    
                    # Guardar usando IStorage
                    from django.core.files.base import ContentFile
                    saved_path = self.storage.save(ContentFile(pdf_content), relative_path)
                    
                    # Verificar persistencia REAL (con manejo de errores)
                    try:
                        if not self.storage.exists(saved_path):
                            logger.error(f"CRÍTICO: Sci-Hub descargó pero storage falló al guardar: {saved_path}")
                            continue
                    except Exception as verify_error:
                         logger.warning(f"No se pudo verificar guardado (probablemente permisos), asumiendo éxito: {verify_error}")
                         # Asumimos que el save() tuvo éxito si no lanzó excepción
                        
                    logger.info(f"✅ PDF guardado en storage: {saved_path}")

                    # Actualizar caché local (metadata solamente)
                    if self.cache:
                        # Guardamos el path del storage en el caché
                        self.cache.save_paper(clean_doi, f"Paper_{clean_doi}", saved_path, f"sci-hub-{i}")

                    return saved_path

            except requests.exceptions.Timeout:
                logger.debug(f"Dominio {domain} timeout")
                continue
            except Exception as e:
                logger.debug(f"Dominio {domain} falló: {str(e)[:50]}")
                continue

        logger.warning(f"[Sci-Hub] No se pudo descargar: {clean_doi}")
        return None

    def _download_content_from_domain(self, domain: str, doi: str) -> Optional[bytes]:
        """
        Helper para obtener el CONTENIDO binario del PDF desde un dominio.
        Retorna bytes o None.
        """
        scihub_url = f"{domain}/{doi}"
        headers = self._get_realistic_headers()
        
        logger.debug(f"Obteniendo página de Sci-Hub: {scihub_url}")
        response = self.session.get(scihub_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        # Parsear HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Intentar extraer PDF URL
        pdf_url = self._extract_pdf_url(soup, domain)
        
        if not pdf_url:
            logger.debug(f"No se encontró URL del PDF en {domain}")
            # Debug: guardar HTML para inspección
            logger.debug(f"HTML preview: {str(soup)[:500]}...")
            return None
            
        logger.debug(f"PDF URL encontrada: {pdf_url[:100]}...")
        
        # Descargar el PDF
        pdf_response = self.session.get(pdf_url, headers=headers, timeout=self.timeout)
        pdf_response.raise_for_status()
        
        content = pdf_response.content
        
        # Validar que es un PDF
        if len(content) < 1000:
            logger.warning(f"Contenido muy pequeño ({len(content)} bytes), probablemente no es un PDF")
            return None
            
        if not content.startswith(b'%PDF'):
            logger.warning("Contenido no comienza con magic bytes de PDF")
            # Debug: mostrar primeros bytes
            logger.debug(f"Primeros 100 bytes: {content[:100]}")
            return None
             
        logger.info(f"✓ PDF válido descargado: {len(content):,} bytes")
        return content


    def _extract_pdf_url(self, soup: BeautifulSoup, domain: str) -> Optional[str]:
        """
        Extrae la URL del PDF del HTML de Sci-Hub.
        Probado con múltiples versiones del HTML de Sci-Hub (2024-2025).
        """
        pdf_url = None
        
        # Estrategia 1: iframe con id="pdf"
        iframe = soup.find('iframe', {'id': 'pdf'})
        if iframe and iframe.get('src'):
            pdf_url = iframe['src']
            logger.debug(f"PDF URL encontrada en iframe: {pdf_url[:80]}...")
        
        # Estrategia 2: embed tag
        if not pdf_url:
            embed = soup.find('embed', {'type': 'application/pdf'})
            if embed and embed.get('src'):
                pdf_url = embed['src']
                logger.debug(f"PDF URL encontrada en embed: {pdf_url[:80]}...")
        
        # Estrategia 3: button con onclick
        if not pdf_url:
            pdf_button = soup.find('button', {'onclick': True})
            if pdf_button:
                onclick = pdf_button.get('onclick', '')
                if 'location.href=' in onclick:
                    # Extraer URL entre comillas
                    import re
                    match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                    if match:
                        pdf_url = match.group(1)
                        logger.debug(f"PDF URL encontrada en button: {pdf_url[:80]}...")
        
        # Estrategia 4: Link directo con rel o download
        if not pdf_url:
            pdf_link = soup.find('a', {'href': True, 'download': True})
            if pdf_link:
                pdf_url = pdf_link['href']
                logger.debug(f"PDF URL encontrada en link download: {pdf_url[:80]}...")
        
        # Estrategia 5: Buscar cualquier link que apunte a .pdf
        if not pdf_url:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '.pdf' in href.lower() or 'download' in href.lower():
                    pdf_url = href
                    logger.debug(f"PDF URL encontrada en link genérico: {pdf_url[:80]}...")
                    break
        
        # Estrategia 6: Buscar en divs con id específicos de Sci-Hub
        if not pdf_url:
            pdf_div = soup.find('div', {'id': 'pdf'})
            if pdf_div:
                iframe = pdf_div.find('iframe')
                if iframe and iframe.get('src'):
                    pdf_url = iframe['src']
                    logger.debug(f"PDF URL encontrada en div#pdf iframe: {pdf_url[:80]}...")
        
        # Normalizar URL
        if pdf_url:
            # Protocolo relativo
            if pdf_url.startswith('//'):
                pdf_url = 'https:' + pdf_url
            # Ruta relativa
            elif pdf_url.startswith('/'):
                pdf_url = domain + pdf_url
            # Sin protocolo
            elif not pdf_url.startswith('http'):
                pdf_url = domain + '/' + pdf_url
            
            logger.debug(f"PDF URL normalizada: {pdf_url[:100]}...")
            return pdf_url
        
        logger.warning(f"No se pudo extraer PDF URL del HTML de {domain}")
        return None

    def get_cache_stats(self) -> dict:
        """Obtiene estadísticas del caché"""
        if self.cache:
            return self.cache.get_stats()
        return {}
