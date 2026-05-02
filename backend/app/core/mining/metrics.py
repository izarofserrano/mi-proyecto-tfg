from __future__ import annotations

import numpy as np
import pandas as pd


def calcular_soporte(df: pd.DataFrame, columnas) -> float:
    """Soporte difuso = sum(min(mu1, mu2, ...)) / N."""
    if isinstance(columnas, str):
        mu = df[columnas]
    else:
        mu = df[list(columnas)].min(axis=1)
    return float(mu.sum() / len(df))


def calcular_confianza(df: pd.DataFrame, antecedente, consecuente: str) -> float:
    """Confianza = Sop(A AND C) / Sop(A)."""
    ant = [antecedente] if isinstance(antecedente, str) else list(antecedente)
    sop_a = calcular_soporte(df, ant)
    if sop_a == 0:
        return 0.0
    return float(calcular_soporte(df, ant + [consecuente]) / sop_a)


def calcular_lift(df: pd.DataFrame, antecedente, consecuente: str) -> float:
    """Lift = Conf(A->C) / Sop(C). Lift > 1 indica correlación positiva."""
    sop_c = calcular_soporte(df, consecuente)
    if sop_c == 0:
        return 0.0
    return float(calcular_confianza(df, antecedente, consecuente) / sop_c)


def evaluar_regla(df: pd.DataFrame, antecedente, consecuente: str) -> dict:
    ant = [antecedente] if isinstance(antecedente, str) else list(antecedente)
    return {
        "antecedente": " AND ".join(ant),
        "consecuente": consecuente,
        "n_vars":      len(ant),
        "soporte":     round(calcular_soporte(df, ant),                4),
        "confianza":   round(calcular_confianza(df, ant, consecuente), 4),
        "lift":        round(calcular_lift(df, ant, consecuente),      4),
    }


def calcular_aportacion(
    df: pd.DataFrame,
    columnas_antecedente,
    consecuente: str,
    cobertura_acumulada: np.ndarray,
) -> float:
    """Soporte marginal: cuánto soporte NUEVO aporta la regla sobre lo ya cubierto."""
    mu_ant = df[list(columnas_antecedente)].min(axis=1).to_numpy()
    mu_con = df[consecuente].to_numpy()
    mu_regla = np.minimum(mu_ant, mu_con)
    aportacion = np.maximum(0, mu_regla - cobertura_acumulada)
    return float(aportacion.sum() / len(df))
