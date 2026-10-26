-- =============================================================================
-- SAAC · Migración 005 · Esquema auditoria
-- Bitácoras de solo inserción. Cada registro incluye el hash del anterior, de
-- modo que cualquier alteración posterior rompe la cadena y es detectable
-- (Schneier y Kelsey, 1999). Además, los disparadores impiden UPDATE, DELETE y
-- TRUNCATE incluso al propietario de las tablas.
-- =============================================================================

CREATE TABLE auditoria.bitacora_decision (
    id                 BIGSERIAL    PRIMARY KEY,
    evaluacion_id      UUID         NOT NULL,
    seudonimo          CHAR(24)     NOT NULL,
    origen             VARCHAR(12)  NOT NULL,
    categoria          VARCHAR(2)   NOT NULL,
    accion             VARCHAR(30)  NOT NULL,
    reglas             JSONB        NOT NULL,   -- reglas evaluadas y la que se cumplió
    evidencias         JSONB        NOT NULL,   -- códigos de indicadores, puntajes, patrones
    version_reglas     VARCHAR(20)  NOT NULL,
    huella_reglas      CHAR(64)     NOT NULL,   -- SHA-256 del archivo de reglas vigente
    componente_modelo  VARCHAR(80),             -- modelo usado por el extractor, si aplica
    registrado_en      VARCHAR(40)  NOT NULL,   -- ISO 8601 (UTC), parte del hash
    hash_anterior      CHAR(64)     NOT NULL,
    hash_actual        CHAR(64)     NOT NULL UNIQUE
);

CREATE TABLE auditoria.bitacora_acceso (
    id             BIGSERIAL    PRIMARY KEY,
    usuario_id     UUID         NOT NULL,
    rol            VARCHAR(20)  NOT NULL,
    accion         VARCHAR(40)  NOT NULL,       -- p. ej. VER_CONTACTO, CAMBIAR_ESTADO
    recurso        VARCHAR(40)  NOT NULL,
    recurso_id     VARCHAR(64),
    direccion_ip   VARCHAR(45),
    registrado_en  VARCHAR(40)  NOT NULL,
    hash_anterior  CHAR(64)     NOT NULL,
    hash_actual    CHAR(64)     NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION auditoria.impedir_modificacion() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La tabla %.% es de solo inserción', TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_bitacora_decision_inmutable
    BEFORE UPDATE OR DELETE ON auditoria.bitacora_decision
    FOR EACH ROW EXECUTE FUNCTION auditoria.impedir_modificacion();

CREATE TRIGGER tr_bitacora_decision_sin_truncate
    BEFORE TRUNCATE ON auditoria.bitacora_decision
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria.impedir_modificacion();

CREATE TRIGGER tr_bitacora_acceso_inmutable
    BEFORE UPDATE OR DELETE ON auditoria.bitacora_acceso
    FOR EACH ROW EXECUTE FUNCTION auditoria.impedir_modificacion();

CREATE TRIGGER tr_bitacora_acceso_sin_truncate
    BEFORE TRUNCATE ON auditoria.bitacora_acceso
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria.impedir_modificacion();
