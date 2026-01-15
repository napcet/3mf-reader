import sys
from pathlib import Path
# Garantir que o diretório do projeto esteja no sys.path para importar o pacote src
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extractor import ThreeMFExtractor

ex = ThreeMFExtractor('Bordeaux_The_Octopus.3mf')
summary = ex.extract()
ps = ex._project_settings
print('G-code:', ex._gcode_path)
print('\nRelevant keys and values:')
for k in sorted(ps.keys()):
    if 'initial' in k or 'layer' in k or 'speed' in k:
        print(f"{k} : {ps[k]}")
print('\nFull sample of initial related keys:')
for k in ['initial_layer_speed','initial_layer_print_height','initial_layer_print_speed','initial_layer_height']:
    print(k, ':', ps.get(k))
print('\nTotal keys count:', len(ps))