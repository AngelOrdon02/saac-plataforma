"""Mensajes fijos de la capa de canalización.

Estos textos NO los genera el modelo de lenguaje: son plantillas revisables y
versionadas. Siguen dos criterios de la literatura: presentar la derivación en
lenguaje no clínico y como una opción de apoyo, no como una etiqueta (Clement et
al., 2015), y no dejar nunca a la persona sin un camino claro hacia la atención
humana (Ni y Jia, 2025; OMS, 2016).
"""

OFRECER_TAMIZAJE = (
    "Gracias por contarme cómo te has sentido. A veces lo que se nota en los estudios tiene que "
    "ver con cómo estamos por dentro. Si quieres, puedes responder un cuestionario breve (unos dos "
    "minutos) que también usan los servicios de bienestar para orientar mejor. Es voluntario y "
    "podemos seguir conversando de todas formas.")

MONITOREO = (
    "Si en algún momento quieres hablar con alguien, la universidad cuenta con atención "
    "psicológica gratuita y confidencial. Encuentras los datos en «Recursos de apoyo».")

OFRECER_DERIVACION = (
    "Por lo que me compartes, creo que te podría ayudar conversar con una persona del equipo de "
    "atención psicológica de la universidad. Es gratuito y confidencial. Si quieres, puedo pedir "
    "que te contacten; tú eliges cómo y cuándo. También puedes acudir por tu cuenta con la "
    "información de «Recursos de apoyo».")

SEGUIMIENTO_SOLICITUD = (
    "Tu solicitud {codigo} sigue activa y el equipo de atención te contactará. Puedes revisar su "
    "estado en «Mis solicitudes».")

VERIFICAR_RIESGO = (
    "Quiero asegurarme de entenderte bien, y te lo pregunto con respeto: ¿has tenido pensamientos "
    "de hacerte daño o de quitarte la vida?")

PROTOCOLO_RIESGO = (
    "Gracias por decírmelo. Lo que sientes importa y no tienes que pasarlo a solas. Ya avisé al "
    "equipo de atención psicológica de la universidad para que se comunique contigo lo antes "
    "posible, con los datos de contacto de tu cuenta. Mientras tanto, aquí tienes a quién llamar "
    "ahora mismo.")

PROTOCOLO_RIESGO_INMINENTE = (
    "Gracias por decírmelo. Tu seguridad es lo más importante en este momento. Por favor, no te "
    "quedes a solas: busca a alguien de confianza que esté cerca y llama ahora a uno de los "
    "números de emergencia. Ya avisé con prioridad máxima al equipo de atención psicológica de la "
    "universidad.")

VERIFICACION_NEGATIVA = (
    "Gracias por responder. Si en algún momento cambia cómo te sientes, puedes hablar con alguien "
    "del equipo de atención psicológica; los datos están en «Recursos de apoyo».")

VERIFICACION_SIN_RESPUESTA = (
    "Está bien, no tienes que responder. Te dejo los contactos de apoyo por si los necesitas en "
    "algún momento.")
