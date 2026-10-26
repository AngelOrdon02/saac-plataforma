"""Rutas del personal de atención psicológica: bandeja de solicitudes, detalle,
cambios de estado y notificaciones. Cada consulta de datos de contacto y cada
cambio de estado queda registrado en la bitácora de accesos."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.esquemas import CambioEstado
from app.auditoria.bitacora import registrar_acceso
from app.db import sesion_nucleo
from app.modelos import Notificacion, SolicitudDerivacion, Usuario
from app.seguridad.acceso import UsuarioActual, ip_cliente, requiere_permiso
from app.seguridad.proteccion import cifrador_nucleo
from app.solicitudes.servicio import (TransicionInvalida, bandeja, cambiar_estado,
                                      transiciones_personal)

router = APIRouter(prefix="/api/atencion", tags=["personal de atención"])


def _fila(s: SolicitudDerivacion) -> dict:
    return {"id": s.id, "codigo": s.codigo, "categoria": s.categoria, "prioridad": s.prioridad,
            "estado": s.estado, "creada_en": s.creada_en, "actualizada_en": s.actualizada_en,
            "regla": s.resumen.get("regla"), "nombre_regla": s.resumen.get("nombre_regla"),
            "asignada_a": s.asignada_a}


@router.get("/solicitudes")
def listar(estado: str | None = None, prioridad: str | None = None, incluir_cerradas: bool = False,
           _: UsuarioActual = Depends(requiere_permiso("solicitudes:listar")),
           sesion: Session = Depends(sesion_nucleo)) -> list[dict]:
    return [_fila(s) for s in bandeja(sesion, estado, prioridad, incluir_cerradas)]


@router.get("/solicitudes/{solicitud_id}")
def detalle(solicitud_id: uuid.UUID, request: Request,
            usuario: UsuarioActual = Depends(requiere_permiso("solicitudes:ver_contacto")),
            sesion: Session = Depends(sesion_nucleo)) -> dict:
    s = sesion.get(SolicitudDerivacion, solicitud_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    cif = cifrador_nucleo()
    registrar_acceso(sesion, usuario_id=usuario.id, rol=usuario.rol, accion="VER_CONTACTO",
                     recurso="solicitud_derivacion", recurso_id=s.codigo,
                     direccion_ip=ip_cliente(request))
    nombres = {u.id: cif.descifrar(u.nombre_cifrado) for u in sesion.scalars(
        select(Usuario).where(Usuario.rol.in_(["ATENCION", "ADMIN"])))}
    return {
        **_fila(s),
        "resumen": s.resumen,
        "contacto": cif.descifrar_json(s.contacto_cifrado),
        "nota": cif.descifrar(s.nota_cifrada) if s.nota_cifrada else None,
        "transiciones_permitidas": transiciones_personal(s.estado),
        "historial": [{"estado_anterior": h.estado_anterior, "estado_nuevo": h.estado_nuevo,
                       "actor": nombres.get(h.actor_id, "Sistema") if h.actor_id else "Sistema",
                       "comentario": cif.descifrar(h.comentario_cifrado)
                       if h.comentario_cifrado else None,
                       "fecha": h.creado_en} for h in s.historial],
    }


@router.post("/solicitudes/{solicitud_id}/estado")
def actualizar_estado(solicitud_id: uuid.UUID, datos: CambioEstado, request: Request,
                      usuario: UsuarioActual = Depends(requiere_permiso("solicitudes:cambiar_estado")),
                      sesion: Session = Depends(sesion_nucleo)) -> dict:
    s = sesion.get(SolicitudDerivacion, solicitud_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if datos.estado not in transiciones_personal(s.estado):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"No se permite pasar de {s.estado} a {datos.estado}")
    try:
        cambiar_estado(sesion, s, datos.estado, usuario.id, datos.comentario)
    except TransicionInvalida as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    registrar_acceso(sesion, usuario_id=usuario.id, rol=usuario.rol, accion="CAMBIAR_ESTADO",
                     recurso="solicitud_derivacion", recurso_id=f"{s.codigo}:{datos.estado}",
                     direccion_ip=ip_cliente(request))
    return _fila(s)


@router.get("/notificaciones")
def notificaciones(usuario: UsuarioActual = Depends(requiere_permiso("notificaciones:ver")),
                   sesion: Session = Depends(sesion_nucleo)) -> list[dict]:
    filas = sesion.scalars(select(Notificacion).where(
        Notificacion.destinatario_id == usuario.id, Notificacion.canal == "APP")
        .order_by(Notificacion.creada_en.desc()).limit(30))
    return [{"id": n.id, "asunto": n.asunto, "creada_en": n.creada_en, "leida": n.leida_en is not None,
             "solicitud_id": n.solicitud_id} for n in filas]


@router.post("/notificaciones/{notificacion_id}/leida", status_code=204, response_model=None)
def marcar_leida(notificacion_id: int,
                 usuario: UsuarioActual = Depends(requiere_permiso("notificaciones:ver")),
                 sesion: Session = Depends(sesion_nucleo)) -> None:
    n = sesion.get(Notificacion, notificacion_id)
    if n and n.destinatario_id == usuario.id and n.leida_en is None:
        n.leida_en = datetime.now(UTC)
