<!-- Claude Code lee este fichero automáticamente al iniciar -->
<!-- Modelo recomendado: /model opusplan -->

# CONTEXTO DEL PROYECTO — TFG Traffic Summary System

## Qué es este proyecto
Sistema de generación automática de resúmenes de tráfico urbano basado en
lógica difusa y minería de reglas de asociación. El pipeline convierte datos
brutos de sensores de tráfico en informes en lenguaje natural.

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

### src02 — Beam Search
- Lee CSV fuzzy, extrae reglas de asociación difusas.
- Parámetros clave: MIN_SOPORTE, MIN_CONFIANZA, MIN_LIFT, BEAM_WIDTH, MAX_VARS.
- Filtros: variables constantes, grupos mutuamente excluyentes (dinámicos),
  jerarquía semántica (dinámico según columnas presentes), combinaciones inválidas.
- Salida: CSV con columnas [antecedente, consecuente, soporte, confianza, lift, n_vars].

### src03 — NLG
- Lee CSV de reglas, genera informe Markdown estructurado.
- Funciones clave: verbalizar_antecedente(), regla_a_frase(), agrupar_reglas().
- ETIQUETA_TEMPORAL: diccionario t_* → texto legible en español.
- Soporta: horas, franjas, días, laborables, meses, estaciones, quincenas,
  años, minutos (cuartos), festivos.
- Informe dividido en secciones por franja horaria y tipo de día.

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
**Última sesión: 2026-05-02**

### Completado ✓
- **src00** — `backend/app/core/preprocessing/splitter.py`: `split_by_sensor()`, `detect_sensors()`. Tests: 3/3.
- **src01** — `backend/app/core/fuzzy/`: `FuzzyConfig`, `trapecio()`, `rampa_s()`, `_heuristica()`, todos los bloques `generar_*`, `fuzzify()`. Tests: 3/3.
- **src02** — `backend/app/core/mining/`: `BeamSearchMiner.fit()`, métricas difusas, `_construir_grupos()` dinámico, `_construir_jerarquia()` dinámica, 3 filtros de post-procesado. Tests: 4/4.
- **src03** — `backend/app/core/nlg/`: `ETIQUETA_TEMPORAL` completo (años 2020-2030, festivos, minutos), `verbalizar_antecedente()`, `generar_resumen()`. Tests: 14/14.
- **API REST** — `backend/app/api/routes/pipeline.py`: 4 endpoints (`POST /run`, `GET /status`, `GET /report`, `GET /rules?sensor_id=`). Modelos SQLAlchemy async (`Job`, `Rule`). BackgroundTask con `run_in_executor` para no bloquear el event loop.
- **Auth** — `backend/app/api/deps.py`: `verify_api_key` con header `X-API-Key`. Desactivada si `API_KEY=""` (desarrollo). Aplicada a todos los endpoints vía `dependencies=[]` en el router.
- **Multi-sensor** — `backend/app/services/pipeline.py`: `_get_all_sensor_paths()` + loop sobre todos los sensores del CSV. Reglas etiquetadas con `sensor_id`. Informes combinados. Progreso proporcional al número de sensores.
- **Frontend** — `frontend/src/`: `UploadView` (drag & drop + parámetros avanzados), `StatusView` (polling 2 s + barra de progreso), `ReportView` (Markdown con marked.js + tabla reglas ordenable + descarga). Pinia + Vue Router.
- **Docker** — `backend/Dockerfile`, `frontend/Dockerfile` (multi-stage → nginx), `docker-compose.yml` (postgres + backend + frontend + volumen uploads, healthcheck pg_isready, `API_KEY` env var).
- **Documentación** — `README.md` completo en la raíz.

### Tests totales: 38/38 ✓
| Suite | Tests |
|---|---|
| test_preprocessing.py | 3 |
| test_fuzzy.py | 3 |
| test_mining.py | 4 |
| test_nlg.py | 14 |
| test_integration.py | 14 |

### Próximos pasos sugeridos
- Añadir Alembic para migraciones de base de datos (actualmente `create_all` en lifespan).
- Tests E2E completos: upload de CSV real + esperar `status=done` + verificar reglas y report.
- Soporte para cancelar/eliminar un job en curso.
- Rate limiting en los endpoints (p. ej. `slowapi`).

### Bloqueantes
- Ninguno. El stack arranca localmente con `uvicorn` + PostgreSQL. Tests: `pytest tests/ -q`.