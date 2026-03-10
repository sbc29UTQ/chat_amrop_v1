"""
tools_navegacion.py – Herramientas Selenium del NavigationAgent.

Responsabilidad:
    Controlar un navegador Chrome real para ejecutar búsquedas en Google
    y extraer URLs de perfiles de LinkedIn de los resultados.

Estilo: programación funcional (solo funciones, sin clases propias).

Patrón de driver:
    El driver de Chrome se crea de forma "lazy" (al primer uso) mediante
    _ensure_driver(). Se almacena en _driver_state para reutilizarlo entre
    llamadas sin necesidad de abrir un nuevo navegador cada vez.

Herramientas de navegación (NavigationAgent):
    build_google_search_url   – construye la URL de búsqueda de Google
    go_to_url                 – navega a una URL
    extract_linkedin_profiles – extrae hrefs de los 3 primeros <a> del DOM con linkedin.com/in/

Herramientas de control del LoopAgent:
    get_next_query    – lee/actualiza el índice de iteración en el estado de sesión
    save_query_result – acumula resultados de cada iteración en el estado
    exit_loop         – señaliza al LoopAgent que debe detenerse (escalate=True)
"""

import random
import time
import urllib.parse
import warnings
from typing import List

import selenium
import selenium.webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from google.adk.tools.tool_context import ToolContext

# Suprimir avisos repetitivos de ChromeDriver durante la inicialización
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Estado compartido del driver (patrón funcional)
# ---------------------------------------------------------------------------
_driver_state: dict = {"instance": None}  # "instance" → selenium.webdriver.Chrome | None


def _build_options() -> Options:
    """
    Construye las opciones de Chrome para selenium.webdriver.

    Sin --headless: el navegador abre con ventana visible para monitoreo.
    user-data-dir persiste cookies y sesión entre ejecuciones.
    """
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-data-dir=/tmp/selenium")
    opts.add_argument("--lang=es-PE")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    return opts


def _ensure_driver() -> selenium.webdriver.Chrome:
    """Retorna el driver activo, creándolo si no existe aún (lazy init)."""
    if _driver_state["instance"] is None:
        driver = selenium.webdriver.Chrome(options=_build_options())
        _driver_state["instance"] = driver
    return _driver_state["instance"]


# ---------------------------------------------------------------------------
# Tool 1: build_google_search_url
# ---------------------------------------------------------------------------

def build_google_search_url(query: str) -> str:
    """
    Construye la URL de búsqueda de Google para una query dada.

    Codifica correctamente la query (espacios, comillas, tildes, ñ, etc.)
    usando urllib.parse — sin que el LLM tenga que hacer encoding manual.

    Args:
        query: Query de búsqueda tal como la retorna get_next_query.
               Ejemplo: 'site:pe.linkedin.com/in "Luis Santivañez"'

    Returns:
        URL completa lista para usar en go_to_url.
        Ejemplo: 'https://www.google.com/search?hl=es&q=site%3Ape.linkedin.com%2Fin+%22Luis+Santiva%C3%B1ez%22'
    """
    encoded = urllib.parse.urlencode({"hl": "es", "q": query})
    url = f"https://www.google.com/search?{encoded}"
    print(f"🔗 URL construida: {url}")
    return url


# ---------------------------------------------------------------------------
# Tool 2: go_to_url
# ---------------------------------------------------------------------------

def go_to_url(url: str) -> str:
    """
    Navega el navegador a la URL indicada.

    Agrega un delay aleatorio entre 2 y 4 segundos después de cargar la
    página para simular comportamiento humano.

    Args:
        url: URL completa a visitar.

    Returns:
        Confirmación de navegación como string.
    """
    print(f"🌐 Navegando a: {url}")
    driver = _ensure_driver()
    driver.get(url.strip())
    time.sleep(random.uniform(2.0, 4.0))
    return f"Navegado a URL: {url}"


# ---------------------------------------------------------------------------
# Tool 3: extract_linkedin_profiles
# ---------------------------------------------------------------------------

def extract_linkedin_profiles() -> dict:
    """
    Extrae URLs de perfiles de LinkedIn desde los primeros 3 elementos <a>
    del DOM de la página actual que coincidan con el filtro linkedin.com/in/.

    Consulta directamente las etiquetas <a> del DOM mediante Selenium y
    obtiene el atributo href de cada una, filtrando solo perfiles LinkedIn
    válidos (linkedin.com/in/). No requiere HTML como entrada — opera
    sobre la página que el driver tiene cargada en ese momento.

    Returns:
        dict con:
            linkedin_urls : list[str] – URLs de perfiles encontradas (máx. 3)
            total         : int       – cantidad de URLs
            status        : str       – "ok" | "error"
            message       : str       – descripción del resultado
    """
    BLACKLIST = ("/company/", "/jobs/", "/learning/", "/posts/", "/pulse/")
    MAX_RESULTS = 1
    print("🔗 Extrayendo perfiles de LinkedIn desde el DOM (<a href>)...")

    try:
        driver = _ensure_driver()
        urls: list[str] = []

        for tag in driver.find_elements(By.TAG_NAME, "a"):
            if len(urls) >= MAX_RESULTS:
                break
            href: str = tag.get_attribute("href") or ""
            if "linkedin.com/in/" in href:
                if not any(bad in href for bad in BLACKLIST):
                    clean = urllib.parse.unquote(href)
                    if clean not in urls:
                        urls.append(clean)

        return {
            "linkedin_urls": urls,
            "total":         len(urls),
            "status":        "ok",
            "message":       f"Se extrajeron {len(urls)} perfil(es) de LinkedIn.",
        }
    except Exception as exc:
        return {
            "linkedin_urls": [],
            "total":         0,
            "status":        "error",
            "message":       str(exc),
        }


# ---------------------------------------------------------------------------
# Tool: get_next_query  (control del LoopAgent)
# ---------------------------------------------------------------------------

def get_next_query(tool_context: ToolContext) -> dict:
    """
    Retorna la próxima query a procesar y avanza el índice interno.

    Lee `_nav_queries` (lista Python) y `_nav_index` del estado de sesión.
    Cuando se han procesado todas las queries, retorna done=True junto
    con todos los resultados acumulados en `_nav_results`.

    Args:
        tool_context: Contexto inyectado por ADK (acceso al estado de sesión).

    Returns:
        Si quedan queries:
            {"done": False, "query": str, "index": int, "total": int}
        Si ya no quedan:
            {"done": True, "query": None, "results": list, "total_processed": int}
    """
    state = tool_context.state

    queries: list[str] = state.get("_nav_queries", [])
    total: int = len(queries)
    index: int = int(state.get("_nav_index", 0))

    if index >= total:
        results = state.get("_nav_results", [])
        return {
            "done":            True,
            "query":           None,
            "results":         results,
            "total_processed": len(results),
        }

    state["_nav_index"] = index + 1
    return {
        "done":  False,
        "query": queries[index],
        "index": index + 1,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Tool: save_query_result  (acumulación entre iteraciones)
# ---------------------------------------------------------------------------

def save_query_result(query: str, urls: List[str], tool_context: ToolContext) -> str:
    """
    Guarda el resultado de una query procesada en el estado de sesión.

    Args:
        query:        La query de búsqueda procesada.
        urls:         Lista de URLs de LinkedIn encontradas.
        tool_context: Contexto inyectado por ADK.

    Returns:
        Confirmación con la cantidad de URLs guardadas.
    """
    results: list = tool_context.state.get("_nav_results", [])
    results.append({"query": query, "urls": urls})
    tool_context.state["_nav_results"] = results
    print(f"💾 Guardado: {len(urls)} URL(s) para '{query}'")
    return f"Resultado guardado: {len(urls)} URL(s) encontradas para '{query}'."


# ---------------------------------------------------------------------------
# Tool: exit_loop  (señal de salida del LoopAgent)
# ---------------------------------------------------------------------------

def exit_loop(tool_context: ToolContext) -> str:
    """
    Señaliza al LoopAgent que debe detener la iteración.

    Debe llamarse cuando get_next_query retorna done=True.

    Args:
        tool_context: Contexto inyectado por ADK.

    Returns:
        Mensaje de confirmación.
    """
    print("🏁 Loop de navegación finalizado.")
    tool_context.actions.escalate = True
    return "Todas las queries han sido procesadas. Loop finalizado."


# ---------------------------------------------------------------------------
# Tool: close_browser
# ---------------------------------------------------------------------------

def close_browser() -> str:
    """
    Cierra el navegador Chrome y libera el driver de Selenium.

    Debe llamarse una vez que el reporte final ha sido generado y el ciclo
    completo de navegación ha concluido. Después de esta llamada el driver
    queda en None; si se necesitara navegar de nuevo se crearía uno nuevo
    mediante _ensure_driver().

    Returns:
        Mensaje de confirmación o aviso si el navegador ya estaba cerrado.
    """
    driver = _driver_state.get("instance")
    if driver is None:
        return "El navegador ya estaba cerrado."
    try:
        driver.quit()
        print("🔒 Navegador cerrado correctamente.")
        return "Navegador cerrado correctamente."
    except Exception as exc:
        return f"Error al cerrar el navegador: {exc}"
    finally:
        _driver_state["instance"] = None