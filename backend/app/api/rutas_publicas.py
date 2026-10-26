"""Rutas públicas y de integración.

* ``/api/recursos``: directorio de recursos de atención (siempre visible).
* ``/api/integracion/conocimiento/*``: búsqueda en la base de conocimiento para
  el prototipo de servidor MCP (``extensiones/mcp-servidor``). Requiere una clave
  de API y solo expone la capa académica; nunca datos de canalización.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.academico.conocimiento import buscar
from app.canalizacion.servicio import recursos_activos
from app.config import obtener_configuracion
from app.db import sesion_academica, sesion_nucleo
from app.ia.proveedores import obtener_proveedor
from app.modelos import DocumentoConocimiento

router = APIRouter(prefix="/api", tags=["público"])


@router.get("/salud")
def salud() -> dict:
    return {"estado": "ok", "proveedor_ia": obtener_proveedor().nombre}


@router.get("/recursos")
def recursos(sesion: Session = Depends(sesion_nucleo)) -> list[dict]:
    return recursos_activos(sesion)


def _clave_integracion(x_clave_api: str | None = Header(default=None)) -> None:
    clave = obtener_configuracion().clave_api_mcp
    if not clave:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integración deshabilitada")
    if x_clave_api != clave:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clave de API inválida")


@router.get("/integracion/conocimiento/buscar", dependencies=[Depends(_clave_integracion)])
def buscar_conocimiento(q: str, k: int = 4, s_acad: Session = Depends(sesion_academica)) -> list[dict]:
    return [{"titulo": f.titulo, "referencia": f.referencia, "contenido": f.contenido,
             "similitud": round(f.similitud, 3)}
            for f in buscar(s_acad, obtener_proveedor(), q[:500], k=min(k, 8))]


@router.get("/integracion/conocimiento/indice", dependencies=[Depends(_clave_integracion)])
def indice_conocimiento(s_acad: Session = Depends(sesion_academica)) -> list[dict]:
    return [{"clave": d.clave, "titulo": d.titulo, "tema": d.tema, "referencia": d.referencia}
            for d in s_acad.scalars(select(DocumentoConocimiento).order_by(DocumentoConocimiento.tema))]
