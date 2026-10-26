"""Diagrama de despliegue de la demostración."""
from kit import Lienzo

c = Lienzo(5.94, 4.4)
# Clientes
c.caja(0.08, 0.2, 1.25, 0.95, "«dispositivo»\nNavegador web\n(estudiante, personal,\nadministración)", relleno="claro", tam=6.2)
c.caja(0.08, 2.3, 1.25, 0.85, "«dispositivo»\nCliente MCP\n(trabajo futuro)", relleno="blanco", tam=6.2, punteada=True)
# Nodo VM
c.caja(1.6, 0.08, 4.27, 3.55, relleno="blanco", estilo="square")
c.texto(3.73, 0.24, "«nodo» Máquina virtual Linux en la nube (IaaS) · Docker Engine + Docker Compose", tam=6.4, negrita=True)
def contenedor(x, y, w, h, nombre, detalle, relleno="claro", punteada=False):
    c.caja(x, y, w, h, "", relleno=relleno, estilo="square", punteada=punteada)
    c.texto(x + w / 2, y + 0.15, nombre, tam=6.5, negrita=True)
    c.texto(x + w / 2, y + 0.15 + (h - 0.15) / 2, detalle, tam=5.9)
contenedor(1.78, 0.5, 1.75, 0.8, "frontend", "«contenedor» nginx 1.27\narchivos estáticos (React)\nproxy inverso /api · :8080")
contenedor(1.78, 1.6, 1.75, 0.8, "backend", "«contenedor» Python 3.12\nFastAPI + Uvicorn · :8000\nreglas YAML · conocimiento")
contenedor(1.78, 2.65, 1.75, 0.8, "db", "«contenedor» PostgreSQL 16\n+ pgvector · volumen\npersistente datos_bd")
contenedor(3.95, 0.5, 1.75, 0.8, "mailpit", "«contenedor» servidor SMTP\nde pruebas · :8025", relleno="blanco")
contenedor(3.95, 1.6, 1.75, 0.95, "ollama (opcional)", "«contenedor» perfil ia-local\nqwen2.5:7b-instruct\nbge-m3 · volumen de modelos", relleno="blanco", punteada=True)
c.caja(3.95, 3.82, 1.92, 0.5, "Alternativa externa: servicio comercial\ncompatible con la API de OpenAI (HTTPS)", relleno="blanco", tam=5.9, punteada=True)
# Conexiones
c.flecha(1.33, 0.75, 1.78, 0.85, etiqueta="HTTPS", tam=5.8, desp=(0, -0.12))
c.flecha(2.65, 1.3, 2.65, 1.6)
c.texto(2.98, 1.45, "HTTP /api", tam=5.6, cursiva=True)
c.flecha(2.65, 2.4, 2.65, 2.65)
c.texto(3.05, 2.52, "2 conexiones", tam=5.6, cursiva=True)
c.flecha(3.53, 1.85, 3.95, 1.1, punteada=True)
c.texto(3.75, 1.38, "SMTP", tam=5.6, cursiva=True)
c.flecha(3.53, 2.05, 3.95, 2.05, punteada=True)
c.flecha(3.53, 2.3, 4.6, 3.82, punteada=True)
c.flecha(1.33, 2.7, 1.78, 2.2, punteada=True)
c.texto(0.7, 3.3, "REST + clave de API", tam=5.6, cursiva=True)
c.guardar("16_despliegue.png")
