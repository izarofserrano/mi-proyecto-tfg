"""
src04 - Informe Global Comparativo
Genera análisis cross-sensor a partir de CSVs de reglas generados por src02.
Portado del notebook src04_informe_global (4).ipynb
"""
import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


# Etiquetas de métricas — mismo diccionario que src03
ETIQUETA_METRICA = {
    "v_MuyBaja":     "muy baja",
    "v_Baja":        "baja",
    "v_Media":       "media",
    "v_Alta":        "alta",
    "v_MuyAlta":     "muy alta",
    "v_OutlierBajo": "excepcionalmente baja (outlier inferior)",
    "v_OutlierAlto": "excepcionalmente alta (outlier superior)",
}

# Emojis de nivel — mismo criterio que src03 (escala de color consistente)
NIVEL_EMOJI = {
    "v_OutlierAlto": "🔴",
    "v_MuyAlta":     "🟠",
    "v_Alta":        "🟡",
    "v_Media":       "🟢",
    "v_Baja":        "🔵",
    "v_MuyBaja":     "🟣",
    "v_OutlierBajo": "⚪",
}

# Peso semántico de cada nivel (mayor = más relevante para el lector)
# Mismo criterio que _parrafo_coloquial de src03
NIVEL_PESO = {
    "v_OutlierAlto": 7, "v_MuyAlta": 6, "v_Alta": 5,
    "v_Media": 4,
    "v_Baja": 3, "v_MuyBaja": 2, "v_OutlierBajo": 1,
}

# Franjas horarias — idéntico a HORAS_FRANJA_MAP de src03
HORAS_FRANJA_MAP = {
    "t_Madrugada": list(range(0, 7)),
    "t_Mañana":    list(range(7, 14)),
    "t_Tarde":     list(range(14, 21)),
    "t_Noche":     list(range(21, 24)),
}
NOMBRE_FRANJA = {
    "t_Madrugada": "Madrugada (0–6 h)",
    "t_Mañana":    "Mañana (7–13 h)",
    "t_Tarde":     "Tarde (14–20 h)",
    "t_Noche":     "Noche (21–23 h)",
}


def cargar_reglas_todos(sensores, metricas, dir_datos):
    """
    Devuelve un diccionario {(sensor, metrica): df_reglas}.
    Los CSVs ausentes se registran en `faltantes`.
    """
    reglas = {}
    faltantes = []

    for sensor in sensores:
        for metrica in metricas:
          if not (sensor == "3600" and metrica == "ocupacion"):
            ruta = f"{dir_datos}/{sensor}_{metrica}_reglas.csv"
            if not os.path.exists(ruta):
                faltantes.append(ruta)
                continue
            df = pd.read_csv(ruta)
            if df.empty:
                faltantes.append(f"{ruta} (vacío)")
                continue
            reglas[(sensor, metrica)] = df

    return reglas, faltantes


def hora_mas_frecuente(df):
    """Hora del día (00–23) con más reglas que la mencionan en el antecedente."""
    cuentas = Counter()
    for ant in df["antecedente"]:
        for token in ant.split(" AND "):
            if token.startswith("t_H") and len(token) == 5:
                try:
                    cuentas[int(token[3:])] += 1
                except ValueError:
                    continue
    if not cuentas:
        return None
    return cuentas.most_common(1)[0][0]


def dia_mas_frecuente(df):
    """Día de la semana con más reglas que lo mencionan."""
    DIAS = {"t_Lun":"Lunes","t_Mar":"Martes","t_Mie":"Miércoles","t_Jue":"Jueves",
            "t_Vie":"Viernes","t_Sab":"Sábado","t_Dom":"Domingo"}
    cuentas = Counter()
    for ant in df["antecedente"]:
        for tok in ant.split(" AND "):
            if tok in DIAS:
                cuentas[DIAS[tok]] += 1
    if not cuentas:
        return None
    return cuentas.most_common(1)[0][0]


def _mapa_horario_sensor(df):
    """
    Para un sensor, construye {hora_int: consecuente_dominante}.
    Mismo criterio que _mapa_horario de src03: hora directa primero,
    luego herencia de franja si la hora no tiene regla propia.
    """
    mapa = {}
    for h in range(24):
        tok = f"t_H{h:02d}"
        sub = df[df["antecedente"].str.contains(tok, regex=False)]
        if not sub.empty:
            mapa[h] = sub.loc[sub["lift"].idxmax(), "consecuente"]
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        sub = df[df["antecedente"].str.contains(franja_tok, regex=False)]
        if not sub.empty:
            cons_franja = sub.loc[sub["lift"].idxmax(), "consecuente"]
            for h in horas:
                if h not in mapa:
                    mapa[h] = cons_franja
    return mapa


def _nivel_franja_dominante(df_reglas, horas):
    """
    Nivel más relevante de una franja por votación ponderada (lift × confianza).
    Mismo criterio que _nivel_franja() en src03: no el nivel semánticamente
    más alto que aparece, sino el respaldado por mayor evidencia acumulada.

    Antes usaba max(NIVEL_PESO) sobre un mapa hora→nivel, lo que ignoraba
    cuántas reglas respaldan cada nivel. Un único pico excepcional en 1h
    podía dominar sobre 6h de tráfico moderado bien respaldado.
    """
    patron = "|".join(f"t_H{h:02d}" for h in horas)
    sub = df_reglas[df_reglas["antecedente"].str.contains(patron, regex=True)]
    if sub.empty:
        return None

    # Suma lift × confianza por nivel (igual que src03)
    votos: dict[str, float] = {}
    for _, row in sub.iterrows():
        n = row["consecuente"]
        votos[n] = votos.get(n, 0.0) + row["lift"] * row["confianza"]

    return max(votos, key=votos.get)


def _perfil_dia_sensor(df):
    """
    Genera una cadena compacta del perfil diario de un sensor.
    Ejemplo: "Madrugada 🔵 | Mañana 🟡 | Tarde 🟠 | Noche 🟢"
    """
    partes = []
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        nombre_corto = NOMBRE_FRANJA[franja_tok].split(" (")[0]
        nivel = _nivel_franja_dominante(df, horas)   # ← ahora recibe df, no mapa
        if nivel is None:
            partes.append(f"{nombre_corto} —")
        else:
            emoji = NIVEL_EMOJI.get(nivel, "")
            partes.append(f"{nombre_corto} {emoji}")
    return " | ".join(partes)


def construir_tabla_cross_sensor(reglas_por_sensor, HAY_HORAS, HAY_FRANJAS, HAY_DIAS):
    """
    Construye la tabla comparativa cross-sensor/dataset.
    Adapta las columnas según los bloques temporales disponibles:
    - Si hay horas/franjas → columna "Perfil del día"
    - Si no → columna "Patrón calendario dominante"
    - Si no hay horas → omite "Hora más mencionada en reglas"
    """
    filas = []
    for (sensor, metrica), df in reglas_por_sensor.items():

        # ── Consecuente dominante ─────────────────────────────────────────
        consec_dom = (df["consecuente"].value_counts().idxmax()
                      if not df["consecuente"].mode().empty else "—")
        emoji_dom = NIVEL_EMOJI.get(consec_dom, "")
        etiq_dom  = ETIQUETA_METRICA.get(consec_dom, consec_dom)

        # ── Columnas base (siempre presentes) ────────────────────────────
        fila = {
            "Sensor":          sensor,
            "Métrica":         metrica,
            "Reglas":          len(df),
            "Conf. media (%)": round(df["confianza"].mean() * 100, 1),
            "Lift medio":      round(df["lift"].mean(), 2),
            "Lift máx":        round(df["lift"].max(), 2),
            "Lift mín":        round(df["lift"].min(), 2),
            "Soporte medio":   round(df["soporte"].mean(), 4),
            "Nivel dominante": f"{emoji_dom} {etiq_dom}",
            "Outlier alto":    "✅" if "v_OutlierAlto" in df["consecuente"].values else "—",
            "Outlier bajo":    "✅" if "v_OutlierBajo" in df["consecuente"].values else "—",
        }

        # ── Columnas temporales: dependen de los bloques disponibles ─────
        if HAY_HORAS or HAY_FRANJAS:
            # Dataset con resolución intra-día → perfil por franjas
            fila["Perfil del día"]               = _perfil_dia_sensor(df)
            fila["Hora más mencionada en reglas"] = hora_mas_frecuente(df)
        else:
            # Dataset diario o de menor resolución → patrón estacional/calendario
            _tokens_cal = [
                t for ant in df["antecedente"]
                for t in ant.split(" AND ")
                if t.startswith("t_") and not re.match(r'^t_H\d{2}$', t)
            ]
            _mas_frecuente = (Counter(_tokens_cal).most_common(1)[0][0]
                              .replace("t_", "")
                              if _tokens_cal else "—")
            fila["Patrón calendario dominante"] = _mas_frecuente

        # ── Día de la semana (solo si hay días en las reglas) ────────────
        if HAY_DIAS:
            _dia = dia_mas_frecuente(df)
            if _dia:
                fila["Día más mencionado"] = _dia

        filas.append(fila)

    return pd.DataFrame(filas)


def patrones_compartidos(reglas_por_sensor, umbral=0.5):
    """
    Devuelve lista de patrones (antecedente, consecuente) que aparecen
    en al menos `umbral` proporción de los sensores.
    """
    apariciones = defaultdict(set)  # (antecedente, consecuente) → set de sensores

    for (sensor, _metrica), df in reglas_por_sensor.items():
        for _, row in df.iterrows():
            clave = (row["antecedente"], row["consecuente"])
            apariciones[clave].add(sensor)

    n_sensores = len(set(s for s, _ in reglas_por_sensor.keys()))
    umbral_n = max(2, int(n_sensores * umbral))

    comunes = [
        {"antecedente": ant, "consecuente": cons,
         "n_sensores": len(sens), "sensores": sorted(sens)}
        for (ant, cons), sens in apariciones.items()
        if len(sens) >= umbral_n
    ]
    comunes.sort(key=lambda x: -x["n_sensores"])
    return comunes


def detectar_atipicos(tabla_cross):
    """
    Marca como atípico un sensor que esté a más de 1.5·MAD de la mediana
    del grupo en cualquier métrica numérica clave.
    """
    metricas_num = ["Reglas", "Conf. media (%)", "Lift medio", "Lift máx"]
    atipicos = []

    for met in metricas_num:
        if met not in tabla_cross.columns:
            continue
        valores = tabla_cross[met].astype(float)
        mediana = valores.median()
        mad = (valores - mediana).abs().median()
        if mad == 0:
            continue
        for _, row in tabla_cross.iterrows():
            v = float(row[met])
            desviacion = (v - mediana) / mad
            if abs(desviacion) >= 1.5:
                atipicos.append({
                    "sensor":         row["Sensor"],
                    "metrica_global": met,
                    "valor":          v,
                    "mediana_grupo":  round(mediana, 2),
                    "direccion":      "alto" if desviacion > 0 else "bajo",
                    "desviacion_mad": round(abs(desviacion), 1),
                })
    return atipicos


def comparar_perfiles_dia(tabla_cross):
    """
    Compara perfiles temporales entre sensores.
    Usa 'Perfil del día' si hay horas/franjas,
    o 'Patrón calendario dominante' si el dataset es diario.
    """

    # Detectar qué columna de perfil existe
    if "Perfil del día" in tabla_cross.columns:
        col_perfil  = "Perfil del día"
        etiq_perfil = "perfil diario"
        etiq_sensor = "sensor"
    elif "Patrón calendario dominante" in tabla_cross.columns:
        col_perfil  = "Patrón calendario dominante"
        etiq_perfil = "patrón calendario dominante"
        etiq_sensor = "fuente"
    else:
        return ["No hay información de perfil temporal disponible."]

    perfiles = dict(zip(tabla_cross["Sensor"], tabla_cross[col_perfil]))
    if len(perfiles) == 1:
        return []
    grupos   = defaultdict(list)
    for sensor, perfil in perfiles.items():
        grupos[perfil].append(sensor)

    frases = []
    for perfil, sensores in sorted(grupos.items(), key=lambda x: -len(x[1])):
        if len(sensores) > 1:
            frases.append(
                f"Las fuentes **{', '.join(sensores)}** comparten el mismo "
                f"{etiq_perfil}: *{perfil}*."
            )
        else:
            frases.append(
                f"La fuente **{sensores[0]}** tiene {etiq_perfil} propio: *{perfil}*."
            )
    return frases


def parrafo_coloquial_global(tabla_cross, NOMBRE_CONJUNTO):
    n = tabla_cross["Sensor"].nunique()
    total_reglas = tabla_cross["Reglas"].sum()
    # Singular/plural correcto
    _fuentes = "fuente de datos" if n == 1 else "fuentes de datos"

    if n == 1:
        sensor = tabla_cross["Sensor"].iloc[0]
        return (
            f"Se ha analizado **1 {_fuentes}** ({sensor}), "
            f"detectando **{total_reglas} patrones** de comportamiento "
            f"estadísticamente significativos."
        )

    sensor_pico  = tabla_cross.loc[tabla_cross["Lift máx"].idxmax(), "Sensor"]
    lift_pico    = tabla_cross["Lift máx"].max()
    sensor_plano = tabla_cross.loc[tabla_cross["Lift medio"].idxmin(), "Sensor"]
    lift_plano   = tabla_cross["Lift medio"].min()

    return (
        f"Se han analizado **{n} {_fuentes}** de {NOMBRE_CONJUNTO}, detectando un total "
        f"de **{total_reglas} patrones** de comportamiento estadísticamente significativos.\n\n"
        f"La fuente con los patrones más marcados es **{sensor_pico}** "
        f"(fuerza de asociación máxima: {lift_pico:.1f}), mientras que **{sensor_plano}** "
        f"presenta el comportamiento más uniforme (fuerza media: {lift_plano:.1f})."
    )

def parrafo_introductorio(tabla_cross, NOMBRE_CONJUNTO):
    n_sensores   = tabla_cross["Sensor"].nunique()
    n_reglas     = tabla_cross["Reglas"].sum()
    conf_media_g = tabla_cross["Conf. media (%)"].mean()
    _fuentes     = "fuente de datos" if n_sensores == 1 else "fuentes de datos"

    if n_sensores == 1:
        sensor = tabla_cross["Sensor"].iloc[0]
        return (
            f"El presente informe recoge los resultados del análisis difuso sobre "
            f"**1 {_fuentes}** ({sensor}), con un total de {n_reglas} reglas de asociación "
            f"significativas. La confianza media es del {conf_media_g:.1f} %."
        )

    sensor_max_r = tabla_cross.loc[tabla_cross["Reglas"].idxmax(), "Sensor"]
    sensor_min_r = tabla_cross.loc[tabla_cross["Reglas"].idxmin(), "Sensor"]
    lift_max_g   = tabla_cross["Lift máx"].max()
    sensor_lmax  = tabla_cross.loc[tabla_cross["Lift máx"].idxmax(), "Sensor"]

    return (
        f"El presente informe agrega los resultados del análisis difuso sobre "
        f"{n_sensores} {_fuentes} de {NOMBRE_CONJUNTO}, comprendiendo un total de "
        f"{n_reglas} reglas de asociación significativas. "
        f"La confianza media global es del {conf_media_g:.1f} %. "
        f"La fuente con mayor riqueza de patrones es **{sensor_max_r}** y la de menor, "
        f"**{sensor_min_r}**. "
        f"El patrón más fuerte se observa en **{sensor_lmax}** con lift máximo de {lift_max_g:.1f}."
    )


def parrafo_hallazgos_comunes(comunes, n_sensores_total):
    if n_sensores_total == 1:
        return (
            "> ℹ️ El análisis comparativo de patrones compartidos requiere "
            "al menos 2 fuentes de datos."
        )
    if not comunes:
        return (
            "No se han identificado patrones que se repitan en al menos la mitad "
            "de los sensores, lo que sugiere que el comportamiento del tráfico es "
            "marcadamente local en cada punto de medición."
        )
    top = comunes[:5]
    descripciones = []
    for c in top:
        # Verbalizar el antecedente de forma legible (quitar prefijos t_)
        tokens = c["antecedente"].split(" AND ")
        tok_legibles = []
        for t in tokens:
            if t.startswith("t_H") and len(t) == 5:
                tok_legibles.append(f"las {int(t[3:])}h")
            elif t == "t_Laborable": tok_legibles.append("días laborables")
            elif t == "t_FinSemana": tok_legibles.append("fin de semana")
            elif t == "t_Festivo":   tok_legibles.append("festivos")
            elif t == "t_Madrugada": tok_legibles.append("madrugada")
            elif t == "t_Mañana":    tok_legibles.append("mañana")
            elif t == "t_Tarde":     tok_legibles.append("tarde")
            elif t == "t_Noche":     tok_legibles.append("noche")
            else: tok_legibles.append(t.replace("t_", ""))
        ant_legible  = " + ".join(tok_legibles)
        cons_legible = ETIQUETA_METRICA.get(c["consecuente"], c["consecuente"])
        emoji        = NIVEL_EMOJI.get(c["consecuente"], "")
        descripciones.append(
            f"- {emoji} **{ant_legible}** → {cons_legible} "
            f"({c['n_sensores']}/{n_sensores_total} sensores)"
        )
    bullets = "\n".join(descripciones)
    return (
        f"Se identifican patrones recurrentes en al menos la mitad de los sensores, "
        f"lo que sugiere regularidades temporales transversales en el tráfico de Madrid:\n\n"
        f"{bullets}"
    )


def parrafo_atipicos(atipicos, tabla_cross):
    if not atipicos:
        return (
            "Ninguna fuente de datos muestra desviaciones marcadas respecto al "
            "comportamiento medio del grupo en las métricas globales."
        )
    por_sensor = defaultdict(list)
    for a in atipicos:
        por_sensor[a["sensor"]].append(a)

    lineas = []
    for sensor, lista in por_sensor.items():
        partes = []
        for a in lista:
            adj = "elevado" if a["direccion"] == "alto" else "reducido"
            partes.append(
                f"{a['metrica_global']} {adj} "
                f"({a['valor']} vs mediana {a['mediana_grupo']})"
            )
        desc = "; ".join(partes)
        lineas.append(f"- El sensor **{sensor}** presenta {desc}.")

    return "Se detectan comportamientos atípicos:\n\n" + "\n".join(lineas)


def parrafo_outliers(tabla_cross):
    con_alto = tabla_cross[tabla_cross["Outlier alto"] == "✅"]["Sensor"].tolist()
    con_bajo = tabla_cross[tabla_cross["Outlier bajo"] == "✅"]["Sensor"].tolist()
    partes = []
    if con_alto:
        partes.append(
            f"🔴 Picos excepcionales detectados en: **{', '.join(con_alto)}**"
        )
    if con_bajo:
        partes.append(
            f"⚪ Caídas excepcionales detectadas en: **{', '.join(con_bajo)}**"
        )
    if not partes:
        return "Ningún sensor presenta reglas asociadas a comportamientos outlier."
    if tabla_cross["Sensor"].nunique() == 1:
      return ""
    return "\n\n".join(partes)


def construir_informe_global(tabla_cross, comunes, atipicos, reglas_por_sensor,
                               NOMBRE_CONJUNTO, METRICAS, NOMBRE_METRICA_GLOBAL,
                               HAY_HORAS, HAY_FRANJAS):
    n_sensores = tabla_cross["Sensor"].nunique()
    fecha = datetime.now().strftime("%Y-%m-%d")
    lineas = []

    # ── 1. Cabecera ──────────────────────────────────────────────────────────
    lineas.append(f"# Informe Global Comparativo — {NOMBRE_CONJUNTO}")
    lineas.append("")
    lineas.append(
        f"*Generado el {fecha} "
        f"| {n_sensores} {'fuente' if n_sensores == 1 else 'fuentes'} de datos analizada{'s' if n_sensores != 1 else ''} "
        f"| {tabla_cross['Reglas'].sum()} patrones en total*"
    )
    lineas.append("")

    # ── 2. Narrativa coloquial ───────────────────────────────────────────────
    lineas.append(f"## ¿Cómo se comporta **{', '.join(METRICAS)}** en {NOMBRE_CONJUNTO}?")
    lineas.append("")
    lineas.append(
        "> Esta sección resume los hallazgos principales en lenguaje sencillo, "
        "sin tecnicismos. Los detalles técnicos se encuentran en las secciones siguientes."
    )
    lineas.append("")
    lineas.append(parrafo_coloquial_global(tabla_cross, NOMBRE_CONJUNTO))
    lineas.append("")

    # ── 3. Tabla comparativa global ──────────────────────────────────────────
    lineas.append("## Tabla comparativa global")
    lineas.append("")

    # Descripción de la tabla adaptada según bloques disponibles
    if HAY_HORAS or HAY_FRANJAS:
        lineas.append(
            f"Cada fila representa una fuente de datos. "
            f"La columna **Perfil del día** muestra el nivel de **{NOMBRE_METRICA_GLOBAL}** "
            f"dominante en cada franja (Madrugada | Mañana | Tarde | Noche): "
            f"🔴 excepcional · 🟠 muy alto · 🟡 alto · 🟢 moderado · 🔵 bajo · 🟣 muy bajo · ⚪ mínimo."
        )
    else:
        lineas.append(
            f"Cada fila representa una fuente de datos. "
            f"La columna **Patrón calendario dominante** indica el período temporal "
            f"(mes, estación, año) más recurrente en las reglas detectadas."
        )
    lineas.append("")

    # Columnas a mostrar — solo las que existen en la tabla
    _cols_candidatas = [
        "Sensor", "Métrica", "Reglas", "Conf. media (%)", "Lift medio", "Lift máx",
        "Nivel dominante",
        "Perfil del día",                    # solo si HAY_HORAS o HAY_FRANJAS
        "Patrón calendario dominante",        # solo si dataset diario
        "Hora más mencionada en reglas",      # solo si HAY_HORAS
        "Día más mencionado",                 # solo si HAY_DIAS
        "Outlier alto", "Outlier bajo",
    ]
    cols_mostrar = [c for c in _cols_candidatas if c in tabla_cross.columns]
    lineas.append(tabla_cross[cols_mostrar].to_markdown(index=False))
    lineas.append("")

    # ── 4. Análisis técnico ──────────────────────────────────────────────────
    lineas.append("## Análisis técnico comparativo")
    lineas.append("")
    lineas.append(parrafo_introductorio(tabla_cross, NOMBRE_CONJUNTO))
    lineas.append("")

    lineas.append("### Patrones compartidos entre fuentes de datos")
    lineas.append("")
    n_sensores = len(set(s for s, _ in reglas_por_sensor.keys()))
    lineas.append(parrafo_hallazgos_comunes(comunes, n_sensores))
    lineas.append("")

    lineas.append("### Fuentes con comportamiento atípico")
    lineas.append("")
    lineas.append(parrafo_atipicos(atipicos, tabla_cross))
    lineas.append("")

    _texto_outliers = parrafo_outliers(tabla_cross)
    if _texto_outliers:
        lineas.append("### Comportamientos extremos (outliers)")
        lineas.append("")
        lineas.append(_texto_outliers)
        lineas.append("")

    # Sección de perfiles solo si tiene contenido útil
    _frases_perfil = comparar_perfiles_dia(tabla_cross)
    if _frases_perfil:
        if HAY_HORAS or HAY_FRANJAS:
            lineas.append("### Comparativa de perfiles de día")
            lineas.append("")
            lineas.append(
                "Cada fuente tiene un perfil diario propio. "
                "Las fuentes con perfil idéntico comparten el mismo patrón estructural."
            )
        else:
            lineas.append("### Comparativa de patrones calendario")
            lineas.append("")
            lineas.append(
                "Cada fuente tiene un patrón calendario propio. "
                "Las fuentes con patrón idéntico comparten el mismo período temporal dominante."
            )
        lineas.append("")
        for frase in _frases_perfil:
            lineas.append(frase)
            lineas.append("")

    # ── 5. Enlaces a informes individuales ──────────────────────────────────
    lineas.append("---")
    lineas.append("")
    lineas.append("## Análisis detallado por fuente de datos")
    lineas.append("")
    lineas.append(
        "Para el desglose completo de reglas, visualizaciones y narrativa, "
        "consultar los informes individuales generados por `src03`:"
    )
    lineas.append("")
    for (sensor, metrica) in sorted(reglas_por_sensor.keys()):
        nombre_m = metrica.replace("_", " ").capitalize()
        lineas.append(
            f"- [{sensor} — {nombre_m}]"
            f"(./{sensor}_{metrica}_resumen.md)"
        )
    lineas.append("")

    return "\n".join(lineas)
