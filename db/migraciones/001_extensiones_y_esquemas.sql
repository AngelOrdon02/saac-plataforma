-- =============================================================================
-- SAAC · Migración 001
-- Extensiones y esquemas. Cada esquema corresponde a una capa o dominio de la
-- arquitectura, de modo que la separación entre capas también se aplique en la
-- base de datos (sección 3.5 del documento).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector: índice vectorial para RAG
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

-- Identidad real de las personas usuarias (único lugar con datos identificativos)
CREATE SCHEMA IF NOT EXISTS identidad;

-- Capa de acompañamiento académico: conversaciones y base de conocimiento
CREATE SCHEMA IF NOT EXISTS academico;

-- Capa de clasificación y canalización: señales, tamizajes y solicitudes
CREATE SCHEMA IF NOT EXISTS canalizacion;

-- Trazabilidad: bitácoras de solo inserción con encadenamiento de hashes
CREATE SCHEMA IF NOT EXISTS auditoria;
