"""Diagrama de componentes."""
from kit import Lienzo, componente

c = Lienzo(5.94, 5.3)
componente(c, 0.25, 0.1, 2.2, 0.62, "Aplicación web", "React + TypeScript (nginx)")
componente(c, 3.45, 0.1, 2.3, 0.62, "Servidor MCP", "prototipo · trabajo futuro", relleno="blanco", punteada=True)
# Backend
c.caja(0.1, 0.95, 4.65, 3.2, relleno="blanco", estilo="square")
c.texto(2.85, 1.12, "«subsistema» Backend SAAC (Python · FastAPI)", tam=7, negrita=True)
componente(c, 0.25, 1.32, 4.35, 0.5, "api", "rutas por actor: estudiante · atención · administración · integración")
componente(c, 0.25, 2.05, 1.38, 0.72, "seguridad", "JWT · RBAC\ncifrado · seudónimos\ndepuración de PII", tam=6.4)
componente(c, 1.74, 2.05, 1.38, 0.72, "academico", "asistente\nconocimiento (RAG)", tam=6.4)
componente(c, 3.23, 2.05, 1.38, 0.72, "canalizacion", "detección · motor\nde reglas · tamizaje", tam=6.4)
componente(c, 0.25, 3.0, 1.38, 0.72, "auditoria", "bitácoras con\nhashes encadenados", tam=6.4)
componente(c, 1.74, 3.0, 1.38, 0.72, "ia", "adaptadores:\nOpenAI-compatible\ny simulado", tam=6.4)
componente(c, 3.23, 3.0, 1.38, 0.72, "solicitudes y\nnotificaciones", "", tam=6.4)
# Externos
c.caja(4.95, 1.25, 0.9, 0.55, "Archivos de\nreglas (YAML)", relleno="medio", estilo="square", tam=6.2)
c.caja(4.95, 2.05, 0.9, 0.55, "Servidor de\ncorreo\n(SMTP)", relleno="blanco", punteada=True, tam=6.2)
c.caja(4.95, 2.95, 0.9, 0.62, "Servicio de\nmodelos de\nlenguaje", relleno="blanco", punteada=True, tam=6.2)
c.cilindro(0.6, 4.4, 3.6, 0.8, "PostgreSQL 16 + pgvector\nconexión rol_academico · conexión rol_nucleo", relleno="medio", tam=6.6)
# Dependencias
c.flecha(1.35, 0.72, 1.35, 1.32)
c.texto(0.88, 0.86, "REST/JSON", tam=6, cursiva=True)
c.flecha(4.6, 0.72, 4.45, 1.32, punteada=True)
c.texto(5.05, 0.9, "REST + clave", tam=6, cursiva=True)
for x in (0.94, 2.43, 3.92):
    c.flecha(x, 1.82, x, 2.05, punteada=True)
c.flecha(2.43, 2.77, 2.43, 3.0, punteada=True)                    # academico -> ia
c.flecha(3.3, 2.77, 3.08, 3.0, punteada=True)                     # canalizacion -> ia
c.flecha(3.92, 2.77, 3.92, 3.0, punteada=True)                    # canalizacion -> solicitudes
c.linea([(3.45, 2.77), (3.45, 2.89), (1.0, 2.89), (1.0, 3.0)], punteada=True)  # canalizacion -> auditoria
c.flecha(4.61, 2.2, 4.95, 1.6, punteada=True)                     # canalizacion -> reglas
c.flecha(4.61, 3.1, 4.95, 2.45, punteada=True)                    # solicitudes -> SMTP
c.linea([(2.75, 3.72), (2.75, 3.9), (5.4, 3.9), (5.4, 3.57)], punteada=True)   # ia -> LLM
c.flecha(0.94, 3.72, 1.1, 4.42, punteada=True)
c.texto(0.62, 4.25, "rol_nucleo", tam=5.8, cursiva=True)
c.linea([(1.74, 2.5), (1.685, 2.5), (1.685, 4.42)], punteada=True)   # academico -> BD
c.texto(2.15, 4.25, "rol_academico", tam=5.8, cursiva=True)
c.flecha(3.92, 3.72, 3.6, 4.42, punteada=True)
c.texto(4.2, 4.25, "rol_nucleo", tam=5.8, cursiva=True)
c.guardar("11_componentes.png")
