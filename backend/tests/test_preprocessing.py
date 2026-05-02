import os

import pandas as pd
import pytest

from app.core.preprocessing.splitter import detect_sensors, split_by_sensor


@pytest.fixture
def master_csv(tmp_path):
    data = {
        "id": ["sensor_A", "sensor_A", "sensor_B", "sensor_B", "sensor_C"],
        "fecha": [
            "2024-01-01 00:00", "2024-01-01 00:15",
            "2024-01-01 00:00", "2024-01-01 00:15",
            "2024-01-01 00:00",
        ],
        "intensidad": [10, 20, 30, 40, 50],
    }
    path = tmp_path / "master.csv"
    pd.DataFrame(data).to_csv(path, index=False)
    return str(path)


def test_split_genera_tres_ficheros(master_csv, tmp_path):
    output_dir = str(tmp_path / "out")
    paths = split_by_sensor(master_csv, output_dir)

    assert len(paths) == 3
    for p in paths:
        assert os.path.isfile(p)


def test_id_con_slash_produce_guion_bajo(tmp_path):
    data = {
        "id": ["zona/norte", "zona/norte"],
        "fecha": ["2024-01-01 00:00", "2024-01-01 00:15"],
        "intensidad": [10, 20],
    }
    path = tmp_path / "master.csv"
    pd.DataFrame(data).to_csv(path, index=False)

    output_dir = str(tmp_path / "out")
    paths = split_by_sensor(str(path), output_dir)

    assert len(paths) == 1
    assert os.path.basename(paths[0]) == "zona_norte.csv"


def test_csv_sin_columna_id_lanza_value_error(tmp_path):
    data = {"fecha": ["2024-01-01"], "intensidad": [10]}
    path = tmp_path / "bad.csv"
    pd.DataFrame(data).to_csv(path, index=False)

    with pytest.raises(ValueError):
        split_by_sensor(str(path), str(tmp_path / "out"))
