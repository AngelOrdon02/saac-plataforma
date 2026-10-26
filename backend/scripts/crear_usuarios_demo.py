"""Crea cuentas de demostración (solo para entornos de desarrollo o demo).

Uso:  python -m scripts.crear_usuarios_demo
"""
import uuid

from sqlalchemy import select

from app.config import obtener_configuracion
from app.db import nueva_sesion_nucleo
from app.modelos import Usuario
from app.seguridad.proteccion import cifrador_nucleo, generar_seudonimo, hashear_contrasena

CUENTAS = [
    ("Licda. Ana Morales (Psicología)", "psicologia@saac.demo", "ATENCION"),
    ("Administrador técnico", "admin@saac.demo", "ADMIN"),
    ("Estudiante de prueba", "estudiante@saac.demo", "ESTUDIANTE"),
]
CONTRASENA_DEMO = "Demo-SAAC-2026"


def main() -> None:
    if obtener_configuracion().entorno == "produccion":
        raise SystemExit("No se crean cuentas de demostración en producción.")
    sesion = nueva_sesion_nucleo()
    cif = cifrador_nucleo()
    try:
        for nombre, correo, rol in CUENTAS:
            if sesion.scalar(select(Usuario).where(Usuario.correo == correo)):
                continue
            uid = uuid.uuid4()
            sesion.add(Usuario(id=uid, correo=correo, hash_contrasena=hashear_contrasena(CONTRASENA_DEMO),
                               nombre_cifrado=cif.cifrar(nombre), rol=rol,
                               telefono_cifrado=cif.cifrar("5555-0000") if rol == "ESTUDIANTE" else None,
                               seudonimo=generar_seudonimo(uid)))
        sesion.commit()
        print(f"Cuentas de demostración listas (contraseña: {CONTRASENA_DEMO}).")
    finally:
        sesion.close()


if __name__ == "__main__":
    main()
