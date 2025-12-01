import logging
import time
import random
import re
from typing import Dict, List, Any, Generator, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from apps.acquisition.shared.domain.services.metadata_matcher import MetadataMatcher

logger = logging.getLogger(__name__)


class ScopusConnector:
    """
    Conector para Scopus que utiliza la API oficial de Elsevier y un fallback
    basado en Playwright. Incluye:
    - Selección automática según disponibilidad de API (campus/VPN vs remoto)
    - Rate limiting configurable
    - Reintentos automáticos con backoff exponencial
    """

    ELSEVIER_BASE_URL = "https://api.elsevier.com"
    SEARCH_ENDPOINT = "/content/search/scopus"
    ABSTRACT_ENDPOINT = "/content/abstract/scopus_id"

    def __init__(
        self,
        username: str = None,
        password: str = None,
        api_key: str = None,
        headless: bool = True,
        rate_limit: float = 1.0,
        auto_detect_location: bool = True,
        prefer_api_when_available: bool = True
    ):
        self.username = username
        self.password = password
        self.api_key = api_key
        self.headless = headless
        self.rate_limit = rate_limit
        self.auto_detect_location = auto_detect_location
        self.prefer_api_when_available = prefer_api_when_available

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'ADN4Research/1.0'
        })

        self.matcher = MetadataMatcher()

        self._location_detected = False
        self._is_on_campus = None
        self._api_available = None

        if api_key:
            self.session.headers['X-ELS-APIKey'] = api_key

        if self.auto_detect_location and self.api_key:
            self._detect_campus_access()

    def _detect_campus_access(self) -> None:
        """Detecta si la API de Elsevier es accesible (campus/VPN)."""
        if self._location_detected:
            return

        try:
            test_url = f"{self.ELSEVIER_BASE_URL}{self.SEARCH_ENDPOINT}"
            response = self.session.get(
                test_url,
                params={'query': 'TITLE(test)', 'count': 1},
                timeout=5
            )

            if response.status_code in [200, 400, 401]:
                self._is_on_campus = True
                self._api_available = True
            else:
                self._is_on_campus = False
                self._api_available = False

        except (requests.Timeout, requests.ConnectionError):
            self._is_on_campus = False
            self._api_available = False

        except Exception:
            self._is_on_campus = False
            self._api_available = False

        self._location_detected = True

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Ejecuta una búsqueda Scopus utilizando API cuando es posible
        o Playwright como fallback.
        """

        if not self._location_detected and self.auto_detect_location:
            self._detect_campus_access()

        results = []
        strategy_used = None

        if self._is_on_campus and self.api_key:
            try:
                results = list(self._search_via_api(query, max_results))
                strategy_used = "api_campus"
            except Exception:
                results = []

        if not results:
            if self.api_key and not self._is_on_campus:
                try:
                    results = list(self._search_via_api(query, max_results))
                    strategy_used = "api_vpn"
                    if results:
                        self._is_on_campus = True
                        self._api_available = True
                except Exception:
                    results = []

            if not results:
                if self.username and self.password:
                    strategy_used = "playwright_remote"
                    results = list(self._search_via_playwright(query, max_results))
                else:
                    raise ValueError(
                        "No es posible acceder a Scopus: API no disponible y "
                        "no se proporcionaron credenciales de EZproxy."
                    )

        for result in results:
            yield result

        time.sleep(self.rate_limit + random.uniform(0.1, 0.5))

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
        """Realiza búsqueda mediante la API oficial de Elsevier."""
        results = []
        start = 0
        count = min(max_results, 25)

        if query.strip().startswith("TITLE-ABS-KEY"):
            scopus_query = query
        else:
            scopus_query = f"TITLE-ABS-KEY({query})"

        while len(results) < max_results:
            params = {
                'query': scopus_query,
                'start': start,
                'count': count,
                'view': 'COMPLETE'
            }

            url = f"{self.ELSEVIER_BASE_URL}{self.SEARCH_ENDPOINT}"
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 429:
                raise Exception("API quota exceeded")
            if response.status_code == 401:
                raise Exception("Invalid API key")

            response.raise_for_status()

            data = response.json()
            search_results = data.get('search-results', {})
            entries = search_results.get('entry', [])
            total_results = int(search_results.get('opensearch:totalResults', 0))

            if not entries:
                break

            entries_without_abstract = []
            for entry in entries:
                if not entry.get('dc:description'):
                    identifier = entry.get('dc:identifier', '')
                    if identifier.startswith('SCOPUS_ID:'):
                        sid = identifier.replace('SCOPUS_ID:', '')
                        entries_without_abstract.append((entry, sid))

            abstracts_map = {}
            if entries_without_abstract:
                scopus_ids = [sid for _, sid in entries_without_abstract]
                abstracts_map = self._fetch_abstracts_parallel(scopus_ids)

            for entry in entries:
                if len(results) >= max_results:
                    break

                identifier = entry.get('dc:identifier', '')
                sid = identifier.replace('SCOPUS_ID:', '') if identifier.startswith('SCOPUS_ID:') else ''
                abstract = entry.get('dc:description') or abstracts_map.get(sid)

                result = self._normalize_api_result(entry, abstract)
                results.append(result)

            if len(entries) < count or len(results) >= total_results:
                break

            start += count
            time.sleep(0.5)

        return results

    def _fetch_abstracts_parallel(
        self,
        scopus_ids: List[str]
    ) -> Dict[str, str]:
        """Obtiene abstracts en paralelo usando ThreadPoolExecutor."""
        abstracts_map = {}

        if not scopus_ids:
            return abstracts_map

        max_abstracts = min(len(scopus_ids), 10)
        ids_to_fetch = scopus_ids[:max_abstracts]

        with ThreadPoolExecutor(max_workers=min(5, len(ids_to_fetch))) as executor:
            future_to_id = {
                executor.submit(self._fetch_single_abstract, sid): sid
                for sid in ids_to_fetch
            }

            for future in as_completed(future_to_id):
                sid = future_to_id[future]
                try:
                    abstract = future.result()
                    if abstract:
                        abstracts_map[sid] = abstract
                except Exception:
                    pass

        return abstracts_map

    def _fetch_single_abstract(self, scopus_id: str) -> Optional[str]:
        """Obtiene el abstract de un documento individual."""
        url = f"{self.ELSEVIER_BASE_URL}{self.ABSTRACT_ENDPOINT}/{scopus_id}"

        try:
            response = self.session.get(url, timeout=15)
            if not response.ok:
                return None

            data = response.json()
            coredata = data.get('abstracts-retrieval-response', {}).get('coredata', {})
            abstract = coredata.get('dc:description', '')
            return abstract.strip() if abstract else None

        except Exception:
            return None

    def _normalize_api_result(
        self,
        entry: Dict,
        abstract: str = None
    ) -> Dict[str, Any]:
        """Normaliza un elemento devuelto por la API de Elsevier."""
        title = entry.get('dc:title', 'N/A')
        doi = entry.get('prism:doi')

        year = None
        cover_date = entry.get('prism:coverDate', '')
        if cover_date:
            match = re.search(r'\d{4}', cover_date)
            if match:
                year = int(match.group())

        authors = []
        creator = entry.get('dc:creator')
        if creator:
            authors.append(creator)

        link = None
        eid = entry.get('eid', '')
        identifier = entry.get('dc:identifier', '')

        if eid:
            link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"
        elif identifier:
            sid = identifier.replace('SCOPUS_ID:', '')
            link = f"https://www.scopus.com/record/display.uri?origin=inward&partnerID=HzOxMe3b&scp={sid}"

        for entry_link in entry.get('link', []):
            if entry_link.get('@ref') == 'scopus':
                link = entry_link.get('@href', link)
                break

        openaccess_flag = entry.get('openaccessFlag')
        openaccess_str = entry.get('openaccess')
        is_open_access = None

        if isinstance(openaccess_flag, bool):
            is_open_access = openaccess_flag
        elif isinstance(openaccess_str, str):
            is_open_access = openaccess_str == '1'
        elif openaccess_str in [0, 1]:
            is_open_access = bool(openaccess_str)

        pdf_url = f"https://doi.org/{doi}" if is_open_access and doi else None

        return {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract,
            'is_open_access': is_open_access,
            'pdf_url': pdf_url,
            'cited_by': entry.get('citedby-count'),
            'publication_name': entry.get('prism:publicationName'),
            'eid': eid
        }

    def _search_via_playwright(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Fallback de búsqueda usando Playwright + EZproxy."""
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

    def find_metadata(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca metadatos de un artículo por título utilizando la API de Scopus
        con validación mediante MetadataMatcher.
        """
        if not title or not title.strip() or not self.api_key:
            return None

        try:
            query = f'TITLE("{title.strip()}")'
            url = f"{self.ELSEVIER_BASE_URL}{self.SEARCH_ENDPOINT}"

            params = {'query': query, 'count': 5, 'view': 'COMPLETE'}
            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                entries = data.get('search-results', {}).get('entry', [])

                candidates = [
                    self._normalize_api_result(entry)
                    for entry in entries
                    if isinstance(entry, dict)
                ]

                if candidates:
                    result = self.matcher.find_best_match(
                        candidates=candidates,
                        search_title=title,
                        search_authors=authors,
                        search_year=year
                    )

                    if result.is_match:
                        match = result.candidate.copy()
                        match["match_score"] = result.score
                        return match

            return None

        except Exception:
            return None

    def force_location_redetection(self) -> None:
        """Fuerza una nueva detección de disponibilidad de API."""
        self._location_detected = False
        self._is_on_campus = None
        self._api_available = None
        self._detect_campus_access()

    def get_location_info(self) -> Dict[str, Any]:
        """Retorna el estado de ubicación y disponibilidad de estrategia."""
        if not self._location_detected:
            return {
                "location": "unknown",
                "api_available": None,
                "strategy": "not_detected",
                "detected": False
            }

        location = "campus" if self._is_on_campus else "remote"
        strategy = "api" if (self._is_on_campus and self.api_key) else "playwright"

        return {
            "location": location,
            "api_available": self._api_available,
            "strategy": strategy,
            "detected": True
        }

    def close(self):
        """Cierra la sesión HTTP."""
        self.session.close()
