"""
Tests para src04 - Informe Global Comparativo
"""
import pandas as pd
import pytest

from app.core.global_report.global_report import (
    construir_informe_global,
    detectar_atipicos,
    patrones_compartidos,
)


def test_patrones_compartidos_detecta_comunes():
    """Dos sensores con una regla común → aparece en patrones_compartidos()"""
    reglas_s1 = pd.DataFrame([
        {"antecedente": "t_H08", "consecuente": "v_Alta", "soporte": 0.1,
         "confianza": 0.8, "lift": 2.0, "n_vars": 1},
    ])
    reglas_s2 = pd.DataFrame([
        {"antecedente": "t_H08", "consecuente": "v_Alta", "soporte": 0.1,
         "confianza": 0.8, "lift": 2.0, "n_vars": 1},
    ])

    reglas_por_sensor = {
        ("sensor1", "intensidad"): reglas_s1,
        ("sensor2", "intensidad"): reglas_s2,
    }

    comunes = patrones_compartidos(reglas_por_sensor, umbral=0.5)

    assert len(comunes) > 0
    assert comunes[0]["antecedente"] == "t_H08"
    assert comunes[0]["consecuente"] == "v_Alta"
    assert comunes[0]["n_sensores"] == 2


def test_patrones_compartidos_umbral():
    """Con umbral=1.0 solo aparece si está en TODOS los sensores"""
    reglas_s1 = pd.DataFrame([
        {"antecedente": "t_H08", "consecuente": "v_Alta", "soporte": 0.1,
         "confianza": 0.8, "lift": 2.0, "n_vars": 1},
    ])
    reglas_s2 = pd.DataFrame([
        {"antecedente": "t_H08", "consecuente": "v_Alta", "soporte": 0.1,
         "confianza": 0.8, "lift": 2.0, "n_vars": 1},
    ])
    reglas_s3 = pd.DataFrame([
        {"antecedente": "t_H09", "consecuente": "v_Media", "soporte": 0.1,
         "confianza": 0.7, "lift": 1.5, "n_vars": 1},
    ])

    reglas_por_sensor = {
        ("sensor1", "intensidad"): reglas_s1,
        ("sensor2", "intensidad"): reglas_s2,
        ("sensor3", "intensidad"): reglas_s3,
    }

    # Con umbral=1.0, solo debe aparecer si está en los 3 sensores
    comunes = patrones_compartidos(reglas_por_sensor, umbral=1.0)

    # La regla t_H08→v_Alta solo está en 2 de 3, por tanto NO debe aparecer
    assert len(comunes) == 0


def test_detectar_atipicos_marca_outlier():
    """Sensor con lift_medio muy alto → marcado como atípico"""
    tabla_cross = pd.DataFrame([
        {"Sensor": "s1", "Reglas": 10, "Conf. media (%)": 80, "Lift medio": 2.0, "Lift máx": 3.0},
        {"Sensor": "s2", "Reglas": 12, "Conf. media (%)": 82, "Lift medio": 2.1, "Lift máx": 3.2},
        {"Sensor": "s3", "Reglas": 15, "Conf. media (%)": 85, "Lift medio": 5.0, "Lift máx": 6.0},  # outlier
    ])

    atipicos = detectar_atipicos(tabla_cross)

    # s3 debe aparecer como atípico en Lift medio
    atipicos_s3 = [a for a in atipicos if a["sensor"] == "s3"]
    assert len(atipicos_s3) > 0
    assert any(a["metrica_global"] == "Lift medio" for a in atipicos_s3)


def test_construir_informe_global_estructura():
    """El markdown generado contiene las secciones esperadas"""
    # Crear datos de prueba mínimos
    reglas_s1 = pd.DataFrame([
        {"antecedente": "t_H08", "consecuente": "v_Alta", "soporte": 0.1,
         "confianza": 0.8, "lift": 2.0, "n_vars": 1},
    ])

    reglas_por_sensor = {("sensor1", "intensidad"): reglas_s1}

    from app.core.global_report.global_report import (
        construir_tabla_cross_sensor,
        detectar_atipicos,
        patrones_compartidos,
    )

    tabla_cross = construir_tabla_cross_sensor(reglas_por_sensor, HAY_HORAS=True, HAY_FRANJAS=True, HAY_DIAS=False)
    comunes = patrones_compartidos(reglas_por_sensor, umbral=0.5)
    atipicos = detectar_atipicos(tabla_cross)

    informe = construir_informe_global(
        tabla_cross=tabla_cross,
        comunes=comunes,
        atipicos=atipicos,
        reglas_por_sensor=reglas_por_sensor,
        NOMBRE_CONJUNTO="Dataset Test",
        METRICAS=["intensidad"],
        NOMBRE_METRICA_GLOBAL="intensidad",
        HAY_HORAS=True,
        HAY_FRANJAS=True,
    )

    # Verificar que contiene las secciones esperadas
    assert "# Informe Global Comparativo" in informe
    assert "## Tabla comparativa global" in informe
    assert "## Análisis técnico comparativo" in informe
    assert "### Patrones compartidos entre fuentes de datos" in informe
    assert "### Fuentes con comportamiento atípico" in informe
    assert "## Análisis detallado por fuente de datos" in informe
