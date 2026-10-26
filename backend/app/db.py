"""Conexiones a la base de datos.

La plataforma mantiene DOS motores de conexión con roles distintos de PostgreSQL:

* ``motor_academico`` (rol ``rol_academico``): solo puede leer y escribir el
  esquema ``academico`` (conversaciones y base de conocimiento).
* ``motor_nucleo`` (rol ``rol_nucleo``): identidad, canalización y auditoría.

Así, la separación entre la capa de acompañamiento académico y la capa de
canalización no depende solo del código: la propia base de datos impide que la
capa académica lea información sensible.
"""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion


class Base(DeclarativeBase):
    pass


@lru_cache
def _fabrica_nucleo() -> sessionmaker[Session]:
    cfg = obtener_configuracion()
    motor = create_engine(cfg.url_bd_nucleo, pool_pre_ping=True, pool_size=5)
    return sessionmaker(bind=motor, expire_on_commit=False)


@lru_cache
def _fabrica_academica() -> sessionmaker[Session]:
    cfg = obtener_configuracion()
    motor = create_engine(cfg.url_bd_academico, pool_pre_ping=True, pool_size=5)
    return sessionmaker(bind=motor, expire_on_commit=False)


def sesion_nucleo() -> Iterator[Session]:
    sesion = _fabrica_nucleo()()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()


def sesion_academica() -> Iterator[Session]:
    sesion = _fabrica_academica()()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()


def nueva_sesion_nucleo() -> Session:
    """Sesión para scripts y tareas fuera de una petición HTTP."""
    return _fabrica_nucleo()()


def nueva_sesion_academica() -> Session:
    return _fabrica_academica()()
