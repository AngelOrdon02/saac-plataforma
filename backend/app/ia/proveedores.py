"""Proveedores de modelos de lenguaje y de embeddings.

Se aplica el patrón Adaptador (Gamma et al., 1994): el resto de la plataforma
depende únicamente de la interfaz ``ProveedorIA`` y no de un servicio concreto.
El contrato de integración elegido es la API de OpenAI (``/chat/completions`` y
``/embeddings``), que hoy implementan tanto servidores de código abierto (Ollama,
vLLM, LM Studio) como servicios comerciales. Cambiar de proveedor es cuestión de
modificar variables de entorno, sin tocar el código.

``ProveedorSimulado`` no usa ningún modelo: genera respuestas extractivas a partir
de los fragmentos recuperados y embeddings por *hashing*. Permite ejecutar las
pruebas automatizadas y la demostración en equipos sin GPU ni conexión.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Protocol

import httpx

from app.config import Configuracion, obtener_configuracion
from app.seguridad.proteccion import normalizar


class ErrorProveedorIA(RuntimeError):
    """El servicio de modelos no respondió o respondió con un formato inválido."""


class ProveedorIA(Protocol):
    nombre: str

    def generar(self, mensajes: list[dict], *, temperatura: float | None = None,
                json_salida: bool = False) -> str: ...

    def embeber(self, textos: list[str]) -> list[list[float]]: ...


# ---------------------------------------------------------------------------
# Proveedor compatible con la API de OpenAI (Ollama, vLLM, servicios comerciales)
# ---------------------------------------------------------------------------


class ProveedorOpenAICompatible:
    def __init__(self, cfg: Configuracion):
        self.cfg = cfg
        self.nombre = f"{cfg.ia_modelo_chat}@{cfg.ia_url_base}"
        self._cliente = httpx.Client(
            base_url=cfg.ia_url_base.rstrip("/"),
            headers={"Authorization": f"Bearer {cfg.ia_clave_api}"},
            timeout=cfg.ia_tiempo_espera_s,
        )

    def generar(self, mensajes: list[dict], *, temperatura: float | None = None,
                json_salida: bool = False) -> str:
        cuerpo: dict = {
            "model": self.cfg.ia_modelo_chat,
            "messages": mensajes,
            "temperature": self.cfg.ia_temperatura if temperatura is None else temperatura,
        }
        if json_salida:
            cuerpo["response_format"] = {"type": "json_object"}
        try:
            r = self._cliente.post("/chat/completions", json=cuerpo)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise ErrorProveedorIA(f"Fallo al generar: {exc}") from exc

    def embeber(self, textos: list[str]) -> list[list[float]]:
        cuerpo: dict = {"model": self.cfg.ia_modelo_embeddings, "input": textos}
        if "openai.com" in self.cfg.ia_url_base:
            cuerpo["dimensions"] = self.cfg.ia_dimension_embeddings
        try:
            r = self._cliente.post("/embeddings", json=cuerpo)
            r.raise_for_status()
            datos = sorted(r.json()["data"], key=lambda d: d["index"])
            vectores = [d["embedding"] for d in datos]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ErrorProveedorIA(f"Fallo al calcular embeddings: {exc}") from exc
        if any(len(v) != self.cfg.ia_dimension_embeddings for v in vectores):
            raise ErrorProveedorIA("La dimensión de los embeddings no coincide con la configurada")
        return vectores


# ---------------------------------------------------------------------------
# Proveedor simulado (sin modelo)
# ---------------------------------------------------------------------------

_PALABRAS_VACIAS = set("""a al algo como con de del el ella ellos en entre es esa ese eso esta este
esto estoy fue ha hay la las le les lo los me mi mis muy no nos o para pero por que se si sin
sobre su sus te tengo ti tu tus un una uno y ya yo cual cuando donde mas menos puedo quiero hacer""".split())


def _tokens(texto: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9ñ]+", normalizar(texto))
            if t not in _PALABRAS_VACIAS and len(t) > 2]


class ProveedorSimulado:
    nombre = "simulado"

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    # Embeddings por hashing de términos y prefijos (bolsa de palabras dispersa).
    def embeber(self, textos: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in textos]

    def _vector(self, texto: str) -> list[float]:
        v = [0.0] * self.dimension
        for tok in _tokens(texto):
            for rasgo in (tok, tok[:5]):        # el prefijo aproxima la raíz de la palabra
                h = int(hashlib.md5(rasgo.encode()).hexdigest(), 16)
                v[h % self.dimension] += 1.0 if (h >> 64) & 1 else -1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def generar(self, mensajes: list[dict], *, temperatura: float | None = None,
                json_salida: bool = False) -> str:
        if json_salida:
            # El extractor simulado no aporta señales: en este modo la detección
            # depende exclusivamente del léxico determinista.
            return json.dumps({"indicadores": [], "posible_riesgo": False})
        sistema = mensajes[0]["content"] if mensajes else ""
        sistema = sistema.split("CONTEXTO:", 1)[-1]
        fragmentos = re.findall(r"\[(F\d+)\][^\n]*\n(.+?)(?=\n\[F\d+\]|\Z)", sistema, flags=re.S)
        if not fragmentos:
            return ("Gracias por contarme cómo te sientes. Desde el acompañamiento académico puedo "
                    "ayudarte a organizar tus tareas y tu tiempo de estudio para que la carga se "
                    "sienta más manejable. ¿Quieres que empecemos por ahí?")
        ultimo = normalizar(mensajes[-1]["content"]) if mensajes else ""
        emotivo = re.search(r"\b(siento|triste|cansad|agobiad|estresad|ansios|mal)\w*", ultimo)
        partes = (["Gracias por contármelo; lamento que estés pasando por días difíciles. "
                   "Mientras tanto, algunas ideas que pueden aligerar la carga de estudio:"]
                  if emotivo else
                  ["Con base en la evidencia sobre hábitos de estudio, te sugiero lo siguiente:"])
        for etiqueta, contenido in fragmentos[:3]:
            texto = re.sub(r"(?m)^\s*(?:-|\d+\.)\s+", "", contenido.strip())
            oraciones = re.split(r"(?<=[.!?:])\s+", texto)
            if len(oraciones) > 1 and len(oraciones[0].split()) <= 4:   # título de sección
                oraciones = oraciones[1:]
            oraciones = [re.sub(r"^[-•]\s*", "", o) for o in oraciones]
            partes.append(f"• {' '.join(oraciones[:2]).strip()} [{etiqueta}]")
        partes.append("¿Quieres que lo aterricemos en un plan para tu semana?")
        return "\n".join(partes)


def obtener_proveedor(cfg: Configuracion | None = None) -> ProveedorIA:
    cfg = cfg or obtener_configuracion()
    if cfg.proveedor_ia == "openai_compatible":
        return ProveedorOpenAICompatible(cfg)
    return ProveedorSimulado(cfg.ia_dimension_embeddings)
