"""Indexa (o reindexa) la base de conocimiento en pgvector.

Uso:  python -m scripts.indexar_conocimiento
"""
from app.academico.conocimiento import indexar_directorio
from app.db import nueva_sesion_academica
from app.ia.proveedores import obtener_proveedor


def main() -> None:
    sesion = nueva_sesion_academica()
    try:
        resumen = indexar_directorio(sesion, obtener_proveedor())
        sesion.commit()
        print(f"Base de conocimiento indexada: {resumen}")
    finally:
        sesion.close()


if __name__ == "__main__":
    main()
