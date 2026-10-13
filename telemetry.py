"""
Módulo de Telemetría y Auditoría de Seguridad (Fail-Closed).
Diseñado para registrar consultas de forma anonimizada y auditable.
Principio Fail-Closed: Si el registrador de seguridad o auditoría falla,
la operación se detiene para evitar fugas de datos sin trazabilidad (Ley 25.326).
"""
import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("capa.telemetry")

class FailClosedTelemetryError(Exception):
    """Error fatal cuando el sistema de telemetría o auditoría no puede garantizar el registro."""
    pass

class PilotTelemetryManager:
    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed
        self._audit_log = []

    def _hash_pii(self, valor: str) -> str:
        """Anonimiza DNI, nombres o patentes mediante hash SHA-256 salteado."""
        return hashlib.sha256(f"capa-salt:{valor}".encode('utf-8')).hexdigest()[:16]

    def record_access(self, dni: str, poliza_numero: Optional[int], accion: str, exito: bool) -> Dict[str, Any]:
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "anonymous_user_id": self._hash_pii(str(dni)),
                "policy_ref": poliza_numero,
                "action": accion,
                "status": "SUCCESS" if exito else "ERROR"
            }
            self._audit_log.append(entry)
            logger.info("Audit entry registered: %s", entry["action"])
            return entry
        except Exception as e:
            if self.fail_closed:
                raise FailClosedTelemetryError(f"Falla crítica en telemetría de seguridad: {str(e)}") from e
            logger.warning("Telemetry failure bypassed (fail-open mode): %s", e)
            return {"status": "TELEMETRY_FAILED", "error": str(e)}

    def get_recent_events(self) -> list:
        return list(self._audit_log)
