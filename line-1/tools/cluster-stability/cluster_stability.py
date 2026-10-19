#!/usr/bin/env python3
"""Leave-one-cluster-out diagnostics using exact whole-cluster sign-flip tests."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
import sys

import verdict_engine as verdict

grouping = verdict.grouping


def deletion_pvalues(deltas):
    """Exact p after each deletion, in O(G * sum(abs(d))) integer operations.

    The subset-sum generating polynomial is product(1 + x**abs(d)).
    Divide out one nonzero factor by q[s] = f[s] - q[s-w]. Zero
    differences add no sign information and need no polynomial division.
    """
    if not 3 <= len(deltas) <= grouping.MAX_CLUSTERS:
        raise ValueError('deletion tests require 3 through 128 clusters')
    if any(type(d) is not int for d in deltas) or sum(map(abs, deltas)) > grouping.MAX_CASES:
        raise ValueError('integer differences must have total magnitude at most 2000')
    distribution = [1]
    nonzero = 0
    for d in deltas:
        if d == 0:
            continue
        nonzero += 1
        w = abs(d)
        following = distribution + [0] * w
        for s, count in enumerate(distribution):
            following[s + w] += count
        distribution = following
    magnitude = len(distribution) - 1
    observed = sum(deltas)
    ps = []
    for d in deltas:
        w = abs(d)
        if w:
            reduced = []
            for s in range(magnitude - w + 1):
                reduced.append(distribution[s] - (reduced[s - w] if s >= w else 0))
        else:
            reduced = distribution
        assignments = 1 << (nonzero - bool(w))
        if min(reduced) < 0 or sum(reduced) != assignments:
            raise ArithmeticError('invalid divided sign distribution')
        threshold = abs(observed - d)
        tail = sum(count for s, count in enumerate(reduced)
                   if abs(2 * s - (magnitude - w)) >= threshold)
        ps.append(Fraction(tail, assignments))
    return ps


def direction(value):
    return 'candidate' if value > 0 else 'baseline' if value < 0 else 'tie'


def review(raw, mapping, alpha_text='0.05', max_details=20):
    # The unchanged predecessor validates both complete files and the whole family.
    full = verdict.analyze(raw, mapping, alpha_text, grouping.MAX_CLUSTERS)
    if type(max_details) is not int or not 0 <= max_details <= grouping.MAX_CLUSTERS:
        raise ValueError('max-details must be 0 through 128')
    groups = full['cluster_details']
    count = full['paired_cases']
    names = [c['name'] for c in full['candidates']]
    columns = [[g['candidate_minus_baseline_passes'][i] for g in groups] for i in range(len(names))]
    totals = [sum(column) for column in columns]
    alpha = Fraction(verdict.engine.parse_alpha(alpha_text))
    testable = len(groups) >= 3
    ps = [deletion_pvalues(column) for column in columns] if testable else None
    effects = [[] for _ in names]
    adjusted_values = [[] for _ in names]
    summaries = [{'name': n, 'decision_changes': 0 if testable else None,
                  'direction_changes': 0} for n in names]
    details = []
    complete = hashlib.sha256()
    changed_groups = 0
    direction_groups = 0
    for g, group in enumerate(groups):
        remaining = count - group['cases']
        adjusted = verdict.holm([column[g] for column in ps]) if testable else [None] * len(names)
        comparisons = []
        for i, (name, old, adj) in enumerate(zip(names, full['candidates'], adjusted)):
            difference = totals[i] - columns[i][g]
            effect = Fraction(difference, remaining)
            effects[i].append(effect)
            new_direction = direction(difference)
            direction_changed = new_direction != old['observed_direction']
            decision = adj <= alpha if testable else None
            decision_changed = decision != old['familywise_reject_sign_exchangeability'] if testable else None
            summaries[i]['direction_changes'] += direction_changed
            if testable:
                summaries[i]['decision_changes'] += decision_changed
                adjusted_values[i].append(adj)
            comparisons.append({
                'name': name, 'case_weighted_effect': grouping.rational(effect),
                'observed_direction': new_direction, 'direction_changed': direction_changed,
                'exact_two_sided_p': grouping.rational(ps[i][g]) if testable else None,
                'holm_adjusted_p': grouping.rational(adj) if testable else None,
                'familywise_reject_sign_exchangeability': decision,
                'decision_changed': decision_changed})
        direction_groups += any(c['direction_changed'] for c in comparisons)
        changed = any(c['decision_changed'] for c in comparisons) if testable else None
        if testable:
            changed_groups += changed
        item = {'removed_cluster': group['cluster'], 'removed_cases': group['cases'],
                'remaining_cases': remaining, 'remaining_clusters': len(groups) - 1,
                'inference_status': 'computed_under_asserted_model' if testable else 'not_computed_fewer_than_two_remaining_clusters',
                'any_decision_changed': changed, 'candidates': comparisons}
        complete.update(grouping.canonical(item) + b'\n')
        if len(details) < max_details:
            details.append(item)
    for i, summary in enumerate(summaries):
        summary.update({'minimum_effect': grouping.rational(min(effects[i])),
                        'maximum_effect': grouping.rational(max(effects[i])),
                        'minimum_holm_adjusted_p': grouping.rational(min(adjusted_values[i])) if testable else None,
                        'maximum_holm_adjusted_p': grouping.rational(max(adjusted_values[i])) if testable else None})
    return {'schema': 'cluster-stability-v1', 'input_sha256': grouping.digest(raw),
            'mapping_sha256': grouping.digest(mapping), 'full_data_analysis': full,
            'clusters_reviewed': len(groups), 'deletions_with_inference': len(groups) if testable else 0,
            'deletions_without_inference': 0 if testable else len(groups),
            'clusters_changing_decision': changed_groups if testable else None,
            'clusters_changing_direction': direction_groups, 'candidates': summaries,
            'details': details, 'details_omitted': len(groups) - len(details),
            'complete_diagnostics_sha256': complete.hexdigest(),
            'method': 'leave each declared cluster out; exact whole-cluster sign-flip with Holm over the unchanged candidate family',
            'limitations': [
                'All full-data assumptions remain required; grouping alone does not justify independent fair signs conditional on magnitudes.',
                'Deletions overlap. These are sensitivity diagnostics, not adjusted new claims or permission to remove inconvenient groups.',
                'Retain the complete full-data analysis. Do not select a deletion, grouping, candidate family or alpha after viewing outcomes.',
                'With only two original clusters, deletion inference is unavailable; null is not a non-rejection or stability result.',
                'Single-deletion stability does not establish equivalence, practical value, representative sampling or robustness to multiple deletions.',
                'Effects weight remaining cases, not clusters equally. Pins identify bytes, not honest labels or preregistration time.'
            ]}


def demo_inputs():
    # Seven independent-sign groups give p=1/64; dropping any gives p=1/32.
    # Two identical candidates yield Holm 1/32 and 1/16, straddling alpha=.05.
    ids = ['synthetic-' + str(i) for i in range(7)]
    raw = grouping.encoded(['first', 'second'], ids, [(0, 1, 1)] * 7)
    mapping = ('case,cluster\n' + ''.join(f'{case},group-{i}\n' for i, case in enumerate(ids))).encode()
    return raw, mapping


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--input')
    parser.add_argument('--mapping')
    parser.add_argument('--expected-input-sha256')
    parser.add_argument('--expected-mapping-sha256')
    parser.add_argument('--alpha', default='0.05')
    parser.add_argument('--max-details', type=int, default=20)
    args = parser.parse_args(argv)
    try:
        external = [args.input, args.mapping, args.expected_input_sha256, args.expected_mapping_sha256]
        if args.demo:
            if any(x is not None for x in external):
                raise ValueError('--demo cannot be combined with files or pins')
            raw, mapping = demo_inputs()
        else:
            if not all(external):
                raise ValueError('supply both files and both independently retained SHA-256 pins')
            raw, mapping = grouping.workspace_bytes(args.input), grouping.workspace_bytes(args.mapping)
            if grouping.digest(raw) != args.expected_input_sha256 or grouping.digest(mapping) != args.expected_mapping_sha256:
                raise ValueError('input or mapping SHA-256 differs from retained pin')
        report = review(raw, mapping, args.alpha, args.max_details)
        report['data_kind'] = 'synthetic_demonstration' if args.demo else 'user_supplied_benchmark'
        output = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, 'error: ' + ascii(str(exc))[:240] + '\n')
    sys.stdout.write(output + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
