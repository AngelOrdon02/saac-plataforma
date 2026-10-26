"""Instrumentos de tamizaje validados: PHQ-9 y GAD-7.

La puntuación y los niveles de severidad son exactamente los publicados por los
autores (tablas 2 y 3 del documento). El sistema NO interpreta el resultado como
diagnóstico: solo lo usa como hecho para el motor de reglas.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.config import obtener_configuracion


@dataclass
class ResultadoTamizaje:
    instrumento: str
    puntaje_total: int
    severidad: str
    item9: int | None = None


class Instrumentos:
    def __init__(self, datos: dict):
        self.opciones = datos["opciones"]
        self.definiciones = {k: datos[k] for k in ("PHQ9", "GAD7")}

    def definicion(self, instrumento: str) -> dict:
        if instrumento not in self.definiciones:
            raise ValueError("Instrumento desconocido")
        d = self.definiciones[instrumento]
        return {"instrumento": instrumento, "nombre": d["nombre"],
                "nombre_tecnico": d["nombre_tecnico"], "instruccion": d["instruccion"],
                "items": d["items"], "opciones": self.opciones}

    def calificar(self, instrumento: str, respuestas: list[int]) -> ResultadoTamizaje:
        d = self.definiciones.get(instrumento)
        if d is None:
            raise ValueError("Instrumento desconocido")
        if len(respuestas) != len(d["items"]):
            raise ValueError(f"{instrumento} requiere {len(d['items'])} respuestas")
        if any(r not in (0, 1, 2, 3) for r in respuestas):
            raise ValueError("Cada respuesta debe estar entre 0 y 3")
        total = sum(respuestas)
        severidad = next(s["nivel"] for s in d["severidad"] if s["minimo"] <= total <= s["maximo"])
        item9 = respuestas[8] if instrumento == "PHQ9" else None
        return ResultadoTamizaje(instrumento, total, severidad, item9)


@lru_cache
def instrumentos() -> Instrumentos:
    ruta = obtener_configuracion().ruta_instrumentos
    return Instrumentos(yaml.safe_load(ruta.read_text(encoding="utf-8")))
