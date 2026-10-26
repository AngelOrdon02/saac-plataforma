"""Detección de señales en el texto del estudiante.

* ``DetectorRiesgo``: determinista, basado en un léxico versionado. Se ejecuta
  SIEMPRE y antes que cualquier modelo de lenguaje.
* ``ExtractorLexico``: determinista; asocia expresiones coloquiales a los
  indicadores del catálogo (ítems del PHQ-9 y la GAD-7, deterioro y persistencia).
* ``ExtractorModelo``: usa el modelo de lenguaje como componente de comprensión
  del lenguaje natural y devuelve indicadores en JSON. Solo COMPLEMENTA al léxico:
  sus resultados se validan contra el catálogo y nunca deciden la categoría.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import obtener_configuracion
from app.ia.proveedores import ErrorProveedorIA, ProveedorIA
from app.seguridad.proteccion import normalizar


def huella_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _precedido_por_negacion(texto: str, inicio: int, negaciones: set[str], ventana: int) -> bool:
    """Busca una negación en las ``ventana`` palabras previas, sin cruzar signos de
    puntuación: en "No sé qué hacer. Quiero morirme" la negación pertenece a otra frase."""
    clausula = re.split(r"[.!?;:,]", texto[:inicio])[-1]
    previas = re.findall(r"[a-z0-9ñ]+", clausula)[-ventana:]
    return any(p in negaciones for p in previas)


# ---------------------------------------------------------------------------
# Detector de riesgo
# ---------------------------------------------------------------------------


@dataclass
class ResultadoRiesgo:
    nivel: int = 0                       # 0 = sin señal; 1 a 3 según la gradación
    nombre: str | None = None
    patrones: list[str] = field(default_factory=list)
    requiere_verificacion: bool = False  # señal ambigua o negada


class DetectorRiesgo:
    def __init__(self, ruta: Path):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        self.version: str = datos["version"]
        self.huella = huella_archivo(ruta)
        self._negaciones = set(datos["negaciones"])
        self._ventana = int(datos["ventana_negacion"])
        self._niveles = [(n["nivel"], n["nombre"],
                          [(p["id"], re.compile(p["regex"])) for p in n["patrones"]])
                         for n in datos["niveles"]]
        self._ambiguos = [(p["id"], re.compile(p["regex"])) for p in datos["ambiguos"]]

    def evaluar(self, texto: str) -> ResultadoRiesgo:
        t = normalizar(texto)
        resultado = ResultadoRiesgo()
        for nivel, nombre, patrones in self._niveles:
            for pid, regex in patrones:
                for m in regex.finditer(t):
                    if _precedido_por_negacion(t, m.start(), self._negaciones, self._ventana):
                        # Una negación no descarta el riesgo: se pregunta de forma directa.
                        resultado.requiere_verificacion = True
                        resultado.patrones.append(f"{pid}:negado")
                        continue
                    resultado.patrones.append(pid)
                    if nivel > resultado.nivel:
                        resultado.nivel, resultado.nombre = nivel, nombre
        for pid, regex in self._ambiguos:
            if regex.search(t):
                resultado.requiere_verificacion = True
                resultado.patrones.append(pid)
        if resultado.nivel > 0:
            resultado.requiere_verificacion = False
        return resultado


# ---------------------------------------------------------------------------
# Extractores de indicadores
# ---------------------------------------------------------------------------


@dataclass
class Indicadores:
    lexico: set[str] = field(default_factory=set)
    modelo: set[str] = field(default_factory=set)
    posible_riesgo_modelo: bool = False
    modelo_usado: str | None = None

    @property
    def todos(self) -> set[str]:
        return self.lexico | self.modelo


class ExtractorLexico:
    def __init__(self, ruta: Path):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        self.version: str = datos["version"]
        self.huella = huella_archivo(ruta)
        self._patrones = {codigo: [re.compile(r) for r in regexes]
                          for codigo, regexes in datos["indicadores"].items()}
        self._negaciones = set(datos.get("negaciones", []))
        self._ventana = int(datos.get("ventana_negacion", 2))
        self._sin_negacion = set(datos.get("sin_negacion", []))

    @property
    def codigos(self) -> set[str]:
        return set(self._patrones)

    def extraer(self, texto: str) -> set[str]:
        t = normalizar(texto)
        encontrados: set[str] = set()
        for codigo, regexes in self._patrones.items():
            for regex in regexes:
                m = regex.search(t)
                if m and (codigo in self._sin_negacion or not _precedido_por_negacion(
                        t, m.start(), self._negaciones, self._ventana)):
                    encontrados.add(codigo)
                    break
        return encontrados


INSTRUCCIONES_EXTRACTOR = """Eres un componente de análisis de texto. NO conversas con nadie.
Analiza el mensaje de un estudiante universitario e identifica cuáles de estos indicadores \
están expresados de forma explícita por la persona sobre sí misma:

{catalogo}

Responde ÚNICAMENTE con un objeto JSON con esta forma:
{{"indicadores": ["CODIGO", ...], "posible_riesgo": true|false}}

- Incluye un código solo si el mensaje lo expresa claramente; ante la duda, no lo incluyas.
- "posible_riesgo" es true si el mensaje sugiere, aunque sea de forma indirecta, deseos de \
morir, de desaparecer o de hacerse daño.
- No agregues explicaciones ni texto fuera del JSON."""


class ExtractorModelo:
    def __init__(self, proveedor: ProveedorIA, catalogo: dict[str, str]):
        self.proveedor = proveedor
        self.catalogo = catalogo

    def extraer(self, texto_depurado: str) -> tuple[set[str], bool]:
        lista = "\n".join(f"- {c}: {d}" for c, d in sorted(self.catalogo.items()))
        mensajes = [{"role": "system", "content": INSTRUCCIONES_EXTRACTOR.format(catalogo=lista)},
                    {"role": "user", "content": texto_depurado}]
        try:
            salida = self.proveedor.generar(mensajes, temperatura=0.0, json_salida=True)
            datos = json.loads(re.search(r"\{.*\}", salida, flags=re.S).group(0))
        except (ErrorProveedorIA, AttributeError, ValueError):
            return set(), False        # degradación controlada: queda el léxico
        codigos = {c for c in datos.get("indicadores", []) if c in self.catalogo}
        return codigos, bool(datos.get("posible_riesgo", False))


@lru_cache
def detector_riesgo() -> DetectorRiesgo:
    return DetectorRiesgo(obtener_configuracion().ruta_lexico_riesgo)


@lru_cache
def extractor_lexico() -> ExtractorLexico:
    return ExtractorLexico(obtener_configuracion().ruta_lexico_indicadores)
