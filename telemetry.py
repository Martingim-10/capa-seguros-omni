"""
Módulo de Telemetría y Auditoría Fail-Closed.
Registra eventos operativos sin almacenar DNI, CUIT, tokens ni datos personales.
"""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class FailClosedTelemetryError(Exception):
    pass


class PilotTelemetryManager:
    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed
        self._events = []

    def _anonymize_subject(self, subject_id: str) -> str:
        return hashlib.sha256(f"omni-audit:{subject_id}".encode("utf-8")).hexdigest()[:16]

    def record_event(self, subject_id: str, action: str, http_status: int, latency_ms: float) -> Dict[str, Any]:
        try:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subject_hash": self._anonymize_subject(subject_id or "anonymous"),
                "action": str(action),
                "http_status": int(http_status),
                "latency_ms": float(latency_ms)
            }
            self._events.append(entry)
            return entry
        except Exception as e:
            if self.fail_closed:
                raise FailClosedTelemetryError(f"Fallo en registro de telemetría fail-closed: {type(e).__name__}") from e
            return {"status": "telemetry_error"}
