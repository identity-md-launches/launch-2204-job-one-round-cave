#!/usr/bin/env python3
"""Review literal invisible format characters and unusual Unicode spacing offline."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata as ud

MAX_BYTES = 2 * 1024 * 1024
MAX_DETAILS = 1000
DEMO = 'pay\u00a0to\u200bken\nname\u034f\ufe0f = x\u2028next\tvalue\n'.encode('utf-8')


def kind(char):
    """Selected review classes, deliberately not a test of rendered visibility."""
    code = ord(char)
    if ud.category(char) == 'Cf':
        return 'format-character'
    if ud.category(char) in ('Zs', 'Zl', 'Zp') and char != ' ':
        return 'unusual-separator'
    if code == 0x034f:
        return 'combining-grapheme-joiner'
    if 0xfe00 <= code <= 0xfe0f or 0xe0100 <= code <= 0xe01ef:
        return 'variation-selector'
    if char == '\t':
        return 'tab'
    return None


def escape(raw):
    return ''.join(chr(b) if 32 <= b <= 126 and b != 92 else
                   '\\\\' if b == 92 else '\\x%02x' % b for b in raw)


def review(raw, source='<memory>', max_details=100):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('input must be bytes, at most %d bytes' % MAX_BYTES)
    if not isinstance(source, str) or len(source.encode('utf-8')) > 1024:
        raise ValueError('source label must fit 1024 UTF-8 bytes')
    if type(max_details) is not int or not 1 <= max_details <= MAX_DETAILS:
        raise ValueError('max_details must be 1..1000')
    text = raw.decode('utf-8', errors='strict')
    details, counts, points = [], Counter(), Counter()
    offset, line, line_start, total = 0, 1, 0, 0
    for char in text:
        end = offset + len(char.encode('utf-8'))
        category = kind(char)
        if category:
            total += 1
            counts[category] += 1
            point = 'U+%04X' % ord(char)
            points[point] += 1
            if len(details) < max_details:
                details.append(dict(index=total-1, kind=category, codepoint=point,
                                    name=ud.name(char, '<unnamed>'),
                                    unicode_category=ud.category(char),
                                    byte_start=offset, byte_end=end, line=line,
                                    byte_column=offset-line_start+1,
                                    bytes_hex=raw[offset:end].hex(),
                                    before=escape(raw[max(0, offset-16):offset]),
                                    after=escape(raw[end:end+16])))
        if char == '\n':
            line += 1
            line_start = end
        offset = end
    return dict(schema_version=1, tool='unicode-gaps/1', source=source,
                source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw),
                unicode_version=ud.unidata_version, analysis_complete=True,
                findings=total, kind_counts=dict(sorted(counts.items())),
                codepoint_counts=dict(sorted(points.items())),
                retained_details=len(details), omitted_details=total-len(details),
                details=details,
                assessment='review-selected-characters' if total else 'no-covered-characters',
                coordinates='Zero-based half-open original byte ranges; one-based line and '
                            'byte column. Only LF advances line; CR and Unicode separators do not.',
                coverage='Unicode Cf; Zs/Zl/Zp except ASCII space; U+034F; '
                         'U+FE00..FE0F; U+E0100..E01EF; ASCII tab.',
                limitations=[
                    'Review candidates, not proof of deception or actual invisibility.',
                    'Joiners, selectors, spacing and tabs often have legitimate uses.',
                    'No rendering, language parsing, escape decoding, normalization or rewriting.',
                    'Not all default-ignorable characters, combining marks or Unicode risks are covered.',
                    'Context is unredacted, at most 16 bytes per side, and may split UTF-8.',
                    'Totals cover complete input even when details are omitted.',
                    'SHA-256 binds bytes, not authorship, authenticity or safety.'])


def render(report):
    # JSON escaping keeps source labels, controls and excerpts inert in terminals.
    return json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2,
                      allow_nan=False) + '\n'


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, json.dumps({'error': message}, ensure_ascii=True) + '\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--demo', action='store_true')
    group.add_argument('--file', help='explicit UTF-8 file inside current workspace')
    parser.add_argument('--max-details', type=int, default=100)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            raw, source = DEMO, '<synthetic-demo>'
        else:
            root = Path.cwd().resolve()
            path = Path(args.file).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError('input must be a regular file resolving inside current workspace')
            with path.open('rb') as handle:
                raw = handle.read(MAX_BYTES+1)
            source = str(path.relative_to(root))
        report = review(raw, source, args.max_details)
        sys.stdout.write(render(report))
        return 0 if args.demo or report['findings'] == 0 else 1
    except (OSError, UnicodeError, ValueError) as error:
        sys.stderr.write(json.dumps({'error': str(error)}, ensure_ascii=True) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
