"""The query service path: only masked text leaves, only one read-only SELECT runs, real values come back locally."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib import filekit, minisql, privacy  # noqa: E402

REL = 'drive/My Drive/shola_plots.xlsx'
REAL = ['Meena Raghavan', 'Arjun Bellie', 'Kavya Shenoy', 'Joseph Mathan', 'Bikkapathimund', 'Avalanche', 'Korakundah',
        'cesaur', 'rapcap', 'lancam']


@pytest.fixture
def shola(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:9/none')
    data = tmp_path / 'data'
    (data / 'drive/My Drive').mkdir(parents=True)
    subprocess.run([sys.executable, str(ROOT / 'tests/make_shola_fixture.py'), str(data / REL)], check=True)
    sheets, _ = filekit.raw_sheets(str(data / REL))
    columns = {c: c in ('sppnam', 'Site', 'Recorder') for f in sheets.values() for c in f.columns}
    privacy.set(data, REL, mode='mask', review='ask', columns=columns)
    privacy.session_vault(data)
    return data


def fake(reply, seen):
    def call(body):
        seen.append(body)
        return reply
    return call


def test_only_codes_leave_and_real_values_come_back(shola):
    vault = privacy.session_vault(shola)
    site = vault.forward[privacy.normalise('Avalanche')]
    rap = vault.forward[privacy.normalise('rapcap')]
    seen = []
    sql = (f'SELECT "sppnam", COUNT(*) AS trees FROM "raw_10x10m_data" WHERE "Site" = \'{site}\' '
           f'AND "gbh_cm" > 100 GROUP BY "sppnam" ORDER BY trees DESC')
    r = minisql.answer(shola, [REL], 'Which species have big trees at Avalanche? Is rapcap one?',
                       call=fake({'sql': sql, 'title': f'Big trees at {site}', 'note': 'Girth over 100 cm.'}, seen))
    sent = json.dumps(seen[0])
    for value in REAL:
        assert value not in sent
    assert site in sent and rap in sent and '"gbh_cm": number' in seen[0]['messages'][1]['content']  # codes and columns go
    assert r['kind'] == 'table' and r['title'] == 'Big trees at Avalanche'
    assert 'rapcap' in set(r['frame']['sppnam'])  # real values in the local answer
    assert r['frame']['trees'].sum() > 0
    assert seen[0].get('provider', {}).get('data_collection') == 'deny'


def test_clarify_options_come_back_real(shola):
    vault = privacy.session_vault(shola)
    site = vault.forward[privacy.normalise('Avalanche')]
    r = minisql.answer(shola, [REL], 'big trees at Avalanche', call=fake(
        {'clarify': 'What counts as big?', 'options': [f'Trees over 100 cm girth at {site}?', 'The 10 tallest?']}, []))
    assert r['kind'] == 'clarify' and r['options'][0]['question'] == 'Trees over 100 cm girth at Avalanche?'


@pytest.mark.parametrize('sql', [
    'SELECT 1; SELECT 2',
    'DELETE FROM "raw_10x10m_data"',
    "COPY (SELECT 1) TO '/tmp/x.csv'",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM '/etc/passwd'",
    "ATTACH '/tmp/x.db' AS x",
    'PRAGMA version',
    "SELECT getenv('HOME')",
])
def test_unsafe_queries_are_refused(shola, sql):
    with pytest.raises(Exception):
        tables = minisql.load(shola, [REL])
        minisql.run(tables, minisql.check_sql(sql))


def test_file_access_is_off_even_if_a_check_missed_it(shola):
    tables = minisql.load(shola, [REL])
    with pytest.raises(Exception):
        minisql.run(tables, "SELECT * FROM '/etc/hostname'")


def test_words_inside_literals_and_identifiers_are_fine(shola):
    tables = minisql.load(shola, [REL])
    sql = minisql.check_sql('SELECT COUNT(*) AS n FROM "raw_10x10m_data" WHERE "sppnam" = \'load\'')
    assert int(minisql.run(tables, sql)['n'][0]) == 0


def test_repeated_header_rows_dropped_and_numbers_typed(shola):
    tables = minisql.load(shola, [REL])
    frame = tables['2x2m_seedlings_and_saplings'][1]
    assert 'sppnam' not in set(frame['sppnam'].astype(str))
    assert str(frame['numsee'].dtype).startswith(('int', 'float', 'Int', 'Float'))
