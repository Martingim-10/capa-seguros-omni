"""
Servidor MCP Estándar para Capa Seguros (JSON-RPC 2.0).
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.engine import CapaEngine
from src.core.smart_link import validar_smart_link

engine = CapaEngine()

HERRAMIENTAS = [
    {
        "name": "consultar_polizas",
        "description": "Obtiene las pólizas activas en Sancor Seguros asociadas a un DNI o sesión del asegurado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dni": {"type": "string", "description": "DNI o CUIT del asegurado."},
                "ramo": {"type": "string", "description": "Filtro opcional (Automotor, Combinado Familiar)."}
            },
            "required": ["dni"]
        }
    },
    {
        "name": "verificar_cobertura",
        "description": "Verifica si un siniestro o elemento (granizo, cristales, auxilio, cerradura, franquicia) está cubierto en la póliza.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poliza_numero": {"type": "integer", "description": "Número oficial de la póliza."},
                "consulta": {"type": "string", "description": "Pregunta o siniestro a verificar."}
            },
            "required": ["poliza_numero", "consulta"]
        }
    },
    {
        "name": "activar_sesion_smart_link",
        "description": "Valida un token de enlace efímero y devuelve los datos vinculados para iniciar la consulta segura.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Token firmado recibido en el enlace de activación."}
            },
            "required": ["token"]
        }
    }
]

def handle_rpc_request(req: dict) -> dict:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})
    
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": HERRAMIENTAS}
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "consultar_polizas":
            res = engine.consultar_polizas(args.get("dni"), args.get("ramo"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]
                }
            }
        elif tool_name == "verificar_cobertura":
            res = engine.verificar_cobertura(args.get("poliza_numero"), args.get("consulta"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]
                }
            }
        elif tool_name == "activar_sesion_smart_link":
            res = validar_smart_link(args.get("token"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Herramienta desconocida: {tool_name}"}
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": f"Método no soportado: {method}"}
        }
