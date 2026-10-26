"""Pruebas del adaptador compatible con la API de OpenAI usando un servidor
simulado (no requiere conexión ni modelo real)."""
import json

import httpx
import pytest

from app.config import Configuracion
from app.ia.proveedores import ErrorProveedorIA, ProveedorOpenAICompatible


def _proveedor(manejador) -> ProveedorOpenAICompatible:
    cfg = Configuracion(proveedor_ia="openai_compatible", ia_url_base="http://ollama:11434/v1",
                        ia_dimension_embeddings=4)
    p = ProveedorOpenAICompatible(cfg)
    p._cliente = httpx.Client(base_url=cfg.ia_url_base, transport=httpx.MockTransport(manejador))
    return p


def test_generar_envia_formato_openai() -> None:
    recibido = {}

    def manejador(req: httpx.Request) -> httpx.Response:
        recibido.update(json.loads(req.content))
        assert req.url.path.endswith("/chat/completions")
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hola"}}]})

    assert _proveedor(manejador).generar([{"role": "user", "content": "x"}], json_salida=True) == "Hola"
    assert recibido["model"] == "qwen2.5:7b-instruct"
    assert recibido["response_format"] == {"type": "json_object"}


def test_embeddings_validan_dimension() -> None:
    def manejador(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]})

    with pytest.raises(ErrorProveedorIA):
        _proveedor(manejador).embeber(["texto"])


def test_error_del_servicio_se_traduce() -> None:
    with pytest.raises(ErrorProveedorIA):
        _proveedor(lambda req: httpx.Response(503)).generar([{"role": "user", "content": "x"}])
