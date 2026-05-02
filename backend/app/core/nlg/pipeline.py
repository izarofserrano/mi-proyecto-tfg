from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from .labels import (
    ANIOS, DIAS, ETIQUETA_METRICA, FESTIVOS, FRANJAS, HORAS, MINUTOS,
    NOMBRE_METRICA, ORDEN_CONSECUENTE,
)
from .verbalize import (
    categoria_dominante, franja_de_tokens, listar_en_español,
    parsear_antecedente, regla_a_frase, verbalizar_antecedente,
)
from ..mining.groups import combinacion_valida, _construir_grupos


def agrupar_reglas(df_consecuente: pd.DataFrame) -> list[list[pd.Series]]:
    """Agrupa filas con contexto temporal similar en listas cohesivas."""
    registros = list(df_consecuente.iterrows())
    grupos: list[list[pd.Series]] = []
    asignado = [False] * len(registros)

    for i, (_, fila_i) in enumerate(registros):
        if asignado[i]:
            continue
        tokens_i = parsear_antecedente(fila_i["antecedente"])
        cat_i    = categoria_dominante(tokens_i)
        franja_i = franja_de_tokens(tokens_i) if cat_i == "hora" else None

        grupo_actual = [fila_i]
        asignado[i] = True

        for j, (_, fila_j) in enumerate(registros):
            if asignado[j]:
                continue
            tokens_j = parsear_antecedente(fila_j["antecedente"])
            cat_j    = categoria_dominante(tokens_j)

            if cat_i != cat_j:
                continue

            if cat_i == "hora":
                if franja_de_tokens(tokens_j) != franja_i:
                    continue

            if cat_i == "minuto":
                if (tokens_i & HORAS) != (tokens_j & HORAS):
                    continue

            if cat_i == "franja":
                if (tokens_i & FRANJAS) != (tokens_j & FRANJAS):
                    continue

            if cat_i == "dia_semana":
                if (tokens_i & DIAS) != (tokens_j & DIAS):
                    continue

            _excluir = ANIOS | FESTIVOS
            ti = tokens_i - _excluir if (tokens_i - _excluir) else tokens_i
            tj = tokens_j - _excluir if (tokens_j - _excluir) else tokens_j
            comun = ti & tj
            solap_i = len(comun) / len(ti) if ti else 0
            solap_j = len(comun) / len(tj) if tj else 0
            if min(solap_i, solap_j) < 0.5:
                continue

            grupo_actual.append(fila_j)
            asignado[j] = True

        grupos.append(grupo_actual)

    return grupos


def grupo_a_parrafo(
    filas: list[pd.Series],
    nombre_metrica: str,
    consecuente: str,
    min_reglas: int,
) -> str:
    desc_v = ETIQUETA_METRICA.get(consecuente, consecuente)
    filas_ordenadas = sorted(filas, key=lambda r: -r["lift"])

    # Caso A: grupo pequeño → frases individuales
    if len(filas_ordenadas) < min_reglas:
        return "\n".join(regla_a_frase(f, nombre_metrica) for f in filas_ordenadas)

    # Caso B: grupo amplio → párrafo narrativo
    conjuntos = [parsear_antecedente(f["antecedente"]) for f in filas_ordenadas]
    contexto_comun = conjuntos[0].copy()
    for c in conjuntos[1:]:
        contexto_comun &= c

    especificos = [c - contexto_comun for c in conjuntos]

    # Caso B.1: los detalles diferenciales son solo años → frase simple
    solo_anios = all(e <= ANIOS or not e for e in especificos)
    if solo_anios:
        conf_media = sum(f["confianza"] for f in filas_ordenadas) / len(filas_ordenadas)
        lift_max   = max(f["lift"] for f in filas_ordenadas)
        desc_ctx = (
            verbalizar_antecedente(contexto_comun) if contexto_comun
            else verbalizar_antecedente(conjuntos[0])
        )
        prefijo = "A" if contexto_comun & HORAS else "En"
        return (
            f"{prefijo} {desc_ctx}, la {nombre_metrica} tiende a ser {desc_v} "
            f"(confianza media {int(round(conf_media*100))} %, lift máximo {lift_max:.1f})."
        )

    # Caso B.2: párrafo narrativo completo
    detalles = []
    for f, especif in zip(filas_ordenadas, especificos):
        if especif:
            especif_filtrado = especif - ANIOS if (especif - ANIOS) else especif
            desc = verbalizar_antecedente(especif_filtrado)
        else:
            desc = verbalizar_antecedente(parsear_antecedente(f["antecedente"]))
        conf_pct = int(round(f["confianza"] * 100))
        detalles.append(f"{desc} ({conf_pct} %)")

    conf_media = sum(f["confianza"] for f in filas_ordenadas) / len(filas_ordenadas)
    lift_max   = max(f["lift"] for f in filas_ordenadas)
    stats = (
        f"Este patrón se observa con una confianza media del "
        f"{int(round(conf_media*100))} % y un lift máximo de {lift_max:.1f}."
    )

    if contexto_comun:
        ctx_desc = verbalizar_antecedente(contexto_comun)
        intro = (
            f"En el contexto de {ctx_desc}, la {nombre_metrica} tiende a ser "
            f"{desc_v}, especialmente en {listar_en_español(detalles)}."
        )
    else:
        intro = (
            f"La {nombre_metrica} tiende a ser {desc_v} en los siguientes "
            f"contextos: {listar_en_español(detalles)}."
        )

    return intro + " " + stats


def generar_resumen(
    df_reglas: pd.DataFrame,
    sensor: str,
    metrica: str,
    min_reglas_grupo: int = 2,
    output_path: Optional[str] = None,
) -> str:
    """Genera el resumen completo en Markdown para un sensor y métrica.

    Args:
        df_reglas: DataFrame con columnas [antecedente, consecuente, n_vars,
                   soporte, confianza, lift].
        sensor: identificador del sensor (usado en el título y rutas de imagen).
        metrica: nombre de la métrica (ej. "intensidad", "ocupacion").
        min_reglas_grupo: mínimo de reglas por grupo para párrafo narrativo.
        output_path: si se proporciona, guarda el Markdown en esta ruta.

    Returns:
        Cadena Markdown con el resumen completo.
    """
    nombre_metrica = NOMBRE_METRICA.get(metrica, metrica)

    # Filtrar combinaciones mes+estación semánticamente inválidas
    _cols_reglas = {
        tok
        for ant in df_reglas["antecedente"]
        for tok in ant.split(" AND ")
    }
    grupos_exc = _construir_grupos(_cols_reglas)
    df_reglas = df_reglas[
        df_reglas["antecedente"].apply(
            lambda a: combinacion_valida({t.strip() for t in a.split(" AND ")}, grupos_exc)
        )
    ].reset_index(drop=True)

    lineas: list[str] = []

    # Cabecera
    lineas += [
        f"# Resumen de comportamiento — Sensor {sensor}",
        "",
        f"**Métrica analizada:** {nombre_metrica.capitalize()}  ",
        f"**Total de reglas analizadas:** {len(df_reglas)}",
        "",
    ]

    # Sección de visualizaciones
    lineas += [
        "## Visualizaciones",
        "",
        "### Mapa de calor hora × día de la semana",
        f"![Mapa de calor hora x día](data/{sensor}_{metrica}_heatmap.png)",
        "",
        "### Reglas por fuerza de asociación (lift)",
        f"![Barras lift](data/{sensor}_{metrica}_barras_lift.png)",
        "",
        "### Soporte vs Confianza",
        f"![Scatter soporte-confianza](data/{sensor}_{metrica}_scatter.png)",
        "",
        "### Resumen por categoría",
        f"![Tabla consecuentes](data/{sensor}_{metrica}_tabla_consecuentes.png)",
        "",
    ]

    # Ordenar consecuentes
    consecuentes_en_datos = set(df_reglas["consecuente"].unique())
    consecuentes_ordenados = [c for c in ORDEN_CONSECUENTE if c in consecuentes_en_datos]
    for c in consecuentes_en_datos:
        if c not in consecuentes_ordenados:
            consecuentes_ordenados.append(c)

    # Análisis por nivel de tráfico
    lineas.append("## Análisis por nivel de tráfico")
    lineas.append("")

    for consecuente in consecuentes_ordenados:
        df_c = df_reglas[df_reglas["consecuente"] == consecuente].copy()
        if df_c.empty:
            continue

        desc_v = ETIQUETA_METRICA.get(consecuente, consecuente)
        n = len(df_c)
        lineas.append(f"### {nombre_metrica.capitalize()} {desc_v}")
        lineas.append(
            f"*{n} {'regla' if n == 1 else 'reglas'} — "
            f"confianza media: {df_c['confianza'].mean()*100:.0f} %, "
            f"lift medio: {df_c['lift'].mean():.1f}*"
        )
        lineas.append("")

        for grupo in agrupar_reglas(df_c):
            lineas.append(grupo_a_parrafo(grupo, nombre_metrica, consecuente, min_reglas_grupo))
            lineas.append("")

    # Estadísticas globales
    lineas += [
        "---",
        "",
        "## Estadísticas globales del análisis",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Reglas totales | {len(df_reglas)} |",
        f"| Consecuentes únicos | {len(consecuentes_ordenados)} |",
        f"| Soporte medio | {df_reglas['soporte'].mean():.4f} |",
        f"| Confianza media | {df_reglas['confianza'].mean()*100:.1f} % |",
        f"| Lift medio | {df_reglas['lift'].mean():.2f} |",
        f"| Lift máximo | {df_reglas['lift'].max():.2f} |",
    ]

    resultado = "\n".join(lineas)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(resultado)

    return resultado
