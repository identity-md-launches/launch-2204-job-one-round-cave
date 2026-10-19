#!/usr/bin/env python3
"""Bounded leave-one-declared-cluster-out diagnostics for paired binary evidence."""
import argparse
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import sys

import ladder_engine as engine

MAX_CASES = 2000
MAX_CLUSTERS = 128


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def read_mapping(raw, ids):
    if len(raw) > engine.MAX_BYTES:
        raise ValueError('mapping exceeds 2 MiB')
    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    if next(reader, None) != ['case', 'cluster']:
        raise ValueError('mapping header must be case,cluster')
    assignments = {}
    for row in reader:
        if len(row) != 2 or any(not engine.valid_id(s) for s in row):
            raise ValueError('mapping requires two nonempty IDs without controls or edge whitespace')
        case, cluster = row
        if case in assignments:
            raise ValueError('duplicate mapping case')
        assignments[case] = cluster
        if len(assignments) > MAX_CASES:
            raise ValueError('too many mapping cases')
    if set(assignments) != set(ids):
        raise ValueError('mapping must cover exactly all CSV case IDs')
    # Order follows first occurrence in the benchmark, independent of mapping row order.
    groups = {}
    for index, case in enumerate(ids):
        groups.setdefault(assignments[case], []).append(index)
    if not 2 <= len(groups) <= MAX_CLUSTERS:
        raise ValueError('requires 2 through 128 nonempty disjoint clusters')
    return groups


def encoded(names, ids, rows):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['case', 'baseline', *names])
    writer.writerows([case, *row] for case, row in zip(ids, rows))
    return out.getvalue().encode('utf-8')


def review(raw, mapping, alpha_text='0.05', max_details=20):
    alpha = engine.parse_alpha(alpha_text)
    if type(max_details) is not int or not 0 <= max_details <= MAX_CLUSTERS:
        raise ValueError('max-details must be 0 through 128')
    names, rows = engine.read_csv_bytes(raw)
    if not 2 <= len(rows) <= MAX_CASES:
        raise ValueError('requires 2 through 2000 cases')
    parsed = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
    ids = [r[0] for r in parsed[1:]]
    groups = read_mapping(mapping, ids)
    base = engine.analyze(raw, names, rows, alpha)
    summaries = [{'name': n, 'decision_changes': 0, 'direction_changes': 0} for n in names]
    effects = [[] for _ in names]
    details = []
    changed_groups = 0
    complete = hashlib.sha256()
    for group, indexes in groups.items():
        removed = set(indexes)
        kept = [i for i in range(len(rows)) if i not in removed]
        subset = encoded(names, [ids[i] for i in kept], [rows[i] for i in kept])
        analysis = engine.analyze(subset, names, [rows[i] for i in kept], alpha)
        comparisons = []
        for i, (old, new) in enumerate(zip(base['candidates'], analysis['candidates'])):
            effect = Fraction(new['candidate_only_pass'] - new['baseline_only_pass'], len(kept))
            effects[i].append(effect)
            decision = new['familywise_reject_equal_discordance'] != old['familywise_reject_equal_discordance']
            direction = new['observed_direction'] != old['observed_direction']
            summaries[i]['decision_changes'] += decision
            summaries[i]['direction_changes'] += direction
            comparisons.append({'name': names[i], 'effect': rational(effect),
                                'holm_adjusted_p': new['holm_adjusted_p'],
                                'reject_equal_discordance': new['familywise_reject_equal_discordance'],
                                'direction': new['observed_direction'],
                                'decision_changed': decision, 'direction_changed': direction})
        changed = any(c['decision_changed'] or c['direction_changed'] for c in comparisons)
        changed_groups += changed
        item = {'removed_cluster': group, 'removed_cases': len(removed),
                'remaining_cases': len(kept), 'changes_decision_or_direction': changed,
                'candidates': comparisons}
        complete.update(canonical(item) + b'\n')
        if len(details) < max_details:
            details.append(item)
    for i, summary in enumerate(summaries):
        summary['minimum_effect'] = rational(min(effects[i]))
        summary['maximum_effect'] = rational(max(effects[i]))
    return {'schema': 'cluster-influence-v1', 'input_sha256': digest(raw),
            'mapping_sha256': digest(mapping), 'full_data_analysis': base,
            'clusters_checked': len(groups),
            'cluster_sizes': [{'cluster': g, 'cases': len(v)} for g, v in groups.items()],
            'clusters_changing_decision_or_direction': changed_groups,
            'candidates': summaries, 'details': details,
            'details_omitted': len(groups) - len(details),
            'complete_diagnostics_sha256': complete.hexdigest(),
            'effect_units': 'candidate pass fraction minus baseline pass fraction, case weighted',
            'limitations': [
                'Declared clusters are assertions, not discovered or verified independence groups.',
                'All p-values retain the original case-level independence assumption; this is not cluster-adjusted inference.',
                'These overlapping deletions are diagnostics, not replacement analyses or multiple-testing-corrected new claims.',
                'Retain the complete original family and full-data result; do not select groups to delete.',
                'Stability under one group deletion does not cover multiple groups, wrong labels, selection or population validity.',
                'Group sizes can differ; effects weight remaining cases equally, not clusters equally.',
                'Pins identify bytes, not authenticity, preregistration time or honest outcomes.'
            ]}


def demo_inputs():
    names = ['first', 'second']
    ids = ['synthetic-' + str(i) for i in range(12)]
    raw = encoded(names, ids, [(0, 1, 1)] * 10 + [(1, 1, 1)] * 2)
    mapping = ('case,cluster\n' + ''.join(f'{case},{"related-a" if i < 5 else "related-b" if i < 10 else "agreement"}\n'
                                          for i, case in enumerate(ids))).encode()
    return raw, mapping


def workspace_bytes(name):
    root = Path.cwd().resolve()
    path = Path(name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('input must resolve to a regular file inside the workspace')
    with path.open('rb') as handle:
        raw = handle.read(engine.MAX_BYTES + 1)
    if len(raw) > engine.MAX_BYTES:
        raise ValueError('input exceeds 2 MiB')
    return raw


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--input')
    p.add_argument('--mapping')
    p.add_argument('--expected-input-sha256')
    p.add_argument('--expected-mapping-sha256')
    p.add_argument('--alpha', default='0.05')
    p.add_argument('--max-details', type=int, default=20)
    args = p.parse_args(argv)
    try:
        external = [args.input, args.mapping, args.expected_input_sha256, args.expected_mapping_sha256]
        if args.demo:
            if any(x is not None for x in external):
                raise ValueError('--demo cannot be combined with input files or pins')
            raw, mapping = demo_inputs()
        else:
            if not all(external):
                raise ValueError('supply both input files and both independently retained SHA-256 pins')
            raw, mapping = workspace_bytes(args.input), workspace_bytes(args.mapping)
            if digest(raw) != args.expected_input_sha256 or digest(mapping) != args.expected_mapping_sha256:
                raise ValueError('input or mapping SHA-256 differs from retained pin')
        result = review(raw, mapping, args.alpha, args.max_details)
        result['data_kind'] = 'synthetic_demonstration' if args.demo else 'user_supplied_benchmark'
        output = json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False)
    except (ValueError, OSError, csv.Error) as exc:
        p.exit(2, 'error: ' + ascii(str(exc))[:240] + '\n')
    sys.stdout.write(output + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
