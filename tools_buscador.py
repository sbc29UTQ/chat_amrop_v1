"""
tools_buscador.py – Herramientas del KeywordGenAgent.

Responsabilidad:
    Convertir nombres de personas en queries optimizadas para buscar
    sus perfiles de LinkedIn directamente en Google.

Estilo: programación funcional (solo funciones, sin clases).
"""

from google.adk.tools.tool_context import ToolContext


# ---------------------------------------------------------------------------
# Tool: generar_keywords
#
# ¿Qué hace?
#   Recibe un texto con nombres de personas (uno por línea) y genera para
#   cada nombre una query de búsqueda en Google con el formato:
#       site:<pais>.linkedin.com/in "Nombre Apellido"
#
#   Guarda la lista de queries en el estado de sesión bajo "_nav_queries"
#   para que NavigationAgent las consuma directamente (sin re-parseo de texto).
#
# ¿Por qué acepta str en vez de list[str]?
#   El LLM invoca esta herramienta vía function calling. Pasar el texto
#   completo como string es más robusto que pedirle al LLM que construya
#   una lista Python — evita errores de serialización JSON.
# ---------------------------------------------------------------------------

def generar_keywords(
    nombres_texto: str,
    tool_context: ToolContext,
    pais: str = "pe",
) -> dict:
    """
    Convierte un texto con nombres (uno por línea) en queries optimizadas
    para buscar perfiles de LinkedIn en Google.

    Persiste las queries en el estado de sesión bajo "_nav_queries" y
    reinicia "_nav_index" a 0 para que NavigationAgent itere desde el inicio.

    Parámetros:
        nombres_texto : Texto con nombres completos, uno por línea.
                        Ejemplo: "Luis Santivañez\nAbraham Chahuan"
        tool_context  : Contexto ADK inyectado automáticamente (acceso al estado).
        pais          : Código de país del subdominio LinkedIn (default "pe").
                        Ejemplos: "pe" → pe.linkedin.com, "co" → co.linkedin.com

    Retorna:
        dict con:
          - queries : lista de strings con el formato
                      site:<pais>.linkedin.com/in "<Nombre Apellido>"
          - total   : cantidad de queries generadas
    """
    # Prefijo de búsqueda que filtra resultados al subdominio de LinkedIn del país
    dominio: str = f"site:{pais}.linkedin.com/in"

    # Parsear el texto línea por línea, ignorando líneas vacías
    nombres: list[str] = [
        line.strip()
        for line in nombres_texto.splitlines()
        if line.strip()
    ]

    # Construir la query para cada nombre con comillas para búsqueda exacta
    queries: list[str] = [
        f'{dominio} "{nombre}"'
        for nombre in nombres
    ]

    # Persistir en estado para que get_next_query las consuma como lista Python
    # (evita re-parseo frágil de texto en NavigationAgent)
    tool_context.state["_nav_queries"] = queries
    tool_context.state["_nav_index"] = 0

    return {
        "queries": queries,       # Lista de queries listas para usar en Google
        "total":   len(queries),  # Cantidad de queries generadas
    }