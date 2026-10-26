"""Pruebas del motor de reglas con los casos derivados de la literatura."""
from pathlib import Path

import pytest
import yaml

from app.canalizacion.motor_reglas import Hechos, MotorReglas
from app.config import obtener_configuracion

CASOS = yaml.safe_load((Path(__file__).parent / "casos" / "casos_motor.yaml").read_text("utf-8"))


@pytest.fixture(scope="module")
def motor() -> MotorReglas:
    return MotorReglas(obtener_configuracion().ruta_criterios)


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(motor: MotorReglas, caso: dict) -> None:
    decision = motor.evaluar(Hechos(**caso["hechos"]))
    esperado = caso["esperado"]
    assert (decision.categoria, decision.accion, decision.regla) == (
        esperado["categoria"], esperado["accion"], esperado["regla"]), caso["descripcion"]


def test_es_determinista(motor: MotorReglas) -> None:
    hechos = Hechos(indicadores_emocionales=3, persistencia=True, deterioro_funcional=True)
    resultados = {(d.categoria, d.accion, d.regla) for d in (motor.evaluar(hechos) for _ in range(50))}
    assert len(resultados) == 1


def test_traza_completa_hasta_la_regla_aplicada(motor: MotorReglas) -> None:
    decision = motor.evaluar(Hechos(phq9_total=12, phq9_item9=0))
    assert [t["regla"] for t in decision.traza] == ["R1", "R2", "R3"]
    assert decision.traza[-1]["cumple"] is True
    assert len(decision.huella) == 64 and decision.version == "1.0.0"


def test_rechaza_reglas_sin_regla_por_defecto(tmp_path: Path) -> None:
    ruta = tmp_path / "malas.yaml"
    ruta.write_text("version: '0'\nparametros: {}\nreglas:\n  - {id: X, nombre: x, categoria: C1, "
                    "accion: A, condicion: {todas: []}}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        MotorReglas(ruta)
