"""Prioritize the two exact axis intersections of p as first-object inputs.

Uses the already audited v2 worker. All geometry remains exact. This companion
search has separate checkpoints and skips jobs already completed by the main
search. Its budget is part of the same authorized wall-clock hour.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from euclid_min.geometry import Line,Circle
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.formats import load_profile
from euclid_min.target import adjacent_targets
import search_exact_budget_v2 as support

HERE=Path(__file__).resolve().parent
MAIN=HERE/'runs/exact-local-v2-2026-09-11'
RUN=HERE/'runs/exact-targeted-centers-2026-09-11'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,required=True)
    parser.add_argument('--job-seconds',type=int,default=30)
    args=parser.parse_args()
    start=time.monotonic_ns(); deadline=start+args.seconds*1000000000
    RUN.mkdir(exist_ok=True); (RUN/'jobs').mkdir(exist_ok=True)
    support.TARGETS=adjacent_targets(); support.PROFILE=load_profile(HERE.parent/'profiles/regular-17-e-fixed-v1.yaml')
    support.TIMEOUT=args.job_seconds
    program=json.loads((HERE/'construction-12e-011.json').read_text())['construction']['program']
    state_jobs=[]; selected_points={}; omitted=[]
    for branch in (0,1):
        key='k'+str(branch)+'-e9'
        prefix=support.prefix(program,9)
        for e in prefix:
            if e['id']=='ggb_K': e['index']=branch
        replay=ProgramReplayer().replay(prefix)
        objects={n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}
        support.CONTEXTS[key]={'program':prefix,'names':replay.names,'objects':objects,'score':9}
        support.RUN=MAIN
        assert support.assemble_points(key)['full_closure']
        points=support.CONTEXTS[key]['points']
        axis_points=intersect(objects['ggb_p'],objects['ggb_f']).points
        chosen=[i for i,r in enumerate(points) if any(r['point']==p for p in axis_points)]
        assert len(chosen)==2
        selected_points[key]=chosen
        rows=set()
        for i in chosen:
            for j in range(len(points)):
                if i==j: continue
                rows.update((('circle',i,j),('circle',j,i),('line',min(i,j),max(i,j))))
        jobs=[]
        for op,i,j in sorted(rows,key=lambda r:(r[1] not in chosen,r[0]!='circle',r[1],r[2])):
            identifier=key+'-two-'+op+'-'+str(i)+'-'+str(j)
            path=MAIN/'jobs'/(identifier+'.json')
            if path.exists() and json.loads(path.read_text())['status']=='complete':
                omitted.append(identifier); continue
            jobs.append({'phase':'two','state':key,'op':op,'inputs':[i,j],'id':identifier})
        state_jobs.append(jobs)
    import itertools
    jobs=[j for row in itertools.zip_longest(*state_jobs) for j in row if j is not None]
    support.RUN=RUN
    manifest={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'worker_sha256':hashlib.sha256(Path(support.__file__).read_bytes()).hexdigest(),
      'source_manifest':json.loads((MAIN/'manifest.json').read_text()),'geometry':'Exact Sage AA; no float geometry'}
    support.dump_json(RUN/'manifest.json',manifest)
    summary={'status':'running','shorter_found':False,'verified_candidates':[],
      'budget_seconds':args.seconds,'workers':2,'job_seconds':args.job_seconds,
      'scope':'Two-step extensions of fixed 9 E K=0/1 prefixes with at least one first-object input at either intersection of p and f. All terminal choices use the v2 worker.',
      'selected_point_indices':selected_points,'already_complete_in_main':omitted,'planned_jobs':len(jobs)}
    support.dump_json(RUN/'summary.json',summary)
    records=support.run_jobs(jobs,SimpleNamespace(workers=2,retry_deferred=False),deadline,summary)
    summary['stages']={'two_step':support.stage_summary(records,len(jobs))}
    summary['status']='found' if summary['shorter_found'] else 'budget_exhausted' if time.monotonic_ns()>=deadline else 'selected_jobs_finished'
    summary['elapsed_ms']=(time.monotonic_ns()-start)//1000000
    support.dump_json(RUN/'summary.json',summary)
    print(json.dumps({'event':'targeted_finished',**summary}),flush=True)


if __name__=='__main__': main()
