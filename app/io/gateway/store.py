"""Private operator state; opaque public IDs are not credentials."""
import os
import pathlib
import secrets
import sqlite3
import threading


class Store:
    def __init__(self, filename):
        path = pathlib.Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, check_same_thread=False)
        os.chmod(path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, issuer TEXT NOT NULL, subject TEXT NOT NULL, email TEXT NOT NULL, token TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(issuer,subject))')
        self.db.commit()

    def get_or_create(self, identity):
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM workspaces WHERE issuer=? AND subject=?',
                                  (identity['issuer'], identity['subject'])).fetchone()
            if row:
                return dict(row)
            value = dict(id='workspace_' + secrets.token_hex(16), issuer=identity['issuer'],
                         subject=identity['subject'], email=identity['email'],
                         token=secrets.token_urlsafe(48), state='provisioning')
            self.db.execute('INSERT INTO workspaces VALUES (:id,:issuer,:subject,:email,:token,:state)', value)
            return value

    def owned(self, workspace_id, identity):
        with self.lock:
            row = self.db.execute('SELECT * FROM workspaces WHERE id=? AND issuer=? AND subject=?',
                                 (workspace_id, identity['issuer'], identity['subject'])).fetchone()
            return dict(row) if row else None

    def state(self, workspace_id, state):
        with self.lock, self.db:
            self.db.execute('UPDATE workspaces SET state=? WHERE id=?', (state, workspace_id))

    def remove(self, workspace_id):
        with self.lock, self.db:
            self.db.execute('DELETE FROM workspaces WHERE id=?', (workspace_id,))
