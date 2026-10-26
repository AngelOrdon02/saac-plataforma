"""Base de conocimiento: indexación y recuperación (generación aumentada por
recuperación, Lewis et al., 2020).

Cada documento de ``backend/conocimiento`` es un archivo Markdown con un
encabezado YAML (clave, título, tema y referencia bibliográfica). El indexador
lo divide en fragmentos, calcula sus embeddings y los guarda en PostgreSQL con
pgvector. Solo se reindexa un documento cuando cambia su contenido.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.ia.proveedores import ProveedorIA
from app.modelos import DocumentoConocimiento, FragmentoConocimiento

MAX_CARACTERES_FRAGMENTO = 900


@dataclass
class DocumentoFuente:
    clave: str
    titulo: str
    tema: str
    referencia: str
    cuerpo: str

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.cuerpo.encode()).hexdigest()


@dataclass
class FragmentoRecuperado:
    clave: str
    titulo: str
    referencia: str
    contenido: str
    similitud: float


def leer_documento(ruta: Path) -> DocumentoFuente:
    texto = ruta.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, flags=re.S)
    if not m:
        raise ValueError(f"{ruta.name}: falta el encabezado YAML")
    meta = yaml.safe_load(m.group(1))
    return DocumentoFuente(meta["clave"], meta["titulo"], meta["tema"], meta["referencia"],
                           m.group(2).strip())


def fragmentar(cuerpo: str, maximo: int = MAX_CARACTERES_FRAGMENTO) -> list[str]:
    """Divide por párrafos y agrupa párrafos consecutivos hasta ``maximo``
    caracteres. Los títulos Markdown se conservan como contexto del fragmento."""
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", cuerpo) if p.strip()]
    fragmentos: list[str] = []
    actual = ""
    titulo_seccion = ""
    for p in parrafos:
        if p.startswith("#"):
            titulo_seccion = p.lstrip("# ").strip()
            continue
        bloque = f"{titulo_seccion}. {p}" if titulo_seccion and not actual else p
        if actual and len(actual) + len(bloque) + 1 > maximo:
            fragmentos.append(actual)
            actual = f"{titulo_seccion}. {p}" if titulo_seccion else p
        else:
            actual = f"{actual}\n{bloque}" if actual else bloque
    if actual:
        fragmentos.append(actual)
    return fragmentos


def indexar_directorio(sesion: Session, proveedor: ProveedorIA, directorio: Path | None = None
                       ) -> dict[str, int]:
    directorio = directorio or obtener_configuracion().ruta_conocimiento
    resumen = {"nuevos": 0, "actualizados": 0, "sin_cambios": 0, "fragmentos": 0}
    for ruta in sorted(directorio.glob("*.md")):
        doc = leer_documento(ruta)
        existente = sesion.scalar(select(DocumentoConocimiento).where(
            DocumentoConocimiento.clave == doc.clave))
        if existente and existente.hash_contenido == doc.hash:
            resumen["sin_cambios"] += 1
            continue
        textos = fragmentar(doc.cuerpo)
        vectores = proveedor.embeber([f"{doc.titulo}. {t}" for t in textos])
        if existente:
            existente.fragmentos.clear()
            sesion.flush()
            registro = existente
            resumen["actualizados"] += 1
        else:
            registro = DocumentoConocimiento(clave=doc.clave)
            sesion.add(registro)
            resumen["nuevos"] += 1
        registro.titulo, registro.tema, registro.referencia = doc.titulo, doc.tema, doc.referencia
        registro.hash_contenido = doc.hash
        registro.fragmentos = [FragmentoConocimiento(orden=i, contenido=t, embedding=v)
                               for i, (t, v) in enumerate(zip(textos, vectores, strict=True))]
        resumen["fragmentos"] += len(textos)
    sesion.flush()
    return resumen


def buscar(sesion: Session, proveedor: ProveedorIA, consulta: str, k: int | None = None,
           similitud_minima: float | None = None) -> list[FragmentoRecuperado]:
    """Recupera los ``k`` fragmentos más similares a la consulta (distancia de
    coseno con el índice HNSW de pgvector)."""
    cfg = obtener_configuracion()
    k = k or cfg.rag_k
    minimo = cfg.rag_similitud_minima if similitud_minima is None else similitud_minima
    if proveedor.nombre == "simulado":
        # Los embeddings por hashing producen similitudes más bajas que un modelo real.
        minimo = min(minimo, 0.10)
    vector = proveedor.embeber([consulta])[0]
    distancia = FragmentoConocimiento.embedding.cosine_distance(vector).label("distancia")
    filas = sesion.execute(
        select(FragmentoConocimiento, DocumentoConocimiento, distancia)
        .join(DocumentoConocimiento)
        .order_by(distancia)
        .limit(k)
    ).all()
    return [FragmentoRecuperado(doc.clave, doc.titulo, doc.referencia, frag.contenido, 1 - dist)
            for frag, doc, dist in filas if 1 - dist >= minimo]
