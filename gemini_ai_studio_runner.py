"""
Capa Seguros - Runner para Google AI Studio & Gemini API SDK
Permite ejecutar el motor completo de Capa dentro del entorno de Google AI Studio
usando la API Key generada en aistudio.google.com.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json
from src.core.engine import CapaEngine

# Motor local de Capa (conecta con Sancor)
engine = CapaEngine()

def get_ai_studio_configuration():
    """
    Devuelve el payload completo para configurar el asistente en Google AI Studio:
    - Model selection
    - System Instructions
    - Function Declarations (Tools)
    """
    system_instruction = (
        "Sos Capa Seguros, una infraestructura de inteligencia aseguradora independiente "
        "conectada a pólizas reales de Sancor Seguros.\n\n"
        "REGLAS ESTRICTAS DE RESPUESTA:\n"
        "1. Toda afirmación sobre coberturas, sumas aseguradas o franquicias DEBE basarse "
        "exclusivamente en los datos retornados por las herramientas de consulta contractual.\n"
        "2. NUNCA inventes coberturas. Si una cobertura no figura en la póliza o la herramienta "
        "devuelve veredicto SIN_EVIDENCIA_DIRECTA, debes aclarar expresamente que no es posible "
        "confirmar el dato y sugerir contactar al Productor Asesor de Seguros (PAS).\n"
        "3. Jamás asumas que la falta de confirmación equivale a una exclusión.\n"
        "4. Cita siempre el número de póliza y la cláusula específica (ej. CA-CR 2.1, CP-FR 0.1)."
    )

    tools_definitions = [
        {
            "name": "consultar_polizas_asegurado",
            "description": "Obtiene la lista de pólizas vigentes asociadas a un DNI en Sancor Seguros.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "dni": {
                        "type": "STRING",
                        "description": "Número de DNI del asegurado (ej. '29269803')."
                    },
                    "ramo": {
                        "type": "STRING",
                        "description": "Filtro opcional: 'Automotor' o 'Combinado Familiar'."
                    }
                },
                "required": ["dni"]
            }
        },
        {
            "name": "verificar_cobertura_poliza",
            "description": "Verifica si un siniestro o evento (granizo, rotura de cristal, robo de auxilio, franquicia, grúa) está cubierto bajo una póliza oficial.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "poliza_numero": {
                        "type": "INTEGER",
                        "description": "Número oficial de la póliza (ej. 7894561)."
                    },
                    "consulta": {
                        "type": "STRING",
                        "description": "Siniestro o cobertura a consultar."
                    }
                },
                "required": ["poliza_numero", "consulta"]
            }
        }
    ]

    return {
        "model": "gemini-1.5-pro",
        "system_instruction": system_instruction,
        "tools": tools_definitions
    }

def ejecutar_herramienta_local(nombre_funcion: str, argumentos: dict) -> dict:
    """
    Simula o despacha la ejecución de la función solicitada por Gemini en AI Studio.
    """
    if nombre_funcion == "consultar_polizas_asegurado":
        return engine.consultar_polizas(argumentos.get("dni"), argumentos.get("ramo"))
    elif nombre_funcion == "verificar_cobertura_poliza":
        return engine.verificar_cobertura(argumentos.get("poliza_numero"), argumentos.get("consulta"))
    else:
        return {"error": f"Función no reconocida: {nombre_funcion}"}

if __name__ == "__main__":
    cfg = get_ai_studio_configuration()
    print("=== CONFIGURACIÓN LISTA PARA GOOGLE AI STUDIO ===")
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
