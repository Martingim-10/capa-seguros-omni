# CAPA SEGUROS — Infraestructura de Inteligencia Aseguradora Omni-LLM

Infraestructura tecnológica independiente que conecta modelos de lenguaje (**ChatGPT, Gemini y clientes MCP**) con las APIs oficiales de aseguradoras (**Sancor Seguros**), permitiendo a las personas consultar y comprender sus pólizas en lenguaje natural con evidencia contractual verificable.

---

## 🎯 Visión y Principios del Proyecto

1. **La consulta sucede donde el usuario ya está:** Vive dentro de ChatGPT, Gemini o WhatsApp sin forzar al asegurado a descargar aplicaciones adicionales ni entrar a portales complejos.
2. **Onboarding móvil en 1-Toque (Smart Links):** Mediante tokens efímeros firmados (`HMAC-SHA256`) con tiempo de expiración (TTL), el Productor Asesor (PAS) envía un enlace directo para que el cliente consulte su póliza sin contraseñas ni configuraciones técnicas.
3. **Privacidad por Diseño (Ley 25.326):** El backend sanitiza los documentos en memoria RAM, eliminando DNI, CUIT, domicilios y datos bancarios antes de que la información toque el modelo de lenguaje.
4. **Guardrails Antialucinación:** Toda respuesta cita número de póliza y cláusulas contractuales específicas (ej. Granizo `CA-CC 4.2`, Cristales `CA-CR 2.1`, Franquicia fija `CP-FR 0.1`). Si no hay evidencia, emite un veredicto neutro y deriva al PAS.

---

## 🏛️ Arquitectura del Repositorio

- `src/core/engine.py`: Motor semántico de resolución de pólizas y ontología de seguros.
- `src/core/smart_link.py`: Generador y validador de enlaces de activación efímeros.
- `src/core/telemetry.py`: Telemetría *fail-closed* con anonimización de identidad mediante hashes salteados.
- `src/server/api_server.py`: Gateway HTTP universal (FastAPI) compatible con ChatGPT Actions y webhooks.
- `src/server/mcp_server.py`: Servidor estándar JSON-RPC 2.0 (Model Context Protocol).
- `src/server/gemini_ai_studio_runner.py`: Conector para Google AI Studio y el SDK de Gemini.
- `tests/test_pilot.py`: Suite de 7 pruebas unitarias automatizadas (100% aprobadas).
- `render.yaml` & `Dockerfile`: Configuración de despliegue directo en Render.

---

## 🚀 Despliegue Rápido en Render

1. En [Render Dashboard](https://dashboard.render.com/), creá un **New Web Service**.
2. Conectá este repositorio de GitHub.
3. Render detectará automáticamente el archivo `render.yaml` y configurará el entorno en Python.
