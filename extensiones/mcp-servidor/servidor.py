"""Prototipo de servidor MCP (Model Context Protocol) para SAAC.

ESTADO: prueba de concepto para TRABAJO FUTURO (sección 3.3.5 del documento).
No forma parte del alcance evaluado de la plataforma.

Expone, como herramientas y recursos MCP, ÚNICAMENTE la capa de acompañamiento
académico y el directorio público de recursos de apoyo. Nunca expone datos de la
capa de canalización (señales, tamizajes o solicitudes) ni datos identificativos.
Así, cualquier agente de IA compatible con MCP —comercial o de código abierto—
puede consultar la base de conocimiento validada de la plataforma.

Uso con un cliente MCP (transporte stdio):
    SAAC_API_URL=http://localhost:8000 SAAC_CLAVE_API_MCP=... python servidor.py
"""
from __future__ import annotations

import os

import httpx
from mcp.server import MCPServer

API = os.environ.get("SAAC_API_URL", "http://localhost:8000").rstrip("/")
CLAVE = os.environ.get("SAAC_CLAVE_API_MCP", "")

servidor = MCPServer(
    name="saac-acompanamiento-academico",
    title="SAAC · Acompañamiento académico (USAC)",
    version="0.1.0",
    instructions=(
        "Herramientas de consulta sobre técnicas de estudio y gestión del tiempo basadas en "
        "evidencia, curadas para estudiantes de la Escuela de Ingeniería en Ciencias y Sistemas "
        "(USAC). Cita siempre la referencia de cada fragmento. Este servidor no ofrece "
        "diagnósticos ni atención en salud mental: si la persona expresa malestar emocional o "
        "señales de riesgo, muéstrale los recursos de 'listar_recursos_de_apoyo' y recomiéndale "
        "contactar a una persona del servicio de atención psicológica."),
)


def _get(ruta: str, **params) -> list[dict]:
    r = httpx.get(f"{API}{ruta}", params=params, headers={"X-Clave-API": CLAVE}, timeout=30)
    r.raise_for_status()
    return r.json()


@servidor.tool(title="Buscar técnicas de estudio",
               description="Busca en la base de conocimiento de SAAC fragmentos sobre técnicas de "
                           "estudio, gestión del tiempo y organización de tareas.")
def buscar_tecnicas_estudio(consulta: str, cantidad: int = 4) -> list[dict]:
    return _get("/api/integracion/conocimiento/buscar", q=consulta, k=cantidad)


@servidor.tool(title="Listar recursos de apoyo",
               description="Devuelve el directorio de servicios de atención psicológica de la "
                           "universidad, líneas de apoyo y números de emergencia.")
def listar_recursos_de_apoyo() -> list[dict]:
    return _get("/api/recursos")


@servidor.resource("saac://conocimiento/indice", name="indice-conocimiento",
                   title="Índice de la base de conocimiento", mime_type="application/json")
def indice_conocimiento() -> list[dict]:
    return _get("/api/integracion/conocimiento/indice")


if __name__ == "__main__":
    servidor.run("stdio")
