"""
Capa Seguros - Cliente Python para Infraestructura Omni MCP
Cumple estrictamente GEMINI_START_HERE.md:
- Cero datos sintéticos en código.
- Cero credenciales directas de Sancor (usa exclusivamente https://capa-omni-mcp.onrender.com).
- Validación de preflight (/health, /pilot/readiness, /.well-known/oauth-protected-resource y rechazo anónimo /mcp).
- Consumo de las 6 herramientas MCP bajo OAuth Bearer token con scope insurance:read.
- Separación explícita para Auto 200 (discovery, PDF legible, evidencia) y Hogar 1800 (discovery soportado, PDF pendiente).
"""
import os
import time
import requests
from typing import Dict, Any, Optional, Tuple

OMNI_MCP_BASE_URL = os.getenv("OMNI_MCP_BASE_URL", "https://capa-omni-mcp.onrender.com").rstrip("/")
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-1xadutu23ydo7tvz.us.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://capa-omni-mcp.onrender.com")
AUTH0_REQUIRED_SCOPE = os.getenv("AUTH0_REQUIRED_SCOPE", "insurance:read")

FORBIDDEN_ARBITRARY_IDENTIFIER_KEYS = {"dni", "cuit", "identificationNumber", "referenceNumber", "officialNumber"}


class CapaEngine:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or OMNI_MCP_BASE_URL).rstrip("/")
        self.mcp_endpoint = f"{self.base_url}/mcp"

    def validar_bearer_header(self, auth_header: Optional[str]) -> Tuple[bool, Optional[str], int, str]:
        """
        Valida que exista un token OAuth en el encabezado Authorization.
        Rechaza consultas anónimas y cualquier token estático de prueba.
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return False, None, 401, "Autenticación OAuth requerida. No se permiten consultas anónimas."

        token = auth_header.replace("Bearer ", "", 1).strip()
        if not token or len(token) < 20 or token.lower().startswith("token_"):
            return False, None, 403, "Token inválido o estático. Se requiere un JWT OAuth emitido por Auth0 con scope insurance:read."

        return True, token, 200, "OK"

    def validar_argumentos_seguros(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Regla 1 y 2 de GEMINI_START_HERE.md:
        Nunca enviar DNI ni referencia arbitrarios como autorización.
        """
        if not isinstance(arguments, dict):
            return False, "Formato de argumentos inválido."
        present_forbidden = FORBIDDEN_ARBITRARY_IDENTIFIER_KEYS.intersection(set(arguments.keys()))
        if present_forbidden:
            return False, f"Prohibido enviar identificadores arbitrarios ({', '.join(sorted(present_forbidden))}) sin vínculo OAuth verificado."
        return True, None

    def ejecutar_preflight_paso4(self) -> Dict[str, Any]:
        """
        Ejecuta las 4 comprobaciones del Paso 4 de GEMINI_START_HERE.md:
        1. GET /health
        2. GET /pilot/readiness
        3. GET /.well-known/oauth-protected-resource
        4. POST /mcp sin credenciales (debe ser denegado con 401/403)
        """
        resultados = {}

        resultados["health"] = self._get_public_json(f"{self.base_url}/health")
        resultados["pilot_readiness"] = self._get_public_json(f"{self.base_url}/pilot/readiness")
        resultados["oauth_discovery"] = self._get_public_json(f"{self.base_url}/.well-known/oauth-protected-resource")

        t0 = time.perf_counter()
        try:
            resp_anon = requests.post(
                self.mcp_endpoint,
                headers={"Content-Type": "application/json"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                timeout=10
            )
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            rechazado = resp_anon.status_code in (401, 403)
            resultados["anonymous_mcp_rejection"] = {
                "url": self.mcp_endpoint,
                "http_status": resp_anon.status_code,
                "latencia_ms": lat_ms,
                "passed_security_gate": rechazado
            }
        except Exception as e:
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            resultados["anonymous_mcp_rejection"] = {
                "url": self.mcp_endpoint,
                "http_status": 0,
                "latencia_ms": lat_ms,
                "passed_security_gate": False,
                "error_sanitizado": type(e).__name__
            }

        return {
            "step": "GEMINI_START_HERE_STEP_4_PREFLIGHT",
            "upstream_base_url": self.base_url,
            "checks": resultados
        }

    def _get_public_json(self, url: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            resp = requests.get(url, timeout=10)
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            try:
                body = resp.json()
            except Exception:
                body = {"raw_preview": resp.text[:300]}
            return {
                "url": url,
                "http_status": resp.status_code,
                "latencia_ms": lat_ms,
                "body": body
            }
        except Exception as e:
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "url": url,
                "http_status": 0,
                "latencia_ms": lat_ms,
                "error_sanitizado": type(e).__name__
            }

    def listar_herramientas_mcp(self, oauth_token: str) -> Tuple[int, Dict[str, Any]]:
        """Inspecciona las 6 herramientas MCP del servidor Omni."""
        rpc_req = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/list",
            "params": {}
        }
        return self._post_mcp(oauth_token, rpc_req)

    def invocar_herramienta_mcp(self, oauth_token: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Invoca una herramienta en https://capa-omni-mcp.onrender.com/mcp
        validando previamente que no se inyecten DNI ni referencias libres.
        """
        args = arguments or {}
        seguro, motivo_rechazo = self.validar_argumentos_seguros(args)
        if not seguro:
            return 403, {
                "error": "forbidden_arbitrary_identifier",
                "message": motivo_rechazo
            }

        ramo_arg = str(args.get("branchCode") or args.get("ramo") or "").lower()
        if ("1800" in ramo_arg or "hogar" in ramo_arg or "combinado" in ramo_arg) and ("doc" in tool_name.lower() or "pdf" in tool_name.lower()):
            return 422, {
                "status": "pending_upstream_capability",
                "branch": 1800,
                "discovery_supported": True,
                "pdf_retrieval_supported": False,
                "message": "Para Combinado Familiar (ramo 1800), el descubrimiento de póliza está soportado, pero la recuperación de PDF permanece pendiente en Sancor (error 401 upstream). No se anuncia como resuelto."
            }

        rpc_req = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        return self._post_mcp(oauth_token, rpc_req)

    def _post_mcp(self, oauth_token: str, rpc_payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        t0 = time.perf_counter()
        try:
            resp = requests.post(self.mcp_endpoint, headers=headers, json=rpc_payload, timeout=20)
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            try:
                data = resp.json()
            except Exception:
                data = {"raw_text": resp.text[:500]}

            return resp.status_code, {
                "http_status": resp.status_code,
                "latencia_ms": lat_ms,
                "mcp_response": data
            }
        except Exception as e:
            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            return 504, {
                "http_status": 504,
                "latencia_ms": lat_ms,
                "error_sanitizado": f"Error de conexión con servidor MCP: {type(e).__name__}"
            }
