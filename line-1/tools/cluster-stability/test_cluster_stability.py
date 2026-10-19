import csv
from fractions import Fraction
import hashlib
import io
import itertools
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

import cluster_stability as cs


def rat(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def brute(deltas):
    values = [sum(s*d for s, d in zip(signs, deltas))
              for signs in itertools.product((-1, 1), repeat=len(deltas))]
    return Fraction(sum(abs(v) >= abs(sum(deltas)) for v in values), len(values))


def independent_holm(ps):
    order = sorted(range(len(ps)), key=lambda i: (ps[i], i))
    result = [None] * len(ps)
    for j, i in enumerate(order):
        result[i] = min(Fraction(1), max((len(ps)-k)*ps[order[k]] for k in range(j+1)))
    return result


class Tests(unittest.TestCase):
    def test_exhaustive_polynomial_division(self):
        for n in range(3, 6):
            for ds in itertools.product((-1, 0, 1), repeat=n):
                ps = cs.deletion_pvalues(ds)
                for g, p in enumerate(ps):
                    self.assertEqual(p, brute(ds[:g] + ds[g+1:]))

    def test_unequal_magnitudes_zeros_and_negative_differences(self):
        rng = random.Random(3101)
        for _ in range(150):
            ds = [rng.randint(-8, 8) for _ in range(rng.randint(3, 9))]
            for g, p in enumerate(cs.deletion_pvalues(ds)):
                self.assertEqual(p, brute(ds[:g] + ds[g+1:]))
        self.assertEqual(cs.deletion_pvalues([0, 0, 0]), [Fraction(1)]*3)
        ds = [1]*128
        self.assertEqual(cs.deletion_pvalues(ds), [Fraction(1, 2**126)]*128)
        ds = [999, -1000, 1]
        self.assertEqual(cs.deletion_pvalues(ds), [brute(ds[:g]+ds[g+1:]) for g in range(3)])

    def test_demo_boundary_and_full_result_preserved(self):
        raw, mapping = cs.demo_inputs()
        result = cs.review(raw, mapping)
        self.assertEqual(result['full_data_analysis'], cs.verdict.analyze(raw, mapping, max_details=128))
        self.assertEqual(result['clusters_changing_decision'], 7)
        self.assertEqual(result['clusters_changing_direction'], 0)
        for c in result['full_data_analysis']['candidates']:
            self.assertEqual(rat(c['holm_adjusted_p']), Fraction(1, 32))
            self.assertTrue(c['familywise_reject_sign_exchangeability'])
        for c in result['candidates']:
            self.assertEqual(c['decision_changes'], 7)
            self.assertEqual(rat(c['minimum_holm_adjusted_p']), Fraction(1, 16))
        self.assertTrue(all(not c['familywise_reject_sign_exchangeability']
                            for d in result['details'] for c in d['candidates']))

    def test_seeded_reports_against_independent_enumeration_and_reduced_csv(self):
        rng = random.Random(3131)
        for _ in range(60):
            n, k, g = rng.randint(8, 30), rng.randint(2, 6), rng.randint(3, 7)
            names, ids = [f'candidate-{i}' for i in range(k)], [f'case-{i}' for i in range(n)]
            rows = [tuple(rng.randrange(2) for _ in range(k+1)) for _ in range(n)]
            raw = cs.grouping.encoded(names, ids, rows)
            mapping = ('case,cluster\n' + ''.join(f'{case},g{i%g}\n' for i, case in enumerate(ids))).encode()
            report = cs.review(raw, mapping, max_details=128)
            decision_changes, direction_changes = [0]*k, [0]*k
            for removed, item in enumerate(report['details']):
                kept = [i for i in range(n) if i%g != removed]
                subset = cs.grouping.encoded(names, [ids[i] for i in kept], [rows[i] for i in kept])
                subset_mapping = ('case,cluster\n'+''.join(f'{ids[i]},g{i%g}\n' for i in kept)).encode()
                fresh = cs.verdict.analyze(subset, subset_mapping)
                ps = [brute([sum(row[c]-row[0] for i, row in enumerate(rows) if i%g == h)
                             for h in range(g) if h != removed]) for c in range(1, k+1)]
                for i, (p, adj, actual, old) in enumerate(zip(ps, independent_holm(ps), item['candidates'], report['full_data_analysis']['candidates'])):
                    self.assertEqual(rat(actual['exact_two_sided_p']), p)
                    self.assertEqual(rat(actual['holm_adjusted_p']), adj)
                    self.assertEqual(actual['familywise_reject_sign_exchangeability'], adj <= Fraction(1, 20))
                    self.assertEqual(actual['case_weighted_effect'], fresh['candidates'][i]['case_weighted_effect'])
                    self.assertEqual(actual['holm_adjusted_p'], fresh['candidates'][i]['holm_adjusted_p'])
                    self.assertEqual(actual['observed_direction'], fresh['candidates'][i]['observed_direction'])
                    decision_changes[i] += actual['decision_changed']
                    direction_changes[i] += actual['direction_changed']
            for i, c in enumerate(report['candidates']):
                self.assertEqual(c['decision_changes'], decision_changes[i])
                self.assertEqual(c['direction_changes'], direction_changes[i])

    def test_two_clusters_report_unavailable_not_false_stability(self):
        raw = b'case,baseline,a,b\nx,0,1,1\ny,1,0,1\n'
        mapping = b'case,cluster\nx,g1\ny,g2\n'
        result = cs.review(raw, mapping)
        self.assertEqual(result['deletions_without_inference'], 2)
        self.assertIsNone(result['clusters_changing_decision'])
        self.assertEqual(result['candidates'][0]['direction_changes'], 2)
        for c in result['candidates']:
            self.assertIsNone(c['decision_changes'])
            self.assertIsNone(c['minimum_holm_adjusted_p'])
        for item in result['details']:
            self.assertIn('not_computed', item['inference_status'])
            for c in item['candidates']:
                self.assertIsNone(c['exact_two_sided_p'])
                self.assertIsNone(c['familywise_reject_sign_exchangeability'])
                self.assertIsNone(c['decision_changed'])

    def test_caps_digest_and_mapping_order(self):
        raw, mapping = cs.demo_inputs()
        full = cs.review(raw, mapping, max_details=128)
        for cap in (0, 1, 6, 7, 128):
            report = cs.review(raw, mapping, max_details=cap)
            self.assertEqual(report['details'], full['details'][:cap])
            self.assertEqual(report['details_omitted'], max(0, 7-cap))
            self.assertEqual(report['candidates'], full['candidates'])
            self.assertEqual(report['complete_diagnostics_sha256'], full['complete_diagnostics_sha256'])
        digest = hashlib.sha256(b''.join(cs.grouping.canonical(d)+b'\n' for d in full['details'])).hexdigest()
        self.assertEqual(digest, full['complete_diagnostics_sha256'])
        reversed_mapping = b'\xef\xbb\xbfcase,cluster\r\n'+b'\r\n'.join(reversed(mapping.splitlines()[1:]))+b'\r\n'
        self.assertEqual(cs.review(raw, reversed_mapping)['details'], full['details'])
        self.assertEqual(cs.review(raw, reversed_mapping)['complete_diagnostics_sha256'], digest)

    def test_unicode_quoted_ids_cancellation_and_effect_extrema(self):
        out = io.StringIO(newline='')
        writer = csv.writer(out, lineterminator='\r\n')
        writer.writerows([['case', 'baseline', 'a', 'b'], ['comma,🐸', 0, 1, 1],
                          ['y', 1, 0, 0], ['z', 0, 1, 1], ['w', 1, 0, 1]])
        raw = b'\xef\xbb\xbf'+out.getvalue().encode()
        mapping = 'case,cluster\n"comma,🐸",cancel\ny,cancel\nz,win\nw,loss\n'.encode()
        result = cs.review(raw, mapping)
        self.assertEqual(result['full_data_analysis']['candidates'][0]['zero_clusters'], 1)
        for i, summary in enumerate(result['candidates']):
            effects = [rat(d['candidates'][i]['case_weighted_effect']) for d in result['details']]
            self.assertEqual(rat(summary['minimum_effect']), min(effects))
            self.assertEqual(rat(summary['maximum_effect']), max(effects))

    def test_bad_data_budgets_types_and_alpha(self):
        raw, mapping = cs.demo_inputs()
        for bad in (b'', b'\xff', mapping+mapping.splitlines(keepends=True)[1],
                    b'\n'.join(mapping.splitlines()[:-1]), mapping+b'unknown,g\n',
                    mapping.replace(b'group-0', b' group-0'), b'x'*(2*1024*1024+1)):
            with self.assertRaises((ValueError, csv.Error)):
                cs.review(raw, bad)
        for bad in (b'', b'\xff', raw.replace(b',0,1,1', b',0,1,2'), raw+raw.splitlines(keepends=True)[1]):
            with self.assertRaises(ValueError):
                cs.review(bad, mapping)
        for cap in (-1, 129, True, 1.5):
            with self.assertRaises(ValueError):
                cs.review(raw, mapping, max_details=cap)
        for alpha in ('NaN', '0', '0.21', '1e-7'):
            with self.assertRaises(ValueError):
                cs.review(raw, mapping, alpha)
        for ds in ([1, 1], [0]*129, [999, 999, 3], [True, 1, 1], [1.0, 1, 1]):
            with self.assertRaises(ValueError):
                cs.deletion_pvalues(ds)

    def test_standalone_cli_pins_errors_and_immutability(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            folder = Path(temp).resolve()
            for name in ('cluster_stability.py', 'verdict_engine.py', 'grouping_engine.py', 'ladder_engine.py'):
                shutil.copyfile(Path(__file__).with_name(name), folder/name)
            raw, mapping = cs.demo_inputs()
            (folder/'cases.csv').write_bytes(raw)
            (folder/'groups.csv').write_bytes(mapping)
            args = ['--input', 'cases.csv', '--mapping', 'groups.csv',
                    '--expected-input-sha256', cs.grouping.digest(raw),
                    '--expected-mapping-sha256', cs.grouping.digest(mapping)]
            def run(opts):
                return subprocess.run([sys.executable, '-B', str(folder/'cluster_stability.py'), *opts],
                                      cwd=folder, capture_output=True)
            good = run(args)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(json.loads(good.stdout)['clusters_changing_decision'], 7)
            self.assertEqual(run(['--demo']).returncode, 0)
            for opts in ([], args[:-1]+['bad'], ['--demo', '--input', 'x'],
                         ['--demo', '--alpha', 'NaN'], ['--demo', '--max-details', '129'],
                         args[:1]+['../outside.csv']+args[2:]):
                bad = run(opts)
                self.assertEqual(bad.returncode, 2)
                self.assertEqual(bad.stdout, b'')
            self.assertEqual((folder/'cases.csv').read_bytes(), raw)
            self.assertEqual((folder/'groups.csv').read_bytes(), mapping)
            # An existing file reached through a symlink must still be inside cwd.
            outside = folder.parent/(folder.name+'-outside.csv')
            outside.write_bytes(raw)
            try:
                (folder/'escape.csv').symlink_to(outside)
                bad = run(['--input', 'escape.csv', *args[2:]])
                self.assertEqual(bad.returncode, 2)
                self.assertEqual(bad.stdout, b'')
            finally:
                outside.unlink()

    def test_source_snapshots(self):
        folder = Path(__file__).parent
        for item in json.loads((folder/'provenance.json').read_text())['snapshots']:
            raw = (folder/item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
            self.assertEqual(raw, Path(item['source']).read_bytes())

    def test_retained_policy_measurements_reproduce(self):
        folder = Path(__file__).parent
        raw = (folder/'policy-results.csv').read_bytes()
        mapping = (folder/'policy-groups.csv').read_bytes()
        retained = json.loads((folder/'retained-policy-review.json').read_text())
        actual = cs.review(raw, mapping, max_details=128)
        for key, value in actual.items():
            self.assertEqual(value, retained[key])
        self.assertEqual(actual['candidates'][0]['direction_changes'], 1)
        self.assertEqual(actual['clusters_changing_decision'], 0)


if __name__ == '__main__':
    unittest.main()
