"""The platform's capability menu: what a team extension may use, cheapest first (narrative/MODEL_TYPES.md).

Extensions import this module inside Idli's sandbox (no network, read-only filesystem), so everything here is local.
The private-model and outside rows of the menu are reached through the platform, never from extension code.
Nothing here installs anything: a missing tool is a platform request, not a pip install.
"""
import csv
import importlib.util
import os
import shutil
import subprocess

# need -> options, cheapest first. 'how' is what an extension calls; 'check' says if this computer has it.
MENU = {
    'ocr': [
        {'tier': 'local', 'name': 'Tesseract', 'how': 'capmenu.ocr_text(path) / capmenu.ocr_words(path)',
         'check': lambda: bool(shutil.which('tesseract'))},
        {'tier': 'private model', 'name': 'Muse (vision)', 'how': 'platform request: not open to extensions yet',
         'check': lambda: False},
        {'tier': 'outside', 'name': 'Consultant, on masked text after OCR', 'how': 'automatic, after a yes',
         'check': lambda: False},
    ],
    'speech-to-text': [
        {'tier': 'local', 'name': 'faster-whisper', 'how': 'capmenu.transcribe(path)',
         'check': lambda: importlib.util.find_spec('faster_whisper') is not None},
        {'tier': 'private model', 'name': 'Muse on the transcript', 'how': 'platform request', 'check': lambda: False},
    ],
    'text-to-speech': [
        {'tier': 'local', 'name': 'Kokoro', 'how': 'capmenu.speak(text, out_wav)',
         'check': lambda: importlib.util.find_spec('kokoro') is not None},
    ],
    'video': [
        {'tier': 'local', 'name': 'ffmpeg', 'how': 'capmenu.ffmpeg(args)', 'check': lambda: bool(shutil.which('ffmpeg'))},
    ],
    'pdf': [
        {'tier': 'local', 'name': 'pdftotext (poppler)', 'how': 'capmenu.pdf_text(path)',
         'check': lambda: bool(shutil.which('pdftotext'))},
    ],
    'tables-and-charts': [
        {'tier': 'local', 'name': 'pandas, openpyxl, matplotlib, Vega-Lite', 'how': 'import as usual',
         'check': lambda: importlib.util.find_spec('pandas') is not None},
    ],
}


class Missing(RuntimeError):
    """This computer doesn't have the tool. Ask for it as a platform feature; never install it."""


def available():
    return {need: [{k: v for k, v in o.items() if k != 'check'} | {'here': bool(o['check']())} for o in opts]
            for need, opts in MENU.items()}


def describe():
    lines = []
    for need, opts in available().items():
        lines.append(f'- **{need}**: ' + '; '.join(
            f"{o['tier']}: {o['name']} ({'on this computer' if o['here'] else 'not available'}) -> {o['how']}" for o in opts))
    return '\n'.join(lines)


def _run(cmd, timeout=120):
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode:
        raise RuntimeError((out.stderr or 'failed').strip()[:300])
    return out.stdout


def _langs(langs):
    have = set(_run(['tesseract', '--list-langs']).split()[1:]) if shutil.which('tesseract') else set()
    want = [l for l in (langs or ['eng', 'hin', 'mar']) if l in have]
    return '+'.join(want or ['eng'])


def ocr_text(path, langs=None):
    """The text of an image or scan, read on this computer."""
    if not shutil.which('tesseract'):
        raise Missing('OCR (Tesseract) is not on this computer')
    return _run(['tesseract', str(path), 'stdout', '-l', _langs(langs)])


def ocr_words(path, langs=None):
    """Words with their position and confidence (Tesseract's TSV): for rebuilding tables from a photo of a form."""
    if not shutil.which('tesseract'):
        raise Missing('OCR (Tesseract) is not on this computer')
    rows = list(csv.DictReader(_run(['tesseract', str(path), 'stdout', '-l', _langs(langs), 'tsv']).splitlines(),
                               delimiter='\t', quoting=csv.QUOTE_NONE))
    words = []
    for r in rows:
        text = (r.get('text') or '').strip()
        if not text:
            continue
        words.append({'text': text, 'conf': float(r.get('conf') or -1), 'left': int(r['left']), 'top': int(r['top']),
                      'width': int(r['width']), 'height': int(r['height']), 'block': int(r['block_num']),
                      'line': int(r['line_num']), 'par': int(r['par_num'])})
    return words


def transcribe(path, language=None):
    if importlib.util.find_spec('faster_whisper') is None:
        raise Missing('Speech to text (faster-whisper) is not on this computer')
    from faster_whisper import WhisperModel  # pragma: no cover (not installed on the test machines)
    model = WhisperModel(os.environ.get('IDLI_WHISPER', 'small'), device='cpu', compute_type='int8')
    segments, _ = model.transcribe(str(path), language=language)
    return [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segments]


def speak(text, out_wav):
    if importlib.util.find_spec('kokoro') is None:
        raise Missing('Text to speech (Kokoro) is not on this computer')
    raise Missing('Text to speech is listed but not wired yet')  # pragma: no cover


def ffmpeg(args, timeout=600):
    if not shutil.which('ffmpeg'):
        raise Missing('ffmpeg is not on this computer')
    return _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', *map(str, args)], timeout=timeout)


def pdf_text(path):
    if not shutil.which('pdftotext'):
        raise Missing('PDF text (pdftotext) is not on this computer')
    return _run(['pdftotext', '-layout', str(path), '-'])
