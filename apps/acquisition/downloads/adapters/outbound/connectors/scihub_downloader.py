"""
Sci-Hub Downloader - Descarga PDFs desde Sci-Hub.

⚠️  AVISO LEGAL:
Este módulo se proporciona ÚNICAMENTE para investigación académica personal.
El uso de Sci-Hub puede violar leyes de copyright en algunas jurisdicciones.

RECOMENDACIONES:
- Usar SOLO como último recurso (después de Unpaywall, Crossref, institucional)
- Verificar leyes locales antes de usar
- Preferir siempre fuentes oficiales y Open Access
- En Ecuador: Consultar Art. 379 de la Constitución sobre acceso a conocimiento

USO RESPONSABLE:
- Solo para investigación académica personal
- No redistribuir PDFs descargados
- Respetar términos de uso institucionales
- Citar apropiadamente todos los trabajos

IMPLEMENTACIÓN:
Este downloader está DESHABILITADO por defecto.
Para habilitarlo, establecer ENABLE_SCIHUB=true en .env
"""
import logging
import time
import requests
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SciHubDownloader:
    """
    Descargador de PDFs desde Sci-Hub.

    IMPORTANTE: Deshabilitado por defecto por consideraciones legales.
    Solo se activa si el usuario explícitamente lo habilita.
    """

    # Dominios de Sci-Hub (actualizados a 2025)
    # NOTA: Estos dominios cambian frecuentemente debido a bloqueos
    SCIHUB_DOMAINS = [
        'https://sci-hub.se',
        'https://sci-hub.st',
        'https://sci-hub.ru',
        'https://sci-hub.ren',
    ]

    def __init__(
        self,
        enabled: bool = False,
        timeout: int = 30,
        delay_between_requests: float = 3.0,
        base_dir: str = "media/papers"
    ):
        """
        Args:
            enabled: Si True, permite descargas desde Sci-Hub
            timeout: Timeout en segundos para requests
            delay_between_requests: Espera entre peticiones (anti-bloqueo)
            base_dir: Directorio base para guardar PDFs
        """
        self.enabled = enabled
        self.timeout = timeout
        self.delay = delay_between_requests
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Session con headers realistas
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        })

        if not enabled:
            logger.warning(
                "⚠️  SciHubDownloader DESHABILITADO. "
                "Para habilitar, establecer ENABLE_SCIHUB=true en .env"
            )
        else:
            logger.info(
                "⚠️  SciHubDownloader HABILITADO. "
                "Usar SOLO como último recurso para investigación académica."
            )

    def download(self, doi: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Descarga PDF desde Sci-Hub usando DOI.

        Args:
            doi: DOI del paper
            output_path: Ruta donde guardar (opcional, se genera automática)

        Returns:
            Ruta del PDF descargado o None si falla
        """
        if not self.enabled:
            logger.debug("Sci-Hub deshabilitado, saltando")
            return None

        if not doi:
            return None

        # Limpiar DOI
        clean_doi = doi.strip().replace('https://doi.org/', '').replace('http://dx.doi.org/', '')

        logger.info(f"[Sci-Hub] Intentando descargar: {clean_doi}")

        # Intentar con múltiples dominios
        for domain in self.SCIHUB_DOMAINS:
            try:
                pdf_path = self._download_from_domain(domain, clean_doi, output_path)
                if pdf_path:
                    logger.info(f"✓ [Sci-Hub] PDF descargado desde {domain}")
                    return pdf_path

            except Exception as e:
                logger.debug(f"Dominio {domain} falló: {e}")
                continue

            # Rate limiting entre intentos
            time.sleep(self.delay)

        logger.warning(f"[Sci-Hub] No se pudo descargar: {clean_doi}")
        return None

    def _download_from_domain(
        self,
        domain: str,
        doi: str,
        output_path: Optional[str]
    ) -> Optional[str]:
        """
        Intenta descargar desde un dominio específico de Sci-Hub.

        Args:
            domain: URL base de Sci-Hub
            doi: DOI limpio
            output_path: Ruta de salida

        Returns:
            Ruta del PDF descargado o None
        """
        # Construir URL de Sci-Hub
        scihub_url = f"{domain}/{doi}"

        # Obtener página de Sci-Hub
        response = self.session.get(scihub_url, timeout=self.timeout)
        response.raise_for_status()

        # Parsear HTML para encontrar enlace del PDF
        soup = BeautifulSoup(response.content, 'lxml')

        # Sci-Hub puede tener el PDF en diferentes elementos
        pdf_url = None

        # Método 1: iframe embed
        iframe = soup.find('iframe', {'id': 'pdf'})
        if iframe and iframe.get('src'):
            pdf_url = iframe['src']

        # Método 2: button/link directo
        if not pdf_url:
            pdf_button = soup.find('button', {'onclick': True})
            if pdf_button:
                onclick = pdf_button.get('onclick', '')
                if 'location.href=' in onclick:
                    pdf_url = onclick.split("'")[1]

        # Método 3: embed tag
        if not pdf_url:
            embed = soup.find('embed', {'type': 'application/pdf'})
            if embed and embed.get('src'):
                pdf_url = embed['src']

        if not pdf_url:
            return None

        # Asegurar URL absoluta
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = domain + pdf_url

        logger.debug(f"PDF URL encontrada: {pdf_url}")

        # Descargar el PDF
        pdf_response = self.session.get(pdf_url, timeout=self.timeout)
        pdf_response.raise_for_status()

        # Verificar que sea PDF
        content_type = pdf_response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower() and not pdf_response.content.startswith(b'%PDF'):
            logger.warning(f"Respuesta no es PDF: {content_type}")
            return None

        # Determinar ruta de salida
        if output_path:
            final_path = Path(output_path)
        else:
            # Generar nombre único
            import uuid
            filename = f"{uuid.uuid4()}.pdf"
            final_path = self.base_dir / filename

        # Guardar PDF
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(pdf_response.content)

        # Verificar tamaño
        size_kb = final_path.stat().st_size / 1024
        if size_kb < 10:  # PDFs muy pequeños probablemente sean errores
            logger.warning(f"PDF sospechosamente pequeño: {size_kb:.2f} KB")
            final_path.unlink()
            return None

        logger.info(f"PDF guardado: {final_path} ({size_kb:.2f} KB)")
        return str(final_path)

    def test_connection(self) -> bool:
        """
        Prueba conectividad con dominios de Sci-Hub.

        Returns:
            True si al menos un dominio responde
        """
        if not self.enabled:
            return False

        for domain in self.SCIHUB_DOMAINS:
            try:
                response = self.session.get(domain, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✓ Sci-Hub accesible: {domain}")
                    return True
            except:
                continue

        logger.warning("⚠️  Ningún dominio de Sci-Hub es accesible")
        return False
