"""
Capa Seguros - API Server & Gateway Universal
Compatible tanto con estructura en raíz como con paquetes src.
"""
import sys
import os
import json
import types
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Compatibilidad automática para imports en raíz
_cur = os.path.dirname(os.path.abspath(__file__))
if _cur not in sys.path:
    sys.path.insert(0, _cur)

if "src" not in sys.modules:
    _src = types.ModuleType("src")
    _src.__path__ = [_cur]
    _core = types.ModuleType("src.core")
    _core.__path__ = [_cur]
    sys.modules["src"] = _src
    sys.modules["src.core"] = _core

# Importación de módulos de Capa Seguros
try:
    from engine import CapaEngine
    from smart_link import generar_smart_link, validar_smart_link
    from telemetry import PilotTelemetryManager
except ModuleNotFoundError:
    from src.core.engine import CapaEngine
    from src.core.smart_link import generar_smart_link, validar_smart_link
    from src.core.telemetry import PilotTelemetryManager

# Inicialización de servicios
telemetry = PilotTelemetryManager(fail_closed=True)
engine = CapaEngine(telemetry=telemetry)

def handle_http_request(method: str, path: str, query_params: dict = None, body: dict = None, headers: dict = None) -> tuple[int, dict]:
    query_params = query_params or {}
    body = body or {}
    headers = headers or {}
    
    # 1. Healthcheck
    if path in ["/health", "/"]:
        return 200, {
            "status": "online",
            "service": "Capa Seguros Omni-LLM Gateway",
            "version": "1.0.0",
            "environment": "production"
        }
        
    # 2. Consulta de Pólizas (para ChatGPT Actions y Gemini)
    if path == "/v1/policies" and method == "GET":
        dni = query_params.get("dni") or query_params.get("identificationNumber")
        ramo = query_params.get("ramo") or query_params.get("branchCode")
        
        if not dni:
            return 400, {"error": "Falta parámetro obligatorio: dni o identificationNumber"}
            
        res = engine.consultar_polizas(str(dni), str(ramo) if ramo else None)
        return 200, res

    # 3. Verificación Contractual de Cobertura
    if path == "/v1/coverage/verify" and method == "POST":
        poliza_num = body.get("poliza_numero") or body.get("policyNumber")
        consulta = body.get("consulta") or body.get("inquiry")
        
        if not poliza_num or not consulta:
            return 400, {"error": "Faltan parámetros obligatorios: poliza_numero y consulta"}
            
        res = engine.verificar_cobertura(int(poliza_num), str(consulta))
        return 200, res

    # 4. Generación de Smart Link (Para WhatsApp)
    if path == "/v1/smart-link/generate" and method == "POST":
        poliza_id = body.get("poliza_id")
        dni = body.get("dni")
        canal = body.get("canal", "gemini")
        
        if not poliza_id or not dni:
            return 400, {"error": "Faltan parámetros: poliza_id y dni"}
            
        res = generar_smart_link(str(poliza_id), str(dni), canal=canal)
        return 200, res

    # 5. Validación de Smart Link
    if path == "/v1/smart-link/validate" and method == "POST":
        token = body.get("token")
        if not token:
            return 400, {"error": "Falta parámetro: token"}
            
        res = validar_smart_link(str(token))
        status_code = 200 if res.get("valido") else 401
        return status_code, res

    return 404, {"error": f"Ruta no encontrada: {method} {path}"}

class CapaHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        headers = dict(self.headers)
        status, data = handle_http_request("GET", parsed.path, query_params=query, headers=headers)
        
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
            
        headers = dict(self.headers)
        status, data = handle_http_request("POST", parsed.path, body=body, headers=headers)
        
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), CapaHTTPHandler)
    print(f"🚀 Capa Seguros Server escuchando en http://0.0.0.0:{port}")
    sys.stdout.flush()
    server.serve_forever()

if __name__ == "__main__":
    run_server()
