"""Orquestación de la capa de clasificación y canalización.

Flujo para cada evento (mensaje, tamizaje o verificación):

1. Detección determinista de riesgo (léxico versionado).
2. Extracción de indicadores: léxico + modelo de lenguaje (opcional).
3. Persistencia de las señales (solo códigos, nunca texto).
4. Cálculo de los hechos dentro de la ventana de tiempo.
5. Evaluación del motor de reglas → categoría y acción.
6. Acciones: registrar ofrecimientos, crear solicitud prioritaria y notificar.
7. Registro de la decisión en la bitácora encadenada.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auditoria.bitacora import registrar_decision
from app.canalizacion import mensajes
from app.canalizacion.deteccion import (ExtractorModelo, Indicadores, ResultadoRiesgo,
                                        detector_riesgo, extractor_lexico)
from app.canalizacion.motor_reglas import Decision, Hechos, motor_reglas
from app.canalizacion.tamizaje import ResultadoTamizaje
from app.config import obtener_configuracion
from app.ia.proveedores import ProveedorIA
from app.modelos import (Evaluacion, Indicador, Oferta, RecursoAtencion, Senal,
                         SolicitudDerivacion, Tamizaje, Usuario)
from app.notificaciones import notificar_nueva_solicitud
from app.seguridad.proteccion import cifrador_nucleo, depurar_identificadores
from app.solicitudes.servicio import crear_solicitud, solicitud_activa


@dataclass
class ResultadoCanalizacion:
    evaluacion_id: uuid.UUID
    categoria: str
    accion: str
    regla: str
    texto: str | None = None                    # mensaje fijo para el estudiante
    recursos: list[dict] = field(default_factory=list)
    solicitud_codigo: str | None = None
    oferta_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Hechos
# ---------------------------------------------------------------------------


def calcular_hechos(sesion: Session, seudonimo: str, riesgo: ResultadoRiesgo | None = None,
                    verificacion_positiva: bool = False) -> Hechos:
    motor = motor_reglas()
    p = motor.parametros
    ahora = datetime.now(UTC)
    desde = ahora - timedelta(days=p["ventana_dias"])

    codigos = set(sesion.scalars(select(Senal.indicador_codigo).distinct().where(
        Senal.seudonimo == seudonimo, Senal.detectada_en >= desde)))
    catalogo = {i.codigo: i for i in sesion.scalars(select(Indicador))}
    emocionales = [catalogo[c] for c in codigos
                   if c in catalogo and catalogo[c].dominio in ("DEPRESIVO", "ANSIOSO")]
    propios = [i for i in emocionales if not i.compartido]
    compartidos = [i for i in emocionales if i.compartido]
    # Un indicador compartido (p. ej. falta de concentración) es también una dificultad
    # académica ordinaria: solo suma cuando existe al menos un indicador emocional propio.
    total_emocionales = len(propios) + (len(compartidos) if propios else 0)

    def ultimo(instr: str) -> Tamizaje | None:
        return sesion.scalar(select(Tamizaje).where(
            Tamizaje.seudonimo == seudonimo, Tamizaje.instrumento == instr,
            Tamizaje.aplicado_en >= desde).order_by(Tamizaje.aplicado_en.desc()).limit(1))

    phq9, gad7 = ultimo("PHQ9"), ultimo("GAD7")

    def ofrecido_reciente(tipo: str) -> bool:
        rechazo = ahora - timedelta(days=p["dias_espera_reoferta"])
        pendiente = ahora - timedelta(hours=p["horas_oferta_pendiente"])
        ofertas = sesion.scalars(select(Oferta).where(
            Oferta.seudonimo == seudonimo, Oferta.tipo == tipo, Oferta.creada_en >= rechazo))
        return any(o.respuesta == "RECHAZADA" or
                   (o.respuesta == "PENDIENTE" and o.creada_en >= pendiente) for o in ofertas)

    return Hechos(
        nivel_riesgo=riesgo.nivel if riesgo else 0,
        requiere_verificacion=bool(riesgo and riesgo.requiere_verificacion),
        verificacion_positiva=verificacion_positiva,
        phq9_total=phq9.puntaje_total if phq9 else None,
        phq9_item9=phq9.respuestas[8] if phq9 else None,
        gad7_total=gad7.puntaje_total if gad7 else None,
        indicadores_emocionales=total_emocionales,
        persistencia="T1" in codigos,
        deterioro_funcional="F1" in codigos,
        tamizaje_reciente=bool(phq9 or gad7),
        tamizaje_ofrecido_reciente=ofrecido_reciente("TAMIZAJE"),
        derivacion_ofrecida_reciente=ofrecido_reciente("DERIVACION"),
        solicitud_activa=solicitud_activa(sesion, seudonimo) is not None,
    )


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def recursos_activos(sesion: Session, tipos: set[str] | None = None) -> list[dict]:
    consulta = select(RecursoAtencion).where(RecursoAtencion.activo.is_(True)) \
        .order_by(RecursoAtencion.orden)
    return [{"id": r.id, "nombre": r.nombre, "tipo": r.tipo, "descripcion": r.descripcion,
             "ubicacion": r.ubicacion, "horario": r.horario, "telefono": r.telefono,
             "enlace": r.enlace, "procedimiento": r.procedimiento}
            for r in sesion.scalars(consulta) if not tipos or r.tipo in tipos]


def recursos_crisis(sesion: Session) -> list[dict]:
    """Ante una señal de riesgo se muestran primero los contactos inmediatos."""
    orden = {"EMERGENCIA": 0, "LINEA_APOYO": 1, "INSTITUCIONAL": 2}
    return sorted(recursos_activos(sesion), key=lambda r: orden[r["tipo"]])


def _resumen_para_personal(sesion: Session, seudonimo: str, decision: Decision, hechos: Hechos,
                           riesgo: ResultadoRiesgo | None) -> dict:
    """Resumen estructurado para el personal de atención: códigos, puntajes y la
    regla aplicada. No incluye el texto de las conversaciones."""
    desde = datetime.now(UTC) - timedelta(days=motor_reglas().parametros["ventana_dias"])
    codigos = sorted(set(sesion.scalars(select(Senal.indicador_codigo).where(
        Senal.seudonimo == seudonimo, Senal.detectada_en >= desde))))
    catalogo = {i.codigo: i for i in sesion.scalars(select(Indicador))}
    return {
        "regla": decision.regla,
        "nombre_regla": decision.nombre_regla,
        "fuentes": decision.fuentes,
        "version_reglas": decision.version,
        "nivel_riesgo": riesgo.nivel if riesgo else 0,
        "descripcion_riesgo": riesgo.nombre if riesgo and riesgo.nivel else None,
        "indicadores": [{"codigo": c, "descripcion": catalogo[c].descripcion,
                         "referencia": catalogo[c].referencia} for c in codigos if c in catalogo],
        "phq9_total": hechos.phq9_total,
        "gad7_total": hechos.gad7_total,
        "persistencia": hechos.persistencia,
        "deterioro_funcional": hechos.deterioro_funcional,
    }


def _prioridad(decision: Decision, riesgo: ResultadoRiesgo | None) -> str:
    if decision.categoria == "C3":
        return "CRITICA" if riesgo and riesgo.nivel >= 3 else "ALTA"
    return "NORMAL"


# ---------------------------------------------------------------------------
# Núcleo: evaluar, decidir, actuar y registrar
# ---------------------------------------------------------------------------


def _decidir_y_actuar(sesion: Session, *, seudonimo: str, origen: str, evaluacion: Evaluacion,
                      riesgo: ResultadoRiesgo | None, indicadores: Indicadores | None,
                      verificacion_positiva: bool = False, evidencia_extra: dict | None = None
                      ) -> ResultadoCanalizacion:
    hechos = calcular_hechos(sesion, seudonimo, riesgo, verificacion_positiva)
    decision = motor_reglas().evaluar(hechos)

    evaluacion.categoria = decision.categoria
    evaluacion.accion = decision.accion
    evaluacion.version_reglas = decision.version
    evaluacion.reglas_aplicadas = {"regla": decision.regla, "traza": decision.traza,
                                   "supresion": decision.supresion}
    sesion.flush()

    resultado = ResultadoCanalizacion(evaluacion.id, decision.categoria, decision.accion,
                                      decision.regla)

    if decision.accion == "PROTOCOLO_RIESGO":
        prioridad = _prioridad(decision, riesgo)
        resultado.texto = (mensajes.PROTOCOLO_RIESGO_INMINENTE if prioridad == "CRITICA"
                           else mensajes.PROTOCOLO_RIESGO)
        resultado.recursos = recursos_crisis(sesion)
        existente = solicitud_activa(sesion, seudonimo)
        if existente and existente.categoria == "C3":
            resultado.solicitud_codigo = existente.codigo
        else:
            usuario = sesion.scalar(select(Usuario).where(Usuario.seudonimo == seudonimo))
            cif = cifrador_nucleo()
            contacto = {"nombre": cif.descifrar(usuario.nombre_cifrado), "correo": usuario.correo,
                        "telefono": cif.descifrar(usuario.telefono_cifrado)
                        if usuario.telefono_cifrado else None,
                        "preferencia": "CUALQUIERA", "disponibilidad": "Contactar de inmediato",
                        "base_legal": "Consentimiento informado aceptado al registrarse"}
            solicitud = crear_solicitud(
                sesion, seudonimo=seudonimo, evaluacion_id=evaluacion.id, categoria="C3",
                prioridad=prioridad, resumen=_resumen_para_personal(sesion, seudonimo, decision,
                                                                    hechos, riesgo),
                contacto=contacto)
            notificar_nueva_solicitud(sesion, solicitud)
            resultado.solicitud_codigo = solicitud.codigo
    elif decision.accion == "VERIFICAR_RIESGO":
        resultado.texto = mensajes.VERIFICAR_RIESGO
    elif decision.accion in ("OFRECER_TAMIZAJE", "OFRECER_DERIVACION"):
        tipo = "TAMIZAJE" if decision.accion == "OFRECER_TAMIZAJE" else "DERIVACION"
        oferta = Oferta(seudonimo=seudonimo, tipo=tipo, evaluacion_id=evaluacion.id)
        sesion.add(oferta)
        sesion.flush()
        resultado.oferta_id = oferta.id
        resultado.texto = getattr(mensajes, decision.accion)
        if tipo == "DERIVACION":
            resultado.recursos = recursos_activos(sesion, {"INSTITUCIONAL"})
    elif decision.accion == "MONITOREO":
        resultado.texto = mensajes.MONITOREO
    elif decision.accion == "SEGUIMIENTO_SOLICITUD":
        activa = solicitud_activa(sesion, seudonimo)
        resultado.solicitud_codigo = activa.codigo if activa else None
        resultado.texto = mensajes.SEGUIMIENTO_SOLICITUD.format(codigo=resultado.solicitud_codigo)

    evidencias = {
        "patrones_riesgo": riesgo.patrones if riesgo else [],
        "indicadores_lexico": sorted(indicadores.lexico) if indicadores else [],
        "indicadores_modelo": sorted(indicadores.modelo) if indicadores else [],
        "hechos": hechos.como_dict(),
        **(evidencia_extra or {}),
    }
    if resultado.solicitud_codigo:
        evidencias["solicitud"] = resultado.solicitud_codigo
    registrar_decision(
        sesion, evaluacion_id=evaluacion.id, seudonimo=seudonimo, origen=origen,
        categoria=decision.categoria, accion=decision.accion,
        reglas={"regla": decision.regla, "traza": decision.traza, "supresion": decision.supresion},
        evidencias=evidencias, version_reglas=decision.version, huella_reglas=decision.huella,
        componente_modelo=indicadores.modelo_usado if indicadores else None)
    return resultado


def evaluar_mensaje(sesion: Session, proveedor: ProveedorIA, *, seudonimo: str,
                    conversacion_id: uuid.UUID, mensaje_id: uuid.UUID, texto: str,
                    nombres: list[str] | None = None) -> ResultadoCanalizacion:
    cfg = obtener_configuracion()
    riesgo = detector_riesgo().evaluar(texto)
    indicadores = Indicadores(lexico=extractor_lexico().extraer(texto))

    if cfg.ia_extractor_habilitado and riesgo.nivel == 0:
        catalogo = {i.codigo: i.descripcion for i in sesion.scalars(select(Indicador))}
        depurado, _ = depurar_identificadores(texto, nombres)
        codigos, posible = ExtractorModelo(proveedor, catalogo).extraer(depurado)
        indicadores.modelo = codigos - indicadores.lexico
        indicadores.modelo_usado = proveedor.nombre
        if posible:
            indicadores.posible_riesgo_modelo = True
            riesgo.requiere_verificacion = True
            riesgo.patrones.append("MODELO:posible_riesgo")

    evaluacion = Evaluacion(seudonimo=seudonimo, conversacion_id=conversacion_id,
                            mensaje_id=mensaje_id, origen="MENSAJE", nivel_riesgo=riesgo.nivel,
                            categoria="C0", accion="PENDIENTE", reglas_aplicadas={},
                            version_reglas=motor_reglas().version)
    sesion.add(evaluacion)
    sesion.flush()
    for codigo in indicadores.lexico:
        sesion.add(Senal(evaluacion_id=evaluacion.id, seudonimo=seudonimo,
                         indicador_codigo=codigo, origen="LEXICO"))
    for codigo in indicadores.modelo:
        sesion.add(Senal(evaluacion_id=evaluacion.id, seudonimo=seudonimo,
                         indicador_codigo=codigo, origen="MODELO"))
    sesion.flush()
    return _decidir_y_actuar(sesion, seudonimo=seudonimo, origen="MENSAJE", evaluacion=evaluacion,
                             riesgo=riesgo, indicadores=indicadores)


def evaluar_tamizaje(sesion: Session, *, seudonimo: str,
                     resultados: list[tuple[ResultadoTamizaje, list[int]]]) -> ResultadoCanalizacion:
    """Registra uno o ambos instrumentos y emite UNA decisión con todos los puntajes."""
    for resultado, respuestas in resultados:
        sesion.add(Tamizaje(seudonimo=seudonimo, instrumento=resultado.instrumento,
                            respuestas=respuestas, puntaje_total=resultado.puntaje_total,
                            severidad=resultado.severidad))
    _responder_oferta(sesion, seudonimo, "TAMIZAJE", "ACEPTADA")
    evaluacion = Evaluacion(seudonimo=seudonimo, origen="TAMIZAJE", nivel_riesgo=0,
                            categoria="C0", accion="PENDIENTE", reglas_aplicadas={},
                            version_reglas=motor_reglas().version)
    sesion.add(evaluacion)
    sesion.flush()
    return _decidir_y_actuar(sesion, seudonimo=seudonimo, origen="TAMIZAJE", evaluacion=evaluacion,
                             riesgo=None, indicadores=None,
                             evidencia_extra={"tamizajes": [
                                 {"instrumento": r.instrumento, "puntaje": r.puntaje_total,
                                  "severidad": r.severidad, "item9": r.item9}
                                 for r, _ in resultados]})


def evaluar_verificacion(sesion: Session, *, seudonimo: str, respuesta: str
                         ) -> ResultadoCanalizacion:
    """``respuesta``: SI, NO o SIN_RESPUESTA."""
    evaluacion = Evaluacion(seudonimo=seudonimo, origen="VERIFICACION", nivel_riesgo=0,
                            categoria="C0", accion="PENDIENTE", reglas_aplicadas={},
                            version_reglas=motor_reglas().version)
    sesion.add(evaluacion)
    sesion.flush()
    resultado = _decidir_y_actuar(sesion, seudonimo=seudonimo, origen="VERIFICACION",
                                  evaluacion=evaluacion, riesgo=None, indicadores=None,
                                  verificacion_positiva=respuesta == "SI",
                                  evidencia_extra={"respuesta_verificacion": respuesta})
    if respuesta == "NO" and resultado.accion not in ("OFRECER_DERIVACION", "OFRECER_TAMIZAJE"):
        resultado.texto = mensajes.VERIFICACION_NEGATIVA
    elif respuesta == "SIN_RESPUESTA" and resultado.categoria != "C3":
        resultado.texto = mensajes.VERIFICACION_SIN_RESPUESTA
        resultado.recursos = recursos_crisis(sesion)
    return resultado


def _responder_oferta(sesion: Session, seudonimo: str, tipo: str, respuesta: str) -> None:
    oferta = sesion.scalar(select(Oferta).where(
        Oferta.seudonimo == seudonimo, Oferta.tipo == tipo, Oferta.respuesta == "PENDIENTE")
        .order_by(Oferta.creada_en.desc()).limit(1))
    if oferta:
        oferta.respuesta = respuesta
        oferta.respondida_en = datetime.now(UTC)


def rechazar_oferta(sesion: Session, seudonimo: str, tipo: str) -> None:
    _responder_oferta(sesion, seudonimo, tipo, "RECHAZADA")


def aceptar_derivacion(sesion: Session, *, seudonimo: str, preferencia: str, telefono: str | None,
                       disponibilidad: str, nota: str | None) -> SolicitudDerivacion:
    """El estudiante acepta, con consentimiento explícito, que el personal de
    atención lo contacte (derivación ordinaria, categoría C2)."""
    existente = solicitud_activa(sesion, seudonimo)
    if existente:
        return existente
    oferta = sesion.scalar(select(Oferta).where(
        Oferta.seudonimo == seudonimo, Oferta.tipo == "DERIVACION")
        .order_by(Oferta.creada_en.desc()).limit(1))
    if oferta is None:
        raise ValueError("No hay un ofrecimiento de derivación para este estudiante")
    evaluacion = sesion.get(Evaluacion, oferta.evaluacion_id)
    _responder_oferta(sesion, seudonimo, "DERIVACION", "ACEPTADA")
    usuario = sesion.scalar(select(Usuario).where(Usuario.seudonimo == seudonimo))
    cif = cifrador_nucleo()
    hechos = calcular_hechos(sesion, seudonimo)
    regla_id = evaluacion.reglas_aplicadas.get("regla", "")
    regla = next((r for r in motor_reglas().reglas if r["id"] == regla_id), {})
    decision = Decision(evaluacion.categoria, evaluacion.accion, regla_id,
                        regla.get("nombre", ""), list(regla.get("fuentes", [])),
                        version=evaluacion.version_reglas)
    resumen = _resumen_para_personal(sesion, seudonimo, decision, hechos, None)
    contacto = {"nombre": cif.descifrar(usuario.nombre_cifrado), "correo": usuario.correo,
                "telefono": telefono or (cif.descifrar(usuario.telefono_cifrado)
                                         if usuario.telefono_cifrado else None),
                "preferencia": preferencia, "disponibilidad": disponibilidad,
                "base_legal": "Consentimiento explícito al aceptar la derivación"}
    solicitud = crear_solicitud(sesion, seudonimo=seudonimo, evaluacion_id=evaluacion.id,
                                categoria="C2", prioridad="NORMAL", resumen=resumen,
                                contacto=contacto, nota=nota)
    notificar_nueva_solicitud(sesion, solicitud)
    return solicitud
