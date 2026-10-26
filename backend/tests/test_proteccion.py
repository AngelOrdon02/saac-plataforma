"""Pruebas de seudonimización, cifrado, depuración de identificadores y bitácora."""
import uuid

from cryptography.fernet import Fernet

from app.auditoria.bitacora import HASH_INICIAL, calcular_hash
from app.seguridad.proteccion import Cifrador, depurar_identificadores, generar_seudonimo


def test_seudonimo_estable_y_dependiente_de_la_clave() -> None:
    uid = uuid.uuid4()
    assert generar_seudonimo(uid, "clave-a") == generar_seudonimo(uid, "clave-a")
    assert generar_seudonimo(uid, "clave-a") != generar_seudonimo(uid, "clave-b")
    assert len(generar_seudonimo(uid, "clave-a")) == 24


def test_cifrado_ida_y_vuelta() -> None:
    c = Cifrador(Fernet.generate_key().decode())
    token = c.cifrar("Me siento triste")
    assert "triste" not in token and c.descifrar(token) == "Me siento triste"


def test_depuracion_de_identificadores() -> None:
    texto = ("Soy María López, carné 201905741, DPI 3006 61320 0101, "
             "mi correo es maria@ejemplo.com y mi número 5555-1234")
    depurado, n = depurar_identificadores(texto, ["María López"])
    for dato in ("201905741", "3006 61320 0101", "maria@ejemplo.com", "5555-1234", "López"):
        assert dato not in depurado
    assert n >= 5


def test_encadenamiento_detecta_alteracion() -> None:
    r1 = {"accion": "ACOMPANAMIENTO", "categoria": "C0"}
    h1 = calcular_hash(HASH_INICIAL, r1)
    r2 = {"accion": "PROTOCOLO_RIESGO", "categoria": "C3"}
    h2 = calcular_hash(h1, r2)
    alterado = {**r1, "categoria": "C1"}
    assert calcular_hash(HASH_INICIAL, alterado) != h1
    assert calcular_hash(calcular_hash(HASH_INICIAL, alterado), r2) != h2
