import os

import pandas as pd
import pytest

from app.core.nlg import generar_resumen
from app.core.nlg.verbalize import verbalizar_antecedente

_REGLAS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "ejemplos", "6823_ocupacion_reglas.csv"
)


# ── verbalizar_antecedente ─────────────────────────────────────────────────

@pytest.mark.parametrize("tokens,esperado_contiene", [
    # Hora sola
    ({"t_H07"},                 "las 7 h"),
    # Hora + tipo de día
    ({"t_H07", "t_Laborable"},  "días laborables"),
    # Franja
    ({"t_Madrugada"},           "madrugada"),
    # Día de semana
    ({"t_Dom"},                 "domingos"),
    # Mes
    ({"t_Ago"},                 "agosto"),
    # Estación
    ({"t_Verano"},              "verano"),
    # Festivo
    ({"t_Festivo"},             "festivos"),
    # Quincena
    ({"t_Q1mes"},               "primera quincena"),
    # Año dinámico
    ({"t_2024"},                "2024"),
    # Minutos + hora (orden: minuto primero)
    ({"t_M00", "t_H08"},        "primer cuarto"),
    # Minutos solos
    ({"t_M15"},                 "segundo cuarto"),
])
def test_verbalizar_antecedente_nunca_condiciones_no_especificadas(tokens, esperado_contiene):
    resultado = verbalizar_antecedente(tokens)
    assert resultado != "condiciones no especificadas", (
        f"verbalizar_antecedente({tokens}) devolvió 'condiciones no especificadas'"
    )
    assert esperado_contiene in resultado, (
        f"Se esperaba '{esperado_contiene}' en '{resultado}'"
    )


def test_verbalizar_antecedente_minutos_hora_orden_correcto():
    """Con t_M00 + t_H08 el minuto debe aparecer antes que la hora."""
    resultado = verbalizar_antecedente({"t_M00", "t_H08"})
    idx_min = resultado.find("cuarto")
    idx_hora = resultado.find("las 8")
    assert idx_min < idx_hora, f"Orden incorrecto en: '{resultado}'"


def test_verbalizar_antecedente_horas_consecutivas():
    """t_H03 y t_H04 consecutivas → 'entre las 3 h y las 4 h'."""
    resultado = verbalizar_antecedente({"t_H03", "t_H04"})
    assert "entre las 3 h y las 4 h" in resultado, f"Resultado: '{resultado}'"


# ── generar_resumen con CSV real ───────────────────────────────────────────

def test_generar_resumen_produce_markdown_valido():
    """generar_resumen sobre las reglas de ejemplo produce Markdown con cabecera,
    secciones esperadas y tabla de estadísticas."""
    df = pd.read_csv(_REGLAS_CSV)
    md = generar_resumen(df, sensor="6823", metrica="ocupacion")

    assert md.startswith("# Resumen de comportamiento"), "Falta cabecera H1"
    assert "## Análisis por nivel de tráfico" in md
    assert "## Estadísticas globales" in md
    assert "| Reglas totales |" in md
    assert "condiciones no especificadas" not in md, (
        "El resumen contiene 'condiciones no especificadas'"
    )
