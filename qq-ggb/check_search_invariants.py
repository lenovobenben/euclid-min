"""Check exact search bookkeeping, independent availability, and hard deadlines."""
import hashlib
import itertools
import json
import signal
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from euclid_min.geometry import Point,Line,Circle
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
import search_exact_budget as old
import search_exact_budget_v2 as new
import search_pair_geometry as geometry

HERE=Path(__file__).resolve().parent
OLD=HERE/'runs/exact-local-2026-09-10'
NEW=HERE/'runs/exact-local-v2-2026-09-11'


def ignore_alarm(job):
    signal.signal(signal.SIGALRM,signal.SIG_IGN)
    while True: signal.pause()


def brute_availability(window,replacement):
    """Explicitly compute every new intersection before each retained draw."""
    replay=ProgramReplayer().replay(new.prefix(geometry.PROGRAM,window))
    objects={n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}
    points=[replay.names['O'],replay.names['A']]
    def include(obj):
        for old_obj in objects.values():
            for p in intersect(obj,old_obj).points:
                if not any(p==q for q in points): points.append(p)
    for a,b in itertools.combinations(objects,2):
        for p in intersect(objects[a],objects[b]).points:
            if not any(p==q for q in points): points.append(p)
    if replacement is not None:
        if any(new.same_object(replacement,o) for o in objects.values()):
            return False  # Search handles the identical no-op via its None case.
        include(replacement); objects['replacement']=replacement
    for entry in geometry.PAID[window+2:]:
        obj=geometry.OBJECTS[entry['id']]
        if any(new.same_object(obj,o) for o in objects.values()): continue
        if isinstance(obj,Circle):
            if not any(obj.center==p for p in points): return False
            if not any(obj.contains(p) for p in points): return False
        elif sum(obj.contains(p) for p in points)<2: return False
        include(obj); objects[entry['id']]=obj
    return True


def main():
    start=time.monotonic_ns()
    report={'status':'running','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    certificate=json.loads((HERE/'construction-12e-011.json').read_text())
    checked_points=0; checked_provenance=0
    for score,k in [(11,0),(10,0),(10,1),(9,0),(9,1)]:
        key='k'+str(k)+'-e'+str(score)
        for engine,run in ((old,OLD),(new,NEW)):
            engine.RUN=run
            program=engine.prefix(certificate['construction']['program'],score)
            for e in program:
                if e['id']=='ggb_K': e['index']=k
            replay=ProgramReplayer().replay(program)
            engine.CONTEXTS[key]={'program':program,'names':replay.names,
              'objects':{n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}}
            assert engine.assemble_points(key)['full_closure']
        one=old.CONTEXTS[key]['points']; two=new.CONTEXTS[key]['points']
        assert len(one)==len(two)
        for a,b in zip(one,two):
            assert a['point']==b['point']; checked_points+=1
            for name in b['incidents']:
                assert new.CONTEXTS[key]['objects'][name].contains(b['point'])
                checked_provenance+=1
    report['exact_ordered_prefix_points_compared']=checked_points
    report['exact_provenance_relations_checked']=checked_provenance
    common=[]
    for path in (OLD/'jobs').glob('*-two-*.json'):
        other=NEW/'jobs'/path.name
        if not other.exists(): continue
        a=json.loads(path.read_text()); b=json.loads(other.read_text())
        if a['status']!='complete' or b['status']!='complete': continue
        for field in ('new_points','tested_terminal_parameterizations','hits','skipped'):
            assert a.get(field)==b.get(field),(path.name,field,a.get(field),b.get(field))
        common.append(path.stem)
    report['overlapping_completed_two_step_jobs_agree']=len(common)
    report['overlap_job_ids']=sorted(common)
    original_worker=new.worker
    with tempfile.TemporaryDirectory(prefix='qq-exact-deadline-') as temporary:
        new.RUN=Path(temporary); (new.RUN/'jobs').mkdir()
        new.worker=ignore_alarm; new.TIMEOUT=1
        args=SimpleNamespace(workers=2,retry_deferred=False)
        summary={'verified_candidates':[],'shorter_found':False}
        jobs=[{'phase':'two','id':'ignore-alarm-'+str(i)} for i in range(2)]
        then=time.monotonic_ns()
        records=new.run_jobs(jobs,args,then+10*1000000000,summary)
        elapsed=(time.monotonic_ns()-then)//1000000
        assert len(records)==2 and all(r['status']=='deferred' for r in records)
        assert all('parent enforced' in r['reason'] for r in records)
        assert elapsed<5000 and not summary['shorter_found']
        report['parent_deadline_ignoring_sigalrm']={'passed':True,'jobs':2,'elapsed_ms':elapsed}
    new.worker=original_worker; new.RUN=NEW
    geometry.prepare()
    cases=0
    for window in range(4):
        points=geometry.PLANS[window]['points']
        candidates=[(None,None,None)]
        candidates += [('line',i,j) for i,j in itertools.combinations(points,2)]
        candidates += [('circle',i,j) for i in points for j in points if i!=j]
        for op,i,j in candidates:
            obj=None if op is None else new.object_from(op,geometry.POINTS[i]['point'],geometry.POINTS[j]['point'])
            expected=brute_availability(window,obj)
            actual=geometry.choices(window,obj) is not None
            assert actual==expected,(window,op,i,j,actual,expected)
            cases+=1
    report['pair_geometry_vs_explicit_intersections']={'passed':True,'windows':[0,1,2,3],'parameterizations':cases}
    report['status']='passed'; report['elapsed_ms']=(time.monotonic_ns()-start)//1000000
    new.dump_json(NEW/'search-invariants-report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='overlap_job_ids'},indent=2),flush=True)


if __name__=='__main__': main()
