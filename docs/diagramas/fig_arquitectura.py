"""Arquitectura general de la plataforma (capas)."""
from kit import Lienzo

c = Lienzo(5.94, 5.6)
T = 7  # tamaño base
# Presentación
c.caja(0.1, 0.08, 4.55, 0.82, relleno="claro", titulo="Capa de presentación · aplicación web (React + TypeScript)", tam=T)
for i, t in enumerate(["Interfaz del\nestudiante", "Interfaz del personal\nde atención psicológica", "Interfaz de\nadministración técnica"]):
    c.caja(0.25 + i * 1.47, 0.36, 1.35, 0.44, t, relleno="blanco", tam=6.5)
c.flecha(2.37, 0.9, 2.37, 1.08, etiqueta="HTTPS · JSON", tam=6.2, desp=(0.45, 0))
# Servicios
c.caja(0.1, 1.08, 4.55, 0.72, relleno="medio", titulo="Capa de servicios · API REST (FastAPI)", tam=T)
c.caja(0.25, 1.34, 2.05, 0.38, "Autenticación (JWT) y control\nde acceso por roles (RBAC)", relleno="blanco", tam=6.3)
c.caja(2.45, 1.34, 2.05, 0.38, "Orquestación: primero canalización,\nluego asistente académico", relleno="blanco", tam=6.3)
c.flecha(1.35, 1.8, 1.35, 2.0)
c.flecha(3.7, 1.8, 3.7, 2.0)
# Dominio: canalización (izquierda) y académico (derecha)
c.caja(0.1, 2.0, 2.75, 1.65, relleno="oscuro", titulo="Capa de clasificación y canalización", tam=T)
cajas = ["Detector de riesgo\n(léxico determinista)", "Extractor de\nindicadores", "Motor de reglas\nversionado (YAML)",
         "Tamizaje\nPHQ-9 / GAD-7", "Solicitudes y\nmáquina de estados", "Notificaciones\nal personal"]
for i, t in enumerate(cajas):
    fila, col = divmod(i, 2)
    c.caja(0.2 + col * 1.3, 2.3 + fila * 0.44, 1.22, 0.38, t, relleno="blanco", tam=6.1)
c.caja(3.0, 2.0, 1.65, 1.65, relleno="claro", titulo="Capa de acompañamiento\nacadémico", tam=T)
for i, t in enumerate(["Asistente\nconversacional", "Recuperación\nsemántica (RAG)", "Base de conocimiento\n(10 documentos)"]):
    c.caja(3.12, 2.42 + i * 0.4, 1.41, 0.34, t, relleno="blanco", tam=6.1)
# Servicio externo de modelos
c.caja(4.85, 2.25, 1.0, 1.0, "Servicio de\nmodelos de\nlenguaje\n(Ollama local o\nAPI compatible\ncon OpenAI)",
       relleno="blanco", tam=6.0, punteada=True)
c.flecha(4.53, 2.59, 4.85, 2.59)
c.texto(4.7, 2.36, "texto\ndepurado", tam=5.6, cursiva=True)
c.linea([(2.11, 2.3), (2.11, 1.9), (5.35, 1.9), (5.35, 2.25)], punteada=True)
c.texto(4.9, 1.83, "extracción opcional (JSON)", tam=5.6, cursiva=True)
# Transversal
c.caja(0.1, 3.76, 4.55, 0.42, "", relleno="medio")
c.texto(2.37, 3.88, "Protección y trazabilidad (transversal)", tam=6.4, negrita=True)
c.texto(2.37, 4.05, "seudonimización · cifrado · depuración de identificadores · bitácora encadenada", tam=5.9)
# Persistencia
c.caja(0.1, 4.3, 4.55, 1.22, relleno="fuerte", titulo="Capa de persistencia · PostgreSQL 16 + pgvector", tam=T)
c.cilindro(0.35, 4.75, 2.2, 0.68, "esquemas identidad,\ncanalizacion y auditoria", relleno="claro", tam=6.3)
c.cilindro(3.05, 4.75, 1.5, 0.68, "esquema academico\n(mensajes cifrados\ny vectores)", relleno="claro", tam=6.1)
c.flecha(0.3, 3.65, 0.3, 5.05, cabeza=False)
c.flecha(0.3, 5.05, 0.36, 5.05)
c.texto(0.72, 4.63, "rol_nucleo", tam=6, cursiva=True)
c.flecha(4.45, 3.65, 4.45, 4.77)
c.texto(4.0, 4.63, "rol_academico", tam=6, cursiva=True)
c.texto(5.3, 4.85, "La capa académica\nno tiene permisos\nsobre identidad,\ncanalización ni\nauditoría", tam=5.8, cursiva=True)
c.guardar("07_arquitectura.png")
