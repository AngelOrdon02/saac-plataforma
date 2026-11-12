"""Oráculo independiente de los criterios de clasificación (capítulo 5).

Implementa directamente la tabla 22 (reglas R1 a R7) y las supresiones descritas
en la sección 3.2.3 del documento, SIN leer el archivo YAML ni usar el motor de
reglas. Sirve para verificar que el motor y el archivo de criterios aplican
exactamente lo que el documento establece.
"""
from __future__ import annotations

# Parámetros de la tabla 23
CORTE_DERIVACION = 10       # PHQ-9 >= 10 o GAD-7 >= 10 (Kroenke et al., 2001; Spitzer et al., 2006)
CORTE_LEVE = 5              # PHQ-9 >= 5 o GAD-7 >= 5
MIN_IND_TAMIZAJE = 2        # indicadores para ofrecer el tamizaje
MIN_IND_DERIVACION = 3      # indicadores para la regla R4 (con persistencia y deterioro)


def _ge(valor, corte) -> bool:
    """Un puntaje ausente (cuestionario no respondido) nunca cumple un corte."""
    return valor is not None and valor >= corte


def clasificar(h: dict) -> tuple[str, str, str]:
    """Devuelve (regla, categoría, acción) según la tabla 22 y las supresiones."""
    if h.get("nivel_riesgo", 0) >= 1 or _ge(h.get("phq9_item9"), 1) or h.get("verificacion_positiva"):
        return "R1", "C3", "PROTOCOLO_RIESGO"           # las supresiones nunca aplican al riesgo
    if h.get("requiere_verificacion"):
        return "R2", "C1", "VERIFICAR_RIESGO"
    if _ge(h.get("phq9_total"), CORTE_DERIVACION) or _ge(h.get("gad7_total"), CORTE_DERIVACION):
        regla, categoria, accion = "R3", "C2", "OFRECER_DERIVACION"
    elif (h.get("indicadores_emocionales", 0) >= MIN_IND_DERIVACION and h.get("persistencia")
          and h.get("deterioro_funcional")):
        regla, categoria, accion = "R4", "C2", "OFRECER_DERIVACION"
    elif _ge(h.get("phq9_total"), CORTE_LEVE) or _ge(h.get("gad7_total"), CORTE_LEVE):
        return "R5", "C1", "MONITOREO"
    elif h.get("indicadores_emocionales", 0) >= MIN_IND_TAMIZAJE:
        regla, categoria, accion = "R6", "C1", "OFRECER_TAMIZAJE"
    else:
        return "R7", "C0", "ACOMPANAMIENTO"

    # Supresiones (sección 3.2.3): no cambian la categoría, solo la acción.
    if accion == "OFRECER_TAMIZAJE" and (h.get("tamizaje_reciente") or h.get("tamizaje_ofrecido_reciente")):
        accion = "MONITOREO"
    elif accion == "OFRECER_DERIVACION":
        if h.get("solicitud_activa"):
            accion = "SEGUIMIENTO_SOLICITUD"
        elif h.get("derivacion_ofrecida_reciente"):
            accion = "MONITOREO"
    return regla, categoria, accion


NIVEL = {"C0": 0, "C1": 1, "C2": 2, "C3": 3}
