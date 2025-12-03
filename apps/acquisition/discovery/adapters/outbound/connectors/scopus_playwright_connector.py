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
    Conector para Scopus usando Playwright y APIs JSON internas.

    Se utiliza como fallback cuando la API oficial de Elsevier no está disponible.
    Flujo general:
      1. Abrir navegador con Playwright
      2. Autenticar vía EZproxy EPN
      3. Consumir APIs JSON internas con page.request.post()
      4. Normalizar y retornar resultados
    """

    SCOPUS_VIA_EZPROXY = "https://bvirtual.epn.edu.ec/login?url=http://www.scopus.com/"
    DEFAULT_PROXY_BASE = "https://bvirtual.epn.edu.ec:2057"
    SEARCH_PATH = "/api/documents/search"  # API real sin /facets
    ABSTRACTS_PATH = "/gateway/documents/abstracts/retrieve"

    # Cache de cookies a nivel de clase para reutilizar entre instancias
    _cookies_cache = None
    _cookies_cache_timestamp = None
    _cookies_cache_ttl = 3600  # 1 hora

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        preloaded_cookies: str = None,
        enable_dom_fallback: bool = True,
        use_cookies_cache: bool = True
    ):
        """
        Args:
            username: Usuario EPN
            password: Contraseña EPN
            headless: Si False, muestra el navegador (útil para depuración)
            preloaded_cookies: Cookies JSON exportadas (opcional)
            enable_dom_fallback: Si True, usa DOM scraping cuando las APIs fallan
            use_cookies_cache: Si True, reutiliza cookies entre instancias (recomendado para tests)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.preloaded_cookies = preloaded_cookies
        self.enable_dom_fallback = enable_dom_fallback
        self.use_cookies_cache = use_cookies_cache

    def search(
        self,
        query: str,
        max_results: int = 25
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Busca en Scopus usando estrategia híbrida:
        1. Intenta APIs JSON internas
        2. Si fallan, usa DOM scraping

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Yields:
            Diccionario normalizado con title, link, doi, source, year, authors, abstract
        """
        logger.info(f"[Scopus Playwright] Búsqueda: '{query}' (max: {max_results})")

        with sync_playwright() as p:
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

            context = self._create_stealth_context(browser)

            # Intentar cargar cookies del cache primero
            cookies_loaded = False
            if self.use_cookies_cache and self._is_cache_valid():
                try:
                    context.add_cookies(self._cookies_cache)
                    logger.info("✓ Cookies cacheadas reutilizadas (evita re-autenticación)")
                    cookies_loaded = True
                except Exception as e:
                    logger.warning(f"No se pudieron cargar cookies del cache: {e}")
            
            # Si no hay cache, intentar preloaded cookies
            if not cookies_loaded and self.preloaded_cookies:
                try:
                    cookies = json.loads(self.preloaded_cookies)
                    context.add_cookies(cookies)
                    logger.info("Cookies preloaded cargadas")
                    cookies_loaded = True
                except Exception as e:
                    logger.warning(f"No se pudieron cargar cookies preloaded: {e}")

            page = context.new_page()
            self._apply_stealth_scripts(page)

            try:
                self._authenticate(page)
                
                # Guardar cookies en cache después de autenticación exitosa
                if self.use_cookies_cache:
                    self._save_cookies_to_cache(context)
                
                results = self._execute_search_with_fallback(page, query, max_results)

                for result in results:
                    yield result

            except Exception as e:
                logger.error(f"Error en búsqueda Scopus: {e}", exc_info=True)
                page.screenshot(path="debug_scopus_error.png")
                raise
            finally:
                browser.close()

        logger.info("[Scopus Playwright] Búsqueda completada")

    def _authenticate(self, page: Page) -> None:
        """
        Autentica en Scopus vía EZproxy EPN.

        Selectores específicos:
        - Usuario: input[name="user"]
        - Contraseña: input[name="pass"]
        - Botón: #submit_button
        """
        logger.info("Navegando a EZProxy EPN...")
        page.goto(self.SCOPUS_VIA_EZPROXY, wait_until="domcontentloaded", timeout=60000)
        self._human_delay(1.0, 2.0)

        current_url = page.url
        logger.info(f"URL inicial: {current_url}")

        if self._is_authenticated(page):
            logger.info("✓ Sesión ya autenticada (cookies válidas)")
            self._ensure_scopus_proxy_cookie(page)
            return

        # Si llegamos aquí y había cookies cacheadas, significa que expiraron
        if self.use_cookies_cache and self._cookies_cache:
            logger.warning("⚠️  Cookies cacheadas no funcionaron - re-autenticando...")
            self.clear_cookies_cache()

        logger.info("Detectado formulario de login EPN...")

        try:
            username_field = page.wait_for_selector(
                'input[name="user"]',
                timeout=5000,
                state="visible"
            )
            logger.debug("Campo usuario EPN encontrado")
        except Exception as e:
            page.screenshot(path="debug_no_login_form.png")
            logger.error(f"No se encontró formulario EPN: {e}")
            raise Exception("Formulario de login EPN no encontrado. Ver debug_no_login_form.png")

        username_field.click()
        self._human_delay(0.3, 0.6)
        username_field.fill("")
        username_field.type(self.username, delay=random.randint(50, 150))
        logger.debug(f"Usuario ingresado: {self.username[:3]}***")
        self._human_delay(0.5, 1.0)

        try:
            password_field = page.wait_for_selector(
                'input[name="pass"]',
                timeout=3000,
                state="visible"
            )
            logger.debug("Campo contraseña EPN encontrado")
        except Exception:
            password_field = page.query_selector('input[type="password"]')
            if not password_field:
                page.screenshot(path="debug_no_password.png")
                raise Exception("Campo contraseña no encontrado")

        password_field.click()
        self._human_delay(0.3, 0.6)
        password_field.fill("")
        password_field.type(self.password, delay=random.randint(50, 150))
        logger.debug("Contraseña ingresada")
        self._human_delay(0.8, 1.5)

        # Verificar si hay reCAPTCHA y si está visible
        try:
            logger.info("Verificando reCAPTCHA...")
            recaptcha_iframe = page.wait_for_selector('iframe[src*="recaptcha"]', timeout=2000)
            
            if recaptcha_iframe and recaptcha_iframe.is_visible():
                logger.warning("reCAPTCHA visible detectado")
                
                if not self.headless:
                    logger.warning("⏳ Por favor resuelve el reCAPTCHA manualmente...")
                    logger.warning("Esperando hasta 60 segundos...")
                    
                    # Esperar hasta que el botón submit esté habilitado o 60 segundos
                    for i in range(60):
                        try:
                            submit_btn = page.query_selector('#submit_button')
                            if submit_btn and not submit_btn.is_disabled():
                                logger.info("✓ reCAPTCHA resuelto")
                                break
                        except Exception:
                            pass
                        time.sleep(1)
                else:
                    logger.warning("Modo headless con reCAPTCHA - puede fallar")
                    time.sleep(2)
            else:
                logger.info("reCAPTCHA no visible o ya resuelto")
        except Exception:
            logger.info("No se detectó reCAPTCHA")

        logger.info("Enviando credenciales...")
        try:
            submit_btn = page.query_selector('#submit_button')
            if submit_btn:
                logger.info("Haciendo click en botón submit...")
                submit_btn.click()
                logger.info("Click realizado, esperando navegación...")
            else:
                logger.info("Botón no encontrado, usando Enter")
                password_field.press('Enter')
        except Exception as e:
            logger.warning(f"Error en submit: {e}")
            # La navegación puede haber comenzado de todos modos

        logger.info("Esperando redirección post-login...")
        try:
            # Esperar a que la URL cambie (salga de /login)
            # Según el flujo HTTP: /login -> /connect -> puerto 2057
            page.wait_for_url(
                lambda url: "/login" not in url or "2057" in url or "scopus.com" in url,
                timeout=60000
            )
            logger.info("Redirección detectada, esperando carga completa...")
            self._human_delay(3.0, 5.0)
        except Exception as e:
            logger.warning(f"Timeout esperando redirección: {e}")
            # Continuar de todos modos para verificar

        current_url = page.url
        logger.info(f"URL post-login: {current_url}")

        # Verificar si realmente falló el login
        # Solo es error si estamos en /login Y hay un formulario visible
        if "/login" in current_url.lower():
            # Verificar si hay formulario de login (indica fallo real)
            try:
                page.wait_for_selector('input[name="user"]', timeout=2000, state="visible")
                # Si llegamos aquí, el formulario está visible = login falló
                page.screenshot(path="debug_login_failed.png")
                
                error_msg = "desconocido"
                try:
                    error_elem = page.query_selector('.error, .alert, [id*="error"]')
                    if error_elem:
                        error_msg = error_elem.inner_text()[:200]
                except Exception:
                    pass

                logger.error(f"Autenticación falló. Error: {error_msg}")
                raise Exception(
                    "Autenticación EPN fallida.\n"
                    "Posibles causas:\n"
                    "  1. Credenciales incorrectas\n"
                    "  2. reCAPTCHA bloqueó (usar headless=False)\n"
                    "  3. Error de red o EZProxy caído\n"
                    f"  Error: {error_msg}\n"
                    "  Ver: debug_login_failed.png"
                )
            except Exception:
                # No hay formulario visible, probablemente está en proceso de redirección
                logger.info("URL contiene /login pero no hay formulario visible, continuando...")
                pass

        self._ensure_scopus_proxy_cookie(page)
        logger.info("Autenticación EPN exitosa")

    def _is_authenticated(self, page: Page) -> bool:
        """
        Verifica si ya existe una sesión autenticada en Scopus.

        Criterios:
        - URL contiene 'scopus.com' (directo, sin proxy)
        - URL de proxy sin '/login' (ya pasó la autenticación)
        - Existe formulario de login = NO autenticado
        """
        current_url = page.url

        # Si estamos en scopus.com directo (sin proxy), estamos autenticados
        if "scopus.com" in current_url and "bvirtual.epn.edu.ec" not in current_url:
            logger.debug("URL es scopus.com directo - autenticado")
            return True

        # Si la URL contiene /login, definitivamente NO estamos autenticados
        if "/login" in current_url:
            logger.debug("URL contiene /login - NO autenticado")
            return False

        # Si estamos en el proxy pero no en /login, verificar si hay formulario
        if "bvirtual.epn.edu.ec" in current_url:
            try:
                # Intentar encontrar el formulario de login
                page.wait_for_selector('input[name="user"]', timeout=2000, state="visible")
                logger.debug("Formulario de login visible - NO autenticado")
                return False
            except Exception:
                # No hay formulario de login, estamos autenticados
                logger.debug("Sin formulario de login en proxy - autenticado")
                return True

        # Por defecto, asumir que NO estamos autenticados
        logger.debug("Estado de autenticación desconocido - asumiendo NO autenticado")
        return False

    def _ensure_scopus_proxy_cookie(self, page: Page) -> None:
        """
        Configura la cookie scopus-proxy cuando estamos en dominio proxy.
        Esta cookie es necesaria para habilitar las APIs JSON internas.
        """
        current_url = page.url
        parsed = urlparse(current_url)

        if parsed.hostname and parsed.hostname.endswith("bvirtual.epn.edu.ec"):
            base = f"{parsed.scheme}://{parsed.netloc}"
            self._set_scopus_proxy_cookie(page, base)

    def _set_scopus_proxy_cookie(self, page: Page, base: str) -> None:
        """
        Marca la cookie scopus-proxy=true para habilitar las APIs JSON internas.
        """
        try:
            page.request.post(
                f"{base}/cookies/set.uri",
                data=urlencode(
                    {
                        "name": "scopus-proxy",
                        "value": "true",
                        "expiration": "86400000",
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
            logger.debug("Cookie scopus-proxy configurada")
        except Exception as e:
            logger.debug(f"No se pudo establecer scopus-proxy: {e}")

    def _resolve_api_urls(self, page: Page) -> Tuple[str, str]:
        """
        Construye las URLs de las APIs usando el host actual (incluye puerto de EZproxy).

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
                base = self.DEFAULT_PROXY_BASE if parsed.port is None else f"{parsed.scheme}://{parsed.netloc}"
            elif "scopus.com" in hostname:
                base = self.DEFAULT_PROXY_BASE
            else:
                base = f"{parsed.scheme}://{parsed.netloc}"

        search_api = f"{base}{self.SEARCH_PATH}"
        abstracts_api = f"{base}{self.ABSTRACTS_PATH}"

        return search_api, abstracts_api

    def _execute_search_with_fallback(
        self,
        page: Page,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la búsqueda utilizando primero APIs JSON internas y,
        en caso de fallo o ausencia de resultados, DOM scraping.

        Args:
            page: Página autenticada
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        results = []

        try:
            logger.info("Intentando APIs JSON internas...")
            results = self._search_and_extract(page, query, max_results)

            if results:
                logger.info(f"APIs JSON exitosas: {len(results)} resultados")
                return results
            else:
                logger.warning("APIs JSON sin resultados")
        except Exception as e:
            logger.warning(f"APIs JSON fallaron: {e}")

        if self.enable_dom_fallback:
            try:
                logger.info("Fallback a DOM scraping...")
                results = self._search_dom_scraping(page, query, max_results)

                if results:
                    logger.info(f"DOM scraping exitoso: {len(results)} resultados")
                    return results
                else:
                    logger.warning("DOM scraping sin resultados")
            except Exception as e:
                logger.error(f"DOM scraping también falló: {e}")
        else:
            logger.warning("DOM scraping deshabilitado")

        logger.error("No se obtuvieron resultados con ninguna estrategia")
        return []

    def _search_and_extract(
        self,
        page: Page,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Estrategia principal: búsqueda usando APIs JSON internas.

        Args:
            page: Página autenticada
            query: Término de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Lista de resultados normalizados
        """
        try:
            scopus_query = query if "TITLE-ABS-KEY" in query else f"TITLE-ABS-KEY({query})"

            search_api, abstracts_api = self._resolve_api_urls(page)

            # Payload simplificado basado en el flujo HTTP real
            search_payload = {
                "documentClassificationEnum": "primary",
                "query": scopus_query,
                "sort": "plf-f",  # Más recientes primero (plf-f) o más antiguos (plf-t)
                "itemcount": max_results,
                "offset": 0,
                "showAbstract": False  # Los abstracts se obtienen por separado
            }

            logger.debug(f"POST {search_api}")
            logger.debug(f"Payload: {json.dumps(search_payload, indent=2)}")

            response = page.request.post(
                search_api,
                data=json.dumps(search_payload),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Accept-Language": "es-ES,es;q=0.9"
                }
            )

            status_code = response.status if hasattr(response, "status") else None
            logger.debug(f"Response status: {status_code}")

            if not response.ok:
                logger.error(f"Scopus API interna: HTTP error {status_code}")
                try:
                    response_text = response.text()
                    with open("debug_scopus_playwright_error.html", "w", encoding="utf-8") as f:
                        f.write(response_text)
                    logger.info("Error guardado en debug_scopus_playwright_error.html")
                except Exception as e:
                    logger.error(f"No se pudo guardar debug: {e}")
                raise Exception(f"Search API HTTP error: {status_code}")

            # Intentar parsear como JSON
            try:
                data = response.json()
                logger.debug(f"JSON parseado exitosamente")
            except Exception as json_error:
                logger.error(f"Respuesta no es JSON válido: {json_error}")
                try:
                    response_text = response.text()
                    logger.debug(f"Response text (primeros 500 chars): {response_text[:500]}")
                    with open("debug_scopus_playwright_error.html", "w", encoding="utf-8") as f:
                        f.write(response_text)
                    logger.info("Respuesta guardada en debug_scopus_playwright_error.html")
                except Exception as e:
                    logger.error(f"No se pudo guardar debug: {e}")
                raise Exception(f"Search API response is not JSON: {json_error}")

            items = (
                data.get('items')
                or data.get('documents')
                or data.get('results', {}).get('documents')
                or []
            )
            metadata = data.get('metadata') or data.get('results', {}).get('metadata') or {}
            total_count = metadata.get('totalCount', 0) or len(items)

            logger.info(f"Obtenidos {len(items)} resultados (total: {total_count:,})")

            if not items:
                return []

            items = items[:max_results]

            abstracts_map = self._fetch_abstracts(
                page,
                [item.get('eid') for item in items],
                scopus_query,
                abstracts_api
            )

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
        Obtiene abstracts usando la API /gateway/documents/abstracts/retrieve.

        Args:
            page: Página autenticada
            eids: Lista de EIDs
            query: Query original

        Returns:
            Diccionario eid -> abstract_text
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

            logger.debug(f"Solicitando abstracts para {len(eids)} documentos...")

            response = page.request.post(
                abstracts_api,
                data=json.dumps(abstracts_payload),
                headers={"Content-Type": "application/json"}
            )

            if not response.ok:
                logger.warning(f"Abstracts API error: {response.status}")
                return {}

            data = response.json()
            abstracts = data.get('abstracts', [])
            abstracts_map: Dict[str, str] = {}

            for abstract_item in abstracts:
                eid = abstract_item.get('eid')
                abstract_html = abstract_item.get('abstractHtml', '')

                if isinstance(abstract_html, list):
                    abstract_html = ' '.join(abstract_html)

                abstract_text = re.sub(r'<[^>]+>', '', abstract_html).strip()

                if abstract_text:
                    abstracts_map[eid] = abstract_text

            logger.debug(f"Obtenidos {len(abstracts_map)} abstracts")
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
        Normaliza un item devuelto por la API interna.

        Args:
            item: Item del response
            abstract: Abstract asociado (opcional)

        Returns:
            Diccionario normalizado de resultados
        """
        title = item.get('title', 'N/A')
        doi = item.get('doi')

        year = item.get('pubYear')
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        authors_data = item.get('authors', [])
        authors: List[str] = []
        for author in authors_data:
            preferred_name = author.get('preferredName', {})
            full_name = preferred_name.get('full', '').strip()
            if full_name:
                authors.append(full_name)

        link = None
        links = item.get('links', [])
        for link_item in links:
            if link_item.get('label') == 'View at Publisher':
                link = link_item.get('href')
                break

        if not link:
            eid = item.get('eid', '')
            if eid:
                link = f"https://www.scopus.com/record/display.uri?eid={eid}&origin=resultslist"

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
            'pdf_url': pdf_url
        }

    def _search_dom_scraping(
        self,
        page: Page,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Estrategia de fallback: Intercepta las llamadas API que hace la UI de Scopus.
        
        En lugar de parsear el DOM (que cambia frecuentemente), interceptamos las 
        respuestas JSON de la API /api/documents/search que usa la interfaz React.

        Args:
            page: Página autenticada
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de resultados obtenidos desde las APIs interceptadas
        """
        results: List[Dict[str, Any]] = []
        api_response_data = None

        try:
            logger.info("Estrategia DOM: Interceptando llamadas API de la UI...")
            
            # Interceptor para capturar la respuesta de la API de búsqueda
            def handle_response(response):
                nonlocal api_response_data
                if "/api/documents/search" in response.url and response.status == 200:
                    try:
                        api_response_data = response.json()
                        logger.info(f"✓ API interceptada: {len(api_response_data.get('items', []))} items")
                    except Exception as e:
                        logger.debug(f"Error parseando respuesta interceptada: {e}")

            page.on("response", handle_response)

            # Navegar a la página de inicio de Scopus (vía proxy con puerto correcto)
            # Según el flujo HTTP, debe ser bvirtual.epn.edu.ec:2057
            base_url = self.DEFAULT_PROXY_BASE  # Ya incluye :2057
            
            home_url = f"{base_url}/pages/home?display=basic"
            logger.info(f"Navegando a: {home_url}")
            page.goto(home_url, wait_until="domcontentloaded", timeout=30000)
            self._human_delay(2.0, 3.0)

            # Manejar cookies/consentimiento si aparece
            try:
                cookie_buttons = [
                    'button:has-text("Accept")',
                    'button:has-text("Aceptar")',
                    '#onetrust-accept-btn-handler'
                ]
                for btn_selector in cookie_buttons:
                    try:
                        btn = page.wait_for_selector(btn_selector, timeout=2000)
                        if btn and btn.is_visible():
                            logger.info(f"Aceptando cookies: {btn_selector}")
                            btn.click()
                            self._human_delay()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # Buscar el input de búsqueda en la nueva UI de Scopus
            # Basado en el flujo HTTP, la página usa React y tiene un input de búsqueda
            search_input_selectors = [
                'input[name="searchterm1"]',
                'input[id*="search-input"]',
                'input[placeholder*="Enter keywords"]',
                'input[placeholder*="Search"]',
                'textarea[name="searchterm1"]',
                '#searchfield',
                'input[type="text"]'
            ]

            search_input = None
            for selector in search_input_selectors:
                try:
                    search_input = page.wait_for_selector(selector, timeout=3000, state="visible")
                    if search_input:
                        logger.info(f"✓ Input encontrado: {selector}")
                        break
                except Exception:
                    continue

            if not search_input:
                # Fallback: buscar cualquier input visible
                try:
                    all_inputs = page.locator('input[type="text"]:visible').all()
                    if all_inputs:
                        search_input = all_inputs[0]
                        logger.info("✓ Usando primer input visible")
                except Exception:
                    pass

            if not search_input:
                logger.error("No se encontró input de búsqueda")
                page.screenshot(path="debug_no_search_input.png")
                raise Exception("Input de búsqueda no encontrado. Ver debug_no_search_input.png")

            # Escribir la búsqueda
            logger.info(f"Escribiendo query: {query}")
            search_input.click()
            self._human_delay(0.3, 0.6)
            search_input.fill(query)
            self._human_delay(0.5, 1.0)
            
            # Buscar botón de búsqueda o presionar Enter
            search_button_selectors = [
                'button[type="submit"]',
                'button:has-text("Search")',
                'button:has-text("Buscar")',
                'button[id*="search"]',
                'button.search-button'
            ]
            
            button_clicked = False
            for btn_selector in search_button_selectors:
                try:
                    btn = page.wait_for_selector(btn_selector, timeout=2000, state="visible")
                    if btn:
                        logger.info(f"Haciendo click en botón: {btn_selector}")
                        btn.click()
                        button_clicked = True
                        break
                except Exception:
                    continue
            
            if not button_clicked:
                logger.info("Presionando Enter para buscar")
                search_input.press("Enter")

            # Esperar a que se complete la llamada API
            logger.info("Esperando respuesta de la API...")
            timeout = 30
            elapsed = 0
            while api_response_data is None and elapsed < timeout:
                time.sleep(0.5)
                elapsed += 0.5

            if api_response_data is None:
                logger.warning("No se interceptó respuesta API, intentando parsear DOM...")
                page.screenshot(path="debug_no_api_response.png")
                # Fallback a parseo DOM tradicional
                return self._fallback_parse_dom(page, max_results)

            # Procesar los datos interceptados
            items = (
                api_response_data.get('items')
                or api_response_data.get('documents')
                or api_response_data.get('results', {}).get('documents')
                or []
            )

            logger.info(f"Procesando {len(items)} items interceptados...")
            
            for item in items[:max_results]:
                try:
                    result = self._normalize_result(item, abstract=None)
                    results.append(result)
                except Exception as e:
                    logger.debug(f"Error normalizando item: {e}")
                    continue

            logger.info(f"DOM scraping (API interceptada): {len(results)} resultados")
            return results

        except Exception as e:
            logger.error(f"Error en DOM scraping: {e}")
            page.screenshot(path="debug_dom_scraping_error.png")
            raise
        finally:
            # Remover el listener
            try:
                page.remove_listener("response", handle_response)
            except Exception:
                pass

    def _fallback_parse_dom(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """
        Último recurso: parsear el DOM directamente cuando la interceptación falla.
        
        Args:
            page: Página con resultados cargados
            max_results: Máximo de resultados
            
        Returns:
            Lista de resultados parseados del HTML
        """
        results: List[Dict[str, Any]] = []
        
        try:
            logger.info("Parseando DOM como último recurso...")
            
            # Esperar a que aparezcan resultados
            page.wait_for_selector('article, .result-item, [data-testid*="result"]', timeout=10000)
            self._human_delay(1.0, 2.0)
            
            # Intentar múltiples selectores para los resultados
            result_selectors = [
                'article',
                '.result-item',
                '[data-testid*="result"]',
                'tr.searchArea',
                '.ResultItem'
            ]
            
            rows = []
            for selector in result_selectors:
                try:
                    rows = page.locator(selector).all()
                    if rows:
                        logger.info(f"✓ Encontrados {len(rows)} resultados con: {selector}")
                        break
                except Exception:
                    continue
            
            if not rows:
                logger.error("No se encontraron resultados en el DOM")
                return []
            
            count = 0
            for row in rows:
                if count >= max_results:
                    break
                
                try:
                    # Buscar título
                    title_selectors = ['h2 a', 'h3 a', 'h4 a', 'a.doc-link', 'a[href*="record"]']
                    title = None
                    link = None
                    
                    for title_sel in title_selectors:
                        try:
                            title_el = row.locator(title_sel).first
                            if title_el.is_visible():
                                title = title_el.inner_text().strip()
                                link = title_el.get_attribute('href') or ""
                                break
                        except Exception:
                            continue
                    
                    if not title:
                        continue
                    
                    if link and not link.startswith('http'):
                        link = f"https://www.scopus.com{link}"
                    
                    # Extraer año del texto
                    text_content = row.inner_text()
                    year = None
                    year_match = re.search(r'\b(19|20)\d{2}\b', text_content)
                    if year_match:
                        year = int(year_match.group(0))
                    
                    # Extraer autores
                    authors: List[str] = []
                    try:
                        authors_text = row.locator('.author, .authors-list, [class*="author"]').first.inner_text()
                        authors = [a.strip() for a in re.split(r'[,;]', authors_text) if a.strip()]
                    except Exception:
                        pass
                    
                    result = {
                        'title': title,
                        'link': link if link else "N/A",
                        'year': year,
                        'source': 'Scopus (DOM)',
                        'authors': authors,
                        'abstract': None,
                        'doi': None,
                        'is_open_access': None,
                        'pdf_url': None
                    }
                    
                    results.append(result)
                    count += 1
                    
                except Exception as e:
                    logger.debug(f"Error parseando fila: {e}")
                    continue
            
            logger.info(f"Parseados {len(results)} resultados del DOM")
            return results
            
        except Exception as e:
            logger.error(f"Error en fallback DOM: {e}")
            return []

    def _create_stealth_context(self, browser) -> BrowserContext:
        """
        Crea un contexto de navegador con configuración anti-detección básica.

        Args:
            browser: Instancia de navegador Playwright

        Returns:
            BrowserContext configurado
        """
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
            geolocation={'latitude': -0.1807, 'longitude': -78.4678},
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
        stealth_js = """
        () => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-EC', 'es', 'en-US', 'en']
            });

            window.chrome = {
                runtime: {}
            };

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

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
            logger.debug("Scripts anti-detección aplicados")
        except Exception as e:
            logger.warning(f"No se pudieron aplicar scripts stealth: {e}")

    def _human_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
        """
        Pausa aleatoria para simular interacciones humanas.

        Args:
            min_seconds: Mínimo de segundos a esperar
            max_seconds: Máximo de segundos a esperar
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def _is_cache_valid(self) -> bool:
        """
        Verifica si el cache de cookies es válido.
        
        Returns:
            True si el cache existe y no ha expirado, False en caso contrario
        """
        if not self._cookies_cache or not self._cookies_cache_timestamp:
            logger.debug("Cache vacío - no hay cookies guardadas")
            return False
        
        elapsed = time.time() - self._cookies_cache_timestamp
        remaining = self._cookies_cache_ttl - elapsed
        
        if elapsed < self._cookies_cache_ttl:
            logger.debug(f"Cache válido - expira en {int(remaining)} segundos")
            return True
        else:
            logger.info(f"⏰ Cache expirado (edad: {int(elapsed)}s, TTL: {self._cookies_cache_ttl}s)")
            # Limpiar cache expirado
            self.clear_cookies_cache()
            return False

    def _save_cookies_to_cache(self, context: BrowserContext) -> None:
        """Guarda las cookies del contexto en el cache de clase."""
        try:
            cookies = context.cookies()
            ScopusPlaywrightConnector._cookies_cache = cookies
            ScopusPlaywrightConnector._cookies_cache_timestamp = time.time()
            logger.debug(f"✓ Cookies guardadas en cache ({len(cookies)} cookies)")
        except Exception as e:
            logger.warning(f"No se pudieron guardar cookies en cache: {e}")

    @classmethod
    def clear_cookies_cache(cls):
        """Limpia el cache de cookies (útil para tests)."""
        cls._cookies_cache = None
        cls._cookies_cache_timestamp = None
        logger.info("🗑️  Cache de cookies limpiado")

    @classmethod
    def get_cache_info(cls) -> dict:
        """
        Obtiene información sobre el estado actual del cache.
        
        Returns:
            Diccionario con información del cache
        """
        if not cls._cookies_cache or not cls._cookies_cache_timestamp:
            return {
                'has_cache': False,
                'cookies_count': 0,
                'age_seconds': 0,
                'ttl_seconds': cls._cookies_cache_ttl,
                'remaining_seconds': 0,
                'is_valid': False
            }
        
        elapsed = time.time() - cls._cookies_cache_timestamp
        remaining = cls._cookies_cache_ttl - elapsed
        
        return {
            'has_cache': True,
            'cookies_count': len(cls._cookies_cache),
            'age_seconds': int(elapsed),
            'ttl_seconds': cls._cookies_cache_ttl,
            'remaining_seconds': int(remaining),
            'is_valid': remaining > 0
        }

    def close(self):
        """Cierra recursos del conector."""
        logger.info("ScopusPlaywrightConnector cerrado")
