"""docmask: PDF text that pypdf gives one word per line is joined back, and long lines are scanned in windows
(the 2025 NDSA report's authors reached Claude before this, 2026-11-19)."""
import unittest
from unittest import mock

from lib import docmask


class Rejoin(unittest.TestCase):
    def test_word_per_line_runs_are_joined(self):
        self.assertEqual(docmask._rejoin('Matthew\n \nMcEniry (co-chair),\n \nTexas'), 'Matthew McEniry (co-chair), Texas')

    def test_paragraph_breaks_stay(self):
        self.assertEqual(docmask._rejoin('One line.\n\nNext paragraph.'), 'One line.\n\nNext paragraph.')


class Windows(unittest.TestCase):
    def test_long_line_is_scanned_in_overlapping_windows(self):
        seen = []

        def fake_scanner(text):
            seen.append(text)
            i = text.find('Kathryn Michaelis')
            return [(i, i + 17, 'person', 0.9)] if i >= 0 else []
        with mock.patch('lib.privacy.Scanner', return_value=fake_scanner):
            ls = docmask.LineScanner(workers=2)
            line = ('Lauren Goodley, Texas State University, ' * 3) + 'Kathryn Michaelis, Emory University'
            spans = ls(line)
            ls.close()
        self.assertTrue(all(len(s) <= docmask.LineScanner.WINDOW for s in seen))
        self.assertGreater(len(seen), 1)
        start = line.find('Kathryn Michaelis')
        self.assertIn((start, start + 17, 'person', 0.9), spans)


if __name__ == '__main__':
    unittest.main()
