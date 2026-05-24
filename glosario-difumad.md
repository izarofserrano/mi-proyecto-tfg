# Glosario DifuMad — Vocabulario fijo del proyecto

Este archivo recoge los nombres canónicos de los componentes, métricas y conceptos del proyecto DifuMad. Aplicar siempre estos términos para mantener coherencia entre secciones de la memoria, entre la memoria y el artículo, y entre la memoria y el código.

## Nombre del sistema

- **DifuMad** — nombre propio del sistema. Sin acentos, sin espacios. En cursiva la primera vez en cada sección («*DifuMad*»), después sin cursiva.

## Componentes del pipeline

| Componente | Nombre canónico | Función |
|------------|-----------------|---------|
| `src01` | Etapa de fuzzificación | Convierte series temporales numéricas en variables lingüísticas mediante particiones de Ruspini con funciones trapezoidales adaptativas. |
| `src02` | Etapa de minería de reglas | Extrae reglas de asociación difusas mediante *beam search* con poda submodular. |
| `src03` | Etapa de generación de lenguaje natural (NLG) | Verbaliza las reglas seleccionadas en un resumen estructurado en español con dos niveles de lectura. |
| `src04` | Módulo de informe global | Genera un informe comparativo entre múltiples sensores. |

Términos a evitar para evitar ambigüedad:

- ❌ «notebook 1», «notebook 2»… → ✅ «etapa de fuzzificación», «`src01`».
- ❌ «el módulo NLP» → ✅ «la etapa NLG», «`src03`».
- ❌ «el algoritmo» (genérico) → ✅ nombrar el algoritmo concreto: *beam search*, t-norma del mínimo, etc.

## Conceptos del marco difuso

| Concepto | Cómo se nombra | Definición breve |
|----------|----------------|------------------|
| Conjunto difuso | conjunto difuso (no «fuzzy set» en cuerpo) | Generalización de conjunto clásico con función de pertenencia μ: U → [0, 1]. |
| Función de pertenencia | función de pertenencia (μ) | Mapea un valor a su grado de pertenencia a una etiqueta. |
| Etiqueta lingüística | etiqueta lingüística | Nombre humano asignado a un conjunto difuso («alto», «moderado», «bajo»). |
| Variable lingüística | variable lingüística | Conjunto de etiquetas que describen una magnitud. |
| Partición de Ruspini | partición difusa de Ruspini | Conjunto de funciones de pertenencia tal que ∑μ_i(x) = 1 para todo x. |
| t-norma | t-norma | Generalización de la conjunción lógica al intervalo [0, 1]. |
| t-norma del mínimo | t-norma del mínimo (Zadeh, Mamdani) | t(a, b) = min(a, b). Es la usada por DifuMad. |
| Fuzzificación | fuzzificación | Proceso de convertir un valor numérico en grados de pertenencia a etiquetas. |
| Inferencia difusa | inferencia difusa | Aplicación de reglas difusas a una entrada fuzzificada. |
| Defuzzificación | defuzzificación | Conversión de salida difusa a un valor numérico. (DifuMad **no** defuzzifica: la salida es texto, no número.) |

## Métricas de minería de reglas

| Métrica | Cómo se nombra | Fórmula simplificada |
|---------|----------------|----------------------|
| Soporte | soporte (`sop`) | sop(A → C) = (1/N) · ∑_i T(μ_A(x_i), μ_C(x_i)) |
| Confianza | confianza (`conf`) | conf(A → C) = sop(A ∩ C) / sop(A) |
| Lift | *lift* (en cursiva la primera vez) | lift(A → C) = conf(A → C) / sop(C) |

**Importante (versión final, verificado en código vivo mayo 2026)**: el *lift* cumple **dos funciones simultáneas y no contradictorias**:

1. **Umbral de sorpresa seleccionable por el usuario**: el analista elige el nivel de exigencia mediante un selector con etiquetas legibles («Incluir todas», «Algo sorprendentes», «Sorprendentes», «Muy sorprendentes»), que se traducen a umbrales de *lift* **absolutos** (1,0 / 1,5 / 2,0 / 3,0). El *lift* descarta reglas por debajo del umbral elegido.
2. **Criterio de ordenación de la salida**: las reglas que superan el umbral se presentan ordenadas por *lift* descendente (las más fuertes primero).

Esto sustituye a la formulación anterior («lift solo ordena, no filtra»), que correspondía a una versión previa con filtro por percentil. La distinción clave para la defensa: **el umbral es absoluto, no relativo a la distribución del conjunto de datos**. Un mismo nivel («Sorprendentes» = *lift* ≥ 2,0) significa lo mismo en cualquier sensor, métrica o dataset. Esto garantiza comparabilidad entre ejecuciones.

El *soporte*, en cambio, actúa **únicamente como umbral de masa mínima** en dos puntos del *beam search* (admisión de un candidato y aceptación de su aportación marginal a la cobertura), **nunca como criterio de ordenación ni de puntuación**. Formulación validada para la memoria: «el soporte interviene como filtro de masa mínima en la admisión de candidatos y en la aportación marginal al conjunto de reglas; en ningún caso como criterio de ordenación o puntuación».

## Parámetros del sistema (valores actuales — verificados en código vivo, mayo 2026)

Todos los parámetros son **decisiones explícitas del usuario** (parámetros `@param` visibles en `src02`), no valores calibrados automáticamente sobre los datos. Esta es una decisión de diseño central, justificada más abajo.

| Parámetro | Valor por defecto | Notas |
|-----------|-------|-------|
| `MIN_SOPORTE` | 0,005 | Una regla debe cubrir ≥0,5 % de las observaciones para no sustentarse en casos anecdóticos. ≈88 ocurrencias anuales con muestreo de 15 min. |
| `MIN_CONFIANZA` | 0,50 | Mínimo conceptual: una regla que se cumple <50 % de las veces no es propiamente una regla. |
| `_LIFT_MINIMO` | 1,0 / 1,5 / 2,0 / 3,0 | Seleccionable por el usuario vía etiquetas («Incluir todas» … «Muy sorprendentes»). Umbral **absoluto** de sorpresa. Defaults anclados en literatura (Brin et al. 1997; Tan et al. 2005): correlación débil/moderada/fuerte/excepcional. |
| `MAX_PROF` | 3 | Profundidad máxima del antecedente en *beam search*. |
| `K_BEAM` | 10 | Anchura del haz. Poda por **confianza** (no por lift ni soporte). |
| `TOP_POR_CONSECUENTE` | 10 | Top reglas conservadas por consecuente en el informe NL. |

Estos valores deben aparecer en la sección de Desarrollo con su justificación heurística y referencia bibliográfica (Brin et al. 1997 para el criterio de *lift*).

## Escala adverbial de verbalización (`construir_calidad`, src03)

`src03` traduce el *lift* de cada regla en un adverbio de fuerza estadística mediante umbrales **fijos y coherentes con la escala de `src02`**:

| Rango de *lift* | Adverbio generado |
|-----------------|-------------------|
| < 1,5 | «con cierta tendencia» |
| 1,5 – 2,0 | «con cierta consistencia» |
| 2,0 – 3,0 | «de forma notable» |
| ≥ 3,0 | «de forma muy marcada» |

Estos umbrales son los mismos que los niveles del selector de sorpresa de `src02`, lo que garantiza que el filtrado y la verbalización «hablan el mismo idioma»: si el usuario filtra por «Sorprendentes» (*lift* ≥ 2,0), todas las reglas que pasan se describen como «de forma notable» o «de forma muy marcada», nunca con adverbios de menor fuerza. Coherencia verificada en código vivo.

## Componente `src05` — descartado del pipeline (decisión de diseño documentable)

`src05` (calibración automática de umbrales de calidad por cuantiles del conjunto de reglas) **no forma parte del pipeline ejecutable**. Se ensayó y se descartó. Argumento de defensa validado, a incluir en la sección de Metodología:

> Se ensayó inicialmente una calibración automática de los umbrales a partir de la distribución de *lift* del propio conjunto de reglas. Se descartó por una limitación conceptual: al depender de la composición del conjunto de datos, el significado de los adverbios dejaba de ser estable y comparable entre ejecuciones. La verificación empírica sobre un conjunto de datos de prueba ajeno al dominio lo confirmó: la calibración por cuantiles clasificaba como «mera tendencia» reglas con *lift* superior a 3 —estadísticamente fuertes según la literatura—, degradando la calidad descriptiva. Se adoptó en su lugar la parametrización explícita por el usuario, con valores por defecto justificados en la literatura. Esta decisión responde al principio de que el destinatario de los resúmenes es un analista que debe poder razonar los umbrales en magnitudes interpretables (un valor de *lift*, un porcentaje de soporte), no en propiedades estadísticas internas del conjunto de datos.

Este pasaje es, en sí mismo, una de las secciones de Metodología más sólidas de la memoria: documenta una decisión de diseño razonada con evidencia empírica.

## Datos del caso de estudio

- **Fuente**: portal de datos abiertos del Ayuntamiento de Madrid.
- **Periodo**: 2024–2025 (bienio).
- **Granularidad**: 15 minutos.
- **Sensores**: 6 (3600, 3730, 4301, 6791, 6822, 6823).
- **Métricas**: intensidad (vehículos/hora) y ocupación (% de tiempo ocupado).

Nombres canónicos de sensores:

| ID | Ubicación | Notas |
|----|-----------|-------|
| 3600 | A-3 (autovía radial), sentido X | Ocupación excluida por datos no fiables (rango cercano a cero). |
| 6791 | A-3 (autovía radial), sentido Y | Reglas fuertemente asociadas al año 2024 en franja tarde (posible cambio infraestructural externo). |
| 4301 | Gran Vía | *Lift* estructuralmente bajo por uniformidad del tráfico tras peatonalización. |
| 3730 | Gran Vía | Comportamiento anómalo (hipótesis: carril bus o vía de acceso restringido). Pendiente de verificar físicamente. |
| 6822 | Plaza Elíptica | Solo ocupación generada actualmente. Falta intensidad. |
| 6823 | Plaza Elíptica | Sensor de referencia del análisis. |

## Generalizabilidad del pipeline (evidencia validada)

El esqueleto del pipeline es **agnóstico al dominio**. Validado empíricamente: el sistema se ejecutó de extremo a extremo sobre un conjunto de datos climáticos diarios (temperatura media, granularidad diaria) ajeno al dominio del tráfico. El pipeline detectó automáticamente la granularidad diaria, desactivó los bloques de hora/franja/minuto, identificó la métrica mediante el mecanismo de respaldo, y generó reglas físicamente correctas (p. ej. enero/invierno → temperatura muy baja; junio → muy alta) y un resumen coherente.

Formulación para la memoria: «La estructura temporal del pipeline es independiente del dominio; su adaptación a series no relacionadas con el tráfico requiere únicamente ajustar los puntos de corte de fuzzificación y los diccionarios de etiquetas semánticas, no la arquitectura». Madrid es el caso de validación, no el límite del sistema. Esto sustenta el posicionamiento como *infraestructura modular* y no como *generador de informes de tráfico*.

## Cobertura marginal (anti-redundancia en beam search)

El *beam search* incorpora un criterio de **aportación marginal**: una regla solo se acepta si cubre casos nuevos que las reglas ya aceptadas no cubrían, por encima del umbral `MIN_SOPORTE`. Esto evita reglas redundantes (p. ej. «en enero, temperatura baja» y «en invierno, temperatura baja» cubren casi los mismos casos). Formulación para la memoria: «el sistema aplica un criterio de cobertura marginal para evitar reglas redundantes: solo acepta una regla nueva si aporta información sobre al menos el mismo porcentaje de casos que se exige como soporte mínimo». Consecuencia documentable: el conjunto de reglas depende del orden de exploración de consecuentes; es una decisión de diseño, no un defecto.

## Decisiones de paradigma del sistema

Estas tres frases deben aparecer **literales** o muy cercanas en cualquier sección que justifique el enfoque del sistema:

> «El sistema mantiene un paradigma modular basado en plantillas y reglas explícitas, frente a un enfoque end-to-end con LLM. Esta elección responde a tres requisitos no funcionales fundamentales: **fidelidad verificable** (cada afirmación textual es trazable hasta una regla concreta), **reproducibilidad determinista** (la salida es estable para una misma entrada) e **independencia de infraestructura** (el sistema no requiere acceso a recursos de cómputo intensivos ni a APIs externas).»

## Posicionamiento de la contribución

Frase canónica del posicionamiento (a usar en Resumen, Introducción, Conclusiones, abstract del artículo):

> «Infraestructura modular para la generación automática de resúmenes en lenguaje natural sobre series temporales mediante lógica difusa y minería de reglas de asociación, validada en datos abiertos de tráfico urbano de Madrid (2024–2025).»

**No usar** las formulaciones siguientes (rechazadas por el Consejo LLM por sobrevender o ser ambiguas):

- ❌ «Sistema que genera informes de tráfico interpretativos».
- ❌ «Solución basada en IA para análisis del tráfico urbano».
- ❌ «Aplicación de lógica difusa al tráfico de Madrid».

## Términos a no confundir

| Confusión común | Aclaración |
|-----------------|------------|
| Resumen / informe / reporte | Usar «resumen» para la salida de DifuMad. «Informe» se reserva al documento global multi-sensor. |
| Regla / patrón | «Regla» tiene forma A → C. «Patrón» es el concepto general. Una regla es un tipo de patrón. |
| Lift / soporte / confianza | Tres métricas distintas. No mezclar. |
| *Lift* filtro / *lift* etiqueta | El *lift* hace dos trabajos: en `src02` filtra qué reglas existen (umbral de sorpresa); en `src03` etiqueta cómo se describen (adverbio). Misma magnitud, mismos umbrales, funciones distintas. No describir como contradicción: es coherencia deliberada. |
| Percentil / umbral absoluto | La versión final usa umbral **absoluto** de *lift*, no percentil. El percentil (relativo a la distribución del dataset) fue descartado por no ser comparable entre ejecuciones. No mencionar percentiles como mecanismo vigente. |
| Fuzzificación / discretización | Fuzzificación produce grados continuos en [0,1]. Discretización produce valores categóricos crisp. |
| NLG / NLP | NLG (generación) es subcampo de NLP. DifuMad hace NLG, no NLP en sentido amplio. |

## Lenguaje sobre limitaciones (formulaciones aceptadas)

- ✅ «El sistema asume X, lo que constituye una decisión de diseño justificada por…»
- ✅ «La validación temporal cruzada queda fuera del alcance y se plantea como línea futura.»
- ✅ «El alcance del PFG no contempla Y; este aspecto se trataría en…»
- ❌ «No hemos podido…», «no nos dio tiempo a…», «desafortunadamente…»


## Validaciones semánticas en el beam search (hallazgos validados)

El sistema aplica tres validaciones semánticas sobre los antecedentes 
candidatos antes de evaluar una regla:

1. **Grupos excluyentes**: una variable de cada grupo categórico mutuamente 
   excluyente (mes, día de la semana, franja, año, estación).
2. **Compatibilidad mes-estación**: los meses deben pertenecer a la 
   estación declarada.
3. **Compatibilidad hora-franja**: las horas deben pertenecer a la franja 
   declarada (validación añadida tras hallazgo empírico, ver más abajo).

**Hallazgo validado empíricamente (mayo 2026):** sin la tercera validación, 
el sistema generaba reglas semánticamente imposibles con *lift* elevado. 
Caso concreto en el sensor 6823 (intensidad): `t_H07 AND t_Laborable AND 
t_Madrugada → v_OutlierAlto` con *lift* = 10,78, la regla de mayor *lift* 
del conjunto. La hora 7 pertenece a la franja Mañana, no a Madrugada; la 
combinación es contradictoria en el tiempo real, pero produce una 
correlación espuria por coincidencia estadística en el espacio difuso. 
Esto demuestra que un *lift* alto no garantiza significado semántico: las 
métricas estadísticas requieren validaciones de dominio. La incorporación 
de la validación hora-franja eliminó esta regla y otras similares sin 
afectar a las reglas válidas, mejorando la fidelidad del informe sin 
comprometer su densidad informativa.