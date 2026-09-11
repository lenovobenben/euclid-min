"""Decode the local GGB and build a 15 E certificate using exact Sage replay.

Run with Sage Python and PYTHONPATH=<repository>/sage. Embedded JavaScript is
never executed. Cached coordinates identify source branches only; all geometry,
scores, and target identities are recomputed exactly from the two initial points.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from fractions import Fraction
from pathlib import Path

from sage.all import QQ, QQbar
from euclid_min.formats import construction_sha256, load_profile
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = HERE / '正17边形.ggb'
SOURCE_SHA256 = '4142700f7f7de84fa65b8546ecafd87b1abc037e6722b81fe9940b98483eb838'
# Exact lexicographic indices after mapping source A -> (0,0), B -> (1,0).
# GeoGebra's own indices are different and are not copied into the certificate.
INDICES = {'C':0,'D':1,'E':0,'F':0,'G':1,'H':1,'I':0,'J':1,'K':1,
           'L':1,'M':0,'N':1,'O':0,'P':0,'Q':1,'R':0}


def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def build_program():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    with zipfile.ZipFile(SOURCE) as archive:
        construction = ET.fromstring(archive.read('geogebra.xml')).find('construction')
    elements = {e.get('label'):e for e in construction.findall('element')}
    outputs = {v for c in construction.findall('command') for v in c.find('output').attrib.values()}
    free_points = [n for n,e in elements.items() if e.get('type')=='point' and n not in outputs]
    assert free_points == ['A','B']
    names = {'A':'O','B':'A','c':'unit_circle'}
    program = []
    for command in construction.findall('command'):
        op = command.get('name')
        args = list(command.find('input').attrib.values())
        label = command.find('output').get('a0')
        if op == 'Angle':
            assert args == ['C','A','Q']
            continue  # Measurement only; no drawable is produced.
        if label == 'c':
            assert op == 'Circle' and args == ['A','B']
            continue  # The profile gives precisely this initial circle for free.
        identifier = 'ggb_'+label
        if op == 'Line':
            assert len(args)==2
            entry = {'id':identifier,'op':'line','through':[names[a] for a in args]}
        elif op == 'Circle':
            assert len(args)==2
            entry = {'id':identifier,'op':'circle','center':names[args[0]],'through':names[args[1]]}
        elif op == 'Intersect':
            entry = {'id':identifier,'op':'intersect','objects':[names[a] for a in args[:2]],'index':INDICES[label]}
        else:
            raise ValueError('Unexpected geometric command: '+op)
        names[label] = identifier
        program.append(entry)
    return program, elements, names


def main():
    profile = load_profile(ROOT / 'profiles/regular-17-e-fixed-v1.yaml')
    program, elements, mapping = build_program()
    original = ProgramReplayer().replay(program)

    def cached(label):
        coords = elements[label].find('coords')
        # Parse the stored decimal strings as exact rational numbers. They are
        # only source-branch locators, never construction inputs.
        def rational(text):
            value = Fraction(text)
            return QQ(value.numerator)/value.denominator
        return tuple(rational(coords.get(k))/rational(coords.get('z')) for k in ('x','y'))
    ax,ay = cached('A'); bx,by = cached('B'); dx,dy=bx-ax,by-ay
    norm = dx*dx+dy*dy
    assert norm > 0
    branch_checks = {}
    for label in INDICES:
        x,y = cached(label); x-=ax; y-=ay
        normalized = ((dx*x+dy*y)/norm,(-dy*x+dx*y)/norm)
        entry = next(e for e in program if e['id']==mapping[label])
        alternatives = intersect(*(original.names[n] for n in entry['objects'])).points
        distances = [(p.x-normalized[0])**2+(p.y-normalized[1])**2 for p in alternatives]
        selected = entry['index']
        branch_checks[label] = all(
            i==selected or distances[selected]<distance
            for i,distance in enumerate(distances)
        )
    assert all(branch_checks.values())

    z = QQbar.zeta(17)
    def is_vertex(replay,label,k):
        p = replay.names[label]
        return bool(QQbar(p.x)+QQbar.gen()*QQbar(p.y) == z**k)
    checks = {
        'Q_equals_zeta17_power_5':is_vertex(original,'ggb_Q',5),
        'R_equals_zeta17_power_minus_5':is_vertex(original,'ggb_R',-5),
        'original_is_12_e':original.e_move==12,
        'original_has_no_profile_target':len(original.targets)==0,
        'original_has_no_duplicate_draws':original.duplicate_draws==0,
    }
    assert all(checks.values())
    extra = [
        {'id':'extra_circle_13','op':'circle','center':'ggb_Q','through':'A'},
        {'id':'vertex_10','op':'intersect','objects':['unit_circle','extra_circle_13'],'index':0},
        {'id':'extra_circle_14','op':'circle','center':'vertex_10','through':'A'},
        {'id':'vertex_3','op':'intersect','objects':['unit_circle','extra_circle_14'],'index':0},
        {'id':'extra_circle_15','op':'circle','center':'vertex_3','through':'ggb_Q'},
        {'id':'adjacent_vertex','op':'intersect','objects':['unit_circle','extra_circle_15'],'index':1},
    ]
    adapted = ProgramReplayer().replay(program+extra)
    for label,k in [('vertex_10',10),('vertex_3',3),('adjacent_vertex',1)]:
        checks[label+'_equals_zeta17_power_'+str(k)] = is_vertex(adapted,label,k)
    checks['adapted_first_target_at_15_e'] = adapted.first_target_e_move==15
    checks['adapted_no_duplicate_draws'] = adapted.duplicate_draws==0
    assert all(checks.values())

    construction = {
        'id':'local-geogebra-adapted-15e',
        'title':'QQ 讨论组提供的 GeoGebra 文件追加三个圆后的 15 E 构造（首创者未确认）',
        'program':program+extra,
    }
    save('construction-15e.json',{
        'schema':'euclid-min-certificate/v1','problem':'regular-17-adjacent-vertex',
        'profile':{'id':profile.data['id'],'sha256':profile.sha256},
        'construction':construction,
        'assertions':{'score':{'metric':'e_move','e_move':15},'targets':['B_plus'],'claim':'verified_construction'},
        'software':{'producer':{'name':'local-geogebra-audit','version':'1.0.0'}},
        'integrity':{'construction_sha256':construction_sha256(construction)},
    })
    save('original-program.json',{'program':program,'score':12,'targets':[],'note':'合法的 12 E 程序，但不是当前 profile 的成功证书。'})
    report = {
        'source_file':SOURCE.name,'source_sha256':SOURCE_SHA256,
        'source_channel':'QQ discussion group; relayed to the project by the user',
        'original_creator':None,'originality_status':'not_established',
        'coordinate_mapping':'source A -> O=(0,0), source B -> A=(1,0), orientation-preserving similarity',
        'checks':checks,'all_checks_passed':all(checks.values()),
        'cached_branch_check_method':'Exact rational parsing of XML decimal strings, followed by exact algebraic squared-distance comparisons; no tolerance',
        'exact_cached_branch_checks':branch_checks,
        'original':{'lines':original.line_draws,'circles':original.circle_draws,'e_move':original.e_move,'targets':[]},
        'adapted':{'lines':adapted.line_draws,'circles':adapted.circle_draws,'e_move':adapted.e_move,'targets':[t.value for t in adapted.targets],'first_target_e_move':adapted.first_target_e_move},
        'Q_x_minimal_polynomial':str(original.names['ggb_Q'].x.minpoly()),
    }
    save('exact-audit.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
