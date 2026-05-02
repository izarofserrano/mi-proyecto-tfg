from __future__ import annotations

import re
from typing import Optional

import pandas as pd


_NO_METRICA: set[str] = {
    "id", "codigo", "code", "cod", "clave", "key",
    "nombre", "name", "descripcion", "description", "label", "tag",
    "utm", "lon", "lat", "longitud", "latitud", "coordenada",
    "coord", "norte", "este", "x", "y", "z",
    "distrito", "zona", "area", "region", "municipio", "ciudad",
    "sensor", "estacion", "punto", "ubicacion", "location",
    "tipo", "type", "categoria", "category", "clase", "class",
    "flag", "estado", "status", "activo", "active",
}

_METRICA_POSITIVA: set[str] = {
    "intensidad", "ocupacion", "flujo", "velocidad", "volumen", "caudal",
    "temperatura", "presion", "humedad", "concentracion", "nivel",
    "consumo", "potencia", "energia", "demanda", "produccion",
    "ventas", "precio", "importe", "valor", "medida", "lectura",
    "indice", "tasa", "ratio", "porcentaje", "trafico", "carga",
    "uso", "rendimiento", "eficiencia",
}


def _tokenizar(col: str) -> set[str]:
    return set(re.split(r"[_\-\s]+", col.lower()))


def _heuristica(
    df: pd.DataFrame,
    var_tiempo: str,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Detecta candidatos a variable métrica por reglas estadísticas y nombres.

    Portada íntegramente del notebook src01, celda 3.

    Returns:
        claras:   columnas claramente métricas (token positivo + alta variabilidad).
        ambiguas: columnas que pasan los filtros pero no tienen token conocido.
        info:     motivo de clasificación por columna.
    """
    N = len(df)
    claras: list[str] = []
    ambiguas: list[str] = []
    info: dict[str, str] = {}

    for col in df.columns:
        if col == var_tiempo:
            continue
        serie = df[col]
        tokens = _tokenizar(col)

        # Texto
        if serie.dtype == object:
            info[col] = "texto → descartada"
            continue

        # Lista negra de tokens
        neg = tokens & _NO_METRICA
        if neg:
            info[col] = f"token no-métrica {neg} → descartada"
            continue

        # Estadísticos
        rango = serie.max() - serie.min()
        cv = serie.std() / (abs(serie.mean()) + 1e-9)
        n_u = serie.nunique()
        pct_u = n_u / N

        if rango < 1e-6 or cv < 0.01:
            info[col] = f"constante (cv={cv:.4f}) → descartada"
            continue

        if pct_u > 0.95:
            info[col] = f"posible ID ({n_u} únicos) → descartada"
            continue

        if n_u <= 10:
            info[col] = f"categórica ({n_u} valores) → descartada"
            continue

        # Variabilidad temporal
        try:
            tmp = df[[var_tiempo, col]].copy()
            tmp[var_tiempo] = pd.to_datetime(tmp[var_tiempo])
            tmp["_h"] = tmp[var_tiempo].dt.hour
            ratio_t = tmp.groupby("_h")[col].std().mean() / (serie.std() + 1e-9)
            if ratio_t < 0.05:
                info[col] = "sin variabilidad temporal → descartada"
                continue
        except Exception:
            pass

        # Clasificar
        pos = tokens & _METRICA_POSITIVA
        if pos and cv > 0.1:
            claras.append(col)
            info[col] = f"✓ CLARA (token={pos}, cv={cv:.2f})"
        else:
            ambiguas.append(col)
            info[col] = f"? AMBIGUA (cv={cv:.2f}, únicos={n_u})"

    return claras, ambiguas, info


def detectar_var_metrica(
    df: pd.DataFrame,
    var_tiempo: str,
    override: Optional[str] = None,
) -> str:
    """Devuelve el nombre de la columna métrica, usando override si se proporcionó.

    Raises:
        ValueError: si no hay candidatos y no se indicó override.
    """
    if override is not None:
        return override

    claras, ambiguas, _ = _heuristica(df, var_tiempo)
    todas = claras + ambiguas

    if not todas:
        raise ValueError(
            "No se detectó ninguna variable métrica candidata. "
            "Especifica var_metrica_override."
        )
    if len(todas) == 1:
        return todas[0]
    if not ambiguas:
        return claras[0]
    return claras[0] if claras else ambiguas[0]
