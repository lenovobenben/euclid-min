"""Exact pair replacement allowing every legal redefinition of retained objects.

All retained geometries and their order are fixed. A point on a retained object
is available before drawing it iff it is free, lies on two earlier objects, or
lies on the replacement and an earlier object. Thus all relevant points can be
precomputed from pairs of baseline objects, without constructing costly new
intersections for rejected replacements. Coincidence with the replacement is
handled separately. No numerical geometry or approximate pruning is used.
"""
import argparse
import hashlib
import itertools
import json
import signal
import time
from pathlib import Path

from euclid_min.geometry import Point,Line,Circle
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.formats import load_profile
from euclid_min.target import adjacent_targets
import search_exact_budget_v2 as support

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/exact-local-v2-2026-09-11'
POINTS=[]
OBJECTS={}
PROGRAM=[]
PAID=[]
PLANS={}


def point_index(point):
    for i,record in enumerate(POINTS):
        if point==record['point']: return i
    POINTS.append({'point':point,'incidents':set(),'free':False})
    return len(POINTS)-1


def available_base(i,previous):
    r=POINTS[i]
    return r['free'] or len(r['incidents'] & previous)>=2


def prepare():
    global PROGRAM,PAID,OBJECTS
    certificate=json.loads((HERE/'construction-12e-011.json').read_text())
    PROGRAM=certificate['construction']['program']
    PAID=[e for e in PROGRAM if e['op'] in ('line','circle')]
    replay=ProgramReplayer().replay(PROGRAM)
    OBJECTS={n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}
    for name in ('O','A'):
        POINTS[point_index(replay.names[name])]['free']=True
    for a,b in itertools.combinations(OBJECTS,2):
        for p in intersect(OBJECTS[a],OBJECTS[b]).points:
            support.simplify_point(p)
            POINTS[point_index(p)]['incidents'].update((a,b))
    # Include every required center, even one on no baseline object.
    for obj in OBJECTS.values():
        if isinstance(obj,Circle): point_index(obj.center)
    for record in POINTS:
        record['incidents'].update(n for n,o in OBJECTS.items() if o.contains(record['point']))
    for window in range(11):
        previous={'unit_circle',*(e['id'] for e in PAID[:window])}
        prefix_indices=[i for i in range(len(POINTS)) if available_base(i,previous)]
        steps=[]
        for entry in PAID[window+2:]:
            name=entry['id']; obj=OBJECTS[name]
            boundary=[i for i,r in enumerate(POINTS) if name in r['incidents']]
            steps.append({'name':name,'previous':set(previous),'boundary':boundary,
              'center':point_index(obj.center) if isinstance(obj,Circle) else None})
            previous.add(name)
        PLANS[window]={'points':prefix_indices,'steps':steps}


def choices(window,replacement):
    """Return exact defining points, or None if this replacement cannot work."""
    memo={}; selected=[]
    duplicate=next((n for n,o in OBJECTS.items() if replacement is not None and support.same_object(o,replacement)),None)
    if duplicate in {'unit_circle',*(e['id'] for e in PAID[:window])}: return None
    def on_replacement(i):
        if i not in memo: memo[i]=replacement is not None and replacement.contains(POINTS[i]['point'])
        return memo[i]
    def available(i,previous):
        if available_base(i,previous): return True
        # If replacement equals an earlier retained object, that one curve
        # cannot witness an intersection with itself.
        return bool(POINTS[i]['incidents'] & (previous-{duplicate})) and on_replacement(i)
    for step in PLANS[window]['steps']:
        name=step['name']; obj=OBJECTS[name]; previous=step['previous']
        if name==duplicate:
            selected.append((name,None)); continue
        center=step['center']
        if center is not None and not available(center,previous): return None
        needed=1 if center is not None else 2
        candidates=sorted(step['boundary'],key=lambda i:not available_base(i,previous))
        boundary=[]
        for i in candidates:
            if available(i,previous): boundary.append(i)
            if len(boundary)==needed: break
        if len(boundary)<needed: return None
        selected.append((name,[center,*boundary] if center is not None else boundary))
    if window==10:
        if replacement is None or not any(replacement.contains(t) for t in support.TARGETS.values()): return None
    return selected


def assemble(window,op,p,q,replacement,selected):
    program=support.prefix(PROGRAM,window)
    replay=ProgramReplayer().replay(program)
    current=dict(replay.names)
    counter=0
    def bind(point):
        nonlocal counter
        for name,value in current.items():
            if isinstance(value,Point) and value==point: return name
        incident=[n for n,o in current.items() if isinstance(o,(Line,Circle)) and o.contains(point)]
        for a,b in itertools.combinations(incident,2):
            if support.same_object(current[a],current[b]): continue
            for index,found in enumerate(intersect(current[a],current[b]).points):
                if found!=point: continue
                counter+=1; name='geometry_point_'+str(counter)
                program.append({'id':name,'op':'intersect','objects':[a,b],'index':index})
                current[name]=point
                return name
        raise AssertionError('Availability predicate produced no legal witness')
    if replacement is not None:
        a=bind(POINTS[p]['point']); b=bind(POINTS[q]['point'])
        program.append(support.draw_entry('replacement',op,a,b))
        current['replacement']=replacement
    for name,indices in selected:
        if indices is None: continue
        a,b=(bind(POINTS[i]['point']) for i in indices)
        kind='circle' if isinstance(OBJECTS[name],Circle) else 'line'
        program.append(support.draw_entry(name,kind,a,b))
        current[name]=OBJECTS[name]
    return program


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,default=300)
    args=parser.parse_args()
    support.RUN=RUN; support.PROFILE=load_profile(HERE.parent/'profiles/regular-17-e-fixed-v1.yaml')
    support.TARGETS=adjacent_targets()
    signal.signal(signal.SIGALRM,support.timeout_handler)
    start=time.monotonic_ns(); deadline=start+args.seconds*1000000000
    prepare()
    # Rebuild all original geometries with arbitrary available defining points.
    previous={'unit_circle'}; control_steps=[]
    for e in PAID:
        name=e['id']; obj=OBJECTS[name]
        control_steps.append({'name':name,'previous':set(previous),
          'boundary':[i for i,r in enumerate(POINTS) if name in r['incidents']],
          'center':point_index(obj.center) if isinstance(obj,Circle) else None})
        previous.add(name)
    PLANS[-1]={'steps':control_steps}
    chosen=choices(-1,None)
    assert chosen is not None
    # assemble(0) gives an empty paid prefix; selected includes all 12 objects.
    control=assemble(0,None,None,None,None,chosen)
    hit=support.save_candidate({'id':'geometry-redefinition-control'},control)
    assert hit['score']==12
    control_verified=support.verify_hits({'hits':[hit]})
    report={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'scope':'All legal point definitions for fixed retained baseline geometries/order after one consecutive pair is removed and zero/one object inserted from full prefix closure; K=0 baseline only. Not a global lower bound.',
      'positive_control':control_verified,'global_relevant_points':len(POINTS),'windows':[],
      'status':'running','found':False}
    support.dump_json(RUN/'pair-geometry-summary.json',report)
    for window in range(11):
        local_start=time.monotonic_ns(); indices=PLANS[window]['points']
        candidates=[(None,None,None)]
        candidates += [('line',i,j) for i,j in itertools.combinations(indices,2)]
        candidates += [('circle',i,j) for i in indices for j in indices if i!=j]
        row={'window':window,'prefix_points':len(indices),'planned_parameterizations':len(candidates),
          'complete_parameterizations':0,'deferred':0,'hits':[]}
        print(json.dumps({'event':'pair_geometry_window',**row}),flush=True)
        for op,p,q in candidates:
            if time.monotonic_ns()>=deadline: break
            signal.alarm(5)
            try:
                obj=None if op is None else support.object_from(op,POINTS[p]['point'],POINTS[q]['point'])
                selected=choices(window,obj)
                if selected is None:
                    row['complete_parameterizations']+=1; continue
                proposed=assemble(window,op,p,q,obj,selected)
                result=ProgramReplayer().replay(proposed)
                if not result.targets or result.e_move>11: raise AssertionError('Replacement predicate accepted invalid construction')
                hit=support.save_candidate({'id':'geometry-'+str(window)+'-'+str(op)+'-'+str(p)+'-'+str(q)},proposed)
                row['hits'].extend(support.verify_hits({'hits':[hit]}))
                row['complete_parameterizations']+=1
                report['found']=True; break
            except TimeoutError:
                row['deferred']+=1
            finally:
                signal.alarm(0)
        row['elapsed_ms']=(time.monotonic_ns()-local_start)//1000000
        report['windows'].append(row)
        support.dump_json(RUN/'pair-geometry-summary.json',report)
        print(json.dumps({'event':'pair_geometry_done',**row}),flush=True)
        if report['found'] or time.monotonic_ns()>=deadline: break
    report['elapsed_ms']=(time.monotonic_ns()-start)//1000000
    report['status']='found' if report['found'] else 'selected_jobs_finished' if len(report['windows'])==11 and all(r['complete_parameterizations']==r['planned_parameterizations'] for r in report['windows']) else 'incomplete'
    support.dump_json(RUN/'pair-geometry-summary.json',report)
    print(json.dumps({'event':'pair_geometry_finished',**report}),flush=True)


if __name__=='__main__': main()
