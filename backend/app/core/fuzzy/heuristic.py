from __future__ import annotations

import json
import re
from typing import Optional

import numpy as np
import pandas as pd

from app.core.config import settings


# ── Funciones LLM fallback (portadas del notebook src01 celda 3) ──────────────

def _llamar_llm(prompt: str, proveedor: str | None = None, modelo: str | None = None, api_key: str | None = None) -> str | None:
    """
    Interfaz única de LLM. Recibe un prompt (str), devuelve texto (str)
    o None si falla. Toda la dependencia de proveedor está AQUÍ y solo aquí.

    Para añadir un proveedor nuevo: añade una rama. El resto del código
    (perfilado, parseo, degradación) no se entera de qué proveedor es.
    """
    proveedor = proveedor or settings.proveedor_llm
    api_key = api_key or settings.llm_api_key

    _MODELO_LLM = {
        "gemini": "gemini-2.5-flash",
        "anthropic": "claude-opus-4-5",
        "openai": "gpt-4o",
        "ninguno": None,
    }
    modelo = modelo or _MODELO_LLM.get(proveedor)

    if proveedor == "ninguno" or not api_key:
        return None

    try:
        if proveedor == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=modelo, max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in resp.content if b.type == "text")

        elif proveedor == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=modelo, max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        elif proveedor == "gemini":
            import requests as _req
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{modelo}:generateContent?key={api_key}"
            )
            resp = _req.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=15,
            )
            resp.raise_for_status()
            texto = (resp.json()["candidates"][0]["content"]["parts"][0]["text"])
            # Gemini a veces envuelve la respuesta en ```json ... ```
            return texto.strip().removeprefix("```json").removesuffix("```").strip()

        else:
            print(f"  (LLM) Proveedor no soportado: {proveedor!r}")
            return None

    except ImportError as e:
        print(f"  (LLM) Paquete del proveedor no instalado: {e}")
        return None
    except Exception as e:
        print(f"  (LLM) Error en la llamada ({type(e).__name__}): {e}")
        return None


def _perfil_columnas_para_llm(df: pd.DataFrame, var_tiempo: str, columnas: list[str]) -> list[dict]:
    """Perfil AGREGADO de columnas. NO incluye datos crudos."""
    perfil = []
    N = len(df)
    for col in columnas:
        s = df[col]
        d = {"columna": col, "dtype": str(s.dtype), "n_unicos": int(s.nunique())}
        if np.issubdtype(s.dtype, np.number):
            d.update({
                "min": float(s.min()), "max": float(s.max()),
                "media": round(float(s.mean()), 4),
                "cv": round(float(s.std() / (abs(s.mean()) + 1e-9)), 4),
                "pct_unicos": round(s.nunique() / N, 4),
            })
        perfil.append(d)
    return perfil


def _detectar_metrica_via_llm(df: pd.DataFrame, var_tiempo: str, candidatas: list[str]) -> list[str] | None:
    """
    Usa _llamar_llm (agnóstico al proveedor) para clasificar columnas.
    Devuelve lista de nombres de columna, o None si falla / no disponible.
    Degrada con elegancia: cualquier problema → None.
    """
    if not settings.usar_llm_fallback:
        return None

    perfil = _perfil_columnas_para_llm(df, var_tiempo, candidatas)
    prompt = (
        "Eres un asistente que clasifica columnas de un dataset temporal.\n"
        "Dada esta lista de columnas candidatas con sus estadísticos agregados "
        "(NO se incluyen datos crudos), identifica cuáles representan MÉTRICAS "
        "cuantitativas analizables (magnitudes que varían en el tiempo y tiene "
        "sentido resumir: intensidad, ocupación, consumo, temperatura, etc.) "
        "y cuáles NO lo son (identificadores, códigos, coordenadas, categorías).\n\n"
        f"Variable temporal del dataset: {var_tiempo!r}\n"
        f"Columnas candidatas:\n{json.dumps(perfil, ensure_ascii=False, indent=2)}\n\n"
        "Responde EXCLUSIVAMENTE con un objeto JSON, sin texto adicional, "
        'con esta forma: {"metricas": ["col1", "col2"], "razonamiento": "breve"}'
    )

    texto = _llamar_llm(prompt)
    if texto is None:
        print("  (LLM) No disponible → se omite el fallback por LLM.")
        return None

    try:
        texto = texto.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(texto)
        metricas = [c for c in data.get("metricas", []) if c in candidatas]
        razon = data.get("razonamiento", "")
        if metricas:
            print(f"  (LLM) Métricas detectadas: {metricas}")
            print(f"  (LLM) Razonamiento: {razon}")
            return metricas
        print("  (LLM) No identificó métricas válidas entre las candidatas.")
        return None
    except (ValueError, KeyError) as e:
        print(f"  (LLM) Respuesta no parseable ({type(e).__name__}). Fallback manual.")
        return None


def _detectar_var_tiempo(df_raw: pd.DataFrame) -> tuple[str | None, pd.DataFrame]:
    """
    Busca columnas temporales: datetime, o fecha+hora separadas para combinar.
    Devuelve (nombre_columna, df_modificado_si_hay_combinacion).

    Estrategias (en orden):
    1. Columna datetime directa
    2. Par fecha + hora separadas
    3. Unix timestamp numérico
    4. Fallback: primera columna parseable como fecha
    """
    _TOKENS_FECHA = {'fecha', 'date', 'day', 'dia', 'txndate', 'fec'}
    _TOKENS_HORA = {'hora', 'time', 'hour', 'txntime', 'hh', 'hhmm'}

    def _tokenizar_col(col):
        return set(re.split(r'[_\-\s]+', col.lower())) | {col.lower()}

    # Python 3.14+: dtype puede ser str en lugar de object para columnas de texto
    cols_obj = [c for c in df_raw.columns if pd.api.types.is_string_dtype(df_raw[c]) or df_raw[c].dtype == object]
    cols_num = [c for c in df_raw.columns if pd.api.types.is_numeric_dtype(df_raw[c])]

    # Estrategia 1: columna datetime directa
    _candidata_solo_fecha = None
    for col in df_raw.columns:
        if not (pd.api.types.is_string_dtype(df_raw[col]) or df_raw[col].dtype == object):
            continue
        try:
            parsed = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
            if parsed.isna().mean() > 0.1:  # >10% sin parsear → no es fecha
                continue

            tiene_variabilidad_hora = parsed.dt.hour.std() > 0 or parsed.dt.minute.std() > 0
            tiene_variabilidad_fecha = parsed.dt.date.nunique() > 1

            if tiene_variabilidad_hora and tiene_variabilidad_fecha:
                print(f"  (tiempo) Columna datetime detectada: {col!r}")
                return col, df_raw
            elif tiene_variabilidad_fecha and _candidata_solo_fecha is None:
                _candidata_solo_fecha = col
        except Exception:
            pass

    # Estrategia 2: par fecha + hora separadas
    cols_fecha = [c for c in cols_obj if _tokenizar_col(c) & _TOKENS_FECHA]
    cols_hora = [c for c in cols_obj if _tokenizar_col(c) & _TOKENS_HORA]

    if cols_fecha and cols_hora:
        col_f, col_h = cols_fecha[0], cols_hora[0]
        try:
            combinada = pd.to_datetime(
                df_raw[col_f].astype(str) + ' ' + df_raw[col_h].astype(str)
            )
            df_raw = df_raw.copy()
            df_raw['_datetime'] = combinada
            print(f"  (tiempo) Fecha+hora combinadas: {col_f!r} + {col_h!r} -> '_datetime'")
            print(f"           Rango: {combinada.min()} -> {combinada.max()}")
            return '_datetime', df_raw
        except Exception as e:
            print(f"  (tiempo) Combinación fallida ({e})")

    # Estrategia 3: unix timestamp numérico
    for col in cols_num:
        tokens = _tokenizar_col(col)
        if tokens & {'timestamp', 'ts', 'epoch', 'unix', 'time'}:
            try:
                parsed = pd.to_datetime(df_raw[col], unit='s', errors='coerce')
                if parsed.notna().mean() > 0.9:
                    print(f"  (tiempo) Unix timestamp detectado: {col!r}")
                    df_raw = df_raw.copy()
                    df_raw['_datetime'] = parsed
                    return '_datetime', df_raw
            except Exception:
                pass

    # Usar candidata de solo fecha si no se encontró nada mejor
    if _candidata_solo_fecha is not None:
        print(f"  (tiempo) Columna de fecha detectada (sin hora): {_candidata_solo_fecha!r}")
        return _candidata_solo_fecha, df_raw

    # Fallback: primera columna parseable como fecha
    for col in cols_obj:
        try:
            pd.to_datetime(df_raw[col])
            print(f"  (tiempo) Fallback — usando primera columna fecha: {col!r}")
            return col, df_raw
        except Exception:
            pass

    print("  (!) No se detecto columna temporal. Especifica var_tiempo manualmente.")
    return None, df_raw


# ── Constantes heurística (portadas del notebook src01 celda 4) ───────────────

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

    Lógica de decisión (portada del notebook src01 celda 4):
      - Override manual      → usar lo que dijo el usuario
      - 0 candidatas         → error
      - 1 candidata total    → automático, sin ambigüedad
      - >1 CLARAS, 0 AMBIGUAS→ usar la primera (todas son métricas válidas)
      - hay AMBIGUAS         → intentar LLM fallback, si no, usar la primera clara o ambigua

    Raises:
        ValueError: si no hay candidatos y no se indicó override.
    """
    if override is not None:
        print(f"✓ Override manual: VAR_METRICA = {override!r}")
        return override

    claras, ambiguas, _ = _heuristica(df, var_tiempo)
    todas = claras + ambiguas

    if len(todas) == 0:
        raise ValueError(
            "No se detectó ninguna variable métrica candidata. "
            "Especifica var_metrica_override."
        )

    if len(todas) == 1:
        print(f"✓ Detección automática unívoca: VAR_METRICA = {todas[0]!r}")
        return todas[0]

    if len(ambiguas) == 0:
        # Varias CLARAS: todas son métricas reales del dataset
        print(f"✓ Varias métricas detectadas: {claras}")
        print(f"  Usando: {claras[0]!r}")
        return claras[0]

    # Hay AMBIGUAS y la heurística no puede decidir.
    print(f"⚠️  Columnas con nombre incierto: {ambiguas}")
    print(f"    Métricas claras: {claras}")

    metricas_llm = None
    if settings.usar_llm_fallback and not claras:
        # Solo recurrimos al LLM si NO hay ninguna clara: último recurso real.
        print("    → Intentando desambiguar con el LLM...")
        metricas_llm = _detectar_metrica_via_llm(df, var_tiempo, todas)

    if metricas_llm:
        print(f"✓ Métrica seleccionada por LLM: VAR_METRICA = {metricas_llm[0]!r}")
        if len(metricas_llm) > 1:
            print(f"  Otras métricas detectadas: {metricas_llm[1:]}")
        return metricas_llm[0]
    else:
        # Fallback manual (comportamiento original)
        var_metrica = claras[0] if claras else ambiguas[0]
        print(f"    Usando por defecto: {var_metrica!r}")
        return var_metrica
