#!/usr/bin/env python3
"""Replay a timeline and inspect the exact embedded UTF-8 log bytes together."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'engines'))
import timeline_replay as replay
import unicode_gaps as gaps

SCHEMA = 'log-spacing-review/1'
MAX_BYTES = 16 * 1024 * 1024
SOURCE_NAMES = ('log_spacing_review.py', 'engines/unicode_gaps.py',
                'engines/timeline_replay.py', 'engines/vendor/time_flint.py',
                'engines/vendor/__init__.py')


def canonical(value):
    return replay.canonical(value)


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def source_hashes():
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in SOURCE_NAMES}


def create(pack, max_details=20):
    if type(max_details) is not int or not 1 <= max_details <= 1000:
        raise ValueError('max_details must be 1..1000 per source')
    if len(canonical(pack)) > MAX_BYTES:
        raise ValueError('pack exceeds combined byte limit')
    verified = replay.verify_pack(pack)
    timeline = pack['timeline']
    reports = []
    for item in pack['inputs']:
        name = item['source']
        raw = base64.b64decode(item['base64'], validate=True)
        # Scan the whole original source, including BOM, CRLF and undated lines.
        # Do not scan normalized messages: offsets must cite original bytes.
        report = gaps.review(raw, source=name, max_details=max_details)
        event_lines = {e['line'] for e in timeline['events'] if e['source'] == name}
        omitted_lines = {e['line'] for e in timeline['omitted'] if e['source'] == name}
        for detail in report['details']:
            line = detail['line']
            detail['timeline_disposition'] = ('event' if line in event_lines else
                'omitted' if line in omitted_lines else 'blank-or-unrepresented')
        reports.append(report)
    result = {'schema': SCHEMA, 'sources_sha256': source_hashes(),
              'pack': copy.deepcopy(pack), 'max_details': max_details,
              'timeline_replay': verified, 'source_reviews': reports,
              'findings': sum(r['findings'] for r in reports),
              'retained_details': sum(r['retained_details'] for r in reports),
              'omitted_details': sum(r['omitted_details'] for r in reports),
              'limitations': [
                  'Literal source bytes only; JSON escapes are not decoded for Unicode review.',
                  'Findings are review candidates, not proof of deception or rendering behavior.',
                  'Only LF advances line numbers in both engines; BOM and CRLF bytes stay in citations.',
                  'Clock assumptions are asserted, not measured. Timeline compatibility is not causality.',
                  'Embedded logs and contexts are unredacted; source labels are inert and never reopened.',
                  'A retained independent digest binds content, not authorship, input truth or creation time.',
                  'Unicode database version is part of replay; different runtime tables may reject a receipt.']}
    result['receipt_sha256'] = digest(result)
    if len(canonical(result)) > MAX_BYTES:
        raise ValueError('combined receipt exceeds 16 MiB')
    return result


def verify(receipt, expected_sha256=None):
    if type(receipt) is not dict or 'receipt_sha256' not in receipt:
        raise ValueError('expected a log-spacing receipt')
    if len(canonical(receipt)) > MAX_BYTES:
        raise ValueError('receipt exceeds 16 MiB')
    payload = {k: v for k, v in receipt.items() if k != 'receipt_sha256'}
    actual = digest(payload)
    if type(receipt['receipt_sha256']) is not str or receipt['receipt_sha256'] != actual:
        raise ValueError('receipt content digest mismatch')
    if expected_sha256 is not None:
        if type(expected_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
            raise ValueError('retained digest must be 64 lowercase hex digits')
        if actual != expected_sha256:
            raise ValueError('receipt differs from independently retained digest')
    if receipt.get('sources_sha256') != source_hashes():
        raise ValueError('shipped source hashes differ')
    if 'pack' not in receipt or 'max_details' not in receipt:
        raise ValueError('receipt is missing inputs')
    recomputed = create(receipt['pack'], receipt['max_details'])
    if canonical(recomputed) != canonical(receipt):
        raise ValueError('receipt differs from complete replay')
    return {'verified': True, 'receipt_sha256': actual,
            'findings': recomputed['findings'],
            'retained_details': recomputed['retained_details'],
            'omitted_details': recomputed['omitted_details'],
            'timeline_replay': recomputed['timeline_replay']}


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('input exceeds 16 MiB')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=replay.engine.unique_object,
                       parse_constant=replay.engine.reject_constant)
    replay.engine.check_json_depth(value)
    return value


def demo_pack():
    return replay.make_pack([
        ('synthetic.log', ('\ufeff2026-10-18T10:00:00Z pay\u200bload\r\n'
                           'undated\u00a0diagnostic\n'
                           '2026-10-18T10:00:01Z done\tvalue\n').encode()),
        ('synthetic.jsonl', b'{"ts":1792317602000,"message":"literal \\u200b escape"}\n')],
        ignore_unmatched=True, clock_uncertainty_ms=750)


def demo():
    receipt = create(demo_pack(), 2)
    altered = copy.deepcopy(receipt)
    altered['source_reviews'][0]['details'][0]['byte_start'] += 1
    altered['receipt_sha256'] = digest({k: v for k, v in altered.items() if k != 'receipt_sha256'})
    try:
        verify(altered)
    except ValueError:
        rejected = True
    else:
        raise ValueError('demo failed to reject changed citation')
    return {'data_kind': 'synthetic_demonstration', 'receipt': receipt,
            'replay': verify(receipt, receipt['receipt_sha256']),
            'rehashed_citation_forgery_rejected': rejected}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    make = sub.add_parser('create', help='read a timeline-replay pack from stdin')
    make.add_argument('--max-details', type=int, default=20)
    check = sub.add_parser('verify', help='read a combined receipt from stdin')
    check.add_argument('--expected-sha256')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'create':
            result = create(decode(sys.stdin.buffer.read(MAX_BYTES + 1)), args.max_details)
        else:
            result = verify(decode(sys.stdin.buffer.read(MAX_BYTES + 1)), args.expected_sha256)
        sys.stdout.buffer.write(canonical(result) + b'\n')
        return 1 if args.command != 'demo' and result['findings'] else 0
    except (ValueError, OSError, RecursionError, KeyError, TypeError) as error:
        sys.stderr.write(json.dumps({'error': str(error)}, ensure_ascii=True) + '\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
