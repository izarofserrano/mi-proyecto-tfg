from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FuzzyConfig:
    # Tolerancia general (herencia cuando la específica es None)
    tolerancia: float = 0.2

    # Tolerancias por bloque (None → hereda tolerancia general)
    tol_anios: Optional[float] = None
    tol_meses: Optional[float] = None
    tol_semanas: Optional[float] = None
    tol_horas: float = 0.5
    tol_quincenas: Optional[float] = None
    tol_estaciones: Optional[float] = None
    tol_absolutas: Optional[float] = None

    # Suelo mínimo de muestras en cada rampa difusa
    # Garantiza que la rampa no sea más estrecha que el intervalo entre muestras.
    n_muestras_rampa: int = 2

    # Flags de activación de bloques temporales
    # None = automático según granularidad y cobertura del dataset
    # True / False = el usuario fuerza la activación/desactivación
    gen_anios: Optional[bool] = None
    gen_meses: Optional[bool] = None
    gen_estaciones: Optional[bool] = None
    gen_quincenas: Optional[bool] = None
    gen_dias: Optional[bool] = None
    gen_laborables: Optional[bool] = None
    gen_franjas: Optional[bool] = None
    gen_horas: Optional[bool] = None
    gen_minutos: Optional[bool] = None
    gen_min_finos: Optional[bool] = None
    gen_festivos: Optional[bool] = None

    # Configuración de festivos (librería `holidays`)
    pais_festivos: str = "ES"
    subdiv_festivos: str = "MD"

    def tol(self, especifica: Optional[float]) -> float:
        """Devuelve la tolerancia específica o la general si es None."""
        return especifica if especifica is not None else self.tolerancia
