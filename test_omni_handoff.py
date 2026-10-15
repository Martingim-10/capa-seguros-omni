import os
import unittest
from api_server import handle_http_request

class TestOmniHandoffCompliance(unittest.TestCase):
    def test_01_no_synthetic_data_or_static_tokens_in_codebase(self):
        """Verifica que ningún archivo .py contenga PILOTO_POLIZAS_SANCOR ni PILOT_BINDINGS ni tokens fijos."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        forbidden_literals = ["PILOTO_POLIZAS_SANCOR", "PILOT_BINDINGS", "token_p01_auth", "AF123CD", "7894561"]
        for fname in ["engine.py", "api_server.py", "telemetry.py"]:
            fpath = os.path.join(base_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for lit in forbidden_literals:
                self.assertNotIn(lit, content, f"Hallazgo de seguridad: '{lit}' encontrado en {fname}")

    def test_02_health_reports_clean_omni_configuration(self):
        code, body = handle_http_request("GET", "/health")
        self.assertEqual(code, 200)
        self.assertTrue(body["synthetic_policies_removed"])
        self.assertTrue(body["static_pilot_tokens_removed"])
        self.assertEqual(body["upstream_omni_mcp"], "https://capa-omni-mcp.onrender.com")
        self.assertEqual(body["oauth_required_scope"], "insurance:read")

    def test_03_reject_anonymous_access(self):
        code_tools, _ = handle_http_request("GET", "/v1/mcp/tools")
        self.assertEqual(code_tools, 401)
        code_call, _ = handle_http_request("POST", "/v1/mcp/call", body={"name": "consultar_cartera"})
        self.assertEqual(code_call, 401)

    def test_04_reject_static_tokens(self):
        code, body = handle_http_request(
            "GET", "/v1/mcp/tools",
            headers={"Authorization": "Bearer token_p01_auth"}
        )
        self.assertEqual(code, 403)

    def test_05_reject_arbitrary_dni_or_reference(self):
        valid_looking_jwt = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwic2NvcGUiOiJpbnN1cmFuY2U6cmVhZCJ9.signature"
        code, body = handle_http_request(
            "POST", "/v1/mcp/call",
            body={"name": "consultar_cartera", "arguments": {"dni": "29269803"}},
            headers={"Authorization": valid_looking_jwt}
        )
        self.assertEqual(code, 403)
        self.assertEqual(body["error"], "forbidden_arbitrary_identifier")

    def test_06_hogar_1800_pdf_explicitly_marked_pending(self):
        valid_looking_jwt = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwic2NvcGUiOiJpbnN1cmFuY2U6cmVhZCJ9.signature"
        code, body = handle_http_request(
            "POST", "/v1/mcp/call",
            body={"name": "obtener_documento", "arguments": {"ramo": "1800"}},
            headers={"Authorization": valid_looking_jwt}
        )
        self.assertEqual(code, 422)
        self.assertEqual(body["status"], "pending_upstream_capability")
        self.assertFalse(body["pdf_retrieval_supported"])

if __name__ == "__main__":
    unittest.main()
