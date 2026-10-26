-- =============================================================================
-- SAAC · Semilla 020 · Directorio de recursos de atención
-- Datos recopilados de fuentes públicas (ver columna 'fuente'). ANTES de un
-- despliegue con usuarios reales deben confirmarse con cada unidad, ya que
-- horarios y procedimientos pueden cambiar.
-- =============================================================================

INSERT INTO canalizacion.recurso_atencion
    (nombre, tipo, descripcion, ubicacion, horario, telefono, enlace, procedimiento, fuente, orden)
VALUES
('Unidad de Salud – Área de Psicología (DBEU)', 'INSTITUCIONAL',
 'Atención psicológica para estudiantes, docentes y trabajadores de la USAC, como parte de la División de Bienestar Estudiantil Universitario.',
 'Ciudad Universitaria, zona 12. Primer nivel del edificio de Recursos Educativos (Biblioteca Central).',
 'Lunes a viernes, 7:30 a 19:00; sábados, 8:00 a 14:00 (confirmar con la unidad).',
 NULL, 'https://virtual.usac.edu.gt/dbeu/',
 'Presentarse en la consulta externa con carné vigente y solicitar cita en el área de psicología.',
 'Soy USAC (2020); División de Bienestar Estudiantil Universitario (s.f.)', 1),

('Unidad de Apoyo Psicológico – Escuela de Ciencias Psicológicas', 'INSTITUCIONAL',
 'Atención psicológica gratuita para la comunidad universitaria y el público en general.',
 'Centro Universitario Metropolitano (CUM), zona 11.',
 'Confirmar horario con la unidad.', NULL, NULL,
 'Solicitar cita directamente en la unidad.',
 'Agencia Universitaria de Noticias (2024)', 2),

('Centro Integral de Atención Psicológica (CIAP)', 'INSTITUCIONAL',
 'Atención psicológica gratuita de la Escuela de Ciencias Psicológicas.',
 'Centro Universitario Metropolitano (CUM), zona 11.',
 'Confirmar horario con la unidad.', NULL, NULL,
 'Solicitar cita directamente en la unidad.',
 'Agencia Universitaria de Noticias (2024)', 3),

('Línea ALMA de apoyo psicológico', 'LINEA_APOYO',
 'Línea gratuita y confidencial atendida por psicólogos capacitados en intervención en crisis (FUNDEGUA).',
 NULL, 'Lunes a viernes, 7:00 a 19:00.', '1582 (llamada) · 3007-1582 (WhatsApp)', NULL,
 'Llamar o escribir por WhatsApp en el horario indicado.',
 'Emisoras Unidas (2026)', 4),

('Emergencias dentro de la Ciudad Universitaria', 'EMERGENCIA',
 'Paramédicos y ambulancia para emergencias dentro del campus central.',
 'Ciudad Universitaria, zona 12.', 'Todos los días.', '1592', NULL,
 'Llamar de inmediato e indicar la ubicación exacta.',
 'Soy USAC (2020)', 5),

('Bomberos Voluntarios / Bomberos Municipales', 'EMERGENCIA',
 'Atención de emergencias médicas en todo el país, las 24 horas.',
 NULL, '24 horas, todos los días.', '122 · 123', NULL,
 'Llamar de inmediato si hay peligro para la vida.',
 'Números nacionales de emergencia de Guatemala', 6);
