-- =============================================================================
-- SAAC · Migración 006 · Roles de base de datos (mínimo privilegio)
-- La capa académica se conecta con un rol que SOLO ve el esquema academico.
-- Aunque esa capa procese salidas de un modelo de lenguaje, no puede leer
-- identidades, señales ni solicitudes. El núcleo puede insertar en las bitácoras,
-- pero no modificarlas.
-- Los usuarios de conexión (LOGIN) se crean en db/init/00_usuarios.sh con las
-- contraseñas definidas en las variables de entorno.
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_academico') THEN
        CREATE ROLE rol_academico NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_nucleo') THEN
        CREATE ROLE rol_nucleo NOLOGIN;
    END IF;
END $$;

-- Capa académica: únicamente su esquema
GRANT USAGE ON SCHEMA academico TO rol_academico;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA academico TO rol_academico;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA academico TO rol_academico;

-- Núcleo (identidad, canalización y auditoría)
GRANT USAGE ON SCHEMA identidad, canalizacion, auditoria TO rol_nucleo;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identidad    TO rol_nucleo;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA canalizacion TO rol_nucleo;
GRANT SELECT, INSERT                 ON ALL TABLES IN SCHEMA auditoria    TO rol_nucleo;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identidad, canalizacion, auditoria TO rol_nucleo;

-- Ningún rol de aplicación recibe privilegios sobre el esquema del otro
REVOKE ALL ON SCHEMA identidad, canalizacion, auditoria FROM rol_academico;
REVOKE ALL ON SCHEMA academico FROM rol_nucleo;
