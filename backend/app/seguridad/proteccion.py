"""Primitivas de protección de datos: seudonimización, cifrado, contraseñas y
depuración de identificadores antes de enviar texto a servicios externos."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import unicodedata
import uuid
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet

from app.config import obtener_configuracion

# ---------------------------------------------------------------------------
# Seudonimización
# ---------------------------------------------------------------------------


def generar_seudonimo(usuario_id: uuid.UUID, clave: str | None = None) -> str:
    """HMAC-SHA256 del identificador del usuario, codificado en base32 y truncado
    a 24 caracteres (120 bits). Sin la clave no es posible calcular el seudónimo a
    partir del id, ni revertirlo (Krawczyk et al., 1997)."""
    clave = clave or obtener_configuracion().clave_seudonimo
    resumen = hmac.new(clave.encode(), usuario_id.bytes, hashlib.sha256).digest()
    return base64.b32encode(resumen).decode().lower()[:24]


# ---------------------------------------------------------------------------
# Cifrado simétrico autenticado (Fernet: AES-128-CBC + HMAC-SHA256)
# ---------------------------------------------------------------------------


@lru_cache
def _fernet(clave: str) -> Fernet:
    return Fernet(clave.encode())


class Cifrador:
    def __init__(self, clave: str):
        self._f = _fernet(clave)

    def cifrar(self, texto: str) -> str:
        return self._f.encrypt(texto.encode("utf-8")).decode()

    def descifrar(self, token: str) -> str:
        return self._f.decrypt(token.encode()).decode("utf-8")

    def cifrar_json(self, datos: dict) -> str:
        return self.cifrar(json.dumps(datos, ensure_ascii=False))

    def descifrar_json(self, token: str) -> dict:
        return json.loads(self.descifrar(token))


def cifrador_nucleo() -> Cifrador:
    return Cifrador(obtener_configuracion().clave_cifrado_nucleo)


def cifrador_mensajes() -> Cifrador:
    return Cifrador(obtener_configuracion().clave_cifrado_mensajes)


# ---------------------------------------------------------------------------
# Contraseñas (Argon2id, RFC 9106)
# ---------------------------------------------------------------------------

_hasher = PasswordHasher()


def hashear_contrasena(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except VerifyMismatchError:
        return False


# ---------------------------------------------------------------------------
# Normalización y depuración de identificadores
# ---------------------------------------------------------------------------


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples. Se usa antes de aplicar
    los léxicos para que 'Ojalá' y 'ojala' coincidan."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto)
                         if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


_PATRONES_PII: list[tuple[str, re.Pattern[str]]] = [
    ("[CORREO]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("[CUI]", re.compile(r"\b\d{4}\s?\d{5}\s?\d{4}\b")),             # DPI de Guatemala (13 dígitos)
    ("[CARNE]", re.compile(r"\b(?:19|20)\d{7}\b")),                  # carné USAC (9 dígitos)
    ("[TELEFONO]", re.compile(r"(?:\+?502[\s-]?)?\b\d{4}[\s-]?\d{4}\b")),
]


def depurar_identificadores(texto: str, nombres: list[str] | None = None) -> tuple[str, int]:
    """Sustituye identificadores directos por marcadores antes de enviar el texto a
    un servicio externo de modelos de lenguaje (principio de minimización).

    Devuelve el texto depurado y la cantidad de sustituciones realizadas."""
    total = 0
    for marcador, patron in _PATRONES_PII:
        texto, n = patron.subn(marcador, texto)
        total += n
    for nombre in nombres or []:
        for parte in [p for p in nombre.split() if len(p) >= 3]:
            texto, n = re.subn(rf"\b{re.escape(parte)}\b", "[NOMBRE]", texto, flags=re.IGNORECASE)
            total += n
    return texto, total
