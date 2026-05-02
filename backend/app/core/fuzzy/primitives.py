from __future__ import annotations

import numpy as np


def trapecio(x, a: float, b: float, c: float, d: float) -> np.ndarray:
    """Función de pertenencia trapezoidal.

    Núcleo [b, c] con valor 1.0; rampas de subida [a, b) y de bajada (c, d].
    Idéntica al notebook src01, con atleast_1d para aceptar escalares.
    """
    x = np.atleast_1d(np.asarray(x, dtype=float))
    y = np.zeros_like(x)

    m1 = (x >= a) & (x < b)
    y[m1] = (x[m1] - a) / (b - a) if b != a else 1.0

    m2 = (x >= b) & (x <= c)
    y[m2] = 1.0

    m3 = (x > c) & (x <= d)
    y[m3] = (d - x[m3]) / (d - c) if d != c else 1.0

    return np.clip(y, 0, 1).round(4)


def rampa_s(
    tol_prop: float,
    duracion_bloque: float,
    granularidad_s: float,
    n_muestras_rampa: int,
) -> float:
    """Calcula la rampa en segundos para un bloque temporal.

    max(tol_prop * duracion_bloque, n_muestras_rampa * granularidad_s)

    Garantiza que la rampa no sea más estrecha que el intervalo entre muestras,
    evitando que la variable difusa degenere en crisp cuando granularidad ≥ duración.
    """
    rampa_proporcional = tol_prop * duracion_bloque
    rampa_minima = n_muestras_rampa * granularidad_s
    return max(rampa_proporcional, rampa_minima)
