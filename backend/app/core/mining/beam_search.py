from __future__ import annotations

import numpy as np
import pandas as pd

from .groups import combinacion_valida
from .metrics import (
    calcular_aportacion,
    calcular_confianza,
    calcular_lift,
    calcular_soporte,
    evaluar_regla,
)


def beam_search_reglas(
    df: pd.DataFrame,
    vars_antecedente: list[str],
    consecuente: str,
    min_soporte: float,
    min_confianza: float,
    min_lift: float,
    max_profundidad: int,
    k_beam: int,
    grupos_excluyentes: list[set[str]],
) -> pd.DataFrame:
    """Genera reglas difusas SI antecedente → consecuente mediante beam search.

    Acepta una regla solo si su aportación marginal al soporte global supera
    min_soporte. Devuelve DataFrame ordenado por lift DESC.
    """
    reglas_validas: list[dict] = []
    vistos: set[tuple] = set()
    beam_actual: list[tuple] = [(v,) for v in vars_antecedente]
    cobertura_acumulada = np.zeros(len(df))

    for profundidad in range(1, max_profundidad + 1):
        puntuaciones: list[tuple[tuple, float]] = []

        for candidato in beam_actual:
            clave = tuple(sorted(candidato))
            if clave in vistos:
                continue
            vistos.add(clave)

            if not combinacion_valida(set(clave), grupos_excluyentes):
                continue

            sop = calcular_soporte(df, list(clave))
            if sop < min_soporte:
                continue

            conf = calcular_confianza(df, list(clave), consecuente)
            lift = calcular_lift(df, list(clave), consecuente)

            if conf >= min_confianza and lift >= min_lift:
                aportacion = calcular_aportacion(
                    df, list(clave), consecuente, cobertura_acumulada
                )
                if aportacion >= min_soporte:
                    reglas_validas.append(evaluar_regla(df, list(clave), consecuente))
                    mu_ant = df[list(clave)].min(axis=1).to_numpy()
                    mu_con = df[consecuente].to_numpy()
                    cobertura_acumulada = np.maximum(
                        cobertura_acumulada,
                        np.minimum(mu_ant, mu_con),
                    )

            puntuaciones.append((clave, conf))

        if not puntuaciones or profundidad == max_profundidad:
            break

        top_k = sorted(puntuaciones, key=lambda x: x[1], reverse=True)[:k_beam]

        beam_siguiente: list[tuple] = []
        for clave, _ in top_k:
            for nueva_var in vars_antecedente:
                if nueva_var not in clave:
                    nuevo = tuple(sorted(set(clave) | {nueva_var}))
                    if nuevo not in vistos:
                        beam_siguiente.append(nuevo)

        beam_actual = list(dict.fromkeys(beam_siguiente))
        if not beam_actual:
            break

    if not reglas_validas:
        return pd.DataFrame(
            columns=["antecedente", "consecuente", "n_vars", "soporte", "confianza", "lift"]
        )

    return (
        pd.DataFrame(reglas_validas)
        .drop_duplicates(subset=["antecedente", "consecuente"])
        .sort_values("lift", ascending=False)
        .reset_index(drop=True)
    )


def filtrar_redundantes(df_reglas: pd.DataFrame, min_confianza: float) -> pd.DataFrame:
    """Elimina regla A si existe subconjunto estricto A' con mismo consecuente
    y confianza ≥ min_confianza."""
    registros = df_reglas.to_dict("records")
    mantener = []
    for i, fila in enumerate(registros):
        vars_fila = set(fila["antecedente"].split(" AND "))
        es_redundante = False
        for j, otra in enumerate(registros):
            if i == j:
                continue
            vars_otra = set(otra["antecedente"].split(" AND "))
            if (
                vars_otra < vars_fila
                and otra["consecuente"] == fila["consecuente"]
                and otra["confianza"] >= min_confianza
            ):
                es_redundante = True
                break
        if not es_redundante:
            mantener.append(fila)
    return pd.DataFrame(mantener).reset_index(drop=True)


def filtrar_por_jerarquia(
    df_reglas: pd.DataFrame,
    jerarquia: dict[str, list[str]],
    min_confianza: float,
) -> pd.DataFrame:
    """Elimina la regla con variable 'hijo' si existe la equivalente con 'padre'
    y su confianza supera min_confianza."""
    registros = df_reglas.to_dict("records")
    mantener = []
    for i, fila in enumerate(registros):
        vars_fila = set(fila["antecedente"].split(" AND "))
        es_redundante = False
        for padre, hijos in jerarquia.items():
            hijos_en_fila = vars_fila & set(hijos)
            if not hijos_en_fila:
                continue
            vars_con_padre = (vars_fila - hijos_en_fila) | {padre}
            for j, otra in enumerate(registros):
                if i == j:
                    continue
                vars_otra = set(otra["antecedente"].split(" AND "))
                if (
                    vars_otra == vars_con_padre
                    and otra["consecuente"] == fila["consecuente"]
                    and otra["confianza"] >= min_confianza
                ):
                    es_redundante = True
                    break
            if es_redundante:
                break
        if not es_redundante:
            mantener.append(fila)
    return pd.DataFrame(mantener).reset_index(drop=True)


def filtrar_top_por_consecuente(df_reglas: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Limita a top_n reglas por consecuente (ordenadas por lift)."""
    return (
        df_reglas
        .sort_values("lift", ascending=False)
        .groupby("consecuente", group_keys=False)
        .head(top_n)
        .sort_values("lift", ascending=False)
        .reset_index(drop=True)
    )
