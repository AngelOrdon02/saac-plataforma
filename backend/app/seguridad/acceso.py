"""Autenticación (JWT) y autorización por roles (RBAC).

Los permisos se asignan a roles y no a personas (Sandhu et al., 1996). Ningún rol
tiene un permiso para leer conversaciones ajenas: ni el personal de atención ni
el administrador técnico pueden ver lo que un estudiante conversa con el
asistente académico.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import obtener_configuracion

# Matriz de control de acceso (tabla 23 del documento)
PERMISOS: dict[str, set[str]] = {
    "ESTUDIANTE": {
        "conversacion:propia",
        "tamizaje:responder",
        "solicitud:crear_propia",
        "solicitud:ver_propia",
        "recursos:ver",
    },
    "ATENCION": {
        "solicitudes:listar",
        "solicitudes:ver_detalle",
        "solicitudes:ver_contacto",
        "solicitudes:cambiar_estado",
        "notificaciones:ver",
        "recursos:ver",
    },
    "ADMIN": {
        "metricas:ver_agregadas",
        "bitacora:verificar",
        "reglas:ver",
        "usuarios:gestionar_personal",
        "conocimiento:gestionar",
        "recursos:ver",
    },
}

_esquema_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioActual:
    id: uuid.UUID
    rol: str
    seudonimo: str

    def puede(self, permiso: str) -> bool:
        return permiso in PERMISOS.get(self.rol, set())


def crear_token(usuario_id: uuid.UUID, rol: str, seudonimo: str) -> str:
    cfg = obtener_configuracion()
    ahora = datetime.now(UTC)
    carga = {
        "sub": str(usuario_id),
        "rol": rol,
        "seu": seudonimo,      # la capa académica trabaja con el seudónimo, no con el id
        "iat": ahora,
        "exp": ahora + timedelta(minutes=cfg.minutos_expiracion_token),
    }
    return jwt.encode(carga, cfg.clave_jwt, algorithm="HS256")


def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer)
                   ) -> UsuarioActual:
    if credenciales is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Se requiere autenticación")
    try:
        carga = jwt.decode(credenciales.credentials, obtener_configuracion().clave_jwt,
                           algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o vencido") from exc
    return UsuarioActual(id=uuid.UUID(carga["sub"]), rol=carga["rol"], seudonimo=carga["seu"])


def requiere_permiso(permiso: str):
    """Dependencia de FastAPI que exige un permiso concreto."""

    def _verificar(usuario: UsuarioActual = Depends(usuario_actual)) -> UsuarioActual:
        if not usuario.puede(permiso):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta operación")
        return usuario

    return _verificar


def ip_cliente(request: Request) -> str | None:
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else None
