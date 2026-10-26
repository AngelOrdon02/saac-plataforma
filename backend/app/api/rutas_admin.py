"""Rutas del administrador técnico. Solo ve información agregada y técnica: no
tiene acceso a conversaciones, datos de contacto ni solicitudes individuales."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.academico.conocimiento import indexar_directorio
from app.api.esquemas import NuevoPersonal
from app.auditoria.bitacora import verificar_cadena
from app.canalizacion.deteccion import detector_riesgo, extractor_lexico
from app.canalizacion.motor_reglas import motor_reglas
from app.config import obtener_configuracion
from app.db import sesion_academica, sesion_nucleo
from app.ia.proveedores import obtener_proveedor
from app.modelos import (BitacoraAcceso, BitacoraDecision, DocumentoConocimiento, Evaluacion,
                         FragmentoConocimiento, HistorialEstado, SolicitudDerivacion, Usuario)
from app.seguridad.acceso import UsuarioActual, requiere_permiso
from app.seguridad.proteccion import cifrador_nucleo, generar_seudonimo, hashear_contrasena

router = APIRouter(prefix="/api/admin", tags=["administración"])


def _k(valor: int) -> int | str:
    """Supresión de conteos pequeños (umbral k) para evitar la reidentificación
    a partir de estadísticas (Sweeney, 2002)."""
    k = obtener_configuracion().umbral_k_anonimato
    return valor if valor == 0 or valor >= k else f"<{k}"


@router.get("/metricas")
def metricas(dias: int = 30, _: UsuarioActual = Depends(requiere_permiso("metricas:ver_agregadas")),
             sesion: Session = Depends(sesion_nucleo)) -> dict:
    desde = datetime.now(UTC) - timedelta(days=dias)
    por_categoria = dict(sesion.execute(
        select(Evaluacion.categoria, func.count()).where(Evaluacion.creada_en >= desde)
        .group_by(Evaluacion.categoria)).all())
    por_estado = dict(sesion.execute(
        select(SolicitudDerivacion.estado, func.count()).group_by(SolicitudDerivacion.estado)).all())
    por_prioridad = dict(sesion.execute(
        select(SolicitudDerivacion.prioridad, func.count())
        .group_by(SolicitudDerivacion.prioridad)).all())

    # Tiempo hasta el primer contacto, por prioridad (horas)
    tiempos: dict[str, list[float]] = {}
    for s in sesion.scalars(select(SolicitudDerivacion)):
        contacto = next((h for h in s.historial if h.estado_nuevo == "CONTACTADO"), None)
        if contacto:
            horas = (contacto.creado_en - s.creada_en).total_seconds() / 3600
            tiempos.setdefault(s.prioridad, []).append(horas)
    return {
        "periodo_dias": dias,
        "evaluaciones_por_categoria": {c: _k(por_categoria.get(c, 0)) for c in ("C0", "C1", "C2", "C3")},
        "solicitudes_por_estado": {e: _k(n) for e, n in por_estado.items()},
        "solicitudes_por_prioridad": {p: _k(n) for p, n in por_prioridad.items()},
        "horas_promedio_primer_contacto": {p: round(sum(v) / len(v), 2) for p, v in tiempos.items()
                                           if len(v) >= obtener_configuracion().umbral_k_anonimato},
        "umbral_k": obtener_configuracion().umbral_k_anonimato,
    }


@router.get("/bitacora/verificacion")
def verificar_bitacoras(_: UsuarioActual = Depends(requiere_permiso("bitacora:verificar")),
                        sesion: Session = Depends(sesion_nucleo)) -> dict:
    return {"decisiones": verificar_cadena(sesion, BitacoraDecision),
            "accesos": verificar_cadena(sesion, BitacoraAcceso),
            "verificado_en": datetime.now(UTC)}


@router.get("/bitacora/decisiones")
def ultimas_decisiones(limite: int = 20,
                       _: UsuarioActual = Depends(requiere_permiso("bitacora:verificar")),
                       sesion: Session = Depends(sesion_nucleo)) -> list[dict]:
    filas = sesion.scalars(select(BitacoraDecision).order_by(BitacoraDecision.id.desc())
                           .limit(min(limite, 100)))
    return [{"id": b.id, "registrado_en": b.registrado_en, "origen": b.origen,
             "categoria": b.categoria, "accion": b.accion, "regla": b.reglas.get("regla"),
             "version_reglas": b.version_reglas, "seudonimo": b.seudonimo[:6] + "…",
             "hash": b.hash_actual[:16] + "…"} for b in filas]


@router.get("/reglas")
def reglas_vigentes(_: UsuarioActual = Depends(requiere_permiso("reglas:ver"))) -> dict:
    m = motor_reglas()
    return {"version": m.version, "huella": m.huella, "parametros": m.parametros,
            "reglas": [{"id": r["id"], "nombre": r["nombre"], "categoria": r["categoria"],
                        "accion": r["accion"], "fuentes": r.get("fuentes", [])} for r in m.reglas],
            "lexico_riesgo": {"version": detector_riesgo().version, "huella": detector_riesgo().huella},
            "lexico_indicadores": {"version": extractor_lexico().version,
                                   "huella": extractor_lexico().huella},
            "proveedor_ia": obtener_proveedor().nombre}


@router.get("/personal")
def listar_personal(_: UsuarioActual = Depends(requiere_permiso("usuarios:gestionar_personal")),
                    sesion: Session = Depends(sesion_nucleo)) -> list[dict]:
    cif = cifrador_nucleo()
    return [{"id": u.id, "nombre": cif.descifrar(u.nombre_cifrado), "correo": u.correo,
             "rol": u.rol, "activo": u.activo}
            for u in sesion.scalars(select(Usuario).where(Usuario.rol.in_(["ATENCION", "ADMIN"])))]


@router.post("/personal", status_code=201)
def crear_personal(datos: NuevoPersonal,
                   _: UsuarioActual = Depends(requiere_permiso("usuarios:gestionar_personal")),
                   sesion: Session = Depends(sesion_nucleo)) -> dict:
    if sesion.scalar(select(Usuario).where(Usuario.correo == datos.correo.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    nuevo_id = uuid.uuid4()
    sesion.add(Usuario(id=nuevo_id, correo=datos.correo.lower(),
                       hash_contrasena=hashear_contrasena(datos.contrasena),
                       nombre_cifrado=cifrador_nucleo().cifrar(datos.nombre), rol=datos.rol,
                       seudonimo=generar_seudonimo(nuevo_id)))
    return {"id": nuevo_id}


@router.get("/conocimiento")
def documentos(_: UsuarioActual = Depends(requiere_permiso("conocimiento:gestionar")),
               s_acad: Session = Depends(sesion_academica)) -> list[dict]:
    conteo = dict(s_acad.execute(select(FragmentoConocimiento.documento_id, func.count())
                                 .group_by(FragmentoConocimiento.documento_id)).all())
    return [{"clave": d.clave, "titulo": d.titulo, "tema": d.tema, "referencia": d.referencia,
             "fragmentos": conteo.get(d.id, 0), "indexado_en": d.indexado_en}
            for d in s_acad.scalars(select(DocumentoConocimiento).order_by(DocumentoConocimiento.tema))]


@router.post("/conocimiento/reindexar")
def reindexar(_: UsuarioActual = Depends(requiere_permiso("conocimiento:gestionar")),
              s_acad: Session = Depends(sesion_academica)) -> dict:
    return indexar_directorio(s_acad, obtener_proveedor())
