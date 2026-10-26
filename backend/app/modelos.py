"""Modelos objeto-relacionales (SQLAlchemy 2.0).

Reflejan las tablas definidas en ``db/migraciones``. El esquema de cada tabla
indica a qué capa pertenece.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (ARRAY, BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger,
                        String, Text, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# ---------------------------------------------------------------------------
# Esquema identidad
# ---------------------------------------------------------------------------


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    hash_contrasena: Mapped[str] = mapped_column(Text)
    nombre_cifrado: Mapped[str] = mapped_column(Text)
    telefono_cifrado: Mapped[str | None] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(20))
    seudonimo: Mapped[str] = mapped_column(String(24), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consentimiento(Base):
    __tablename__ = "consentimiento"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identidad.usuario.id"))
    version: Mapped[str] = mapped_column(String(20))
    hash_texto: Mapped[str] = mapped_column(String(64))
    aceptado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Esquema academico
# ---------------------------------------------------------------------------


class Conversacion(Base):
    __tablename__ = "conversacion"
    __table_args__ = {"schema": "academico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seudonimo: Mapped[str] = mapped_column(String(24))
    titulo: Mapped[str] = mapped_column(String(120), default="Nueva conversación")
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mensajes: Mapped[list[Mensaje]] = relationship(back_populates="conversacion",
                                                   order_by="Mensaje.creado_en")


class Mensaje(Base):
    __tablename__ = "mensaje"
    __table_args__ = {"schema": "academico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academico.conversacion.id"))
    autor: Mapped[str] = mapped_column(String(12))
    contenido_cifrado: Mapped[str] = mapped_column(Text)
    fuentes: Mapped[list] = mapped_column(JSONB, default=list)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversacion: Mapped[Conversacion] = relationship(back_populates="mensajes")


class DocumentoConocimiento(Base):
    __tablename__ = "documento_conocimiento"
    __table_args__ = {"schema": "academico"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(60), unique=True)
    titulo: Mapped[str] = mapped_column(String(200))
    tema: Mapped[str] = mapped_column(String(40))
    referencia: Mapped[str] = mapped_column(Text)
    hash_contenido: Mapped[str] = mapped_column(String(64))
    indexado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fragmentos: Mapped[list[FragmentoConocimiento]] = relationship(
        back_populates="documento", cascade="all, delete-orphan")


class FragmentoConocimiento(Base):
    __tablename__ = "fragmento_conocimiento"
    __table_args__ = {"schema": "academico"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("academico.documento_conocimiento.id"))
    orden: Mapped[int] = mapped_column(Integer)
    contenido: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024))

    documento: Mapped[DocumentoConocimiento] = relationship(back_populates="fragmentos")


# ---------------------------------------------------------------------------
# Esquema canalizacion
# ---------------------------------------------------------------------------


class Indicador(Base):
    __tablename__ = "indicador"
    __table_args__ = {"schema": "canalizacion"}

    codigo: Mapped[str] = mapped_column(String(8), primary_key=True)
    dominio: Mapped[str] = mapped_column(String(12))
    referencia: Mapped[str] = mapped_column(String(60))
    descripcion: Mapped[str] = mapped_column(String(200))
    compartido: Mapped[bool] = mapped_column(Boolean, default=False)


class Evaluacion(Base):
    __tablename__ = "evaluacion"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seudonimo: Mapped[str] = mapped_column(String(24))
    conversacion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    mensaje_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    origen: Mapped[str] = mapped_column(String(12))
    nivel_riesgo: Mapped[int] = mapped_column(SmallInteger, default=0)
    categoria: Mapped[str] = mapped_column(String(2))
    accion: Mapped[str] = mapped_column(String(30))
    reglas_aplicadas: Mapped[dict] = mapped_column(JSONB)
    version_reglas: Mapped[str] = mapped_column(String(20))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Senal(Base):
    __tablename__ = "senal"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canalizacion.evaluacion.id"))
    seudonimo: Mapped[str] = mapped_column(String(24))
    indicador_codigo: Mapped[str] = mapped_column(ForeignKey("canalizacion.indicador.codigo"))
    origen: Mapped[str] = mapped_column(String(10))
    detectada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tamizaje(Base):
    __tablename__ = "tamizaje"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seudonimo: Mapped[str] = mapped_column(String(24))
    instrumento: Mapped[str] = mapped_column(String(6))
    respuestas: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    puntaje_total: Mapped[int] = mapped_column(SmallInteger)
    severidad: Mapped[str] = mapped_column(String(25))
    aplicado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Oferta(Base):
    __tablename__ = "oferta"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seudonimo: Mapped[str] = mapped_column(String(24))
    tipo: Mapped[str] = mapped_column(String(12))
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canalizacion.evaluacion.id"))
    respuesta: Mapped[str] = mapped_column(String(10), default="PENDIENTE")
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    respondida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecursoAtencion(Base):
    __tablename__ = "recurso_atencion"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[str] = mapped_column(String(14))
    descripcion: Mapped[str] = mapped_column(Text)
    ubicacion: Mapped[str | None] = mapped_column(String(200))
    horario: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(40))
    enlace: Mapped[str | None] = mapped_column(String(300))
    procedimiento: Mapped[str | None] = mapped_column(Text)
    fuente: Mapped[str | None] = mapped_column(String(300))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class SolicitudDerivacion(Base):
    __tablename__ = "solicitud_derivacion"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(16), unique=True)
    seudonimo: Mapped[str] = mapped_column(String(24))
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canalizacion.evaluacion.id"))
    categoria: Mapped[str] = mapped_column(String(2))
    prioridad: Mapped[str] = mapped_column(String(8))
    estado: Mapped[str] = mapped_column(String(14), default="NUEVA")
    resumen: Mapped[dict] = mapped_column(JSONB)
    contacto_cifrado: Mapped[str] = mapped_column(Text)
    nota_cifrada: Mapped[str | None] = mapped_column(Text)
    asignada_a: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    historial: Mapped[list[HistorialEstado]] = relationship(
        back_populates="solicitud", order_by="HistorialEstado.creado_en")


class HistorialEstado(Base):
    __tablename__ = "historial_estado"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canalizacion.solicitud_derivacion.id"))
    estado_anterior: Mapped[str | None] = mapped_column(String(14))
    estado_nuevo: Mapped[str] = mapped_column(String(14))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    comentario_cifrado: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    solicitud: Mapped[SolicitudDerivacion] = relationship(back_populates="historial")


class Notificacion(Base):
    __tablename__ = "notificacion"
    __table_args__ = {"schema": "canalizacion"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    solicitud_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canalizacion.solicitud_derivacion.id"))
    destinatario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    canal: Mapped[str] = mapped_column(String(6))
    asunto: Mapped[str] = mapped_column(String(200))
    enviada: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    leida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Esquema auditoria
# ---------------------------------------------------------------------------


class BitacoraDecision(Base):
    __tablename__ = "bitacora_decision"
    __table_args__ = {"schema": "auditoria"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    seudonimo: Mapped[str] = mapped_column(String(24))
    origen: Mapped[str] = mapped_column(String(12))
    categoria: Mapped[str] = mapped_column(String(2))
    accion: Mapped[str] = mapped_column(String(30))
    reglas: Mapped[dict] = mapped_column(JSONB)
    evidencias: Mapped[dict] = mapped_column(JSONB)
    version_reglas: Mapped[str] = mapped_column(String(20))
    huella_reglas: Mapped[str] = mapped_column(String(64))
    componente_modelo: Mapped[str | None] = mapped_column(String(80))
    registrado_en: Mapped[str] = mapped_column(String(40))
    hash_anterior: Mapped[str] = mapped_column(String(64))
    hash_actual: Mapped[str] = mapped_column(String(64), unique=True)


class BitacoraAcceso(Base):
    __tablename__ = "bitacora_acceso"
    __table_args__ = {"schema": "auditoria"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    rol: Mapped[str] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    recurso: Mapped[str] = mapped_column(String(40))
    recurso_id: Mapped[str | None] = mapped_column(String(64))
    direccion_ip: Mapped[str | None] = mapped_column(String(45))
    registrado_en: Mapped[str] = mapped_column(String(40))
    hash_anterior: Mapped[str] = mapped_column(String(64))
    hash_actual: Mapped[str] = mapped_column(String(64), unique=True)
