-- =============================================================================
-- SAAC · Migración 003 · Esquema academico (capa de acompañamiento académico)
-- No contiene datos identificativos: las conversaciones se asocian al seudónimo
-- y el contenido de los mensajes se almacena cifrado.
-- =============================================================================

CREATE TABLE academico.conversacion (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    seudonimo       CHAR(24)     NOT NULL,
    titulo          VARCHAR(120) NOT NULL DEFAULT 'Nueva conversación',
    creada_en       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    actualizada_en  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ix_conversacion_seudonimo ON academico.conversacion(seudonimo, actualizada_en DESC);

CREATE TABLE academico.mensaje (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    conversacion_id  UUID         NOT NULL REFERENCES academico.conversacion(id) ON DELETE CASCADE,
    autor            VARCHAR(12)  NOT NULL CHECK (autor IN ('ESTUDIANTE', 'ASISTENTE')),
    contenido_cifrado TEXT        NOT NULL,
    fuentes          JSONB        NOT NULL DEFAULT '[]'::jsonb,   -- claves de documentos citados
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ix_mensaje_conversacion ON academico.mensaje(conversacion_id, creado_en);

-- Base de conocimiento sobre técnicas de estudio y gestión del tiempo (RAG)
CREATE TABLE academico.documento_conocimiento (
    id              SERIAL       PRIMARY KEY,
    clave           VARCHAR(60)  NOT NULL UNIQUE,
    titulo          VARCHAR(200) NOT NULL,
    tema            VARCHAR(40)  NOT NULL,
    referencia      TEXT         NOT NULL,                  -- fuente bibliográfica (APA)
    hash_contenido  CHAR(64)     NOT NULL,                  -- para reindexar solo si cambia
    indexado_en     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE academico.fragmento_conocimiento (
    id            SERIAL       PRIMARY KEY,
    documento_id  INT          NOT NULL REFERENCES academico.documento_conocimiento(id) ON DELETE CASCADE,
    orden         INT          NOT NULL,
    contenido     TEXT         NOT NULL,
    embedding     vector(1024) NOT NULL,                    -- dimensión de bge-m3
    UNIQUE (documento_id, orden)
);

-- Índice HNSW para búsqueda aproximada por similitud de coseno
CREATE INDEX ix_fragmento_embedding
    ON academico.fragmento_conocimiento USING hnsw (embedding vector_cosine_ops);
