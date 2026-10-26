"""Casos de uso del sistema: estudiante y servicio de modelos."""
from kit import Lienzo

c = Lienzo(5.94, 4.3)
c.caja(0.95, 0.15, 4.05, 4.05, relleno="blanco", estilo="square")
c.texto(2.97, 0.3, "SAAC", tam=7.5, negrita=True)
WA, WB, H = 1.62, 1.42, 0.46
A, B = 1.85, 3.98
ucs_a = [("CU-01 Registrarse y aceptar\nel consentimiento", 0.7), ("CU-06 Consultar\nrecursos de apoyo", 1.25),
         ("CU-07 Consultar y cancelar\nmis solicitudes", 1.8), ("CU-02 Conversar con el\nasistente académico", 2.35),
         ("CU-04 Responder cuestionario\nde bienestar", 2.9), ("CU-05 Solicitar contacto con\natención psicológica", 3.6)]
for t, y in ucs_a:
    c.elipse(A, y, WA, H, t, tam=6.2)
    c.flecha(0.58, 2.15, A - WA / 2 + 0.02, y, cabeza=False)
c.elipse(B, 1.45, WB, H, "CU-09 Verificar\nseñal ambigua", tam=6.2)
c.elipse(B, 2.6, WB, H, "CU-03 Evaluar\nmensaje", tam=6.2)
c.elipse(B, 3.2, WB, H, "CU-08 Activar\nprotocolo de riesgo", tam=6.2)
c.elipse(B, 3.85, WB, 0.4, "CU-12 Notificar\nal personal", tam=6.2)
# include / extend
c.flecha(A + WA / 2 - 0.02, 2.4, B - WB / 2 + 0.02, 2.55, punteada=True)
c.texto(2.98, 2.36, "«include»", tam=5.8, cursiva=True)
c.flecha(A + WA / 2 - 0.02, 2.88, B - WB / 2 + 0.02, 2.68, punteada=True)
c.texto(2.98, 2.9, "«include»", tam=5.8, cursiva=True)
c.flecha(B, 1.68, B, 2.37, punteada=True)
c.texto(B - 0.33, 1.84, "«extend»", tam=5.8, cursiva=True)
c.flecha(B, 2.97, B, 2.83, punteada=True)
c.texto(B + 0.33, 2.9, "«extend»", tam=5.8, cursiva=True)
c.flecha(A + WA / 2 - 0.05, 3.7, B - WB / 2 + 0.02, 3.85, punteada=True)
c.texto(3.0, 3.88, "«include»", tam=5.8, cursiva=True)
c.flecha(B, 3.43, B, 3.65, punteada=True)
c.texto(B + 0.33, 3.54, "«include»", tam=5.8, cursiva=True)
# actores
c.actor(0.42, 2.05, "Estudiante", tam=7)
c.actor(5.45, 1.85, "Servicio de\nmodelos de\nlenguaje", estereotipo="sistema", tam=6.4)
c.flecha(B + WB / 2, 2.55, 5.3, 1.95, cabeza=False)
c.flecha(A + WA / 2 - 0.05, 2.25, 5.3, 1.88, cabeza=False)
c.guardar("05a_casos_uso_estudiante.png")
