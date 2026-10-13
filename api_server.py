"""
Capa Seguros - Gateway Seguro & Adaptador Oficial de Sancor (Día 1)
"""
import sys
import os
import time
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, Tuple

# Variables de entorno oficiales de Sancor (se configuran en Render)
SANCOR_BASE_URL = os.getenv("SANCOR_BASE_URL", "https://external-pre-api.gruposancorseguros.com/apissa/pre-catalog").rstrip('/')
SANCOR_CLIENT_ID = os.getenv("SANCOR_CLIENT_ID", "")
SANCOR_USERNAME = os.getenv("SANCOR_USERNAME", "")
SANCOR_PASSWORD = os.getenv("SANCOR_PASSWORD", "")

# Matriz estricta de casos autorizados para el piloto (Casos P01 a P05)
PILOT_BINDINGS = {
    "token_p01_auth": {"ref": 31226261, "ramo": 200, "caso": "P01"},
    "token_p02_auth": {"ref": 31120099, "ramo": 200, "caso": "P02"},
    "token_p03_auth": {"ref": 31125958, "ramo": 200, "caso": "P03"},
    "token_p04_auth": {"ref": 30754360, "ramo": 200, "caso": "P04"},
    "token_p05_auth": {"ref": 30224203, "ramo": 200, "caso": "P05"},
}

_cached_id_token = None
_token_expires_at = 0

def obtener_sancor_id_token() -> Tuple[bool, Optional[str], int, float, Optional[str]]:
    global _cached_id_token, _token_expires_at
    if _cached_id_token and time.time() < (_token_expires_at - 60):
        return True, _cached_id_token, 200, 0.0, None

    if not (SANCOR_CLIENT_ID and SANCOR_USERNAME and SANCOR_PASSWORD):
        return False, None, 500, 0.0, "Credenciales de Sancor no configuradas en Render."

    url = f"{SANCOR_BASE_URL}/v2/security/auth0/token"
    headers = {
        "gss_apiclient_id": SANCOR_CLIENT_ID,
        "Content-Type": "application/json"
    }
    body = {
        "username": SANCOR_USERNAME,
        "password": SANCOR_PASSWORD,
        "app_client": "Ceibo"
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=12)
        lat_ms = round((time.perf_counter() - t0) * 1000, 2)
        if resp.status_code == 200:
            data = resp.json()
            id_token = data.get("id_token") or data.get("access_token")
            if not id_token:
                return False, None, resp.status_code, lat_ms, "Respuesta sin id_token."
            _cached_id_token = id_token
            _token_expires_at = time.time() + data.get("expires_in", 3600)
            return True, id_token, 200, lat_ms, None
        return False, None, resp.status_code, lat_ms, f"Sancor Auth0 devolvió HTTP {resp.status_code}"
    except Exception as e:
        lat_ms = round((time.perf_counter() - t0) * 1000, 2)
        return False, None, 0, lat_ms, f"Error de red Auth0: {type(e).__name__}"

def verificar_autorizacion(auth_header: Optional[str]) -> Tuple[bool, Optional[dict], int, str]:
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, None, 401, "Autenticación requerida. No se permiten consultas anónimas."
    token = auth_header.replace("Bearer ", "").strip()
    binding = PILOT_BINDINGS.get(token)
    if not binding:
        return False, None, 403, "Acceso denegado: póliza no autorizada para esta identidad."
    return True, binding, 200, "Autorizado"

def handle_http_request(method: str, path: str, query_params: dict, body: dict, headers: dict) -> Tuple[int, dict]:
    auth_header = headers.get("authorization") or headers.get("Authorization")

    if path in ["/health", "/"]:
        return 200, {
            "status": "online",
            "service": "Capa Seguros Omni-LLM",
            "sancor_configured": bool(SANCOR_CLIENT_ID and SANCOR_USERNAME and SANCOR_PASSWORD),
            "auth_required": True
        }

    if path == "/v1/policies" and method == "GET":
        ok_auth, binding, code_auth, msg_auth = verificar_autorizacion(auth_header)
        if not ok_auth:
            return code_auth, {"error": "unauthorized" if code_auth == 401 else "forbidden", "message": msg_auth}

        ref_autorizada = binding["ref"]
        ramo_autorizado = binding["ramo"]
        caso_id = binding["caso"]

        ok_tok, id_token, code_tok, lat_tok, err_tok = obtener_sancor_id_token()
        if not ok_tok:
            return 502, {"status": "error_upstream_auth", "auth0_status": code_tok, "detalle": err_tok}

        url = f"{SANCOR_BASE_URL}/policies"
        sancor_headers = {
            "Authorization": f"Bearer {id_token}",
            "gss_apiclient_id": SANCOR_CLIENT_ID,
            "Content-Type": "application/json"
        }
        params = {"referenceNumber": int(ref_autorizada), "branchCode": int(ramo_autorizado)}

        t0 = time.perf_counter()
        try:
            resp = requests.get(url, headers=sancor_headers, params=params, timeout=15)
            lat_pol_ms = round((time.perf_counter() - t0) * 1000, 2)
            if resp.status_code == 200:
                return 200, {
                    "status": "success",
                    "caso": caso_id,
                    "referencia": ref_autorizada,
                    "latencia_policies_ms": lat_pol_ms,
                    "latencia_auth0_ms": lat_tok,
                    "polizas": resp.json()
                }
            return resp.status_code, {
                "status": "error_sancor",
                "caso": caso_id,
                "http_code": resp.status_code,
                "latencia_ms": lat_pol_ms,
                "error_sanitizado": f"Sancor devolvió HTTP {resp.status_code}"
            }
        except Exception as e:
            lat_pol_ms = round((time.perf_counter() - t0) * 1000, 2)
            return 504, {"status": "timeout_error", "caso": caso_id, "latencia_ms": lat_pol_ms, "error": str(type(e).__name__)}

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
    print(f"🚀 Capa Seguros Server escuchando en puerto {port}")
    sys.stdout.flush()
    server.serve_forever()
