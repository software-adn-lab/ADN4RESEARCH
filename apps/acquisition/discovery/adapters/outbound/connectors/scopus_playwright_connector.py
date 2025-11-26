"""
Scopus Playwright Connector - Scraping basado en APIs internas de Scopus.

Este conector se usa como FALLBACK cuando el API oficial de Elsevier no está disponible.
Usa Playwright para autenticar vía EZproxy y luego llama APIs JSON internas de Scopus.

APIs USADAS:
- POST /api/documents/search/facets -> Resultados (title, doi, authors, year, eid)
- POST /gateway/documents/abstracts/retrieve -> Abstracts

ANTI-DETECCIÓN:
- Stealth mode para evadir detección de automatización
- Headers realistas y configuración de navegador completa
- Delays humanos entre acciones

NOTA: Las APIs de Scopus solo funcionan dentro del contexto de Playwright,
no se pueden llamar con requests directamente (dan 403 Forbidden).
"""
import logging
import time
import json
import re
import random
from typing import Dict, List, Any, Generator, Tuple
from urllib.parse import urlparse
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)


class ScopusPlaywrightConnector:
    """
    Conector para Scopus usando APIs JSON internas (vía Playwright).

    Se usa como fallback cuando el API oficial de Elsevier no está disponible.

    Flujo:
    1. Abrir navegador con Playwright
    2. Autenticar vía EZproxy
    3. Usar page.request.post() para llamar APIs JSON internas
    4. Normalizar y retornar
    """

    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com/"
    DEFAULT_PROXY_BASE = "https://bvirtual.epn.edu.ec:2057"
    SEARCH_PATH = "/api/documents/search/facets"
    ABSTRACTS_PATH = "/gateway/documents/abstracts/retrieve"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        preloaded_cookies: str = None
    ):
        """
        Args:
            username: Usuario EPN
            password: Contraseña EPN
            headless: Navegador sin interfaz. Default False para evitar detección de bot.
                     Si reCAPTCHA aparece, el usuario puede resolverlo manualmente.
            preloaded_cookies: Cookies JSON exportadas (opcional, para bypass total)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.preloaded_cookies = preloaded_cookies

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Busca en Scopus usando APIs JSON internas.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Yields:
            Dict normalizado con title, link, doi, source, year, authors, abstract
        """
        logger.info(f"[Playwright] Buscando en Scopus: '{query}' (max: {max_results})")

        with sync_playwright() as p:
            # Configuración anti-detección mejorada
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )

            # Context con configuración realista
            context = self._create_stealth_context(browser)

            # Si hay cookies preloaded, cargarlas antes de abrir página
            if self.preloaded_cookies:
                try:
                    cookies = json.loads(self.preloaded_cookies)
                    context.add_cookies(cookies)
                    logger.info("✓ Cookies preloaded cargadas")
                except Exception as e:
                    logger.warning(f"No se pudieron cargar cookies preloaded: {e}")

            page = context.new_page()

            self._apply_stealth_scripts(page)

            try:
                self._authenticate(page)
                results = list(self._search_and_extract(page, query, max_results))

                for result in results:
                    yield result

            finally:
                browser.close()

        logger.info("[Playwright] Búsqueda completada")

    def _authenticate(self, page: Page) -> None:
        """
        Autentica en Scopus vía EZproxy con comportamiento humano.

        Args:
            page: Página de Playwright
        """
        logger.info("Navegando a EZProxy...")
        page.goto(self.SCOPUS_VIA_EZPROXY, wait_until="domcontentloaded", timeout=60000)
        self._human_delay(1.0, 2.0)

        current_url = page.url

        # Si ya estamos en Scopus, no necesitamos autenticar
        if "scopus.com" in current_url or ("bvirtual.epn.edu.ec" in current_url and "/login" not in current_url):
            logger.info("✓ Ya autenticado (cookies o acceso directo)")
            # Asegurar que la cookie scopus-proxy esté configurada
            parsed = urlparse(current_url)
            if parsed.hostname and parsed.hostname.endswith("bvirtual.epn.edu.ec"):
                base = f"{parsed.scheme}://{parsed.netloc}"
                self._set_scopus_proxy_cookie(page, base)
            return

        # Buscar formulario de login
        logger.info("Detectado formulario de login...")

        username_selectors = [
            'input[name="user"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[id="username"]',
            'input[placeholder*="usuario" i]',
            'input[placeholder*="email" i]'
        ]

        username_field = None
        for selector in username_selectors:
            try:
                username_field = page.wait_for_selector(selector, timeout=3000, state="visible")
                if username_field:
                    logger.debug(f"Campo de usuario encontrado: {selector}")
                    break
            except:
                continue

        if not username_field:
            page.screenshot(path="debug_login_page.png")
            logger.error("Screenshot guardado en debug_login_page.png")
            raise Exception("No se encontró campo de usuario. Verifica debug_login_page.png")

        username_field.click()
        self._human_delay(0.3, 0.6)

        username_field.type(self.username, delay=random.randint(50, 150))
        self._human_delay(0.5, 1.0)

        password_field = page.query_selector('input[type="password"]')
        if not password_field:
            page.screenshot(path="debug_login_page.png")
            logger.error("Screenshot guardado en debug_login_page.png")
            raise Exception("No se encontró campo de contraseña. Verifica debug_login_page.png")

        password_field.click()
        self._human_delay(0.3, 0.6)
        password_field.type(self.password, delay=random.randint(50, 150))
        self._human_delay(0.8, 1.5)

        # Esperar reCAPTCHA si existe (máximo 5 segundos)
        try:
            logger.info("Verificando si hay reCAPTCHA...")
            page.wait_for_selector('iframe[src*="recaptcha"]', timeout=5000)
            logger.warning("⚠️ reCAPTCHA detectado. Esperando resolución manual...")
            logger.warning("   Si estás en headless=True, cambia a headless=False")
            logger.warning("   El navegador se pausará por 30 segundos para resolución manual")

            # En modo no-headless, el usuario puede resolver manualmente
            if not self.headless:
                time.sleep(30)  # Dar tiempo para resolución manual
            else:
                # En headless, intentar continuar de todos modos
                logger.warning("   Modo headless detectado, intentando continuar...")
                time.sleep(5)
        except:
            logger.debug("No se detectó reCAPTCHA visible")

        # Submit
        logger.info("Enviando credenciales...")
        password_field.press('Enter')

        # Esperar redirección con timeout largo (puede tomar tiempo con reCAPTCHA)
        logger.info("Esperando redirección...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=90000)
            self._human_delay(2.0, 3.0)
        except Exception as e:
            logger.warning(f"Timeout esperando redirección: {e}")

        current_url = page.url

        # Verificar si seguimos en login
        if "login" in current_url.lower():
            page.screenshot(path="debug_login_failed.png")
            logger.error("Screenshot del error guardado en debug_login_failed.png")

            # Verificar si hay mensaje de error
            error_msg = "desconocido"
            try:
                error_elem = page.query_selector('.error, .alert, [class*="error" i], [class*="alert" i]')
                if error_elem:
                    error_msg = error_elem.inner_text()
            except:
                pass

            raise Exception(
                f"Autenticación fallida. Posibles causas:\n"
                f"  1. Credenciales incorrectas\n"
                f"  2. reCAPTCHA bloqueando (usa headless=False)\n"
                f"  3. Error de servidor EZProxy\n"
                f"  Mensaje de error: {error_msg}\n"
                f"  Verifica debug_login_failed.png"
            )

        # Configurar cookie scopus-proxy
        parsed = urlparse(current_url)
        if parsed.hostname and parsed.hostname.endswith("bvirtual.epn.edu.ec"):
            base = f"{parsed.scheme}://{parsed.netloc}"
            self._set_scopus_proxy_cookie(page, base)

        logger.info("✓ Autenticación exitosa")

    def _set_scopus_proxy_cookie(self, page: Page, base: str) -> None:
        """
        Marca la cookie scopus-proxy=true (vista en tráfico real) para habilitar las APIs JSON.
        """
        try:
            page.request.post(
                f"{base}/cookies/set.uri",
                data=urlencode(
                    {
                        "name": "scopus-proxy",
                        "value": "true",
                        "expiration": "86400000",  # 1 día en ms (mismo que tráfico capturado)
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
            logger.debug("✓ Cookie scopus-proxy configurada")
        except Exception as e:
            logger.debug(f"No se pudo setear scopus-proxy: {e}")

    def _resolve_api_urls(self, page: Page) -> Tuple[str, str]:
        """
        Construye las URLs de API usando el host actual (incluye puerto de EZproxy).

        Args:
            page: Página autenticada

        Returns:
            (search_api_url, abstracts_api_url)
        """
        parsed = urlparse(page.url)
        base = self.DEFAULT_PROXY_BASE

        if parsed.scheme and parsed.netloc:
            hostname = parsed.hostname or ""

            if hostname.endswith("bvirtual.epn.edu.ec"):
                # Preferir el puerto proxy (2057) si no viene en la URL
                base = self.DEFAULT_PROXY_BASE if parsed.port is None else f"{parsed.scheme}://{parsed.netloc}"
            elif "scopus.com" in hostname:
                # La sesión sigue autenticada vía EZproxy, pero las APIs responden en el host proxy
                base = self.DEFAULT_PROXY_BASE
            else:
                base = f"{parsed.scheme}://{parsed.netloc}"

        search_api = f"{base}{self.SEARCH_PATH}"
        abstracts_api = f"{base}{self.ABSTRACTS_PATH}"

        return search_api, abstracts_api

    def _search_and_extract(
        self,
        page: Page,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta búsqueda usando API /api/documents/search.

        Args:
            page: Página autenticada de Playwright
            query: Término de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        try:
            # Construir query de Scopus
            scopus_query = query if "TITLE-ABS-KEY" in query else f"TITLE-ABS-KEY({query})"

            search_api, abstracts_api = self._resolve_api_urls(page)

            # Payload para la búsqueda
            search_payload = {
                "query": scopus_query,
                "documentClassificationEnum": "primary",
                "facetMaxCount": 7,
                "includeFacets": [
                    "pubyr", "subjabbr", "subtype", "lang",
                    "exactkeywords", "affilctry", "srctype",
                    "exactsrctitle", "prefnameauid", "pubstage",
                    "afid", "fundsponsor", "freetoread"
                ],
                "itemcount": max_results,
                "offset": 0
            }

            logger.debug(f"POST {search_api}")

            response = page.request.post(
                search_api,
                data=json.dumps(search_payload),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Source": "scopus-frontend"  # Header visto en tráfico real
                }
            )

            # Verificar respuesta
            headers = response.headers if isinstance(response.headers, dict) else response.headers()
            content_type = (headers.get("content-type") or "").lower()
            status_code = response.status if hasattr(response, "status") else None

            if not response.ok or "json" not in content_type:
                logger.error(f"Scopus API interna: Error {status_code}")
                try:
                    response_text = response.text()
                    with open("debug_scopus_playwright_error.html", "w", encoding="utf-8") as f:
                        f.write(response_text)
                    logger.info("Error guardado en debug_scopus_playwright_error.html")
                except Exception as e:
                    logger.error(f"No se pudo guardar debug: {e}")
                raise Exception(f"Search API error: {status_code}")

            data = response.json()

            # Extraer items
            items = (
                data.get('items')
                or data.get('documents')
                or data.get('results', {}).get('documents')
                or []
            )
            metadata = data.get('metadata') or data.get('results', {}).get('metadata') or {}
            total_count = metadata.get('totalCount', 0) or len(items)

            logger.info(f"✓ Obtenidos {len(items)} resultados (total: {total_count:,})")

            if not items:
                return []

            # Limitar a max_results
            items = items[:max_results]

            # Obtener abstracts
            abstracts_map = self._fetch_abstracts(
                page,
                [item.get('eid') for item in items],
                scopus_query,
                abstracts_api
            )

            # Normalizar resultados
            results = []
            for item in items:
                eid = item.get('eid')
                abstract = abstracts_map.get(eid)
                result = self._normalize_result(item, abstract)
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error en API search: {e}")
            raise

    def _fetch_abstracts(
        self,
        page: Page,
        eids: List[str],
        query: str,
        abstracts_api: str
    ) -> Dict[str, str]:
        """
        Obtiene abstracts usando API /gateway/documents/abstracts/retrieve.

        Args:
            page: Página autenticada de Playwright
            eids: Lista de EIDs
            query: Query original

        Returns:
            Dict mapeando eid -> abstract_text
        """
        try:
            abstracts_payload = {
                "eids": eids,
                "query": query,
                "documentClassification": "primary",
                "resultSet": {
                    "itemCount": len(eids),
                    "offset": 0
                },
                "enableHighlight": True
            }

            logger.debug(f"Fetching abstracts for {len(eids)} documents...")

            response = page.request.post(
                abstracts_api,
                data=json.dumps(abstracts_payload),
                headers={"Content-Type": "application/json"}
            )

            if not response.ok:
                logger.warning(f"Abstracts API error: {response.status}")
                return {}

            data = response.json()

            # Parsear abstracts
            abstracts = data.get('abstracts', [])
            abstracts_map = {}

            for abstract_item in abstracts:
                eid = abstract_item.get('eid')
                abstract_html = abstract_item.get('abstractHtml', '')

                if isinstance(abstract_html, list):
                    abstract_html = ' '.join(abstract_html)

                # Limpiar HTML tags
                abstract_text = re.sub(r'<[^>]+>', '', abstract_html)
                abstract_text = abstract_text.strip()

                if abstract_text:
                    abstracts_map[eid] = abstract_text

            logger.debug(f"✓ Obtenidos {len(abstracts_map)} abstracts")

            return abstracts_map

        except Exception as e:
            logger.warning(f"Error obteniendo abstracts: {e}")
            return {}

    def _normalize_result(
        self,
        item: Dict,
        abstract: str = None
    ) -> Dict[str, Any]:
        """
        Normaliza resultado de la API interna.

        Args:
            item: Item del response
            abstract: Abstract obtenido

        Returns:
            Dict normalizado
        """
        # Título
        title = item.get('title', 'N/A')

        # DOI
        doi = item.get('doi')

        # Año
        year = item.get('pubYear')
        if year:
            try:
                year = int(year)
            except:
                year = None

        # Autores
        authors_data = item.get('authors', [])
        authors = []
        for author in authors_data:
            preferred_name = author.get('preferredName', {})
            full_name = preferred_name.get('full', '').strip()
            if full_name:
                authors.append(full_name)

        # Link
        link = None
        links = item.get('links', [])
        for link_item in links:
            if link_item.get('label') == 'View at Publisher':
                link = link_item.get('href')
                break

        # Si no hay link, construir desde EID
        if not link:
            eid = item.get('eid', '')
            if eid:
                link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"

        # Extraer información de Open Access
        # Las APIs internas de Scopus también incluyen OA flags
        is_open_access = None
        openaccess_flag = item.get('openaccessFlag') or item.get('openAccessFlag')
        openaccess_str = item.get('openaccess') or item.get('openAccess')

        if isinstance(openaccess_flag, bool):
            is_open_access = openaccess_flag
        elif isinstance(openaccess_str, str):
            normalized = openaccess_str.lower()
            if normalized in ('1', 'true', 'yes'):
                is_open_access = True
            elif normalized in ('0', 'false', 'no'):
                is_open_access = False
        elif openaccess_str in (1, True):
            is_open_access = True
        elif openaccess_str in (0, False):
            is_open_access = False

        # PDF URL: Si es OA y tiene DOI, usar URL del DOI
        pdf_url = None
        if is_open_access and doi:
            pdf_url = f"https://doi.org/{doi}"

        return {
            'title': title,
            'link': link,
            'doi': doi,
            'source': 'Scopus',
            'year': year,
            'authors': authors,
            'abstract': abstract,
            # Open Access (Feature 4 integration)
            'is_open_access': is_open_access,
            'pdf_url': pdf_url
        }

    def _create_stealth_context(self, browser) -> BrowserContext:
        """
        Crea un contexto de navegador con configuración anti-detección.

        Args:
            browser: Instancia de navegador Playwright

        Returns:
            BrowserContext configurado con propiedades realistas
        """
        # User agents realistas (Windows 10 + Chrome reciente)
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(user_agents),
            locale='es-EC',
            timezone_id='America/Guayaquil',
            permissions=['geolocation'],
            geolocation={'latitude': -0.1807, 'longitude': -78.4678},  # Quito, Ecuador
            color_scheme='light',
            extra_http_headers={
                'Accept-Language': 'es-EC,es;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        )

        return context

    def _apply_stealth_scripts(self, page: Page) -> None:
        """
        Inyecta scripts JavaScript para ocultar propiedades de automatización.

        Args:
            page: Página de Playwright
        """
        # Script para sobrescribir navigator.webdriver
        stealth_js = """
        () => {
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Sobrescribir plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Sobrescribir languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-EC', 'es', 'en-US', 'en']
            });

            // Chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Agregar propiedades de navegador real
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.'
            });
        }
        """

        try:
            page.add_init_script(stealth_js)
            logger.debug("✓ Scripts anti-detección aplicados")
        except Exception as e:
            logger.warning(f"No se pudieron aplicar scripts stealth: {e}")

    def _human_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
        """
        Delay aleatorio para simular comportamiento humano.

        Args:
            min_seconds: Mínimo de segundos a esperar
            max_seconds: Máximo de segundos a esperar
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def close(self):
        """Cierra recursos."""
        logger.info("ScopusPlaywrightConnector cerrado")
