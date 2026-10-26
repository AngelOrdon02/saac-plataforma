"""Módulo de gestión de solicitudes de derivación.

El ciclo de vida de una solicitud es una máquina de estados explícita (figura
13 del documento). Cada transición válida queda registrada en el historial con
su autor y fecha; las transiciones no previstas se rechazan.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modelos import HistorialEstado, SolicitudDerivacion
from app.seguridad.proteccion import cifrador_nucleo

ESTADOS_ACTIVOS = {"NUEVA", "EN_REVISION", "CONTACTADO", "AGENDADA", "NO_LOCALIZADO"}
ESTADOS_FINALES = {"FINALIZADA", "CANCELADA"}

# Tabla 20 del documento
TRANSICIONES: dict[str, set[str]] = {
    "NUEVA": {"EN_REVISION", "CANCELADA"},
    "EN_REVISION": {"CONTACTADO", "NO_LOCALIZADO", "FINALIZADA"},
    "CONTACTADO": {"AGENDADA", "FINALIZADA"},
    "NO_LOCALIZADO": {"CONTACTADO", "FINALIZADA"},
    "AGENDADA": {"FINALIZADA", "NO_LOCALIZADO"},
    "FINALIZADA": set(),
    "CANCELADA": set(),
}

ORDEN_PRIORIDAD = {"CRITICA": 0, "ALTA": 1, "NORMAL": 2}
ORDEN_ESTADOS = ["NUEVA", "EN_REVISION", "CONTACTADO", "AGENDADA", "NO_LOCALIZADO", "FINALIZADA",
                 "CANCELADA"]
# Solo el propio estudiante puede cancelar su solicitud (mientras siga NUEVA).
ESTADOS_SOLO_ESTUDIANTE = {"CANCELADA"}


def transiciones_personal(estado: str) -> list[str]:
    return [e for e in ORDEN_ESTADOS
            if e in TRANSICIONES.get(estado, set()) and e not in ESTADOS_SOLO_ESTUDIANTE]


class TransicionInvalida(ValueError):
    pass


def _siguiente_codigo(sesion: Session) -> str:
    numero = sesion.scalar(text("SELECT nextval('canalizacion.seq_solicitud')"))
    return f"SOL-{datetime.now(UTC).year}-{numero:04d}"


def crear_solicitud(sesion: Session, *, seudonimo: str, evaluacion_id: uuid.UUID, categoria: str,
                    prioridad: str, resumen: dict, contacto: dict, nota: str | None = None
                    ) -> SolicitudDerivacion:
    cifrador = cifrador_nucleo()
    solicitud = SolicitudDerivacion(
        codigo=_siguiente_codigo(sesion), seudonimo=seudonimo, evaluacion_id=evaluacion_id,
        categoria=categoria, prioridad=prioridad, estado="NUEVA", resumen=resumen,
        contacto_cifrado=cifrador.cifrar_json(contacto),
        nota_cifrada=cifrador.cifrar(nota) if nota else None)
    sesion.add(solicitud)
    sesion.flush()
    sesion.add(HistorialEstado(solicitud_id=solicitud.id, estado_anterior=None,
                               estado_nuevo="NUEVA", actor_id=None))
    sesion.flush()
    return solicitud


def solicitud_activa(sesion: Session, seudonimo: str) -> SolicitudDerivacion | None:
    return sesion.scalar(select(SolicitudDerivacion)
                         .where(SolicitudDerivacion.seudonimo == seudonimo,
                                SolicitudDerivacion.estado.in_(ESTADOS_ACTIVOS))
                         .order_by(SolicitudDerivacion.creada_en.desc()).limit(1))


def cambiar_estado(sesion: Session, solicitud: SolicitudDerivacion, nuevo: str,
                   actor_id: uuid.UUID | None, comentario: str | None = None) -> SolicitudDerivacion:
    if nuevo not in TRANSICIONES.get(solicitud.estado, set()):
        raise TransicionInvalida(f"No se permite pasar de {solicitud.estado} a {nuevo}")
    anterior = solicitud.estado
    solicitud.estado = nuevo
    solicitud.actualizada_en = datetime.now(UTC)
    if nuevo in ESTADOS_FINALES:
        solicitud.cerrada_en = solicitud.actualizada_en
    if actor_id and solicitud.asignada_a is None and nuevo == "EN_REVISION":
        solicitud.asignada_a = actor_id
    sesion.add(HistorialEstado(
        solicitud_id=solicitud.id, estado_anterior=anterior, estado_nuevo=nuevo, actor_id=actor_id,
        comentario_cifrado=cifrador_nucleo().cifrar(comentario) if comentario else None))
    sesion.flush()
    return solicitud


def bandeja(sesion: Session, estado: str | None = None, prioridad: str | None = None,
            incluir_cerradas: bool = False) -> list[SolicitudDerivacion]:
    consulta = select(SolicitudDerivacion)
    if estado:
        consulta = consulta.where(SolicitudDerivacion.estado == estado)
    elif not incluir_cerradas:
        consulta = consulta.where(SolicitudDerivacion.estado.in_(ESTADOS_ACTIVOS))
    if prioridad:
        consulta = consulta.where(SolicitudDerivacion.prioridad == prioridad)
    solicitudes = list(sesion.scalars(consulta))
    # Primero la prioridad; dentro de la misma prioridad, la más antigua primero.
    solicitudes.sort(key=lambda s: (ORDEN_PRIORIDAD[s.prioridad], s.creada_en))
    return solicitudes


def conteo_por_estado(sesion: Session) -> dict[str, int]:
    filas = sesion.execute(select(SolicitudDerivacion.estado, func.count())
                           .group_by(SolicitudDerivacion.estado)).all()
    return {e: n for e, n in filas}
