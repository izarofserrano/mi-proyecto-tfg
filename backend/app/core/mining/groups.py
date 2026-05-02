from __future__ import annotations

_MESES_POR_ESTACION: dict[str, set[str]] = {
    "t_Invierno":  {"t_Dic", "t_Ene", "t_Feb"},
    "t_Primavera": {"t_Marz", "t_Abr", "t_May"},
    "t_Verano":    {"t_Jun", "t_Jul", "t_Ago"},
    "t_Otonio":    {"t_Sep", "t_Oct", "t_Nov"},
}

_TODOS_MESES: set[str] = {
    "t_Ene", "t_Feb", "t_Marz", "t_Abr", "t_May", "t_Jun",
    "t_Jul", "t_Ago", "t_Sep", "t_Oct", "t_Nov", "t_Dic",
}


def _construir_grupos(cols_disponibles) -> list[set[str]]:
    """Grupos mutuamente excluyentes filtrados a columnas presentes en el CSV."""
    cols = set(cols_disponibles)
    candidatos: list[set[str]] = [
        _TODOS_MESES,
        {"t_Primavera", "t_Verano", "t_Otonio", "t_Invierno"},
        {f"t_H{h:02d}" for h in range(24)},
        {"t_Madrugada", "t_Mañana", "t_Tarde", "t_Noche"},
        {"t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie", "t_Sab", "t_Dom"},
        {"t_Laborable", "t_FinSemana"},
        {c for c in cols if c.startswith("t_20")},
        {"t_Q1mes", "t_Q2mes"},
        {"t_M00", "t_M15", "t_M30", "t_M45"},
        {"t_Laborable", "t_Sab", "t_Dom"},
        {"t_FinSemana", "t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"},
    ]
    return [grupo & cols for grupo in candidatos if len(grupo & cols) >= 2]


def _construir_jerarquia(cols_disponibles) -> dict[str, list[str]]:
    """Jerarquía padre→hijos filtrada a columnas presentes en el CSV."""
    cols = set(cols_disponibles)
    completa: dict[str, list[str]] = {
        "t_Madrugada": [f"t_H{h:02d}" for h in range(0, 7)],
        "t_Mañana":    [f"t_H{h:02d}" for h in range(7, 14)],
        "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
        "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
        "t_Laborable": ["t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"],
        "t_FinSemana": ["t_Sab", "t_Dom"],
        "t_Invierno":  ["t_Dic", "t_Ene", "t_Feb"],
        "t_Primavera": ["t_Marz", "t_Abr", "t_May"],
        "t_Verano":    ["t_Jun", "t_Jul", "t_Ago"],
        "t_Otonio":    ["t_Sep", "t_Oct", "t_Nov"],
        "t_Festivo":   ["t_Laborable", "t_FinSemana"],
    }
    jerarquia = {}
    for padre, hijos in completa.items():
        if padre not in cols:
            continue
        hijos_presentes = [h for h in hijos if h in cols]
        if hijos_presentes:
            jerarquia[padre] = hijos_presentes
    return jerarquia


def combinacion_valida(tokens: set[str], grupos_excluyentes: list[set[str]]) -> bool:
    """Descarta combinaciones con >1 variable del mismo grupo excluyente,
    y mes+estación incompatibles."""
    for grupo in grupos_excluyentes:
        if len(tokens & grupo) > 1:
            return False
    for estacion, meses_validos in _MESES_POR_ESTACION.items():
        if estacion in tokens:
            meses_en_regla = tokens & _TODOS_MESES
            if meses_en_regla - meses_validos:
                return False
    return True
