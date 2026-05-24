"""Generación de visualizaciones para informes de reglas difusas."""
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para entornos sin display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd


# Paleta coherente con los colores del heatmap
COLORES_CONSECUENTE = {
    "v_OutlierBajo": "#4a0e8f",
    "v_MuyBaja":     "#2166ac",
    "v_Baja":        "#74add1",
    "v_Media":       "#ffffbf",
    "v_Alta":        "#fdae61",
    "v_MuyAlta":     "#d73027",
    "v_OutlierAlto": "#7f0000",
}

ETIQUETA_CONSECUENTE = {
    "v_OutlierBajo": "Outlier bajo",
    "v_MuyBaja":     "Muy baja",
    "v_Baja":        "Baja",
    "v_Media":       "Media",
    "v_Alta":        "Alta",
    "v_MuyAlta":     "Muy alta",
    "v_OutlierAlto": "Outlier alto",
}

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def generar_heatmap(
    fuzzy_csv_path: str,
    sensor: str,
    metrica: str,
    output_path: Optional[str] = None
) -> Optional[Path]:
    """Genera el mapa de calor hora × día de la semana."""
    df = pd.read_csv(fuzzy_csv_path)

    # Identificar columnas de categoría disponibles
    orden = ["v_OutlierBajo", "v_MuyBaja", "v_Baja",
             "v_Media", "v_Alta", "v_MuyAlta", "v_OutlierAlto"]
    cols_v = [c for c in orden if c in df.columns
              and not c.startswith("v_abs_")
              and c != "v_Mediana"]

    # Extraer hora y día de semana
    horas_cols = [f"t_H{h:02d}" for h in range(24) if f"t_H{h:02d}" in df.columns]
    dias_cols = ["t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie", "t_Sab", "t_Dom"]
    dias_cols = [c for c in dias_cols if c in df.columns]

    if not horas_cols or not dias_cols:
        return None

    # Reconstruir columnas hora y dia_semana
    df["_hora"] = (df[horas_cols]
                   .idxmax(axis=1)
                   .str.extract(r"t_H(\d+)")[0]
                   .astype(int))
    df["_dia"] = (df[dias_cols]
                  .idxmax(axis=1)
                  .map({c: i for i, c in enumerate(dias_cols)}))

    # Calcular pertenencia media por hora × día
    grid_categoria = np.full((24, 7), "", dtype=object)
    grid_intensidad = np.zeros((24, 7))

    for h in range(24):
        for d in range(7):
            mask = (df["_hora"] == h) & (df["_dia"] == d)
            sub = df[mask]
            if sub.empty:
                grid_categoria[h, d] = "v_Media"
                continue
            medias = {c: sub[c].mean() for c in cols_v}
            cat_dominante = max(medias, key=medias.get)
            grid_categoria[h, d] = cat_dominante
            grid_intensidad[h, d] = medias[cat_dominante]

    # Construir array RGBA
    rgba_grid = np.zeros((24, 7, 4))
    for h in range(24):
        for d in range(7):
            cat = grid_categoria[h, d]
            color_hex = COLORES_CONSECUENTE.get(cat, "#cccccc")
            r, g, b = mcolors.to_rgb(color_hex)
            alpha = max(0.55, min(1.0, grid_intensidad[h, d] * 2))
            rgba_grid[h, d] = [r, g, b, alpha]

    # Plot
    nombre_metrica_str = metrica.replace("_", " ").capitalize()

    fig, ax = plt.subplots(figsize=(9, 11))
    ax.imshow(rgba_grid, aspect="auto", origin="upper",
              extent=[-0.5, 6.5, 23.5, -0.5])

    ax.set_xticks(range(7))
    ax.set_xticklabels(DIAS_SEMANA, fontsize=11)
    ax.set_yticks(range(24))
    ax.set_yticklabels([f"{h:02d}h" for h in range(24)], fontsize=9)
    ax.set_xlabel("Día de la semana", fontsize=11, labelpad=8)
    ax.set_ylabel("Hora del día", fontsize=11, labelpad=8)
    ax.set_title(
        f"Categoría dominante — {sensor}\n{nombre_metrica_str}",
        fontsize=13, fontweight="bold", pad=12
    )

    # Grid
    ax.set_xticks(np.arange(-0.5, 7, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 24, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.6)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Líneas separadoras de franjas
    for franja_inicio in [0, 7, 14, 21]:
        ax.axhline(franja_inicio - 0.5, color="white", linewidth=1.8, alpha=0.7)

    # Etiquetas de franja
    franjas = [(0, 6, "Madrugada"), (7, 13, "Mañana"),
               (14, 20, "Tarde"), (21, 23, "Noche")]
    for ini, fin, nombre in franjas:
        ax.annotate(nombre, xy=(7.05, (ini + fin) / 2),
                    xycoords=("data", "data"),
                    fontsize=8, color="#555555", va="center",
                    annotation_clip=False)

    # Leyenda
    categorias_presentes = [c for c in orden if c in np.unique(grid_categoria)]
    patches = [
        mpatches.Patch(
            color=COLORES_CONSECUENTE[c],
            label=ETIQUETA_CONSECUENTE[c]
        )
        for c in categorias_presentes
    ]
    ax.legend(handles=patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.13),
              ncol=len(patches), fontsize=9,
              frameon=True, edgecolor="#cccccc")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return Path(output_path)

    plt.close(fig)
    return None


def grafica_barras_lift(
    df_reglas: pd.DataFrame,
    sensor: str,
    metrica: str,
    output_path: Optional[str] = None,
    top_n: int = 20
) -> Optional[Path]:
    """Barras horizontales con las top_n reglas ordenadas por lift."""
    if df_reglas.empty:
        return None

    nombre_metrica_str = metrica

    top = df_reglas.nlargest(min(top_n, len(df_reglas)), "lift").copy()
    top = top.iloc[::-1]  # invertir para que el mayor quede arriba

    etiquetas = [
        f"{row['antecedente']}  →  {ETIQUETA_CONSECUENTE.get(row['consecuente'], row['consecuente'])}"
        for _, row in top.iterrows()
    ]
    colores = [
        COLORES_CONSECUENTE.get(row["consecuente"], "#888888")
        for _, row in top.iterrows()
    ]

    fig, ax = plt.subplots(figsize=(11, max(5, len(top) * 0.45)))

    bars = ax.barh(range(len(top)), top["lift"], color=colores,
                   edgecolor="white", linewidth=0.5)

    # Etiqueta del valor
    for i, (bar, (_, row)) in enumerate(zip(bars, top.iterrows())):
        ax.text(bar.get_width() + 0.05, i,
                f"lift {row['lift']:.1f}  conf {int(row['confianza']*100)}%",
                va="center", fontsize=8, color="#444444")

    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(etiquetas, fontsize=8)
    ax.set_xlabel("Lift", fontsize=10)
    ax.set_title(
        f"Top {len(top)} reglas por lift — {sensor} | {nombre_metrica_str}",
        fontsize=11, fontweight="bold", pad=10
    )
    ax.axvline(1.0, color="#aaaaaa", linewidth=0.8, linestyle="--")
    ax.set_xlim(0, top["lift"].max() * 1.25)
    ax.grid(axis="x", alpha=0.3)

    # Leyenda
    consecuentes_presentes = top["consecuente"].unique()
    patches = [
        plt.Rectangle((0, 0), 1, 1,
                      color=COLORES_CONSECUENTE.get(c, "#888888"),
                      label=ETIQUETA_CONSECUENTE.get(c, c))
        for c in sorted(consecuentes_presentes,
                        key=lambda x: list(ETIQUETA_CONSECUENTE.keys()).index(x)
                        if x in ETIQUETA_CONSECUENTE else 99)
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8,
              frameon=True, edgecolor="#cccccc", title="Categoría")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return Path(output_path)

    plt.close(fig)
    return None


def grafica_scatter(
    df_reglas: pd.DataFrame,
    sensor: str,
    metrica: str,
    output_path: Optional[str] = None
) -> Optional[Path]:
    """Scatter plot de soporte vs confianza coloreado por consecuente."""
    if df_reglas.empty:
        return None

    nombre_metrica_str = metrica

    fig, ax = plt.subplots(figsize=(10, 7))

    # Plot por consecuente para colorear
    for cons in df_reglas["consecuente"].unique():
        subset = df_reglas[df_reglas["consecuente"] == cons]
        ax.scatter(
            subset["soporte"],
            subset["confianza"],
            c=COLORES_CONSECUENTE.get(cons, "#888888"),
            label=ETIQUETA_CONSECUENTE.get(cons, cons),
            s=subset["lift"] * 30,  # tamaño proporcional al lift
            alpha=0.6,
            edgecolors="white",
            linewidth=0.5
        )

    ax.set_xlabel("Soporte", fontsize=10)
    ax.set_ylabel("Confianza", fontsize=10)
    ax.set_title(
        f"Soporte vs Confianza — {sensor} | {nombre_metrica_str}",
        fontsize=11, fontweight="bold", pad=10
    )
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=8, frameon=True,
              edgecolor="#cccccc", title="Categoría")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return Path(output_path)

    plt.close(fig)
    return None


def grafica_tabla_consecuentes(
    df_reglas: pd.DataFrame,
    sensor: str,
    metrica: str,
    output_path: Optional[str] = None
) -> Optional[Path]:
    """Tabla visual con resumen por consecuente."""
    if df_reglas.empty:
        return None

    nombre_metrica_str = metrica

    ORDEN = ["v_OutlierBajo", "v_MuyBaja", "v_Baja",
             "v_Media", "v_Alta", "v_MuyAlta", "v_OutlierAlto"]

    resumen = (df_reglas
               .groupby("consecuente")
               .agg(
                   n_reglas=("lift", "count"),
                   conf_media=("confianza", "mean"),
                   lift_medio=("lift", "mean"),
                   lift_max=("lift", "max"),
               )
               .round(2))

    # Ordenar según escala semántica
    resumen = resumen.reindex(
        [c for c in ORDEN if c in resumen.index]
    )

    cols = ["Categoría", "Nº reglas", "Conf. media", "Lift medio", "Lift máx."]
    filas = []
    colores_f = []

    for cat, row in resumen.iterrows():
        filas.append([
            ETIQUETA_CONSECUENTE.get(cat, cat),
            int(row["n_reglas"]),
            f"{row['conf_media']*100:.0f} %",
            f"{row['lift_medio']:.2f}",
            f"{row['lift_max']:.2f}",
        ])
        colores_f.append(COLORES_CONSECUENTE.get(cat, "#cccccc"))

    fig, ax = plt.subplots(figsize=(9, 0.55 * len(filas) + 1.5))
    ax.axis("off")

    tabla = ax.table(
        cellText=filas,
        colLabels=cols,
        cellLoc="center",
        loc="center",
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.6)

    # Colorear cabecera
    for j in range(len(cols)):
        tabla[0, j].set_facecolor("#333333")
        tabla[0, j].set_text_props(color="white", fontweight="bold")

    # Colorear filas
    for i, color_hex in enumerate(colores_f):
        r, g, b = mcolors.to_rgb(color_hex)
        fondo = (r * 0.35 + 0.65, g * 0.35 + 0.65, b * 0.35 + 0.65)
        for j in range(len(cols)):
            tabla[i + 1, j].set_facecolor(fondo)

    ax.set_title(
        f"Resumen por categoría — Sensor {sensor} | {nombre_metrica_str}",
        fontsize=11, fontweight="bold", pad=12
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return Path(output_path)

    plt.close(fig)
    return None


def generar_todas_visualizaciones(
    fuzzy_csv_path: str,
    rules_df: pd.DataFrame,
    sensor: str,
    metrica: str,
    output_dir: str
) -> list[Path]:
    """Genera las 4 visualizaciones y devuelve las rutas de los archivos generados."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    archivos = []

    # 1. Heatmap
    heatmap_path = output_dir / f"{sensor}_{metrica}_heatmap.png"
    if generar_heatmap(fuzzy_csv_path, sensor, metrica, str(heatmap_path)):
        archivos.append(heatmap_path)

    # 2. Barras lift
    barras_path = output_dir / f"{sensor}_{metrica}_barras_lift.png"
    if grafica_barras_lift(rules_df, sensor, metrica, str(barras_path)):
        archivos.append(barras_path)

    # 3. Scatter
    scatter_path = output_dir / f"{sensor}_{metrica}_scatter.png"
    if grafica_scatter(rules_df, sensor, metrica, str(scatter_path)):
        archivos.append(scatter_path)

    # 4. Tabla consecuentes
    tabla_path = output_dir / f"{sensor}_{metrica}_tabla_consecuentes.png"
    if grafica_tabla_consecuentes(rules_df, sensor, metrica, str(tabla_path)):
        archivos.append(tabla_path)

    return archivos
