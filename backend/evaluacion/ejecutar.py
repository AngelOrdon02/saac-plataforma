"""Evaluación de la plataforma SAAC (capítulo 5 del trabajo de graduación).

Requiere PostgreSQL con las migraciones, las semillas, las cuentas de
demostración y la base de conocimiento indexada (igual que las pruebas de
integración). Uso, desde backend/:

    python -m evaluacion.ejecutar --superusuario postgresql://postgres@localhost:5432/saac

Los resultados se guardan en evaluacion/resultados/*.json.
"""
from __future__ import annotations

import argparse
import base64
import itertools
import json
import os
import platform
import statistics
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("SAAC_ENTORNO", "pruebas")
os.environ.setdefault("SAAC_SMTP_HOST", "127.0.0.1")
os.environ.setdefault("SAAC_SMTP_PUERTO", "2525")

import psycopg  # noqa: E402
import yaml  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from evaluacion import oraculo  # noqa: E402

DIR = Path(__file__).resolve().parent
RAIZ = DIR.parent
SALIDA = DIR / "resultados"
SALIDA.mkdir(exist_ok=True)


def guardar(nombre: str, datos) -> None:
    (SALIDA / f"{nombre}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def percentil(valores: list[float], p: float) -> float:
    v = sorted(valores)
    if not v:
        return float("nan")
    k = (len(v) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def resumen_tiempos(ms: list[float]) -> dict:
    return {"n": len(ms), "media": statistics.fmean(ms), "p50": percentil(ms, 50),
            "p95": percentil(ms, 95), "p99": percentil(ms, 99), "max": max(ms), "min": min(ms)}


# =============================================================================
# 1. Motor de reglas: casos M01–M18, determinismo y detectores
# =============================================================================


def parte_motor() -> dict:
    from app.canalizacion.deteccion import detector_riesgo, extractor_lexico
    from app.canalizacion.motor_reglas import Hechos, motor_reglas

    motor = motor_reglas()
    casos = yaml.safe_load((RAIZ / "tests/casos/casos_motor.yaml").read_text("utf-8"))
    filas = []
    for c in casos:
        d = motor.evaluar(Hechos(**c["hechos"]))
        obtenido = {"categoria": d.categoria, "accion": d.accion, "regla": d.regla}
        filas.append({"id": c["id"], "descripcion": c["descripcion"], "esperado": c["esperado"],
                      "obtenido": obtenido, "coincide": obtenido == c["esperado"],
                      "oraculo": dict(zip(("regla", "categoria", "accion"),
                                          oraculo.clasificar(Hechos(**c["hechos"]).como_dict())))})

    # Determinismo: 1 000 repeticiones de cada caso (decisión y traza idénticas)
    repeticiones, distintos = 1000, 0
    for c in casos:
        h = Hechos(**c["hechos"])
        firmas = {json.dumps([d.categoria, d.accion, d.regla, d.traza, d.supresion, d.huella])
                  for d in (motor.evaluar(h) for _ in range(repeticiones))}
        distintos += len(firmas) != 1

    # Detectores deterministas: 21 casos de texto del repositorio
    textos = yaml.safe_load((RAIZ / "tests/casos/casos_texto.yaml").read_text("utf-8"))
    det, ext = detector_riesgo(), extractor_lexico()
    det_filas = []
    for c in textos["riesgo"]:
        r = det.evaluar(c["texto"])
        det_filas.append({"texto": c["texto"], "esperado": [c["nivel"], c["verificar"]],
                          "obtenido": [r.nivel, r.requiere_verificacion],
                          "coincide": [r.nivel, r.requiere_verificacion] == [c["nivel"], c["verificar"]]})
    for c in textos["indicadores"]:
        cods = sorted(ext.extraer(c["texto"]))
        det_filas.append({"texto": c["texto"], "esperado": sorted(c["codigos"]), "obtenido": cods,
                          "coincide": cods == sorted(c["codigos"])})

    res = {"version_reglas": motor.version, "huella_reglas": motor.huella,
           "casos_motor": filas,
           "coincidencias_motor": sum(f["coincide"] for f in filas), "total_motor": len(filas),
           "coincidencias_con_oraculo": sum(f["oraculo"] == f["obtenido"] for f in filas),
           "determinismo": {"casos": len(casos), "repeticiones": repeticiones,
                            "evaluaciones": len(casos) * repeticiones, "casos_con_variacion": distintos},
           "detectores": det_filas,
           "coincidencias_detectores": sum(f["coincide"] for f in det_filas),
           "total_detectores": len(det_filas)}
    guardar("01_motor", res)
    return res


# =============================================================================
# 2. Verificación exhaustiva contra el oráculo y propiedades
# =============================================================================


def _espacio_phq9():
    yield None, None
    for total in range(28):
        for item9 in range(4):
            if item9 <= total and total - item9 <= 24:
                yield total, item9


def parte_exhaustiva() -> dict:
    from app.canalizacion.motor_reglas import Hechos, motor_reglas
    motor = motor_reglas()
    t0 = time.perf_counter()

    # Espacio A: todos los hechos de clasificación (sin supresiones)
    total_a, difs_a, por_regla = 0, [], Counter()
    gad_vals = [None, *range(22)]
    for nivel, req, vpos in itertools.product(range(4), (False, True), (False, True)):
        for (phq, i9), gad, ind, pers, det in itertools.product(
                list(_espacio_phq9()), gad_vals, range(7), (False, True), (False, True)):
            h = Hechos(nivel_riesgo=nivel, requiere_verificacion=req, verificacion_positiva=vpos,
                       phq9_total=phq, phq9_item9=i9, gad7_total=gad, indicadores_emocionales=ind,
                       persistencia=pers, deterioro_funcional=det)
            d = motor.evaluar(h)
            esperado = oraculo.clasificar(h.como_dict())
            total_a += 1
            por_regla[d.regla] += 1
            if (d.regla, d.categoria, d.accion) != esperado and len(difs_a) < 20:
                difs_a.append({"hechos": h.como_dict(), "motor": [d.regla, d.categoria, d.accion],
                               "oraculo": esperado})
    seg_a = time.perf_counter() - t0

    # Espacio B: valores límite combinados con los cuatro indicadores de supresión
    t1 = time.perf_counter()
    total_b, difs_b = 0, []
    phq_b = [(None, None), (4, 0), (5, 0), (9, 0), (10, 0), (15, 1), (19, 0)]
    gad_b = [None, 4, 5, 9, 10, 21]
    props = Counter()
    for nivel, req, vpos, (phq, i9), gad, ind, pers, det, tr, tor, dor, sa in itertools.product(
            range(4), (False, True), (False, True), phq_b, gad_b, range(5), (False, True),
            (False, True), (False, True), (False, True), (False, True), (False, True)):
        h = Hechos(nivel_riesgo=nivel, requiere_verificacion=req, verificacion_positiva=vpos,
                   phq9_total=phq, phq9_item9=i9, gad7_total=gad, indicadores_emocionales=ind,
                   persistencia=pers, deterioro_funcional=det, tamizaje_reciente=tr,
                   tamizaje_ofrecido_reciente=tor, derivacion_ofrecida_reciente=dor,
                   solicitud_activa=sa)
        d = motor.evaluar(h)
        esperado = oraculo.clasificar(h.como_dict())
        total_b += 1
        if (d.regla, d.categoria, d.accion) != esperado and len(difs_b) < 20:
            difs_b.append({"hechos": h.como_dict(), "motor": [d.regla, d.categoria, d.accion],
                           "oraculo": esperado})
        # P1: toda señal de riesgo produce C3 y PROTOCOLO_RIESGO
        hay_riesgo = nivel >= 1 or (i9 or 0) >= 1 or vpos
        if hay_riesgo:
            props["P1_casos"] += 1
            props["P1_cumple"] += d.categoria == "C3" and d.accion == "PROTOCOLO_RIESGO"
        # P2: las supresiones no cambian la categoría
        sin_sup = motor.evaluar(Hechos(**{**h.como_dict(), "tamizaje_reciente": False,
                                          "tamizaje_ofrecido_reciente": False,
                                          "derivacion_ofrecida_reciente": False,
                                          "solicitud_activa": False}))
        props["P2_casos"] += 1
        props["P2_cumple"] += sin_sup.categoria == d.categoria
        # P3: ninguna supresión se aplica al protocolo de riesgo
        if d.accion == "PROTOCOLO_RIESGO" or d.categoria == "C3":
            props["P3_casos"] += 1
            props["P3_cumple"] += d.supresion is None
    seg_b = time.perf_counter() - t1

    # P4: monotonicidad respecto al puntaje del PHQ-9 y de la GAD-7 (más puntaje,
    # nunca menor categoría), con el resto de los hechos fijos.
    mono_casos = mono_ok = 0
    for ind, pers, det in itertools.product(range(5), (False, True), (False, True)):
        for gad in gad_vals:
            prev = -1
            for total in range(25):  # ítem 9 = 0
                d = motor.evaluar(Hechos(phq9_total=total, phq9_item9=0, gad7_total=gad,
                                         indicadores_emocionales=ind, persistencia=pers,
                                         deterioro_funcional=det))
                nivel_cat = oraculo.NIVEL[d.categoria]
                mono_casos += 1
                mono_ok += nivel_cat >= prev
                prev = nivel_cat
    # P5: la ausencia de un cuestionario nunca activa R3 ni R5
    aus_casos = aus_ok = 0
    for ind, pers, det in itertools.product(range(7), (False, True), (False, True)):
        d = motor.evaluar(Hechos(indicadores_emocionales=ind, persistencia=pers, deterioro_funcional=det))
        aus_casos += 1
        aus_ok += d.regla not in ("R3", "R5")

    res = {"espacio_a": {"combinaciones": total_a, "discrepancias": len(difs_a),
                         "ejemplos": difs_a, "segundos": seg_a, "por_regla": dict(por_regla)},
           "espacio_b": {"combinaciones": total_b, "discrepancias": len(difs_b),
                         "ejemplos": difs_b, "segundos": seg_b},
           "propiedades": {
               "P1_riesgo_siempre_C3": [props["P1_cumple"], props["P1_casos"]],
               "P2_supresion_no_cambia_categoria": [props["P2_cumple"], props["P2_casos"]],
               "P3_sin_supresion_en_riesgo": [props["P3_cumple"], props["P3_casos"]],
               "P4_monotonicidad_puntajes": [mono_ok, mono_casos],
               "P5_ausencia_de_tamizaje": [aus_ok, aus_casos]}}
    guardar("02_exhaustiva", res)
    return res


# =============================================================================
# 3. Escenarios de extremo a extremo
# =============================================================================


class ProveedorInstrumentado:
    """Envuelve al proveedor real para registrar cada llamada y el texto enviado."""
    llamadas: list[dict] = []
    falla: bool = False

    def __init__(self, base):
        self.base = base
        self.nombre = base.nombre

    def generar(self, mensajes, **kw):
        ProveedorInstrumentado.llamadas.append(
            {"op": "generar", "contenido": " ".join(m["content"] for m in mensajes if m["role"] == "user")})
        if ProveedorInstrumentado.falla:
            from app.ia.proveedores import ErrorProveedorIA
            raise ErrorProveedorIA("servicio no disponible (simulación de falla)")
        return self.base.generar(mensajes, **kw)

    def embeber(self, textos):
        ProveedorInstrumentado.llamadas.append({"op": "embeber", "contenido": " ".join(textos)})
        if ProveedorInstrumentado.falla:
            from app.ia.proveedores import ErrorProveedorIA
            raise ErrorProveedorIA("servicio no disponible (simulación de falla)")
        return self.base.embeber(textos)


def _instalar_proveedor() -> None:
    import app.api.rutas_estudiante as rutas
    from app.ia.proveedores import obtener_proveedor
    rutas.obtener_proveedor = lambda: ProveedorInstrumentado(obtener_proveedor())


def _seudonimo(token: str) -> str:
    carga = token.split(".")[1]
    carga += "=" * (-len(carga) % 4)
    return json.loads(base64.urlsafe_b64decode(carga))["seu"]     # reclamo definido en seguridad/acceso.py


class SumideroSMTP:
    """Servidor SMTP mínimo que guarda los correos de notificación recibidos."""

    def __init__(self, puerto: int):
        from aiosmtpd.controller import Controller
        self.correos: list[dict] = []
        sumidero = self

        class Manejador:
            async def handle_DATA(self, server, session, envelope):
                sumidero.correos.append({"para": envelope.rcpt_tos,
                                         "contenido": envelope.content.decode("utf-8", "replace")})
                return "250 OK"

        self.controlador = Controller(Manejador(), hostname="127.0.0.1", port=puerto)

    def __enter__(self):
        self.controlador.start()
        return self

    def __exit__(self, *exc):
        self.controlador.stop()


def parte_escenarios(su: str) -> dict:
    from app.main import app
    _instalar_proveedor()
    cliente = TestClient(app)
    datos = yaml.safe_load((DIR / "escenarios_v1.yaml").read_text("utf-8"))
    bd = create_engine(su.replace("postgresql://", "postgresql+psycopg://"))

    def ultima_evaluacion(seu: str) -> dict:
        with bd.connect() as c:
            f = c.execute(text("SELECT id, categoria, accion, reglas_aplicadas, nivel_riesgo, origen "
                               "FROM canalizacion.evaluacion WHERE seudonimo=:s "
                               "ORDER BY creada_en DESC LIMIT 1"), {"s": seu}).mappings().first()
            return dict(f) if f else {}

    def solicitudes(seu: str) -> list[dict]:
        with bd.connect() as c:
            return [dict(r) for r in c.execute(text(
                "SELECT codigo, categoria, prioridad, estado, creada_en FROM canalizacion.solicitud_derivacion "
                "WHERE seudonimo=:s ORDER BY creada_en"), {"s": seu}).mappings()]

    pasos_res, escenarios_res = [], []
    textos_enviados = []
    with SumideroSMTP(int(os.environ["SAAC_SMTP_PUERTO"])) as smtp:
        for esc in datos["escenarios"]:
            correo = f"eval-{esc['id'].lower()}-{uuid.uuid4().hex[:6]}@prueba.gt"
            nombre = esc.get("nombre_registro", f"Estudiante Simulado {esc['id']}")
            r = cliente.post("/api/auth/registro", json={
                "nombre": nombre, "correo": correo, "contrasena": "Clave-Evaluacion-2026",
                "telefono": "5555-0101", "acepta_consentimiento": True})
            assert r.status_code == 201, r.text
            token = r.json()["token"]
            seu = _seudonimo(token)
            h = {"Authorization": f"Bearer {token}"}
            conv = cliente.post("/api/estudiante/conversaciones", json={}, headers=h).json()
            todos_ok = True
            for i, paso in enumerate(esc["pasos"], start=1):
                ProveedorInstrumentado.llamadas.clear()
                antes = solicitudes(seu)
                t0 = time.perf_counter()
                tipo = next(k for k in ("mensaje", "tamizaje", "verificacion", "rechazo",
                                        "aceptar_derivacion") if k in paso)
                if tipo == "mensaje":
                    r = cliente.post(f"/api/estudiante/conversaciones/{conv['id']}/mensajes",
                                     json={"texto": paso["mensaje"]}, headers=h)
                    cuerpo = r.json()
                    accion = cuerpo["accion"]
                    respuesta_ia = cuerpo["respuesta"] is not None
                elif tipo == "tamizaje":
                    r = cliente.post("/api/estudiante/tamizajes", json=paso["tamizaje"], headers=h)
                    accion, respuesta_ia = r.json(), False
                elif tipo == "verificacion":
                    r = cliente.post("/api/estudiante/verificacion",
                                     json={"respuesta": paso["verificacion"]}, headers=h)
                    accion, respuesta_ia = r.json(), False
                elif tipo == "rechazo":
                    r = cliente.post("/api/estudiante/ofertas/rechazo", json={"tipo": paso["rechazo"]},
                                     headers=h)
                    accion, respuesta_ia = {}, False
                else:
                    r = cliente.post("/api/estudiante/solicitudes", headers=h, json={
                        "preferencia": "CORREO", "disponibilidad": "Tardes",
                        "consiento_contacto": paso["aceptar_derivacion"]})
                    accion, respuesta_ia = (r.json() if r.status_code < 500 else {}), False
                ms = (time.perf_counter() - t0) * 1000
                llamadas = list(ProveedorInstrumentado.llamadas)
                textos_enviados.extend(x["contenido"] for x in llamadas)
                esp = paso.get("esperado")
                if esp is None:
                    continue
                ev = ultima_evaluacion(seu)
                despues = solicitudes(seu)
                fila = {"escenario": esc["id"], "grupo": esc["grupo"], "forma": esc["forma"],
                        "nivel": esc.get("nivel"), "paso": i, "tipo": tipo,
                        "entrada": paso.get(tipo), "esperado": esp, "estado_http": r.status_code,
                        "ms": ms, "llamadas_modelo": [x["op"] for x in llamadas],
                        "respuesta_ia": respuesta_ia}
                if tipo in ("mensaje", "tamizaje", "verificacion"):
                    fila.update({"categoria": ev.get("categoria"), "accion": accion.get("tipo"),
                                 "regla": (ev.get("reglas_aplicadas") or {}).get("regla"),
                                 "nivel_riesgo": ev.get("nivel_riesgo"),
                                 "recursos": [x["tipo"] for x in accion.get("recursos", [])],
                                 "solicitud": accion.get("solicitud_codigo")})
                    ok = fila["categoria"] == esp["categoria"] and fila["accion"] == esp["accion"]
                    if "prioridad" in esp:
                        activa = [s for s in despues if s["categoria"] == "C3"]
                        fila["prioridad"] = activa[-1]["prioridad"] if activa else None
                        fila["solicitudes_c3"] = len(activa)
                        ok = ok and fila["prioridad"] == esp["prioridad"]
                        if esp.get("misma_solicitud"):
                            ok = ok and len(activa) == 1
                    if esp.get("recursos"):
                        ok = ok and bool(fila["recursos"])
                    if esp.get("sin_solicitud"):
                        ok = ok and len(despues) == len(antes)
                else:   # aceptar_derivacion
                    nuevas = [s for s in despues if s["codigo"] not in {a["codigo"] for a in antes}]
                    fila["solicitud_creada"] = nuevas[0] if nuevas else None
                    if "estado_http" in esp:
                        ok = r.status_code == esp["estado_http"] and not nuevas
                    else:
                        ok = bool(nuevas) and nuevas[0]["categoria"] == esp["solicitud"] and \
                            nuevas[0]["prioridad"] == esp["prioridad"]
                fila["coincide"] = ok
                todos_ok &= ok
                pasos_res.append(fila)
            escenarios_res.append({"id": esc["id"], "grupo": esc["grupo"], "forma": esc["forma"],
                                   "coincide": todos_ok, "seudonimo": seu})
        time.sleep(0.5)
        correos = list(smtp.correos)

    # ---- métricas -------------------------------------------------------------
    clasif = [p for p in pasos_res if p["tipo"] in ("mensaje", "tamizaje", "verificacion")]
    matriz = defaultdict(Counter)
    for p in clasif:
        matriz[p["esperado"]["categoria"]][p["categoria"]] += 1
    por_grupo = defaultdict(lambda: [0, 0])
    for e in escenarios_res:
        por_grupo[e["grupo"]][0] += e["coincide"]
        por_grupo[e["grupo"]][1] += 1
    por_forma = defaultdict(lambda: [0, 0])
    for p in clasif:
        por_forma[p["forma"]][0] += p["coincide"]
        por_forma[p["forma"]][1] += 1
    res = {"escenarios": escenarios_res, "pasos": pasos_res,
           "resumen": {"escenarios": len(escenarios_res),
                       "escenarios_coinciden": sum(e["coincide"] for e in escenarios_res),
                       "pasos_evaluados": len(pasos_res),
                       "pasos_coinciden": sum(p["coincide"] for p in pasos_res),
                       "pasos_clasificacion": len(clasif),
                       "pasos_clasificacion_coinciden": sum(p["coincide"] for p in clasif),
                       "por_grupo": dict(por_grupo), "por_forma_pasos": dict(por_forma),
                       "matriz_confusion": {k: dict(v) for k, v in matriz.items()}},
           "correos": correos, "textos_enviados_al_modelo": textos_enviados}
    guardar("03_escenarios", res)
    return res


# =============================================================================
# 4. Trazabilidad
# =============================================================================


def parte_trazabilidad(su: str, escenarios: dict) -> dict:
    from app.auditoria.bitacora import verificar_cadena
    from app.canalizacion.motor_reglas import Hechos, motor_reglas
    from app.db import nueva_sesion_nucleo
    from app.modelos import BitacoraAcceso, BitacoraDecision

    motor = motor_reglas()
    bd = create_engine(su.replace("postgresql://", "postgresql+psycopg://"))
    with bd.connect() as c:
        evals = c.execute(text("SELECT id FROM canalizacion.evaluacion")).scalars().all()
        regs = [dict(r) for r in c.execute(text(
            "SELECT id, evaluacion_id, categoria, accion, reglas, evidencias, version_reglas, "
            "huella_reglas, registrado_en FROM auditoria.bitacora_decision ORDER BY id")).mappings()]
    por_eval = Counter(str(r["evaluacion_id"]) for r in regs)
    con_registro = sum(1 for e in evals if por_eval.get(str(e)) == 1)
    campos = ("categoria", "accion", "reglas", "evidencias", "version_reglas", "huella_reglas",
              "registrado_en")
    completos = sum(all(r.get(k) not in (None, "", {}) for k in campos) and
                    "hechos" in r["evidencias"] and "traza" in r["reglas"] for r in regs)
    huella_ok = sum(r["huella_reglas"] == motor.huella and r["version_reglas"] == motor.version
                    for r in regs)
    # Reproducibilidad: volver a evaluar los hechos registrados
    reproducidas, difs = 0, []
    for r in regs:
        d = motor.evaluar(Hechos(**r["evidencias"]["hechos"]))
        igual = (d.categoria, d.accion, d.regla, d.traza) == (
            r["categoria"], r["accion"], r["reglas"]["regla"], r["reglas"]["traza"])
        reproducidas += igual
        if not igual and len(difs) < 10:
            difs.append(r["id"])

    # Ausencia de texto de los mensajes en las tablas de canalización y auditoría
    textos = [p["entrada"] for p in escenarios["pasos"] if p["tipo"] == "mensaje"]
    fragmentos = {t[:25].lower() for t in textos if len(t) >= 25}
    with bd.connect() as c:
        volcado = " ".join(c.execute(text(
            "SELECT string_agg(t::text, ' ') FROM ("
            " SELECT row_to_json(x)::text t FROM auditoria.bitacora_decision x UNION ALL"
            " SELECT row_to_json(x)::text FROM auditoria.bitacora_acceso x UNION ALL"
            " SELECT row_to_json(x)::text FROM canalizacion.evaluacion x UNION ALL"
            " SELECT row_to_json(x)::text FROM canalizacion.senal x UNION ALL"
            " SELECT row_to_json(x)::text FROM canalizacion.solicitud_derivacion x UNION ALL"
            " SELECT row_to_json(x)::text FROM canalizacion.notificacion x) s")).scalars().all()
            or [""]).lower()
        volcado_mensajes = " ".join(c.execute(text(
            "SELECT string_agg(contenido_cifrado, ' ') FROM academico.mensaje")).scalars().all()
            or [""]).lower()
    fugas_auditoria = sum(f in volcado for f in fragmentos)
    fugas_mensajes = sum(f in volcado_mensajes for f in fragmentos)

    # Verificación de las cadenas y prueba de alteración
    s = nueva_sesion_nucleo()
    v_dec, v_acc = verificar_cadena(s, BitacoraDecision), verificar_cadena(s, BitacoraAcceso)
    s.close()
    pruebas = []
    with psycopg.connect(su, autocommit=True) as c:
        n = c.execute("SELECT count(*) FROM auditoria.bitacora_decision").fetchone()[0]
        objetivo = n // 2
        # (a) El rol de la aplicación no puede modificar ni borrar
        for sql in ("UPDATE auditoria.bitacora_decision SET categoria='C0' WHERE id=%s",
                    "DELETE FROM auditoria.bitacora_decision WHERE id=%s"):
            try:
                with psycopg.connect(su.replace("postgres@", "saac_app_nucleo@"), autocommit=True) as ca:
                    ca.execute(sql, (objetivo,))
                pruebas.append({"prueba": f"rol nucleo: {sql.split()[0]}", "bloqueado": False})
            except psycopg.Error as exc:
                pruebas.append({"prueba": f"rol nucleo: {sql.split()[0]}", "bloqueado": True,
                                "motivo": type(exc).__name__})
        # (b) Ni siquiera el superusuario puede, mientras los disparadores estén activos
        for sql in ("UPDATE auditoria.bitacora_decision SET categoria='C0' WHERE id=%s",
                    "DELETE FROM auditoria.bitacora_decision WHERE id=%s"):
            try:
                c.execute(sql, (objetivo,))
                pruebas.append({"prueba": f"superusuario: {sql.split()[0]}", "bloqueado": False})
            except psycopg.Error as exc:
                pruebas.append({"prueba": f"superusuario: {sql.split()[0]}", "bloqueado": True,
                                "motivo": str(exc).splitlines()[0]})
        try:
            c.execute("TRUNCATE auditoria.bitacora_decision")
            pruebas.append({"prueba": "superusuario: TRUNCATE", "bloqueado": False})
        except psycopg.Error as exc:
            pruebas.append({"prueba": "superusuario: TRUNCATE", "bloqueado": True,
                            "motivo": str(exc).splitlines()[0]})
        # (c) Alteración directa desactivando los disparadores (atacante con privilegios)
        alteraciones = []
        original = c.execute("SELECT categoria, accion FROM auditoria.bitacora_decision WHERE id=%s",
                             (objetivo,)).fetchone()
        c.execute("SET session_replication_role = replica")
        c.execute("UPDATE auditoria.bitacora_decision SET categoria='C0', accion='ACOMPANAMIENTO' "
                  "WHERE id=%s", (objetivo,))
        s = nueva_sesion_nucleo()
        alteraciones.append({"tipo": "modificar categoría y acción", "registro": objetivo,
                             **verificar_cadena(s, BitacoraDecision)})
        s.close()
        c.execute("UPDATE auditoria.bitacora_decision SET categoria=%s, accion=%s WHERE id=%s",
                  (*original, objetivo))
        fila = c.execute("SELECT * FROM auditoria.bitacora_decision WHERE id=%s", (objetivo,)).fetchone()
        cols = [d.name for d in c.execute("SELECT * FROM auditoria.bitacora_decision LIMIT 0").description]
        c.execute("DELETE FROM auditoria.bitacora_decision WHERE id=%s", (objetivo,))
        s = nueva_sesion_nucleo()
        alteraciones.append({"tipo": "eliminar un registro", "registro": objetivo,
                             **verificar_cadena(s, BitacoraDecision)})
        s.close()
        c.execute(f"INSERT INTO auditoria.bitacora_decision ({','.join(cols)}) VALUES "
                  f"({','.join(['%s'] * len(cols))})",
                  [json.dumps(v) if isinstance(v, dict) else v for v in fila])
        # (d) Recalcular el hash del registro alterado (sin recalcular los siguientes)
        from app.auditoria.bitacora import calcular_hash, CAMPOS
        c.execute("UPDATE auditoria.bitacora_decision SET categoria='C0', accion='ACOMPANAMIENTO' "
                  "WHERE id=%s", (objetivo,))
        s = nueva_sesion_nucleo()
        reg = s.get(BitacoraDecision, objetivo)
        datos = {k: getattr(reg, k) for k in CAMPOS[BitacoraDecision]}
        datos = {k: (str(v) if k.endswith("_id") and v is not None else v) for k, v in datos.items()}
        nuevo_hash = calcular_hash(reg.hash_anterior, datos)
        s.close()
        hash_original = fila[cols.index("hash_actual")]
        c.execute("UPDATE auditoria.bitacora_decision SET hash_actual=%s WHERE id=%s",
                  (nuevo_hash, objetivo))
        s = nueva_sesion_nucleo()
        alteraciones.append({"tipo": "modificar y recalcular su propio hash", "registro": objetivo,
                             **verificar_cadena(s, BitacoraDecision)})
        s.close()
        c.execute("UPDATE auditoria.bitacora_decision SET categoria=%s, accion=%s, hash_actual=%s "
                  "WHERE id=%s", (*original, hash_original, objetivo))
        c.execute("SET session_replication_role = origin")
    s = nueva_sesion_nucleo()
    restaurada = verificar_cadena(s, BitacoraDecision)
    s.close()

    res = {"evaluaciones": len(evals), "registros_bitacora": len(regs),
           "evaluaciones_con_un_registro": con_registro, "registros_completos": completos,
           "huella_y_version_vigentes": huella_ok, "decisiones_reproducidas": reproducidas,
           "no_reproducidas_ejemplos": difs,
           "fragmentos_de_texto_buscados": len(fragmentos), "fugas_en_canalizacion_y_auditoria": fugas_auditoria,
           "fragmentos_legibles_en_mensajes": fugas_mensajes,
           "verificacion": {"decisiones": v_dec, "accesos": v_acc},
           "proteccion_modificacion": pruebas, "alteraciones": alteraciones,
           "cadena_tras_restaurar": restaurada}
    guardar("04_trazabilidad", res)
    return res


# =============================================================================
# 5. Protocolo de escalamiento y falla segura
# =============================================================================


def parte_escalamiento(su: str, escenarios: dict) -> dict:
    from app.main import app
    _instalar_proveedor()
    cliente = TestClient(app, raise_server_exceptions=False)
    pasos = escenarios["pasos"]
    c3 = [p for p in pasos if p.get("categoria") == "C3"]
    c3_mensaje = [p for p in c3 if p["tipo"] == "mensaje"]
    orden_ok = sum(1 for p in c3 if p["recursos"] and p["recursos"][0] == "EMERGENCIA")
    sin_ia = sum(1 for p in c3 if not p["respuesta_ia"])
    sin_llamadas = sum(1 for p in c3_mensaje if not p["llamadas_modelo"])
    con_solicitud = sum(1 for p in c3 if p.get("solicitud"))
    prioridad_esperada = sum(1 for p in c3 if p.get("prioridad") == p["esperado"].get("prioridad"))
    verif = [p for p in pasos if p.get("accion") == "VERIFICAR_RIESGO"]
    verif_sin_ia = sum(1 for p in verif if not p["respuesta_ia"])

    # Notificaciones: contenido de los avisos y de los correos
    bd = create_engine(su.replace("postgresql://", "postgresql+psycopg://"))
    with bd.connect() as c:
        notifs = [dict(r) for r in c.execute(text(
            "SELECT n.canal, n.asunto, n.enviada, s.codigo, s.prioridad, s.categoria, "
            "EXTRACT(EPOCH FROM (n.creada_en - s.creada_en))*1000 AS ms "
            "FROM canalizacion.notificacion n JOIN canalizacion.solicitud_derivacion s "
            "ON s.id = n.solicitud_id")).mappings()]
        personal = c.execute(text("SELECT count(*) FROM identidad.usuario WHERE rol='ATENCION' "
                                  "AND activo")).scalar()
        solicitudes = [dict(r) for r in c.execute(text(
            "SELECT codigo, categoria, prioridad FROM canalizacion.solicitud_derivacion")).mappings()]
        nombres = [n for n in c.execute(text("SELECT correo FROM identidad.usuario WHERE rol='ESTUDIANTE'")).scalars()]
    correos = escenarios["correos"]
    sensibles = ["estudiante simulado", "ana lucía", "ana lucia", "5555-0101", "@prueba.gt", "202012345"]
    aviso_sin_datos = sum(1 for n in notifs if not any(x in n["asunto"].lower() for x in sensibles))
    correo_sin_datos = sum(1 for m in correos if not any(
        x in m["contenido"].lower().split("\n\n", 1)[-1] for x in sensibles))
    por_solicitud = Counter(n["codigo"] for n in notifs if n["canal"] == "APP")

    # Bandeja del personal: las críticas primero
    r = cliente.post("/api/auth/ingreso", json={"correo": "psicologia@saac.demo", "contrasena": "Demo-SAAC-2026"})
    hp = {"Authorization": f"Bearer {r.json()['token']}"}
    bandeja = cliente.get("/api/atencion/solicitudes", headers=hp).json()
    rango = {"CRITICA": 0, "ALTA": 1, "NORMAL": 2}
    orden_bandeja = all(rango[a["prioridad"]] <= rango[b["prioridad"]] for a, b in zip(bandeja, bandeja[1:]))

    # Registro de accesos del personal (RF-19): ver cada detalle y cambiar estados
    from app.auditoria.bitacora import verificar_cadena
    from app.db import nueva_sesion_nucleo
    from app.modelos import BitacoraAcceso
    vistas = sum(cliente.get(f"/api/atencion/solicitudes/{b['id']}", headers=hp).status_code == 200
                 for b in bandeja)
    cambios = [cliente.post(f"/api/atencion/solicitudes/{bandeja[0]['id']}/estado", headers=hp,
                            json={"estado": e, "comentario": "Seguimiento simulado"}).status_code
               for e in ("EN_REVISION", "CONTACTADO", "AGENDADA")]
    invalido = cliente.post(f"/api/atencion/solicitudes/{bandeja[1]['id']}/estado", headers=hp,
                            json={"estado": "AGENDADA"}).status_code       # NUEVA -> AGENDADA no permitida
    with bd.connect() as c:
        accesos = Counter(r[0] for r in c.execute(text("SELECT accion FROM auditoria.bitacora_acceso")))
    s_v = nueva_sesion_nucleo()
    cadena_accesos = verificar_cadena(s_v, BitacoraAcceso)
    s_v.close()
    registro_accesos = {"detalles_consultados": vistas, "cambios_http": cambios,
                        "transicion_invalida_http": invalido, "registros_por_accion": dict(accesos),
                        "cadena": cadena_accesos}

    # El estudiante no puede cancelar una solicitud por riesgo
    def nuevo_estudiante():
        r = cliente.post("/api/auth/registro", json={
            "nombre": "Estudiante Falla", "correo": f"falla-{uuid.uuid4().hex[:8]}@prueba.gt",
            "contrasena": "Clave-Evaluacion-2026", "telefono": "5555-0101",
            "acepta_consentimiento": True})
        h = {"Authorization": f"Bearer {r.json()['token']}"}
        conv = cliente.post("/api/estudiante/conversaciones", json={}, headers=h).json()
        return h, conv

    h, conv = nuevo_estudiante()
    s = cliente.post(f"/api/estudiante/conversaciones/{conv['id']}/mensajes",
                     json={"texto": "He pensado en quitarme la vida"}, headers=h).json()
    cancelar = cliente.post(f"/api/estudiante/solicitudes/{s['accion']['solicitud_codigo']}/cancelar",
                            headers=h).status_code

    # Falla segura 1: el servicio de modelos no está disponible
    ProveedorInstrumentado.falla = True
    falla_modelo = []
    for texto_msg in ("He pensado en quitarme la vida", "¿Cómo organizo mi semana de parciales?",
                      "Ya no puedo más con todo esto"):
        h, conv = nuevo_estudiante()
        r = cliente.post(f"/api/estudiante/conversaciones/{conv['id']}/mensajes",
                         json={"texto": texto_msg}, headers=h)
        cuerpo = r.json() if r.status_code == 200 else {}
        falla_modelo.append({"texto": texto_msg, "http": r.status_code,
                             "accion": cuerpo.get("accion", {}).get("tipo"),
                             "recursos": len(cuerpo.get("accion", {}).get("recursos", [])),
                             "respuesta": (cuerpo.get("respuesta") or {}).get("contenido", "")[:160],
                             "solicitud": cuerpo.get("accion", {}).get("solicitud_codigo")})
    ProveedorInstrumentado.falla = False

    # Falla segura 2: la propia capa de canalización falla
    import app.api.rutas_estudiante as rutas
    original = rutas.canalizacion.evaluar_mensaje

    def _falla(*a, **k):
        raise RuntimeError("falla simulada de la capa de canalización")
    rutas.canalizacion.evaluar_mensaje = _falla
    h, conv = nuevo_estudiante()
    r = cliente.post(f"/api/estudiante/conversaciones/{conv['id']}/mensajes",
                     json={"texto": "Me siento muy mal"}, headers=h)
    rutas.canalizacion.evaluar_mensaje = original
    cuerpo = r.json() if r.status_code == 200 else {}
    falla_canal = {"http": r.status_code, "accion": cuerpo.get("accion", {}).get("tipo"),
                   "tipos_recursos": sorted({x["tipo"] for x in cuerpo.get("accion", {}).get("recursos", [])})}

    res = {"pasos_c3": len(c3), "pasos_c3_por_mensaje": len(c3_mensaje),
           "recursos_emergencia_primero": orden_ok, "sin_respuesta_generada": sin_ia,
           "sin_llamadas_al_modelo": sin_llamadas, "con_solicitud": con_solicitud,
           "prioridad_correcta": prioridad_esperada,
           "pasos_verificacion": len(verif), "verificacion_sin_respuesta_generada": verif_sin_ia,
           "tiempos_c3_ms": resumen_tiempos([p["ms"] for p in c3]) if c3 else None,
           "notificaciones": {"total": len(notifs), "personal_activo": personal,
                              "solicitudes": len(solicitudes),
                              "solicitudes_notificadas_a_todo_el_personal":
                                  sum(1 for k, v in por_solicitud.items() if v >= personal),
                              "avisos_prioridad_elevada":
                                  sum(1 for n in notifs if "Prioridad elevada" in n["asunto"]),
                              "avisos_sin_datos_personales": aviso_sin_datos,
                              "correos": len(correos), "correos_sin_datos_personales": correo_sin_datos,
                              "retraso_ms": resumen_tiempos([float(n["ms"]) for n in notifs]) if notifs else None,
                              "ejemplo_asunto": notifs[0]["asunto"] if notifs else None,
                              "ejemplo_correo": correos[0]["contenido"][-420:] if correos else None},
           "bandeja_ordenada_por_prioridad": orden_bandeja, "bandeja_tamano": len(bandeja),
           "bandeja_primeras": [b["prioridad"] for b in bandeja[:5]],
           "registro_accesos": registro_accesos,
           "cancelar_solicitud_c3_http": cancelar,
           "falla_modelo": falla_modelo, "falla_canalizacion": falla_canal}
    guardar("05_escalamiento", res)
    return res


# =============================================================================
# 6. Requerimientos no funcionales verificables en este entorno
# =============================================================================


def parte_rnf(su: str, escenarios: dict) -> dict:
    from app.main import app
    from app.seguridad.proteccion import depurar_identificadores
    res: dict = {}
    with psycopg.connect(su) as c:
        res["RNF01"] = {
            "mensajes": c.execute("SELECT count(*), count(*) FILTER (WHERE contenido_cifrado LIKE 'gAAAAA%') "
                                  "FROM academico.mensaje").fetchone(),
            "nombres": c.execute("SELECT count(*), count(*) FILTER (WHERE nombre_cifrado LIKE 'gAAAAA%') "
                                 "FROM identidad.usuario").fetchone(),
            "telefonos": c.execute("SELECT count(telefono_cifrado), count(*) FILTER (WHERE telefono_cifrado LIKE 'gAAAAA%') "
                                   "FROM identidad.usuario").fetchone(),
            "contactos": c.execute("SELECT count(*), count(*) FILTER (WHERE contacto_cifrado LIKE 'gAAAAA%') "
                                   "FROM canalizacion.solicitud_derivacion").fetchone(),
            "contrasenas_argon2id": c.execute("SELECT count(*), count(*) FILTER (WHERE hash_contrasena LIKE '$argon2id$%') "
                                              "FROM identidad.usuario").fetchone()}
    # RNF-02: el rol académico no puede leer los esquemas sensibles (y viceversa)
    intentos = []
    url_acad = su.replace("postgres@", "saac_app_academico@")
    url_nuc = su.replace("postgres@", "saac_app_nucleo@")
    for url, rol, tabla in [(url_acad, "academico", "identidad.usuario"),
                            (url_acad, "academico", "canalizacion.evaluacion"),
                            (url_acad, "academico", "canalizacion.solicitud_derivacion"),
                            (url_acad, "academico", "auditoria.bitacora_decision"),
                            (url_nuc, "nucleo", "academico.mensaje"),
                            (url_nuc, "nucleo", "academico.conversacion")]:
        try:
            with psycopg.connect(url) as c:
                c.execute(f"SELECT 1 FROM {tabla} LIMIT 1")
            intentos.append({"rol": rol, "tabla": tabla, "rechazado": False})
        except psycopg.errors.InsufficientPrivilege:
            intentos.append({"rol": rol, "tabla": tabla, "rechazado": True})
    res["RNF02"] = intentos
    # RNF-04: identificadores en el texto enviado al modelo
    enviados = " ".join(escenarios["textos_enviados_al_modelo"]).lower()
    pii = ["202012345", "ana.lopez@gmail.com", "ana lópez", "lópez", "5555-0101"]
    res["RNF04"] = {"textos_enviados": len(escenarios["textos_enviados_al_modelo"]),
                    "identificadores_presentes": [x for x in pii if x in enviados],
                    "marcadores_presentes": sorted({m for m in ("[nombre]", "[carne]", "[correo]",
                                                                "[telefono]", "[cui]") if m in enviados})}
    muestras = ["Me llamo Ana López, carné 202012345, cel 5555-0101, correo ana@gmail.com",
                "Mi DPI es 3006 61320 0101 y mi número +502 4123-4567",
                "Escríbeme a juan.perez@ingenieria.usac.edu.gt o al 41234567"]
    res["RNF04"]["muestras"] = [{"original": m, "depurado": depurar_identificadores(m, ["Ana López"])[0]}
                                for m in muestras]
    # RNF-10: documentación OpenAPI generada
    cliente = TestClient(app)
    esquema = cliente.get("/api/openapi.json")
    if esquema.status_code != 200:
        esquema = cliente.get(app.openapi_url or "/openapi.json")
    rutas = esquema.json().get("paths", {})
    res["RNF10"] = {"url": app.openapi_url, "http": esquema.status_code, "rutas": len(rutas),
                    "operaciones": sum(len(v) for v in rutas.values()),
                    "version_openapi": esquema.json().get("openapi")}
    guardar("06_rnf", res)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--superusuario", default="postgresql://postgres@localhost:5432/saac")
    ap.add_argument("--partes", default="motor,exhaustiva,escenarios,trazabilidad,escalamiento,rnf")
    a = ap.parse_args()
    partes = a.partes.split(",")
    entorno = {"fecha": datetime.now(UTC).isoformat(), "python": platform.python_version(),
               "sistema": platform.platform(), "procesadores": os.cpu_count()}
    guardar("00_entorno", entorno)
    if "motor" in partes:
        r = parte_motor()
        print("motor:", r["coincidencias_motor"], "/", r["total_motor"], "· detectores:",
              r["coincidencias_detectores"], "/", r["total_detectores"], "· determinismo:", r["determinismo"])
    if "exhaustiva" in partes:
        r = parte_exhaustiva()
        print("exhaustiva:", r["espacio_a"]["combinaciones"], r["espacio_a"]["discrepancias"],
              r["espacio_b"]["combinaciones"], r["espacio_b"]["discrepancias"], r["propiedades"])
    esc = None
    if "escenarios" in partes:
        esc = parte_escenarios(a.superusuario)
        print("escenarios:", json.dumps(esc["resumen"], ensure_ascii=False))
    if esc is None and (SALIDA / "03_escenarios.json").exists():
        esc = json.loads((SALIDA / "03_escenarios.json").read_text("utf-8"))
    if "trazabilidad" in partes:
        r = parte_trazabilidad(a.superusuario, esc)
        print("trazabilidad:", {k: v for k, v in r.items() if k not in ("alteraciones", "verificacion")})
        print("alteraciones:", r["alteraciones"])
    if "escalamiento" in partes:
        r = parte_escalamiento(a.superusuario, esc)
        print("escalamiento:", json.dumps(r, ensure_ascii=False, default=str)[:3000])
    if "rnf" in partes:
        r = parte_rnf(a.superusuario, esc)
        print("rnf:", json.dumps(r, ensure_ascii=False, default=str)[:3000])


if __name__ == "__main__":
    main()
