"""Install representative tools from Idli's trusted catalog with plain pixi and check that they work.

Runs on Linux, macOS and Windows (GitHub Actions: .github/workflows/catalog-tools.yml). No silo access: models come
from each entry's public `source` URL and must match the catalog's sha256.

Usage: python tools.py GROUP [--out results.json]
  speech  voice-piper speaks a sentence, speech-whisper-small types it back, the words are checked
  ocr     ocr-tesseract reads a ruled table drawn with Pillow, the numbers are checked
  face    face-blur hides the astronaut's face in a photo and in a short video, the face region is checked

The install goes through cowork's own code (lib/catalog.check, lib/toolhome.write_manifest, pixi_install and
fetch_model), with IDLI_TOOLS_HOME in a work folder and IDLI_CATALOG_URL pointing at a local server that has no
files, so fetch_model falls back to the public source the way it would when silo has no copy.
"""
import argparse
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
REPO = HERE.parents[3]
COWORK = REPO / 'benchmarks' / 'runs' / '2026-11-06-oss-desktop-independent' / 'cowork'
CATALOG = RUN / 'catalog' / 'catalog.json'
EXAMPLES = RUN / 'catalog' / 'examples'
WORK = Path(os.environ.get('CATALOG_CI_WORK') or (HERE / 'work')).resolve()

sys.path.insert(0, str(COWORK))
from lib import catalog, toolhome  # noqa: E402

GROUPS = {'speech': ['voice-piper', 'speech-whisper-small'], 'ocr': ['ocr-tesseract'], 'face': ['face-blur']}

# The catalog's whisper-small.tar is our own archive of these four files (its sha256 can't be rebuilt from the
# public source, and its `source` is a Hugging Face folder page, not a file). These are the sha256 of the files
# inside the catalog's tar, checked on 2026-11-17 against the tar on silo and against Hugging Face.
WHISPER_REV = 'https://huggingface.co/Systran/faster-whisper-small/resolve/536b0662742c02347bc0e980a01041f333bce120/'
WHISPER_FILES = {
    'config.json': 'b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828',
    'model.bin': '3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671',
    'tokenizer.json': 'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab',
    'vocabulary.txt': '34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913',
}
# scikit-image's astronaut (NASA photo of Eileen Collins, public domain), pinned by release tag and sha256.
ASTRONAUT = ('https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png',
             '88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5')

SENTENCE = 'The quick brown fox jumps over the lazy dog near the river bank.'
HINDI = 'नमस्ते, आज मौसम बहुत अच्छा है।'


class NoFiles(http.server.BaseHTTPRequestHandler):
    """A catalog server with no files: every model falls back to its public source."""

    def do_GET(self):
        body = json.dumps(json.loads(CATALOG.read_text(encoding='utf-8'))).encode() \
            if self.path.endswith('/catalog.json') else b'{}'
        self.send_response(200 if self.path.endswith('/catalog.json') else 404)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, want):
    dest = Path(dest)
    if dest.exists() and sha256(dest) == want:
        return 'cached'
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'idli-ci'}),
                                        timeout=300) as r, open(str(dest) + '.part', 'wb') as out:
                shutil.copyfileobj(r, out, 1 << 20)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5)
    got = sha256(str(dest) + '.part')
    if got != want:
        os.remove(str(dest) + '.part')
        raise ValueError(f'{dest.name}: sha256 {got} is not {want}')
    os.replace(str(dest) + '.part', dest)
    return 'downloaded'


class Tool:
    def __init__(self, tid, cat, files):
        self.id, self.cat, self.files = tid, cat, files
        self.t = catalog.tools_by_id(cat)[tid]
        self.team = 'ci-' + tid
        self.r = {'tool': tid, 'install_ok': False, 'pass': False, 'notes': [], 'checks': []}

    def manifest(self):
        return toolhome.env_dir(self.team) / 'pixi.toml'

    def install(self):
        v = catalog.check([self.id], cat=self.cat, registry=[])
        self.r['check_ok'] = v['ok']
        if not v['ok']:
            self.r['notes'].append('catalog.check refused: ' + ' '.join(v['reasons']))
            return False
        toolhome.write_manifest(self.team, [self.id], self.cat)
        t0 = time.time()
        # Linux keeps Idli's bubblewrap wall in the product; on the CI runner we install it plainly like macOS and
        # Windows (the wall is tested elsewhere), so the three columns compare like for like.
        with patch.object(toolhome, 'walled', return_value=False):
            ok, tail, _ = toolhome.pixi_install(self.team, timeout=1500)
        self.r['install_s'] = round(time.time() - t0, 1)
        self.r['install_ok'] = ok
        if not ok:
            self.r['notes'].append('pixi install failed: ' + tail[-1500:])
            print(tail, flush=True)
            return False
        lock = self.manifest().parent / 'pixi.lock'
        self.r['lock_platforms'] = sorted(set(re.findall(r'^\s+(linux-64|linux-aarch64|osx-arm64|osx-64|win-64):\s*$',
                                                         lock.read_text(encoding='utf-8'), re.M)))
        t0 = time.time()
        for m in self.t.get('models') or []:
            self.fetch(m)
        self.r['models_s'] = round(time.time() - t0, 1)
        self.r['env_mb'] = round(toolhome.size(toolhome.env_dir(self.team)) / 2 ** 20)
        return True

    def fetch(self, m):
        """toolhome.fetch_model from the public source (sha256 checked), then the example's layout
        ($IDLI_FILES/models/<file>) as a copy."""
        if m.get('unpack') == 'tar' and '/tree/' in str(m.get('source')):
            # the catalog-only archive: fetch_model can't get it without silo (see WHISPER_FILES above)
            try:
                toolhome.fetch_model(m)
                self.r['notes'].append(f'unexpected: fetch_model got {m["file"]} from {m["source"]}')
            except ValueError as e:
                self.r['notes'].append(f'fetch_model without silo for {m["file"]}: "{e}" (expected: the source is '
                                       'a folder page, the tar exists only on silo)')
            folder = self.files / 'models' / Path(m['file']).name[:-4]
            for name, want in WHISPER_FILES.items():
                download(WHISPER_REV + name, folder / name, want)
            return
        p = toolhome.fetch_model(m)
        assert sha256(p) == m['sha256'], m['file']
        dest = self.files / m['file']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or sha256(dest) != m['sha256']:
            shutil.copyfile(p, dest)

    def run(self, *args, env=None, timeout=900):
        """`pixi run python ...` in the tool's environment, the way Idli runs a tool on macOS and Windows."""
        cache = toolhome.cache_dir()
        extra = {**toolhome._pixi_env(cache), 'IDLI_FILES': str(self.files), **(env or {})}
        cmd = [shutil.which('pixi'), 'run', '--manifest-path', str(self.manifest()), *args]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=WORK, env=toolhome._plain_env(extra))
        secs = round(time.time() - t0, 1)
        out = p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace')
        print(f'$ {" ".join(map(str, args))}  ({secs} s, exit {p.returncode})\n{out[-3000:]}', flush=True)
        return p.returncode, out, secs

    def check(self, name, ok, detail=''):
        self.r['checks'].append({'check': name, 'ok': bool(ok), 'detail': str(detail)[:600]})
        print(('PASS ' if ok else 'FAIL ') + name + (': ' + str(detail)[:300] if detail else ''), flush=True)
        return ok


def words(s):
    return re.findall(r"[a-z]+", s.lower())


def speech(cat, files):
    piper, whisper = Tool('voice-piper', cat, files), Tool('speech-whisper-small', cat, files)
    out = WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    if piper.install():
        t = 0
        code, log, s = piper.run('python', EXAMPLES / 'voice-piper.py', SENTENCE, out / 'en.wav', 'en_US-lessac-medium')
        t += s
        piper.check('English sentence spoken', code == 0 and (out / 'en.wav').exists()
                    and (out / 'en.wav').stat().st_size > 50_000, log[-300:])
        code, log, s = piper.run('python', EXAMPLES / 'voice-piper.py', HINDI, out / 'hi.wav', 'hi_IN-pratham-medium')
        t += s
        piper.check('Hindi sentence spoken', code == 0 and (out / 'hi.wav').exists()
                    and (out / 'hi.wav').stat().st_size > 30_000, log[-300:])
        piper.r['run_s'] = round(t, 1)
        piper.r['pass'] = all(c['ok'] for c in piper.r['checks'])
    if whisper.install():
        if not (out / 'en.wav').exists():
            whisper.check('English transcript', False, 'no speech file (voice-piper failed)')
        else:
            code, log, s = whisper.run('python', EXAMPLES / 'speech-whisper.py', out / 'en.wav', 'en', 'whisper-small')
            whisper.r['run_s'] = s
            heard = set(words(' '.join(line.split(']', 1)[1] for line in log.splitlines() if line.startswith('['))))
            want = set(words(SENTENCE)) - {'the'}
            hit = want & heard
            whisper.check('English transcript has the words', code == 0 and len(hit) >= 0.8 * len(want),
                          f'{len(hit)}/{len(want)} words; missing {sorted(want - hit)}; heard {sorted(heard)}')
            whisper.r['pass'] = all(c['ok'] for c in whisper.r['checks'])
        if (out / 'hi.wav').exists():  # Hindi round trip: reported, not a pass/fail gate (small is weak on Hindi)
            code, log, s = whisper.run('python', EXAMPLES / 'speech-whisper.py', out / 'hi.wav', 'hi', 'whisper-small')
            ok = code == 0 and any(ord(c) > 0x900 for c in log)
            whisper.r['notes'].append(f'Hindi transcript (not gated): exit {code}, ' + (
                'Devanagari text out' if ok else 'no Devanagari text: ' + log[-400:]))
            if code != 0 and 'UnicodeEncodeError' in log:
                code2, log2, _ = whisper.run('python', EXAMPLES / 'speech-whisper.py', out / 'hi.wav', 'hi',
                                             'whisper-small', env={'PYTHONUTF8': '1'})
                whisper.r['notes'].append('FINDING: the example crashes printing Hindi to a piped stdout '
                                          f'(UnicodeEncodeError); with PYTHONUTF8=1 it exits {code2}.')
    return [piper.r, whisper.r]


def ocr(cat, files):
    tool = Tool('ocr-tesseract', cat, files)
    out = WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    if not tool.install():
        return [tool.r]
    png, txt = out / 'table.png', out / 'text.png'
    code, log, t = tool.run('python', HERE / 'make_table.py', png, txt)
    if not tool.check('table and text images drawn with Pillow', code == 0 and png.exists(), log[-300:]):
        return [tool.r]
    numbers = json.loads(log.strip().splitlines()[-1])['numbers']
    for langs in ('eng', 'hin+mar+eng'):  # an empty OUT.xlsx argument means plain text in the example
        code, log, s = tool.run('python', EXAMPLES / 'ocr-tesseract.py', txt, '', langs)
        t += s
        found = [n for n in numbers if n in log]
        detail = f'{len(found)}/{len(numbers)}; missing {sorted(set(numbers) - set(found))}'
        if langs == 'eng':
            tool.check('plain text (eng) has the numbers', code == 0 and len(found) == len(numbers), detail)
        else:  # the example's default languages on English print: reported, not gated (a quality finding)
            tool.check('plain text (hin+mar+eng, the default) runs', code == 0, log[-200:])
            tool.r['notes'].append(f'default languages hin+mar+eng on English text: numbers {detail}')
    code, log, _ = tool.run('python', EXAMPLES / 'ocr-tesseract.py', png, '', 'eng')
    tool.r['notes'].append('plain mode on the ruled table (not gated): ' + (
        'read the numbers' if all(n in log for n in numbers) else 'did not read the numbers'))
    xlsx = out / 'table.xlsx'
    code, log, s = tool.run('python', EXAMPLES / 'ocr-tesseract.py', png, xlsx, 'eng')
    t += s
    tool.check('img2table found one table', code == 0 and '1 table(s) written' in log, log[-300:])
    code, log, s = tool.run('python', HERE / 'read_xlsx.py', xlsx)
    cells = log
    found = [n for n in numbers if n in cells]
    tool.check('the spreadsheet has the numbers', code == 0 and len(found) == len(numbers),
               f'{len(found)}/{len(numbers)}; missing {sorted(set(numbers) - set(found))}')
    tool.r['run_s'] = round(t, 1)
    tool.r['pass'] = all(c['ok'] for c in tool.r['checks'])
    return [tool.r]


def face(cat, files):
    tool = Tool('face-blur', cat, files)
    out = WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    if not tool.install():
        return [tool.r]
    src = files / 'inputs' / 'astronaut.png'
    download(*ASTRONAUT[:1], src, ASTRONAUT[1])
    code, log, t = tool.run('python', EXAMPLES / 'face-blur.py', src, out / 'astronaut-hidden.png', '--boxes')
    tool.check('photo: one face hidden', code == 0 and '1 face(s) hidden' in log, log[-300:])
    code, log, _ = tool.run('python', HERE / 'check_face.py', src, out / 'astronaut-hidden.png')
    tool.check('photo: face region changed, rest unchanged', code == 0 and 'OK' in log, log[-400:])
    clip = out / 'astronaut.mp4'
    code, log, _ = tool.run('ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-loop', '1', '-i', src,
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-t', '2', '-r', '10',
                            '-vf', 'scale=640:640', '-c:v', 'mpeg4', '-q:v', '3', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-shortest', clip)
    if tool.check('video: 2 s clip made with the env\'s ffmpeg', code == 0 and clip.exists(), log[-300:]):
        code, log, s = tool.run('python', EXAMPLES / 'face-blur.py', clip, out / 'astronaut-hidden.mp4')
        t += s
        m = re.search(r'(\d+) frames, faces found in (\d+) frame-faces', log)
        tool.check('video: faces found in most frames', code == 0 and m and int(m.group(1)) >= 15
                   and int(m.group(2)) >= int(m.group(1)) - 2, log[-300:])
        code, log, _ = tool.run('python', HERE / 'check_face.py', clip, out / 'astronaut-hidden.mp4')
        tool.check('video: face region changed, sound kept', code == 0 and 'OK' in log, log[-400:])
    tool.r['run_s'] = round(t, 1)
    tool.r['pass'] = all(c['ok'] for c in tool.r['checks'])
    return [tool.r]


def main():
    for stream in (sys.stdout, sys.stderr):  # Windows consoles are cp1252; tool output can be Hindi
        stream.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('group', choices=sorted(GROUPS))
    ap.add_argument('--out', default=str(WORK / 'results.json'))
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), NoFiles)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update({'IDLI_HOME': str(WORK / 'idli'), 'IDLI_TOOLS_HOME': str(WORK / 'tools'),
                       'IDLI_CATALOG_URL': f'http://127.0.0.1:{srv.server_address[1]}'})
    if not shutil.which('pixi'):
        sys.exit('pixi is not on PATH')
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    files = WORK / 'files'
    res = catalog.resources()
    rows = []
    try:
        rows = {'speech': speech, 'ocr': ocr, 'face': face}[a.group](cat, files)
    except Exception:
        rows.append({'tool': a.group, 'pass': False, 'notes': ['harness error: ' + traceback.format_exc()[-1500:]]})
        traceback.print_exc()
    pixi_v = subprocess.run([shutil.which('pixi'), '--version'], capture_output=True, text=True).stdout.strip()
    report = {'group': a.group, 'platform': catalog.platform(), 'runner': os.environ.get('RUNNER_NAME'),
              'image': os.environ.get('ImageOS'), 'pixi': pixi_v, 'python': sys.version.split()[0],
              'resources': {k: res[k] for k in ('platform', 'disk_free', 'ram', 'cores', 'gpu')}, 'tools': rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=1, ensure_ascii=True))
    srv.shutdown()
    sys.exit(0 if rows and all(r.get('pass') for r in rows) else 1)


if __name__ == '__main__':
    main()
