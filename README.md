# Traffic Summary System — TFG

Sistema de generación automática de resúmenes de tráfico urbano basado en **lógica difusa** y **minería de reglas de asociación**. Convierte datos brutos de sensores de tráfico en informes en lenguaje natural.

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Pipeline de datos](#pipeline-de-datos)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Requisitos previos](#requisitos-previos)
5. [Puesta en marcha](#puesta-en-marcha)
   - [Manual (desarrollo)](#manual-desarrollo)
   - [Con Docker](#con-docker)
6. [API REST](#api-rest)
7. [Frontend](#frontend)
8. [Configuración](#configuración)
9. [Tests](#tests)
10. [Ejemplos incluidos](#ejemplos-incluidos)

---

## Arquitectura

```
┌─────────────┐   HTTP/multipart   ┌──────────────────────────────────┐
│  Vue 3 SPA  │ ────────────────►  │  FastAPI (async)                 │
│  (Vite)     │ ◄────────────────  │  • POST /api/v1/pipeline/run     │
│  port 5173  │    JSON            │  • GET  /api/v1/pipeline/{id}/…  │
└─────────────┘                    └────────────┬─────────────────────┘
                                                │ BackgroundTask
                                                ▼
                                   ┌────────────────────────┐
                                   │  Pipeline Python        │
                                   │  src00 → src01 → src02 │
                                   │        → src03          │
                                   └────────────┬───────────┘
                                                │ SQLAlchemy async
                                                ▼
                                   ┌────────────────────────┐
                                   │  PostgreSQL             │
                                   │  • jobs                 │
                                   │  • rules                │
                                   └────────────────────────┘
```

**Stack:**

| Capa | Tecnología |
|---|---|
| Frontend | Vue 3 · Vite · Vue Router · Pinia · Axios · marked.js |
| Backend | FastAPI · Python 3.11+ · Uvicorn |
| Base de datos | PostgreSQL · SQLAlchemy async · asyncpg |
| Lógica difusa | NumPy · Pandas · holidays |
| Testing | Pytest · pytest-asyncio · httpx · coverage |

---

## Pipeline de datos

El sistema implementa cuatro etapas encadenadas:

```
CSV raw (multi-sensor)
    │
    ▼ src00 — Separación por sensor
CSV sensor individual
    │
    ▼ src01 — Fuzzificación
CSV fuzzy  (columnas t_* temporales + v_* métricas)
    │
    ▼ src02 — Beam search (minería de reglas difusas)
CSV reglas (antecedente, consecuente, soporte, confianza, lift)
    │
    ▼ src03 — NLG (generación de lenguaje natural)
Informe Markdown
```

### src00 — División por sensor
Lee un CSV maestro con columna `id` y separa cada sensor en un fichero independiente.

### src01 — Fuzzificación
- Detecta automáticamente la variable métrica (`_heuristica`).
- Calcula la granularidad temporal como mediana de diffs.
- Genera variables difusas `t_*` (temporales) y `v_*` (métricas).
- Bloques activables: años, meses, días, horas, minutos, franjas, laborables, quincenas, estaciones, festivos.
- `rampa_s(tol, dur)` garantiza rampas ≥ `N_MUESTRAS_RAMPA × granularidad`.

### src02 — Beam search
- Explora combinaciones de variables temporales como antecedentes.
- Métricas difusas: soporte `Σmin(μ)/N`, confianza, lift.
- Aportación marginal: solo acepta una regla si aporta soporte nuevo sobre lo ya cubierto.
- Grupos excluyentes y jerarquía semántica **dinámicos** (se construyen a partir de las columnas presentes).
- Tres filtros de post-procesado: redundancias por subconjunto, jerarquía padre→hijo, top-N por consecuente.

### src03 — NLG
- `verbalizar_antecedente()` convierte tokens temporales en frases en español.
- `agrupar_reglas()` agrupa reglas con contexto similar para párrafos narrativos.
- `generar_resumen()` produce un Markdown estructurado con estadísticas globales.

---

## Estructura del proyecto

```
/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + lifespan (create_all)
│   │   ├── core/
│   │   │   ├── config.py            # Settings (pydantic-settings + .env)
│   │   │   ├── fuzzy/               # src01: FuzzyConfig, fuzzify(), blocks
│   │   │   ├── mining/              # src02: BeamSearchMiner, metrics, groups
│   │   │   ├── nlg/                 # src03: generar_resumen(), labels
│   │   │   └── preprocessing/       # src00: split_by_sensor()
│   │   ├── api/
│   │   │   ├── deps.py              # get_db dependency
│   │   │   └── routes/pipeline.py   # 4 endpoints REST
│   │   ├── db/
│   │   │   ├── base.py              # DeclarativeBase
│   │   │   └── session.py           # async engine + AsyncSessionLocal
│   │   ├── models/                  # SQLAlchemy: Job, Rule
│   │   ├── schemas/                 # Pydantic: RunPipelineResponse, …
│   │   └── services/pipeline.py     # Background task orquestador
│   ├── tests/
│   │   ├── test_preprocessing.py    # 3 tests src00
│   │   ├── test_fuzzy.py            # 3 tests src01
│   │   ├── test_mining.py           # 4 tests src02
│   │   └── test_nlg.py              # 14 tests src03
│   ├── conftest.py                  # sys.path para pytest
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.js                  # Pinia + Vue Router mount
│   │   ├── App.vue                  # Navbar + RouterView + CSS global
│   │   ├── api/pipeline.js          # Axios: runPipeline, getStatus, …
│   │   ├── stores/job.js            # Pinia store
│   │   ├── router/index.js          # 3 rutas
│   │   └── views/
│   │       ├── UploadView.vue       # Drag & drop + parámetros avanzados
│   │       ├── StatusView.vue       # Progress bar + polling 2 s
│   │       └── ReportView.vue       # Markdown + tabla reglas + descarga
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── notebooks/                       # Implementaciones de referencia (Colab)
│   ├── src00_Preparar_Datos.ipynb
│   ├── src01_Partir_variable_tiempo.ipynb
│   ├── src02_Procesamiento_de_Métricas.ipynb
│   └── src03_Generacion_Lenguaje_Natural_2.ipynb
├── ejemplos/                        # CSVs y resúmenes de referencia
│   ├── trafico_puntos_de_interes_2024_2025.csv   # dataset completo
│   ├── 6823_intensidad_fuzzy.csv
│   ├── 6823_intensidad_reglas.csv
│   ├── 6823_intensidad_resumen.md
│   ├── 6823_ocupacion_fuzzy.csv
│   ├── 6823_ocupacion_reglas.csv
│   └── 6823_ocupacion_resumen.md
└── docker-compose.yml
```

---

## Requisitos previos

| Herramienta | Versión mínima |
|---|---|
| Python | 3.11 |
| Node.js | 18 |
| PostgreSQL | 14 (o Docker) |
| npm | 9 |

---

## Puesta en marcha

### Manual (desarrollo)

#### 1. Clonar y preparar el entorno

```bash
git clone <url-del-repo>
cd mi-proyecto-tfg
```

#### 2. Backend

```bash
cd backend

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env               # editar DATABASE_URL si es necesario
```

Contenido mínimo de `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tfg
UPLOAD_DIR=/tmp/tfg_uploads
```

Crear la base de datos en PostgreSQL:

```sql
CREATE DATABASE tfg;
```

> Las tablas (`jobs`, `rules`) se crean automáticamente al arrancar la API gracias al lifespan de FastAPI (`Base.metadata.create_all`).

Arrancar el servidor:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La documentación interactiva estará disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 3. Frontend

```bash
cd frontend

npm install

# Configurar URL de la API
cp .env.example .env               # VITE_API_URL=http://localhost:8000

npm run dev
```

La aplicación estará disponible en `http://localhost:5173`.

---

### Con Docker

> Los `Dockerfile` están pendientes de implementación. Mientras tanto, usa el modo manual.

Una vez implementados, el arranque completo será:

```bash
docker compose up --build
```

---

## API REST

Base URL: `http://localhost:8000/api/v1/pipeline`

### `POST /run`

Lanza el pipeline completo en background y devuelve un `job_id`.

**Request** — `multipart/form-data`:

| Campo | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `file` | CSV | — | Fichero CSV del sensor |
| `min_lift` | float | `1.5` | Lift mínimo de las reglas |
| `min_confianza` | float | `0.5` | Confianza mínima (0–1) |
| `min_soporte` | float | `0.005` | Soporte difuso mínimo |
| `beam_width` | int | `10` | Anchura del beam search |
| `max_vars` | int | `3` | Profundidad máxima del antecedente |
| `tol_horas` | float | `0.5` | Tolerancia de rampa para horas |

**Response** `202`:

```json
{ "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6" }
```

---

### `GET /{job_id}/status`

**Response** `200`:

```json
{
  "job_id":    "3fa85f64-...",
  "status":    "running",
  "progress":  50,
  "step":      "Minando reglas…",
  "sensor_id": "6823",
  "metrica":   "intensidad",
  "error_msg": null
}
```

`status` puede ser: `pending` · `running` · `done` · `error`

---

### `GET /{job_id}/report`

**Response** `200`:

```json
{
  "job_id":    "3fa85f64-...",
  "status":    "done",
  "sensor_id": "6823",
  "metrica":   "intensidad",
  "report_md": "# Resumen de comportamiento — Sensor 6823\n..."
}
```

Mientras el job no ha terminado, `report_md` es `null`.

---

### `GET /{job_id}/rules?page=1&page_size=50`

**Query params:**

| Param | Por defecto | Máximo |
|---|---|---|
| `page` | `1` | — |
| `page_size` | `50` | `200` |

**Response** `200`:

```json
{
  "job_id":    "3fa85f64-...",
  "status":    "done",
  "total":     39,
  "page":      1,
  "page_size": 50,
  "rules": [
    {
      "antecedente": "t_H07 AND t_Laborable",
      "consecuente": "v_OutlierAlto",
      "n_vars":      2,
      "soporte":     0.0445,
      "confianza":   0.5258,
      "lift":        11.87
    }
  ]
}
```

---

## Frontend

La SPA cuenta con tres vistas:

| Ruta | Vista | Descripción |
|---|---|---|
| `/` | `UploadView` | Drag & drop del CSV + panel de parámetros avanzados colapsable |
| `/status/:jobId` | `StatusView` | Barra de progreso con polling cada 2 s; redirige automáticamente a `/report` cuando el job termina |
| `/report/:jobId` | `ReportView` | Informe Markdown renderizado + tabla de reglas ordenable por cualquier columna + botón de descarga |

---

## Configuración

### Backend — variables de entorno (`backend/.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/tfg` | Cadena de conexión async a PostgreSQL |
| `UPLOAD_DIR` | `<tmpdir>/tfg_uploads` | Directorio temporal para los CSVs subidos |

### Frontend — variables de entorno (`frontend/.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `VITE_API_URL` | `` (vacío → proxy Vite) | URL base de la API. En producción: `https://api.tudominio.com` |

---

## Tests

Los tests se ejecutan desde el directorio `backend/`:

```bash
cd backend
pytest tests/ -v
```

| Suite | Fichero | Tests |
|---|---|---|
| Preprocesado (src00) | `tests/test_preprocessing.py` | 3 |
| Fuzzificación (src01) | `tests/test_fuzzy.py` | 3 |
| Minería (src02) | `tests/test_mining.py` | 4 |
| NLG (src03) | `tests/test_nlg.py` | 14 |
| **Total** | | **24** |

Con cobertura:

```bash
coverage run -m pytest tests/ && coverage report -m
```

Casos cubiertos destacados:

- `trapecio(x=0, a=-1800, b=0, c=3600, d=5400)` → `1.0`
- `rampa_s(0.5, 3600, granularidad_s=900, n_muestras_rampa=2)` → `1800.0`
- `_heuristica()` detecta `intensidad` como CLARA e ignora `utm_x` y `latitud`
- `BeamSearchMiner.fit()` sobre `6823_intensidad_fuzzy.csv` retorna ≥ 1 regla con `lift > 1.0`
- `verbalizar_antecedente({"t_M00", "t_H08"})` pone el minuto antes que la hora
- `generar_resumen()` nunca produce `"condiciones no especificadas"` para tokens conocidos

---

## Ejemplos incluidos

En el directorio `ejemplos/` se incluyen ficheros de referencia del sensor `6823`:

| Fichero | Descripción |
|---|---|
| `trafico_puntos_de_interes_2024_2025.csv` | Dataset completo (todos los sensores, 2024–2025) |
| `6823_intensidad_fuzzy.csv` | Salida de src01 para intensidad |
| `6823_intensidad_reglas.csv` | Salida de src02 para intensidad |
| `6823_intensidad_resumen.md` | Informe final de intensidad |
| `6823_ocupacion_fuzzy.csv` | Salida de src01 para ocupación |
| `6823_ocupacion_reglas.csv` | Salida de src02 para ocupación |
| `6823_ocupacion_resumen.md` | Informe final de ocupación |

Para probar el sistema manualmente, sube `trafico_puntos_de_interes_2024_2025.csv` o cualquiera de los CSVs de sensor individual desde la interfaz web.

---

## Decisiones de diseño relevantes

- **Detección automática de VAR_METRICA**: la heurística `_heuristica()` clasifica columnas como CLARAS o AMBIGUAS usando estadísticos (CV, unicidad, variabilidad temporal) y un diccionario de tokens positivos/negativos. No se pregunta al usuario salvo ambigüedad irresoluble.
- **GEN_MINUTOS estrictamente `< 900`**: activado solo si la granularidad es subhoraria (< 15 min), no `≤`.
- **GRUPOS_EXCLUYENTES y JERARQUIA dinámicos**: se construyen a partir de las columnas presentes en el CSV fuzzy, lo que hace el código robusto ante cualquier combinación de bloques activos en src01.
- **Aportación marginal en beam search**: una regla solo se acepta si aporta soporte nuevo sobre las reglas ya aceptadas (`calcular_aportacion`), evitando redundancias desde el origen.
- **CPU-bound en thread pool**: las tres etapas de cálculo pesado (`fuzzify`, `BeamSearchMiner.fit`, `generar_resumen`) se ejecutan en `loop.run_in_executor(None, …)` para no bloquear el event loop de FastAPI.
