"""Extensión futura mediante Model Context Protocol."""
from kit import Lienzo

c = Lienzo(5.94, 3.5)
# Clientes
c.caja(0.08, 0.3, 1.6, 2.2, relleno="claro", titulo="Agentes de IA\n(clientes MCP)", tam=7)
c.caja(0.2, 0.85, 1.36, 0.62, "Comerciales\n(p. ej. Claude,\nChatGPT)", relleno="blanco", tam=6.4)
c.caja(0.2, 1.62, 1.36, 0.74, "Código abierto\n(p. ej. Goose,\nLibreChat) con\nmodelos en Ollama", relleno="blanco", tam=6.4)
# Servidor MCP
c.caja(2.05, 0.3, 1.75, 2.2, relleno="medio", titulo="Servidor MCP SAAC\n(prototipo)", tam=7, punteada=True)
c.caja(2.15, 0.88, 1.55, 0.78, "Herramientas\nbuscar_tecnicas_estudio\nlistar_recursos_de_apoyo", relleno="blanco", tam=6.0)
c.caja(2.15, 1.76, 1.55, 0.6, "Recurso\nsaac://conocimiento/indice", relleno="blanco", tam=6.0)
# Plataforma
c.caja(4.15, 0.3, 1.72, 2.2, relleno="claro", titulo="Plataforma SAAC", tam=7)
c.caja(4.25, 0.62, 1.52, 0.42, "API de integración\n(clave de API)", relleno="blanco", tam=6.2)
c.caja(4.25, 1.18, 1.52, 0.42, "Base de conocimiento\n(capa académica)", relleno="blanco", tam=6.2)
c.caja(4.25, 1.68, 1.52, 0.3, "Directorio de recursos", relleno="blanco", tam=6.2)
c.caja(4.25, 2.07, 1.52, 0.35, "Capa de canalización", relleno="oscuro", tam=6.2, punteada=True)
c.flecha(4.3, 2.1, 5.72, 2.39, cabeza=False)
c.flecha(4.3, 2.39, 5.72, 2.1, cabeza=False)
# Flechas
c.flecha(1.68, 1.4, 2.05, 1.4, doble=True)
c.texto(1.865, 1.62, "MCP", tam=5.8, cursiva=True)
c.flecha(3.8, 1.0, 4.25, 0.83)
c.texto(4.0, 0.62, "REST", tam=5.8, cursiva=True)
c.flecha(5.0, 1.04, 5.0, 1.18, cabeza=True)
c.linea([(4.25, 0.92), (4.18, 0.92), (4.18, 1.83), (4.25, 1.83)], punteada=False)
# Notas
c.caja(0.08, 2.68, 5.79, 0.74, relleno="blanco", estilo="square", punteada=True)
c.texto(0.18, 2.82, "Condiciones de diseño", tam=6.8, negrita=True, ha="left")
c.texto(0.18, 3.13,
        "• Solo se exponen la capa académica y el directorio público de recursos; nunca señales, tamizajes, solicitudes ni datos personales.\n"
        "• La decisión de derivar permanece en el motor de reglas de la plataforma: un agente externo no puede canalizar ni diagnosticar.\n"
        "• Extensión inversa posible: SAAC como cliente MCP de servidores externos (p. ej., el calendario del estudiante para planificar su semana).",
        tam=5.8, ha="left")
c.guardar("12_mcp.png")
