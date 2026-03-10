"""
agent.py – Sistema multi-agente lkn_scraper_agent.
Stack  : Python + Google ADK
Estilo : Programación funcional (sin clases propias)

Arquitectura:
    ROOT_AGENT (SequentialAgent) — orquesta el flujo completo
    ├── SearchAgent      → google_search           [built-in]
    ├── KeywordGenAgent  → generar_keywords         [custom]
    └── NavigationAgent (LoopAgent)
        └── NavigationSubAgent → build_google_search_url, go_to_url,
                                 extract_linkedin_profiles, close_browser,
                                 get_next_query, save_query_result,
                                 exit_loop              [custom Selenium]

Flujo de datos entre agentes:
    1. SearchAgent      → state["search_output"]   : texto con nombres (uno/línea)
    2. KeywordGenAgent  → state["_nav_queries"]    : lista Python de queries LinkedIn
                          (generar_keywords persiste la lista directo en estado;
                           evita re-parseo frágil de texto por el LLM)
    3. NavigationAgent  → itera sobre state["_nav_queries"] query por query
                          usando state["_nav_index"] como puntero de avance

"""

import os
from dotenv import load_dotenv

# Carga las variables del archivo .env antes de importar agentes
load_dotenv()

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools import google_search                          # Built-in tool de ADK

# Instrucciones de cada agente (prompts del sistema)
from lkn_scraper_agent.instructions import (
    SEARCH_AGENT_INSTRUCTION,
    KEYWORDGEN_INSTRUCTION,
    NAVIGATION_SUB_INSTRUCTION,
)

# Herramientas custom
from lkn_scraper_agent.tools_buscador import generar_keywords
from lkn_scraper_agent.tools_navegacion import (
    build_google_search_url,    # Construye la URL de búsqueda Google a partir de una query
    go_to_url,                  # Navega a una URL en el navegador
    extract_linkedin_profiles,  # Extrae hrefs de los 3 primeros <a> del DOM con linkedin.com/in/
    close_browser,              # Cierra Chrome y libera el driver al finalizar el ciclo
    get_next_query,             # Lee el índice actual y retorna la próxima query
    save_query_result,          # Acumula el resultado de una query en el estado
    exit_loop,                  # Señaliza al LoopAgent que debe detenerse
)

# ---------------------------------------------------------------------------
# Variables de entorno (.env)
#
# MODEL              : Modelo Gemini a usar (ej. gemini-2.5-flash)
# DISABLE_WEB_DRIVER : Si es "1", NavigationSubAgent opera sin herramientas
#                      Selenium (útil para depurar lógica de prompts)
# ---------------------------------------------------------------------------
MODEL: str = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.5-flash")
DISABLE_WEB_DRIVER: bool = os.environ.get("DISABLE_WEB_DRIVER", "0") == "1"

# ---------------------------------------------------------------------------
# SearchAgent
#
# Responsabilidad: Identificar nombres de personas reales asociadas al
#                  cargo o empresa que consulta el usuario.
# Herramienta   : google_search (built-in de ADK — no mezclar con custom)
# output_key    : "search_output" → texto con nombres, uno por línea
# ---------------------------------------------------------------------------
search_agent = LlmAgent(
    name="SearchAgent",
    model=MODEL,
    description="Busca en Google y extrae nombres de personas según la consulta.",
    instruction=SEARCH_AGENT_INSTRUCTION,
    tools=[google_search],
    output_key="search_output",
)

# ---------------------------------------------------------------------------
# KeywordGenAgent
#
# Responsabilidad: Convertir los nombres encontrados en queries optimizadas
#                  para buscar perfiles de LinkedIn en Google.
# Herramienta   : generar_keywords (custom function)
# Entrada       : Lee "search_output" del estado de sesión
# output_key    : "keyword_gen_output" → texto con queries, una por línea
# ---------------------------------------------------------------------------
keyword_gen_agent = LlmAgent(
    name="KeywordGenAgent",
    model=MODEL,
    description="Convierte nombres en queries LinkedIn optimizadas.",
    instruction=KEYWORDGEN_INSTRUCTION,
    tools=[generar_keywords],
    output_key="keyword_gen_output",
)

# ---------------------------------------------------------------------------
# NavigationSubAgent — LlmAgent (sub-agente interno del LoopAgent)
#
# Responsabilidad: Procesar UNA query por iteración del loop.
#   - Llama a get_next_query() para obtener la query actual.
#   - Navega a Google con Selenium y extrae URLs de LinkedIn.
#   - Guarda el resultado con save_query_result().
#   - Cuando done=True, genera el reporte final y llama a exit_loop().
#
# Herramientas:
#   - Selenium: build_google_search_url, go_to_url, extract_linkedin_profiles
#   - Control del loop: get_next_query, save_query_result, exit_loop
#
# output_key: "navigation_output" — el reporte final queda en esta clave
#             (solo tiene valor significativo en la última iteración)
#
# DISABLE_WEB_DRIVER=1 → tools Selenium vacías (modo debug sin navegador)
# ---------------------------------------------------------------------------
_nav_tools = [get_next_query, save_query_result, exit_loop] + (
    [] if DISABLE_WEB_DRIVER else [
        build_google_search_url,    # Construye URL de Google codificando la query
        go_to_url,                  # Abre una URL en Chrome
        extract_linkedin_profiles,  # Extrae hrefs de los 3 primeros <a> del DOM (linkedin.com/in/)
        close_browser,              # Cierra Chrome y libera el driver al finalizar
    ]
)

navigation_sub_agent = LlmAgent(
    name="NavigationSubAgent",
    model=MODEL,
    description="Procesa una query por iteración: navega con Selenium y extrae URLs LinkedIn.",
    instruction=NAVIGATION_SUB_INSTRUCTION,
    tools=_nav_tools,
    output_key="navigation_output",
)

# ---------------------------------------------------------------------------
# NavigationAgent — LoopAgent
#
# Responsabilidad: Iterar sobre cada query generada por KeywordGenAgent,
#                  delegando el procesamiento de cada una a NavigationSubAgent.
#
# Flujo por iteración:
#   1. NavigationSubAgent llama a get_next_query() → obtiene la query actual
#   2. Navega a Google y extrae las URLs de LinkedIn
#   3. Guarda el resultado con save_query_result()
#   4. Si es la última query → genera reporte final y llama a exit_loop()
#
# max_iterations: límite de seguridad para evitar loops infinitos
#                 (debe ser mayor que el número máximo de queries esperadas)
# ---------------------------------------------------------------------------
navigation_agent = LoopAgent(
    name="NavigationAgent",
    description="Ejecuta búsquedas Selenium query por query y extrae URLs de perfiles LinkedIn.",
    sub_agents=[navigation_sub_agent],
    max_iterations=100,
)

# ---------------------------------------------------------------------------
# ROOT_AGENT — SequentialAgent
#
# Orquesta el flujo completo en tres pasos:
#   1. SearchAgent      → identifica nombres de candidatos
#   2. KeywordGenAgent  → genera queries LinkedIn para cada nombre
#   3. NavigationAgent  → navega query por query y extrae URLs de perfiles
#
# El resultado final queda en "navigation_output" del estado de sesión.
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="LknScraperRootAgent",
    description=(
        "Descubre perfiles de LinkedIn: identifica candidatos en Google, "
        "genera queries y navega con Selenium para extraer URLs."
    ),
    sub_agents=[search_agent, keyword_gen_agent, navigation_agent],
)