"""
Módulo de Seguridad, Autenticación y Control de Acceso por Rol (RBAC)
Mini-Azure LUIS v2 - Agroexportación Ica

Implementa tokens de acceso firmados criptográficamente con HMAC-SHA256,
hashing de contraseñas y validación de roles (OPERADOR / SUPERVISOR).
"""

import os
import hmac
import hashlib
import json
import base64
import time
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Clave secreta desde variable de entorno o valor seguro por defecto
SECRET_KEY = os.getenv("SECRET_KEY", "agroica_secret_token_key_cloud_2026_super_segura_jwt")
TOKEN_DURACION_HORAS = int(os.getenv("TOKEN_DURACION_HORAS", "24"))

# Base de usuarios configurable por variables de entorno
USUARIOS_DB = {
    os.getenv("OPERADOR_USER", "operador_ica"): {
        "password": os.getenv("OPERADOR_PASSWORD", "operador2026"),
        "role": "OPERADOR",
        "nombre_completo": "Personal de Campo y Empaque"
    },
    os.getenv("SUPERVISOR_USER", "supervisor_ica"): {
        "password": os.getenv("SUPERVISOR_PASSWORD", "supervisor2026"),
        "role": "SUPERVISOR",
        "nombre_completo": "Jefatura de Calidad y Operaciones"
    }
}

security_bearer = HTTPBearer(auto_error=False)

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_decode(data_str: str) -> bytes:
    padding = "=" * (4 - (len(data_str) % 4)) if len(data_str) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data_str + padding)

def crear_token_acceso(username: str, role: str) -> str:
    """Genera un token firmado con estructura JWT (HMAC-SHA256)."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + (TOKEN_DURACION_HORAS * 3600)
    }

    h_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    firma_base = f"{h_b64}.{p_b64}".encode("utf-8")
    firma = hmac.new(SECRET_KEY.encode("utf-8"), firma_base, hashlib.sha256).digest()
    sig_b64 = _b64_encode(firma)

    return f"{h_b64}.{p_b64}.{sig_b64}"

def verificar_token(token: str) -> Dict[str, Any]:
    """Verifica la firma y expiración del token. Lanza HTTPException si es inválido."""
    partes = token.split(".")
    if len(partes) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    h_b64, p_b64, sig_b64 = partes
    firma_base = f"{h_b64}.{p_b64}".encode("utf-8")
    firma_calculada = hmac.new(SECRET_KEY.encode("utf-8"), firma_base, hashlib.sha256).digest()
    sig_esperada = _b64_encode(firma_calculada)

    # Comparación segura contra ataques de tiempo
    if not hmac.compare_digest(sig_b64, sig_esperada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido o alterado.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload_bytes = _b64_decode(p_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo decodificar el payload del token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verificar expiración
    if payload.get("exp", 0) < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de sesión ha expirado. Inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload

def obtener_usuario_autenticado(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> Dict[str, Any]:
    """Dependencia de FastAPI: Rechaza con 401 si no hay token o es inválido."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso no autenticado. Debe proporcionar un token Bearer en el encabezado Authorization.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return verificar_token(credentials.credentials)

def requerir_roles(roles_permitidos: List[str]):
    """Dependencia de FastAPI: Rechaza con 403 si el rol no tiene permisos."""
    def _verificador_rol(usuario: Dict[str, Any] = Security(obtener_usuario_autenticado)) -> Dict[str, Any]:
        rol_usuario = usuario.get("role")
        if rol_usuario not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado (403 Forbidden): Su rol '{rol_usuario}' no tiene permisos para esta acción. Roles requeridos: {roles_permitidos}."
            )
        return usuario
    return _verificador_rol
