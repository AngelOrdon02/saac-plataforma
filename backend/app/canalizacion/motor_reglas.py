"""Motor de reglas declarativo y versionado.

Las reglas no están escritas en el código: se cargan desde un archivo YAML
(``reglas/criterios_vX.Y.Z.yaml``). El motor solo sabe interpretar condiciones
simples sobre hechos (``>=``, ``==``, etc.) combinadas con ``todas`` (Y lógico) o
``cualquiera`` (O lógico). No se usa ``eval``: un archivo de reglas no puede
ejecutar código.

El resultado incluye la regla que se cumplió y la traza de todas las reglas
evaluadas, que se guarda en la bitácora para reconstruir cada decisión.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.canalizacion.deteccion import huella_archivo
from app.config import obtener_configuracion

_OPERADORES = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
               "==": operator.eq, "!=": operator.ne}


@dataclass
class Hechos:
    """Hechos que el motor evalúa. Se calculan a partir de las señales y
    tamizajes del estudiante dentro de la ventana de tiempo configurada."""
    nivel_riesgo: int = 0
    requiere_verificacion: bool = False
    verificacion_positiva: bool = False
    phq9_total: int | None = None
    phq9_item9: int | None = None
    gad7_total: int | None = None
    indicadores_emocionales: int = 0
    persistencia: bool = False
    deterioro_funcional: bool = False
    tamizaje_reciente: bool = False
    tamizaje_ofrecido_reciente: bool = False
    derivacion_ofrecida_reciente: bool = False
    solicitud_activa: bool = False

    def como_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Decision:
    categoria: str
    accion: str
    regla: str
    nombre_regla: str
    fuentes: list[str]
    traza: list[dict] = field(default_factory=list)
    supresion: str | None = None
    version: str = ""
    huella: str = ""


class MotorReglas:
    def __init__(self, ruta: Path):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        self.version: str = datos["version"]
        self.huella = huella_archivo(ruta)
        self.parametros: dict[str, Any] = datos["parametros"]
        self.reglas: list[dict] = datos["reglas"]
        self.supresiones: list[dict] = datos.get("supresiones", [])
        self._validar()

    def _validar(self) -> None:
        ids = [r["id"] for r in self.reglas]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay identificadores de regla repetidos")
        if not any(r["condicion"].get("siempre") for r in self.reglas):
            raise ValueError("Debe existir una regla por defecto ({siempre: true})")
        for r in self.reglas:
            if r["categoria"] not in {"C0", "C1", "C2", "C3"}:
                raise ValueError(f"Categoría inválida en {r['id']}")

    # -- evaluación de condiciones ------------------------------------------------
    def _valor(self, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("$"):
            return self.parametros[v[1:]]
        return v

    def _cumple(self, condicion: dict, hechos: dict[str, Any]) -> bool:
        if condicion.get("siempre"):
            return True
        if "todas" in condicion:
            return all(self._cumple(c, hechos) for c in condicion["todas"])
        if "cualquiera" in condicion:
            return any(self._cumple(c, hechos) for c in condicion["cualquiera"])
        valor_hecho = hechos.get(condicion["hecho"])
        if valor_hecho is None:          # un hecho ausente (p. ej. sin tamizaje) no se cumple
            return False
        return _OPERADORES[condicion["op"]](valor_hecho, self._valor(condicion["valor"]))

    def evaluar(self, hechos: Hechos) -> Decision:
        h = hechos.como_dict()
        traza: list[dict] = []
        for regla in self.reglas:
            cumple = self._cumple(regla["condicion"], h)
            traza.append({"regla": regla["id"], "cumple": cumple})
            if cumple:
                decision = Decision(regla["categoria"], regla["accion"], regla["id"],
                                    regla["nombre"], list(regla.get("fuentes", [])), traza,
                                    version=self.version, huella=self.huella)
                return self._aplicar_supresiones(decision, h)
        raise RuntimeError("Ninguna regla se cumplió")   # imposible: existe regla por defecto

    def _aplicar_supresiones(self, decision: Decision, h: dict[str, Any]) -> Decision:
        for s in self.supresiones:
            if s["si_accion"] == decision.accion and self._cumple(s["cuando"], h):
                decision.supresion = f"{decision.accion}->{s['nueva_accion']}"
                decision.accion = s["nueva_accion"]
                break
        return decision


@lru_cache
def motor_reglas() -> MotorReglas:
    return MotorReglas(obtener_configuracion().ruta_criterios)
