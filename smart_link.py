"""
Módulo de Enlaces Inteligentes Efímeros (Smart Link Handshake)
Formato estándar: base64url(payload).base64url(firma_hmac_sha256)
"""
import hmac
import hashlib
import time
import json
import base64
import os

SECRET_KEY = os.getenv("SMART_LINK_SECRET", "capa-seguros-pilot-secret-2026").encode('utf-8')

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def b64url_decode(data_str: str) -> bytes:
    padded = data_str + "=" * ((4 - len(data_str) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode('utf-8'))

def generar_smart_link(poliza_id: str, dni: str, canal: str = "gemini", ttl_segundos: int = 86400) -> dict:
    expiracion = int(time.time()) + ttl_segundos
    payload = {
        "poliza_id": str(poliza_id),
        "dni": str(dni),
        "canal_destino": canal,
        "exp": expiracion
    }
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    firma = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    
    token = f"{b64url_encode(payload_bytes)}.{b64url_encode(firma)}"
    
    deep_link = (
        f"https://gemini.google.com/gem/capa-seguros?auth_token={token}"
        if canal == "gemini"
        else f"https://chatgpt.com/g/g-capa-seguros?auth_token={token}"
    )
    
    return {
        "token": token,
        "expira_en_unix": expiracion,
        "url_activacion": f"https://capa.link/a/{token}",
        "deep_link_llm": deep_link
    }

def validar_smart_link(token: str) -> dict:
    try:
        if "." not in token:
            return {"valido": False, "error": "Formato de token inválido"}
            
        payload_part, firma_part = token.split(".", 1)
        payload_bytes = b64url_decode(payload_part)
        firma = b64url_decode(firma_part)
        
        firma_esperada = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(firma, firma_esperada):
            return {"valido": False, "error": "Firma criptográfica inválida"}
            
        data = json.loads(payload_bytes.decode('utf-8'))
        if time.time() > data["exp"]:
            return {"valido": False, "error": "El enlace ha expirado"}
            
        return {"valido": True, "datos": data}
    except Exception as e:
        return {"valido": False, "error": f"Token corrupto o malformado: {str(e)}"}
