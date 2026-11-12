"""Desempeño técnico de la plataforma (sección 5.5).

1. Tiempo de la clasificación determinista (detector, extractor léxico y motor).
2. Tiempo de la evaluación completa de un mensaje en la capa de canalización,
   con la base de datos (criterio RNF-06: percentil 95 < 300 ms sin el modelo).
3. Tiempo de respuesta de la API por HTTP con distintos niveles de concurrencia.
4. Disponibilidad y consumo de recursos bajo carga sostenida.

Uso, desde backend/ y con la API levantada en http://127.0.0.1:8000:

    python -m evaluacion.desempeno --duracion 300
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import threading
import time
import uuid
from pathlib import Path

import httpx
import psutil
import yaml

from evaluacion.ejecutar import guardar, percentil, resumen_tiempos

DIR = Path(__file__).resolve().parent
API = "http://127.0.0.1:8000"


def textos_escenarios() -> list[str]:
    datos = yaml.safe_load((DIR / "escenarios_v1.yaml").read_text("utf-8"))
    return [p["mensaje"] for e in datos["escenarios"] for p in e["pasos"] if "mensaje" in p]


def mezcla_de_carga() -> list[str]:
    """Mezcla de carga: 266 académicas (67 %), 115 emocionales o ambiguas (29 %) y 14 de
    riesgo (4 %) por cada 395 mensajes."""
    datos = yaml.safe_load((DIR / "escenarios_v1.yaml").read_text("utf-8"))
    por_grupo: dict[str, list[str]] = {}
    for e in datos["escenarios"]:
        for p in e["pasos"]:
            if "mensaje" in p:
                por_grupo.setdefault(e["grupo"], []).append(p["mensaje"])
    academicas = por_grupo["G1"] + por_grupo["G2"] + por_grupo["G3"]
    emocionales = por_grupo["G4"] + por_grupo["G5"] + por_grupo["G7"]
    riesgo = por_grupo["G8"]
    return academicas * 14 + emocionales * 5 + riesgo * 1


# -----------------------------------------------------------------------------
# 1 y 2. Mediciones dentro del proceso
# -----------------------------------------------------------------------------


def en_proceso(iteraciones: int) -> dict:
    from app.canalizacion.deteccion import detector_riesgo, extractor_lexico
    from app.canalizacion.motor_reglas import Hechos, motor_reglas
    from app.canalizacion.servicio import evaluar_mensaje
    from app.db import nueva_sesion_nucleo
    from app.ia.proveedores import obtener_proveedor
    from app.modelos import Usuario
    from sqlalchemy import select

    textos = textos_escenarios()
    det, ext, motor = detector_riesgo(), extractor_lexico(), motor_reglas()
    for t in textos:                      # calentamiento
        det.evaluar(t), ext.extraer(t)
    ms = []
    for i in range(iteraciones):
        t = textos[i % len(textos)]
        t0 = time.perf_counter()
        r = det.evaluar(t)
        cods = ext.extraer(t)
        motor.evaluar(Hechos(nivel_riesgo=r.nivel, requiere_verificacion=r.requiere_verificacion,
                             indicadores_emocionales=len(cods)))
        ms.append((time.perf_counter() - t0) * 1000)
    deterministas = resumen_tiempos(ms)

    proveedor = obtener_proveedor()
    s = nueva_sesion_nucleo()
    seu = s.scalar(select(Usuario.seudonimo).where(Usuario.rol == "ESTUDIANTE").limit(1))
    ms_bd = []
    n_bd = max(500, iteraciones // 10)
    for i in range(n_bd):
        t = textos[i % len(textos)]
        t0 = time.perf_counter()
        evaluar_mensaje(s, proveedor, seudonimo=seu, conversacion_id=uuid.uuid4(),
                        mensaje_id=uuid.uuid4(), texto=t, nombres=[])
        s.flush()
        ms_bd.append((time.perf_counter() - t0) * 1000)
        s.rollback()                      # no se conservan las evaluaciones de la medición
    s.close()
    return {"clasificacion_determinista": deterministas,
            "canalizacion_con_base_de_datos": resumen_tiempos(ms_bd)}


# -----------------------------------------------------------------------------
# 3 y 4. Mediciones por HTTP
# -----------------------------------------------------------------------------


async def preparar_usuarios(cliente: httpx.AsyncClient, n: int) -> list[dict]:
    usuarios = []
    for i in range(n):
        r = await cliente.post("/api/auth/registro", json={
            "nombre": f"Carga {i}", "correo": f"carga-{i}-{uuid.uuid4().hex[:6]}@prueba.gt",
            "contrasena": "Clave-Carga-2026", "telefono": "5555-0101", "acepta_consentimiento": True})
        h = {"Authorization": f"Bearer {r.json()['token']}"}
        conv = (await cliente.post("/api/estudiante/conversaciones", json={}, headers=h)).json()
        usuarios.append({"h": h, "conv": conv["id"], "enviados": 0})
    return usuarios


async def enviar(cliente: httpx.AsyncClient, u: dict, texto: str) -> tuple[float, int]:
    if u["enviados"] and u["enviados"] % 10 == 0:          # conversaciones de 10 mensajes
        u["conv"] = (await cliente.post("/api/estudiante/conversaciones", json={},
                                        headers=u["h"])).json()["id"]
    t0 = time.perf_counter()
    try:
        r = await cliente.post(f"/api/estudiante/conversaciones/{u['conv']}/mensajes",
                               json={"texto": texto}, headers=u["h"])
        codigo = r.status_code
    except httpx.HTTPError:
        codigo = 0
    u["enviados"] += 1
    return (time.perf_counter() - t0) * 1000, codigo


async def escalon(concurrencia: int, por_usuario: int, mezcla: list[str]) -> dict:
    async with httpx.AsyncClient(base_url=API, timeout=60) as cliente:
        usuarios = await preparar_usuarios(cliente, concurrencia)
        rnd = random.Random(concurrencia)
        resultados: list[tuple[float, int]] = []

        async def virtual(u):
            for _ in range(por_usuario):
                resultados.append(await enviar(cliente, u, rnd.choice(mezcla)))

        t0 = time.perf_counter()
        await asyncio.gather(*(virtual(u) for u in usuarios))
        duracion = time.perf_counter() - t0
    ok = [ms for ms, c in resultados if c == 200]
    return {"concurrencia": concurrencia, "solicitudes": len(resultados), "exitosas": len(ok),
            "errores": len(resultados) - len(ok), "duracion_s": duracion,
            "rendimiento_rps": len(resultados) / duracion, **resumen_tiempos(ok)}


def procesos_objetivo() -> dict[str, list[psutil.Process]]:
    grupos: dict[str, list[psutil.Process]] = {"api": [], "postgres": []}
    for p in psutil.process_iter(["name", "cmdline"]):
        cmd = " ".join(p.info["cmdline"] or [])
        if "uvicorn" in cmd and "app.main:app" in cmd:
            grupos["api"].append(p)
        elif (p.info["name"] or "").startswith("postgres"):
            grupos["postgres"].append(p)
    return grupos


class Muestreador(threading.Thread):
    def __init__(self, intervalo: float = 1.0):
        super().__init__(daemon=True)
        self.intervalo, self.activo, self.muestras = intervalo, True, []
        self.grupos = procesos_objetivo()
        for ps in self.grupos.values():
            for p in ps:
                p.cpu_percent(None)

    def run(self):
        while self.activo:
            time.sleep(self.intervalo)
            fila = {"t": time.time()}
            for nombre, ps in self.grupos.items():
                cpu = mem = 0.0
                for p in ps:
                    try:
                        cpu += p.cpu_percent(None)
                        mem += p.memory_info().rss / 2**20
                    except psutil.NoSuchProcess:
                        pass
                fila[f"{nombre}_cpu"], fila[f"{nombre}_mem_mb"] = cpu, mem
            fila["sistema_mem_mb"] = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 2**20
            self.muestras.append(fila)


async def sostenida(concurrencia: int, duracion_s: int, mezcla: list[str]) -> dict:
    async with httpx.AsyncClient(base_url=API, timeout=60) as cliente:
        usuarios = await preparar_usuarios(cliente, concurrencia)
        rnd = random.Random(7)
        resultados: list[tuple[float, float, int]] = []
        fin = time.perf_counter() + duracion_s
        muestreador = Muestreador()
        muestreador.start()

        async def virtual(u):
            while time.perf_counter() < fin:
                ms, c = await enviar(cliente, u, rnd.choice(mezcla))
                resultados.append((time.time(), ms, c))
                await asyncio.sleep(rnd.uniform(0.5, 1.5))      # tiempo de lectura y escritura

        t0 = time.perf_counter()
        await asyncio.gather(*(virtual(u) for u in usuarios))
        total = time.perf_counter() - t0
        muestreador.activo = False
        muestreador.join()
    ok = [ms for _, ms, c in resultados if c == 200]
    m = muestreador.muestras

    def serie(k):
        v = [x[k] for x in m]
        return {"media": statistics.fmean(v), "max": max(v)} if v else None

    # Latencia por minuto para observar la estabilidad
    inicio = resultados[0][0] if resultados else 0
    por_minuto: dict[int, list[float]] = {}
    for t, ms, c in resultados:
        if c == 200:
            por_minuto.setdefault(int((t - inicio) // 60), []).append(ms)
    return {"concurrencia": concurrencia, "duracion_s": total, "solicitudes": len(resultados),
            "exitosas": len(ok), "errores": len(resultados) - len(ok),
            "disponibilidad_pct": 100 * len(ok) / len(resultados) if resultados else 0,
            "rendimiento_rps": len(resultados) / total, "latencia": resumen_tiempos(ok),
            "p95_por_minuto": {k: percentil(v, 95) for k, v in sorted(por_minuto.items())},
            "api_cpu_pct": serie("api_cpu"), "api_mem_mb": serie("api_mem_mb"),
            "postgres_cpu_pct": serie("postgres_cpu"), "postgres_mem_mb": serie("postgres_mem_mb"),
            "sistema_mem_mb": serie("sistema_mem_mb"), "muestras": len(m),
            "serie": [{k: round(v, 2) for k, v in x.items()} for x in m]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteraciones", type=int, default=10000)
    ap.add_argument("--duracion", type=int, default=300)
    ap.add_argument("--concurrencia-sostenida", type=int, default=20)
    ap.add_argument("--partes", default="proceso,escalones,sostenida")
    a = ap.parse_args()
    res = {"procesadores": os.cpu_count(), "memoria_total_mb": psutil.virtual_memory().total / 2**20}
    mezcla = mezcla_de_carga()
    if "proceso" in a.partes:
        res["en_proceso"] = en_proceso(a.iteraciones)
        print(json.dumps(res["en_proceso"], indent=1))
    if "escalones" in a.partes:
        res["escalones"] = []
        for c in (1, 5, 10, 20, 40):
            r = asyncio.run(escalon(c, max(10, 400 // c), mezcla))
            print(json.dumps(r))
            res["escalones"].append(r)
    if "sostenida" in a.partes:
        res["sostenida"] = asyncio.run(sostenida(a.concurrencia_sostenida, a.duracion, mezcla))
        print(json.dumps({k: v for k, v in res["sostenida"].items() if k != "serie"}, indent=1))
    guardar("07_desempeno", res)


if __name__ == "__main__":
    main()
