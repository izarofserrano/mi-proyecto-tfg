from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from .beam_search import (
    beam_search_reglas,
    filtrar_por_jerarquia,
    filtrar_redundantes,
    filtrar_top_por_consecuente,
)
from .groups import _construir_grupos, _construir_jerarquia


class BeamSearchMiner:
    """Minería de reglas de asociación difusas sobre un CSV fuzzificado."""

    def __init__(
        self,
        min_soporte: float = 0.005,
        min_confianza: float = 0.50,
        min_lift: float = 1.5,
        beam_width: int = 10,
        max_vars: int = 3,
        top_por_consecuente: int = 10,
    ) -> None:
        self.min_soporte = min_soporte
        self.min_confianza = min_confianza
        self.min_lift = min_lift
        self.beam_width = beam_width
        self.max_vars = max_vars
        self.top_por_consecuente = top_por_consecuente

    def fit(
        self,
        df: pd.DataFrame,
        output_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """Ejecuta el pipeline completo de minería sobre un DataFrame fuzzificado.

        Args:
            df: DataFrame con columnas t_* (antecedentes) y v_* (consecuentes).
            output_path: si se proporciona, guarda el CSV de reglas en esta ruta.

        Returns:
            DataFrame con columnas [antecedente, consecuente, n_vars, soporte,
            confianza, lift], ordenado por lift DESC.
        """
        vars_t = [c for c in df.columns if c.startswith("t_")]
        vars_v = [
            c for c in df.columns
            if c.startswith("v_")
            and not c.startswith("v_abs_")
            and c != "v_Mediana"
        ]

        grupos = _construir_grupos(df.columns)
        jerarquia = _construir_jerarquia(df.columns)

        todos: list[pd.DataFrame] = []
        for consecuente in vars_v:
            df_r = beam_search_reglas(
                df=df,
                vars_antecedente=vars_t,
                consecuente=consecuente,
                min_soporte=self.min_soporte,
                min_confianza=self.min_confianza,
                min_lift=self.min_lift,
                max_profundidad=self.max_vars,
                k_beam=self.beam_width,
                grupos_excluyentes=grupos,
            )
            if not df_r.empty:
                todos.append(df_r)

        if not todos:
            return pd.DataFrame(
                columns=["antecedente", "consecuente", "n_vars", "soporte", "confianza", "lift"]
            )

        df_reglas = (
            pd.concat(todos, ignore_index=True)
            .sort_values("lift", ascending=False)
            .reset_index(drop=True)
        )

        df_reglas = filtrar_redundantes(df_reglas, self.min_confianza)
        df_reglas = filtrar_por_jerarquia(df_reglas, jerarquia, self.min_confianza)
        df_reglas = filtrar_top_por_consecuente(df_reglas, self.top_por_consecuente)

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            df_reglas.to_csv(output_path, index=False)

        return df_reglas
