"""2026-11-18 owner round: @ a folder for insights, "entirely withheld" on the privacy page, and Minis that can be
asked, activated and forked (narrative/UX.md)."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _xlsx(path, rows):
    import pandas as pd
    pd.DataFrame(rows).to_excel(path, index=False)


class FolderFetchTests(unittest.TestCase):
    def setUp(self):
        self.dd = tempfile.mkdtemp()
        self.fake = Path(tempfile.mkdtemp())
        _xlsx(self.fake / 's1.xlsx', {'Ward': ['A', 'B'], 'Debt': [1, 2]})
        _xlsx(self.fake / 's2.xlsx', {'Ward': ['C'], 'Debt': [3]})
        self.entries = {
            'My Drive/Survey/round1': {'id': 's1', 'url': 'x', 'kind': 'Google Sheets', 'title': 'round1'},
            'My Drive/Survey/round2': {'id': 's2', 'url': 'x', 'kind': 'Google Sheets', 'title': 'round2'},
            'My Drive/Survey/notes.pdf': {'id': 'p1', 'url': 'x', 'kind': 'PDF', 'title': 'notes.pdf'},
            'My Drive/Papers/a.pdf': {'id': 'p2', 'url': 'x', 'kind': 'PDF', 'title': 'a.pdf'},
            'My Drive/Papers/b.pdf': {'id': 'p3', 'url': 'x', 'kind': 'PDF', 'title': 'b.pdf'},
            'My Drive/Survey summary': {'id': 's2', 'url': 'x', 'kind': 'Google Sheets', 'title': 'Survey summary'},
        }

    def tearDown(self):
        shutil.rmtree(self.dd)
        shutil.rmtree(self.fake)

    def fetch(self, paths):
        from lib import drivestubs
        with patch.dict(os.environ, {'IDLI_DRIVE_FAKE': str(self.fake)}), \
                patch.object(drivestubs, 'refresh', return_value=self.entries):
            return drivestubs.fetch(self.dd, paths, spreadsheets_only=True)

    def test_a_folder_without_its_slash_is_a_folder(self):
        out = self.fetch(['Drive/My Drive/Survey'])
        self.assertEqual(sorted(f['title'] for f in out['files']), ['round1', 'round2'])
        self.assertEqual(out['folders'], ['Survey'])
        self.assertEqual(out['skipped'], {'PDF': 1})

    def test_a_file_named_like_the_folder_is_still_that_file(self):
        out = self.fetch(['Drive/My Drive/Survey summary'])
        self.assertEqual([f['title'] for f in out['files']], ['Survey summary'])
        self.assertNotIn('folders', out)

    def test_router_words(self):
        from lib import modes
        self.assertEqual(modes._kinds_words({'PDF': 18, 'Image': 1}), '18 PDFs and 1 image')
        out = self.fetch(['Drive/My Drive/Papers'])
        self.assertEqual(out['files'], [])
        self.assertEqual(out['folders'], ['Papers'])
        self.assertEqual(out['skipped'], {'PDF': 2})


class WithheldColumnTests(unittest.TestCase):
    def test_review_rows_show_filled_cells_and_say_withheld(self):
        from lib import privacy
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'visits.xlsx')
        notes = [''] * 4 + ['Met the family at home and talked about the loan for a long time'] * 2
        _xlsx(path, {'Ward': ['A', 'B', 'C', 'D', 'E', 'F'], 'Visits': [1, 2, 3, 4, 5, 6], 'Notes': notes})
        rows = [{'column': 'Ward', 'mask': False, 'reason': 'x', 'samples': [], 'as_sent': []},
                {'column': 'Visits', 'mask': False, 'reason': 'x', 'samples': [], 'as_sent': []},
                {'column': 'Notes', 'mask': True, 'reason': 'free-text', 'samples': ['', '', ''], 'as_sent': []}]
        with patch.object(privacy, 'suggest', return_value=rows):
            got = privacy.review(d, 'visits.xlsx', path, columns={'Notes': True})
        note = next(r for r in got['suggestions'] if r['column'] == 'Notes')
        self.assertTrue(note['samples'][0].startswith('Met the family'))  # not the blank top rows
        self.assertTrue(note['withheld'])  # each note became one code: the page says "Notes entirely withheld"
        ward = next(r for r in got['suggestions'] if r['column'] == 'Ward')
        self.assertFalse(ward['withheld'])
        shutil.rmtree(d)


if __name__ == '__main__':
    unittest.main()
