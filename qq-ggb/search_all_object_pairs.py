"""Exact deletion of any two baseline objects, inserting at most one object.

Insertion is at the first deletion. All later retained geometries/order stay
fixed, but their defining points can change. This extends the consecutive-pair
search to all 66 pairs; it is not a global search over 11 E constructions.
"""
import argparse
import hashlib
import itertools
import json
import signal
import time
from pathlib import Path
from euclid_min.geometry import Circle
from euclid_min.replay import ProgramReplayer
from euclid_min.formats import load_profile
from euclid_min.target import adjacent_targets
import search_pair_geometry as geometry
import search_exact_budget_v2 as support

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/exact-local-v2-2026-09-11'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,default=300)
    args=parser.parse_args()
    support.RUN=RUN; support.PROFILE=load_profile(HERE.parent/'profiles/regular-17-e-fixed-v1.yaml')
    support.TARGETS=adjacent_targets()
    signal.signal(signal.SIGALRM,support.timeout_handler)
    start=time.monotonic_ns(); deadline=start+args.seconds*1000000000
    geometry.prepare()
    original_plans=dict(geometry.PLANS)
    control_report=json.loads((RUN/'pair-geometry-summary.json').read_text())
    assert control_report['status']=='selected_jobs_finished'
    assert control_report['script_sha256']==hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest()
    report={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'support_sha256':control_report['script_sha256'],'consecutive_control_report':'pair-geometry-summary.json',
      'scope':'Any two paid K=0 baseline objects deleted; at most one replacement inserted at the first deletion from the full exact prefix closure. Retained geometries/order fixed, all legal defining points allowed. Not a global lower bound.',
      'status':'running','pairs':[],'found':False}
    for first,last in itertools.combinations(range(12),2):
        previous={'unit_circle',*(e['id'] for e in geometry.PAID[:first])}
        steps=[]
        for k,entry in enumerate(geometry.PAID[first+1:],start=first+1):
            if k==last: continue
            name=entry['id']; obj=geometry.OBJECTS[name]
            steps.append({'name':name,'previous':set(previous),
              'boundary':[i for i,r in enumerate(geometry.POINTS) if name in r['incidents']],
              'center':geometry.point_index(obj.center) if isinstance(obj,Circle) else None})
            previous.add(name)
        indices=original_plans[first]['points']
        geometry.PLANS[first]={'steps':steps,'points':indices}
        row={'removed_positions':[first+1,last+1],'prefix_points':len(indices),
          'complete_parameterizations':0,'deferred':0,'hits':[]}
        candidates=[(None,None,None)]
        candidates += [('line',i,j) for i,j in itertools.combinations(indices,2)]
        candidates += [('circle',i,j) for i in indices for j in indices if i!=j]
        row['planned_parameterizations']=len(candidates)
        local_start=time.monotonic_ns()
        for op,i,j in candidates:
            if time.monotonic_ns()>=deadline: break
            signal.alarm(5)
            try:
                obj=None if op is None else support.object_from(op,geometry.POINTS[i]['point'],geometry.POINTS[j]['point'])
                # When the final target circle is deleted, the replacement
                # must meet either exact target; all other retained objects
                # have already been shown not to produce one.
                if last==11 and (obj is None or not any(obj.contains(t) for t in support.TARGETS.values())):
                    row['complete_parameterizations']+=1; continue
                selected=geometry.choices(first,obj)
                if selected is None:
                    row['complete_parameterizations']+=1; continue
                proposed=geometry.assemble(first,op,i,j,obj,selected)
                replay=ProgramReplayer().replay(proposed)
                if not replay.targets or replay.e_move>11: raise AssertionError('Invalid pair replacement accepted')
                hit=support.save_candidate({'id':'all-pairs-'+str(first)+'-'+str(last)+'-'+str(op)+'-'+str(i)+'-'+str(j)},proposed)
                row['hits'].extend(support.verify_hits({'hits':[hit]}))
                row['complete_parameterizations']+=1
                report['found']=True; break
            except TimeoutError:
                row['deferred']+=1
            finally:
                signal.alarm(0)
        row['elapsed_ms']=(time.monotonic_ns()-local_start)//1000000
        report['pairs'].append(row)
        support.dump_json(RUN/'all-object-pairs-summary.json',report)
        print(json.dumps({'event':'object_pair_done',**row}),flush=True)
        if report['found'] or time.monotonic_ns()>=deadline: break
    report['elapsed_ms']=(time.monotonic_ns()-start)//1000000
    report['status']='found' if report['found'] else 'selected_jobs_finished' if len(report['pairs'])==66 and all(r['complete_parameterizations']==r['planned_parameterizations'] for r in report['pairs']) else 'incomplete'
    support.dump_json(RUN/'all-object-pairs-summary.json',report)
    print(json.dumps({'event':'all_object_pairs_finished','status':report['status'],'found':report['found'],'elapsed_ms':report['elapsed_ms']}),flush=True)


if __name__=='__main__': main()
