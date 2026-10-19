import base64
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import log_spacing_review as app


def rehash(value):
    value['receipt_sha256'] = app.digest({k: v for k, v in value.items() if k != 'receipt_sha256'})
    return value


class ReviewTests(unittest.TestCase):
    def test_original_bytes_and_dispositions(self):
        receipt = app.create(app.demo_pack(), 100)
        self.assertEqual(receipt['findings'], 4)
        report = receipt['source_reviews'][0]
        self.assertEqual([x['timeline_disposition'] for x in report['details']],
                         ['event', 'event', 'omitted', 'event'])
        raw = base64.b64decode(receipt['pack']['inputs'][0]['base64'])
        for detail in report['details']:
            self.assertEqual(raw[detail['byte_start']:detail['byte_end']].hex(), detail['bytes_hex'])
        self.assertEqual(receipt['source_reviews'][1]['findings'], 0)
        self.assertEqual(receipt['timeline_replay']['events'], 3)
        self.assertEqual(receipt['timeline_replay']['omitted'], 1)

    def test_detail_cap_preserves_full_counts(self):
        one = app.create(app.demo_pack(), 1)
        full = app.create(app.demo_pack(), 100)
        self.assertEqual(one['findings'], full['findings'])
        self.assertEqual((one['retained_details'], one['omitted_details']), (1, 3))
        self.assertTrue(app.verify(one)['verified'])

    def test_cap_does_not_hide_undated_only_findings(self):
        pack = app.replay.make_pack([('a', b'2026-10-18T10:00:00Z clean\nundated\tline\n')], True)
        value = app.create(pack, 1)
        self.assertEqual(value['findings'], 1)
        self.assertEqual(value['source_reviews'][0]['details'][0]['timeline_disposition'], 'omitted')

    def test_input_immutable_and_roundtrip(self):
        pack = app.demo_pack()
        before = copy.deepcopy(pack)
        value = app.create(pack)
        self.assertEqual(pack, before)
        self.assertTrue(app.verify(app.decode(app.canonical(value)), value['receipt_sha256'])['verified'])
        pack['options']['clock_uncertainty_ms'] = 0
        self.assertEqual(value['pack'], before)

    def test_rehashed_forged_outputs_rejected(self):
        for mutation in (
            lambda r: r.update(findings=0),
            lambda r: r.update(findings=True),
            lambda r: r['source_reviews'][0]['details'][0].update(byte_start=1),
            lambda r: r['source_reviews'][0]['details'][0].update(timeline_disposition='omitted'),
            lambda r: r['pack']['timeline']['events'][0].update(message='changed'),
            lambda r: r.update(extra='unrecognized')):
            value = app.create(app.demo_pack())
            mutation(value)
            with self.assertRaises(ValueError):
                app.verify(rehash(value))

    def test_detached_clean_report_rejected(self):
        dirty = app.create(app.demo_pack())
        clean = app.create(app.replay.make_pack([('clean', b'2026-10-18T10:00:00Z ok\n')]))
        dirty['source_reviews'] = clean['source_reviews']
        with self.assertRaises(ValueError):
            app.verify(rehash(dirty))

    def test_pin_and_source_drift(self):
        value = app.create(app.demo_pack())
        for pin in ('f'*64, 'bad', True):
            with self.assertRaises(ValueError):
                app.verify(value, pin)
        value['sources_sha256']['engines/unicode_gaps.py'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'source hashes'):
            app.verify(rehash(value))

    def test_source_labels_are_inert_and_terminal_output_escaped(self):
        pack = app.replay.make_pack([('../../never-open\u202e\x1b',
                    b'2026-10-18T10:00:00Z x\t\n')])
        value = app.create(pack)
        output = app.canonical(value)
        self.assertTrue(all(b == 10 or 32 <= b <= 126 for b in output))
        self.assertTrue(app.verify(value)['verified'])

    def test_invalid_data_caps_and_decoder(self):
        for cap in (0, 1001, True, 1.5):
            with self.assertRaises(ValueError):
                app.create(app.demo_pack(), cap)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff',
                    b'x'*(app.MAX_BYTES+1)):
            with self.assertRaises((ValueError, UnicodeError)):
                app.decode(raw)
        for value in (None, {}, []):
            with self.assertRaises(ValueError):
                app.verify(value)

    def test_clean_empty_source_and_unrepresented_line(self):
        pack = app.replay.make_pack([('empty', b''), ('tabs', b'\t\n')], True)
        receipt = app.create(pack)
        self.assertEqual(receipt['findings'], 1)
        self.assertEqual(receipt['source_reviews'][1]['details'][0]['timeline_disposition'],
                         'blank-or-unrepresented')
        self.assertTrue(app.verify(receipt)['verified'])

    def test_portable_cli_findings_clean_errors(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            copied = Path(directory).resolve() / 'portable'
            shutil.copytree(app.HERE, copied)
            command = [sys.executable, '-B', 'log_spacing_review.py']
            clean = app.replay.make_pack([('clean', b'2026-10-18T10:00:00Z ok\n')])
            for pack, expected in ((app.demo_pack(), 1), (clean, 0)):
                made = subprocess.run(command+['create'], cwd=copied,
                    input=app.canonical(pack), capture_output=True, timeout=20)
                self.assertEqual(made.returncode, expected, made.stderr)
                pin = json.loads(made.stdout)['receipt_sha256']
                verified = subprocess.run(command+['verify', '--expected-sha256', pin],
                    cwd=copied, input=made.stdout, capture_output=True, timeout=20)
                self.assertEqual(verified.returncode, expected, verified.stderr)
                self.assertTrue(json.loads(verified.stdout)['verified'])
            bad = subprocess.run(command+['verify'], cwd=copied, input=b'{}', capture_output=True)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(bad.stdout, b'')
            self.assertEqual(subprocess.run(command+['demo'], cwd=copied,
                capture_output=True).returncode, 0)

    def test_snapshot_provenance(self):
        for row in json.loads((app.HERE/'provenance.json').read_text()):
            data = (app.HERE/Path(row['snapshot']).relative_to('shared/log-spacing-review')).read_bytes()
            self.assertEqual(app.hashlib.sha256(data).hexdigest(), row['sha256'])


if __name__ == '__main__':
    unittest.main()
