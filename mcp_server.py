"""
Wrapper MCP stdio/JSON-RPC 2.0 que delega al motor limpio CapaEngine (sin mocks ni secretos).
"""
import json
from typing import Dict, Any
from engine import CapaEngine

engine = CapaEngine()

def handle_rpc_request(req: Dict[str, Any], oauth_token: str = "") -> Dict[str, Any]:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    ok, token, code, msg = engine.validar_bearer_header(f"Bearer {oauth_token}" if oauth_token else None)
    if not ok:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32001, "message": msg, "http_status": code}
        }

    if method == "tools/list":
        status, data = engine.listar_herramientas_mcp(token)
        return {"jsonrpc": "2.0", "id": req_id, "result": data}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        status, data = engine.invocar_herramienta_mcp(token, tool_name, arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": data}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Método no soportado: {method}"}
    }
