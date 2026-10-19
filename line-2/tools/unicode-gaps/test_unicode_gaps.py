import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
spec = importlib.util.spec_from_file_location('unicode_gaps', HERE / 'unicode_gaps.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GapsTests(unittest.TestCase):
    def test_demo(self):
        r = g.review(g.DEMO, max_details=2)
        self.assertEqual((r['findings'], r['retained_details'], r['omitted_details']), (6, 2, 4))
        self.assertTrue(r['analysis_complete'])

    def test_original_coordinates(self):
        raw = 'é\r\nA\u00a0B\u2028C\t'.encode()
        items = g.review(raw)['details']
        self.assertEqual([(x['byte_start'], x['byte_end'], x['line'], x['byte_column'])
                          for x in items], [(5, 7, 2, 2), (8, 11, 2, 5), (12, 13, 2, 9)])
        for x in items:
            self.assertEqual(raw[x['byte_start']:x['byte_end']].hex(), x['bytes_hex'])
        self.assertEqual(g.review(raw)['source_sha256'], hashlib.sha256(raw).hexdigest())

    def test_ordinary_text(self):
        self.assertEqual(g.review('English Ελληνικά 日本語 é\n\r '.encode())['findings'], 0)

    def test_literal_escapes(self):
        self.assertEqual(g.review(br'pay\u200bload\t')['findings'], 0)

    def test_classes(self):
        cases = {'\u200d': 'format-character', '\u202e': 'format-character',
                 '\u00ad': 'format-character', '\ufeff': 'format-character',
                 '\u202f': 'unusual-separator', '\u2029': 'unusual-separator',
                 '\u034f': 'combining-grapheme-joiner', '\t': 'tab',
                 '\ufe0f': 'variation-selector', '\U000e0100': 'variation-selector'}
        for char, category in cases.items():
            with self.subTest(char=repr(char)):
                self.assertEqual(g.review(char.encode())['details'][0]['kind'], category)

    def test_selector_boundaries(self):
        for code in [0xfdff, 0xfe10, 0xe00ff, 0xe01f0]:
            self.assertNotEqual(g.kind(chr(code)), 'variation-selector')
        for code in [0xfe00, 0xfe0f, 0xe0100, 0xe01ef]:
            self.assertEqual(g.kind(chr(code)), 'variation-selector')

    def test_inert_output(self):
        raw = '\x1b[31m\\\u200b\x00'.encode()
        rendered = g.render(g.review(raw, source='\u202e\x1b'))
        self.assertTrue(all(c == '\n' or 32 <= ord(c) <= 126 for c in rendered))
        r = json.loads(rendered)
        self.assertIn('\\x1b', r['details'][0]['before'])
        self.assertIn('\\\\', r['details'][0]['before'])

    def test_context_bounds(self):
        r = g.review(('é'*100 + '\u200b' + 'é'*100).encode())['details'][0]
        self.assertEqual(len(r['before']), 64)
        self.assertEqual(len(r['after']), 64)

    def test_empty(self):
        self.assertEqual(g.review(b'')['findings'], 0)

    def test_input_errors(self):
        for raw in [b'\xff', b'x'*(g.MAX_BYTES+1), 'text']:
            with self.assertRaises((ValueError, UnicodeError)):
                g.review(raw)
        for cap in [0, -1, 1001, True, 1.2]:
            with self.assertRaises(ValueError):
                g.review(b'', max_details=cap)
        with self.assertRaises(ValueError):
            g.review(b'', source='x'*1025)

    def test_large_input_retains_counts(self):
        r = g.review(b'\t'*g.MAX_BYTES, max_details=1)
        self.assertEqual(r['findings'], g.MAX_BYTES)
        self.assertEqual(r['kind_counts'], {'tab': g.MAX_BYTES})
        self.assertEqual(r['omitted_details'], g.MAX_BYTES-1)

    def test_seeded_byte_oracle(self):
        rng = random.Random(731)
        # Expected selected positions assembled independently of the classifier.
        pool = [('é', False), ('\n', False), ('a', False), (' ', False),
                ('\t', True), ('\u200b', True), ('\u00a0', True), ('\U000e0100', True)]
        for _ in range(100):
            raw, expected = b'', []
            for _ in range(100):
                char, selected = rng.choice(pool)
                data = char.encode()
                if selected:
                    expected.append((len(raw), len(raw)+len(data)))
                raw += data
            r = g.review(raw, max_details=1000)
            self.assertEqual([(x['byte_start'], x['byte_end']) for x in r['details']], expected)

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, '-B', str(HERE/'unicode_gaps.py'), *args],
                              cwd=cwd or ROOT, capture_output=True)

    def test_cli_demo_and_errors(self):
        self.assertEqual(self.run_cli('--demo').returncode, 0)
        for args in [[], ['--demo', '--max-details', '0'], ['--file', 'missing-file'],
                     ['--file', '../outside-workspace']]:
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout, b'')
            self.assertTrue(r.stderr.isascii())

    def test_cli_files_and_portability(self):
        scratch = ROOT / 'test/scratch/unicode-gaps'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            folder = Path(folder)
            (folder/'unicode_gaps.py').write_bytes((HERE/'unicode_gaps.py').read_bytes())
            for name, raw, status in [('clean.txt', b'normal', 0),
                                      ('gap.txt', 'pay\u200bload'.encode(), 1),
                                      ('bad.txt', b'\xff', 2)]:
                (folder/name).write_bytes(raw)
                r = subprocess.run([sys.executable, '-B', 'unicode_gaps.py', '--file', name],
                                   cwd=folder, capture_output=True)
                self.assertEqual(r.returncode, status)
                if status != 2:
                    self.assertEqual(json.loads(r.stdout)['source_bytes'], len(raw))
                else:
                    self.assertEqual(r.stdout, b'')
            (folder/'escape.txt').symlink_to(ROOT / 'line-2/GOAL.md')
            r = self.run_cli('--file', 'escape.txt', cwd=folder)
            self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
