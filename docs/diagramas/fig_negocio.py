"""Diagrama de casos de uso del negocio (RUP)."""
from kit import Lienzo

c = Lienzo(5.94, 4.05)
c.caja(1.05, 0.25, 3.95, 3.7, relleno="blanco", estilo="square")
c.texto(3.02, 0.4, "Negocio: acompañamiento académico y canalización (USAC)", tam=7.5, negrita=True)
W, H = 1.55, 0.6
uc = {
    "N1": (1.85, 0.95, "CUN-01\nObtener orientación\nacadémica"),
    "N2": (2.95, 1.9, "CUN-02\nIdentificar dificultades\nque exceden lo académico"),
    "N3": (4.1, 1.05, "CUN-03\nCanalizar hacia\natención psicológica"),
    "N4": (4.1, 2.6, "CUN-04\nAtender una situación\nde riesgo"),
    "N5": (4.1, 3.45, "CUN-05\nDar seguimiento a\nla derivación"),
    "N6": (1.85, 3.45, "CUN-06\nSupervisar el servicio\ny su trazabilidad"),
}
for k, (x, y, t) in uc.items():
    c.elipse(x, y, W + (0.15 if k == "N2" else 0), H, t, tam=6.6, negocio=True)

c.actor(0.45, 1.85, "Estudiante", negocio=True, tam=7)
c.actor(5.5, 2.15, "Personal de\natención\npsicológica", estereotipo="trabajador", tam=6.8)
c.actor(0.45, 3.3, "Administrador\ntécnico", estereotipo="trabajador", tam=6.8)

# Asociaciones
c.flecha(0.58, 1.75, 1.12, 1.12, cabeza=False)
c.flecha(0.58, 1.8, 3.33, 1.12, cabeza=False)
c.flecha(0.58, 1.95, 3.33, 2.55, cabeza=False)
c.flecha(5.38, 2.0, 4.87, 1.15, cabeza=False)
c.flecha(5.38, 2.1, 4.87, 2.55, cabeza=False)
c.flecha(5.38, 2.2, 4.8, 3.3, cabeza=False)
c.flecha(0.58, 3.38, 1.07, 3.45, cabeza=False)
# include / extend
c.flecha(2.2, 1.24, 2.6, 1.6, etiqueta="«include»", punteada=True, desp=(-0.32, 0.12), tam=6.5)
c.flecha(3.45, 1.62, 3.75, 1.33, etiqueta="«extend»", punteada=True, desp=(0.1, 0.05), tam=6.5)
c.flecha(3.45, 2.18, 3.72, 2.32, etiqueta="«extend»", punteada=True, desp=(-0.32, 0.1), tam=6.5)
c.guardar("02_casos_uso_negocio.png")
