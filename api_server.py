"""
Capa Seguros - API Server & Gateway Universal (FastAPI)
Expone la infraestructura de Capa para:
- ChatGPT Custom Actions (OpenAPI 3.1)
- Gemini Function Calling / AI Studio SDK
- WhatsApp / Webhooks de integración para PAS
"""
import sys
import os
import json
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.engine import CapaEngine
from src.core.smart_link import generar_smart_link, validar_smart_link
try:
    from engine import CapaEngine
    from smart_link import generar_smart_link, validar_smart_link
    from telemetry import PilotTelemetryManager
except ModuleNotFoundError:
    from src.core.engine import CapaEngine
    from src.core.smart_link import generar_smart_link, validar_smart_link
    from src.core.telemetry import PilotTelemetryManager
telemetry = PilotTelemetryManager(fail_closed=True)
engine = CapaEngine(telemetry=telemetry)

def handle_http_request(method: str, path: str, query_params: dict = None, body: dict = None, headers: dict = None) -> tuple[int, dict]:
    """
    Despachador HTTP determinístico y sin dependencias pesadas.
    Permite correr como ASGI / WSGI en Render o localmente.
    """
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

    # 4. Generación de Smart Link (Para que el PAS envíe por WhatsApp)
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

if __name__ == "__main__":
    # Test básico de despacho
    print("Testing /health:", handle_http_request("GET", "/health"))
    print("Testing /v1/policies:", handle_http_request("GET", "/v1/policies", query_params={"dni": "29269803"}))
    print("Testing /v1/coverage/verify:", handle_http_request("POST", "/v1/coverage/verify", body={"poliza_numero": 7894561, "consulta": "granizo"}))
