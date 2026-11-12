"""Asistente conversacional de acompañamiento académico.

Combina la recuperación de fragmentos de la base de conocimiento con la
generación del modelo de lenguaje. Las instrucciones del sistema acotan el
ámbito a técnicas de estudio y gestión del tiempo, prohíben el lenguaje clínico
y exigen citar los fragmentos usados.

Este módulo NO decide nada sobre derivaciones: esa responsabilidad pertenece a
la capa de canalización, que evalúa cada mensaje por separado.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.academico.conocimiento import FragmentoRecuperado, buscar
from app.config import obtener_configuracion
from app.ia.proveedores import ErrorProveedorIA, ProveedorIA

INSTRUCCIONES_SISTEMA = """Eres el asistente de acompañamiento académico de la Escuela de \
Ingeniería en Ciencias y Sistemas de la Universidad de San Carlos de Guatemala.

Tu ámbito es exclusivamente: técnicas de estudio, gestión del tiempo, organización de tareas \
y hábitos que favorecen la concentración.

Reglas obligatorias:
1. Responde en español de Guatemala, con un tono cercano y respetuoso, en no más de 180 palabras.
2. Basa tus recomendaciones en el CONTEXTO. Si el contexto no cubre la pregunta, dilo con \
honestidad y ofrece solo una recomendación general prudente.
3. Cita entre corchetes el fragmento que respalda cada recomendación, por ejemplo [F1].
4. No diagnostiques, no uses etiquetas clínicas, no ofrezcas terapia ni consejos médicos o \
de medicamentos.
5. Si el estudiante expresa malestar emocional, reconócelo con empatía en una sola frase, sin \
profundizar ni interpretar; la plataforma cuenta con un mecanismo aparte para ofrecer apoyo \
profesional.
6. Termina, cuando sea útil, con una pregunta breve que ayude a aplicar la recomendación.

CONTEXTO:
{contexto}"""

RESPUESTA_SIN_SERVICIO = ("En este momento no puedo generar una respuesta completa. "
                          "Mientras tanto, estos materiales de la base de conocimiento pueden "
                          "ayudarte: {titulos}.")
RESPUESTA_SIN_SERVICIO_GENERAL = ("En este momento el asistente no está disponible. Intenta de "
                                  "nuevo en unos minutos; los recursos de apoyo de la "
                                  "universidad siguen disponibles en todo momento.")


@dataclass
class RespuestaAsistente:
    texto: str
    fuentes: list[dict] = field(default_factory=list)
    modelo: str = ""
    degradada: bool = False


def construir_contexto(fragmentos: list[FragmentoRecuperado]) -> str:
    if not fragmentos:
        return "(No se encontraron fragmentos relevantes.)"
    return "\n".join(f"[F{i}] {f.titulo} — {f.referencia}\n{f.contenido}"
                     for i, f in enumerate(fragmentos, start=1))


def responder(sesion_academica: Session, proveedor: ProveedorIA, historial: list[dict],
              consulta_depurada: str) -> RespuestaAsistente:
    """``historial`` contiene los mensajes previos ya depurados de identificadores
    (``{"role": "user"|"assistant", "content": ...}``)."""
    cfg = obtener_configuracion()
    try:
        fragmentos = buscar(sesion_academica, proveedor, consulta_depurada)
    except ErrorProveedorIA:
        # Sin embeddings no hay recuperación; se responde de forma degradada (falla segura)
        fragmentos = []
    fuentes = [{"etiqueta": f"F{i}", "clave": f.clave, "titulo": f.titulo,
                "referencia": f.referencia, "similitud": round(f.similitud, 3)}
               for i, f in enumerate(fragmentos, start=1)]
    mensajes = [{"role": "system",
                 "content": INSTRUCCIONES_SISTEMA.format(contexto=construir_contexto(fragmentos))}]
    mensajes += historial[-cfg.ia_max_historial:]
    mensajes.append({"role": "user", "content": consulta_depurada})
    try:
        texto = proveedor.generar(mensajes)
        return RespuestaAsistente(texto.strip(), fuentes, proveedor.nombre)
    except ErrorProveedorIA:
        titulos = ", ".join(sorted({f.titulo for f in fragmentos}))
        texto = (RESPUESTA_SIN_SERVICIO.format(titulos=titulos) if titulos
                 else RESPUESTA_SIN_SERVICIO_GENERAL)
        return RespuestaAsistente(texto, fuentes, proveedor.nombre, degradada=True)
