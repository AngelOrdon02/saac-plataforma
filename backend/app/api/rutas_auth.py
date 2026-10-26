"""Registro, ingreso y consentimiento informado."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.esquemas import Ingreso, Registro, Token
from app.config import obtener_configuracion
from app.db import sesion_nucleo
from app.modelos import Consentimiento, Usuario
from app.seguridad.acceso import UsuarioActual, crear_token, usuario_actual
from app.seguridad.proteccion import (cifrador_nucleo, generar_seudonimo, hashear_contrasena,
                                      verificar_contrasena)

router = APIRouter(prefix="/api/auth", tags=["autenticación"])

TEXTO_CONSENTIMIENTO = """Consentimiento informado (versión 1.0)

1. Esta plataforma es un apoyo académico. NO realiza diagnósticos ni sustituye la atención de \
un profesional de la salud mental.
2. Tus conversaciones se guardan cifradas y asociadas a un seudónimo. Ni el personal de atención \
psicológica ni el personal técnico pueden leerlas.
3. El sistema analiza tus mensajes para identificar si una dificultad podría requerir apoyo \
profesional. En ese caso te lo ofrecerá, y solo si aceptas se compartirán tus datos de contacto \
con el equipo de atención psicológica de la universidad.
4. Excepción: si tus mensajes muestran señales de riesgo para tu vida o integridad, el sistema \
avisará de inmediato al equipo de atención psicológica y compartirá tus datos de contacto para \
que puedan comunicarse contigo.
5. Puedes solicitar la eliminación de tu cuenta y de tus conversaciones en cualquier momento.
6. Los datos se tratan conforme a la Ley de Acceso a la Información Pública (Decreto 57-2008)."""


@router.get("/consentimiento")
def consentimiento() -> dict:
    cfg = obtener_configuracion()
    return {"version": cfg.version_consentimiento, "texto": TEXTO_CONSENTIMIENTO}


@router.post("/registro", response_model=Token, status_code=status.HTTP_201_CREATED)
def registro(datos: Registro, sesion: Session = Depends(sesion_nucleo)) -> Token:
    cfg = obtener_configuracion()
    if not datos.acepta_consentimiento:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe aceptar el consentimiento informado")
    dominio = datos.correo.split("@")[1].lower()
    if cfg.dominios_correo_permitidos and dominio not in cfg.dominios_correo_permitidos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use su correo institucional")
    if sesion.scalar(select(Usuario).where(Usuario.correo == datos.correo.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    cif = cifrador_nucleo()
    nuevo_id = uuid.uuid4()
    usuario = Usuario(id=nuevo_id, correo=datos.correo.lower(),
                      hash_contrasena=hashear_contrasena(datos.contrasena),
                      nombre_cifrado=cif.cifrar(datos.nombre.strip()),
                      telefono_cifrado=cif.cifrar(datos.telefono) if datos.telefono else None,
                      rol="ESTUDIANTE", seudonimo=generar_seudonimo(nuevo_id))
    sesion.add(usuario)
    sesion.flush()
    sesion.add(Consentimiento(usuario_id=usuario.id, version=cfg.version_consentimiento,
                              hash_texto=hashlib.sha256(TEXTO_CONSENTIMIENTO.encode()).hexdigest()))
    return Token(token=crear_token(usuario.id, usuario.rol, usuario.seudonimo), rol=usuario.rol,
                 nombre=datos.nombre.strip())


@router.post("/ingreso", response_model=Token)
def ingreso(datos: Ingreso, sesion: Session = Depends(sesion_nucleo)) -> Token:
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == datos.correo.lower()))
    if not usuario or not usuario.activo or not verificar_contrasena(usuario.hash_contrasena,
                                                                     datos.contrasena):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    usuario.ultimo_acceso = datetime.now(UTC)
    nombre = cifrador_nucleo().descifrar(usuario.nombre_cifrado)
    return Token(token=crear_token(usuario.id, usuario.rol, usuario.seudonimo), rol=usuario.rol,
                 nombre=nombre)


@router.get("/yo")
def yo(usuario: UsuarioActual = Depends(usuario_actual)) -> dict:
    return {"rol": usuario.rol, "seudonimo": usuario.seudonimo}
