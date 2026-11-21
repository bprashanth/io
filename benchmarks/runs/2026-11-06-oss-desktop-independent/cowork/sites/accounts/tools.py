"""A sandbox's account blocks for the left chat (the private model, which sees real content). lib/blocks.py checks
the block and the account on every call."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lib import blocks  # noqa: E402


def _safe(fn):
    def run(**kw):
        try:
            return fn(**kw)
        except blocks.NotInSandbox as e:
            return {'error': str(e)}
        except Exception as e:  # a sign-in that lapsed says so plainly (google_api.SignInNeeded)
            return {'error': str(e)[:300]}
    return run


def _block_run(name, paths=None, question=''):
    from lib import transforms
    res = transforms.run(blocks.sandbox_dir(), name, {'paths': paths or [], 'question': question or
                                                      'What are the main themes and ideas?'})
    if res.get('error'):
        return {'error': res['error']}
    used, missed = res.get('used') or [], res.get('missed') or []
    tail = f'\n\nRead {len(used)} file{"s" if len(used) != 1 else ""}.' if used else ''
    if missed:
        tail += ' Could not download: ' + ', '.join(missed[:5]) + '.'
    return {'reply': str(res.get('reply') or '').strip() + tail, 'used': used}


ROLE = {'role': {'type': 'string', 'description': 'Which account: a role like "me" (default) or "lead"'}}
TOOLS = {
    'block_run': (_safe(_block_run), "Run one of this sandbox's added blocks (for example read_pdfs) on Drive files "
                  'picked with @, with the person\'s question.',
                  {'name': {'type': 'string'}, 'paths': {'type': 'array', 'items': {'type': 'string'}},
                   'question': {'type': 'string'}}, ['name']),
    'mail_search': (_safe(lambda query, role=None, limit=10: {'emails': blocks.gmail_search(query, role, limit)}),
                    'Find emails with a Gmail search, e.g. "from:asha@x.org" or "subject:meeting newer_than:7d".',
                    {'query': {'type': 'string'}, 'limit': {'type': 'integer'}, **ROLE}, ['query']),
    'mail_read': (_safe(lambda id, role=None: blocks.gmail_read(id, role)),
                  'Read one email found by mail_search (its id).', {'id': {'type': 'string'}, **ROLE}, ['id']),
    'mail_draft': (_safe(lambda to, body, subject='', reply_to=None, role=None:
                         blocks.gmail_draft(to, subject, body, reply_to, role)),
                   'Write a draft in Gmail (a reply in the thread when reply_to is an email id). The person sends it.',
                   {'to': {'type': 'string'}, 'subject': {'type': 'string'}, 'body': {'type': 'string'},
                    'reply_to': {'type': 'string'}, **ROLE}, ['to', 'body']),
    'free_times': (_safe(lambda count=3, minutes=30, days=5, role=None:
                         {'times': blocks.free_times(days, minutes, count, role=role)}),
                   'A few open meeting times in the calendar on the next working days.',
                   {'count': {'type': 'integer'}, 'minutes': {'type': 'integer'}, 'days': {'type': 'integer'},
                    **ROLE}, []),
    'book_meeting': (_safe(lambda title, start, guests, minutes=30, role=None:
                           blocks.calendar_book(title, start, minutes, guests, role)),
                     'Put a meeting on the calendar and invite the guests (start like 2026-11-20T14:00).',
                     {'title': {'type': 'string'}, 'start': {'type': 'string'},
                      'guests': {'type': 'array', 'items': {'type': 'string'}}, 'minutes': {'type': 'integer'},
                      **ROLE}, ['title', 'start', 'guests']),
    'sheet_rows': (_safe(lambda sheet, role=None: {'rows': blocks.sheet_read(sheet, role=role)[:200]}),
                   'Read the rows of a Google Sheet from its link or id, inside an account workflow (for example a leads list). Not for @Drive files: those go through drive_fetch.', {'sheet': {'type': 'string'}, **ROLE},
                   ['sheet']),
}
