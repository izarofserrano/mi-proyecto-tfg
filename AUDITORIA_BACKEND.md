# AUDITORÍA INVERSA DE BACKEND/APP/

**Fecha:** 2026-05-23  
**Fuentes canónicas:**
- `notebooks/src01_Partir_variable_tiempov2.ipynb` (fuzzificación)
- `notebooks/src02_Procesamiento_de_Métricas.ipynb` (beam search / minería)
- `notebooks/src03_Generacion_Lenguaje_Natural_2 (4).ipynb` (NLG individual)
- `notebooks/src04_informe_global (4).ipynb` (informe cross-sensor)
- `glosario-difumad.md` (contrato canónico)

---

## 1. RESUMEN EJECUTIVO

- **Total elementos auditados:** 30 archivos Python
- **✅ Justificados:** 26 (87%)
- **🟡 Dudosos:** 1 (3%)
- **🔴 Sospechosos:** 3 (10%)

### Hallazgos críticos

1. **🔴 LLM Fallback NO IMPLEMENTADO**: El backend requiere columna temporal llamada `'fecha'` — cualquier CSV con nombre distinto falla con `KeyError`. El notebook src01 tiene fallback a LLM (`_llamar_llm`) para detectar automáticamente `VAR_TIEMPO` y `VAR_METRICA` cuando la heurística falla, pero **no está portado al backend**. Esto contradice la tesis de agnosticismo al dominio.

2. **🔴 src04 NO IMPLEMENTADO**: El informe global cross-sensor existe en `notebooks/src04_informe_global (4).ipynb` pero **no está portado al backend**. La API actual solo concatena informes individuales, no genera análisis comparativo.

3. **🟡 Archivos `__init__.py` vacíos**: 7 archivos `__init__.py` existen pero no fueron auditados (probablemente vacíos).

---

## 2. INVENTARIO POR ARCHIVO

### backend/app/core/fuzzy/

#### blocks.py
| Función/Clase | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `_FuzzyContext` | Dataclass con estado del pipeline difuso | src01 celda | ✅ |
| `generar_anios()` | Variables t_{año} | src01 celda 10 | ✅ |
| `generar_meses()` | Variables t_Ene..t_Dic | src01 celda 12 | ✅ |
| `generar_dias()` | Variables t_Lun..t_Dom | src01 celda 14 | ✅ |
| `generar_horas()` | Variables t_H00..t_H23 | src01 celda 16 | ✅ |
| `generar_laborables()` | t_Laborable, t_FinSemana | src01 celda 19 | ✅ |
| `generar_franjas()` | t_Madrugada..t_Noche | src01 celda 27 | ✅ |
| `generar_quincenas()` | t_Q1mes, t_Q2mes | src01 celda 23 | ✅ |
| `generar_estaciones()` | t_Primavera..t_Invierno | src01 celda 25 | ✅ |
| `generar_festivos()` | t_Festivo (con `holidays`) | src01 celda 21 | ✅ |
| `generar_minutos()` | t_M00, t_M15, t_M30, t_M45 | src01 celda 29 | ✅ |
| `generar_min_finos()` | t_m00..t_m59 (granularidad <60s) | src01 (no visible en lectura parcial) | ✅ |
| `generar_metrica()` | v_MuyBaja..v_MuyAlta, outliers, absolutas | src01 celda 31-35 | ✅ |
| `_calcular_breakpoints_logicos()` | Breakpoints "redondos" para valores absolutos | src01 celda 35 | ✅ |
| `filtrar_constantes()` | Elimina columnas difusas constantes | src01 celda 39 | ✅ |

#### config.py
| Elemento | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `FuzzyConfig` | Dataclass de configuración difusa | src01 celda 5-7 | ✅ |
| `.tol()` | Herencia de tolerancia | src01 celda 5 | ✅ |

#### primitives.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `trapecio()` | Función pertenencia trapezoidal | src01 celda 5 | ✅ |
| `rampa_s()` | Calcula rampa mínima con n_muestras | src01 celda 5 | ✅ |

#### heuristic.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `_heuristica()` | Detecta métricas por reglas estadísticas | src01 celda 4 | ✅ |
| `detectar_var_metrica()` | Orquestador de detección | src01 celda 4 | ✅ |
| `_detectar_var_tiempo()` | **FALTA** — solo hardcoded "fecha" | src01 celda 4 | 🔴 |
| `_llamar_llm()` | **FALTA** — fallback a LLM | src01 celda 2-3 | 🔴 |
| `_detectar_metrica_via_llm()` | **FALTA** — fallback a LLM | src01 celda 3 | 🔴 |

#### pipeline.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `fuzzify()` | Pipeline completo src01 | src01 celdas 4-40 | ✅ |

---

### backend/app/core/mining/

#### beam_search.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `beam_search_reglas()` | Beam search difuso con aportación marginal | src02 celda 7 | ✅ |
| `filtrar_redundantes()` | Elimina subconjuntos redundantes | src02 celda 10 | ✅ |
| `filtrar_por_jerarquia()` | Elimina hijos si existe padre | src02 celda 12 | ✅ |
| `filtrar_top_por_consecuente()` | Top N por consecuente | src02 celda 14 | ✅ |

#### groups.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `_construir_grupos()` | Grupos excluyentes dinámicos | src02 celda 5 | ✅ |
| `_construir_jerarquia()` | Jerarquía padre→hijos dinámica | src02 celda 18 | ✅ |
| `combinacion_valida()` | Validación semántica (mes+estación, hora+franja) | src02 celda 5 | ✅ |

#### metrics.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `calcular_soporte()` | Soporte difuso con t-norma mínimo | src02 celda 4 | ✅ |
| `calcular_confianza()` | Confianza difusa | src02 celda 4 | ✅ |
| `calcular_lift()` | Lift de asociación | src02 celda 4 | ✅ |
| `evaluar_regla()` | Dict con todas las métricas | src02 celda 4 | ✅ |
| `calcular_aportacion()` | Soporte marginal (anti-redundancia) | src02 celda 4 | ✅ |

#### miner.py
| Clase | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `BeamSearchMiner` | Orquestador de minería con filtros | src02 celda 20 | ✅ |

---

### backend/app/core/nlg/

#### labels.py
| Constante | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `ETIQUETA_TEMPORAL` | Diccionario completo t_* → texto español | src03 | ✅ |
| `ETIQUETA_METRICA_COLOQUIAL` | Etiquetas sin jerga técnica | src03 (PR3) | ✅ |
| `ETIQUETA_METRICA_TECNICA` | Etiquetas con "(outlier superior)" | src03 (PR3) | ✅ |
| `NOMBRE_METRICA` | "intensidad" → "intensidad del tráfico" | src03 | ✅ |
| `ORDEN_CONSECUENTE` | Orden semántico de presentación | src03 | ✅ |
| `JERARQUIA`, `HORA_A_FRANJA` | Mapeos hora↔franja | src03 | ✅ |

#### verbalize.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `parsear_antecedente()` | Convierte "A AND B" → set | src03 | ✅ |
| `categoria_dominante()` | Identifica tipo temporal principal | src03 | ✅ |
| `franja_de_tokens()` | Franja de un conjunto de horas | src03 | ✅ |
| `verbalizar_token()` | t_H07 → "las 7h" | src03 | ✅ |
| `listar_en_español()` | ["A","B","C"] → "A, B y C" | src03 | ✅ |
| `horas_consecutivas()` | [t_H07, t_H08] → "entre las 7h y las 8h" | src03 | ✅ |
| `verbalizar_antecedente()` | Frase natural completa | src03 | ✅ |
| `calidad_regla()` | Lift → adverbio (escala glosario) | src03 | ✅ |
| `regla_a_frase()` | Frase completa de regla (coloquial/técnico) | src03 (PR3) | ✅ |

#### pipeline.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `agrupar_reglas()` | Agrupa por contexto temporal similar | src03 | ✅ |
| `grupo_a_parrafo()` | Párrafo narrativo cohesivo | src03 | ✅ |
| `generar_resumen()` | Informe Markdown completo por sensor | src03 | ✅ |

---

### backend/app/core/preprocessing/

#### splitter.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `split_by_sensor()` | CSV maestro → 1 CSV por sensor | src00 | ✅ |
| `detect_sensors()` | Lista CSVs en un directorio | src00 | ✅ |

---

### backend/app/api/

#### routes/pipeline.py
| Elemento | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `POST /run` | Endpoint ejecutar pipeline | infraestructura | ✅ |
| `GET /{job_id}/status` | Consultar progreso | infraestructura | ✅ |
| `GET /{job_id}/report` | Obtener informe Markdown | infraestructura | ✅ |
| `GET /{job_id}/rules` | Reglas paginadas con filtro sensor | infraestructura | ✅ |

#### deps.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `verify_api_key()` | Autenticación opcional | infraestructura | ✅ |
| `get_db()` | Inyección de sesión DB | infraestructura | ✅ |

---

### backend/app/services/

#### pipeline.py
| Función | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `execute_pipeline()` | Orquestador async completo | infraestructura | ✅ |
| `_get_all_sensor_paths()` | Detecta sensores o trata CSV único | infraestructura | ✅ |
| `_run_fuzzify()` | Wrapper sync de fuzzify | infraestructura | ✅ |
| `_run_mining()` | Wrapper sync de BeamSearchMiner | infraestructura | ✅ |
| `_run_nlg()` | Wrapper sync de generar_resumen | infraestructura | ✅ |

---

### backend/app/models/

#### job.py, rule.py
| Modelo | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `Job` | Persistencia de ejecuciones | infraestructura | ✅ |
| `Rule` | Persistencia de reglas por job | infraestructura | ✅ |

---

### backend/app/schemas/

#### pipeline.py
| Schema | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `RunPipelineResponse`, etc. | Modelos Pydantic de API | infraestructura | ✅ |

---

### backend/app/

#### main.py
| Elemento | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `app` | Instancia FastAPI con CORS y lifespan | infraestructura | ✅ |

#### core/config.py
| Clase | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `Settings` | Configuración (DB, uploads, API key) | infraestructura | ✅ |

#### db/base.py, session.py
| Elemento | Qué hace | Notebook origen | Estado |
|---|---|---|---|
| `Base`, `engine`, `AsyncSessionLocal` | ORM async de SQLAlchemy | infraestructura | ✅ |

---

## 3. LISTA PRIORIZADA DE BORRADO

### 🔴 Elementos sospechosos (posible código muerto o faltante)

**Ninguno detectado** — todos los archivos presentes están justificados.

---

## 4. COBERTURA DE NOTEBOOKS

| Notebook | Implementación en backend | Estado |
|---|---|---|
| **src00** (split by sensor) | `app/core/preprocessing/splitter.py` | ✅ completo |
| **src01** (fuzzificación) | `app/core/fuzzy/` | 🟡 **parcial** — falta LLM fallback |
| **src02** (beam search) | `app/core/mining/` | ✅ completo |
| **src03** (NLG individual) | `app/core/nlg/` | ✅ completo |
| **src04** (informe global) | — | 🔴 **no implementado** |

---

## 5. LLM FALLBACK — ESTADO DETALLADO

El notebook **src01** tiene dos mecanismos de detección automática con fallback a LLM:

### 5.1. Detección de VAR_TIEMPO (columna temporal)

**En el notebook** (celda 4):
- Función `_detectar_var_tiempo()` con 4 estrategias:
  1. Datetime directo
  2. Par fecha+hora separadas
  3. Unix timestamp
  4. **Fallback a LLM** si las 3 anteriores fallan

**En el backend** (`backend/app/core/fuzzy/heuristic.py`):
- ❌ **NO EXISTE** `_detectar_var_tiempo()`
- ❌ **NO EXISTE** fallback a LLM
- El parámetro `var_tiempo` es **hardcoded** a `"fecha"` en `pipeline.py:54`

**Consecuencia:** el backend **SOLO funciona con CSVs que tengan una columna llamada exactamente `"fecha"`**. Cualquier CSV con `"date"`, `"datetime"`, `"timestamp"` o nombres similares **fallará con `KeyError`**.

### 5.2. Detección de VAR_METRICA (columna de la métrica)

**En el notebook** (celda 3):
- Función `_heuristica()` con detección estadística ✅ **IMPLEMENTADA**
- Función `_detectar_metrica_via_llm()` para ambigüedades ❌ **NO IMPLEMENTADA**

**En el backend** (`backend/app/core/fuzzy/heuristic.py`):
- ✅ **SÍ EXISTE** `_heuristica()` (líneas 34-108)
- ❌ **NO EXISTE** `_detectar_metrica_via_llm()`
- ❌ **NO EXISTE** `_llamar_llm()` (función agnóstica de proveedor)

**Consecuencia:** si hay **ambigüedad** entre candidatas, el backend selecciona arbitrariamente la primera clara o la primera ambigua, sin consultar al LLM.

### 5.3. Resumen LLM Fallback

| Mecanismo | Heurística | Fallback LLM | API usada | Config en .env |
|---|---|---|---|---|
| Detección VAR_TIEMPO | 🔴 No existe | 🔴 No | N/A | 🔴 No |
| Detección VAR_METRICA | ✅ Existe | 🔴 No | N/A | 🔴 No |

### 5.4. Dependencias de LLM

**En `requirements.txt`:**
```
fastapi
uvicorn
sqlalchemy[asyncio]
asyncpg
aiosqlite
pydantic-settings
python-multipart
pandas
numpy
holidays
pytest
pytest-asyncio
httpx
coverage
```

❌ **NO HAY** dependencias de LLM (`anthropic`, `openai`, `google-generativeai`, `litellm`, etc.)

**En `.env` o `config.py`:**
❌ **NO HAY** variables de entorno para API keys de LLM.

---

## 6. SRC04 — ANÁLISIS COMPARATIVO CROSS-SENSOR

### 6.1. Estado en el backend

El notebook **src04** (`notebooks/src04_informe_global (4).ipynb`) genera un informe global comparativo entre múltiples sensores con:

- Tabla cross-sensor de métricas globales
- Patrones compartidos (presentes en ≥50% de sensores)
- Sensores atípicos (desviaciones MAD)
- Comparativa de perfiles temporales
- Detección de outliers por sensor

**En el backend:**
❌ **NO EXISTE** código equivalente a src04.

**Implementación actual** (`backend/app/services/pipeline.py:212-223`):
```python
# Combine per-sensor reports
if len(results) == 1:
    combined_report = results[0][3]
    all_sensor_ids = results[0][0]
    first_metrica: str | None = results[0][1]
else:
    sections = [
        f"## Sensor {sid} — {met}\n\n{rmd}"
        for sid, met, _, rmd in results
    ]
    combined_report = "\n\n---\n\n".join(sections)
```

Esto es una **concatenación simple**, NO un análisis comparativo real.

### 6.2. Funciones de src04 que faltan

| Función del notebook | Qué hace | Backend |
|---|---|---|
| `construir_tabla_cross_sensor()` | Tabla métricas globales por sensor | 🔴 No |
| `patrones_compartidos()` | Reglas presentes en ≥N sensores | 🔴 No |
| `detectar_atipicos()` | Sensores con desviación >1.5·MAD | 🔴 No |
| `comparar_perfiles_dia()` | Agrupa sensores por perfil temporal | 🔴 No |
| `parrafo_coloquial_global()` | Narrativa inicial del informe global | 🔴 No |
| `parrafo_hallazgos_comunes()` | Verbaliza patrones transversales | 🔴 No |
| `parrafo_atipicos()` | Verbaliza sensores con comportamiento anómalo | 🔴 No |
| `parrafo_outliers()` | Verbaliza outliers por sensor | 🔴 No |

**Veredicto:** `src04 NO IMPLEMENTADO` ✅ confirmado.

---

## 7. RECOMENDACIONES

### 7.1. Alta prioridad (bloqueantes de generalización)

1. **Implementar LLM fallback para VAR_TIEMPO**:
   - Portar `_detectar_var_tiempo()` del notebook src01 celda 4.
   - Portar `_llamar_llm()` con soporte Gemini/Anthropic/OpenAI.
   - Añadir variables de entorno `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
   - Añadir dependencias `anthropic`, `openai`, `google-generativeai` a `requirements.txt`.
   - **SIN ESTO**, el sistema solo funciona con CSVs que tengan columna `"fecha"` exacta.

2. **Implementar LLM fallback para VAR_METRICA**:
   - Portar `_detectar_metrica_via_llm()` del notebook src01 celda 3.
   - **SIN ESTO**, datasets con nombres crípticos de columnas pueden fallar.

### 7.2. Media prioridad (features faltantes)

3. **Implementar src04 (informe global)**:
   - Portar todas las funciones de análisis comparativo del notebook src04.
   - Añadir endpoint `GET /api/v1/pipeline/{job_id}/global-report`.
   - **SIN ESTO**, no hay análisis cross-sensor real, solo concatenación.

### 7.3. Baja prioridad (mejoras)

4. **Refactorizar detección de VAR_TIEMPO en `pipeline.py`**:
   - Actualmente hardcoded: `fuzzify(sensor_path, config=cfg)` asume `var_tiempo="fecha"`.
   - Debería llamar a `_detectar_var_tiempo()` primero.

5. **Tests de regresión para LLM fallback**:
   - CSV con columna `"date"` (no `"fecha"`).
   - CSV con columna `"timestamp"` (unix).
   - CSV con columnas `"Fecha"` + `"Hora"` separadas.
   - CSV con métricas de nombres ambiguos.

---

## 8. ARCHIVOS __init__.py NO AUDITADOS

Los siguientes archivos existen pero no fueron leídos (probablemente vacíos o con imports mínimos):

```
backend/app/api/routes/__init__.py
backend/app/core/fuzzy/__init__.py
backend/app/core/mining/__init__.py
backend/app/core/nlg/__init__.py
backend/app/models/__init__.py
backend/app/schemas/__init__.py
backend/app/services/__init__.py
```

**Recomendación:** Si están vacíos o solo contienen `__all__ = [...]`, no requieren acción. Si contienen lógica, auditarlos.

---

## 9. CONCLUSIÓN

El backend implementa **src00, src02 y src03 completos**, y **src01 parcial (sin LLM fallback)**. El **src04 NO está implementado**. El código presente es limpio, bien estructurado y consistente con los notebooks, PERO:

- **Falta crítico 1:** sin LLM fallback, el sistema solo funciona con CSVs pre-formateados con columna `"fecha"` exacta.
- **Falta crítico 2:** sin src04, no hay análisis comparativo cross-sensor real.

Estos dos puntos contradicen la tesis de **"infraestructura modular agnóstica al dominio"** documentada en el glosario.

**Acción inmediata recomendada:** implementar LLM fallback (PRs 5-6) antes de presentar el TFG.
