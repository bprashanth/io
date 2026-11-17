"""cowork's lib/catalog.py on the real computer it runs on (Linux, macOS, Windows), against the real catalog.json.

    EXPECT_PLATFORM=osx-arm64 python test_catalog_lib.py -v

No network: the catalog is passed in. Writes what it measured to $CATALOG_CI_WORK/lib.json for the results table.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
COWORK = REPO / 'benchmarks' / 'runs' / '2026-11-06-oss-desktop-independent' / 'cowork'
CATALOG = json.loads((HERE.parent / 'catalog' / 'catalog.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(COWORK))
from lib import catalog, toolhome  # noqa: E402

GB = 1024 ** 3
SEEN = {}
REPRESENTATIVE = ['speech-whisper-small', 'voice-piper', 'ocr-tesseract', 'face-blur']


def other_ram():
    """Total memory measured a second way, not through catalog._ram_bytes."""
    if sys.platform.startswith('linux'):
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    if sys.platform == 'darwin':
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'],
                         capture_output=True, text=True, timeout=60).stdout
    return int(out.strip())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='idli-ci-'))
        self.env = patch.dict(os.environ, {'IDLI_HOME': str(self.tmp), 'IDLI_TOOLS_HOME': str(self.tmp / 'tools'),
                                           'IDLI_CATALOG_URL': 'http://127.0.0.1:9'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)


class ThisComputer(Base):
    def test_platform_string(self):
        p = catalog.platform()
        SEEN['platform'] = p
        self.assertIn(p, catalog.PLATFORM_WORDS)
        if os.environ.get('EXPECT_PLATFORM'):
            self.assertEqual(p, os.environ['EXPECT_PLATFORM'])

    def test_ram_is_real_and_matches_a_second_measure(self):
        ram = catalog._ram_bytes()
        SEEN['ram_gb'] = round(ram / GB, 2)
        self.assertGreater(ram, 2 * GB)
        self.assertLess(ram, 4096 * GB)
        other = other_ram()
        SEEN['ram_gb_other'] = round(other / GB, 2)
        self.assertLess(abs(ram - other) / other, 0.05, (ram, other))

    def test_ram_path_per_os(self):
        """The OS-specific branch answers by itself, not the sysconf fallback."""
        if sys.platform == 'darwin':
            out = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout
            self.assertEqual(catalog._ram_bytes(), int(out.strip()))
        if sys.platform.startswith('win'):
            self.assertFalse(hasattr(os, 'sysconf'))  # no fallback on Windows
            self.assertGreater(catalog._ram_bytes(), 0)  # so it came from GlobalMemoryStatusEx (ctypes)

    def test_resources_are_sane(self):
        r = catalog.resources()
        SEEN['resources'] = {**r, 'disk_free_gb': round(r['disk_free'] / GB, 1)}
        self.assertEqual(r['platform'], catalog.platform())
        self.assertGreater(r['disk_free'], 1 * GB)
        self.assertLessEqual(r['disk_free'], shutil.disk_usage(self.tmp).total)
        self.assertEqual(r['cores'], os.cpu_count())
        self.assertGreaterEqual(r['cores'], 2)
        self.assertTrue(Path(r['home']).is_relative_to(self.tmp), r['home'])
        self.assertEqual(r['gpu'], 'apple' if sys.platform == 'darwin' else (
            'nvidia' if shutil.which('nvidia-smi') else None))
        text = catalog.describe_computer(r)
        self.assertIn(f"({r['platform']})", text)
        self.assertIn('Free disk where tools go', text)

    def test_default_tools_home_is_under_the_user_folder(self):
        user = self.tmp / 'user'
        with patch.dict(os.environ, {'IDLI_TOOLS_HOME': '', 'IDLI_HOME': '', 'HOME': str(user),
                                     'USERPROFILE': str(user)}):
            h = catalog.tools_home()
            envs = catalog.envs_home()
        SEEN['default_tools_home'] = str(h)
        self.assertTrue(h.is_absolute(), h)
        self.assertEqual(h, user / 'idli-insights' / 'tools')
        self.assertEqual(envs, user / 'idli-insights' / 'tools' / 'envs')

    def test_environments_folder_on_this_disk(self):
        SEEN['links_ok'] = catalog._links_ok(self.tmp)
        self.assertEqual(catalog.envs_home(), self.tmp / 'tools' / 'envs')


class RealCatalog(Base):
    def test_every_tool_lists_and_fits_this_platform(self):
        res = catalog.resources()
        verdicts = {}
        for t in CATALOG['tools']:
            v = catalog.check([t['id']], cat=CATALOG, res=res, registry=[])
            verdicts[t['id']] = {'ok': v['ok'], 'reasons': v['reasons'], 'notes': v['tools'][t['id']]['notes']}
            self.assertFalse([r for r in v['reasons'] if "doesn't run on this computer" in r], t['id'])
        SEEN['verdicts'] = verdicts
        for tid in REPRESENTATIVE:
            self.assertTrue(verdicts[tid]['ok'], (tid, verdicts[tid]))

    def test_a_tool_not_listing_this_platform_is_refused(self):
        res = catalog.resources()
        plat = res['platform']
        cat = copy.deepcopy(CATALOG)
        for t in cat['tools']:
            t['platforms'] = [p for p in t['platforms'] if p != plat]
        for tid in REPRESENTATIVE:
            v = catalog.check([tid], cat=cat, res=res, registry=[])
            self.assertFalse(v['ok'], tid)
            self.assertIn(f"doesn't run on this computer ({catalog.PLATFORM_WORDS[plat]})", v['reasons'][0])
        rows, other = catalog.fitting(cat=cat, res=res, registry=[])
        self.assertEqual((rows, other), ([], len(cat['tools'])))
        rows, other = catalog.fitting(cat=CATALOG, res=res, registry=[])
        self.assertEqual((len(rows), other), (len(CATALOG['tools']), 0))

    def test_too_little_memory_or_disk_is_refused(self):
        res = {**catalog.resources(), 'ram': int(0.5 * GB), 'disk_free': int(2.5 * GB)}
        v = catalog.check(['speech-whisper-small'], cat=CATALOG, res=res, registry=[])
        self.assertFalse(v['ok'])
        self.assertTrue(any('needs 1 GB of memory' in r for r in v['reasons']), v['reasons'])
        self.assertTrue(any('Not enough free disk' in r for r in v['reasons']), v['reasons'])

    def test_manifest_for_the_representative_tools(self):
        by = catalog.tools_by_id(CATALOG)
        for tid in REPRESENTATIVE:
            text = toolhome.manifest_text('ci', [by[tid]])
            self.assertIn(catalog.platform(), text)
        text = toolhome.manifest_text('ci', [by[t] for t in REPRESENTATIVE])  # one team using all four
        self.assertIn('faster-whisper', text)
        f = toolhome.write_manifest('ci-team', REPRESENTATIVE, CATALOG)
        self.assertEqual(f.read_text(encoding='utf-8'), text.replace('idli-ci"', 'idli-ci-team"'))


def tearDownModule():
    out = Path(os.environ.get('CATALOG_CI_WORK') or HERE / 'work') / 'lib.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(SEEN, indent=1, default=str), encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
