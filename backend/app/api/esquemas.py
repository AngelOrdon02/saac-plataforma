"""Esquemas de entrada y salida de la API (validación con Pydantic)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Registro(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    correo: EmailStr
    contrasena: str = Field(min_length=10, max_length=128)
    telefono: str | None = Field(default=None, max_length=20)
    acepta_consentimiento: bool


class Ingreso(BaseModel):
    correo: EmailStr
    contrasena: str


class Token(BaseModel):
    token: str
    rol: str
    nombre: str


class NuevaConversacion(BaseModel):
    titulo: str | None = Field(default=None, max_length=120)


class ConversacionSalida(BaseModel):
    id: uuid.UUID
    titulo: str
    actualizada_en: datetime


class MensajeEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class MensajeSalida(BaseModel):
    id: uuid.UUID
    autor: str
    contenido: str
    fuentes: list[dict] = []
    creado_en: datetime


class Accion(BaseModel):
    """Lo que la interfaz debe mostrar además (o en lugar) de la respuesta."""
    tipo: str                    # ACOMPANAMIENTO, OFRECER_TAMIZAJE, PROTOCOLO_RIESGO, ...
    texto: str | None = None
    recursos: list[dict] = []
    solicitud_codigo: str | None = None


class RespuestaChat(BaseModel):
    mensaje_estudiante: MensajeSalida
    respuesta: MensajeSalida | None
    accion: Accion


class TamizajeEntrada(BaseModel):
    """Respuestas a uno o ambos instrumentos; se evalúan juntas en una sola decisión."""
    phq9: list[int] | None = None
    gad7: list[int] | None = None


class VerificacionEntrada(BaseModel):
    respuesta: Literal["SI", "NO", "SIN_RESPUESTA"]


class RechazoOferta(BaseModel):
    tipo: Literal["TAMIZAJE", "DERIVACION"]


class AceptacionDerivacion(BaseModel):
    preferencia: Literal["CORREO", "TELEFONO", "WHATSAPP"]
    telefono: str | None = Field(default=None, max_length=20)
    disponibilidad: str = Field(min_length=3, max_length=200)
    nota: str | None = Field(default=None, max_length=500)
    consiento_contacto: bool


class CambioEstado(BaseModel):
    estado: Literal["EN_REVISION", "CONTACTADO", "AGENDADA", "NO_LOCALIZADO", "FINALIZADA",
                    "CANCELADA"]
    comentario: str | None = Field(default=None, max_length=1000)


class NuevoPersonal(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    correo: EmailStr
    contrasena: str = Field(min_length=10, max_length=128)
    rol: Literal["ATENCION", "ADMIN"]
