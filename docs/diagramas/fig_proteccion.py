"""Flujo de la información y medidas de protección."""
from kit import Lienzo

c = Lienzo(5.94, 4.15)
c.caja(0.08, 0.95, 1.05, 0.7, "Mensaje del\nestudiante", relleno="medio", tam=6.8)
c.caja(1.4, 0.75, 1.3, 1.1, "", relleno="claro")
c.texto(2.05, 0.95, "API", tam=6.8, negrita=True)
c.texto(2.05, 1.38, "el token JWT solo\nlleva el seudónimo\n(no el nombre)", tam=6.3)
c.flecha(1.13, 1.3, 1.4, 1.3)
destinos = [
    (0.1, "academico.mensaje", "texto CIFRADO (Fernet)\nconexión rol_academico", "claro"),
    (0.95, "Servicio de modelos", "texto DEPURADO: sin correo,\nteléfono, carné, DPI ni nombre", "blanco"),
    (1.8, "canalizacion.senal", "solo CÓDIGOS de indicador\n+ seudónimo (nunca el texto)", "oscuro"),
]
for y, t, d, r in destinos:
    c.caja(3.15, y, 2.7, 0.66, "", relleno=r, punteada=(r == "blanco"))
    c.texto(4.5, y + 0.17, t, tam=6.8, negrita=True)
    c.texto(4.5, y + 0.44, d, tam=6.0)
    c.flecha(2.7, 1.3, 3.15, y + 0.33)
# Identidad y acceso
c.caja(0.08, 2.75, 1.85, 1.25, "", relleno="medio")
c.texto(1.0, 2.9, "identidad.usuario", tam=6.8, negrita=True)
c.texto(1.0, 3.4, "nombre y teléfono CIFRADOS\ncontraseña con Argon2id\nseudónimo = HMAC-SHA256(id)", tam=6.0)
c.caja(2.2, 2.75, 1.7, 1.25, "", relleno="claro")
c.texto(3.05, 2.9, "Solicitud de derivación", tam=6.8, negrita=True)
c.texto(3.05, 3.42, "contacto CIFRADO; se comparte\nsolo con consentimiento (C2)\no por riesgo (C3, informado\nal registrarse)", tam=5.9)
c.caja(4.15, 2.75, 1.7, 0.56, "Personal de atención\ncada consulta queda en\nla bitácora de accesos", relleno="blanco", tam=5.9)
c.caja(4.15, 3.44, 1.7, 0.56, "Administrador técnico\nsolo métricas agregadas\n(conteos < 5 suprimidos)", relleno="blanco", tam=5.9)
c.flecha(1.93, 3.37, 2.2, 3.37)
c.flecha(3.9, 3.03, 4.15, 3.03)
c.flecha(4.5, 2.46, 3.4, 2.75, etiqueta="motivo: códigos\ny regla aplicada", tam=5.6, desp=(0.75, 0.02), ha="left")
c.guardar("15_proteccion_datos.png")
