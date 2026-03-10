# 🔎 LinkedIn Discovery Multi-Agent

Sistema **multi-agente en Python** que permite descubrir perfiles de **LinkedIn** a partir de una consulta del usuario.

El sistema realiza automáticamente:

1. Buscar personas en Google
2. Generar búsquedas optimizadas para LinkedIn
3. Navegar en Google
4. Extraer perfiles de LinkedIn

El resultado final es un **reporte con perfiles encontrados**.

---

# 🧠 Flujo del sistema:

1. **SearchAgent** → busca nombres de personas
2. **KeywordGenAgent** → genera queries de LinkedIn
3. **NavigationAgent** → navega en Google y extrae perfiles

Los agentes son orquestados por un **SequentialAgent (Root Agent)**. 

---

# 📦 Requisitos

Antes de ejecutar el proyecto necesitas:

* Python **3.10 o superior**
* Chrome instalado
* Acceso a Google Generative AI

---

# ⚙️ Instalación paso a paso

## 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/tu-repo/linkedin-discovery-agent.git

cd linkedin-discovery-agent
```

---

## 2️⃣ Crear entorno virtual

```bash
python -m venv venv
```

Activar entorno:

Mac / Linux

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

---

## 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# 🔑 Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto.

Ejemplo:

```env
# Clave de Google Generative AI
GOOGLE_API_KEY=

# Modelo Gemini utilizado por los agentes
GOOGLE_GENAI_MODEL=gemini-2.5-flash

# Usar Vertex AI o AI Studio
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Si se establece en 1 se desactiva Selenium
DISABLE_WEB_DRIVER=0
```

---

# 📁 Estructura del proyecto

```
lkn_scraper_agent/

agent.py
instructions.py
tools_buscador.py
tools_navegacion.py
.env
```

Descripción:

| Archivo               | Función                                       |
| --------------------- | --------------------------------------------- |
| `agent.py`            | Define los agentes del sistema                |
| `instructions.py`     | Prompts del sistema para cada agente          |
| `tools_buscador.py`   | Generación de queries LinkedIn                |
| `tools_navegacion.py` | Navegación en Google y extracción de perfiles |

---

# 🤖 Agentes del sistema

## SearchAgent

Busca personas relacionadas con la consulta del usuario usando Google.

Salida esperada:

```
Luis Santivañez
Abraham Chahuan
Adolfo Heeren
```

---

## KeywordGenAgent

Convierte los nombres encontrados en queries optimizadas para LinkedIn.

Ejemplo generado:

```
site:pe.linkedin.com/in "Luis Santivañez"
site:pe.linkedin.com/in "Abraham Chahuan"
```

Estas queries se almacenan en el estado interno del agente. 

---

## NavigationAgent

Navega en Google y extrae URLs de perfiles LinkedIn.

Por cada query:

1. Construye la URL de búsqueda
2. Abre Google en el navegador
3. Extrae enlaces de LinkedIn
4. Guarda resultados

---

# 🚀 Ejecutar el sistema

Una vez configurado todo:

```bash
python main.py
```

Ejemplo de consulta:

```
Top gerentes de Antamina
```

---

# 📄 Resultado

El sistema devuelve un reporte con perfiles encontrados.

Ejemplo:

```
Luis Santivañez
- linkedin.com/in/luis-santivanez

Abraham Chahuan
- linkedin.com/in/abraham-chahuan
```

---
