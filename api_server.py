"""
Capa Seguros - Servidor Python Independiente (capa-seguros-omni)
Cumple 100% de GEMINI_START_HERE.md:
1. Cero datos sintéticos ni tokens fijos en código.
2. Cero solicitud de SANCOR_USERNAME / SANCOR_PASSWORD / SANCOR_CLIENT_ID.
3. Consume el backend Omni aislado (https://capa-omni-mcp.onrender.com) con OAuth insurance:read.
4. Ejecuta preflight (/health, /pilot/readiness, /.well-known/oauth-protected-resource y denegación de /mcp anónimo).
5. Separa claramente discovery, PDF legible y evidencia contractual para Auto 200 y Hogar 1800.
"""
import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Tuple, Dict, Any

_cur = os.path.dirname(os.path.abspath(__file__))
if _cur not in sys.path:
    sys.path.insert(0, _cur)

from engine import CapaEngine, OMNI_MCP_BASE_URL, AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_REQUIRED_SCOPE
from telemetry import PilotTelemetryManager

telemetry = PilotTelemetryManager(fail_closed=True)
engine = CapaEngine()


def handle_http_request(method: str, path: str, query_params: dict = None, body: dict = None, headers: dict = None) -> Tuple[int, Dict[str, Any]]:
    query_params = query_params or {}
    body = body or {}
    headers = headers or {}
    auth_header = headers.get("authorization") or headers.get("Authorization")

    # 1. Healthcheck público (sin secretos)
    if path in ["/health", "/"]:
        telemetry.record_event("system", "healthcheck", 200, 0.1)
        return 200, {
            "status": "online",
            "service": "capa-seguros-omni",
            "upstream_omni_mcp": OMNI_MCP_BASE_URL,
            "oauth_tenant": AUTH0_DOMAIN,
            "oauth_audience": AUTH0_AUDIENCE,
            "oauth_required_scope": AUTH0_REQUIRED_SCOPE,
            "synthetic_policies_removed": True,
            "static_pilot_tokens_removed": True,
            "hogar_1800_pdf_status": "pending_upstream_401"
        }

    # 2. Paso 4 de GEMINI_START_HERE.md: Verificación pública de preflight contra capa-omni-mcp.onrender.com
    if path in ["/v1/preflight", "/pilot/readiness"] and method == "GET":
        reporte = engine.ejecutar_preflight_paso4()
        telemetry.record_event("system", "preflight_check", 200, 1.0)
        return 200, reporte

    # 3. Paso 1 de GEMINI_START_HERE.md: Inspeccionar las 6 herramientas MCP (Requiere OAuth Bearer token)
    if path == "/v1/mcp/tools" and method == "GET":
        ok, token, code, msg = engine.validar_bearer_header(auth_header)
        if not ok:
            telemetry.record_event("unauthenticated", "mcp_tools_rejected", code, 0.1)
            return code, {"error": "unauthorized" if code == 401 else "forbidden", "message": msg}
        return engine.listar_herramientas_mcp(token)

    # 4. Paso 2 y 5 de GEMINI_START_HERE.md: Invocar herramienta MCP autorizada
    if path == "/v1/mcp/call" and method == "POST":
        ok, token, code, msg = engine.validar_bearer_header(auth_header)
        if not ok:
            telemetry.record_event("unauthenticated", "mcp_call_rejected", code, 0.1)
            return code, {"error": "unauthorized" if code == 401 else "forbidden", "message": msg}

        tool_name = body.get("name") or body.get("tool")
        arguments = body.get("arguments") or {}
        if not tool_name:
            return 400, {"error": "bad_request", "message": "Debe especificar el nombre de la herramienta MCP en 'name'."}

        status_code, resp_data = engine.invocar_herramienta_mcp(token, str(tool_name), arguments)
        telemetry.record_event(token[:12], f"mcp_call:{tool_name}", status_code, resp_data.get("latencia_ms", 0.0))
        return status_code, resp_data

    # 5. Bloqueo de consultas por DNI o referencia libre en /v1/policies
    if path == "/v1/policies":
        ok, token, code, msg = engine.validar_bearer_header(auth_header)
        if not ok:
            telemetry.record_event("unauthenticated", "policies_rejected", code, 0.1)
            return code, {"error": "unauthorized" if code == 401 else "forbidden", "message": msg}

        seguro, motivo = engine.validar_argumentos_seguros(query_params)
        if not seguro:
            telemetry.record_event(token[:12], "policies_forbidden_identifier", 403, 0.1)
            return 403, {"error": "forbidden_arbitrary_identifier", "message": motivo}

        return 400, {
            "error": "use_mcp_endpoint",
            "message": "Utilice POST /v1/mcp/call con su token OAuth (scope insurance:read) para invocar las herramientas MCP del backend Omni."
        }

    return 404, {"error": "not_found", "message": f"Ruta no encontrada: {method} {path}"}


class CapaHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        status, data = handle_http_request("GET", parsed.path, query, {}, dict(self.headers))
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(content_len).decode("utf-8")) if content_len > 0 else {}
        except Exception:
            body = {}
        status, data = handle_http_request("POST", parsed.path, {}, body, dict(self.headers))
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), CapaHTTPHandler)
    print(f"🚀 Capa Seguros Omni Client escuchando en 0.0.0.0:{port}")
    sys.stdout.flush()
    server.serve_forever()
