"""Configuración de la plataforma.

Todos los valores se leen de variables de entorno con el prefijo ``SAAC_`` (o de
un archivo ``.env``). Ningún secreto se escribe en el código fuente.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parent.parent


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAAC_", env_file=".env", extra="ignore")

    entorno: Literal["desarrollo", "pruebas", "produccion"] = "desarrollo"

    # --- Base de datos: dos conexiones con roles distintos (mínimo privilegio) ---
    url_bd_nucleo: str = "postgresql+psycopg://saac_app_nucleo:cambiar@localhost:5432/saac"
    url_bd_academico: str = "postgresql+psycopg://saac_app_academico:cambiar@localhost:5432/saac"

    # --- Seguridad ---
    clave_jwt: str = "cambiar-en-produccion-por-una-clave-larga-y-aleatoria"
    minutos_expiracion_token: int = 120
    clave_seudonimo: str = "cambiar-clave-hmac-seudonimos"
    # Claves Fernet (32 bytes en base64 URL-safe). Generar con:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    clave_cifrado_nucleo: str = "2hYp3m6mJb3Qk8Hn5w6yQe0m5n9H0x7m2Jc4m7rT6aY="
    clave_cifrado_mensajes: str = "Wq9mZ0hX3c7mPq1sVb6nT4yR8uK2dF5gJ7lN0pA3eC8="
    dominios_correo_permitidos: list[str] = []          # vacío = cualquier dominio
    version_consentimiento: str = "1.0"

    # --- Proveedor de modelos de lenguaje ---
    # 'simulado'            -> sin modelo real; útil para pruebas y demostraciones sin GPU
    # 'openai_compatible'   -> cualquier servicio con la API de OpenAI: Ollama (local,
    #                          código abierto), vLLM, LM Studio u otros servicios comerciales
    proveedor_ia: Literal["simulado", "openai_compatible"] = "simulado"
    ia_url_base: str = "http://localhost:11434/v1"
    ia_clave_api: str = "ollama"
    ia_modelo_chat: str = "qwen2.5:7b-instruct"
    ia_modelo_embeddings: str = "bge-m3"
    ia_dimension_embeddings: int = 1024
    ia_temperatura: float = 0.3
    ia_tiempo_espera_s: float = 90.0
    ia_extractor_habilitado: bool = True
    ia_max_historial: int = 6

    # --- Recuperación (RAG) ---
    rag_k: int = 4
    rag_similitud_minima: float = 0.20

    # --- Reglas versionadas ---
    ruta_criterios: Path = RAIZ_BACKEND / "reglas" / "criterios_v1.0.0.yaml"
    ruta_lexico_riesgo: Path = RAIZ_BACKEND / "reglas" / "lexico_riesgo_v1.0.0.yaml"
    ruta_lexico_indicadores: Path = RAIZ_BACKEND / "reglas" / "lexico_indicadores_v1.0.0.yaml"
    ruta_instrumentos: Path = RAIZ_BACKEND / "reglas" / "instrumentos.yaml"
    ruta_conocimiento: Path = RAIZ_BACKEND / "conocimiento"

    # --- Notificaciones por correo (opcional) ---
    smtp_host: str | None = None
    smtp_puerto: int = 1025
    smtp_remitente: str = "saac-notificaciones@localhost"
    url_publica: str = "http://localhost:8080"

    # --- Privacidad y retención ---
    umbral_k_anonimato: int = 5           # conteos menores se muestran como "<k"
    retencion_mensajes_dias: int = 180

    # --- Extensión MCP (prototipo, deshabilitada si no hay clave) ---
    clave_api_mcp: str | None = None

    cors_origenes: list[str] = ["http://localhost:5173", "http://localhost:8080"]


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
