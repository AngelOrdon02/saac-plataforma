-- =============================================================================
-- SAAC · Migración 002 · Esquema identidad
-- Contiene los únicos datos que permiten identificar a una persona. El resto de
-- esquemas se relaciona con ella solo mediante el seudónimo.
-- =============================================================================

CREATE TABLE identidad.usuario (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    correo           VARCHAR(254) NOT NULL UNIQUE,
    hash_contrasena  TEXT         NOT NULL,                 -- Argon2id
    nombre_cifrado   TEXT         NOT NULL,                 -- Fernet (AES-128-CBC + HMAC-SHA256)
    telefono_cifrado TEXT,                                  -- opcional, cifrado
    rol              VARCHAR(20)  NOT NULL
                     CHECK (rol IN ('ESTUDIANTE', 'ATENCION', 'ADMIN')),
    seudonimo        CHAR(24)     NOT NULL UNIQUE,          -- HMAC-SHA256(id) truncado
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    ultimo_acceso    TIMESTAMPTZ
);

COMMENT ON TABLE  identidad.usuario IS 'Personas usuarias. Único lugar con datos identificativos.';
COMMENT ON COLUMN identidad.usuario.seudonimo IS 'Identificador que usan las demás capas en lugar del id real.';

-- Registro del consentimiento informado aceptado al crear la cuenta
CREATE TABLE identidad.consentimiento (
    id           BIGSERIAL    PRIMARY KEY,
    usuario_id   UUID         NOT NULL REFERENCES identidad.usuario(id) ON DELETE CASCADE,
    version      VARCHAR(20)  NOT NULL,
    hash_texto   CHAR(64)     NOT NULL,                     -- SHA-256 del texto aceptado
    aceptado_en  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ix_consentimiento_usuario ON identidad.consentimiento(usuario_id);
