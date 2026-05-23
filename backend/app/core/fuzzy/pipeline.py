from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from .blocks import (
    _FuzzyContext,
    filtrar_constantes,
    generar_anios,
    generar_dias,
    generar_estaciones,
    generar_festivos,
    generar_franjas,
    generar_horas,
    generar_laborables,
    generar_metrica,
    generar_min_finos,
    generar_minutos,
    generar_meses,
    generar_quincenas,
)
from .config import FuzzyConfig
from .heuristic import _detectar_var_tiempo, detectar_var_metrica


def fuzzify(
    input_path: str,
    var_tiempo: Optional[str] = None,
    var_metrica_override: Optional[str] = None,
    config: Optional[FuzzyConfig] = None,
    output_path: Optional[str] = None,
    filter_constants: bool = False,
) -> pd.DataFrame:
    """Pipeline completo de fuzzificación (src01).

    Args:
        input_path: ruta al CSV del sensor.
        var_tiempo: nombre de la columna temporal. Si es None, se detecta automáticamente.
        var_metrica_override: si se proporciona, omite la heurística automática.
        config: parámetros difusos; usa FuzzyConfig() por defecto.
        output_path: si se proporciona, guarda el CSV fuzzy en esta ruta.
        filter_constants: si True, elimina columnas t_* constantes antes de guardar.

    Returns:
        DataFrame con las columnas t_* y v_* añadidas.
    """
    if config is None:
        config = FuzzyConfig()

    # ── Carga ─────────────────────────────────────────────────────────────────
    df_raw = pd.read_csv(input_path)

    # ── Detección automática de VAR_TIEMPO ────────────────────────────────────
    if var_tiempo is None:
        var_tiempo, df_raw = _detectar_var_tiempo(df_raw)
        if var_tiempo is None:
            raise ValueError(
                "No se detectó columna temporal automáticamente. "
                "Especifica var_tiempo manualmente."
            )

    df_raw[var_tiempo] = pd.to_datetime(df_raw[var_tiempo])

    # ── Granularidad (mediana de diffs temporales) ────────────────────────────
    _diffs = df_raw[var_tiempo].diff().dt.total_seconds().dropna()
    granularidad_s = float(_diffs.median()) if len(_diffs) else 3600.0

    # ── Detección de métrica ──────────────────────────────────────────────────
    var_metrica = detectar_var_metrica(df_raw, var_tiempo, var_metrica_override)

    # ── Preparar DataFrame de trabajo ─────────────────────────────────────────
    df = df_raw[[var_tiempo, var_metrica]].copy()
    t0 = df[var_tiempo].min()
    df["segundos"] = (df[var_tiempo] - t0).dt.total_seconds().astype(int)

    x = df["segundos"].to_numpy()
    x_max = int(df["segundos"].max())
    anio_inicio = df[var_tiempo].min().year
    anio_fin = df[var_tiempo].max().year

    # ── Cobertura ─────────────────────────────────────────────────────────────
    cobertura_s = (df[var_tiempo].max() - t0).total_seconds()
    cobertura_dias = cobertura_s / 86400
    n_anios_distintos = df[var_tiempo].dt.year.nunique()
    n_meses_distintos = df[var_tiempo].dt.to_period("M").nunique()

    # ── Activación automática de bloques ──────────────────────────────────────
    _auto = {
        "ANIOS":      n_anios_distintos >= 2,
        "MESES":      granularidad_s <= 86400  and n_meses_distintos >= 2,
        "ESTACIONES": granularidad_s <= 604800 and cobertura_dias >= 90,
        "QUINCENAS":  granularidad_s <= 86400  and cobertura_dias >= 30,
        "DIAS":       granularidad_s <= 86400  and cobertura_dias >= 7,
        "LABORABLES": granularidad_s <= 86400  and cobertura_dias >= 7,
        "FRANJAS":    granularidad_s <= 3600   and cobertura_dias >= 1,
        "HORAS":      granularidad_s <= 3600   and cobertura_dias >= 1,
        "MIN_FINOS":  granularidad_s < 60      and cobertura_s >= 3600,
        "MINUTOS":    granularidad_s < 900     and cobertura_s >= 3600,  # estricto: < 900
        "FESTIVOS":   granularidad_s <= 86400 and cobertura_dias >= 1,
    }

    def _resolver(flag: Optional[bool], clave: str) -> bool:
        return _auto[clave] if flag is None else bool(flag)

    gen_anios      = _resolver(config.gen_anios,      "ANIOS")
    gen_meses      = _resolver(config.gen_meses,      "MESES")
    gen_estaciones = _resolver(config.gen_estaciones, "ESTACIONES")
    gen_quincenas  = _resolver(config.gen_quincenas,  "QUINCENAS")
    gen_dias       = _resolver(config.gen_dias,       "DIAS")
    gen_laborables = _resolver(config.gen_laborables, "LABORABLES")
    gen_franjas    = _resolver(config.gen_franjas,    "FRANJAS")
    gen_horas      = _resolver(config.gen_horas,      "HORAS")
    gen_minutos    = _resolver(config.gen_minutos,    "MINUTOS")
    gen_min_finos  = _resolver(config.gen_min_finos,  "MIN_FINOS")
    gen_festivos   = _resolver(config.gen_festivos,   "FESTIVOS")

    # ── Contexto ──────────────────────────────────────────────────────────────
    ctx = _FuzzyContext(
        df=df,
        x=x,
        x_max=x_max,
        t0=t0,
        anio_inicio=anio_inicio,
        anio_fin=anio_fin,
        var_tiempo=var_tiempo,
        var_metrica=var_metrica,
        granularidad_s=granularidad_s,
        config=config,
    )

    # ── Bloques temporales (orden importante: dias→laborables, horas→franjas) ─
    if gen_anios:      generar_anios(ctx)
    if gen_meses:      generar_meses(ctx)
    if gen_dias:       generar_dias(ctx)
    if gen_horas:      generar_horas(ctx)
    if gen_laborables: generar_laborables(ctx)
    if gen_franjas:    generar_franjas(ctx)
    if gen_quincenas:  generar_quincenas(ctx)
    if gen_estaciones: generar_estaciones(ctx)
    if gen_festivos:   generar_festivos(ctx)
    if gen_minutos:    generar_minutos(ctx)
    if gen_min_finos:  generar_min_finos(ctx)

    # ── Variables de métrica ──────────────────────────────────────────────────
    generar_metrica(ctx)

    result = filtrar_constantes(ctx.df) if filter_constants else ctx.df

    # ── Guardar ───────────────────────────────────────────────────────────────
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        result.to_csv(output_path, index=False)

    return result
