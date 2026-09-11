"""Replace consecutive pairs of paid baseline objects by one exact object.

The remaining baseline objects keep their geometry and order. Alternative
intersection witnesses are permitted. This is a bounded local search only.
"""
import argparse
import hashlib
import itertools
import json
import signal
import sys
import time
from pathlib import Path

from euclid_min.geometry import Point,Line,Circle
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.target import adjacent_targets
from euclid_min.formats import load_profile
import search_exact_budget as support

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/exact-local-2026-09-10'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--window',type=int,choices=range(11),help='Only this zero-based pair window')
parser.add_argument('--report',default='pair-replacement-summary.json')
args=parser.parse_args()
certificate=json.loads((HERE/'construction-12e-011.json').read_text(encoding='utf-8'))
program=certificate['construction']['program']
baseline=ProgramReplayer().replay(program)
paid=[e for e in program if e['op'] in ('line','circle')]
bound={e['id']:e for e in program if e['op']=='intersect'}
all_objects={n:o for n,o in baseline.names.items() if isinstance(o,(Line,Circle))}
targets=adjacent_targets()
support.RUN=RUN
support.PROFILE=load_profile(HERE.parent/'profiles/regular-17-e-fixed-v1.yaml')
signal.signal(signal.SIGALRM,support.timeout_handler)


def inputs(entry):
    return entry['through'] if entry['op']=='line' else (entry['center'],entry['through'])


def assemble(context,new_object,op,first,second,removed,suffix):
    proposed=[dict(e) for e in context['program']]
    one=support.bind_record(proposed,first,'replacement_input_1')
    two=support.bind_record(proposed,second,'replacement_input_2')
    proposed.append(support.draw_entry('replacement',op,one,two))
    current=dict(context['names']); current['replacement']=new_object
    for name,record in ((one,first),(two,second)):
        current[name]=record['point']
    for entry in suffix:
        if entry['id'] in removed: continue
        for name in inputs(entry):
            if name in current: continue
            point=baseline.names[name]
            incident=[n for n,o in current.items() if isinstance(o,(Line,Circle)) and o.contains(point)]
            witness=None
            for a,b in itertools.combinations(incident,2):
                if support.same_object(current[a],current[b]): continue
                for index,p in enumerate(intersect(current[a],current[b]).points):
                    if p==point:
                        witness={'id':name,'op':'intersect','objects':[a,b],'index':index}; break
                if witness: break
            if witness is None: return None
            proposed.append(witness); current[name]=point
        proposed.append(dict(entry))
        current[entry['id']]=support.object_from(entry['op'],*(current[n] for n in inputs(entry)))
    return proposed


reports=[]
for window in ([args.window] if args.window is not None else range(11)):
    start=time.monotonic_ns()
    removed={paid[window]['id'],paid[window+1]['id']}
    retained={n:o for n,o in all_objects.items() if n not in removed}
    required=set()
    for entry in paid[window+2:]:
        for name in inputs(entry):
            if name in bound and set(bound[name]['objects']) & removed:
                required.add(name)
    # Either adjacent vertex suffices when replacing the final circle.
    must_hit_target='ggb_t' in removed
    mandatory=[]; impossible=[]
    for name in required:
        point=baseline.names[name]
        witnesses=[n for n,o in retained.items() if o.contains(point)]
        if len(witnesses)==1: mandatory.append(name)
        elif len(witnesses)==0: impossible.append(name)
    report={'removed':sorted(removed),'prefix_score':window,'required_points':sorted(required),
      'replacement_must_hit_either_target':must_hit_target,
      'must_lie_on_new_object':sorted(mandatory),'no_remaining_witness':impossible,
      'tested_parameterizations':0,'deferred':0,'geometric_survivors':0,'hits':[]}
    print(json.dumps({'event':'replacement_window',**report}),flush=True)
    if not impossible:
        earlier=support.prefix(program,window)
        replay=ProgramReplayer().replay(earlier)
        context={'program':earlier,'names':replay.names}
        objects={n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}
        points=[{'name':n,'point':p} for n,p in replay.names.items() if isinstance(p,Point)]
        complete=True
        for a,b in itertools.combinations(objects,2):
            signal.alarm(15)
            try:
                for index,point in enumerate(intersect(objects[a],objects[b]).points):
                    support.simplify_point(point)
                    if any(point==p['point'] for p in points): continue
                    points.append({'point':point,'objects':[a,b],'index':index})
            except TimeoutError:
                complete=False
            finally:
                signal.alarm(0)
        report['prefix_distinct_points']=len(points); report['full_prefix_closure']=complete
        candidates=[('line',i,j) for i in range(len(points)) for j in range(i+1,len(points))]
        candidates += [('circle',i,j) for i in range(len(points)) for j in range(len(points)) if i!=j]
        for op,i,j in candidates:
            signal.alarm(5)
            try:
                report['tested_parameterizations']+=1
                obj=support.object_from(op,points[i]['point'],points[j]['point'])
                if must_hit_target and not any(obj.contains(t) for t in targets.values()): continue
                if not all(obj.contains(baseline.names[n]) for n in mandatory): continue
                if any(support.same_object(obj,old) for old in objects.values()): continue
                report['geometric_survivors']+=1
                proposed=assemble(context,obj,op,points[i],points[j],removed,paid[window:])
                if proposed is None: continue
                replay=ProgramReplayer().replay(proposed)
                if not replay.targets: continue
                job={'id':'replace-'+str(window)+'-'+op+'-'+str(i)+'-'+str(j)}
                hit=support.save_candidate(job,proposed)
                report['hits'].extend(support.verify_hits({'hits':[hit]}))
                print(json.dumps({'event':'replacement_found','hit':report['hits']}),flush=True)
                break
            except TimeoutError:
                report['deferred']+=1
            finally:
                signal.alarm(0)
        report['planned_parameterizations']=len(candidates)
    report['elapsed_ms']=(time.monotonic_ns()-start)//1000000
    reports.append(report)
    support.dump_json(RUN/args.report,{'scope':'One-object replacement of each consecutive pair, retaining remaining baseline object definitions/order with alternative intersection witnesses; exact arithmetic',
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'windows':reports,'completed_windows':len(reports),'found':any(r['hits'] for r in reports)})
    print(json.dumps({'event':'replacement_done',**report}),flush=True)
    if report['hits']: break
