"""Rutas del estudiante: conversación con el asistente, tamizaje voluntario,
verificación directa y aceptación de la derivación.

Aquí se coordinan las dos capas. Cada capa usa su propia sesión de base de datos
(con su propio rol de PostgreSQL); la capa académica nunca recibe información
de la capa de canalización, solo el texto que el propio estudiante escribió.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.academico.asistente import responder
from app.api.esquemas import (AceptacionDerivacion, Accion, ConversacionSalida, MensajeEntrada,
                              MensajeSalida, NuevaConversacion, RechazoOferta, RespuestaChat,
                              TamizajeEntrada, VerificacionEntrada)
from app.canalizacion import servicio as canalizacion
from app.canalizacion.servicio import recursos_activos
from app.canalizacion.tamizaje import instrumentos
from app.db import sesion_academica, sesion_nucleo
from app.ia.proveedores import obtener_proveedor
from app.modelos import Conversacion, Mensaje, SolicitudDerivacion, Usuario
from app.seguridad.acceso import UsuarioActual, requiere_permiso
from app.seguridad.proteccion import cifrador_mensajes, cifrador_nucleo, depurar_identificadores
from app.solicitudes.servicio import TransicionInvalida, cambiar_estado

log = logging.getLogger("saac.estudiante")
router = APIRouter(prefix="/api/estudiante", tags=["estudiante"])

ESTUDIANTE = requiere_permiso("conversacion:propia")

# Acciones en las que el asistente académico NO responde: la plataforma muestra
# únicamente el mensaje fijo de la capa de canalización.
ACCIONES_SIN_RESPUESTA_IA = {"PROTOCOLO_RIESGO", "VERIFICAR_RIESGO"}

AVISO_SIN_SERVICIO = ("El asistente no está disponible en este momento. Si necesitas apoyo, "
                      "puedes acudir a estos servicios:")


def _conversacion_propia(sesion: Session, conversacion_id: uuid.UUID, seudonimo: str
                         ) -> Conversacion:
    conv = sesion.get(Conversacion, conversacion_id)
    if conv is None or conv.seudonimo != seudonimo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada")
    return conv


def _salida(m: Mensaje) -> MensajeSalida:
    return MensajeSalida(id=m.id, autor=m.autor,
                         contenido=cifrador_mensajes().descifrar(m.contenido_cifrado),
                         fuentes=m.fuentes or [], creado_en=m.creado_en)


@router.get("/conversaciones", response_model=list[ConversacionSalida])
def listar_conversaciones(usuario: UsuarioActual = Depends(ESTUDIANTE),
                          s_acad: Session = Depends(sesion_academica)):
    return list(s_acad.scalars(select(Conversacion).where(Conversacion.seudonimo == usuario.seudonimo)
                               .order_by(Conversacion.actualizada_en.desc())))


@router.post("/conversaciones", response_model=ConversacionSalida, status_code=201)
def crear_conversacion(datos: NuevaConversacion, usuario: UsuarioActual = Depends(ESTUDIANTE),
                       s_acad: Session = Depends(sesion_academica)):
    conv = Conversacion(seudonimo=usuario.seudonimo, titulo=datos.titulo or "Nueva conversación")
    s_acad.add(conv)
    s_acad.flush()
    s_acad.refresh(conv)
    return conv


@router.get("/conversaciones/{conversacion_id}/mensajes", response_model=list[MensajeSalida])
def listar_mensajes(conversacion_id: uuid.UUID, usuario: UsuarioActual = Depends(ESTUDIANTE),
                    s_acad: Session = Depends(sesion_academica)):
    conv = _conversacion_propia(s_acad, conversacion_id, usuario.seudonimo)
    return [_salida(m) for m in conv.mensajes]


@router.post("/conversaciones/{conversacion_id}/mensajes", response_model=RespuestaChat)
def enviar_mensaje(conversacion_id: uuid.UUID, datos: MensajeEntrada,
                   usuario: UsuarioActual = Depends(ESTUDIANTE),
                   s_acad: Session = Depends(sesion_academica),
                   s_nucleo: Session = Depends(sesion_nucleo)) -> RespuestaChat:
    proveedor = obtener_proveedor()
    cif = cifrador_mensajes()
    conv = _conversacion_propia(s_acad, conversacion_id, usuario.seudonimo)
    previos = list(conv.mensajes)

    # 1. Guardar el mensaje del estudiante (capa académica, cifrado)
    msg = Mensaje(conversacion_id=conv.id, autor="ESTUDIANTE", contenido_cifrado=cif.cifrar(datos.texto))
    s_acad.add(msg)
    if conv.titulo == "Nueva conversación":
        conv.titulo = datos.texto[:60] + ("…" if len(datos.texto) > 60 else "")
    conv.actualizada_en = datetime.now(UTC)
    s_acad.flush()

    # 2. Evaluar el mensaje en la capa de canalización (ANTES de generar la respuesta)
    persona = s_nucleo.scalar(select(Usuario).where(Usuario.seudonimo == usuario.seudonimo))
    nombres = [cifrador_nucleo().descifrar(persona.nombre_cifrado)] if persona else []
    try:
        decision = canalizacion.evaluar_mensaje(
            s_nucleo, proveedor, seudonimo=usuario.seudonimo, conversacion_id=conv.id,
            mensaje_id=msg.id, texto=datos.texto, nombres=nombres)
        accion = Accion(tipo=decision.accion, texto=decision.texto, recursos=decision.recursos,
                        solicitud_codigo=decision.solicitud_codigo)
    except Exception:  # noqa: BLE001 - degradación segura
        log.exception("Fallo en la capa de canalización; se muestran los recursos de apoyo")
        s_nucleo.rollback()
        accion = Accion(tipo="FALLA_SEGURA", texto=None,
                        recursos=recursos_activos(s_nucleo, {"EMERGENCIA", "LINEA_APOYO",
                                                             "INSTITUCIONAL"}))

    # 3. Respuesta del asistente académico (solo si la acción lo permite)
    respuesta = None
    if accion.tipo not in ACCIONES_SIN_RESPUESTA_IA:
        historial = []
        for m in previos:
            texto, _ = depurar_identificadores(cif.descifrar(m.contenido_cifrado), nombres)
            historial.append({"role": "user" if m.autor == "ESTUDIANTE" else "assistant",
                              "content": texto})
        consulta, _ = depurar_identificadores(datos.texto, nombres)
        r = responder(s_acad, proveedor, historial, consulta)
        respuesta = Mensaje(conversacion_id=conv.id, autor="ASISTENTE",
                            contenido_cifrado=cif.cifrar(r.texto), fuentes=r.fuentes)
        s_acad.add(respuesta)
        s_acad.flush()
        if r.degradada and not accion.recursos:
            # Falla segura (RNF-05): si el servicio de modelos no responde, se muestran
            # los recursos de apoyo junto con la respuesta degradada.
            accion.recursos = recursos_activos(s_nucleo, {"EMERGENCIA", "LINEA_APOYO",
                                                          "INSTITUCIONAL"})
            accion.texto = accion.texto or AVISO_SIN_SERVICIO

    return RespuestaChat(mensaje_estudiante=_salida(msg),
                         respuesta=_salida(respuesta) if respuesta else None, accion=accion)


@router.get("/instrumentos/{instrumento}")
def obtener_instrumento(instrumento: str, _: UsuarioActual = Depends(ESTUDIANTE)) -> dict:
    try:
        return instrumentos().definicion(instrumento.upper())
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/tamizajes", response_model=Accion)
def responder_tamizaje(datos: TamizajeEntrada,
                       usuario: UsuarioActual = Depends(requiere_permiso("tamizaje:responder")),
                       s_nucleo: Session = Depends(sesion_nucleo)) -> Accion:
    entradas = [(i, r) for i, r in (("PHQ9", datos.phq9), ("GAD7", datos.gad7)) if r is not None]
    if not entradas:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Envíe al menos un instrumento")
    try:
        resultados = [(instrumentos().calificar(i, r), r) for i, r in entradas]
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    d = canalizacion.evaluar_tamizaje(s_nucleo, seudonimo=usuario.seudonimo, resultados=resultados)
    texto = d.texto or ("Gracias por responder. Puedes seguir conversando conmigo sobre tus "
                        "estudios cuando quieras.")
    return Accion(tipo=d.accion, texto=texto, recursos=d.recursos,
                  solicitud_codigo=d.solicitud_codigo)


@router.post("/verificacion", response_model=Accion)
def responder_verificacion(datos: VerificacionEntrada, usuario: UsuarioActual = Depends(ESTUDIANTE),
                           s_nucleo: Session = Depends(sesion_nucleo)) -> Accion:
    d = canalizacion.evaluar_verificacion(s_nucleo, seudonimo=usuario.seudonimo,
                                          respuesta=datos.respuesta)
    return Accion(tipo=d.accion, texto=d.texto, recursos=d.recursos,
                  solicitud_codigo=d.solicitud_codigo)


@router.post("/ofertas/rechazo", status_code=204, response_model=None)
def rechazar_oferta(datos: RechazoOferta, usuario: UsuarioActual = Depends(ESTUDIANTE),
                    s_nucleo: Session = Depends(sesion_nucleo)) -> None:
    canalizacion.rechazar_oferta(s_nucleo, usuario.seudonimo, datos.tipo)


@router.post("/solicitudes", status_code=201)
def aceptar_derivacion(datos: AceptacionDerivacion,
                       usuario: UsuarioActual = Depends(requiere_permiso("solicitud:crear_propia")),
                       s_nucleo: Session = Depends(sesion_nucleo)) -> dict:
    if not datos.consiento_contacto:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Se requiere su consentimiento explícito")
    try:
        solicitud = canalizacion.aceptar_derivacion(
            s_nucleo, seudonimo=usuario.seudonimo, preferencia=datos.preferencia,
            telefono=datos.telefono, disponibilidad=datos.disponibilidad, nota=datos.nota)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"codigo": solicitud.codigo, "estado": solicitud.estado}


@router.post("/solicitudes/{codigo}/cancelar")
def cancelar_solicitud(codigo: str,
                       usuario: UsuarioActual = Depends(requiere_permiso("solicitud:ver_propia")),
                       s_nucleo: Session = Depends(sesion_nucleo)) -> dict:
    s = s_nucleo.scalar(select(SolicitudDerivacion).where(SolicitudDerivacion.codigo == codigo))
    if s is None or s.seudonimo != usuario.seudonimo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if s.categoria == "C3":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Las solicitudes por señales de riesgo no se pueden cancelar")
    try:
        cambiar_estado(s_nucleo, s, "CANCELADA", None, "Cancelada por el estudiante")
    except TransicionInvalida as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"codigo": s.codigo, "estado": s.estado}


@router.get("/solicitudes")
def mis_solicitudes(usuario: UsuarioActual = Depends(requiere_permiso("solicitud:ver_propia")),
                    s_nucleo: Session = Depends(sesion_nucleo)) -> list[dict]:
    filas = s_nucleo.scalars(select(SolicitudDerivacion)
                             .where(SolicitudDerivacion.seudonimo == usuario.seudonimo)
                             .order_by(SolicitudDerivacion.creada_en.desc()))
    return [{"codigo": s.codigo, "estado": s.estado, "creada_en": s.creada_en,
             "cancelable": s.estado == "NUEVA" and s.categoria == "C2",
             "actualizada_en": s.actualizada_en,
             "historial": [{"estado": h.estado_nuevo, "fecha": h.creado_en} for h in s.historial]}
            for s in filas]
