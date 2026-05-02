import os
import sys

# Añade backend/ al path para que 'from app.*' funcione desde cualquier
# subdirectorio al ejecutar pytest.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
