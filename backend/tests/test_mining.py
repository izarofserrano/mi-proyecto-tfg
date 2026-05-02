import os

import pandas as pd
import pytest

from app.core.mining import BeamSearchMiner
from app.core.mining.groups import _construir_grupos, _construir_jerarquia, combinacion_valida

_FUZZY_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "ejemplos", "6823_intensidad_fuzzy.csv"
)


def test_miner_devuelve_reglas_con_lift_mayor_1():
    """BeamSearchMiner.fit() debe encontrar al menos 1 regla con lift > 1.0."""
    df = pd.read_csv(_FUZZY_CSV)
    miner = BeamSearchMiner(
        min_soporte=0.005,
        min_confianza=0.50,
        min_lift=1.5,
        beam_width=10,
        max_vars=3,
    )
    resultado = miner.fit(df)
    assert not resultado.empty, "No se encontraron reglas"
    assert (resultado["lift"] > 1.0).all(), "Algunas reglas tienen lift ≤ 1.0"


def test_construir_grupos_dinamico():
    """_construir_grupos omite grupos con < 2 columnas presentes."""
    cols = ["t_H08", "t_H09", "t_Lun", "t_Mar", "t_Mie", "v_Alta"]
    grupos = _construir_grupos(cols)
    # Debe incluir horas (t_H08, t_H09 = 2) y días (t_Lun, t_Mar, t_Mie = 3)
    todos = set().union(*grupos)
    assert "t_H08" in todos
    assert "t_Lun" in todos
    # v_Alta no es temporal → no debe aparecer en ningún grupo
    assert "v_Alta" not in todos


def test_combinacion_valida_rechaza_dos_horas():
    """No puede haber t_H08 y t_H09 juntos (mismo grupo excluyente)."""
    cols = [f"t_H{h:02d}" for h in range(24)] + ["t_Lun", "t_Mar"]
    grupos = _construir_grupos(cols)
    assert not combinacion_valida({"t_H08", "t_H09"}, grupos)
    assert combinacion_valida({"t_H08", "t_Lun"}, grupos)


def test_construir_jerarquia_dinamica():
    """La jerarquía omite padres cuyos hijos no están en el CSV."""
    cols = ["t_Tarde", "t_H14", "t_H15", "t_Laborable"]
    jerarquia = _construir_jerarquia(cols)
    assert "t_Tarde" in jerarquia
    assert "t_H14" in jerarquia["t_Tarde"]
    # t_Madrugada no está en cols → no debe aparecer
    assert "t_Madrugada" not in jerarquia
