# Prototipo de servidor MCP para SAAC (trabajo futuro)

Prueba de concepto que expone parte de la plataforma mediante el **Model Context Protocol (MCP)**, el estándar abierto para conectar agentes de IA con herramientas y datos externos (Anthropic, 2024; hoy bajo la Agentic AI Foundation de la Linux Foundation).

## Qué expone

| Tipo | Nombre | Descripción |
|---|---|---|
| Herramienta | `buscar_tecnicas_estudio(consulta, cantidad)` | Búsqueda semántica en la base de conocimiento de SAAC |
| Herramienta | `listar_recursos_de_apoyo()` | Directorio de atención psicológica, líneas de apoyo y emergencias |
| Recurso | `saac://conocimiento/indice` | Índice de documentos de la base de conocimiento |

**Qué NO expone, por diseño:** conversaciones, señales, tamizajes, solicitudes ni datos identificativos. La decisión de derivar sigue siendo exclusiva del motor de reglas de la plataforma.

## Uso

```bash
pip install -r requirements.txt
# En el .env del backend: SAAC_CLAVE_API_MCP=<clave>
SAAC_API_URL=http://localhost:8000 SAAC_CLAVE_API_MCP=<clave> python servidor.py
```

Configuración típica en un cliente MCP (transporte stdio):

```json
{
  "mcpServers": {
    "saac": {
      "command": "python",
      "args": ["/ruta/a/extensiones/mcp-servidor/servidor.py"],
      "env": { "SAAC_API_URL": "http://localhost:8000", "SAAC_CLAVE_API_MCP": "<clave>" }
    }
  }
}
```

Funciona con clientes comerciales (por ejemplo, Claude Desktop o ChatGPT) y con agentes de código abierto que admiten MCP (por ejemplo, Goose o LibreChat), que a su vez pueden usar modelos abiertos servidos con Ollama.
