"""
src04 - Global Report Module
Función orquestadora para generar informes globales comparativos
"""
import os
import re
import pandas as pd
from pathlib import Path
from collections import Counter

from .global_report import (
    cargar_reglas_todos,
    construir_tabla_cross_sensor,
    patrones_compartidos,
    detectar_atipicos,
    construir_informe_global,
)


def generar_informe_global(
    sensores: list[str],
    metricas: list[str],
    dir_datos: str,
    nombre_conjunto: str,
    nombre_metrica_global: str = None
) -> dict:
    """
    Orquestador del informe global cross-sensor.

    Args:
        sensores: Lista de IDs de sensores/datasets
        metricas: Lista de métricas (ej: ["intensidad", "ocupacion"])
        dir_datos: Directorio donde están los CSVs de reglas
        nombre_conjunto: Nombre descriptivo del conjunto (ej: "Sensores de tráfico de Madrid")
        nombre_metrica_global: Nombre de la métrica principal para el informe

    Returns:
        dict con:
        - informe_md: str con el Markdown del informe
        - n_sources: int número de fuentes analizadas
        - total_rules: int número total de reglas
        - faltantes: list de CSVs no encontrados
    """
    # 1. Cargar reglas
    reglas_por_sensor, faltantes = cargar_reglas_todos(sensores, metricas, dir_datos)

    if not reglas_por_sensor:
        return {
            "informe_md": "# Informe Global\n\nNo se encontraron CSVs de reglas para procesar.",
            "n_sources": 0,
            "total_rules": 0,
            "faltantes": faltantes,
        }

    # 2. Detectar bloques temporales disponibles (unión de todos los CSVs fuzzy)
    _cols_fuzzy_union = set()
    for sensor in sensores:
        for metrica in metricas:
            _ruta_fuzzy = Path(dir_datos) / f"{sensor}_{metrica}_fuzzy.csv"
            if _ruta_fuzzy.exists():
                try:
                    _cols_fuzzy_union |= set(pd.read_csv(_ruta_fuzzy, nrows=0).columns)
                except Exception:
                    pass

    HAY_HORAS      = any(re.match(r'^t_H\d{2}$', c) for c in _cols_fuzzy_union)
    HAY_FRANJAS    = bool(_cols_fuzzy_union & {"t_Madrugada","t_Mañana","t_Tarde","t_Noche"})
    HAY_DIAS       = bool(_cols_fuzzy_union & {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"})

    # 3. Construir tabla cross-sensor
    tabla_cross = construir_tabla_cross_sensor(reglas_por_sensor, HAY_HORAS, HAY_FRANJAS, HAY_DIAS)

    # 4. Detectar patrones compartidos
    comunes = patrones_compartidos(reglas_por_sensor, umbral=0.5)

    # 5. Detectar atípicos
    atipicos = detectar_atipicos(tabla_cross)

    # 6. Nombre de métrica global (usar primera si no se especifica)
    if nombre_metrica_global is None:
        nombre_metrica_global = metricas[0] if metricas else "métrica"

    # 7. Generar informe Markdown
    informe_md = construir_informe_global(
        tabla_cross=tabla_cross,
        comunes=comunes,
        atipicos=atipicos,
        reglas_por_sensor=reglas_por_sensor,
        NOMBRE_CONJUNTO=nombre_conjunto,
        METRICAS=metricas,
        NOMBRE_METRICA_GLOBAL=nombre_metrica_global,
        HAY_HORAS=HAY_HORAS,
        HAY_FRANJAS=HAY_FRANJAS,
    )

    return {
        "informe_md": informe_md,
        "n_sources": len(reglas_por_sensor),
        "total_rules": tabla_cross["Reglas"].sum(),
        "faltantes": faltantes,
    }
