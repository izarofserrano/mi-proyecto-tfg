import os
import re

import pandas as pd


def _sanitize_id(sensor_id: str) -> str:
    return re.sub(r"[/\\ ]", "_", str(sensor_id))


def split_by_sensor(input_path: str, output_dir: str) -> list[str]:
    """Lee un CSV maestro y escribe un CSV por sensor en output_dir.

    Args:
        input_path: ruta al CSV maestro (debe contener columnas 'id' y 'fecha').
        output_dir: carpeta de destino; se crea si no existe.

    Returns:
        Lista de rutas absolutas de los ficheros generados.

    Raises:
        ValueError: si el CSV no contiene las columnas 'id' o 'fecha'.
    """
    df = pd.read_csv(input_path)

    missing = [col for col in ("id", "fecha") if col not in df.columns]
    if missing:
        raise ValueError(f"El CSV no contiene las columnas obligatorias: {missing}")

    df["fecha"] = pd.to_datetime(df["fecha"])
    os.makedirs(output_dir, exist_ok=True)

    paths: list[str] = []
    for sensor_id, group in df.groupby("id"):
        filename = _sanitize_id(sensor_id) + ".csv"
        path = os.path.join(output_dir, filename)
        group.to_csv(path, index=False)
        paths.append(path)

    return paths


def detect_sensors(output_dir: str) -> list[str]:
    """Devuelve los ficheros .csv presentes en output_dir, ordenados."""
    if not os.path.isdir(output_dir):
        return []
    return [
        os.path.join(output_dir, f)
        for f in sorted(os.listdir(output_dir))
        if f.endswith(".csv")
    ]
