"""
Scopus Connector con API oficial de Elsevier y fallback a Playwright.

ESTRATEGIA DE ACCESO:
1. API oficial de Elsevier (api.elsevier.com) - Requiere API key
   - Rápido, confiable, datos completos
   - Límites: 20,000 búsquedas/semana, 10,000 abstracts/semana

2. Fallback: APIs internas de Scopus vía Playwright (EZproxy)
   - Más lento (requiere navegador)
   - Útil si no hay API key o si la cuota se agotó

ENDPOINTS ELSEVIER:
- GET /content/search/scopus -> Búsqueda
- GET /content/abstract/scopus_id/{id} -> Abstract

DOCS: https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl
"""
import logging
import time
import random
import re
from typing import Dict, List, Any, Generator, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

logger = logging.getLogger(__name__)


class ScopusConnector:
    """
    Conector para Scopus con API oficial de Elsevier y fallback a Playwright.

    Características:
    - Usa API oficial primero (rápido, sin navegador)
    - Fallback automático a Playwright si API falla
    - Rate limiting configurable
    - Retry automático con backoff exponencial
    """

    # URLs API oficial de Elsevier
    ELSEVIER_BASE_URL = "https://api.elsevier.com"
    SEARCH_ENDPOINT = "/content/search/scopus"
    ABSTRACT_ENDPOINT = "/content/abstract/scopus_id"

    def __init__(
        self,
        username: str = None,
        password: str = None,
        api_key: str = None,
        headless: bool = True,
        rate_limit: float = 1.0
    ):
        """
        Args:
            username: Usuario EPN (para fallback Playwright)
            password: Contraseña EPN (para fallback Playwright)
            api_key: API key de Elsevier (para API oficial)
            headless: Navegador sin interfaz (para fallback)
            rate_limit: Segundos de espera entre requests
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.headless = headless
        self.rate_limit = rate_limit

        # Session para requests
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'ADN4Research/1.0 (Academic Research Tool)'
        })

        if api_key:
            self.session.headers['X-ELS-APIKey'] = api_key
            logger.info("ScopusConnector inicializado con API key de Elsevier")
        else:
            logger.warning("ScopusConnector sin API key - solo fallback Playwright disponible")

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Busca artículos en Scopus.

        Intenta primero con API oficial, luego fallback a Playwright.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a retornar

        Yields:
            Dict normalizado con title, link, doi, source, year, authors, abstract
        """
        logger.info(f"Buscando en Scopus: '{query}' (max: {max_results})")

        results = []

        # Intentar con API oficial de Elsevier
        if self.api_key:
            try:
                logger.info("Usando API oficial de Elsevier...")
                results = list(self._search_via_api(query, max_results))

                if results:
                    logger.info(f"✓ API Elsevier: {len(results)} resultados obtenidos")
                else:
                    logger.warning("API Elsevier no devolvió resultados, intentando fallback...")
                    raise ValueError("Sin resultados en API")

            except Exception as api_error:
                logger.warning(f"API Elsevier falló: {api_error}")
                results = []

        # Fallback a Playwright si API falló o no hay API key
        if not results:
            if self.username and self.password:
                logger.info("Usando fallback Playwright (APIs internas de Scopus)...")
                try:
                    results = list(self._search_via_playwright(query, max_results))
                except Exception as pw_error:
                    logger.error(f"Fallback Playwright también falló: {pw_error}")
                    raise
            else:
                raise ValueError(
                    "API de Elsevier falló y no hay credenciales EZproxy para fallback. "
                    "Proporcione api_key o username/password."
                )

        # Yield resultados
        for result in results:
            yield result

        # Rate limiting
        delay = self.rate_limit + random.uniform(0.1, 0.5)
        time.sleep(delay)

        logger.info(f"✓ Búsqueda completada: {len(results)} resultados")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=True
    )
    def _search_via_api(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Busca usando API oficial de Elsevier.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        results = []
        start = 0
        count = min(max_results, 25)  # API acepta hasta 25 por página (default)

        # Construir query de Scopus
        scopus_query = f"TITLE-ABS-KEY({query})"

        while len(results) < max_results:
            # Parámetros de búsqueda
            params = {
                'query': scopus_query,
                'start': start,
                'count': count,
                'view': 'STANDARD'
            }

            url = f"{self.ELSEVIER_BASE_URL}{self.SEARCH_ENDPOINT}"
            logger.debug(f"GET {url} (start={start}, count={count})")

            response = self.session.get(url, params=params, timeout=30)

            # Verificar respuesta
            if response.status_code == 429:
                logger.error("Cuota de API agotada (429 Too Many Requests)")
                raise Exception("API quota exceeded")

            if response.status_code == 401:
                logger.error("API key inválida o expirada (401 Unauthorized)")
                raise Exception("Invalid API key")

            response.raise_for_status()

            data = response.json()

            # Extraer resultados
            search_results = data.get('search-results', {})
            entries = search_results.get('entry', [])
            total_results = int(search_results.get('opensearch:totalResults', 0))

            logger.debug(f"Página {start // count + 1}: {len(entries)} resultados (total: {total_results})")

            if not entries:
                break

            # Obtener abstracts para estos resultados
            scopus_ids = []
            for entry in entries:
                identifier = entry.get('dc:identifier', '')
                if identifier.startswith('SCOPUS_ID:'):
                    scopus_ids.append(identifier.replace('SCOPUS_ID:', ''))

            abstracts_map = self._fetch_abstracts_batch(scopus_ids)

            # Normalizar resultados
            for entry in entries:
                if len(results) >= max_results:
                    break

                identifier = entry.get('dc:identifier', '')
                scopus_id = identifier.replace('SCOPUS_ID:', '') if identifier.startswith('SCOPUS_ID:') else ''
                abstract = abstracts_map.get(scopus_id)

                result = self._normalize_api_result(entry, abstract)
                results.append(result)

            # Si no hay más resultados
            if len(entries) < count or len(results) >= total_results:
                break

            start += count

            # Rate limit entre páginas
            time.sleep(0.5)

        return results

    def _fetch_abstracts_batch(
        self,
        scopus_ids: List[str]
    ) -> Dict[str, str]:
        """
        Obtiene abstracts para múltiples documentos.

        Nota: Cada abstract requiere una llamada individual al API.
        Para no agotar la cuota, limitamos a los primeros N.

        Args:
            scopus_ids: Lista de Scopus IDs

        Returns:
            Dict mapeando scopus_id -> abstract
        """
        abstracts_map = {}

        # Limitar para no agotar cuota
        max_abstracts = min(len(scopus_ids), 10)

        for scopus_id in scopus_ids[:max_abstracts]:
            try:
                abstract = self._fetch_single_abstract(scopus_id)
                if abstract:
                    abstracts_map[scopus_id] = abstract

                # Rate limit entre abstracts
                time.sleep(0.2)

            except Exception as e:
                logger.debug(f"No se pudo obtener abstract para {scopus_id}: {e}")
                continue

        logger.debug(f"Obtenidos {len(abstracts_map)} abstracts")
        return abstracts_map

    def _fetch_single_abstract(self, scopus_id: str) -> Optional[str]:
        """
        Obtiene abstract de un documento individual.

        Args:
            scopus_id: Scopus ID del documento

        Returns:
            Texto del abstract o None
        """
        url = f"{self.ELSEVIER_BASE_URL}{self.ABSTRACT_ENDPOINT}/{scopus_id}"

        try:
            response = self.session.get(url, timeout=15)

            if not response.ok:
                return None

            data = response.json()

            # Navegar estructura del response
            abstract_response = data.get('abstracts-retrieval-response', {})
            coredata = abstract_response.get('coredata', {})

            # El abstract puede estar en dc:description
            abstract = coredata.get('dc:description', '')

            if abstract:
                # Limpiar caracteres especiales
                abstract = abstract.strip()
                return abstract

        except Exception as e:
            logger.debug(f"Error obteniendo abstract {scopus_id}: {e}")

        return None

    def _normalize_api_result(
        self,
        entry: Dict,
        abstract: str = None
    ) -> Dict[str, Any]:
        """
        Normaliza resultado del API oficial de Elsevier.

        Args:
            entry: Entrada del response de búsqueda
            abstract: Abstract obtenido

        Returns:
            Dict normalizado
        """
        # Título
        title = entry.get('dc:title', 'N/A')

        # DOI
        doi = entry.get('prism:doi')

        # Año
        year = None
        cover_date = entry.get('prism:coverDate', '')
        if cover_date:
            year_match = re.search(r'\d{4}', cover_date)
            if year_match:
                year = int(year_match.group())

        # Autores - API solo devuelve primer autor en dc:creator
        authors = []
        creator = entry.get('dc:creator')
        if creator:
            authors.append(creator)

        # Link - construir desde Scopus ID o usar EID
        link = None
        eid = entry.get('eid', '')
        identifier = entry.get('dc:identifier', '')

        if eid:
            link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"
        elif identifier:
            scopus_id = identifier.replace('SCOPUS_ID:', '')
            link = f"https://www.scopus.com/record/display.uri?origin=inward&partnerID=HzOxMe3b&scp={scopus_id}"

        # Link alternativo del entry
        entry_links = entry.get('link', [])
        for entry_link in entry_links:
            if entry_link.get('@ref') == 'scopus':
                link = entry_link.get('@href', link)
                break

        return {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract,
            # Campos adicionales del API
            'cited_by': entry.get('citedby-count'),
            'publication_name': entry.get('prism:publicationName'),
            'eid': eid
        }

    def _search_via_playwright(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback usando Playwright y APIs internas de Scopus.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        from .scopus_playwright_connector import ScopusPlaywrightConnector

        connector = ScopusPlaywrightConnector(
            username=self.username,
            password=self.password,
            headless=self.headless
        )

        try:
            return list(connector.search(query, max_results))
        finally:
            connector.close()

    def close(self):
        """Cierra recursos."""
        self.session.close()
        logger.info("ScopusConnector cerrado")
