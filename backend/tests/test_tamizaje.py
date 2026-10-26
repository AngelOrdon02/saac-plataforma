"""Pruebas de calificación del PHQ-9 y la GAD-7 (puntos de corte publicados)."""
import pytest

from app.canalizacion.tamizaje import instrumentos


@pytest.mark.parametrize("total,nivel", [(0, "Mínimo o ninguno"), (4, "Mínimo o ninguno"), (5, "Leve"),
                                         (9, "Leve"), (10, "Moderado"), (14, "Moderado"),
                                         (15, "Moderadamente severo"), (19, "Moderadamente severo"),
                                         (20, "Severo"), (27, "Severo")])
def test_phq9_severidad(total: int, nivel: str) -> None:
    respuestas = [3] * (total // 3) + ([total % 3] if total % 3 else [])
    respuestas += [0] * (9 - len(respuestas))
    r = instrumentos().calificar("PHQ9", respuestas)
    assert (r.puntaje_total, r.severidad) == (total, nivel)


@pytest.mark.parametrize("total,nivel", [(0, "Mínimo"), (4, "Mínimo"), (5, "Leve"), (9, "Leve"),
                                         (10, "Moderado"), (14, "Moderado"), (15, "Severo"),
                                         (21, "Severo")])
def test_gad7_severidad(total: int, nivel: str) -> None:
    respuestas = [3] * (total // 3) + ([total % 3] if total % 3 else [])
    respuestas += [0] * (7 - len(respuestas))
    r = instrumentos().calificar("GAD7", respuestas)
    assert (r.puntaje_total, r.severidad) == (total, nivel)


def test_item9_se_reporta_por_separado() -> None:
    assert instrumentos().calificar("PHQ9", [0] * 8 + [2]).item9 == 2


@pytest.mark.parametrize("respuestas", [[0] * 8, [0] * 10, [4] + [0] * 8, [-1] + [0] * 8])
def test_respuestas_invalidas(respuestas: list[int]) -> None:
    with pytest.raises(ValueError):
        instrumentos().calificar("PHQ9", respuestas)
