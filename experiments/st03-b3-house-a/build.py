"""PROPOSED experiment: generate one house A template; not a production asset."""
from pathlib import Path
import json
import shutil
import tempfile

from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
SIZE = (9, 10, 7)  # x, y, z

def design():
    cells = {}
    def put(x, y, z, block, **props):
        assert 0 <= x < 9 and 0 <= y < 10 and 0 <= z < 7
        cells[(x, y, z)] = ('minecraft:' + block, props)
    for x in range(9):
        for z in range(7):
            put(x, 0, z, 'cobblestone' if x in (0, 8) or z in (0, 6) else 'dark_oak_planks')
    for y in range(1, 5):
        for x in range(9):
            for z in range(7):
                if x in (0, 8) or z in (0, 6):
                    block = 'cobblestone' if y == 1 else ('dark_oak_log' if x in (0, 8) and z in (0, 6) else 'dark_oak_planks')
                    put(x, y, z, block, **({'axis': 'y'} if block == 'dark_oak_log' else {}))
    for y in (2, 3):
        for x, z in [(0, 2), (0, 4), (8, 2), (8, 4), (2, 0), (6, 0), (2, 6), (6, 6)]:
            put(x, y, z, 'glass_pane')
    for y, half in ((1, 'lower'), (2, 'upper')):
        put(4, y, 6, 'dark_oak_door', facing='south', half=half, hinge='left', open='false', powered='false')
    # Closed attic floor and gable end infill. Roof slope runs toward x=4.
    for x in range(1, 8):
        for z in range(1, 6):
            put(x, 5, z, 'dark_oak_planks')
    for y in range(5, 9):
        for x in range(y - 4, 13 - y):
            for z in (0, 6):
                put(x, y, z, 'dark_oak_planks')
    for x in range(9):
        y = 5 + min(x, 8 - x)
        for z in range(7):
            if x == 4:
                put(x, y, z, 'dark_oak_planks')
            else:
                put(x, y, z, 'dark_oak_stairs', facing='east' if x < 4 else 'west', half='bottom', shape='straight')
    # Design-package decor: five cells including the two bed parts.
    put(1, 1, 1, 'red_bed', facing='east', occupied='false', part='foot')
    put(2, 1, 1, 'red_bed', facing='east', occupied='false', part='head')
    put(7, 1, 1, 'crafting_table')
    put(7, 1, 3, 'furnace', facing='west', lit='false')
    put(1, 1, 5, 'barrel', facing='east', open='false')
    put(4, 4, 3, 'lantern', hanging='true')
    return cells

def main():
    cells = design()
    ROOT.joinpath('proposed-cells.json').write_text(json.dumps({'status':'PROPOSED', 'size':list(SIZE), 'air':'include', 'cells':[{'pos':list(p),'block':b,'properties':s} for p,(b,s) in sorted(cells.items(), key=lambda item:(item[0][1],item[0][2],item[0][0]))]}, indent=2)+'\n')
    module = {'id':'st03_house_a', 'file':'experimental_house_a', 'size':list(SIZE), 'air':'include'}
    with tempfile.TemporaryDirectory() as d:
        result = export_module(module, cells, Path(d)/'pack')
        shutil.copyfile(result.config.nbt_path, ROOT/'experimental_house_a.nbt')
        shutil.copyfile(result.config.source, ROOT/'experimental_house_a.schem')
        ROOT.joinpath('export-report.json').write_text(json.dumps(result.report, indent=2, sort_keys=True)+'\n')
    print(f'Generated {len(cells)} non-air cells; experimental only')

if __name__ == '__main__':
    main()
