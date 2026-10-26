"""Bitácoras con encadenamiento de hashes (evidencia de alteración).

Cada registro guarda ``hash_actual = SHA-256(hash_anterior || JSON canónico)``.
Si alguien modificara o eliminara un registro directamente en la base de datos,
la verificación detectaría el punto exacto en que la cadena se rompe (Schneier y
Kelsey, 1999; Kent y Souppaya, 2006). Las tablas, además, tienen disparadores que
impiden UPDATE, DELETE y TRUNCATE.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modelos import BitacoraAcceso, BitacoraDecision

HASH_INICIAL = "0" * 64

CAMPOS = {
    BitacoraDecision: ["evaluacion_id", "seudonimo", "origen", "categoria", "accion", "reglas",
                       "evidencias", "version_reglas", "huella_reglas", "componente_modelo",
                       "registrado_en"],
    BitacoraAcceso: ["usuario_id", "rol", "accion", "recurso", "recurso_id", "direccion_ip",
                     "registrado_en"],
}


def json_canonico(datos: dict[str, Any]) -> str:
    return json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def calcular_hash(hash_anterior: str, datos: dict[str, Any]) -> str:
    return hashlib.sha256((hash_anterior + json_canonico(datos)).encode("utf-8")).hexdigest()


def _registrar(sesion: Session, modelo: type, datos: dict[str, Any]):
    # Serializa las inserciones concurrentes para que la cadena sea lineal.
    sesion.execute(text("SELECT pg_advisory_xact_lock(hashtext(:t))"), {"t": modelo.__tablename__})
    anterior = sesion.scalar(select(modelo.hash_actual).order_by(modelo.id.desc()).limit(1))
    anterior = anterior or HASH_INICIAL
    datos = {k: (str(v) if k.endswith("_id") and v is not None else v) for k, v in datos.items()}
    datos["registrado_en"] = datetime.now(UTC).isoformat(timespec="microseconds")
    registro = modelo(**datos, hash_anterior=anterior, hash_actual=calcular_hash(anterior, datos))
    sesion.add(registro)
    sesion.flush()
    return registro


def registrar_decision(sesion: Session, **datos: Any) -> BitacoraDecision:
    return _registrar(sesion, BitacoraDecision, datos)


def registrar_acceso(sesion: Session, **datos: Any) -> BitacoraAcceso:
    return _registrar(sesion, BitacoraAcceso, datos)


def verificar_cadena(sesion: Session, modelo: type) -> dict[str, Any]:
    """Recorre la bitácora completa y recalcula cada hash."""
    esperado_anterior = HASH_INICIAL
    total = 0
    for registro in sesion.scalars(select(modelo).order_by(modelo.id)):
        datos = {c: getattr(registro, c) for c in CAMPOS[modelo]}
        datos = {k: (str(v) if k.endswith("_id") and v is not None else v) for k, v in datos.items()}
        if registro.hash_anterior != esperado_anterior:
            return {"integra": False, "registros": total, "falla_en_id": registro.id,
                    "motivo": "El enlace con el registro anterior no coincide"}
        if calcular_hash(registro.hash_anterior, datos) != registro.hash_actual:
            return {"integra": False, "registros": total, "falla_en_id": registro.id,
                    "motivo": "El contenido del registro fue alterado"}
        esperado_anterior = registro.hash_actual
        total += 1
    return {"integra": True, "registros": total, "falla_en_id": None, "motivo": None,
            "ultimo_hash": esperado_anterior}
