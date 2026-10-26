# SAAC · Sistema de Acompañamiento Académico y Canalización

Plataforma de acompañamiento académico asistido por inteligencia artificial con canalización hacia los servicios de atención psicológica universitaria.

> Trabajo de graduación · Escuela de Ingeniería en Ciencias y Sistemas, Facultad de Ingeniería, Universidad de San Carlos de Guatemala.
> Autor: Angel Geovanny Ordón Colchaj · Asesor: Ing. Herman Igor Véliz Linares.

**Aviso importante.** SAAC es un prototipo académico de demostración. **No realiza diagnósticos** ni sustituye la atención de un profesional de la salud mental. Los criterios de derivación provienen de literatura científica e instrumentos validados (PHQ-9, GAD-7, NICE, OMS mhGAP), pero **no han sido validados clínicamente**. Las pruebas se ejecutan con datos simulados. Antes de un uso con estudiantes reales se necesita la revisión de profesionales de la salud mental y la autorización de las autoridades universitarias.

---

## ¿Qué hace?

La plataforma tiene dos capas separadas:

| Capa | Qué hace | Cómo usa la IA |
|---|---|---|
| **Acompañamiento académico** | Responde dudas sobre técnicas de estudio, gestión del tiempo y organización de tareas. | Modelo de lenguaje con **generación aumentada por recuperación (RAG)** sobre una base de conocimiento curada a partir de la literatura (Dunlosky et al., 2013, entre otros). |
| **Clasificación y canalización** | Detecta cuándo la dificultad excede el ámbito académico y gestiona la derivación hacia atención profesional. | El modelo **solo extrae indicadores** del texto (comprensión del lenguaje). **La decisión la toma un motor de reglas determinista y versionado**, y las señales de riesgo se detectan con un léxico determinista *antes* de consultar cualquier modelo. |

Categorías de clasificación (reglas `v1.0.0`):

| Categoría | Significado | Acción de la plataforma |
|---|---|---|
| C0 | Acompañamiento académico | Respuesta del asistente |
| C1 | Acompañamiento con monitoreo activo | Ofrecer cuestionario voluntario (PHQ-9 / GAD-7) o informar sobre servicios |
| C2 | Derivación ordinaria | Ofrecer contacto con el personal de atención (requiere consentimiento explícito) |
| C3 | Escalamiento prioritario | Protocolo de riesgo: recursos de crisis inmediatos, solicitud prioritaria y notificación al personal |

## Arquitectura

- **Frontend**: React 18 + TypeScript + Vite (servido con nginx).
- **Backend**: Python 3.12 + FastAPI, organizado en capas (API → servicios de dominio → persistencia).
- **Base de datos**: PostgreSQL 16 + pgvector, con **un esquema por capa** (`identidad`, `academico`, `canalizacion`, `auditoria`) y **dos roles de conexión**: la capa académica no puede leer identidades, señales ni solicitudes.
- **Modelos de lenguaje**: cualquier servicio compatible con la API de OpenAI. Por defecto se propone **Ollama** con modelos abiertos (`qwen2.5:7b-instruct` para conversación y `bge-m3` para *embeddings*). También existe un proveedor **simulado** para pruebas y demostraciones sin GPU.
- **Despliegue**: Docker Compose (una máquina virtual en la nube es suficiente para la demostración).

Los diagramas están en [`docs/diagramas`](docs/diagramas) y su explicación completa en el documento de tesis (capítulos 3 y 4).

## Estructura del repositorio

```
saac/
├── backend/
│   ├── app/
│   │   ├── api/             # Rutas HTTP por actor (estudiante, atención, administración)
│   │   ├── academico/       # Asistente conversacional y base de conocimiento (RAG)
│   │   ├── canalizacion/    # Detección de riesgo, indicadores, motor de reglas, tamizaje
│   │   ├── solicitudes/     # Máquina de estados de las solicitudes de derivación
│   │   ├── auditoria/       # Bitácoras con encadenamiento de hashes
│   │   ├── notificaciones/  # Avisos al personal (sin datos sensibles)
│   │   ├── seguridad/       # JWT, RBAC, seudonimización, cifrado, depuración de PII
│   │   └── ia/              # Adaptadores de proveedores de modelos (OpenAI-compatible / simulado)
│   ├── reglas/              # Criterios y léxicos VERSIONADOS (YAML)
│   ├── conocimiento/        # Documentos de la base de conocimiento (Markdown + referencia APA)
│   ├── scripts/             # Indexación, cuentas de demostración, retención de datos
│   └── tests/               # Pruebas unitarias y de integración + casos derivados de la literatura
├── frontend/                # Interfaz web (estudiante, personal de atención, administración)
├── db/                      # Migraciones SQL, semillas y script de inicialización
├── extensiones/mcp-servidor # Prototipo de servidor MCP (trabajo futuro)
├── docs/                    # Diagramas y documentación técnica
└── docker-compose.yml
```

## Inicio rápido (Docker)

```bash
git clone https://github.com/AngelOrdon02/saac-plataforma.git
cd saac-plataforma
cp .env.example .env          # edite las claves (ver comentarios del archivo)
docker compose up -d --build
docker compose exec backend python -m scripts.crear_usuarios_demo
```

- Aplicación: <http://localhost:8080>
- Documentación interactiva de la API (OpenAPI): <http://localhost:8080/api/docs>
- Bandeja de correos de prueba (notificaciones): <http://localhost:8025>

Cuentas de demostración (contraseña `Demo-SAAC-2026`): `psicologia@saac.demo` (personal de atención), `admin@saac.demo` (administración técnica), `estudiante@saac.demo` (estudiante). También puede crear una cuenta de estudiante desde la pantalla de registro.

### Con modelos de código abierto (Ollama)

```bash
# En .env: SAAC_PROVEEDOR_IA=openai_compatible y SAAC_IA_URL_BASE=http://ollama:11434/v1
docker compose --profile ia-local up -d
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose exec ollama ollama pull bge-m3
docker compose exec backend python -m scripts.indexar_conocimiento   # recalcula embeddings
```

Un modelo de 7 u 8 mil millones de parámetros cuantizado necesita unos 6 a 8 GB de memoria; en CPU responde en varios segundos, con GPU en uno o dos.

> Si cambia de modelo de *embeddings*, la dimensión debe seguir siendo 1024 (o ajustar la columna `vector(1024)` y reindexar).

### Con un servicio comercial

Cualquier servicio compatible con la API de OpenAI funciona cambiando `SAAC_IA_URL_BASE`, `SAAC_IA_CLAVE_API` y los nombres de los modelos. Solo se envía texto **depurado de identificadores** (correos, teléfonos, carné, DPI y el nombre del estudiante).

## Desarrollo local sin Docker

```bash
# 1. PostgreSQL 16 con pgvector
for f in db/migraciones/*.sql db/semillas/*.sql; do psql -d saac -f "$f"; done
psql -d saac -c "CREATE USER saac_app_academico WITH PASSWORD 'x' IN ROLE rol_academico; CREATE USER saac_app_nucleo WITH PASSWORD 'y' IN ROLE rol_nucleo;"

# 2. Backend
cd backend
pip install -r requirements-dev.txt
cp ../.env.example .env   # y ajuste SAAC_URL_BD_* a su servidor local
python -m scripts.crear_usuarios_demo && python -m scripts.indexar_conocimiento
uvicorn app.main:app --reload

# 3. Frontend
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

## Pruebas

```bash
cd backend
python -m pytest                                  # unitarias (no requieren base de datos)
SAAC_PRUEBAS_INTEGRACION=1 python -m pytest       # además, flujos completos contra PostgreSQL
```

Los casos de `tests/casos/` (18 casos del motor de reglas y 21 de los detectores) se derivan de los criterios documentados en la literatura y sirven de base para la evaluación del capítulo 5.

## Reglas versionadas

Los criterios de clasificación **no están en el código**: están en `backend/reglas/criterios_vX.Y.Z.yaml`. Cada decisión queda registrada en la bitácora con la versión y la huella SHA-256 del archivo de reglas vigente, de modo que siempre se puede reconstruir por qué se tomó. Para modificar un criterio:

1. Copie el archivo con una nueva versión (`criterios_v1.1.0.yaml`) y documente el cambio y su fuente.
2. Agregue o ajuste los casos en `tests/casos/casos_motor.yaml`.
3. Apunte `SAAC_RUTA_CRITERIOS` al nuevo archivo y ejecute las pruebas.

## Seguridad y privacidad

- Seudonimización (HMAC-SHA256): las capas académica y de canalización solo conocen el seudónimo.
- Cifrado en reposo (Fernet) de mensajes, nombres, teléfonos y datos de contacto.
- Contraseñas con Argon2id; sesiones con JWT de corta duración.
- Control de acceso por roles: ningún rol puede leer conversaciones ajenas.
- Bitácoras de decisiones y de accesos **de solo inserción**, con encadenamiento de hashes verificable.
- Métricas agregadas con supresión de conteos pequeños (umbral *k* = 5).
- Política de retención configurable (`scripts/depurar_retencion.py`).

## Extensión MCP (trabajo futuro)

`extensiones/mcp-servidor` contiene un prototipo de servidor [Model Context Protocol](https://modelcontextprotocol.io) que expone la base de conocimiento y el directorio de recursos de apoyo como herramientas para agentes de IA (comerciales o de código abierto). **No expone datos de canalización.** Ver su README.

## Licencia

MIT. Ver [LICENSE](LICENSE).
