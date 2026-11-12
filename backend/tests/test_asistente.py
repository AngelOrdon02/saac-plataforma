"""Falla segura del asistente académico cuando el servicio de modelos no responde.
No requiere base de datos: la búsqueda falla antes de consultar la sesión."""
from app.academico.asistente import RESPUESTA_SIN_SERVICIO_GENERAL, responder
from app.ia.proveedores import ErrorProveedorIA


class ProveedorCaido:
    nombre = "caido"

    def generar(self, mensajes, **kw):
        raise ErrorProveedorIA("servicio no disponible")

    def embeber(self, textos):
        raise ErrorProveedorIA("servicio no disponible")


def test_respuesta_degradada_si_fallan_embeddings_y_generacion() -> None:
    r = responder(None, ProveedorCaido(), [], "¿Cómo organizo mi semana de parciales?")
    assert r.degradada is True
    assert r.texto == RESPUESTA_SIN_SERVICIO_GENERAL
    assert r.fuentes == []
