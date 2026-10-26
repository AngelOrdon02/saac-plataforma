"""Pruebas de los detectores deterministas (riesgo e indicadores)."""
from pathlib import Path

import pytest
import yaml

from app.canalizacion.deteccion import DetectorRiesgo, ExtractorLexico
from app.config import obtener_configuracion

CASOS = yaml.safe_load((Path(__file__).parent / "casos" / "casos_texto.yaml").read_text("utf-8"))
cfg = obtener_configuracion()
detector = DetectorRiesgo(cfg.ruta_lexico_riesgo)
extractor = ExtractorLexico(cfg.ruta_lexico_indicadores)


@pytest.mark.parametrize("caso", CASOS["riesgo"], ids=[c["texto"][:30] for c in CASOS["riesgo"]])
def test_riesgo(caso: dict) -> None:
    r = detector.evaluar(caso["texto"])
    assert r.nivel == caso["nivel"]
    assert r.requiere_verificacion == caso["verificar"]


@pytest.mark.parametrize("caso", CASOS["indicadores"],
                         ids=[c["texto"][:30] for c in CASOS["indicadores"]])
def test_indicadores(caso: dict) -> None:
    assert extractor.extraer(caso["texto"]) == set(caso["codigos"])


def test_tildes_y_mayusculas_no_afectan() -> None:
    assert detector.evaluar("OJALÁ ESTUVIERA MUERTO").nivel == 1
