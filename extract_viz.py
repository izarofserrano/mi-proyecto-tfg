import json
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

with open('notebooks/src03_Generacion_Lenguaje_Natural_2 (4).ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

with open('viz_functions.txt', 'w', encoding='utf-8') as out:
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if 'def generar_heatmap' in source or 'def grafica_barras_lift' in source or 'def grafica_scatter' in source or 'def tabla_consecuentes' in source:
                out.write(f'=== CELL {i} ===\n')
                out.write(source)
                out.write('\n' + '='*80 + '\n\n')

print("Extracted to viz_functions.txt")
