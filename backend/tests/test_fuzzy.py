import numpy as np
import pandas as pd
import pytest

from app.core.fuzzy.blocks import _FuzzyContext, filtrar_constantes, generar_metrica
from app.core.fuzzy.config import FuzzyConfig
from app.core.fuzzy.heuristic import _heuristica
from app.core.fuzzy.primitives import rampa_s, trapecio


def test_trapecio_nucleo_devuelve_1():
    """x=0 está en el núcleo [b=0, c=3600] → pertenencia debe ser 1.0."""
    result = trapecio(0, -1800, 0, 3600, 5400)
    assert float(result[0]) == 1.0


def test_rampa_s_valor_correcto():
    """0.5*3600=1800 y 2*900=1800 → max es 1800.0."""
    result = rampa_s(0.5, 3600, granularidad_s=900, n_muestras_rampa=2)
    assert result == 1800.0


def test_filtrar_constantes_metricas():
    """filtrar_constantes debe eliminar columnas v_* constantes (prefijo v_, no m_)."""
    df = pd.DataFrame({
        "v_X": [1.0, 1.0, 1.0],   # constante → debe eliminarse
        "v_Y": [0.1, 0.5, 0.9],   # variable  → debe mantenerse
        "t_A": [0.0, 0.0, 0.0],   # constante → debe eliminarse
        "t_B": [0.0, 0.5, 1.0],   # variable  → debe mantenerse
    })
    resultado = filtrar_constantes(df)
    assert "v_X" not in resultado.columns, "v_X constante debería haberse eliminado"
    assert "v_Y" in resultado.columns,     "v_Y variable no debería eliminarse"
    assert "t_A" not in resultado.columns, "t_A constante debería haberse eliminado"
    assert "t_B" in resultado.columns,     "t_B variable no debería eliminarse"


def test_trapecio_abs_no_es_triangulo():
    """Las columnas v_abs_ deben ser trapezoides (núcleo con anchura > 0), no triángulos."""
    n = 200
    valores = np.linspace(0.0, 100.0, n)
    fechas = pd.date_range("2024-01-01", periods=n, freq="h")
    df = pd.DataFrame({"fecha": fechas, "intensidad": valores})
    t0 = fechas[0]
    df["segundos"] = (df["fecha"] - t0).dt.total_seconds().astype(int)

    ctx = _FuzzyContext(
        df=df,
        x=df["segundos"].to_numpy(),
        x_max=int(df["segundos"].max()),
        t0=t0,
        anio_inicio=2024,
        anio_fin=2024,
        var_tiempo="fecha",
        var_metrica="intensidad",
        granularidad_s=3600.0,
        config=FuzzyConfig(),
    )
    generar_metrica(ctx)

    cols_abs = [c for c in df.columns if c.startswith("v_abs_")]
    assert cols_abs, "No se generaron columnas v_abs_"

    for col in cols_abs:
        n_en_nucleo = (df[col] == 1.0).sum()
        assert n_en_nucleo > 1, (
            f"{col}: solo {n_en_nucleo} punto(s) con μ=1.0 — "
            "el núcleo es puntual (triángulo), debería ser un trapecio con anchura > 0"
        )


def test_heuristica_detecta_intensidad_como_clara():
    """Con columnas [id, fecha, intensidad, utm_x, latitud], solo 'intensidad' es CLARA."""
    np.random.seed(42)
    fechas = pd.date_range("2024-01-01", periods=200, freq="h")
    horas = fechas.hour.to_numpy()
    # Valores enteros para evitar pct_u > 0.95 (demasiados únicos)
    intensidad = np.clip(
        np.round(20 + 30 * np.sin(np.pi * horas / 12) + np.random.normal(0, 5, len(fechas))),
        0, 100,
    )

    df = pd.DataFrame({
        "id":         ["sensor_1"] * 200,
        "fecha":      fechas,
        "intensidad": intensidad,
        "utm_x":      [650000.0] * 200,
        "latitud":    [43.26] * 200,
    })

    claras, ambiguas, info = _heuristica(df, "fecha")

    assert "intensidad" in claras, f"intensidad no detectada como CLARA. info={info}"
    assert "utm_x" not in claras
    assert "latitud" not in claras
