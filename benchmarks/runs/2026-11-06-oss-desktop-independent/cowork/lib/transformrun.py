"""Runs one transform block in its own process (lib/transforms.py): its fake-data test, or a run on real files.

    python -I transformrun.py test|run <block folder> <sandbox or ''> <args.json> <out.json>
"""
import importlib.util
import inspect
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.transformkit import Kit  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call_run(block, kit, args):
    params = inspect.signature(block.run).parameters
    if not any(p.kind == p.VAR_KEYWORD for p in params.values()):
        args = {k: v for k, v in args.items() if k in params}
    return block.run(kit, **args)


def where(tb, folder):
    for fr in reversed(traceback.extract_tb(tb)):
        if fr.filename.startswith(str(folder)):
            return f' ({Path(fr.filename).name} line {fr.lineno})'
    return ''


def main():
    mode, folder, sandbox, args_path, out_path = sys.argv[1:6]
    folder = Path(folder).resolve()
    a = json.loads(Path(args_path).read_text())
    try:
        block = load(folder / 'block.py', 'idli_block')
        if mode == 'test':
            kit = Kit('test', folder)
            load(folder / 'test_block.py', 'idli_block_test').test(kit, lambda **kw: call_run(block, kit, kw))
            out = {'ok': True}
        else:
            kit = Kit('run', folder, sandbox, a.get('args'), a.get('files'), os.environ['IDLI_MODEL_URL'])
            out = {'ok': True, 'result': call_run(block, kit, a.get('args') or {})}
    except AssertionError as e:
        out = {'ok': False, 'error': 'a check did not hold' + (f': {e}' if str(e) else '') + where(e.__traceback__,
                                                                                                     folder)}
    except Exception as e:  # noqa: BLE001
        out = {'ok': False, 'error': f'{type(e).__name__}: {e}'[:300] + where(e.__traceback__, folder)}
    Path(out_path).write_text(json.dumps(out, default=str, ensure_ascii=False))


if __name__ == '__main__':
    main()
