#!/usr/bin/env python3
"""Check this gathering's output structure and bytes offline, not visual quality."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from make_preview import decode_png

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://api.imd.fun/artifacts/'
BARE = '1694079b8c096876644b7db6f84112f2550b53ad024540401ad702809cb35941'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def jpeg_size(data):
    assert data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
    pos = 2
    while pos < len(data):
        assert data[pos] == 255
        code = data[pos+1]
        length = struct.unpack_from('>H', data, pos+2)[0]
        if code == 0xc0:
            depth, h, w, channels = struct.unpack_from('>BHHB', data, pos+4)
            assert depth == 8 and channels == 3
            return w, h
        assert code != 0xda, 'missing baseline JPEG frame'
        pos += length + 2
    raise AssertionError('missing JPEG size')


def traits(record):
    assert set(record) == {'name', 'image', 'attributes'}
    result = {a['trait_type']: a['value'] for a in record['attributes']}
    assert len(result) == len(record['attributes'])
    return result


def main():
    png = ROOT / 'artifacts/gathering/wall-v13.png'
    raw = png.read_bytes()
    width, height, current = decode_png(png)
    assert (width, height) == (1254, 1254)
    assert png.is_file() and not png.is_symlink()
    assert not subprocess.run(['git', 'ls-files', '--', 'artifacts/gathering/wall-v13.png'],
                              cwd=ROOT, check=True, capture_output=True).stdout
    alias = ROOT / 'artifacts/gathering/wall.png'
    assert alias.is_symlink() and alias.readlink() == Path('wall-v13.png')
    assert alias.resolve() == png.resolve()
    ancestor = ROOT / 'artifacts/gathering/wall-v12.png'
    _, _, previous = decode_png(ancestor)
    process = read(ROOT / 'gathering/mark-process13.json')
    assert process['ancestor_sha256'] == hashlib.sha256(ancestor.read_bytes()).hexdigest()
    changed = [(x, y) for y in range(height) for x in range(width)
               if current[y][3*x:3*x+3] != previous[y][3*x:3*x+3]]
    x0, y0, x1, y1 = process['destination_box']
    assert len(changed) == process['changed_pixels'] == 1892
    assert all(x0 <= x < x1 and y0 <= y < y1 for x, y in changed)
    digest = hashlib.sha256(raw).hexdigest()
    record = read(ROOT / 'dist/gathering/13.json')
    values = traits(record)
    assert record['image'] == URL + digest
    assert set(values) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert values['Cave'] == 'Roots' and values['Wall'] == 'Gathering'
    assert type(values['Number']) is int and values['Number'] == 13
    assert values['One thing'] == 'Gathering' and values['Left behind'] == 'Log Spacing Review'
    jpg = ROOT / 'dist/gathering/13.jpg'
    assert jpeg_size(jpg.read_bytes()) == (512, 512)
    assert jpg.stat().st_size <= 100000
    one = read(ROOT / 'dist/one.json')
    assert one['name'] == 'One' and one['image'] == URL + digest
    assert traits(one) == {'Cave': 'Roots', 'Wall': 'One', 'Number': 736, 'Meaning': values['Meaning']}
    placeholder = {'name': 'Not painted yet', 'image': URL + BARE,
                   'attributes': [{'trait_type': 'Cave', 'value': 'Roots'}]}
    painted, future = 0, 0
    for wall in ('line-1', 'line-2', 'line-3', 'line-4', 'gathering'):
        folder = ROOT / 'dist' / wall
        assert all((folder / f'{n:02d}.json').is_file() for n in range(1, 22))
        for path in folder.glob('[0-9][0-9].json'):
            item = read(path)
            if item['name'] == 'Not painted yet':
                assert item == placeholder and not path.with_suffix('.jpg').exists()
                future += 1
            else:
                attrs = traits(item)
                expected = 'Gathering' if wall == 'gathering' else 'Line ' + wall[-1]
                assert attrs['Cave'] == 'Roots' and attrs['Wall'] == expected
                assert type(attrs['Number']) is int and attrs['Number'] == int(path.stem)
                assert set(attrs) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
                assert item['image'].startswith(URL) and len(item['image']) == len(URL) + 64
                assert item['image'][len(URL):] == item['image'][len(URL):].lower()
                int(item['image'][len(URL):], 16)
                assert jpeg_size(path.with_suffix('.jpg').read_bytes()) == (512, 512)
                painted += 1
    assert (painted, future) == (57, 88)
    assert read(ROOT / 'dist/goals.json') == [
        {'line': n, 'goal': (ROOT / f'line-{n}/GOAL.md').read_text().strip()} for n in range(1, 5)]
    for prefix in ('line-1', 'line-2', 'line-3', 'line-4',
                   'dist/line-1', 'dist/line-2', 'dist/line-3', 'dist/line-4'):
        assert not subprocess.run(['git', 'diff', 'HEAD', '--', prefix], cwd=ROOT,
                                  check=True, capture_output=True).stdout
        assert not subprocess.run(['git', 'ls-files', '--others', '--exclude-standard', '--', prefix],
                                  cwd=ROOT, check=True, capture_output=True).stdout
    ancestors = subprocess.run(['git', 'ls-files', '-z', '--', 'dist/gathering'], cwd=ROOT,
                               check=True, capture_output=True).stdout.split(b'\0')
    for entry in filter(None, ancestors):
        path = entry.decode()
        if path == 'dist/gathering/13.json':
            continue
        original = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=ROOT,
                                  check=True, capture_output=True).stdout
        assert (ROOT / path).read_bytes() == original, path
    provenance = read(ROOT / 'shared/log-spacing-review/provenance.json')
    for row in provenance:
        snapshot = (ROOT / row['snapshot']).read_bytes()
        assert snapshot == (ROOT / row['source']).read_bytes()
        assert hashlib.sha256(snapshot).hexdigest() == row['sha256']
    for folder in ('gathering', 'shared', 'dist'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file():
                assert path.stat().st_size <= 100000, str(path)
    checks = read(ROOT / 'gathering/check-results.json')
    assert checks['checks_passed'] and checks['line_files_unchanged']
    assert all(x['exit_code'] == 0 and x['tests'] > 0 for x in checks['suites'])
    assert checks['test_count'] == 675
    demos = read(ROOT / 'gathering/demo-results.json')
    assert demos['checks_passed'] and len(demos['examples']) == 77
    assert all(x['passed'] for x in demos['examples'])
    review = read(ROOT / 'gathering/wall-review.json')
    assert review['wall_sha256'] == digest and review['unmet_visual_requirements'] == []
    gallery = read(ROOT / 'gathering/gallery-check.json')
    assert gallery['checks_passed'] and gallery['numbered_cards'] == painted + future
    result = {'structural_checks': 'passed', 'tests_passed': checks['test_count'],
              'cli_examples': len(demos['examples']), 'line_files_unchanged': True,
              'goals': 4, 'numbered_records': painted + future, 'painted_records': painted,
              'future_records': future, 'unchanged_engine_snapshots': len(provenance),
              'wall': {'path': 'artifacts/gathering/wall-v13.png', 'format': 'PNG RGB8',
                       'width': width, 'height': height, 'bytes': len(raw), 'sha256': digest,
                       'declared_output_tracked': False},
              'preview': {'path': 'dist/gathering/13.jpg', 'format': 'JPEG baseline',
                          'width': 512, 'height': 512, 'bytes': jpg.stat().st_size},
              'pixel_preservation': {'changed_pixels': len(changed), 'allowed_box': process['destination_box'],
                                     'all_pixels_outside_added_motif_unchanged': True},
              'unmet_visual_requirements': review['unmet_visual_requirements'],
              'limitations': ['Local checks, not independent certification.',
                              'Gallery structure checked without browser layout certification.',
                              'Small motif loses fine pigment detail in the preview.']}
    (ROOT / 'gathering/validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
