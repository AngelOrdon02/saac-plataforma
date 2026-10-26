"""Punto de entrada de la API de SAAC."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import rutas_admin, rutas_atencion, rutas_auth, rutas_estudiante, rutas_publicas
from app.config import Configuracion, obtener_configuracion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

cfg = obtener_configuracion()

if cfg.entorno == "produccion":
    # Las claves de ejemplo del código solo sirven para desarrollo.
    for campo in ("clave_jwt", "clave_seudonimo", "clave_cifrado_nucleo", "clave_cifrado_mensajes"):
        if getattr(cfg, campo) == Configuracion.model_fields[campo].default:
            raise RuntimeError(f"Configure SAAC_{campo.upper()} antes de ejecutar en producción")

app = FastAPI(
    title="SAAC · Sistema de Acompañamiento Académico y Canalización",
    description=("API de la plataforma de acompañamiento académico asistido por inteligencia "
                 "artificial con canalización hacia servicios de atención psicológica "
                 "universitaria (USAC, Escuela de Ingeniería en Ciencias y Sistemas)."),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origenes, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for modulo in (rutas_publicas, rutas_auth, rutas_estudiante, rutas_atencion, rutas_admin):
    app.include_router(modulo.router)
