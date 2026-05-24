<!-- Claude Code lee este fichero automáticamente al iniciar -->
<!-- Modelo recomendado: /model opusplan -->

# CONTEXTO DEL PROYECTO — TFG Fuzhify

## Qué es este proyecto
Sistema de generación automática de resúmenes sobre series temporales basado en
lógica difusa y minería de reglas de asociación. El pipeline convierte datos
brutos en informes en lenguaje natural.

## Pipeline (orden de ejecución obligatorio)
```
CSV raw (all) → src00 (separar por sensor) → CSV sensor
CSV raw (sensor) → src01 (fuzzificación) → CSV fuzzy
CSV fuzzy        → src02 (beam search)   → CSV reglas
CSV reglas       → src03 (NLG)           → informe .md
```

## Lógica de negocio crítica — NO reimplementar, LEER y portar

### src00 — Dividir por sensor
- Lee un CSV con muchos registros y agrupa los sensores con el mismo id en un mismo CSV.

### src01 — Fuzzificación
- Lee un CSV con columna temporal (VAR_TIEMPO) y columna métrica (VAR_METRICA).
- Granularidad detectada automáticamente (GRANULARIDAD_S = mediana de diffs).
- Genera variables t_* (temporales difusas) y v_* (métricas difusas).
- Bloques activables: GEN_ANIOS, GEN_MESES, GEN_DIAS, GEN_HORAS, GEN_MINUTOS,
  GEN_FRANJAS, GEN_LABORABLES, GEN_QUINCENAS, GEN_ESTACIONES, GEN_FESTIVOS.
- Tolerancias por bloque: TOL_HORAS=0.5, resto hereda TOLERANCIA=0.2.
- rampa_s(tol, duracion): max(tol*dur, N_MUESTRAS_RAMPA*GRANULARIDAD_S).
- N_MUESTRAS_RAMPA=2 por defecto.
- Detección automática de VAR_METRICA por heurística estadística.
- Festivos: librería `holidays`, configurable por país/subdivisión.
- Detección automática de VAR_TIEMPO: _detectar_var_tiempo() con 4
  estrategias (datetime directo, par fecha+hora, unix timestamp,
  fallback). Portada del notebook src01 celda 4.
- LLM fallback para VAR_METRICA: _llamar_llm(), _detectar_metrica_via_llm()
  portadas del notebook src01 celdas 2-3. Proveedores: gemini, anthropic,
  openai, ninguno. Configurable via settings (usar_llm_fallback,
  proveedor_llm, llm_api_key).
- El backend ya NO hardcodea var_tiempo="fecha". Cualquier CSV con
  columna temporal con cualquier nombre funciona sin renombrar.

### src02 — Beam Search
- Lee CSV fuzzy, extrae reglas de asociación difusas.
- Parámetros (decisiones del usuario, NO calibración automática):
  - MIN_SOPORTE: umbral de masa mínima (default 0.005)
  - MIN_CONFIANZA: umbral mínimo (default 0.50)
  - LIFT_MINIMO: umbral absoluto de sorpresa, seleccionable (1.0/1.5/2.0/3.0)
    con etiquetas "Incluir todas / Algo sorprendentes / Sorprendentes / Muy sorprendentes"
  - MAX_PROF: profundidad máxima del antecedente (default 3)
  - K_BEAM: anchura del haz (default 10)
  - TOP_POR_CONSECUENTE: tope por consecuente (default 10)
- El beam poda por confianza, NO por lift ni soporte.
- El lift hace dos cosas: filtra (umbral absoluto) Y ordena la salida.
- El soporte solo filtra masa mínima (admisión + aportación marginal),
  nunca ordena.
- Salida: CSV con columnas [antecedente, consecuente, soporte, confianza, lift, n_vars].

### src03 — Escala adverbial
| lift | adverbio |
|---|---|
| < 1.5 | "con cierta tendencia" |
| 1.5 ≤ lift < 2.0 | "con cierta consistencia" |
| 2.0 ≤ lift < 3.0 | "de forma notable" |
| lift ≥ 3.0 | "de forma muy marcada" |
Estos umbrales son fijos y coherentes con los del selector de src02.

### src03 — NLG
- Lee CSV de reglas, genera informe Markdown estructurado.
- Funciones clave: verbalizar_antecedente(), regla_a_frase(), agrupar_reglas().
- ETIQUETA_TEMPORAL: diccionario t_* → texto legible en español.
- Soporta: horas, franjas, días, laborables, meses, estaciones, quincenas,
  años, minutos (cuartos), festivos.
- Informe dividido en secciones por franja horaria y tipo de día.

### src04 — Informe global (PENDIENTE — implementar mañana)
- Lee los CSVs de reglas generados por src02 para múltiples sensores.
- Funciones a portar del notebook src04_informe_global__1_.ipynb:
  cargar_reglas_todos(), hora_mas_frecuente(), dia_mas_frecuente(),
  patrones_compartidos(), detectar_atipicos(), parrafo_coloquial_global(),
  construir_informe_global().
- Endpoint: GET /api/v1/pipeline/{job_id}/global-report
- Módulo: backend/app/core/global_report/global_report.py

## Stack tecnológico objetivo
- Backend: FastAPI (Python 3.11+)
- Frontend: Vue.js 3 + Vite + Axios
- Base de datos: PostgreSQL (SQLAlchemy async)
- Infraestructura: Docker + Docker Compose
- Testing: Pytest + Coverage.py

## Estructura de carpetas objetivo
```
/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   │   ├── fuzzy/        ← lógica de src01
│   │   │   ├── mining/       ← lógica de src02
│   │   │   └── nlg/          ← lógica de src03
│   │   ├── models/           ← modelos SQLAlchemy
│   │   ├── schemas/          ← modelos Pydantic
│   │   └── services/         ← orquestación del pipeline
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── api/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── CONTEXTO.md               ← este fichero
```

## Decisiones de diseño ya tomadas (no discutir, implementar)
1. La detección de VAR_METRICA es automática por heurística estadística
   (ver función _heuristica() en src01). NO pedir la métrica al usuario
   salvo que haya ambigüedad irresoluble.
2. Los GRUPOS_EXCLUYENTES y la JERARQUIA son dinámicos — se construyen
   a partir de las columnas presentes en el CSV, no hardcodeados.
3. rampa_s() garantiza que siempre hay muestras en las rampas difusas.
4. GEN_MINUTOS se activa solo si GRANULARIDAD_S < 900 (estricto).
5. t_Festivo usa la librería `holidays` con PAIS y SUBDIV configurables.
6. VAR_TIEMPO se detecta automáticamente con 4 estrategias. NO hardcodear
   "fecha". Ver _detectar_var_tiempo() en heuristic.py.
7. LIFT_MINIMO es un selector de sorpresa con niveles en lift ABSOLUTO
   (1.0/1.5/2.0/3.0). No usar percentiles. El valor es estable entre
   datasets.
8. construir_calidad() usa umbrales fijos (1.5/2.0/3.0) coherentes con
   el selector de src02. No calibrar sobre el pool de reglas.
9. src05 (calibración automática de umbrales) está DESCARTADO del pipeline.
   No implementar ni referenciar.

## Equivalencias Spring Boot → FastAPI (para el desarrollador)
- @RestController     → APIRouter
- @Service            → clase en services/
- @Repository         → clase en models/ con SQLAlchemy
- @Autowired          → Depends() de FastAPI
- @PostMapping        → @router.post()
- ResponseEntity<>    → JSONResponse o schema Pydantic
- application.yml     → .env + pydantic-settings
- @Async              → async def + await
- JUnit @Test         → def test_() con pytest
- @Transactional      → async with session.begin()

## Convenciones de código
- Python: snake_case, type hints en todas las funciones públicas.
- Vue: componentes en PascalCase, composables con use prefix.
- Commits: conventional commits (feat:, fix:, refactor:).
- Variables de entorno: siempre en .env, nunca hardcodeadas.

## Archivos de referencia en este repositorio
- notebook/src00_*.ipynb → implementación de referencia de separación por sensores
- notebooks/src01_*.ipynb → implementación de referencia de fuzzificación
- notebooks/src02_*.ipynb → implementación de referencia de beam search
- notebooks/src03_*.ipynb → implementación de referencia de NLG
- ejemplos/*.csv          → datos de ejemplo para tests
- ejemplos/*.md           → formato esperado de salida


## Estado actual (actualizar al final de cada sesión)
**Última sesión: 2026-05-24**

### Completado ✓
- **src00** — splitter.py: split_by_sensor(), detect_sensors(). Tests: 3/3.
- **src01** — fuzzy/: FuzzyConfig, trapecio(), rampa_s(), _heuristica(),
  _detectar_var_tiempo() (4 estrategias), _llamar_llm(), 
  _detectar_metrica_via_llm(), todos los bloques generar_*. Tests: 9/9.
- **src02** — mining/: BeamSearchMiner.fit(), métricas difusas,
  _construir_grupos() dinámico, _construir_jerarquia() dinámica,
  validación hora+franja, 3 filtros post-procesado. Tests: 4/4.
- **src03** — nlg/: ETIQUETA_METRICA_COLOQUIAL + ETIQUETA_METRICA_TECNICA,
  verbalizar_antecedente(), generar_resumen(), modo coloquial/técnico.
  Tests: 23/23 (19 base + 4 parametrizaciones).
- **Visualizaciones** — core/nlg/visualizations.py: 4 gráficos automáticos
  (heatmap hora×día, barras lift, scatter soporte-confianza, tabla consecuentes).
  Integrado en services/pipeline.py, genera imágenes PNG tras NLG.
- **API REST** — 5 endpoints (POST /run, GET /status, GET /report,
  GET /rules, GET /image/{filename}). Endpoint de imágenes con validación
  path traversal. Modelos SQLAlchemy async (Job, Rule).
- **Frontend** — UploadView con selector de sorpresa (lift absoluto) y
  selector de modo (coloquial/técnico). StatusView, ReportView con
  renderizado automático de imágenes desde el endpoint del backend.
- **Docker** — docker-compose.yml (postgres + backend + frontend).
- **Auditoría** — 97 elementos auditados, 0 código muerto, 100%
  justificado por notebooks v4.

### Tests totales: 61/61 ✓
| Suite | Tests |
|---|---|
| test_preprocessing.py | 3 |
| test_fuzzy.py | 9 |
| test_mining.py | 4 |
| test_nlg.py | 23 |
| test_integration.py | 18 (+3 endpoint imágenes) |
| test_global_report.py | 4 |

### Pendiente
- src04: informe global cross-sensor (implementar mañana, ver sección arriba)
- Renombrar proyecto a Fuzhify (después de src04)
- README: actualizar al final cuando todo esté completo
- Memoria del TFG: empezar tras cerrar src04

### Bloqueantes
- Ninguno. El stack arranca con docker compose up.
  Frontend en http://localhost, API en http://localhost:8000/docs.
  Las visualizaciones se generan automáticamente en cada ejecución del pipeline.