-- =============================================================================
-- SAAC · Migración 004 · Esquema canalizacion (capa de clasificación y canalización)
-- =============================================================================

-- Catálogo de indicadores: cada uno se corresponde con un ítem de un instrumento
-- validado o con un criterio documentado (tabla 17 del documento).
CREATE TABLE canalizacion.indicador (
    codigo       VARCHAR(8)   PRIMARY KEY,
    dominio      VARCHAR(12)  NOT NULL
                 CHECK (dominio IN ('DEPRESIVO', 'ANSIOSO', 'FUNCIONAL', 'TEMPORAL')),
    referencia   VARCHAR(60)  NOT NULL,                     -- p. ej. 'PHQ-9, ítem 1'
    descripcion  VARCHAR(200) NOT NULL,
    compartido   BOOLEAN      NOT NULL DEFAULT FALSE        -- también es dificultad académica
);

-- Cada vez que el motor clasifica (un mensaje, un tamizaje o una verificación)
CREATE TABLE canalizacion.evaluacion (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    seudonimo         CHAR(24)    NOT NULL,
    conversacion_id   UUID,
    mensaje_id        UUID,
    origen            VARCHAR(12) NOT NULL CHECK (origen IN ('MENSAJE', 'TAMIZAJE', 'VERIFICACION')),
    nivel_riesgo      SMALLINT    NOT NULL DEFAULT 0 CHECK (nivel_riesgo BETWEEN 0 AND 3),
    categoria         VARCHAR(2)  NOT NULL CHECK (categoria IN ('C0', 'C1', 'C2', 'C3')),
    accion            VARCHAR(30) NOT NULL,
    reglas_aplicadas  JSONB       NOT NULL,
    version_reglas    VARCHAR(20) NOT NULL,
    creada_en         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_evaluacion_seudonimo ON canalizacion.evaluacion(seudonimo, creada_en DESC);

-- Señales detectadas (solo códigos de indicador, nunca el texto del mensaje)
CREATE TABLE canalizacion.senal (
    id                BIGSERIAL   PRIMARY KEY,
    evaluacion_id     UUID        NOT NULL REFERENCES canalizacion.evaluacion(id) ON DELETE CASCADE,
    seudonimo         CHAR(24)    NOT NULL,
    indicador_codigo  VARCHAR(8)  NOT NULL REFERENCES canalizacion.indicador(codigo),
    origen            VARCHAR(10) NOT NULL CHECK (origen IN ('LEXICO', 'MODELO')),
    detectada_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_senal_seudonimo_fecha ON canalizacion.senal(seudonimo, detectada_en DESC);

-- Resultados de los instrumentos de tamizaje (PHQ-9 y GAD-7)
CREATE TABLE canalizacion.tamizaje (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    seudonimo      CHAR(24)    NOT NULL,
    instrumento    VARCHAR(6)  NOT NULL CHECK (instrumento IN ('PHQ9', 'GAD7')),
    respuestas     SMALLINT[]  NOT NULL,
    puntaje_total  SMALLINT    NOT NULL,
    severidad      VARCHAR(25) NOT NULL,
    aplicado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_tamizaje_seudonimo ON canalizacion.tamizaje(seudonimo, aplicado_en DESC);

-- Ofrecimientos hechos al estudiante y su respuesta (evita insistir)
CREATE TABLE canalizacion.oferta (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    seudonimo      CHAR(24)    NOT NULL,
    tipo           VARCHAR(12) NOT NULL CHECK (tipo IN ('TAMIZAJE', 'DERIVACION')),
    evaluacion_id  UUID        NOT NULL REFERENCES canalizacion.evaluacion(id) ON DELETE CASCADE,
    respuesta      VARCHAR(10) NOT NULL DEFAULT 'PENDIENTE'
                   CHECK (respuesta IN ('PENDIENTE', 'ACEPTADA', 'RECHAZADA')),
    creada_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    respondida_en  TIMESTAMPTZ
);

CREATE INDEX ix_oferta_seudonimo ON canalizacion.oferta(seudonimo, creada_en DESC);

-- Directorio de recursos de atención que se presenta al estudiante
CREATE TABLE canalizacion.recurso_atencion (
    id             SERIAL       PRIMARY KEY,
    nombre         VARCHAR(150) NOT NULL,
    tipo           VARCHAR(14)  NOT NULL CHECK (tipo IN ('INSTITUCIONAL', 'LINEA_APOYO', 'EMERGENCIA')),
    descripcion    TEXT         NOT NULL,
    ubicacion      VARCHAR(200),
    horario        VARCHAR(150),
    telefono       VARCHAR(40),
    enlace         VARCHAR(300),
    procedimiento  TEXT,
    fuente         VARCHAR(300),
    orden          SMALLINT     NOT NULL DEFAULT 0,
    activo         BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Solicitudes de derivación gestionadas por el personal de atención
CREATE SEQUENCE canalizacion.seq_solicitud;

CREATE TABLE canalizacion.solicitud_derivacion (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo            VARCHAR(16) NOT NULL UNIQUE,          -- SOL-2026-0001
    seudonimo         CHAR(24)    NOT NULL,
    evaluacion_id     UUID        NOT NULL REFERENCES canalizacion.evaluacion(id),
    categoria         VARCHAR(2)  NOT NULL CHECK (categoria IN ('C2', 'C3')),
    prioridad         VARCHAR(8)  NOT NULL CHECK (prioridad IN ('NORMAL', 'ALTA', 'CRITICA')),
    estado            VARCHAR(14) NOT NULL DEFAULT 'NUEVA'
                      CHECK (estado IN ('NUEVA', 'EN_REVISION', 'CONTACTADO', 'AGENDADA',
                                        'NO_LOCALIZADO', 'FINALIZADA', 'CANCELADA')),
    resumen           JSONB       NOT NULL,                 -- indicadores, puntajes y reglas; sin texto libre
    contacto_cifrado  TEXT        NOT NULL,                 -- nombre, correo, teléfono, preferencia
    nota_cifrada      TEXT,                                 -- mensaje opcional del estudiante
    asignada_a        UUID,                                 -- personal de atención responsable
    creada_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizada_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrada_en        TIMESTAMPTZ
);

CREATE INDEX ix_solicitud_bandeja ON canalizacion.solicitud_derivacion(estado, prioridad, creada_en);
CREATE INDEX ix_solicitud_seudonimo ON canalizacion.solicitud_derivacion(seudonimo);

CREATE TABLE canalizacion.historial_estado (
    id                  BIGSERIAL   PRIMARY KEY,
    solicitud_id        UUID        NOT NULL REFERENCES canalizacion.solicitud_derivacion(id) ON DELETE CASCADE,
    estado_anterior     VARCHAR(14),
    estado_nuevo        VARCHAR(14) NOT NULL,
    actor_id            UUID,                               -- NULL cuando actúa el sistema
    comentario_cifrado  TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_historial_solicitud ON canalizacion.historial_estado(solicitud_id, creado_en);

CREATE TABLE canalizacion.notificacion (
    id               BIGSERIAL    PRIMARY KEY,
    solicitud_id     UUID         NOT NULL REFERENCES canalizacion.solicitud_derivacion(id) ON DELETE CASCADE,
    destinatario_id  UUID         NOT NULL,
    canal            VARCHAR(6)   NOT NULL CHECK (canal IN ('APP', 'CORREO')),
    asunto           VARCHAR(200) NOT NULL,                 -- sin datos sensibles
    enviada          BOOLEAN      NOT NULL DEFAULT FALSE,
    creada_en        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    leida_en         TIMESTAMPTZ
);

CREATE INDEX ix_notificacion_destinatario ON canalizacion.notificacion(destinatario_id, leida_en);
