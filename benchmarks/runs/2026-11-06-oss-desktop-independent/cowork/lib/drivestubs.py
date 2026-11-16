"""The Drive catalogue as small @-pickable files. Downloads live in lowercase drive/."""
import os
import re
from pathlib import Path, PurePosixPath

from lib import driveindex, drivefetch, home


def _relative(path):
    parts = PurePosixPath(str(path)).parts
    if not parts or str(path).startswith('/') or any(p in ('.', '..') for p in parts) or '\\' in str(path):
        raise ValueError('Use a path inside Drive/')
    return PurePosixPath(*parts).as_posix()


def refresh(data_dir):
    """Refresh from the complete index, deleting only previously generated stubs."""
    root = Path(data_dir).resolve()
    rows = driveindex._read('SELECT id, name, kind, path FROM files ORDER BY path, name, id')
    entries, folders = {}, set()
    for fid, title, kind, folder in rows:
        # The index separates Drive folder components with ' / '.
        parent = '/'.join(p.strip() for p in (folder or '').split(' / ') if p.strip())
        rel = _relative(parent + '/' + title if parent else title)
        if driveindex.is_folder(kind):
            folders.add(rel)
            continue
        if rel in entries:  # Drive permits equal names; keep both deterministically.
            rel += '__' + fid
        entries[rel] = {'id': fid, 'url': 'https://drive.google.com/file/d/' + fid + '/view',
                        'kind': kind, 'title': title}
    manifest = home.inside(root, '.idli/drive-stubs.json', exists=False)
    previous = home.read(manifest) if manifest.exists() else []
    for rel in previous:
        if rel not in entries:
            old = home.inside(root, 'Drive/' + _relative(rel), exists=False)
            if old.is_file():
                old.unlink()
    mirror = root / 'Drive'
    if mirror.is_symlink():
        raise ValueError('Drive/ must be a local folder')
    mirror.mkdir(parents=True, exist_ok=True)
    # A folder may have become a file in the new index.
    for folder in sorted(mirror.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if folder.is_dir() and not folder.is_symlink() and folder.relative_to(mirror).as_posix() not in folders:
            try:
                folder.rmdir()
            except OSError:
                pass
    for folder in sorted(folders):
        home.inside(root, 'Drive/' + folder + '/.folder', exists=False).parent.mkdir(parents=True, exist_ok=True)
    for rel, entry in entries.items():
        home.write(home.inside(root, 'Drive/' + rel, exists=False), entry)
    home.write(manifest, list(entries))
    return entries


from lib.minimap import mentions  # noqa: E402,F401  (light: the router uses it)


def fetch(data_dir, paths, workspace=None, spreadsheets_only=False):
    if not isinstance(paths, list) or not paths:
        raise ValueError('Choose at least one Drive path')
    entries = refresh(data_dir)
    chosen = {}
    for name in paths:
        if not isinstance(name, str) or not name.startswith('Drive/'):
            raise ValueError('Use a Drive/ path')
        if name == 'Drive/':
            chosen.update(entries)
            continue
        folder = name.endswith('/')
        rel = _relative(name[6:].rstrip('/'))
        if not folder and rel not in entries:
            matches = [p for p in entries if rel.startswith(p) and
                       (len(rel) == len(p) or rel[len(p)] in ' .,;!?')]
            if matches:
                rel = max(matches, key=len)
        hits = {p: e for p, e in entries.items() if p.startswith(rel + '/')} if folder else {
            p: e for p, e in entries.items() if p == rel}
        if not hits:
            raise ValueError('No indexed files at ' + name)
        chosen.update(hits)
    result, errors, unsupported, missing = [], [], [], []
    from lib import teamcaps
    for rel, item in chosen.items():
        sheet = item['kind'] in ('Google Sheets', 'application/vnd.google-apps.spreadsheet')
        extension = '.xlsx' if sheet else ('.' + drivefetch.EXPORTS[item['kind']][1]
                                           if item['kind'] in drivefetch.EXPORTS else '')
        target = 'drive/' + rel + (extension if extension and not rel.lower().endswith(extension) else '')
        kind = teamcaps.kind_of(target)
        reader = None
        if spreadsheets_only and kind != 'spreadsheet':
            # A team extension may read this kind into tables (narrative/MODEL_TYPES.md); otherwise the Builder can add it
            reader = teamcaps.reader_for(data_dir, kind) if kind else None
            if not reader:
                unsupported.append(item.get('title') or rel)
                if (kind or 'other') not in missing:
                    missing.append(kind or 'other')
                continue
        dest = home.inside(data_dir, target, exists=False)
        try:
            data = (drivefetch.fetch(item['id'], sheet=sheet, kind=item['kind']) if item['kind'] in drivefetch.EXPORTS
                    else drivefetch.fetch(item['id'], sheet=sheet))
        except (drivefetch.NoAccess, drivefetch.NoGoogle, OSError):
            errors.append({'path': 'Drive/' + rel, 'error': 'Could not download this file. Check your Drive access.'})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Download atomically, just as the stubs are written atomically.
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=dest.parent)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        home.write(str(dest) + '.source.json', {**item, 'sheet': sheet})
        if reader:
            try:
                tables = teamcaps.run_reader(data_dir, reader, dest)
            except (ValueError, OSError, RuntimeError) as exc:
                errors.append({'path': 'Drive/' + rel, 'error': str(exc)})
                continue
            for t in tables:
                local = str(Path(target).parent / t.name)
                home.write(str(t) + '.source.json', {**item, 'sheet': False, 'read_by': reader['id']})
                part = t.name[len(dest.name):].strip('.').rsplit('.', 1)[0]  # photo.png.table.csv -> table
                part = '' if part.lower() in ('csv', 'tsv') else part  # photo.png.csv: one table, not "csv"
                kind = {'lines': 'text, line by line', 'text': 'text', 'table': 'table'}.get(part, part or 'table')
                result.append({**item, 'title': (item.get('title') or rel) + f' (read as {kind})',
                               'file': local, 'local': local, 'read_by': reader['id']})
            continue
        result.append({**item, 'file': target, 'local': target})
    workspace = workspace or os.environ.get('IDLI_WORKSPACE')
    def change(state):
        state['files'] = result
        if workspace:
            state.setdefault('workspace_files', {})[workspace] = result
            state.setdefault('workspace_minis', {})[workspace] = None
    home.update_state(data_dir, change)
    return {'files': result, **({'errors': errors} if errors else {}),
            **({'unsupported': unsupported, 'missing': missing} if unsupported else {})}
