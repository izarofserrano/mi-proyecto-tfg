from __future__ import annotations

ETIQUETA_TEMPORAL: dict[str, str] = {
    # Años 2020–2030
    **{f"t_{y}": f"el año {y}" for y in range(2020, 2031)},
    # Meses
    "t_Ene":  "enero",      "t_Feb":  "febrero",   "t_Marz": "marzo",
    "t_Abr":  "abril",      "t_May":  "mayo",      "t_Jun":  "junio",
    "t_Jul":  "julio",      "t_Ago":  "agosto",    "t_Sep":  "septiembre",
    "t_Oct":  "octubre",    "t_Nov":  "noviembre", "t_Dic":  "diciembre",
    # Días de la semana
    "t_Lun": "los lunes",   "t_Mar": "los martes",   "t_Mie": "los miércoles",
    "t_Jue": "los jueves",  "t_Vie": "los viernes",  "t_Sab": "los sábados",
    "t_Dom": "los domingos",
    # Horas H00–H23
    **{f"t_H{h:02d}": f"las {h}h" for h in range(24)},
    # Franjas horarias
    "t_Madrugada": "la madrugada (0–6 h)",
    "t_Mañana":    "la mañana (7–13 h)",
    "t_Tarde":     "la tarde (14–20 h)",
    "t_Noche":     "la noche (21–23 h)",
    # Tipo de día
    "t_Laborable": "días laborables",
    "t_FinSemana": "fin de semana",
    # Quincenas
    "t_Q1mes": "la primera quincena del mes",
    "t_Q2mes": "la segunda quincena del mes",
    # Estaciones
    "t_Primavera": "primavera",
    "t_Verano":    "verano",
    "t_Otonio":    "otoño",
    "t_Invierno":  "invierno",
    # Festivos
    "t_Festivo": "días festivos",
    # Minutos — cuartos de hora
    "t_M00": "el primer cuarto de hora (minutos 0–14)",
    "t_M15": "el segundo cuarto de hora (minutos 15–29)",
    "t_M30": "el tercer cuarto de hora (minutos 30–44)",
    "t_M45": "el último cuarto de hora (minutos 45–59)",
}

ETIQUETA_METRICA: dict[str, str] = {
    "v_MuyBaja":     "muy baja",
    "v_Baja":        "baja",
    "v_Media":       "media",
    "v_Alta":        "alta",
    "v_MuyAlta":     "muy alta",
    "v_OutlierBajo": "excepcionalmente baja (outlier inferior)",
    "v_OutlierAlto": "excepcionalmente alta (outlier superior)",
}

NOMBRE_METRICA: dict[str, str] = {
    "intensidad": "intensidad del tráfico",
    "ocupacion":  "ocupación de la vía",
}

ORDEN_CONSECUENTE: list[str] = [
    "v_OutlierAlto", "v_MuyAlta", "v_Alta",
    "v_Media",
    "v_Baja", "v_MuyBaja", "v_OutlierBajo",
]

# ── Jerarquía padre → hijos (para agrupar horas bajo su franja) ───────────
JERARQUIA: dict[str, list[str]] = {
    "t_Madrugada": [f"t_H{h:02d}" for h in range(0, 7)],
    "t_Mañana":    [f"t_H{h:02d}" for h in range(7, 14)],
    "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
    "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
}

HORA_A_FRANJA: dict[str, str] = {
    h: f for f, hs in JERARQUIA.items() for h in hs
}

# ── Conjuntos de categorías temporales ────────────────────────────────────
HORAS      = {f"t_H{h:02d}" for h in range(24)}
FRANJAS    = {"t_Madrugada", "t_Mañana", "t_Tarde", "t_Noche"}
MESES      = {"t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
               "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"}
DIAS       = {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"}
ANIOS      = {f"t_{y}" for y in range(2020, 2031)}
TIPO_DIA   = {"t_Laborable", "t_FinSemana"}
QUINCENAS  = {"t_Q1mes", "t_Q2mes"}
MINUTOS    = {"t_M00", "t_M15", "t_M30", "t_M45"}
FESTIVOS   = {"t_Festivo"}
ESTACIONES = {"t_Primavera", "t_Verano", "t_Otonio", "t_Invierno"}
