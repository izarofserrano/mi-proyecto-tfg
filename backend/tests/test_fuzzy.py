import numpy as np
import pandas as pd
import pytest

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
