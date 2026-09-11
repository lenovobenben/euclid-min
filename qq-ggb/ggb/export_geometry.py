"""Export a verified oracle for the editable GeoGebra presentation.

Run with Sage Python and PYTHONPATH=<repository>/sage. Decimal coordinates
are display/compatibility data only; both exact replayers run before export.
"""
import hashlib
import json
import sys
from pathlib import Path

from sage.all import AA, QQ
from euclid_min.formats import construction_sha256, load_profile
from euclid_min.geometry import Point
from euclid_min.replay import ProgramReplayer

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
ROOT = SOURCE.parent
sys.path.insert(0, str(SOURCE))
from independent_certificate_check import replay as independent_replay, radical_points


def decimal(value):
    scale = 10**16
    n = int((AA(value) * scale + QQ(1)/2).floor())
    whole, fraction = divmod(abs(n), scale)
    return ('-' if n < 0 else '') + str(whole) + '.' + str(fraction).zfill(16)


def main():
    raw = (SOURCE / 'construction-12e-011.json').read_bytes()
    certificate = json.loads(raw)
    profile = load_profile(ROOT / 'profiles/regular-17-e-fixed-v1.yaml')
    assert profile.sha256 == certificate['profile']['sha256']
    assert construction_sha256(certificate['construction']) == certificate['integrity']['construction_sha256']
    program = certificate['construction']['program']
    result = ProgramReplayer().replay(program)
    independent, names = independent_replay(certificate)
    assert (result.e_move, result.line_draws, result.circle_draws,
            result.first_target_e_move, result.duplicate_draws) == (12, 3, 9, 12, 0)
    assert independent['score'] == independent['first_target_e_move'] == 12
    radicals = radical_points()
    labels = {'O': 'O', 'A': 'A', 'unit_circle': 'c',
              'ggb_O': 'U', 'ggb_Q': 'B_plus', 'ggb_R': 'B_minus'}
    labels.update({e['id']: labels.get(e['id'], e['id'].removeprefix('ggb_')) for e in program})
    births = {'O': 0, 'A': 0, 'unit_circle': 0}
    steps = []
    last_use = {}
    for entry in program:
        if entry['op'] == 'intersect':
            births[entry['id']] = max(births[n] for n in entry['objects'])
        else:
            e = len(steps) + 1
            births[entry['id']] = e
            refs = entry['through'] if entry['op'] == 'line' else [entry['center'], entry['through']]
            assert all(births[r] < e for r in refs)
            last_use.update({r: e for r in refs})
            steps.append({'e': e, 'label': labels[entry['id']], 'op': entry['op'],
                          'refs': [labels[r] for r in refs]})
    points = {}
    for name, value in result.names.items():
        if isinstance(value, Point):
            assert names[name] == ('point', (value.x, value.y))
            assert radicals[name] == (value.x, value.y)
            points[labels[name]] = {
                'xy': [decimal(value.x), decimal(value.y)],
                'birth': births[name], 'last_use': last_use.get(name, births[name]),
            }
    data = {
        'schema': 'euclid-min-geogebra-oracle/v1',
        'certificate_sha256': hashlib.sha256(raw).hexdigest(),
        'construction_sha256': certificate['integrity']['construction_sha256'],
        'profile_sha256': profile.sha256,
        'certificate': certificate, 'labels': labels, 'points': points, 'steps': steps,
        'verified': {'e_move': 12, 'lines': 3, 'paid_circles': 9,
                     'first_target_e_move': 12, 'exact_point_comparisons': len(points),
                     'independent_replay': True, 'radical_correspondence': True},
        'decimal_role': 'Display and GeoGebra compatibility checks only; never an exact mathematical proof.',
    }
    (HERE / 'geometry.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(data['verified']))


if __name__ == '__main__':
    main()
