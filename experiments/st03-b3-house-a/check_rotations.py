"""Check every template cell after strict placement on the pinned 26.3 server."""
import argparse
import hashlib
import json
from pathlib import Path
from tools.structure_export.live import FLAT, ROTATIONS, _at, _free_port, _template_cells, _text, rotate_props
from tools.structure_export.stair_live import make_server, forceload

ROOT = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server-jar', type=Path, required=True)
    ap.add_argument('--java', required=True)
    ap.add_argument('--work', type=Path, required=True)
    args = ap.parse_args()
    sha = hashlib.sha1(args.server_jar.read_bytes()).hexdigest()
    assert sha == '33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c'
    pack = args.work / 'pack'
    dest = pack / 'data/experimental/structure/house_a.nbt'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((ROOT/'experimental_house_a.nbt').read_bytes())
    (pack/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'experimental','min_format':[121,0],'max_format':[121,0]}}))
    cells = _template_cells(dest)
    server = make_server(args.work/'server', args.server_jar, args.java, pack)
    result = {'server_sha1':sha,'rotations':{}}
    try:
        server.start()
        forceload(server, 0, 0, 112, 32)
        for i, rotation in enumerate(ROTATIONS):
            origin = (16 + i*24, 80, 16)
            reply = server.cmd(f'place template experimental:house_a {origin[0]} {origin[1]} {origin[2]} {rotation} none 1 0 strict')
            if not reply.startswith('Loaded template'):
                raise RuntimeError(reply)
            failures = []
            for pos, (block, props) in sorted(cells.items()):
                p = _at(origin, pos, rotation)
                expected = _text(block, rotate_props(props, rotation))
                if 'passed' not in server.cmd(f'execute if block {p[0]} {p[1]} {p[2]} {expected}'):
                    failures.append({'pos':list(pos), 'expected':expected})
            result['rotations'][rotation] = {'cells':len(cells), 'failures':failures}
            print(rotation, len(cells), len(failures), flush=True)
    finally:
        server.stop()
    (ROOT/'rotation-cell-result.json').write_text(json.dumps(result, indent=2)+'\n')
    if any(v['failures'] for v in result['rotations'].values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
