"""Screenshots of Start here > Teams > Installed tools against the fixture catalog (tests/test_catalog.py), light and
dark, phone and desktop width. Writes to benchmarks/runs/2026-11-17-trusted-catalog/shots/ (needs Playwright).

  python tests/shoot_tools_page.py
"""
import http.server
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
import test_catalog as tc  # noqa: E402
from lib import catalog, formserver, teams, toolhome  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = ROOT.parents[1] / '2026-11-17-trusted-catalog' / 'shots'


def main():
    tmp = Path(tempfile.mkdtemp(prefix='idli-shots-'))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), tc.Server)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update({'IDLI_TOOLS_HOME': str(tmp / 'tools'), 'IDLI_HOME': str(tmp),
                       'IDLI_CATALOG_URL': f'http://127.0.0.1:{srv.server_address[1]}'})
    res = {'platform': 'linux-aarch64', 'home': str(tmp), 'disk_free': 154 * tc.GB, 'ram': 121 * tc.GB,
           'cores': 20, 'gpu': 'nvidia'}
    folders = {}
    for tid, name in (('field-notes', 'Field Notes'), ('comms', 'Comms')):
        d = tmp / 'teams' / tid
        (d / 'extensions').mkdir(parents=True)
        (d / 'team.json').write_text('{"name": "%s"}' % name)
        folders[tid] = str(d)

    def fake_pixi(team, timeout=3600):
        e = toolhome.env_dir(team) / '.pixi'
        e.mkdir(parents=True, exist_ok=True)
        (e / 'blob').write_bytes(b'x' * (300 << 20 if team == 'comms' else 120 << 20))
        return True, '', []
    team_list = {'teams': [{'id': k, 'name': v} for k, v in (('field-notes', 'Field Notes'), ('comms', 'Comms'))]}
    with patch.object(toolhome, 'pixi_install', fake_pixi), patch.object(catalog, 'resources', return_value=res), \
            patch.object(teams, 'list_teams', return_value=team_list), \
            patch.object(teams, '_team_folder', side_effect=lambda t: folders.get(t)):
        toolhome.install(folders['field-notes'], ['office-files'])
        toolhome.install(folders['comms'], ['voice', 'office-files'])
        token = 'shots-token-0123456789abcdef'
        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), formserver.make_handler(
            formserver.Files(str(tmp)), token))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{httpd.server_address[1]}/tools?t={token}'
        OUT.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            for scheme in ('light', 'dark'):
                for width in (360, 860):
                    page = b.new_page(color_scheme=scheme, viewport={'width': width, 'height': 900})
                    page.goto(url)
                    page.wait_for_selector('.card h2')
                    page.screenshot(path=str(OUT / f'tools-by-tool-{scheme}-{width}.png'), full_page=True)
                    page.click('#byteam')
                    page.select_option('#team', 'field-notes')
                    page.select_option('#tool', 'huge-ram')
                    page.click('#check')
                    page.wait_for_selector('#verdict:not([hidden])')
                    page.screenshot(path=str(OUT / f'tools-by-team-check-{scheme}-{width}.png'), full_page=True)
                    page.select_option('#tool', 'voice')
                    page.click('#check')
                    page.wait_for_selector('#install:not([hidden])')
                    page.screenshot(path=str(OUT / f'tools-add-ok-{scheme}-{width}.png'), full_page=True)
                    sw = page.evaluate('document.documentElement.scrollWidth')
                    assert sw <= width, f'horizontal scroll at {width}: {sw}'
                    page.close()
            b.close()
        httpd.shutdown()
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
