"""The kit a transform block gets (lib/transforms.py). A block's code uses only this and the trusted imports.

    def run(kit, question='What are the main ideas?'):
        texts = {f.title: kit.remember(f, 'text', lambda: text_of(kit.read_bytes(f))) for f in kit.files()}
        notes = kit.summarise_all(texts)              # one short summary per file, by the private 9B, kept
        return {'reply': kit.answer(question, notes), 'used': list(texts)}

What the kit offers:
- kit.args: the arguments of this run.
- kit.files(kinds=None): the files the person picked (title, kind). kit.read_bytes(f): a file's bytes.
- kit.remember(f, what, compute): compute once per file (for example its text), then reuse.
- kit.ask(question, text, max_words=150): the private 9B's answer in plain words. kit.judge(question, text,
  schema): its answer as JSON. kit.summarise_all({title: text}): short summaries, two at a time, kept.
  kit.answer(question, {title: text}): one answer across many parts. kit.sample(text): a long text cut to what the
  9B reads well (the start, then pieces from the middle and the end).
- kit.progress(text): a short line about how far it got.
- In a test (fake data only): kit.add_fake_file(title, data) and kit.fake_pdf(text) (a small real PDF).
  kit.ask and friends answer with stand-ins, so a test takes about a second.
"""
import hashlib
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROMPT_VERSION = '2'
SUMMARY_CHARS = 9000  # about 2,000 tokens a file: the start (abstract, introduction) and pieces from further in


class File:
    def __init__(self, title, kind, path=None, ident=None, data=None):
        self.title, self.kind = str(title), kind
        self._path, self._id, self._data = path, ident, data

    def __repr__(self):
        return f'File({self.title!r})'


class Kit:
    def __init__(self, mode, block_dir, sandbox=None, args=None, files=(), model_url=None):
        self._mode, self._block = mode, Path(block_dir)
        self._sandbox = Path(sandbox) if sandbox else None
        self.args = dict(args or {})
        self._files = [File(f['title'], f.get('kind'), f.get('path'), f.get('id')) for f in files or []]
        self._model = model_url
        self._cache = (self._sandbox / '.idli' / 'blocks' / self._block.name / 'cache') if self._sandbox else None
        self._made = 0

    # ---- files ----
    def files(self, kinds=None):
        return [f for f in self._files if not kinds or f.kind in kinds]

    def read_bytes(self, f):
        if f._data is not None:
            return f._data
        if not isinstance(f, File) or f not in self._files:
            raise ValueError('kit.read_bytes reads only the files from kit.files()')
        return Path(f._path).read_bytes()

    def add_fake_file(self, title, data):
        if self._mode != 'test':
            raise ValueError('fake files are for tests only')
        kind = {'.pdf': 'pdf', '.docx': 'documents', '.txt': 'documents', '.csv': 'spreadsheet',
                '.xlsx': 'spreadsheet'}.get(Path(str(title)).suffix.lower())
        self._files.append(File(title, kind, data=bytes(data)))

    def progress(self, text):
        sys.stderr.write('PROGRESS ' + ' '.join(str(text).split())[:200] + '\n')
        sys.stderr.flush()

    # ---- keeping work ----
    def _key(self, *parts):
        return hashlib.sha256('\0'.join(map(str, (PROMPT_VERSION,) + parts)).encode()).hexdigest()[:32]

    def _get(self, key):
        if not self._cache:
            return None
        try:
            return json.loads((self._cache / (key + '.json')).read_text())['v']
        except (OSError, ValueError, KeyError):
            return None

    def _put(self, key, value):
        if self._cache:
            self._cache.mkdir(parents=True, exist_ok=True)
            tmp = self._cache / (key + '.tmp')
            tmp.write_text(json.dumps({'v': value}))
            tmp.replace(self._cache / (key + '.json'))
        return value

    def remember(self, f, what, compute):
        stamp = ''
        if f._path:
            st = Path(f._path).stat()
            stamp = f'{st.st_size}:{int(st.st_mtime)}'
        key = self._key('file', f._id or f.title, stamp, what)
        got = self._get(key)
        return got if got is not None else self._put(key, compute())

    # ---- the private 9B ----
    def _chat(self, prompt, max_tokens, schema=None):
        if self._mode == 'test':
            return None
        body = {'model': 'idli-9b', 'temperature': 0.2, 'max_tokens': int(max_tokens), 'stream': False,
                'messages': [{'role': 'user', 'content': prompt}],
                'chat_template_kwargs': {'enable_thinking': False}}
        if schema:
            body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': schema}}
        req = urllib.request.Request(self._model + '/v1/chat/completions', json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.load(r)['choices'][0]['message']['content'] or ''
            except OSError:
                if attempt:
                    raise
                time.sleep(2)

    def ask(self, question, text, max_words=150):
        if self._mode == 'test':
            return f'(the private model would answer "{str(question)[:60]}" from {len(str(text).split())} words)'
        prompt = (f'{question}\n\nAnswer in plain words, at most {int(max_words)} words. Use only the text below.'
                  f'\n\n---\n{self.sample(text)}\n---')
        return (self._chat(prompt, int(max_words) * 2 + 60) or '').strip()

    def judge(self, question, text, schema=None):
        schema = schema or {'type': 'object', 'properties': {'answer': {'type': 'string'},
                                                             'unclear': {'type': 'boolean'}},
                            'required': ['answer', 'unclear']}
        if self._mode == 'test':
            return {k: (False if v.get('type') == 'boolean' else '') for k, v in schema.get('properties', {}).items()}
        out = self._chat(f'{question}\n\nAnswer with JSON only. If you are not sure, set "unclear" to true.'
                         f'\n\n---\n{self.sample(text, 6000)}\n---', 400, schema)
        m = re.search(r'\{.*\}', out or '', re.S)
        try:
            return json.loads(m.group(0) if m else out)
        except ValueError:
            return {'unclear': True}

    @staticmethod
    def sample(text, chars=14000):
        """The start of a long text, then pieces from further in (where the argument and the conclusion are)."""
        t = ' '.join(str(text).split())
        if len(t) <= chars:
            return t
        head = t[:chars // 2]
        piece = chars // 6
        parts = [head] + [t[int(len(t) * at):int(len(t) * at) + piece] for at in (0.3, 0.55, 0.8)]
        return ' [...] '.join(parts)

    def summarise_all(self, texts, focus='its main ideas and themes'):
        """{title: text} -> {title: summary}. Two at a time (the 9B serves two), each kept for next time."""
        texts = {str(k): str(v) for k, v in texts.items() if str(v).strip()}
        done, todo = {}, []
        for title, text in texts.items():
            key = self._key('summary', title, hashlib.sha256(self.sample(text, SUMMARY_CHARS).encode()).hexdigest(), focus)
            got = self._get(key)
            if got is not None:
                done[title] = got
            else:
                todo.append((title, text, key))
        if todo:
            self.progress(f'Summarising {len(todo)} of {len(texts)} files (the rest were done before).')

        def one(item):
            title, text, key = item
            if self._mode == 'test':
                return title, f'(summary of {title}: {len(text.split())} words)'
            prompt = (f'Below is text from "{title}". In 3 short bullet points (60 words in all), give {focus}. Plain words, '
                      f'no preamble.\n\n---\n{self.sample(text, SUMMARY_CHARS)}\n---')
            return title, self._put(key, (self._chat(prompt, 160) or '').strip())

        with ThreadPoolExecutor(2) as pool:
            for title, summary in pool.map(one, todo):
                done[title] = summary
                self._made += 1
        return {t: done[t] for t in texts if t in done}

    def answer(self, question, parts, max_words=250):
        """One answer across many parts ({title: text}), naming which part says what."""
        parts = {str(k): str(v) for k, v in parts.items() if str(v).strip()}
        if self._mode == 'test':
            return f'(the private model would answer "{str(question)[:60]}" across {len(parts)} parts)'
        budget = max(600, 40000 // max(1, len(parts)))
        body = '\n\n'.join(f'## {t}\n{self.sample(v, budget)}' for t, v in parts.items())
        prompt = (f'Question: {question}\n\nBelow are notes on {len(parts)} documents. Answer the question across '
                  f'them in at most {int(max_words)} words: group the common themes, and name the documents in '
                  f'brackets after each point. Plain words, short paragraphs or bullets, no preamble.\n\n{body}')
        return (self._chat(prompt, int(max_words) * 2 + 100) or '').strip()

    # ---- fake data for tests ----
    @staticmethod
    def fake_pdf(text):
        """A small one-page PDF holding the text (lines of up to 90 characters)."""
        lines = []
        for para in str(text).split('\n'):
            while len(para) > 90:
                cut = para.rfind(' ', 0, 90)
                cut = cut if cut > 0 else 90
                lines.append(para[:cut])
                para = para[cut:].lstrip()
            lines.append(para)
        esc = [l.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') for l in lines[:50]]
        stream = 'BT /F1 11 Tf 50 780 Td 14 TL ' + ' '.join(f'({l}) Tj T*' for l in esc) + ' ET'
        objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R '
                '/Resources << /Font << /F1 5 0 R >> >> >>',
                f'<< /Length {len(stream.encode("latin-1", "replace"))} >>\nstream\n{stream}\nendstream',
                '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        out, offsets = b'%PDF-1.4\n', []
        for i, o in enumerate(objs, 1):
            offsets.append(len(out))
            out += f'{i} 0 obj\n{o}\nendobj\n'.encode('latin-1', 'replace')
        xref = len(out)
        out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
        out += b''.join(f'{o:010d} 00000 n \n'.encode() for o in offsets)
        out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
        return out
