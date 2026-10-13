"""
Capa Seguros - Core Engine
Normalización semántica de seguros, conector Sancor y guardrails antialucinación.
"""
from typing import Dict, Any, List, Optional
try:
    from telemetry import PilotTelemetryManager
except ModuleNotFoundError:
    from src.core.telemetry import PilotTelemetryManager

PILOTO_POLIZAS_SANCOR = {
    "29269803": [
        {
            "officialNumber": 7894561,
            "referenceNumber": 1002345,
            "branchCode": 1,
            "branchName": "Automotor",
            "planDescription": "Auto Max - Todo Riesgo con Franquicia Fija",
            "validFrom": "2026-01-01T00:00:00Z",
            "validTo": "2027-01-01T00:00:00Z",
            "status": "VIGENTE",
            "risk": {
                "licensePlate": "AF123CD",
                "brand": "Toyota",
                "model": "Corolla XEI 2.0 CVT 2024",
                "sumInsured": 28500000.00
            },
            "clauses": {
                "responsabilidad_civil": {
                    "cubierto": True,
                    "limite": 160000000.00,
                    "clausula_ref": "CG-RC 1.1",
                    "detalle": "Límite legal obligatorio y voluntario según resolución SSN."
                },
                "granizo": {
                    "cubierto": True,
                    "limite": 28500000.00,
                    "franquicia": 0.0,
                    "clausula_ref": "CA-CC 4.2",
                    "detalle": "Daños parciales por granizo e inundación cubiertos hasta suma asegurada sin franquicia."
                },
                "cristales": {
                    "cubierto": True,
                    "limite": "Sin límite de suma",
                    "franquicia": 0.0,
                    "clausula_ref": "CA-CR 2.1",
                    "detalle": "Rotura de parabrisas, luneta, cristales laterales y techo solar amparados al 100%."
                },
                "cerraduras": {
                    "cubierto": True,
                    "limite": 450000.00,
                    "franquicia": 0.0,
                    "clausula_ref": "CA-CE 1.3",
                    "detalle": "Reposición de cerraduras por intento de robo hasta tope de póliza."
                },
                "rueda_auxilio": {
                    "cubierto": True,
                    "limite": "1 evento al año sin depreciación",
                    "franquicia": 0.0,
                    "clausula_ref": "CA-RA 3.0",
                    "detalle": "Robo de neumático de auxilio amparado a valor de reposición a nuevo."
                },
                "franquicia_danos_parciales": {
                    "cubierto": True,
                    "monto": 350000.00,
                    "tipo": "Fija por acontecimiento",
                    "clausula_ref": "CP-FR 0.1",
                    "detalle": "Franquicia fija de $350.000 para colisión, vuelco o roce."
                },
                "auxilio_mecanico": {
                    "cubierto": True,
                    "limite": "Hasta 6 servicios al año, máx 300 km lineales por evento",
                    "prestador": "Sancor Asistencia 24hs (0800-777-4643)",
                    "clausula_ref": "ASIST-01",
                    "detalle": "Remolque y mecánica ligera."
                }
            }
        },
        {
            "officialNumber": 7894562,
            "referenceNumber": 1002346,
            "branchCode": 10,
            "branchName": "Combinado Familiar",
            "planDescription": "Hogar Seguro Total",
            "validFrom": "2026-03-01T00:00:00Z",
            "validTo": "2027-03-01T00:00:00Z",
            "status": "VIGENTE",
            "risk": {
                "address": "Dr. Raúl Scalabrini Ortiz 1426, Trelew, Chubut",
                "buildingType": "Casa particular"
            },
            "clauses": {
                "incendio_edificio": {
                    "cubierto": True,
                    "limite": 85000000.00,
                    "clausula_ref": "CG-IN 1.0",
                    "detalle": "Incendio, rayo y explosión de la estructura."
                },
                "robo_contenido": {
                    "cubierto": True,
                    "limite": 12000000.00,
                    "clausula_ref": "CG-RO 2.0",
                    "detalle": "Mobiliario y electrodomésticos en domicilio declarado."
                },
                "cristales": {
                    "cubierto": True,
                    "limite": 800000.00,
                    "clausula_ref": "CG-CR 3.0",
                    "detalle": "Piezas vítreas colocadas en posición vertical."
                }
            }
        }
    ]
}

class CapaEngine:
    def __init__(self, telemetry: Optional[PilotTelemetryManager] = None):
        self.telemetry = telemetry or PilotTelemetryManager(fail_closed=True)

    def consultar_polizas(self, dni: str, ramo_filtro: Optional[str] = None) -> Dict[str, Any]:
        polizas_raw = PILOTO_POLIZAS_SANCOR.get(str(dni), [])
        
        resultado = []
        for p in polizas_raw:
            if ramo_filtro and ramo_filtro.lower() not in p["branchName"].lower():
                continue
            resultado.append({
                "poliza_numero": p["officialNumber"],
                "referencia": p["referenceNumber"],
                "ramo": p["branchName"],
                "plan": p["planDescription"],
                "estado": p["status"],
                "vigencia_hasta": p["validTo"][:10],
                "bien_asegurado": p["risk"]
            })
            
        self.telemetry.record_access(dni, None, "consultar_polizas", exito=True)
        return {
            "exito": True,
            "total": len(resultado),
            "polizas": resultado
        }

    def verificar_cobertura(self, official_number: int, consulta_siniestro: str, dni_context: str = "29269803") -> Dict[str, Any]:
        target_policy = None
        for asegurado_polizas in PILOTO_POLIZAS_SANCOR.values():
            for p in asegurado_polizas:
                if p["officialNumber"] == int(official_number):
                    target_policy = p
                    break
            if target_policy:
                break
                
        if not target_policy:
            self.telemetry.record_access(dni_context, official_number, "verificar_cobertura", exito=False)
            return {
                "veredicto": "POLIZA_NO_ENCONTRADA",
                "cubierto": False,
                "evidencia": None,
                "explicacion": f"No se localizó la póliza oficial N° {official_number} en los registros de Sancor."
            }

        consulta = consulta_siniestro.lower().strip()
        clausulas = target_policy["clauses"]
        
        # Distinción de ontología aseguradora: robo de neumático de auxilio vs remolque mecánico
        es_robo_auxilio = ("auxilio" in consulta or "rueda" in consulta or "neumatico" in consulta) and ("robo" in consulta or "robaron" in consulta or "cubierta" in consulta)
        
        mapeo_claves = {
            "granizo": "granizo",
            "piedra": "granizo",
            "cristal": "cristales",
            "cristales": "cristales",
            "vidrio": "cristales",
            "parabrisas": "cristales",
            "luneta": "cristales",
            "cerradura": "cerraduras",
            "llave": "cerraduras",
            "auxilio": "rueda_auxilio" if es_robo_auxilio else "auxilio_mecanico",
            "grua": "auxilio_mecanico",
            "remolque": "auxilio_mecanico",
            "mecanica": "auxilio_mecanico",
            "franquicia": "franquicia_danos_parciales",
            "terceros": "responsabilidad_civil",
            "robo": "robo_contenido" if target_policy["branchCode"] == 10 else "rueda_auxilio",
            "incendio": "incendio_edificio"
        }
        
        clave_detectada = None
        for termino, clave in mapeo_claves.items():
            if termino in consulta:
                clave_detectada = clave
                break
                
        if clave_detectada and clave_detectada in clausulas:
            c_info = clausulas[clave_detectada]
            self.telemetry.record_access(dni_context, official_number, f"cobertura:{clave_detectada}", exito=True)
            return {
                "veredicto": "COBERTURA_CONFIRMADA" if c_info.get("cubierto") else "EXCLUSION_EXPLICITA",
                "cubierto": c_info.get("cubierto", False),
                "ramo": target_policy["branchName"],
                "poliza": target_policy["officialNumber"],
                "plan": target_policy["planDescription"],
                "clausula_contractual": c_info.get("clausula_ref"),
                "limite_monto": c_info.get("limite"),
                "franquicia": c_info.get("franquicia"),
                "detalle_contractual": c_info.get("detalle"),
                "guardrail_nota": "Respuesta fundamentada en el frente de póliza y condiciones específicas emitidas por Sancor Seguros."
            }
        else:
            self.telemetry.record_access(dni_context, official_number, "cobertura:sin_evidencia", exito=True)
            return {
                "veredicto": "SIN_EVIDENCIA_DIRECTA",
                "cubierto": None,
                "mensaje": (
                    f"No figura una cláusula explícita para '{consulta_siniestro}' en el extracto digital "
                    f"de la póliza {official_number}. No asuma que está descubierto ni cubierto. "
                    "Consulte el condicionado general o comuníquese con su Productor Asesor de Seguros (PAS)."
                )
            }
