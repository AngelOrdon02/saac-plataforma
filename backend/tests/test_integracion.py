"""Pruebas de integración de extremo a extremo (requieren PostgreSQL con las
migraciones aplicadas). Se omiten automáticamente si la base no está disponible.

    SAAC_PRUEBAS_INTEGRACION=1 python -m pytest tests/test_integracion.py
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(os.getenv("SAAC_PRUEBAS_INTEGRACION") != "1",
                                reason="Defina SAAC_PRUEBAS_INTEGRACION=1 para ejecutarlas")


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    from app.main import app
    return TestClient(app)


def _estudiante(cliente: TestClient) -> dict:
    correo = f"est-{uuid.uuid4().hex[:8]}@prueba.gt"
    r = cliente.post("/api/auth/registro", json={
        "nombre": "Estudiante Prueba", "correo": correo, "contrasena": "Clave-Prueba-123",
        "telefono": "5555-0101", "acepta_consentimiento": True})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _ingresar(cliente: TestClient, correo: str) -> dict:
    r = cliente.post("/api/auth/ingreso", json={"correo": correo, "contrasena": "Demo-SAAC-2026"})
    assert r.status_code == 200, "Ejecute antes: python -m scripts.crear_usuarios_demo"
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _conversar(cliente: TestClient, h: dict, textos: list[str]) -> list[dict]:
    conv = cliente.post("/api/estudiante/conversaciones", json={}, headers=h).json()
    salidas = []
    for t in textos:
        r = cliente.post(f"/api/estudiante/conversaciones/{conv['id']}/mensajes",
                         json={"texto": t}, headers=h)
        assert r.status_code == 200
        salidas.append(r.json())
    return salidas


def test_consulta_academica_no_genera_ofrecimientos(cliente: TestClient) -> None:
    h = _estudiante(cliente)
    [s] = _conversar(cliente, h, ["¿Cómo me preparo para un examen parcial?"])
    assert s["accion"]["tipo"] == "ACOMPANAMIENTO"
    assert s["respuesta"] and s["respuesta"]["fuentes"]


def test_flujo_derivacion_ordinaria(cliente: TestClient) -> None:
    h = _estudiante(cliente)
    s = _conversar(cliente, h, ["Me siento triste y no puedo dormir"])
    assert s[0]["accion"]["tipo"] == "OFRECER_TAMIZAJE"
    r = cliente.post("/api/estudiante/tamizajes", json={"phq9": [2, 2, 2, 1, 1, 2, 1, 0, 0],
                                                        "gad7": [1, 1, 1, 1, 0, 0, 0]},
                     headers=h)
    assert r.json()["tipo"] == "OFRECER_DERIVACION"            # PHQ-9 = 11
    r = cliente.post("/api/estudiante/solicitudes", headers=h, json={
        "preferencia": "CORREO", "disponibilidad": "Tardes", "consiento_contacto": True})
    assert r.status_code == 201
    codigo = r.json()["codigo"]

    hp = _ingresar(cliente, "psicologia@saac.demo")
    bandeja = cliente.get("/api/atencion/solicitudes", headers=hp).json()
    sol = next(x for x in bandeja if x["codigo"] == codigo)
    assert sol["prioridad"] == "NORMAL" and sol["regla"] == "R3"
    detalle = cliente.get(f"/api/atencion/solicitudes/{sol['id']}", headers=hp).json()
    assert detalle["contacto"]["preferencia"] == "CORREO"
    assert "texto" not in str(detalle["resumen"]).lower()           # sin texto de conversaciones
    assert cliente.post(f"/api/atencion/solicitudes/{sol['id']}/estado", headers=hp,
                        json={"estado": "CONTACTADO"}).status_code == 409   # transición inválida
    for estado in ("EN_REVISION", "CONTACTADO", "AGENDADA"):
        assert cliente.post(f"/api/atencion/solicitudes/{sol['id']}/estado", headers=hp,
                            json={"estado": estado}).status_code == 200
    mias = cliente.get("/api/estudiante/solicitudes", headers=h).json()
    assert mias[0]["estado"] == "AGENDADA"


def test_flujo_escalamiento_prioritario(cliente: TestClient) -> None:
    h = _estudiante(cliente)
    [s] = _conversar(cliente, h, ["Ya tengo un plan para quitarme la vida"])
    assert s["accion"]["tipo"] == "PROTOCOLO_RIESGO"
    assert s["respuesta"] is None                                 # el modelo no responde
    assert any(r["tipo"] == "EMERGENCIA" for r in s["accion"]["recursos"])
    codigo = s["accion"]["solicitud_codigo"]
    hp = _ingresar(cliente, "psicologia@saac.demo")
    bandeja = cliente.get("/api/atencion/solicitudes", headers=hp).json()
    assert next(x for x in bandeja if x["codigo"] == codigo)["prioridad"] == "CRITICA"
    assert bandeja[0]["prioridad"] == "CRITICA"                    # primero en la bandeja
    notifs = cliente.get("/api/atencion/notificaciones", headers=hp).json()
    assert any(codigo in n["asunto"] for n in notifs)


def test_verificacion_directa(cliente: TestClient) -> None:
    h = _estudiante(cliente)
    [s] = _conversar(cliente, h, ["Ya no puedo más con todo"])
    assert s["accion"]["tipo"] == "VERIFICAR_RIESGO"
    r = cliente.post("/api/estudiante/verificacion", json={"respuesta": "SI"}, headers=h).json()
    assert r["tipo"] == "PROTOCOLO_RIESGO" and r["solicitud_codigo"]


def test_control_de_acceso(cliente: TestClient) -> None:
    h = _estudiante(cliente)
    hp = _ingresar(cliente, "psicologia@saac.demo")
    ha = _ingresar(cliente, "admin@saac.demo")
    assert cliente.get("/api/atencion/solicitudes", headers=h).status_code == 403
    assert cliente.get("/api/estudiante/conversaciones", headers=hp).status_code == 403
    assert cliente.get("/api/estudiante/conversaciones", headers=ha).status_code == 403
    assert cliente.get("/api/atencion/solicitudes", headers=ha).status_code == 403
    assert cliente.get("/api/admin/metricas", headers=hp).status_code == 403
    assert cliente.get("/api/admin/metricas").status_code == 401


def test_bitacoras_integras(cliente: TestClient) -> None:
    ha = _ingresar(cliente, "admin@saac.demo")
    v = cliente.get("/api/admin/bitacora/verificacion", headers=ha).json()
    assert v["decisiones"]["integra"] and v["accesos"]["integra"]
    assert v["decisiones"]["registros"] > 0
