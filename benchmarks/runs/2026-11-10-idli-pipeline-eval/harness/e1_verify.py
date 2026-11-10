#!/usr/bin/env python3
"""Independent E1 checks: default equivalence and basic report integrity."""
from collections import Counter
import json
import os
from pathlib import Path
import sys
import tempfile
import types

ROOT=Path(__file__).resolve().parents[1]
COWORK=ROOT.parent/'2026-11-06-oss-desktop-independent/cowork'
sys.dont_write_bytecode=True
sys.path.insert(0,str(COWORK))
from lib import filekit as staged
import openpyxl

original=types.ModuleType('e1_original')
original.__file__=staged.__file__
exec(compile(Path(original.__file__).read_text(),original.__file__,'exec'),original.__dict__)
exec(compile((ROOT/'generators/e1_stage/filekit.py').read_text(),staged.__file__,'exec'),staged.__dict__)
os.environ.pop('IDLI_MOCK_V2',None)
os.chdir(COWORK)

with tempfile.TemporaryDirectory() as temp:
    for lib,label in [(original,'original'),(staged,'staged')]:
        lib.TEACH_DIR=str(Path(temp)/label)
        lib.SKILLS_DIR=str(Path(temp)/'no-skills')
    for path in sorted((ROOT/'fixtures').glob('*.xlsx')):
        requests=[]; values=[]
        for lib in (original,staged):
            req,mock,_=lib.make_mock(str(path),'Check the workbook',seed=7)
            requests.append({k:v for k,v in req.items() if k not in {'id','created'}})
            wb=openpyxl.load_workbook(mock,data_only=True)
            values.append({s.title:list(s.values) for s in wb if s.title!=lib.WATERMARK})
            wb.close()
        assert requests[0]==requests[1], path.name
        assert values[0]==values[1], path.name
        print('ok  default unchanged:',path.stem)

for label in ('today','fixed'):
    reports=list((ROOT/'results/e1'/label).glob('*.json'))
    assert len(reports)==5
    for path in reports:
        r=json.loads(path.read_text())
        assert all(x['real'] for x in r['kinds'].values()), (path,'detector missed real kind')
        assert set(r['kinds'])=={i['kind'] for i in r['items']}
        assert r['columns'] and r['relationships']
        for relation in r['relationships']:
            if relation['type']=='cross_tab_count':
                for side in ('real','fake'):
                    v=relation[side]
                    assert v['matching']+v['mismatching']==v['rows']
                    assert abs(v['match_share']+v['mismatch_share']-1)<1e-9
                if label=='fixed':
                    assert relation['fake']['match_share']>.9
                    assert relation['fake']['mismatching']>0
    print('ok  report integrity:',label)
print('ALL PASSED')
