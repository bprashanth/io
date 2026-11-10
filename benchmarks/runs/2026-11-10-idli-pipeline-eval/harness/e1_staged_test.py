#!/usr/bin/env python3
"""Run a cowork test with staged filekit code, preserving cowork resource paths."""
from pathlib import Path
import os
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
COWORK=ROOT.parent/'2026-11-06-oss-desktop-independent/cowork'
sys.dont_write_bytecode=True
sys.path.insert(0,str(COWORK))
os.chdir(COWORK)
from lib import filekit
candidate=ROOT/'generators/e1_stage/filekit.py'
exec(compile(candidate.read_text(),filekit.__file__,'exec'),filekit.__dict__)
which=sys.argv[1] if len(sys.argv)>1 else 'test_mock_v2'
path=ROOT/'generators/e1_stage/test_mock_v2.py' if which=='test_mock_v2' else COWORK/'lib'/f'{which}.py'
runpy.run_path(str(path),run_name='__main__')
