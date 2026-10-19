#!/usr/bin/env python3
"""Exact whole-cluster sign-flip tests for complete paired binary benchmarks."""
import argparse
import csv
from fractions import Fraction
import hashlib
import io
import json
import sys

import grouping_engine as grouping
import ladder_engine as engine


def exact_sign_flip(differences):
    """Count |sum(sign_g * d_g)| >= |sum(d_g)| without enumerating 2**G signs.

    Zero differences can be integrated out: each doubles numerator and denominator.
    Integer dynamic programming keeps all multiplicities, including tied sums.
    """
    if not 2 <= len(differences) <= grouping.MAX_CLUSTERS:
        raise ValueError('requires 2 through 128 cluster differences')
    if any(type(d) is not int for d in differences) or sum(map(abs, differences)) > grouping.MAX_CASES:
        raise ValueError('differences must be integers with total absolute magnitude at most 2000')
    observed = sum(differences)
    distribution = {0: 1}
    nonzero = 0
    for d in differences:
        if not d:
            continue
        nonzero += 1
        following = {}
        for total, count in distribution.items():
            for value in (total - abs(d), total + abs(d)):
                following[value] = following.get(value, 0) + count
        distribution = following
    total_signs = 1 << nonzero
    tail_signs = sum(count for total, count in distribution.items() if abs(total) >= abs(observed))
    if sum(distribution.values()) != total_signs:
        raise ArithmeticError('sign multiplicities were not conserved')
    return {'p': Fraction(tail_signs, total_signs), 'observed': observed,
            'nonzero_clusters': nonzero, 'zero_clusters': len(differences) - nonzero,
            'tail_assignments': str(tail_signs), 'assignments': str(total_signs),
            'distinct_null_sums': len(distribution)}


def holm(ps):
    """Exact adjusted p-values, with deterministic original-order tie breaking."""
    adjusted = [None] * len(ps)
    running = Fraction(0)
    for rank, index in enumerate(sorted(range(len(ps)), key=lambda i: (ps[i], i))):
        running = max(running, min(Fraction(1), (len(ps) - rank) * ps[index]))
        adjusted[index] = running
    return adjusted


def analyze(raw, mapping, alpha_text='0.05', max_details=20):
    alpha = Fraction(engine.parse_alpha(alpha_text))
    if type(max_details) is not int or not 0 <= max_details <= grouping.MAX_CLUSTERS:
        raise ValueError('max-details must be 0 through 128')
    names, rows = engine.read_csv_bytes(raw)
    if not 2 <= len(rows) <= grouping.MAX_CASES:
        raise ValueError('requires 2 through 2000 complete paired cases')
    parsed = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
    ids = [r[0] for r in parsed[1:]]
    groups = grouping.read_mapping(mapping, ids)
    details = []
    columns = [[] for _ in names]
    for label, indexes in groups.items():
        deltas = [sum(rows[j][i + 1] - rows[j][0] for j in indexes) for i in range(len(names))]
        for column, delta in zip(columns, deltas):
            column.append(delta)
        details.append({'cluster': label, 'cases': len(indexes), 'candidate_minus_baseline_passes': deltas})
    tests = [exact_sign_flip(column) for column in columns]
    adjusted = holm([t['p'] for t in tests])
    baseline_passes = sum(row[0] for row in rows)
    candidates = []
    for name, test, adj in zip(names, tests, adjusted):
        item = {k: v for k, v in test.items() if k != 'p'}
        item.update({'name': name, 'candidate_passes': baseline_passes + test['observed'],
                     'case_weighted_effect': grouping.rational(Fraction(test['observed'], len(rows))),
                     'exact_two_sided_p': grouping.rational(test['p']),
                     'holm_adjusted_p': grouping.rational(adj),
                     'familywise_reject_sign_exchangeability': adj <= alpha,
                     'observed_direction': 'candidate' if test['observed'] > 0 else
                                           'baseline' if test['observed'] < 0 else 'tie'})
        candidates.append(item)
    return {'schema': 'cluster-verdict-v1', 'input_sha256': grouping.digest(raw),
            'mapping_sha256': grouping.digest(mapping), 'paired_cases': len(rows),
            'baseline_passes': baseline_passes, 'candidate_count': len(names),
            'clusters': len(groups), 'familywise_alpha': grouping.rational(alpha),
            'method': 'exact two-sided whole-cluster sign-flip; Holm familywise correction',
            'statistic': 'sum of candidate-minus-baseline binary pass differences across all cases',
            'candidates': candidates, 'cluster_details': details[:max_details],
            'cluster_details_omitted': len(details) - min(max_details, len(details)),
            'complete_cluster_details_sha256': hashlib.sha256(grouping.canonical(details)).hexdigest(),
            'assumptions': [
                'For each candidate null, conditional on cluster difference magnitudes, nonzero cluster signs are independent fair signs.',
                'This needs a justified whole-cluster swap randomization under a sharp null, or an independent sign-symmetric cluster-difference model.',
                'Related cases may be dependent within a cluster; all dependence across clusters must be justified absent.',
                'Independent clusters alone, or zero mean alone, do not establish sign exchangeability.',
                'Case set, binary pass rule, cluster partition, full candidate family, alpha and one analysis were fixed before viewing outcomes.',
                'Each cluster is a disjoint nonempty group. Each case has one complete observation for all planned systems.'
            ],
            'limitations': [
                'A declared grouping cannot prove independence or exchangeability; this output does not certify either assumption.',
                'Holm covers the complete supplied candidate family at one planned analysis, not repeated looks or chosen groupings.',
                'Effects weight cases equally; large clusters carry more statistic weight. This is not an equal-cluster mean test.',
                'Zero cluster differences cancel internally and add no sign information even when cases disagree within a group.',
                'Non-rejection is not equivalence; rejection alone is not improvement, practical value or population validity.',
                'Input digests establish byte identity, not honest labels, representative sampling or preregistration time.'
            ]}


def demo_inputs():
    # Ten apparent wins, but only two independent nonzero cluster signs.
    return grouping.demo_inputs()


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
            raw = grouping.workspace_bytes(args.input)
            mapping = grouping.workspace_bytes(args.mapping)
            if grouping.digest(raw) != args.expected_input_sha256 or grouping.digest(mapping) != args.expected_mapping_sha256:
                raise ValueError('input or mapping SHA-256 differs from retained pin')
        report = analyze(raw, mapping, args.alpha, args.max_details)
        report['data_kind'] = 'synthetic_demonstration' if args.demo else 'user_supplied_benchmark'
        output = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, 'error: ' + ascii(str(exc))[:240] + '\n')
    sys.stdout.write(output + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
