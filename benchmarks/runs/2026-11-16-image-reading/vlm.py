import base64, csv, io, json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import score
D = os.environ.get('IMGDIR') or os.path.dirname(os.path.abspath(__file__))
url, model, tag = sys.argv[1:4]
only = sys.argv[4:]
truth = json.load(open(f'{D}/truth.json'))
PROMPT = ('Transcribe this table as CSV. Keep every cell exactly as written, in its original script. Use the heading '
          'row as the first CSV row. Leave a cell empty if it is empty in the picture. Output only the CSV.')
for name, rows in truth.items():
    if only and name not in only: continue
    b64 = base64.b64encode(open(f'{D}/{name}.png', 'rb').read()).decode()
    body = {'model': model, 'max_tokens': 6000, 'temperature': 0, **({'chat_template_kwargs': {'enable_thinking': False}} if os.environ.get('NOTHINK') else {}), **({'chat_template_kwargs': {'reasoning_effort': 'low'}, 'reasoning_effort': 'low'} if os.environ.get('LOW') else {}), 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': PROMPT}, {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64}}]}]}
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(url + '/v1/chat/completions', json.dumps(body).encode(),
                      {'Content-Type': 'application/json'}), timeout=600))
        text = r['choices'][0]['message']['content'] or ''
    except Exception as e:
        print(name, 'ERROR', type(e).__name__, str(e)[:100]); break
    text = text.strip().strip('`').removeprefix('csv').strip()
    out = [' '.join(c for c in row) for row in csv.reader(io.StringIO(text))]
    json.dump(out, open(f'{D}/out-{tag}-{name}.json', 'w'), ensure_ascii=False)
    s = score(rows, out)
    print(name.ljust(22), f'{tag}: row {s[0]} cells-in-row {s[1]} read {s[2]} ({time.time() - t:.1f}s)', flush=True)
