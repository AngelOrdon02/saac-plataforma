-- =============================================================================
-- SAAC · Semilla 010 · Catálogo de indicadores
-- Cada indicador del dominio DEPRESIVO corresponde a un ítem del PHQ-9
-- (Kroenke et al., 2001) y cada indicador ANSIOSO a un ítem de la GAD-7
-- (Spitzer et al., 2006). Los dominios FUNCIONAL y TEMPORAL representan los
-- criterios de deterioro funcional y persistencia descritos por NICE (2011).
-- El ítem 9 del PHQ-9 no se incluye aquí: se trata como señal de riesgo.
-- 'compartido' = la expresión también describe una dificultad académica
-- ordinaria, por lo que no cuenta por sí sola como señal emocional.
-- =============================================================================

INSERT INTO canalizacion.indicador (codigo, dominio, referencia, descripcion, compartido) VALUES
('D1', 'DEPRESIVO', 'PHQ-9, ítem 1', 'Poco interés o placer en hacer las cosas', FALSE),
('D2', 'DEPRESIVO', 'PHQ-9, ítem 2', 'Ánimo decaído, tristeza o desesperanza', FALSE),
('D3', 'DEPRESIVO', 'PHQ-9, ítem 3', 'Alteraciones del sueño (dormir poco o demasiado)', FALSE),
('D4', 'DEPRESIVO', 'PHQ-9, ítem 4', 'Cansancio o falta de energía', TRUE),
('D5', 'DEPRESIVO', 'PHQ-9, ítem 5', 'Alteraciones del apetito', FALSE),
('D6', 'DEPRESIVO', 'PHQ-9, ítem 6', 'Sentimientos de fracaso o desvalorización', FALSE),
('D7', 'DEPRESIVO', 'PHQ-9, ítem 7', 'Dificultad para concentrarse', TRUE),
('D8', 'DEPRESIVO', 'PHQ-9, ítem 8', 'Enlentecimiento o inquietud psicomotora', FALSE),
('A1', 'ANSIOSO',   'GAD-7, ítem 1', 'Nerviosismo, ansiedad o tensión', FALSE),
('A2', 'ANSIOSO',   'GAD-7, ítem 2', 'Preocupación que no se puede detener o controlar', FALSE),
('A3', 'ANSIOSO',   'GAD-7, ítem 3', 'Preocupación excesiva por diferentes cosas', FALSE),
('A4', 'ANSIOSO',   'GAD-7, ítem 4', 'Dificultad para relajarse', FALSE),
('A5', 'ANSIOSO',   'GAD-7, ítem 5', 'Inquietud que impide quedarse quieto', FALSE),
('A6', 'ANSIOSO',   'GAD-7, ítem 6', 'Irritabilidad o molestia fácil', FALSE),
('A7', 'ANSIOSO',   'GAD-7, ítem 7', 'Temor de que algo terrible pueda pasar', FALSE),
('F1', 'FUNCIONAL', 'NICE (2011), deterioro funcional', 'El malestar interfiere con clases, tareas o actividades cotidianas', FALSE),
('T1', 'TEMPORAL',  'NICE (2011), persistencia', 'El malestar se mantiene por dos semanas o más', FALSE);
