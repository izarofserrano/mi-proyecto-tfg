"""Bloques de fuzzificación temporal y de métrica, portados de src01.

Cada función generar_*() recibe un _FuzzyContext y escribe columnas
directamente en ctx.df. El orden de llamada en pipeline.py importa:
  generar_dias  → generar_laborables (depende de t_Lun..t_Dom)
  generar_horas → generar_franjas    (depende de t_H00..t_H23)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import FuzzyConfig
from .primitives import rampa_s, trapecio


@dataclass
class _FuzzyContext:
    df: pd.DataFrame
    x: np.ndarray
    x_max: int
    t0: pd.Timestamp
    anio_inicio: int
    anio_fin: int
    var_tiempo: str
    var_metrica: str
    granularidad_s: float
    config: FuzzyConfig


# ── Bloques temporales ────────────────────────────────────────────────────────

def generar_anios(ctx: _FuzzyContext) -> None:
    """Bloque AÑOS: t_{año} por cada año que cubre el dataset."""
    cfg = ctx.config
    for anio in range(ctx.anio_inicio, ctx.anio_fin + 1):
        inicio_anio = pd.Timestamp(year=anio, month=1, day=1)
        fin_anio = pd.Timestamp(year=anio + 1, month=1, day=1)

        b = (inicio_anio - ctx.t0).total_seconds()
        c = (fin_anio - ctx.t0).total_seconds()
        duracion_anio = c - b
        _r = rampa_s(cfg.tol(cfg.tol_anios), duracion_anio, ctx.granularidad_s, cfg.n_muestras_rampa)
        ctx.df[f"t_{anio}"] = trapecio(ctx.x, b - _r, b, c, c + _r)


def generar_meses(ctx: _FuzzyContext) -> None:
    """Bloque MESES: t_Ene, t_Feb, …, t_Dic."""
    cfg = ctx.config
    nombres = ["Ene", "Feb", "Marz", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    for num_mes, nombre in enumerate(nombres, start=1):
        col_difusa = np.zeros_like(ctx.x, dtype=float)

        for anio in range(ctx.anio_inicio, ctx.anio_fin + 1):
            inicio_mes = pd.Timestamp(year=anio, month=num_mes, day=1)
            fin_mes = (pd.Timestamp(year=anio + 1, month=1, day=1)
                       if num_mes == 12
                       else pd.Timestamp(year=anio, month=num_mes + 1, day=1))

            b = (inicio_mes - ctx.t0).total_seconds()
            c = (fin_mes - ctx.t0).total_seconds()
            if c < 0 or b > ctx.x_max:
                continue

            duracion = c - b
            _r = rampa_s(cfg.tol(cfg.tol_meses), duracion, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))

        ctx.df[f"t_{nombre}"] = col_difusa


def generar_dias(ctx: _FuzzyContext) -> None:
    """Bloque DÍAS DE LA SEMANA: t_Lun, t_Mar, …, t_Dom."""
    cfg = ctx.config
    df = ctx.df

    mascara_lunes = df[ctx.var_tiempo].dt.weekday == 0
    if not mascara_lunes.any():
        return
    b0 = int(df.loc[mascara_lunes.idxmax(), "segundos"])

    duracion_dia = 24 * 3600
    duracion_semana = 7 * duracion_dia
    nombres = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

    for n_dia, nombre in enumerate(nombres):
        col_difusa = np.zeros_like(ctx.x, dtype=float)
        offset = n_dia * duracion_dia

        k = 0
        while True:
            b = b0 + offset + k * duracion_semana
            if b > ctx.x_max + duracion_semana:
                break
            c = b + duracion_dia
            _r = rampa_s(cfg.tol(cfg.tol_semanas), duracion_dia, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))
            k += 1

        df[f"t_{nombre}"] = col_difusa


def generar_horas(ctx: _FuzzyContext) -> None:
    """Bloque HORAS DEL DÍA: t_H00, …, t_H23."""
    cfg = ctx.config
    df = ctx.df
    duracion_hora = 3600
    duracion_dia = 24 * 3600

    mascara_medianoche = (df[ctx.var_tiempo].dt.hour == 0) & (df[ctx.var_tiempo].dt.minute == 0)
    if mascara_medianoche.any():
        b0_hora = int(df.loc[mascara_medianoche.idxmax(), "segundos"])
    else:
        primer_dia = df[ctx.var_tiempo].min().normalize() + pd.Timedelta(days=1)
        b0_hora = int((primer_dia - ctx.t0).total_seconds())

    for hora in range(24):
        col_difusa = np.zeros_like(ctx.x, dtype=float)
        offset = hora * duracion_hora

        k = 0
        while True:
            b = b0_hora + offset + k * duracion_dia
            if b > ctx.x_max + duracion_dia:
                break
            c = b + duracion_hora
            _r = rampa_s(cfg.tol(cfg.tol_horas), duracion_hora, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))
            k += 1

        df[f"t_H{hora:02d}"] = col_difusa


def generar_laborables(ctx: _FuzzyContext) -> None:
    """Bloque LABORABLES/FIN DE SEMANA. Requiere generar_dias() previo."""
    df = ctx.df
    df["t_Laborable"] = df[["t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"]].max(axis=1).round(4)
    df["t_FinSemana"] = df[["t_Sab", "t_Dom"]].max(axis=1).round(4)


def generar_franjas(ctx: _FuzzyContext) -> None:
    """Bloque FRANJAS DEL DÍA. Requiere generar_horas() previo."""
    df = ctx.df
    franjas = {
        "t_Madrugada": [f"t_H{h:02d}" for h in range(0,  7)],
        "t_Mañana":    [f"t_H{h:02d}" for h in range(7,  14)],
        "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
        "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
    }
    for nombre_franja, cols_horas in franjas.items():
        existing = [c for c in cols_horas if c in df.columns]
        df[nombre_franja] = df[existing].max(axis=1).round(4) if existing else 0.0


def generar_quincenas(ctx: _FuzzyContext) -> None:
    """Bloque QUINCENAS: t_Q1mes (días 1–15), t_Q2mes (días 16–fin)."""
    cfg = ctx.config
    for nombre_col, dia_inicio, dia_fin_offset in [
        ("t_Q1mes", 1,  15),
        ("t_Q2mes", 16, None),
    ]:
        col_difusa = np.zeros_like(ctx.x, dtype=float)

        for anio in range(ctx.anio_inicio, ctx.anio_fin + 1):
            for mes in range(1, 13):
                inicio = pd.Timestamp(year=anio, month=mes, day=dia_inicio)
                if dia_fin_offset is None:
                    fin = (pd.Timestamp(year=anio + 1, month=1, day=1)
                           if mes == 12
                           else pd.Timestamp(year=anio, month=mes + 1, day=1))
                else:
                    fin = pd.Timestamp(year=anio, month=mes, day=dia_fin_offset,
                                       hour=23, minute=59, second=59)

                b = (inicio - ctx.t0).total_seconds()
                c = (fin - ctx.t0).total_seconds()
                if c < 0 or b > ctx.x_max:
                    continue

                duracion = c - b
                _r = rampa_s(cfg.tol(cfg.tol_quincenas), duracion, ctx.granularidad_s, cfg.n_muestras_rampa)
                col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))

        ctx.df[nombre_col] = col_difusa


def generar_estaciones(ctx: _FuzzyContext) -> None:
    """Bloque ESTACIONES: t_Primavera, t_Verano, t_Otonio, t_Invierno."""
    cfg = ctx.config
    estaciones = {
        "t_Primavera": ((3, 20), (6, 20)),
        "t_Verano":    ((6, 21), (9, 22)),
        "t_Otonio":    ((9, 23), (12, 20)),
    }

    for nombre_col, ((m_ini, d_ini), (m_fin, d_fin)) in estaciones.items():
        col_difusa = np.zeros_like(ctx.x, dtype=float)
        for anio in range(ctx.anio_inicio, ctx.anio_fin + 1):
            inicio = pd.Timestamp(year=anio, month=m_ini, day=d_ini)
            fin = pd.Timestamp(year=anio, month=m_fin, day=d_fin)
            b = (inicio - ctx.t0).total_seconds()
            c = (fin - ctx.t0).total_seconds()
            if c < 0 or b > ctx.x_max:
                continue
            duracion = c - b
            _r = rampa_s(cfg.tol(cfg.tol_estaciones), duracion, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))
        ctx.df[nombre_col] = col_difusa

    # Invierno cruza el año: 21 dic → 19 mar del año siguiente
    col_invierno = np.zeros_like(ctx.x, dtype=float)
    for anio in range(ctx.anio_inicio - 1, ctx.anio_fin + 1):
        inicio = pd.Timestamp(year=anio, month=12, day=21)
        fin = pd.Timestamp(year=anio + 1, month=3, day=19)
        b = (inicio - ctx.t0).total_seconds()
        c = (fin - ctx.t0).total_seconds()
        if c < 0 or b > ctx.x_max:
            continue
        duracion = c - b
        _r = rampa_s(cfg.tol(cfg.tol_estaciones), duracion, ctx.granularidad_s, cfg.n_muestras_rampa)
        col_invierno = np.maximum(col_invierno, trapecio(ctx.x, b - _r, b, c, c + _r))
    ctx.df["t_Invierno"] = col_invierno


def generar_festivos(ctx: _FuzzyContext) -> None:
    """Bloque FESTIVOS: t_Festivo = 1.0 si festivo oficial, 0.0 si no."""
    cfg = ctx.config
    try:
        import holidays as hol_lib
        anios = list(range(ctx.anio_inicio, ctx.anio_fin + 1))
        if cfg.subdiv_festivos and cfg.subdiv_festivos.strip():
            festivos_set = set(hol_lib.country_holidays(
                cfg.pais_festivos, subdiv=cfg.subdiv_festivos, years=anios
            ).keys())
        else:
            festivos_set = set(hol_lib.country_holidays(
                cfg.pais_festivos, years=anios
            ).keys())
        ctx.df["t_Festivo"] = ctx.df[ctx.var_tiempo].dt.date.apply(
            lambda d: 1.0 if d in festivos_set else 0.0
        )
    except ImportError:
        ctx.df["t_Festivo"] = 0.0


def generar_minutos(ctx: _FuzzyContext) -> None:
    """Bloque MINUTOS (cuartos de hora): t_M00, t_M15, t_M30, t_M45.

    Solo debe llamarse si GRANULARIDAD_S < 900 (condición estricta, no <=).
    """
    cfg = ctx.config
    df = ctx.df
    duracion_cuarto = 15 * 60
    duracion_hora_s = 3600

    mascara_mm00 = (df[ctx.var_tiempo].dt.minute == 0) & (df[ctx.var_tiempo].dt.second == 0)
    if mascara_mm00.any():
        b0_min = int(df.loc[mascara_mm00.idxmax(), "segundos"])
    else:
        primer_h = df[ctx.var_tiempo].min().floor("h") + pd.Timedelta(hours=1)
        b0_min = int((primer_h - ctx.t0).total_seconds())

    for minuto_inicio in [0, 15, 30, 45]:
        col_difusa = np.zeros_like(ctx.x, dtype=float)
        offset = minuto_inicio * 60

        k = 0
        while True:
            b = b0_min + offset + k * duracion_hora_s
            if b > ctx.x_max + duracion_hora_s:
                break
            c = b + duracion_cuarto
            _r = rampa_s(cfg.tol(cfg.tol_horas), duracion_cuarto, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))
            k += 1

        df[f"t_M{minuto_inicio:02d}"] = col_difusa


def generar_min_finos(ctx: _FuzzyContext) -> None:
    """Bloque MINUTOS FINOS (minuto a minuto): t_m00..t_m59.

    Solo debe llamarse si GRANULARIDAD_S < 60.
    """
    cfg = ctx.config
    df = ctx.df
    duracion_minuto = 60
    duracion_hora_s = 3600

    mascara_s00 = (df[ctx.var_tiempo].dt.second == 0) & (df[ctx.var_tiempo].dt.minute == 0)
    if mascara_s00.any():
        b0 = int(df.loc[mascara_s00.idxmax(), "segundos"])
    else:
        primer_h = df[ctx.var_tiempo].min().floor("h") + pd.Timedelta(hours=1)
        b0 = int((primer_h - ctx.t0).total_seconds())

    for minuto in range(60):
        col_difusa = np.zeros_like(ctx.x, dtype=float)
        offset = minuto * duracion_minuto

        k = 0
        while True:
            b = b0 + offset + k * duracion_hora_s
            if b > ctx.x_max + duracion_hora_s:
                break
            c = b + duracion_minuto
            _r = rampa_s(cfg.tol(cfg.tol_horas), duracion_minuto, ctx.granularidad_s, cfg.n_muestras_rampa)
            col_difusa = np.maximum(col_difusa, trapecio(ctx.x, b - _r, b, c, c + _r))
            k += 1

        df[f"t_m{minuto:02d}"] = col_difusa


# ── Bloque de métrica ─────────────────────────────────────────────────────────

def _calcular_breakpoints_logicos(min_v: float, max_v: float) -> list[float]:
    """Breakpoints 'redondos' que cubren [min_v, max_v] de forma uniforme."""
    rango = max_v - min_v
    if rango == 0:
        return [min_v]

    escalones_candidatos = [
        0.01, 0.02, 0.025, 0.05,
        0.1, 0.2, 0.25, 0.5,
        1, 2, 2.5, 5,
        10, 20, 25, 50,
        100, 200, 250, 500,
        1000, 2000, 2500, 5000,
    ]
    escalon: float | None = None
    for e in escalones_candidatos:
        if 3 <= rango / e <= 6:
            escalon = e
            break
    if escalon is None:
        escalon = round(rango / 4, 2)

    primer_bp = np.ceil(min_v / escalon) * escalon
    breakpoints: list[float] = []
    bp = primer_bp
    while bp <= max_v + escalon * 0.01:
        breakpoints.append(round(float(bp), 10))
        bp += escalon

    if not breakpoints or breakpoints[0] > min_v:
        breakpoints.insert(0, min_v)
    if breakpoints[-1] < max_v:
        if (max_v - breakpoints[-1]) > escalon * 0.3:
            breakpoints.append(max_v)

    return breakpoints


def generar_metrica(ctx: _FuzzyContext) -> None:
    """Variables difusas de la métrica: v_MuyBaja..v_MuyAlta, outliers y absolutas."""
    cfg = ctx.config
    df = ctx.df
    var = ctx.var_metrica

    max_val = df[var].max()
    min_val = df[var].min()
    p10 = df[var].quantile(0.10)
    p25 = df[var].quantile(0.25)
    p35 = df[var].quantile(0.35)
    p45 = df[var].quantile(0.45)
    p50 = df[var].quantile(0.50)
    p55 = df[var].quantile(0.55)
    p65 = df[var].quantile(0.65)
    p75 = df[var].quantile(0.75)
    p90 = df[var].quantile(0.90)

    # Categorías lingüísticas (percentiles)
    df["v_MuyBaja"] = trapecio(df[var], -1,  0,   p10, p25)
    df["v_Baja"]    = trapecio(df[var], p10, p25, p35, p45)
    df["v_Media"]   = trapecio(df[var], p35, p45, p55, p65)
    df["v_Alta"]    = trapecio(df[var], p55, p65, p75, p90)
    df["v_MuyAlta"] = trapecio(df[var], p75, p90, max_val, max_val + 1)

    # Mediana
    df["v_Mediana"] = trapecio(df[var], p25, p50, p50, p75)

    # Outliers estadísticos (media ± 2·std)
    mean_val = df[var].mean()
    std_val = df[var].std()
    df["v_OutlierBajo"] = trapecio(
        df[var], min_val - 1, min_val, mean_val - 2 * std_val, mean_val - std_val
    )
    df["v_OutlierAlto"] = trapecio(
        df[var], mean_val + std_val, mean_val + 2 * std_val, max_val, max_val + 1
    )

    # Valores absolutos con breakpoints lógicos
    breakpoints = _calcular_breakpoints_logicos(min_val, max_val)

    for i, bp in enumerate(breakpoints):
        if i == 0:
            rampa_izq = breakpoints[1] - bp
        else:
            rampa_izq = bp - breakpoints[i - 1]

        if i == len(breakpoints) - 1:
            rampa_der = bp - breakpoints[i - 1]
        else:
            rampa_der = breakpoints[i + 1] - bp

        ancho_nucleo = min(rampa_izq, rampa_der) * 0.3
        a = bp - rampa_izq
        b = bp - ancho_nucleo / 2
        c = bp + ancho_nucleo / 2
        d = bp + rampa_der

        nombre_bp = str(round(bp, 4)).replace(".", "_").replace("-", "neg")
        df[f"v_abs_{nombre_bp}"] = trapecio(df[var], a, b, c, d)


# ── Utilidad ──────────────────────────────────────────────────────────────────

def filtrar_constantes(
    df: pd.DataFrame,
    prefijos: tuple[str, ...] = ("t_", "v_"),
) -> pd.DataFrame:
    """Elimina columnas difusas constantes (todo 0 o todo 1)."""
    cols_difusas = [c for c in df.columns if any(c.startswith(p) for p in prefijos)]
    cols_eliminar = [c for c in cols_difusas if df[c].nunique() <= 1]
    return df.drop(columns=cols_eliminar)
