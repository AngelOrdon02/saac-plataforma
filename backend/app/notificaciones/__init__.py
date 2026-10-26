"""Notificación al personal de atención.

Los avisos (en la aplicación y, si se configura un servidor SMTP, por correo) NO
contienen información del estudiante: solo el código y la prioridad de la
solicitud. El detalle se consulta dentro de la plataforma, donde el acceso queda
registrado en la bitácora.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.modelos import Notificacion, SolicitudDerivacion, Usuario

log = logging.getLogger("saac.notificaciones")


def notificar_nueva_solicitud(sesion: Session, solicitud: SolicitudDerivacion) -> int:
    cfg = obtener_configuracion()
    destinatarios = sesion.scalars(
        select(Usuario).where(Usuario.rol == "ATENCION", Usuario.activo.is_(True))).all()
    asunto = f"[SAAC] Nueva solicitud {solicitud.codigo} · prioridad {solicitud.prioridad}"
    for persona in destinatarios:
        sesion.add(Notificacion(solicitud_id=solicitud.id, destinatario_id=persona.id,
                                canal="APP", asunto=asunto, enviada=True))
        if cfg.smtp_host:
            enviada = _enviar_correo(persona.correo, asunto, solicitud)
            sesion.add(Notificacion(solicitud_id=solicitud.id, destinatario_id=persona.id,
                                    canal="CORREO", asunto=asunto, enviada=enviada))
    sesion.flush()
    return len(destinatarios)


def _enviar_correo(destino: str, asunto: str, solicitud: SolicitudDerivacion) -> bool:
    cfg = obtener_configuracion()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = cfg.smtp_remitente, destino, asunto
    urgencia = ("Esta solicitud corresponde a un ESCALAMIENTO PRIORITARIO. "
                "Atiéndala de inmediato." if solicitud.prioridad != "NORMAL" else "")
    msg.set_content(
        f"Se registró la solicitud {solicitud.codigo} con prioridad {solicitud.prioridad}.\n"
        f"{urgencia}\n\nIngrese a {cfg.url_publica} para revisarla.\n\n"
        "Por protección de datos, este correo no incluye información del estudiante.")
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_puerto, timeout=10) as smtp:
            smtp.send_message(msg)
        return True
    except OSError as exc:
        log.warning("No se pudo enviar el correo de notificación: %s", exc)
        return False
