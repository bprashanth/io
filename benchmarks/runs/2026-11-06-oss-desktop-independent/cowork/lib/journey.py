"""Local Drivey review sessions and editable Mini drafts. Never imported by the router."""
import datetime
from pathlib import Path
import re
import shutil
import threading
import urllib.parse
import uuid

from lib import home, maskcopy, privacy

LOCK = threading.RLock()


def page_url(data_dir, page, **query):
    from lib import formserver
    port, token = formserver.ensure(str(data_dir))
    return f'http://dashboard.localhost:{port}/{page}?' + urllib.parse.urlencode({'t': token, **query})


def record_path(data_dir, kind, ident):
    if not re.fullmatch(r'[\w-]{1,100}', str(ident)):
        raise ValueError('Open this page again from your chat.')
    return home.inside(data_dir, f'.idli/{kind}/{ident}.json')


def review_open(data_dir, files, question, agent, workspace, preview_only=False, mini_id=None):
    prepared = home.prepare(data_dir, files, question)
    result = {'files': prepared['files'], 'masked_question': prepared['masked_question'],
              'preview_only': preview_only, 'mini_id': mini_id}
    if preview_only:
        return result
    if not isinstance(agent, str) or not re.fullmatch(r'[\w-]{7,80}', agent):
        raise ValueError('Open the review from the left chat to continue.')
    ident = uuid.uuid4().hex
    with LOCK, privacy.session_lock(data_dir):
        home.write(home.inside(data_dir, f'.idli/reviews/{ident}.json', exists=False),
                   {**result, 'question': question, 'agent': agent, 'workspace': workspace, 'notified': False})
        latest = Path(data_dir) / '.idli/review-active.json'
        active = home.read(latest) if latest.exists() else {}
        active[agent] = ident
        home.write(latest, active)
    result['url'] = page_url(data_dir, 'privacy-review', id=ident, embed=1, a=agent)
    return result


def invalidate_review(data_dir, agent):
    if not agent:
        return
    with LOCK, privacy.session_lock(data_dir):
        path = Path(data_dir) / '.idli/review-active.json'
        active = home.read(path) if path.exists() else {}
        active.pop(agent, None)
        home.write(path, active)


def review_data(data_dir, ident):
    session = home.read(record_path(data_dir, 'reviews', ident))
    prepared = home.prepare(data_dir, session['files'], session['question'])
    return {**prepared, 'done': session['notified']}


def review_change(data_dir, ident, file, columns):
    with LOCK, privacy.session_lock(data_dir):
        session = home.read(record_path(data_dir, 'reviews', ident))
        if session['notified']:
            raise ValueError('This review is complete. Send a new question to change your choices.')
        active = home.read(Path(data_dir) / '.idli/review-active.json')
        if active.get(session['agent']) != ident:
            raise ValueError('Continue with the newer question in your chat.')
        if file not in [f['local'] for f in session['files']]:
            raise ValueError('Choose a file in this review.')
        current = home.prepare(data_dir, session['files'], session['question'])
        known = {r['column'] for f in current['reviews'] if f['local'] == file
                 for tab in f['tabs'] for r in tab['suggestions']}
        if not isinstance(columns, dict) or columns.keys() - known:
            raise ValueError('Choose a column shown in the review.')
        privacy.set(data_dir, file, mode='mask', columns=columns)
        return review_data(data_dir, ident)


def review_done(data_dir, ident):
    with LOCK, privacy.session_lock(data_dir):
        path = record_path(data_dir, 'reviews', ident)
        session = home.read(path)
        if session['notified']:
            return {'done': True}
        active = home.read(Path(data_dir) / '.idli/review-active.json')
        if active.get(session['agent']) != ident:
            raise ValueError('A newer review is ready in your chat. Continue there.')
        home.prepare(data_dir, session['files'], session['question'])
        home.cli('send', '--no-wait', session['agent'], 'Privacy checked')
        session['notified'] = True
        home.write(path, session)
        return {'done': True}


def handoff(data_dir, files, question, workspace, mini_id=None):
    # Apply suggestions on the first handoff from a Mini, and retain reviewed choices.
    if not isinstance(workspace, str) or not re.fullmatch(r'[\w-]{1,80}', workspace):
        raise ValueError('Open this question in its Drivey workspace and try again.')
    prepared = home.prepare(data_dir, files, question)
    if mini_id:
        mini = home.read(home.object_path(data_dir, 'minis', mini_id))
        question += ' Mini context: ' + home.plain(mini['name']) + '. ' + home.plain(mini['goal'])[:240]
    result = home.send(data_dir, prepared['files'], question, workspace)
    def change(state):
        state.setdefault('workspace_minis', {})[workspace] = mini_id
        state.setdefault('workspace_files', {})[workspace] = prepared['files']
    home.update_state(data_dir, change)
    return {**result, 'reply': 'Sent to Claude on the right.'}


def pin(data_dir, ident, pinned):
    if type(pinned) is not bool:
        raise ValueError('Choose Pin or Pinned.')
    with LOCK:
        path = home.object_path(data_dir, 'views', ident)
        view = home.read(path)
        view['pinned'] = pinned
        home.write(path, view)
    return {'pinned': pinned}


def back_to_claude(data_dir, workspace):
    from lib import uiswitch
    terminal = home._claude_terminal(data_dir, workspace)
    if not terminal:
        raise ValueError('Open Claude in this workspace, then try again.')
    result = uiswitch.show_terminal(workspace, terminal, 'right', focus=True)
    if not result.get('ok'):
        raise ValueError('Choose the Claude tab on the right to continue.')
    return {'focused': True}


def questions_checked(questions, root):
    if not isinstance(questions, list) or not 1 <= len(questions) <= 8:
        raise ValueError('Keep between one and eight questions in this Mini.')
    out, ids = [], set()
    for item in questions:
        q = dict(item)
        if not re.fullmatch(r'[\w-]{1,80}', str(q.get('id', ''))) or q['id'] in ids:
            raise ValueError('Give each question its own name.')
        ids.add(q['id'])
        q['question'] = home.plain(str(q.get('question', '')).strip())
        if not q['question'] or len(q['question']) > 1000:
            raise ValueError('Write a short question for each script.')
        params = q.get('params', {})
        if not isinstance(params, dict) or len(params) > 3:
            raise ValueError('Keep at most three options for each question.')
        for desc in params.values():
            if not isinstance(desc, dict) or desc.get('type') not in ('choice', 'number') or 'default' not in desc:
                raise ValueError('Give every option a choice or number and a starting value.')
            if desc['type'] == 'choice' and (not isinstance(desc.get('choices'), list) or not desc['choices']
                    or any(not isinstance(c, str) or not c.strip() for c in desc['choices'])):
                raise ValueError('List the choices for every option.')
        asks = q.get('asks', [])
        q['asks'] = [home.plain(str(a).strip())[:200] for a in (asks if isinstance(asks, list) else []) if str(a).strip()][:6]
        home.params_for(q, {})
        path = home.inside(root, q.get('script', ''))
        if path.suffix != '.py':
            raise ValueError('Choose a Python script for each question.')
        out.append(q)
    return out


def draft_mini(data_dir, title, story, questions, code, workspace, author):
    if not isinstance(workspace, str) or not re.fullmatch(r'[\w-]{1,80}', workspace):
        raise ValueError('Open Claude from a Drivey workspace and try again.')
    questions = questions_checked(questions, home.work_dir())
    # Claude wrote these with codes. The Mini runs on the real file for people, so it gets the real values back.
    title, story, questions = home.rehydrate(data_dir, [title, story, questions])
    vault = privacy.session_vault(data_dir)
    ident = uuid.uuid4().hex
    folder = home.inside(data_dir, f'.idli/drafts/{ident}/mini.json', exists=False).parent
    state_path = Path(data_dir) / '.idli/home.json'
    state = home.read(state_path) if state_path.exists() else {}
    selected = state.get('workspace_files', {}).get(workspace, []) if workspace else []
    pins = []
    for path in sorted((Path(data_dir) / 'views').glob('*.json')):
        view = home.read(home.object_path(data_dir, 'views', path.stem))
        if workspace and view.get('workspace') == workspace and view.get('pinned'):
            pins.append({'id': path.stem, 'title': view['title']})
    source_id = state.get('workspace_minis', {}).get(workspace)
    source_name = home.read(home.object_path(data_dir, 'minis', source_id))['name'] if source_id else None
    folder.mkdir(parents=True)
    try:
        for i, q in enumerate(questions):
            source = home.inside(home.work_dir(), q['script'])
            q['script'] = f'question_{i + 1}.py'
            text, _ = maskcopy.rehydrate_script(source.read_text(), vault)
            (folder / q['script']).write_text(text)
        drive = Path(data_dir).resolve() / 'drive'
        drive.mkdir(exist_ok=True)
        (folder / 'drive').symlink_to(drive, target_is_directory=True)
        draft = {'id': ident, 'name': home.plain(title), 'goal': home.plain(story), 'questions': questions,
                 'files': selected, 'charts': pins, 'code': str(code or home.work_dir()), 'workspace': workspace,
                 'source_id': source_id, 'source_name': source_name, 'author': author,
                 'date': datetime.date.today().isoformat()}
        home.write(folder / 'mini.json', draft)
        # Check the very scripts the Mini will run, with their defaults, before offering Save.
        for q in questions:
            home.run_manifest(data_dir, folder / 'mini.json', q['id'], {})
        home.write(home.inside(data_dir, f'.idli/mini-drafts/{ident}.json', exists=False), {'folder': str(folder)})
    except Exception:
        shutil.rmtree(folder)
        raise
    return ident


def draft_data(data_dir, ident):
    pointer = home.read(record_path(data_dir, 'mini-drafts', ident))
    path = home.inside(data_dir, Path(pointer['folder']) / 'mini.json')
    return home.read(path)


def blocks_of(m):
    """A Mini's page, top to bottom: the author's text and pinned charts in their order. Minis saved before blocks
    existed read as their story, then their charts."""
    if isinstance(m.get('blocks'), list) and m['blocks']:
        return m['blocks']
    out = [{'type': 'text', 'text': m['goal']}] if m.get('goal') else []
    return out + [{'type': 'chart', 'id': c['id'], 'title': c.get('title', '')} for c in m.get('charts', [])]


def _card_edits(draft, edits):
    """The page as the author arranged it, checked: text is plain, charts and questions only from this draft."""
    charts = {c['id']: c for c in draft['charts']}
    blocks, seen = [], set()
    for b in (edits.get('blocks') or [])[:60]:
        if not isinstance(b, dict):
            continue
        if b.get('type') == 'text':
            text = home.plain(str(b.get('text', ''))).strip()
            if text:
                blocks.append({'type': 'text', 'text': text[:6000]})
        elif b.get('type') == 'chart' and b.get('id') in charts and b['id'] not in seen:
            seen.add(b['id'])
            blocks.append({'type': 'chart', 'id': b['id'], 'title': charts[b['id']]['title']})
    known = {q['id'] for q in draft['questions']}
    questions = [{'id': q['id'], 'question': home.plain(str(q.get('question', ''))).strip()[:1000]}
                 for q in (edits.get('questions') or []) if isinstance(q, dict) and q.get('id') in known]
    return {'name': home.plain(str(edits.get('name', ''))).strip()[:160], 'blocks': blocks, 'questions': questions}


def edit_draft(data_dir, ident, edits):
    """Keep the author's changes as they make them (the page in the chat and its enlarged copy stay the same)."""
    with LOCK:
        draft = draft_data(data_dir, ident)
        if draft.get('saved_id'):
            return {'saved': True}
        path = home.inside(data_dir, f'.idli/drafts/{ident}/mini.json')
        home.write(path, {**draft, 'edits': _card_edits(draft, edits)})
        return {'kept': True}


def card_data(data_dir, draft=None, mini=None):
    """What the Mini page shows. The same page is the draft (editable) and the saved Mini (as colleagues see it)."""
    if mini:
        m = home.read(home.object_path(data_dir, 'minis', mini))
        questions, mode = m['questions'], 'mini'
        name, blocks = m['name'], blocks_of(m)
    else:
        m = draft_data(data_dir, draft)
        e = m.get('edits') or {}
        mode = 'saved' if m.get('saved_id') else 'draft'
        name, blocks = e.get('name') or m['name'], e.get('blocks') or blocks_of(m)
        by_id = {q['id']: q for q in m['questions']}
        words = {q['id']: q['question'] for q in e.get('questions', [])}
        order = [q['id'] for q in e.get('questions', [])] if e.get('questions') else list(by_id)
        questions = [{**by_id[i], 'question': words.get(i) or by_id[i]['question']} for i in order if i in by_id]
    return {'mode': mode, 'name': home.plain(name), 'blocks': blocks,
            'questions': [{'id': q['id'], 'question': home.plain(q['question']),
                           'options': '; '.join(home._option_words(k, d) for k, d in q.get('params', {}).items())}
                          for q in questions],
            'sources': home.file_labels(m.get('files', [])), 'workspace': m.get('workspace'),
            'saved_id': m.get('saved_id'), 'source_id': m.get('source_id'), 'source_name': m.get('source_name')}


def save_draft(data_dir, ident, edits, action='new'):
    with LOCK:
        draft = draft_data(data_dir, ident)
        if draft.get('saved_id'):
            return {'id': draft['saved_id'], 'saved': True}
        folder = home.inside(data_dir, f'.idli/drafts/{ident}/mini.json').parent
        blocks = None
        if 'blocks' in edits:  # the Mini page: text and charts in the author's order
            card = _card_edits(draft, edits)
            blocks = card['blocks']
            edits = {**edits, 'name': card['name'],
                     'goal': '\n\n'.join(b['text'] for b in blocks if b['type'] == 'text'),
                     'charts': [b['id'] for b in blocks if b['type'] == 'chart']}
        name = home.plain(str(edits.get('name', '')).strip())
        story = home.plain(str(edits.get('goal', '')).strip())
        if not name or len(name) > 160 or not story or len(story) > 12000:
            raise ValueError('Add a title and a few words about the Mini before saving.')
        # Only edit the text/options of existing questions. Scripts are never taken from browser input.
        originals = {q['id']: q for q in draft['questions']}
        raw = edits.get('questions', [])
        if not isinstance(raw, list) or any(not isinstance(q, dict) or q.get('id') not in originals for q in raw):
            raise ValueError('Keep questions from this draft.')
        questions = questions_checked([{**originals[q['id']], 'question': q.get('question'),
                                       'params': q.get('params', originals[q['id']].get('params', {}))}
                                      for q in raw], folder)
        pins = edits.get('charts', [])
        if not isinstance(pins, list) or any(p not in [v['id'] for v in draft['charts']] for p in pins):
            raise ValueError('Keep charts from this draft.')
        charts = [next(v for v in draft['charts'] if v['id'] == p) for p in pins]
        if action not in ('new', 'add') or (action == 'add' and not draft.get('source_id')):
            raise ValueError('Choose how to save this Mini.')
        target_id = draft['source_id'] if action == 'add' else (re.sub('[^a-z0-9]+', '-', name.lower()).strip('-') or 'mini')[:60] + '-' + uuid.uuid4().hex[:8]
        target = home.inside(data_dir, f'minis/{target_id}/mini.json', exists=False)
        existing = home.read(target) if action == 'add' else {}
        if len(existing.get('questions', [])) + len(questions) > 8:
            raise ValueError('This would give the Mini more than eight questions. Remove a question or save a new Mini.')
        # Validate changed defaults too, before changing the published Mini.
        check = {**draft, 'questions': questions}
        home.write(folder / 'check.json', check)
        for q in questions:
            home.run_manifest(data_dir, folder / 'check.json', q['id'], {})
        target.parent.mkdir(parents=True, exist_ok=True)
        saved_questions = list(existing.get('questions', []))
        for q in questions:
            copy = dict(q, id=q['id'] + '-' + uuid.uuid4().hex[:8] if action == 'add' else q['id'],
                        script='question_' + uuid.uuid4().hex + '.py')
            shutil.copyfile(home.inside(folder, q['script']), target.parent / copy['script'])
            saved_questions.append(copy)
        link = target.parent / 'drive'
        if not link.exists():
            link.symlink_to(Path(data_dir).resolve() / 'drive', target_is_directory=True)
        files = {f['local']: f for f in existing.get('files', []) + draft.get('files', [])}
        all_charts = {v['id']: v for v in existing.get('charts', []) + charts}
        if blocks is None:
            blocks = blocks_of({'goal': story, 'charts': charts})
        if action == 'add':
            blocks = blocks_of(existing) + [b for b in blocks if b['type'] == 'text' or
                                            b['id'] not in {c['id'] for c in existing.get('charts', [])}]
        home.write(target, {**existing, 'id': target_id, 'name': name, 'blocks': blocks,
                            'goal': existing['goal'] + '\n\n' + story if existing.get('goal') and existing['goal'] != story else story,
                            'heading': story.splitlines()[0][:140],
                            'questions': saved_questions,
                            'files': list(files.values()), 'charts': list(all_charts.values()),
                            'author': draft['author'], 'date': draft['date'], 'code': draft['code']})
        home.write(folder / 'mini.json', {**draft, 'saved_id': target_id})
        return {'id': target_id, 'saved': True}
