"""
CrossrefConnector - Conector gratuito para Crossref API.

Crossref es una base de datos pública de DOIs con más de 140 millones
de registros académicos. Proporciona metadatos de alta calidad sin
necesidad de autenticación.

Características:
- Sin API key requerida
- Sin límites estrictos (~50 req/seg)
- Metadatos de calidad editorial
- Cobertura de IEEE, Elsevier, Springer, Wiley, etc.

Limitaciones:
- No siempre incluye abstract (depende del publisher)
- No proporciona full text (solo metadatos)

Documentación: https://github.com/CrossRef/rest-api-doc
"""

import logging
import requests
from typing import Optional, Dict, Any, Iterable, List
from apps.acquisition.discovery.domain.interfaces.i_academic_connector import IAcademicConnector
from apps.acquisition.shared.domain.services.metadata_matcher import MetadataMatcher


logger = logging.getLogger(__name__)


class CrossrefConnector(IAcademicConnector):
    """
    Conector para Crossref API (gratuito, sin autenticación).

    Ideal para:
    - Normalizar DOIs
    - Obtener autores formateados
    - Completar años de publicación
    - Limpiar metadatos de IEEE

    Uso:
        connector = CrossrefConnector(email="tu_email@institucion.edu")
        metadata = connector.find_metadata("Deep Learning for Software Testing")

        if metadata:
            print(metadata["doi"])
            print(metadata["authors"])
    """

    def __init__(self, email: str = "researcher@epn.edu.ec", timeout: int = 10):
        """
        Inicializa el conector Crossref.

        Args:
            email: Email de contacto (opcional pero recomendado para polite pool)
            timeout: Timeout en segundos para requests HTTP
        """
        self.base_url = "https://api.crossref.org/works"
        self.timeout = timeout
        self.matcher = MetadataMatcher()

        # Crossref recomienda incluir email en User-Agent para mejor servicio
        self.headers = {
            "User-Agent": f"ADN4Research/1.0 (mailto:{email})"
        }

        logger.info(f"CrossrefConnector inicializado con email={email}")

    def find_metadata(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca metadatos de un estudio específico por título.

        Usa validación multi-criterio para evitar falsos positivos.

        Args:
            title: Título del estudio a buscar
            authors: Lista opcional de autores para validación cruzada
            year: Año opcional de publicación para validación

        Returns:
            Diccionario con metadatos normalizados o None si no se encuentra
        """
        if not title or not title.strip():
            return None

        try:
            # Buscar en Crossref API
            params = {
                "query.bibliographic": title.strip(),
                "rows": 5,
                "select": "DOI,title,author,published-print,published-online,abstract,container-title"
            }

            logger.debug(f"Buscando en Crossref: {title}")
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])

                if items:
                    # Normalizar items de Crossref para el matcher
                    candidates = [self._normalize_item(item) for item in items]

                    # Usar MetadataMatcher para encontrar el mejor match
                    result = self.matcher.find_best_match(
                        candidates=candidates,
                        search_title=title,
                        search_authors=authors,
                        search_year=year
                    )

                    if result.is_match:
                        match = result.candidate.copy()
                        match["match_score"] = result.score
                        match["source"] = "Crossref"
                        return match

                logger.debug(f"No se encontró match válido en Crossref para: {title}")
                return None

            elif response.status_code == 404:
                logger.debug(f"No se encontró en Crossref: {title}")
                return None

            else:
                logger.warning(f"Crossref error {response.status_code}")
                return None

        except requests.Timeout:
            logger.warning(f"Timeout al consultar Crossref: {title}")
            return None

        except requests.RequestException as e:
            logger.error(f"Error de conexión con Crossref: {e}")
            return None

        except Exception as e:
            logger.error(f"Error inesperado en Crossref: {e}", exc_info=True)
            return None

    def search(self, query: str, max_results: int = 10) -> Iterable[dict]:
        """
        Búsqueda general en Crossref (para discovery).

        Args:
            query: Query de búsqueda
            max_results: Número máximo de resultados

        Yields:
            Diccionarios con metadatos normalizados
        """
        try:
            params = {
                "query": query,
                "rows": max_results,
                "select": "DOI,title,author,published-print,published-online,abstract,container-title"
            }

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])

                for item in items:
                    try:
                        yield self._normalize_item(item)
                    except Exception as e:
                        logger.warning(f"Error normalizando item de Crossref: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error en búsqueda Crossref: {e}")

    def _normalize_item(self, item: dict) -> dict:
        """
        Normaliza un item de Crossref a nuestro formato estándar.

        Args:
            item: Item raw de Crossref API

        Returns:
            Diccionario normalizado
        """
        return {
            "doi": item.get("DOI"),
            "title": self._extract_title(item),
            "authors": self._extract_authors(item),
            "year": self._extract_year(item),
            "journal": self._extract_journal(item),
            "abstract": self._extract_abstract(item),
            "source": "Crossref"
        }

    def _extract_title(self, item: dict) -> Optional[str]:
        """Extrae el título del item."""
        titles = item.get("title", [])
        return titles[0] if titles else None

    def _extract_authors(self, item: dict) -> Optional[List[str]]:
        """
        Extrae autores en formato "Apellido, Nombre".

        Crossref devuelve: [{"family": "Smith", "given": "John"}, ...]
        """
        authors_raw = item.get("author", [])
        if not authors_raw:
            return None

        authors = []
        for author in authors_raw:
            family = author.get("family", "")
            given = author.get("given", "")

            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)

        return authors if authors else None

    def _extract_year(self, item: dict) -> Optional[int]:
        """
        Extrae el año de publicación.

        Crossref puede tener published-print o published-online.
        """
        date_info = item.get("published-print") or item.get("published-online")

        if date_info:
            date_parts = date_info.get("date-parts")
            if date_parts and date_parts[0]:
                return date_parts[0][0]

        return None

    def _extract_journal(self, item: dict) -> Optional[str]:
        """Extrae el nombre del journal/conferencia."""
        container_titles = item.get("container-title", [])
        return container_titles[0] if container_titles else None

    def _extract_abstract(self, item: dict) -> Optional[str]:
        """
        Extrae el abstract si está disponible.

        Nota: Crossref no siempre incluye abstract.
        """
        abstract = item.get("abstract")

        if abstract and isinstance(abstract, str):
            # Limpiar posibles tags XML
            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "")
            abstract = abstract.strip()
            return abstract if abstract else None

        return None
