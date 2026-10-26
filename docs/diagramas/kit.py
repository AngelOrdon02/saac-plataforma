"""Utilidades de dibujo para los diagramas de arquitectura (matplotlib).

Los diagramas se dibujan directamente al tamaño en que aparecen en el documento
(ancho de 5.94 pulgadas), de modo que el tamaño de letra indicado en puntos es el
que se imprime. Paleta en escala de grises, coherente con las figuras 1 a 3.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
BORDE = "#333333"
GRIS = {"blanco": "#FFFFFF", "claro": "#F2F2F2", "medio": "#E0E0E0", "oscuro": "#CCCCCC",
        "fuerte": "#B3B3B3"}


class Lienzo:
    def __init__(self, ancho_in: float, alto_in: float):
        self.fig = plt.figure(figsize=(ancho_in, alto_in))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, ancho_in)
        self.ax.set_ylim(0, alto_in)
        self.ax.axis("off")
        self.alto = alto_in

    # Coordenadas: (x, y) desde la esquina SUPERIOR izquierda, en pulgadas
    def _y(self, y: float) -> float:
        return self.alto - y

    def caja(self, x, y, w, h, texto="", relleno="claro", titulo=None, tam=8, negrita=False,
             estilo="round", lw=1.0, punteada=False, alinear_titulo="center", tam_titulo=None):
        p = FancyBboxPatch((x, self._y(y + h)), w, h,
                           boxstyle=f"{estilo},pad=0,rounding_size=0.06" if estilo == "round"
                           else "square,pad=0",
                           linewidth=lw, edgecolor=BORDE, facecolor=GRIS.get(relleno, relleno),
                           linestyle="--" if punteada else "-")
        self.ax.add_patch(p)
        if titulo:
            tx = x + w / 2 if alinear_titulo == "center" else x + 0.08
            self.ax.text(tx, self._y(y + 0.07), titulo, ha=alinear_titulo, va="top",
                         fontsize=tam_titulo or tam, fontweight="bold")
        if texto:
            cy = y + h / 2 + (0.08 if titulo and not negrita else 0)
            self.ax.text(x + w / 2, self._y(cy), texto, ha="center", va="center", fontsize=tam,
                         fontweight="bold" if negrita else "normal", linespacing=1.25)
        return (x, y, w, h)

    def texto(self, x, y, s, tam=8, ha="center", va="center", negrita=False, cursiva=False,
              color="black"):
        self.ax.text(x, self._y(y), s, ha=ha, va=va, fontsize=tam,
                     fontweight="bold" if negrita else "normal",
                     fontstyle="italic" if cursiva else "normal", color=color, linespacing=1.25)

    def flecha(self, x1, y1, x2, y2, etiqueta=None, punteada=False, tam=7, doble=False,
               desp=(0, 0), rad=0.0, cabeza=True, ha="center"):
        estilo = ("<|-|>" if doble else "-|>") if cabeza else "-"
        a = FancyArrowPatch((x1, self._y(y1)), (x2, self._y(y2)), arrowstyle=estilo,
                            mutation_scale=9, linewidth=1.0, color=BORDE,
                            linestyle=(0, (4, 3)) if punteada else "-",
                            connectionstyle=f"arc3,rad={rad}", shrinkA=1, shrinkB=1)
        self.ax.add_patch(a)
        if etiqueta:
            mx, my = (x1 + x2) / 2 + desp[0], (y1 + y2) / 2 + desp[1]
            self.ax.text(mx, self._y(my), etiqueta, ha=ha, va="center", fontsize=tam,
                         fontstyle="italic",
                         bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))

    def linea(self, puntos, punteada=False, flecha_final=True):
        xs = [p[0] for p in puntos]
        ys = [self._y(p[1]) for p in puntos]
        self.ax.plot(xs[:-1] + [xs[-1]], ys[:-1] + [ys[-1]], color=BORDE, lw=1.0,
                     linestyle=(0, (4, 3)) if punteada else "-", solid_capstyle="butt")
        if flecha_final:
            (x1, y1), (x2, y2) = puntos[-2], puntos[-1]
            self.flecha(x1 + (x2 - x1) * 0.6, y1 + (y2 - y1) * 0.6, x2, y2, punteada=punteada)

    def elipse(self, cx, cy, w, h, texto, relleno="claro", tam=7.5, negocio=False):
        e = Ellipse((cx, self._y(cy)), w, h, linewidth=1.0, edgecolor=BORDE,
                    facecolor=GRIS.get(relleno, relleno))
        self.ax.add_patch(e)
        if negocio:  # caso de uso del negocio: trazo diagonal (notación RUP)
            self.ax.plot([cx + w * 0.30, cx + w * 0.44], [self._y(cy + h * 0.38), self._y(cy - h * 0.20)],
                         color=BORDE, lw=0.8)
        self.ax.text(cx, self._y(cy), texto, ha="center", va="center", fontsize=tam, linespacing=1.2)

    def actor(self, cx, cy, etiqueta, tam=7.5, negocio=False, estereotipo=None, escala=1.0):
        s = escala
        y0 = self._y(cy)
        cabeza = plt.Circle((cx, y0 + 0.17 * s), 0.07 * s, fill=True, fc=GRIS["medio"], ec=BORDE, lw=1)
        self.ax.add_patch(cabeza)
        if negocio:
            self.ax.plot([cx - 0.02 * s, cx + 0.06 * s], [y0 + 0.13 * s, y0 + 0.22 * s], color=BORDE, lw=0.8)
        self.ax.plot([cx, cx], [y0 + 0.10 * s, y0 - 0.07 * s], color=BORDE, lw=1)
        self.ax.plot([cx - 0.1 * s, cx + 0.1 * s], [y0 + 0.05 * s, y0 + 0.05 * s], color=BORDE, lw=1)
        self.ax.plot([cx, cx - 0.08 * s], [y0 - 0.07 * s, y0 - 0.2 * s], color=BORDE, lw=1)
        self.ax.plot([cx, cx + 0.08 * s], [y0 - 0.07 * s, y0 - 0.2 * s], color=BORDE, lw=1)
        texto = (f"«{estereotipo}»\n" if estereotipo else "") + etiqueta
        self.ax.text(cx, y0 - 0.26 * s, texto, ha="center", va="top", fontsize=tam, linespacing=1.15)

    def rombo(self, cx, cy, w, h, texto, tam=7):
        y0 = self._y(cy)
        p = Polygon([(cx, y0 + h / 2), (cx + w / 2, y0), (cx, y0 - h / 2), (cx - w / 2, y0)],
                    closed=True, ec=BORDE, fc="white", lw=1)
        self.ax.add_patch(p)
        self.ax.text(cx, y0, texto, ha="center", va="center", fontsize=tam, linespacing=1.15)

    def cilindro(self, x, y, w, h, texto, relleno="medio", tam=7.5):
        e = 0.09
        y0 = self._y(y + h)
        self.ax.add_patch(Rectangle((x, y0 + e / 2), w, h - e, fc=GRIS[relleno], ec="none"))
        self.ax.plot([x, x], [y0 + e / 2, y0 + h - e / 2], color=BORDE, lw=1)
        self.ax.plot([x + w, x + w], [y0 + e / 2, y0 + h - e / 2], color=BORDE, lw=1)
        self.ax.add_patch(Ellipse((x + w / 2, y0 + e / 2), w, e, fc=GRIS[relleno], ec=BORDE, lw=1))
        self.ax.add_patch(Ellipse((x + w / 2, y0 + h - e / 2), w, e, fc=GRIS[relleno], ec=BORDE, lw=1))
        self.ax.text(x + w / 2, y0 + (h - e) / 2, texto, ha="center", va="center", fontsize=tam,
                     linespacing=1.2)

    def guardar(self, ruta: str):
        self.fig.savefig(ruta, dpi=300, facecolor="white")
        plt.close(self.fig)


def componente(c: Lienzo, x, y, w, h, nombre, detalle="", relleno="claro", tam=6.6, punteada=False):
    """Componente UML: caja con el ícono de dos pestañas en la esquina."""
    c.caja(x, y, w, h, relleno=relleno, estilo="square", punteada=punteada)
    ix, iy = x + w - 0.2, y + 0.06
    c.caja(ix, iy, 0.13, 0.15, relleno="blanco", estilo="square", lw=0.7)
    c.caja(ix - 0.04, iy + 0.025, 0.08, 0.035, relleno="blanco", estilo="square", lw=0.7)
    c.caja(ix - 0.04, iy + 0.085, 0.08, 0.035, relleno="blanco", estilo="square", lw=0.7)
    if detalle:
        c.texto(x + w / 2, y + 0.2, nombre, tam=tam, negrita=True)
        c.texto(x + w / 2, y + 0.2 + (h - 0.2) / 2, detalle, tam=tam - 0.8)
    else:
        c.texto(x + w / 2, y + h / 2, nombre, tam=tam, negrita=True)
