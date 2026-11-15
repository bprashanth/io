"""Claude's masked copies: same layout and types as the real file, no real private value anywhere, and Mini scripts
written against the copies give the same answer on the real file once Idli puts the values back."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib import filekit, launchsettings, maskcopy, privacy  # noqa: E402

REL = 'drive/My Drive/shola_plots.xlsx'


@pytest.fixture
def shola(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:9/none')  # regex only; no network in tests
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    data, work = tmp_path / 'data', tmp_path / 'home/idli-insights/claude-masked'
    (data / 'drive/My Drive').mkdir(parents=True)
    work.mkdir(parents=True)
    subprocess.run([sys.executable, str(ROOT / 'tests/make_shola_fixture.py'), str(data / REL)], check=True)
    sheets, _ = filekit.raw_sheets(str(data / REL))
    columns = {c: c in ('sppnam', 'Site', 'Recorder') for frame in sheets.values() for c in frame.columns}
    privacy.set(data, REL, mode='mask', review='ask', columns=columns)
    return data, work


def all_text(path):
    with zipfile.ZipFile(path) as z:
        return ' '.join(z.read(n).decode('utf-8', 'ignore') for n in z.namelist())


def test_copy_keeps_layout_and_hides_every_private_value(shola):
    data, work = shola
    maskcopy.build(data, work)
    real = pd.read_excel(data / REL, sheet_name=None)
    copy = pd.read_excel(work / REL, sheet_name=None)
    assert list(real) == list(copy)
    for name in real:
        assert real[name].shape == copy[name].shape
        assert list(real[name].columns) == list(copy[name].columns)  # repeated header rows don't code the heading
    trees_real, trees_copy = real['Raw 10x10m Data'], copy['Raw 10x10m Data']
    assert (trees_real['gbh_cm'] == trees_copy['gbh_cm']).all() and trees_copy['gbh_cm'].dtype == float
    assert trees_copy['sppnam'].str.match(r'^[A-Z]+_\d{3}$').all()
    text = all_text(work / REL)
    for real_value in ('cesaur', 'rapcap', 'ageade', 'Bikkapathimund', 'Meena Raghavan', 'Arjun Bellie'):
        assert real_value not in text
    # A recorder named in free text elsewhere (the Read me) is coded too.
    assert 'Meena' not in text
    # Searching the copy for guessed names (what Claude did on the real file) finds nothing.
    saps = copy['2x2m Seedlings and saplings']
    assert not saps.astype(str).apply(lambda c: c.str.contains('ageade|cesaur|lantana', case=False)).any().any()


def test_copies_only_reviewed_files_and_replaces_old_link(shola):
    data, work = shola
    (data / 'drive/My Drive/other.csv').write_text('name,phone\nAsha Rao,9876543210\n')
    (work / 'drive').symlink_to(data / 'drive')
    maskcopy.build(data, work)
    assert not (work / 'drive').is_symlink()
    assert (work / REL).is_file() and not (work / 'drive/My Drive/other.csv').exists()
    assert json.loads((work / 'drive' / maskcopy.MANIFEST).read_text())['files'] == [REL]
    assert (data / 'drive/My Drive/other.csv').is_file()  # the real download is untouched


def test_mini_script_from_copy_runs_on_real_file(shola, tmp_path):
    data, work = shola
    maskcopy.build(data, work)
    vault = privacy.session_vault(data)
    code = vault.forward[privacy.normalise('rapcap')]
    script = (f'import pandas as pd\n# trees of {code}\n'
              f'd = pd.read_excel("drive/My Drive/shola_plots.xlsx", "Raw 10x10m Data")\n'
              f'SP = "{code}"\nprint(d[d.sppnam == SP].gbh_cm.max(), (d.sppnam == f"{code}").sum())\n')
    (work / 'q.py').write_text(script)
    on_copy = subprocess.run([sys.executable, 'q.py'], cwd=work, capture_output=True, text=True, check=True).stdout
    text, n = maskcopy.rehydrate_script(script, vault)
    assert n == 2 and f'# trees of {code}' in text and '"rapcap"' in text
    run = tmp_path / 'mini'
    run.mkdir()
    (run / 'drive').symlink_to(data / 'drive')
    (run / 'q.py').write_text(text)
    on_real = subprocess.run([sys.executable, 'q.py'], cwd=run, capture_output=True, text=True, check=True).stdout
    assert on_copy == on_real and float(on_real.split()[0]) > 0


def test_rehydrate_escapes_quotes(shola):
    data, _ = shola
    vault = privacy.session_vault(data)
    code = vault.token('Rao\'s "farm"', 'village')
    text, n = maskcopy.rehydrate_script(f"a = '{code}'\nb = \"{code} x\"\n", vault)
    ns = {}
    exec(text, ns)
    assert n == 2 and ns['a'] == 'Rao\'s "farm"' and ns['b'] == 'Rao\'s "farm" x'


def test_reveal_shows_the_value_in_the_copy(shola, monkeypatch):
    data, work = shola
    maskcopy.build(data, work)
    vault = privacy.session_vault(data)
    code = vault.forward[privacy.normalise('Avalanche')]
    monkeypatch.setattr(privacy, 'revealed_values', lambda *a, **k: {code: 'Avalanche'})
    maskcopy.build(data, work)
    sites = pd.read_excel(work / REL, 'Raw 10x10m Data')['Site']
    assert 'Avalanche' in set(sites) and 'Bikkapathimund' not in set(sites)


def test_sandbox_settings_hide_private_folders(shola):
    data, work = shola
    (work.parent / 'cowork-real').mkdir()
    (work.parent / 'Claude-masked').mkdir()  # differs only in case: denying it would hide Claude's own folder
    stale = str((work.parent / 'Claude-masked').resolve())
    (work / '.claude').mkdir()
    (work / '.claude/settings.json').write_text(json.dumps({'permissions': {'deny': [f'Read(/{stale}/**)', 'Bash(rm:*)']},
                                                            'sandbox': {'filesystem': {'denyRead': [stale]}}}))
    launchsettings.merge(work, data)
    s = json.loads((work / '.claude/settings.json').read_text())
    deny = s['sandbox']['filesystem']['denyRead']
    assert str(data.resolve()) in deny and str((work.parent / 'cowork-real').resolve()) in deny
    assert str(work.resolve()) not in deny
    assert stale not in deny and f'Read(/{stale}/**)' not in s['permissions']['deny']
    assert 'Bash(rm:*)' in s['permissions']['deny']  # other rules are kept
    assert s['sandbox']['enabled'] and s['sandbox']['allowUnsandboxedCommands'] is False
    assert f'Read(/{data.resolve()}/**)' in s['permissions']['deny']
    assert 'mcp__idli__unmask' in s['permissions']['ask']


def test_species_columns_are_contextual():
    assert privacy.column_class('sppnam') == 'contextual'
    assert privacy.column_class('species') == 'contextual'
    assert privacy.column_class('Recorder') == 'personal'


def test_short_numbers_are_not_matched_in_text():
    vault = privacy.PseudonymMap()
    for real in ('6', '120', '1200', '9876543210', '11.41234', 'Asha Rao'):
        vault.token(real, 'value')
    out, found = privacy._known('Asha Rao: 6 trees, 120 cm, Rs 1200, call 9876543210 at 11.41234', vault)
    assert '6 trees' in out and '120 cm' in out  # counts stay readable for Claude
    assert 'Rs 1200' not in out
    assert 'Asha Rao' not in out and '9876543210' not in out and '11.41234' not in out
    assert privacy.known_leaks('6 trees and 120 cm', vault) == []
    assert privacy.known_leaks('call 9876543210', vault) == ['9876543210']


def test_count_columns_are_suggested_visible_ids_are_not(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:9/none')
    path = tmp_path / 'hh.csv'
    path.write_text('household_size,Phone,hh_id,Head\n' + ''.join(
        f'{n % 7 + 1},98765432{n:02d},{n},{name}\n' for n, name in enumerate(
            ['Asha Rao', 'Ravi Kumar', 'Meena Iyer', 'John Mathew', 'Lakshmi Devi'])))
    rows = {r['column']: r for r in privacy._suggest(path, None)}
    assert rows['household_size']['mask'] is False
    assert rows['Phone']['mask'] and rows['hh_id']['mask'] and rows['Head']['mask']


def test_species_key_and_unnamed_column_stay_contextual(tmp_path, monkeypatch):
    """Laptop 2026-11-15: "Species name expanded" read as a person's name, and the same species in a column without
    a heading (column_22) counted as personal, so a species reveal was refused."""
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:9/none')
    data = tmp_path / 'data'
    data.mkdir()
    import openpyxl
    book = openpyxl.Workbook()
    trees = book.active
    trees.title = 'Trees'
    for row in [['sppnam', 'gbh', None], ['syzden', 120, 'Syzygium densiflorum'], ['rapcap', 30, None],
                ['syzden', 95, None], ['rapcap', 41, None]]:
        trees.append(row)
    key = book.create_sheet('Read me')
    for row in [['Species name expanded', 'Recorder'], ['Syzygium densiflorum', 'Meena Raghavan'],
                ['Rapanea capitellata', 'Arjun Bellie']]:
        key.append(row)
    book.save(data / 'f.xlsx')
    sheets, _ = filekit.raw_sheets(str(data / 'f.xlsx'))
    assert any(str(c).startswith('column_') for c in sheets['Trees'].columns), list(sheets['Trees'].columns)
    columns = {str(c): True for f in sheets.values() for c in f.columns}
    privacy.set(data, 'f.xlsx', mode='mask', review='ask', columns=columns)
    vault = privacy.session_vault(data)
    index = privacy.code_index(data, vault)
    assert index[vault.forward[privacy.normalise('Syzygium densiflorum')]]['class'] == 'contextual'
    assert index[vault.forward[privacy.normalise('syzden')]]['class'] == 'contextual'
    assert index[vault.forward[privacy.normalise('Meena Raghavan')]]['class'] == 'personal'
    # An older vault coded a species key as NAME_; one such code must not make its whole column personal.
    old = vault.token('Ilex wightiana', 'person_name')
    book = openpyxl.load_workbook(data / 'f.xlsx')
    book['Read me'].append(['Ilex wightiana', 'Kavya Shenoy'])
    book.save(data / 'f.xlsx')
    privacy._save(vault)
    vault = privacy.session_vault(data)
    index = privacy.code_index(data, vault)
    assert old.startswith('NAME_') and index[old]['class'] == 'contextual'
    assert index[vault.forward[privacy.normalise('Syzygium densiflorum')]]['class'] == 'contextual'
    assert index[vault.forward[privacy.normalise('Kavya Shenoy')]]['class'] == 'personal'


def test_old_heading_codes_no_longer_hide_headings(shola):
    """An older vault coded the repeated header "sppnam" as a value; the copy then showed the heading as a code."""
    data, work = shola
    vault = privacy.session_vault(data)
    junk = vault.token('sppnam', 'value')
    book = __import__('openpyxl').load_workbook(data / REL)
    book['Read me'].append(['sppnam', 'is the species code'])  # also a cell, in a column without a heading
    book.save(data / REL)
    person = vault.token('Recorder', 'person_name')  # a NAME_ code stays masked whatever it stands for
    privacy._save(vault)
    maskcopy.build(data, work)
    copy = pd.read_excel(work / REL, sheet_name='Raw 10x10m Data')
    assert junk.startswith('VALUE_') and 'sppnam' in copy.columns
    assert 'Recorder' not in copy.columns and person in copy.columns
    assert copy['sppnam'].str.match(r'^[A-Z]+_\d{3}$').all()  # the species themselves stay hidden


def test_product_words_never_masked_even_if_an_old_vault_has_them():
    """Laptop 2026-11-15: an old scanner false positive left NAME_007 = "Claude" in the vault; the close-match step
    turned Claude's folder path into ~/idli-insights/NAME_007-masked and Claude wrote files there."""
    vault = privacy.PseudonymMap()
    vault.token('Claude', 'person_name')
    vault.token('Meena Raghavan', 'person_name')
    text = 'cd /home/x/idli-insights/claude-masked && python3 q.py  # Meena Raghavan'
    out = privacy._redact(text, vault, lambda t: [])[0]
    assert '/claude-masked' in out and 'Meena' not in out
    assert privacy.known_leaks(out, vault) == []
