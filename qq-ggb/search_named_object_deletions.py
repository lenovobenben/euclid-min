"""Exact deletion/reordering audit within the 12 E baseline's named-point universe.

Allows alternative point sources and object definitions, but no unnamed points
and no new drawable objects. This finite audit is NOT a global 11 E exclusion.
"""
import itertools
import json
from pathlib import Path
from euclid_min.geometry import Circle,Line,Point
from euclid_min.replay import ProgramReplayer

HERE=Path(__file__).resolve().parent
certificate=json.loads((HERE/'construction-12e-011.json').read_text(encoding='utf-8'))
program=certificate['construction']['program']
replay=ProgramReplayer().replay(program)
names=replay.names
points={n:p for n,p in names.items() if isinstance(p,Point)}
objects={n:o for n,o in names.items() if isinstance(o,(Line,Circle))}
paid=[e['id'] for e in program if e['op'] in ('line','circle')]
def is_zero(value):
    return bool(value==0)
def same_point(p,q):
    return is_zero(p.x-q.x) and is_zero(p.y-q.y)
incidence={}
for object_id,obj in objects.items():
    hits=[]
    for point_id,p in points.items():
        residual=obj.a*p.x+obj.b*p.y+obj.c if isinstance(obj,Line) else (p.x-obj.center.x)**2+(p.y-obj.center.y)**2-obj.radius_squared
        if is_zero(residual): hits.append(point_id)
    incidence[object_id]=hits

sources={n:[pair for pair in itertools.combinations(objects,2) if all(n in incidence[o] for o in pair)] for n in points}
definitions={}
for name,obj in objects.items():
    if isinstance(obj,Line):
        definitions[name]=[pair for pair in itertools.combinations(incidence[name],2) if not same_point(points[pair[0]],points[pair[1]])]
    else:
        centers=[n for n,p in points.items() if same_point(p,obj.center)]
        definitions[name]=[(c,t) for c in centers for t in incidence[name] if not same_point(points[c],points[t])]

def closure(removed):
    available_points={'O','A'}
    available_objects={'unit_circle'}
    operations=[]
    while True:
        before=(len(available_points),len(available_objects))
        for p,alternatives in sources.items():
            if any(set(pair)<=available_objects for pair in alternatives): available_points.add(p)
        for o in paid:
            if o==removed or o in available_objects: continue
            witness=next((pair for pair in definitions[o] if set(pair)<=available_points),None)
            if witness is not None:
                available_objects.add(o)
                operations.append({'object':o,'using':list(witness)})
        if before==(len(available_points),len(available_objects)): break
    return {'removed':removed,'reachable_paid_objects':len(available_objects)-1,
            'target_reached':bool({'ggb_Q','ggb_R'} & available_points),
            'missing_objects':[o for o in paid if o!=removed and o not in available_objects],
            'schedule':operations}

control=closure(None)
assert control['target_reached'] and control['reachable_paid_objects']==12
results=[closure(removed) for removed in paid]
report={
 'scope':'All single-object deletions with reordering and alternative definitions, within exactly the 18 named points and 13 original drawable objects of construction-12e-011.json; no unnamed points or new drawable objects',
 'point_count':len(points),'object_count':len(objects),'control':control,
 'results':results,'found_shorter':any(r['target_reached'] for r in results),
 'conclusion':'This only addresses the frozen named-point/object universe; it is not a global lower bound.',
}
(HERE/'named-object-deletion-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('results','control')},indent=2),flush=True)
print([(r['removed'],r['target_reached'],r['reachable_paid_objects']) for r in results],flush=True)
