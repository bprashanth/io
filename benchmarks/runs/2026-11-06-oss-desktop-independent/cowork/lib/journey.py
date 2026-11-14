"""Local Drivey review sessions and editable Mini drafts. Never imported by the router."""
import datetime
from pathlib import Path
import re
import shutil
import threading
import urllib.parse
import uuid

from lib import home, privacy

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
            shutil.copyfile(source, folder / q['script'])
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


def save_draft(data_dir, ident, edits, action='new'):
    with LOCK:
        draft = draft_data(data_dir, ident)
        if draft.get('saved_id'):
            return {'id': draft['saved_id'], 'saved': True}
        folder = home.inside(data_dir, f'.idli/drafts/{ident}/mini.json').parent
        name = home.plain(str(edits.get('name', '')).strip())
        story = home.plain(str(edits.get('goal', '')).strip())
        if not name or len(name) > 160 or not story or len(story) > 12000:
            raise ValueError('Add a title and a short story before saving.')
        # Only edit the text/options of existing questions. Scripts are never taken from browser input.
        originals = {q['id']: q for q in draft['questions']}
        raw = edits.get('questions', [])
        if not isinstance(raw, list) or any(not isinstance(q, dict) or q.get('id') not in originals for q in raw):
            raise ValueError('Keep questions from this draft.')
        questions = questions_checked([{**originals[q['id']], 'question': q.get('question'),
                                       'params': q.get('params', {})} for q in raw], folder)
        pins = edits.get('charts', [])
        if not isinstance(pins, list) or any(p not in [v['id'] for v in draft['charts']] for p in pins):
            raise ValueError('Keep charts from this draft.')
        charts = [v for v in draft['charts'] if v['id'] in pins]
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
        home.write(target, {**existing, 'id': target_id, 'name': name,
                            'goal': existing['goal'] + '\n\n' + story if existing.get('goal') and existing['goal'] != story else story,
                            'heading': story.splitlines()[0][:140],
                            'questions': saved_questions,
                            'files': list(files.values()), 'charts': list(all_charts.values()),
                            'author': draft['author'], 'date': draft['date'], 'code': draft['code']})
        home.write(folder / 'mini.json', {**draft, 'saved_id': target_id})
        return {'id': target_id, 'saved': True}
