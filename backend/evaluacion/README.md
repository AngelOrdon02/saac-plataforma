# Evaluación de la plataforma (capítulo 5)

Programas y datos de la evaluación descrita en el capítulo 5 del trabajo de graduación.

| Archivo | Contenido |
|---|---|
| `escenarios_v1.yaml` | 70 escenarios simulados con su resultado esperado, asignado antes de la ejecución |
| `oraculo.py` | Implementación independiente de la tabla 22 y de las supresiones (sección 3.2.3) |
| `ejecutar.py` | Motor y detectores, verificación exhaustiva, escenarios, trazabilidad, escalamiento y RNF |
| `desempeno.py` | Tiempos de clasificación, concurrencia por HTTP y carga sostenida |
| `resultados/` | Resultados en JSON de la segunda ejecución, después de corregir los defectos de la sección 5.4 (`07_desempeno.json` y `08_rnf09_proveedor.json` provienen de la primera) |
| `resultados/primera_ejecucion/` | Resultados de la primera ejecución, que detectó los dos defectos, y mediciones de desempeño |

## Cómo repetirla

Requiere la misma base de datos que las pruebas de integración (migraciones, semillas, cuentas de demostración y base de conocimiento indexada).

```bash
cd backend
pip install -r requirements-dev.txt -r evaluacion/requirements.txt
export SAAC_ENTORNO=pruebas SAAC_URL_BD_NUCLEO=... SAAC_URL_BD_ACADEMICO=...
python -m evaluacion.ejecutar --superusuario postgresql://postgres@localhost:5432/saac

# Desempeño: con la API levantada en http://127.0.0.1:8000 (un solo proceso)
uvicorn app.main:app --port 8000 &
python -m evaluacion.desempeno --duracion 300
```

La prueba de alteración de la bitácora desactiva temporalmente los disparadores con el superusuario y restaura los valores originales; ejecútela solo en una base de datos de pruebas.
