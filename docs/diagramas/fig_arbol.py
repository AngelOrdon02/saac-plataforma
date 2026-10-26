"""Árbol de decisión de los criterios de clasificación (reglas v1.0.0)."""
from kit import Lienzo

c = Lienzo(5.94, 7.42)
CX = 1.55          # columna de decisiones
c.caja(CX - 1.3, 0.12, 2.6, 0.36, "Evento: mensaje, tamizaje o verificación", relleno="claro", tam=7)
c.flecha(CX, 0.48, CX, 0.66)
c.caja(CX - 1.4, 0.66, 2.8, 0.62,
       "Cálculo de hechos en la ventana de 14 días\n(riesgo, puntajes, indicadores, persistencia,\n"
       "deterioro, ofrecimientos y solicitudes previas)", relleno="claro", tam=6.6)
decisiones = [
    ("R1 · ¿Riesgo ≥ 1, ítem 9 del PHQ-9 ≥ 1\no verificación afirmativa?",
     "C3 · Escalamiento prioritario", "PROTOCOLO_RIESGO", "fuerte"),
    ("R2 · ¿Expresión ambigua que\nrequiere verificación?",
     "C1 · Monitoreo activo", "VERIFICAR_RIESGO (pregunta directa)", "medio"),
    ("R3 · ¿PHQ-9 ≥ 10\no GAD-7 ≥ 10?",
     "C2 · Derivación ordinaria", "OFRECER_DERIVACION", "oscuro"),
    ("R4 · ¿≥ 3 indicadores emocionales,\npersistencia y deterioro funcional?",
     "C2 · Derivación ordinaria", "OFRECER_DERIVACION", "oscuro"),
    ("R5 · ¿PHQ-9 ≥ 5\no GAD-7 ≥ 5?",
     "C1 · Monitoreo activo", "MONITOREO", "medio"),
    ("R6 · ¿≥ 2 indicadores\nemocionales?",
     "C1 · Monitoreo activo", "OFRECER_TAMIZAJE", "medio"),
]
y = 1.5
BUS = 5.75
ys_salida = []
c.flecha(CX, 1.28, CX, y)
for i, (preg, cat, acc, rel) in enumerate(decisiones):
    h = 0.56
    c.rombo(CX, y + h / 2, 3.0, h, preg, tam=6.2)
    # sí -> derecha
    c.flecha(CX + 1.475, y + h / 2, 3.35, y + h / 2, etiqueta="sí", tam=6.5, desp=(0, -0.09))
    c.caja(3.35, y + h / 2 - 0.25, 2.15, 0.5, "", relleno=rel)
    c.texto(4.425, y + h / 2 - 0.08, cat, tam=6.8, negrita=True)
    c.texto(4.425, y + h / 2 + 0.11, acc, tam=6.2)
    c.linea([(5.5, y + h / 2), (BUS, y + h / 2)], flecha_final=False)
    ys_salida.append(y + h / 2)
    # no -> abajo
    siguiente = y + h + 0.2
    c.flecha(CX, y + h, CX, siguiente, etiqueta="no", tam=6.5, desp=(0.14, 0))
    y = siguiente
# R7 por defecto
c.caja(CX - 1.2, y, 2.4, 0.5, "", relleno="blanco")
c.texto(CX, y + 0.17, "R7 · C0 · Acompañamiento académico", tam=6.8, negrita=True)
c.texto(CX, y + 0.36, "ACOMPANAMIENTO", tam=6.2)
y_final = y + 0.72
c.flecha(CX, y + 0.5, CX, y_final)
c.linea([(BUS, ys_salida[0]), (BUS, y_final + 0.27), (4.9, y_final + 0.27)])
c.caja(0.25, y_final, 4.65, 0.55,
       "Supresiones (no insistir) y registro en la bitácora encadenada\n"
       "(reglas evaluadas, evidencias, versión y huella del archivo de reglas)",
       relleno="claro", tam=6.6)
c.guardar("06_arbol_decision.png")
