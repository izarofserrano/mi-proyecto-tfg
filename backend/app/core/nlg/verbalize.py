from __future__ import annotations

import pandas as pd

from .labels import (
    ANIOS, DIAS, ESTACIONES, ETIQUETA_METRICA, ETIQUETA_TEMPORAL, FESTIVOS,
    FRANJAS, HORA_A_FRANJA, HORAS, MINUTOS, MESES, NOMBRE_METRICA,
    QUINCENAS, TIPO_DIA,
)


def parsear_antecedente(ant_str: str) -> set[str]:
    return {t.strip() for t in ant_str.split(" AND ")}


def categoria_dominante(tokens: set[str]) -> str:
    if tokens & HORAS:      return "hora"
    if tokens & MINUTOS:    return "minuto"
    if tokens & FRANJAS:    return "franja"
    if tokens & DIAS:       return "dia_semana"
    if tokens & FESTIVOS:   return "festivo"
    if tokens & TIPO_DIA:   return "tipo_dia"
    if tokens & MESES:      return "mes"
    if tokens & ESTACIONES: return "estacion"
    if tokens & QUINCENAS:  return "quincena"
    if tokens & ANIOS:      return "anio"
    return "otro"


def franja_de_tokens(tokens: set[str]) -> str | None:
    horas_presentes = tokens & HORAS
    franjas = {HORA_A_FRANJA.get(h) for h in horas_presentes} - {None}
    return franjas.pop() if len(franjas) == 1 else None


def verbalizar_token(tok: str) -> str:
    return ETIQUETA_TEMPORAL.get(tok, tok.replace("t_", ""))


def listar_en_español(items: list[str], conector: str = "y") -> str:
    if not items:       return ""
    if len(items) == 1: return items[0]
    return ", ".join(items[:-1]) + f" {conector} " + items[-1]


def horas_consecutivas(lista_tokens_hora: list[str]) -> str:
    nums = sorted(int(t[3:]) for t in lista_tokens_hora)
    if not nums:
        return ""
    if nums == list(range(nums[0], nums[-1] + 1)) and len(nums) > 1:
        return f"entre las {nums[0]} h y las {nums[-1]} h"
    return listar_en_español([f"las {n} h" for n in nums])


def verbalizar_antecedente(tokens: set[str]) -> str:
    """Convierte un conjunto de tokens temporales en una frase natural en español.

    Casos especiales:
    - minutos + horas → "el primer cuarto de hora de las 8h"  (minuto primero)
    - horas consecutivas → "entre las 3 h y las 5 h"
    """
    horas_tok   = sorted(tokens & HORAS)
    minutos_tok = sorted(tokens & MINUTOS)
    franjas_tok = sorted(tokens & FRANJAS)
    dias_tok    = sorted(tokens & DIAS)
    festivos_tok = sorted(tokens & FESTIVOS)
    tipo_tok    = sorted(tokens & TIPO_DIA)
    meses_tok   = sorted(tokens & MESES)
    est_tok     = sorted(tokens & ESTACIONES)
    quin_tok    = sorted(tokens & QUINCENAS)
    anio_tok    = sorted(tokens & ANIOS)

    partes: list[str] = []

    # Bloque temporal principal
    if minutos_tok and horas_tok:
        # minuto primero: "el primer cuarto de hora de las 8h"
        partes.append(listar_en_español([verbalizar_token(m) for m in minutos_tok]))
        partes.append(horas_consecutivas(horas_tok))
    elif horas_tok:
        partes.append(horas_consecutivas(horas_tok))
    elif franjas_tok:
        partes.append(listar_en_español([verbalizar_token(f) for f in franjas_tok]))
    elif minutos_tok:
        partes.append(listar_en_español([verbalizar_token(m) for m in minutos_tok]))

    if festivos_tok:
        partes.append("días festivos")

    if tipo_tok:
        partes.append(listar_en_español([verbalizar_token(t) for t in tipo_tok]))
    if dias_tok:
        partes.append(listar_en_español([verbalizar_token(d) for d in dias_tok]))
    if meses_tok:
        partes.append(listar_en_español([verbalizar_token(m) for m in meses_tok]))
    if est_tok:
        partes.append(listar_en_español([verbalizar_token(e) for e in est_tok]))
    if quin_tok:
        partes.append(listar_en_español([verbalizar_token(q) for q in quin_tok]))
    if anio_tok:
        partes.append(listar_en_español([verbalizar_token(a) for a in anio_tok]))

    if not partes:
        return "condiciones no especificadas"

    resultado = partes[0]
    for p in partes[1:]:
        resultado += " en " + p
    return resultado


def calidad_regla(row: pd.Series) -> str:
    lift = row["lift"]
    if lift >= 3.0: return "de forma muy marcada"
    if lift >= 2.0: return "de forma notable"
    if lift >= 1.5: return "con cierta consistencia"
    return "con cierta tendencia"


def regla_a_frase(row: pd.Series, nombre_metrica: str) -> str:
    tokens  = parsear_antecedente(row["antecedente"])
    cat     = categoria_dominante(tokens)
    desc_t  = verbalizar_antecedente(tokens)
    desc_v  = ETIQUETA_METRICA.get(row["consecuente"], row["consecuente"])
    calidad = calidad_regla(row)
    conf_pct = int(round(row["confianza"] * 100))
    lift_val = f"{row['lift']:.1f}"

    prefijos = {
        "hora":       "A",
        "franja":     "Durante",
        "dia_semana": "En",
        "tipo_dia":   "Durante los",
        "mes":        "En",
        "estacion":   "En",
        "quincena":   "Durante",
        "anio":       "En",
        "otro":       "En",
    }
    prefijo = prefijos.get(cat, "En")

    return (
        f"{prefijo} {desc_t}, la {nombre_metrica} tiende a ser {desc_v} "
        f"{calidad} (confianza {conf_pct} %, lift {lift_val})."
    )
