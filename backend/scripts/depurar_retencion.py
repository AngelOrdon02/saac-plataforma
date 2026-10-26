"""Aplica la política de retención: elimina las conversaciones académicas sin
actividad durante más de SAAC_RETENCION_MENSAJES_DIAS días, y las evaluaciones
y señales antiguas que no dieron origen a una solicitud. Las bitácoras (que no
contienen texto libre) se conservan.

Uso (p. ej. con cron, una vez al día):  python -m scripts.depurar_retencion
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.config import obtener_configuracion
from app.db import nueva_sesion_academica, nueva_sesion_nucleo
from app.modelos import Conversacion, Evaluacion, Oferta, SolicitudDerivacion


def main() -> None:
    limite = datetime.now(UTC) - timedelta(days=obtener_configuracion().retencion_mensajes_dias)
    s_acad, s_nucleo = nueva_sesion_academica(), nueva_sesion_nucleo()
    try:
        n_conv = s_acad.execute(delete(Conversacion).where(Conversacion.actualizada_en < limite)).rowcount
        con_solicitud = select(SolicitudDerivacion.evaluacion_id)
        s_nucleo.execute(delete(Oferta).where(Oferta.creada_en < limite))
        n_eval = s_nucleo.execute(delete(Evaluacion).where(
            Evaluacion.creada_en < limite, Evaluacion.id.not_in(con_solicitud))).rowcount
        s_acad.commit()
        s_nucleo.commit()
        print(f"Retención aplicada: {n_conv} conversaciones y {n_eval} evaluaciones eliminadas.")
    finally:
        s_acad.close()
        s_nucleo.close()


if __name__ == "__main__":
    main()
