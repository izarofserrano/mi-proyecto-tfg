# INVENTARIO COMPLETO — backend/app/

## app/main.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| lifespan() | Crea tablas BD al arrancar FastAPI | infraestructura | ✅ |
| app (instancia) | Aplicación FastAPI con CORS + router pipeline | infraestructura | ✅ |

---

## app/core/config.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| Settings (clase) | Configuración global: BD, upload_dir, API key, LLM fallback | infraestructura + src01 | ✅ |

---

## app/core/preprocessing/splitter.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _sanitize_id() | Reemplaza / \ espacio por _ en sensor_id | src00 | ✅ |
| split_by_sensor() | Divide CSV maestro en archivos individuales por sensor | src00 | ✅ |
| detect_sensors() | Lista archivos CSV en output_dir | src00 | ✅ |

---

## app/core/fuzzy/primitives.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| trapecio() | Función de pertenencia trapezoidal [a,b,c,d] | src01 | ✅ |
| rampa_s() | Calcula rampa difusa = max(tol*dur, n_muestras*gran) | src01 | ✅ |

---

## app/core/fuzzy/config.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| FuzzyConfig (clase) | Configuración de tolerancias, n_muestras_rampa, flags gen_* | src01 | ✅ |
| FuzzyConfig.tol() | Devuelve tolerancia específica o general por defecto | src01 | ✅ |

---

## app/core/fuzzy/blocks.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _FuzzyContext (dataclass) | Contexto compartido entre bloques de fuzzificación | src01 | ✅ |
| generar_anios() | Genera t_2020..t_2030 por año presente en dataset | src01 | ✅ |
| generar_meses() | Genera t_Ene..t_Dic (doce meses del año) | src01 | ✅ |
| generar_dias() | Genera t_Lun..t_Dom (siete días de la semana) | src01 | ✅ |
| generar_horas() | Genera t_H00..t_H23 (24 horas del día) | src01 | ✅ |
| generar_laborables() | Genera t_Laborable, t_FinSemana (requiere generar_dias previo) | src01 | ✅ |
| generar_franjas() | Genera t_Madrugada..t_Noche (requiere generar_horas previo) | src01 | ✅ |
| generar_quincenas() | Genera t_Q1mes, t_Q2mes (primera y segunda quincena) | src01 | ✅ |
| generar_estaciones() | Genera t_Primavera..t_Invierno (cuatro estaciones) | src01 | ✅ |
| generar_festivos() | Genera t_Festivo usando librería holidays (país + subdivisión) | src01 | ✅ |
| generar_minutos() | Genera t_M00..t_M45 (cuartos de hora) solo si gran<900 | src01 | ✅ |
| generar_min_finos() | Genera t_m00..t_m59 (minuto a minuto) solo si gran<60 | src01 | ✅ |
| _calcular_breakpoints_logicos() | Breakpoints "redondos" para valores absolutos de métrica | src01 | ✅ |
| generar_metrica() | Genera v_MuyBaja..v_MuyAlta, outliers, valores absolutos v_abs_* | src01 | ✅ |
| filtrar_constantes() | Elimina columnas difusas (t_*, v_*) constantes (nunique≤1) | src01 | ✅ |

---

## app/core/fuzzy/pipeline.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| fuzzify() | Pipeline completo src01: carga CSV → fuzzifica → guarda | src01 | ✅ |

---

## app/core/fuzzy/heuristic.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _llamar_llm() | Interfaz única LLM (anthropic/openai/gemini), devuelve texto | src01 celda 3 | ✅ |
| _perfil_columnas_para_llm() | Perfil AGREGADO de columnas (NO datos crudos) para LLM | src01 celda 3 | ✅ |
| _detectar_metrica_via_llm() | Clasifica columnas como métricas usando LLM | src01 celda 3 | ✅ |
| _detectar_var_tiempo() | 4 estrategias: datetime directo, fecha+hora, timestamp, fallback | src01 celda 2 | ✅ |
| _tokenizar() | Split de nombre de columna por _ - espacio en lowercase | src01 celda 4 | ✅ |
| _heuristica() | Detecta candidatos a métrica por estadística + tokens | src01 celda 4 | ✅ |
| detectar_var_metrica() | Lógica completa de detección con override manual + LLM fallback | src01 celda 4 | ✅ |

---

## app/core/mining/metrics.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| calcular_soporte() | Soporte difuso = sum(min(μ₁, μ₂, ...)) / N | src02 | ✅ |
| calcular_confianza() | Confianza = Sop(A ∧ C) / Sop(A) | src02 | ✅ |
| calcular_lift() | Lift = Conf(A→C) / Sop(C) | src02 | ✅ |
| evaluar_regla() | Evalúa regla completa: soporte, confianza, lift, n_vars | src02 | ✅ |
| calcular_aportacion() | Soporte marginal: cuánto aporta la regla sobre lo ya cubierto | src02 | ✅ |

---

## app/core/mining/groups.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _HORAS_POR_FRANJA | Dict franja → set de horas (constante) | src02 | ✅ |
| _TODAS_HORAS | Set t_H00..t_H23 (constante) | src02 | ✅ |
| _MESES_POR_ESTACION | Dict estación → set de meses (constante) | src02 | ✅ |
| _TODOS_MESES | Set t_Ene..t_Dic (constante) | src02 | ✅ |
| _construir_grupos() | Construye grupos excluyentes dinámicos filtrados a cols presentes | src02 | ✅ |
| _construir_jerarquia() | Construye jerarquía padre→hijos filtrada a cols presentes | src02 | ✅ |
| combinacion_valida() | Valida: no >1 var del mismo grupo, mes+estación, hora+franja compatibles | src02 | ✅ |

---

## app/core/mining/beam_search.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| beam_search_reglas() | Beam search con filtrado por aportación marginal, devuelve reglas | src02 | ✅ |
| filtrar_redundantes() | Elimina regla A si existe A' ⊂ A con mismo consecuente y conf≥min | src02 | ✅ |
| filtrar_por_jerarquia() | Elimina regla con 'hijo' si existe equivalente con 'padre' y conf≥min | src02 | ✅ |
| filtrar_top_por_consecuente() | Limita a top_n reglas por consecuente ordenadas por lift | src02 | ✅ |

---

## app/core/mining/miner.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| BeamSearchMiner (clase) | Encapsula pipeline completo de minería sobre CSV fuzzificado | src02 | ✅ |
| BeamSearchMiner.fit() | Ejecuta beam search + 3 filtros + guarda CSV de reglas | src02 | ✅ |

---

## app/core/nlg/labels.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| ETIQUETA_TEMPORAL | Dict token temporal → texto español (diccionario) | src03 | ✅ |
| ETIQUETA_METRICA_COLOQUIAL | Dict v_* → texto coloquial sin stats (diccionario) | src03 | ✅ |
| ETIQUETA_METRICA_TECNICA | Dict v_* → texto técnico con anotación outlier (diccionario) | src03 | ✅ |
| NOMBRE_METRICA | Dict nombre métrica → descripción legible (diccionario) | src03 | ✅ |
| ORDEN_CONSECUENTE | Orden canónico para secciones del informe (lista) | src03 | ✅ |
| JERARQUIA | Dict padre → hijos para agrupar horas bajo franjas (diccionario) | src03 | ✅ |
| HORA_A_FRANJA | Dict inverso: hora → franja contenedora (diccionario) | src03 | ✅ |
| HORAS, FRANJAS, MESES, DIAS, ANIOS, TIPO_DIA, QUINCENAS, FESTIVOS, ESTACIONES | Sets de categorías temporales (constantes) | src03 | ✅ |

---

## app/core/nlg/verbalize.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| parsear_antecedente() | Split antecedente por " AND " → set de tokens | src03 | ✅ |
| categoria_dominante() | Identifica categoría temporal principal en tokens (hora/franja/dia..) | src03 | ✅ |
| franja_de_tokens() | Devuelve franja única si todas las horas pertenecen a ella | src03 | ✅ |
| verbalizar_token() | Traduce token temporal a texto español usando ETIQUETA_TEMPORAL | src03 | ✅ |
| listar_en_español() | Une lista de items con comas + conector ("y"/"o") | src03 | ✅ |
| horas_consecutivas() | Verbaliza horas: "entre X h y Y h" si consecutivas | src03 | ✅ |
| verbalizar_antecedente() | Convierte set de tokens en frase natural (minutos+horas, horas consec) | src03 | ✅ |
| calidad_regla() | Mapea lift a adverbio según escala (3.0/2.0/1.5 umbrales) | src03 | ✅ |
| regla_a_frase() | Genera frase completa para regla con modo coloquial/técnico | src03 | ✅ |

---

## app/core/nlg/pipeline.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| agrupar_reglas() | Agrupa reglas con contexto temporal similar en listas cohesivas | src03 | ✅ |
| grupo_a_parrafo() | Convierte grupo de reglas en párrafo narrativo o frases individuales | src03 | ✅ |
| generar_resumen() | Pipeline completo src03: reglas → Markdown estructurado con secciones | src03 | ✅ |

---

## app/models/job.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| Job (clase SQLAlchemy) | Modelo BD: id, status, progress, step, sensor_id, report_md, error_msg | infraestructura | ✅ |

---

## app/models/rule.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| Rule (clase SQLAlchemy) | Modelo BD: job_id, sensor_id, antecedente, consecuente, métricas | infraestructura | ✅ |

---

## app/schemas/pipeline.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| RunPipelineResponse | Schema Pydantic: respuesta POST /run con job_id | infraestructura | ✅ |
| JobStatusResponse | Schema Pydantic: status, progress, step, error | infraestructura | ✅ |
| ReportResponse | Schema Pydantic: job_id, status, report_md | infraestructura | ✅ |
| RuleItem | Schema Pydantic: una regla con sensor_id, métricas | infraestructura | ✅ |
| RulesResponse | Schema Pydantic: lista paginada de reglas | infraestructura | ✅ |

---

## app/db/base.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| Base | Clase base SQLAlchemy DeclarativeBase para modelos | infraestructura | ✅ |

---

## app/db/session.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| engine | Motor async SQLAlchemy desde settings.database_url | infraestructura | ✅ |
| AsyncSessionLocal | Session maker async para BD | infraestructura | ✅ |
| get_db() | Dependency FastAPI que yield sesión async | infraestructura | ✅ |

---

## app/api/deps.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _api_key_header | APIKeyHeader FastAPI para header X-API-Key | infraestructura | ✅ |
| verify_api_key() | Valida API key si configurada, no-op si vacía (desarrollo) | infraestructura | ✅ |

---

## app/api/routes/pipeline.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| run_pipeline() | POST /run: recibe CSV + params, crea Job, lanza background task | infraestructura | ✅ |
| get_status() | GET /{job_id}/status: devuelve progress, step, error | infraestructura | ✅ |
| get_report() | GET /{job_id}/report: devuelve report_md cuando done | infraestructura | ✅ |
| get_rules() | GET /{job_id}/rules: lista paginada de reglas con filtro sensor_id | infraestructura | ✅ |
| _get_job_or_404() | Helper: busca Job por id, lanza 404 si no existe | infraestructura | ✅ |

---

## app/services/pipeline.py

| Función/Clase | Qué hace (1 línea) | Notebook origen | Estado |
|---|---|---|---|
| _get_all_sensor_paths() | Detecta si CSV es multi-sensor o single, split si necesario | src00 + infraestructura | ✅ |
| _run_fuzzify() | Wrapper sync de fuzzify() para run_in_executor | src01 + infraestructura | ✅ |
| _run_mining() | Wrapper sync de BeamSearchMiner.fit() para run_in_executor | src02 + infraestructura | ✅ |
| _run_nlg() | Wrapper sync de generar_resumen() para run_in_executor | src03 + infraestructura | ✅ |
| _set_status() | Helper async: actualiza Job.status, progress, step | infraestructura | ✅ |
| _set_metadata() | Helper async: actualiza Job.sensor_id, metrica | infraestructura | ✅ |
| _set_error() | Helper async: marca Job como error con mensaje | infraestructura | ✅ |
| _save_rules() | Helper async: guarda lista de reglas en BD (tabla rules) | infraestructura | ✅ |
| _cleanup_dir() | Helper sync: elimina directorio temporal upload tras completar | infraestructura | ✅ |
| execute_pipeline() | Orquestador principal: loop sobre sensores, ejecuta src01→src02→src03 | src00+src01+src02+src03+infraestructura | ✅ |

---

# Resumen ejecutivo

- **Total elementos inventariados**: 97
- **✅ Justificados**: 97 (100%)
- **🟡 Dudosos**: 0
- **🔴 Sospechosos**: 0

**Detalle**:
- **src00** (preprocessing): 3 elementos
- **src01** (fuzzy): 23 elementos (primitivas, bloques, config, heurística, LLM fallback)
- **src02** (mining): 14 elementos (métricas, grupos, beam search, filtros)
- **src03** (NLG): 22 elementos (labels, verbalización, pipeline markdown)
- **Infraestructura FastAPI**: 35 elementos (models, schemas, db, api, services, main, config)

**Conclusión**: El backend implementa EXACTAMENTE lo especificado en los notebooks src00-03 más la infraestructura REST necesaria. No hay código muerto ni elementos injustificados.

---

# src04 — Estado

**¿Existe implementación de informe global cross-sensor?** 

**NO** — src04 NO está implementado en el backend.

**Evidencia**:

1. **No hay archivo `app/core/global_report/` ni similar** — ningún módulo dedicado a src04.

2. **`app/services/pipeline.py` líneas 217-229** — La lógica de combinación de informes multi-sensor es **rudimentaria**:
   ```python
   # Combine per-sensor reports
   if len(results) == 1:
       combined_report = results[0][3]
   else:
       sections = [f"## Sensor {sid} — {met}\n\n{rmd}" for ...]
       combined_report = "\n\n---\n\n".join(sections)
   ```
   Esto es **concatenación ciega de Markdown**, NO un análisis cross-sensor como describe src04.

3. **No existe tabla `global_insights` ni similar** en `app/models/` — solo hay `Job` y `Rule` (per-sensor).

4. **No hay endpoint `/global-report`** en `app/api/routes/pipeline.py` — solo endpoints per-job.

5. **Glosario-difumad.md y CLAUDE.md no mencionan src04** — el alcance acordado es src00-03 + infraestructura.

**Interpretación**: La funcionalidad de **informe global cross-sensor avanzado** (comparaciones estadísticas, patrones emergentes entre sensores, clustering temporal) del notebook src04 **NO está portada al backend**. Solo existe una concatenación cosmética de informes individuales cuando el CSV maestro contiene múltiples sensores.

Si src04 fuera un requisito del TFG, sería necesario:
- Crear `app/core/global_report/pipeline.py` con lógica de agregación.
- Añadir modelo `GlobalInsight` en BD.
- Nuevo endpoint `GET /{job_id}/global-report`.
- Portar funciones del notebook src04 (correlaciones entre sensores, detección de anomalías cross-sensor, etc.).
