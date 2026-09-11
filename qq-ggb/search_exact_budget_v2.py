"""Budgeted exact local search with per-job checkpoints and explicit scope.

No floating-point geometry, tolerances, or numerical candidate ranking. Runtime
accounting uses integer nanoseconds. Run under Sage Python on Linux/Docker.
"""
import argparse
import hashlib
import itertools
import json
import multiprocessing as mp
from multiprocessing.connection import wait as wait_process
import os
import pickle
import signal
import subprocess
import sys
import time
from pathlib import Path
from sage.all import QQ

from euclid_min.formats import construction_sha256,load_profile
from euclid_min.geometry import Circle,Line,Point
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.target import adjacent_targets

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
CONTEXTS={}
RUN=None
TIMEOUT=30
TARGETS=None
PROFILE=None


def dump_json(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary,path)


def dump_pickle(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('wb') as stream:
        pickle.dump(data,stream); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary,path)


def prefix(program,score):
    result=[]; paid=0
    for entry in program:
        if entry['op'] in ('line','circle'):
            if paid==score: break
            paid+=1
        result.append(dict(entry))
    if paid!=score: raise ValueError('Invalid prefix length')
    return result


def timeout_handler(signum,frame):
    raise TimeoutError('exact_job_timeout')


def object_from(op,p,q):
    return Line.through(p,q) if op=='line' else Circle.through(p,q)


def same_object(a,b):
    if type(a) is not type(b): return False
    if isinstance(a,Line): return a.c==b.c and a.b==b.b and a.a==b.a
    return a==b


def incident(op,p,q,target):
    # Test the exact defining equation before constructing or normalizing a
    # drawable. The circle form cancels the center's quadratic terms first.
    if op=='line':
        return (q.x-p.x)*(target.y-p.y)-(q.y-p.y)*(target.x-p.x)==0
    return (q.x-target.x)*(q.x+target.x-2*p.x)+(q.y-target.y)*(q.y+target.y-2*p.y)==0


def known_duplicate(op,a,b,objects):
    if op=='line':
        return any(isinstance(objects[name],Line) for name in a['incidents'] & b['incidents'])
    return any(isinstance(objects[name],Circle) and objects[name].center==a['point']
               for name in b['incidents'])


def simplify_point(point):
    point.x.simplify(); point.y.simplify()
    return point


def draw_entry(identifier,op,p,q):
    if op=='line': return {'id':identifier,'op':'line','through':[p,q]}
    return {'id':identifier,'op':'circle','center':p,'through':q}


def bind_record(program,record,new_id):
    if record.get('name'): return record['name']
    program.append({'id':new_id,'op':'intersect','objects':record['objects'],'index':record['index']})
    return new_id


def save_candidate(job,program):
    replay=ProgramReplayer().replay(program)
    if not replay.targets: raise AssertionError('Candidate failed exact replay')
    construction={'id':'qq-ggb-search-'+job['id'],'title':'QQ GGB 精确局部搜索候选；原始来源首创者未确认','program':program}
    certificate={'schema':'euclid-min-certificate/v1','problem':'regular-17-adjacent-vertex',
      'profile':{'id':PROFILE.data['id'],'sha256':PROFILE.sha256},'construction':construction,
      'assertions':{'score':{'metric':'e_move','e_move':replay.e_move},'targets':[t.value for t in replay.targets],'claim':'verified_construction'},
      'software':{'producer':{'name':'qq-ggb-exact-budget-search','version':'1.0.0'}},
      'integrity':{'construction_sha256':construction_sha256(construction)}}
    filename='candidate-'+job['id']+'.json'
    dump_json(RUN/filename,certificate)
    return {'file':filename,'score':replay.e_move,'first_target_e_move':replay.first_target_e_move}


def pair_job(job):
    context=CONTEXTS[job['state']]
    first,second=job['objects']
    result=intersect(context['objects'][first],context['objects'][second])
    points=[simplify_point(p) for p in result.points]
    dump_pickle(RUN/'cache'/(job['id']+'.pickle'),points)
    return {'kind':result.kind.value,'point_representations':len(points)}


def one_job(job):
    context=CONTEXTS[job['state']]; records=context['points']
    first_index=job['first']; first=records[first_index]
    tested=0; existing=0; same_points=0; hits=[]
    for j,second in enumerate(records):
        if first['point']==second['point']:
            same_points+=1; continue
        for op in (('line','circle') if j>first_index else ('circle',)):
            tested+=1
            drawable=object_from(op,first['point'],second['point'])
            if any(same_object(drawable,o) for o in context['objects'].values()):
                existing+=1; continue
            if not any(drawable.contains(t) for t in TARGETS.values()): continue
            program=[dict(e) for e in context['program']]
            p=bind_record(program,first,'search_input_1')
            q=bind_record(program,second,'search_input_2')
            program.append(draw_entry('search_final',op,p,q))
            hit=save_candidate(dict(job,id=job['id']+'-'+op+'-'+str(j)),program)
            hits.append(hit)
    return {'tested_parameterizations':tested,'existing_objects_skipped':existing,
            'same_point_pairs_skipped':same_points,'hits':hits}


def two_job(job):
    context=CONTEXTS[job['state']]
    records=[dict(r,incidents=set(r.get('incidents',()))) for r in context['points']]
    p,q=(records[i] for i in job['inputs'])
    if p['point']==q['point']: return {'skipped':'same_point','tested_terminal_parameterizations':0,'hits':[]}
    first=object_from(job['op'],p['point'],q['point'])
    if any(same_object(first,o) for o in context['objects'].values()):
        return {'skipped':'existing_object','tested_terminal_parameterizations':0,'hits':[]}
    first_values=(first.a,first.b,first.c) if isinstance(first,Line) else (first.radius_squared,)
    for value in first_values: value.simplify()
    program=[dict(e) for e in context['program']]
    p_name=bind_record(program,p,'search_first_input_1')
    q_name=bind_record(program,q,'search_first_input_2')
    program.append(draw_entry('search_first',job['op'],p_name,q_name))
    if any(first.contains(t) for t in TARGETS.values()):
        return {'hits':[save_candidate(job,program)],'tested_terminal_parameterizations':0}
    new_points=[]
    all_objects=dict(context['objects'],search_first=first)
    ordered_objects=sorted(context['objects'].items(),key=lambda item:0 if isinstance(item[1],Line) else 1)
    for name,obj in ordered_objects:
        result=intersect(first,obj)
        for index,point in enumerate(result.points):
            # AA already denotes an exact algebraic number. Forcing simplify()
            # here can build a huge common number field before it is needed.
            if isinstance(obj,Line): simplify_point(point)
            existing=next((r for r in records+new_points if point==r['point']),None)
            if existing is not None:
                existing['incidents'].update(('search_first',name))
                continue
            new_points.append({'point':point,'objects':['search_first',name],'index':index,
                               'incidents':{'search_first',name}})
    all_points=records+new_points
    tested=0
    for i,new in enumerate(new_points):
        for j,old in enumerate(all_points):
            if new['point']==old['point']: continue
            choices=[('circle',new,old),('circle',old,new)]
            if j<len(records)+i: choices.append(('line',new,old))
            for op,a,b in choices:
                tested+=1
                if known_duplicate(op,a,b,all_objects): continue
                if not any(incident(op,a['point'],b['point'],t) for t in TARGETS.values()): continue
                last=object_from(op,a['point'],b['point'])
                if same_object(last,first) or any(same_object(last,o) for o in context['objects'].values()): continue
                result_program=[dict(e) for e in program]
                a_name=bind_record(result_program,a,'search_last_input_1')
                b_name=bind_record(result_program,b,'search_last_input_2')
                result_program.append(draw_entry('search_last',op,a_name,b_name))
                return {'new_points':len(new_points),'tested_terminal_parameterizations':tested,
                        'hits':[save_candidate(job,result_program)]}
    return {'new_points':len(new_points),'tested_terminal_parameterizations':tested,'hits':[]}


def worker(job):
    start=time.monotonic_ns()
    signal.signal(signal.SIGALRM,timeout_handler)
    signal.alarm(TIMEOUT)
    try:
        result={'pair':pair_job,'one':one_job,'two':two_job}[job['phase']](job)
        status='complete'
    except TimeoutError:
        result={'reason':'exact computation exceeded per-job time limit; not excluded'}; status='deferred'
    except Exception as error:
        result={'reason':type(error).__name__+': '+str(error)}; status='error'
    finally:
        signal.alarm(0)
    record={'job':job,'status':status,'elapsed_ms':(time.monotonic_ns()-start)//1000000,**result}
    dump_json(RUN/'jobs'/(job['id']+'.json'),record)
    return record


def verify_hits(record):
    verified=[]
    for hit in record.get('hits',[]):
        path=RUN/hit['file']; report_path=path.with_suffix('.verification.json')
        result=subprocess.run([sys.executable,'-m','euclid_min','verify','--profile',str(ROOT/'profiles/regular-17-e-fixed-v1.yaml'),str(path),'--report',str(report_path),'--json'],capture_output=True,text=True,timeout=45)
        if result.returncode!=0: raise RuntimeError('Independent verifier rejected candidate: '+result.stdout+result.stderr)
        verified.append({**hit,'independent_verification':report_path.name})
    return verified


def run_jobs(jobs,args,deadline,summary):
    cached=[]; pending=[]
    for job in jobs:
        path=RUN/'jobs'/(job['id']+'.json')
        if path.exists():
            record=json.loads(path.read_text())
            if record['status']=='complete' or not args.retry_deferred: cached.append(record); continue
        pending.append(job)
    result=list(cached)
    for record in cached:
        verified=verify_hits(record)
        if verified: summary['verified_candidates'].extend(verified)
        if any(hit['score']<=11 for hit in verified): summary['shorter_found']=True
    if summary['shorter_found']: return result
    # Sage/PARI can remain inside C after SIGALRM. The parent owns a separate
    # deadline for each child and kills it if necessary; a killed job is never
    # recorded as an exclusion. Forking inherits the exact prefix contexts.
    context=mp.get_context('fork')
    active={}; next_job=0
    completed=0
    last_update=time.monotonic_ns()
    def finish(process,job,started,reason=None):
        if reason is not None and process.is_alive(): process.kill()
        process.join()
        path=RUN/'jobs'/(job['id']+'.json')
        if path.exists():
            record=json.loads(path.read_text())
        else:
            record={'job':job,'status':'deferred' if reason else 'error',
              'reason':reason or 'worker exited without a checkpoint',
              'elapsed_ms':(time.monotonic_ns()-started)//1000000}
            dump_json(path,record)
        process.close()
        return record
    try:
        while completed<len(pending) and time.monotonic_ns()<deadline:
            while len(active)<args.workers and next_job<len(pending):
                job=pending[next_job]; next_job+=1
                process=context.Process(target=worker,args=(job,))
                started=time.monotonic_ns(); process.start()
                active[process.pid]=(process,job,started)
            if active: wait_process([p.sentinel for p,_,_ in active.values()],timeout=1)
            for pid,(process,job,started) in list(active.items()):
                expired=time.monotonic_ns()-started>TIMEOUT*1000000000
                if process.is_alive() and not expired: continue
                record=finish(process,job,started,
                  'parent enforced exact-job deadline; not excluded' if expired else None)
                del active[pid]
                completed+=1; result.append(record)
                verified=verify_hits(record)
                if verified:
                    summary['verified_candidates'].extend(verified)
                    print(json.dumps({'event':'verified_candidate','candidate':verified}),flush=True)
                    if any(hit['score']<=11 for hit in verified):
                        summary['shorter_found']=True; break
            if summary['shorter_found']: break
            if time.monotonic_ns()-last_update>10*1000000000 or completed==len(pending):
                print(json.dumps({'event':'phase_progress','phase':jobs[0]['phase'] if jobs else None,
                  'completed_this_run':completed,'cached':len(cached),'planned':len(jobs),
                  'remaining_budget_seconds':max(0,(deadline-time.monotonic_ns())//1000000000)}),flush=True)
                last_update=time.monotonic_ns()
    finally:
        for process,job,started in active.values():
            finish(process,job,started,'overall search stopped; not excluded')
    # A child may have committed its result just before it was stopped.
    result=[]
    for job in jobs:
        path=RUN/'jobs'/(job['id']+'.json')
        if path.exists(): result.append(json.loads(path.read_text()))
    return result


def assemble_points(key):
    context=CONTEXTS[key]
    points=[{'name':name,'point':p,'incidents':set()} for name,p in context['names'].items() if isinstance(p,Point)]
    next(p for p in points if p.get('name')=='A')['incidents'].add('unit_circle')
    expected=0; complete=0
    for a,b in itertools.combinations(context['objects'],2):
        expected+=1
        identifier=key+'-pair-'+a+'-'+b
        path=RUN/'jobs'/(identifier+'.json')
        if not path.exists(): continue
        report=json.loads(path.read_text())
        if report['status']!='complete': continue
        complete+=1
        with (RUN/'cache'/(identifier+'.pickle')).open('rb') as stream: pair_points=pickle.load(stream)
        for index,point in enumerate(pair_points):
            existing=next((p for p in points if point==p['point']),None)
            if existing is not None:
                existing['incidents'].update((a,b)); continue
            points.append({'point':point,'objects':[a,b],'index':index,'incidents':{a,b}})
    context['points']=points
    return {'distinct_points':len(points),'named_points':sum('name' in p for p in points),
            'closure_pairs_complete':complete,'closure_pairs_planned':expected,'full_closure':complete==expected,
            'one_step_parameterizations':3*len(points)*(len(points)-1)//2}


def stage_summary(records,planned):
    return {'planned_jobs':planned,'recorded_jobs':len(records),
      'complete':sum(r['status']=='complete' for r in records),
      'deferred':sum(r['status']=='deferred' for r in records),
      'errors':sum(r['status']=='error' for r in records),
      'tested_parameterizations':sum(r.get('tested_parameterizations',0)+r.get('tested_terminal_parameterizations',0) for r in records),
      'worker_elapsed_ms':sum(r['elapsed_ms'] for r in records)}


def main():
    global RUN,TIMEOUT,TARGETS,PROFILE
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=3600)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--job-seconds',type=int,default=30)
    parser.add_argument('--run-dir',default='runs/exact-local-v2-2026-09-11')
    parser.add_argument('--retry-deferred',action='store_true')
    parser.add_argument('--one-step-only',action='store_true')
    args=parser.parse_args()
    if min(args.seconds,args.workers,args.job_seconds)<1: raise ValueError('Positive limits required')
    RUN=HERE/args.run_dir; RUN.mkdir(parents=True,exist_ok=True)
    (RUN/'jobs').mkdir(exist_ok=True); (RUN/'cache').mkdir(exist_ok=True)
    TIMEOUT=args.job_seconds; TARGETS=adjacent_targets()
    PROFILE=load_profile(ROOT/'profiles/regular-17-e-fixed-v1.yaml')
    certificate_path=HERE/'construction-12e-011.json'
    certificate=json.loads(certificate_path.read_text(encoding='utf-8'))
    signature={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'certificate_sha256':hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
      'profile_sha256':PROFILE.sha256,'geometry':'Sage AA exact; no floats or tolerances'}
    manifest=RUN/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=signature: raise ValueError('Checkpoint inputs or algorithm changed; use a new run directory')
    dump_json(manifest,signature)
    start=time.monotonic_ns(); deadline=start+args.seconds*1000000000
    summary={'budget_seconds':args.seconds,'workers':args.workers,'per_job_seconds':TIMEOUT,
      'scope':'Fixed QQ-GGB prefixes, both K branches, full available intersections where completed, and bounded local one/two-object extensions. Not global exhaustive search.',
      'shorter_found':False,'verified_candidates':[],'status':'running','stages':{},'states':{}}
    for score,k in [(11,0),(10,0),(10,1),(9,0),(9,1)]:
        key='k'+str(k)+'-e'+str(score)
        program=prefix(certificate['construction']['program'],score)
        for entry in program:
            if entry['id']=='ggb_K': entry['index']=k
        replay=ProgramReplayer().replay(program)
        CONTEXTS[key]={'program':program,'names':replay.names,
          'objects':{n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))},'score':score}
    pair_jobs=[{'phase':'pair','state':key,'objects':[a,b],'id':key+'-pair-'+a+'-'+b}
               for key,context in CONTEXTS.items() for a,b in itertools.combinations(context['objects'],2)]
    print(json.dumps({'event':'start','pair_jobs':len(pair_jobs),'budget_seconds':args.seconds,'workers':args.workers}),flush=True)
    records=run_jobs(pair_jobs,args,deadline,summary)
    summary['stages']['closure']=stage_summary(records,len(pair_jobs)); dump_json(RUN/'summary.json',summary)
    for key in CONTEXTS:
        if time.monotonic_ns()>=deadline: break
        summary['states'][key]=assemble_points(key)
        print(json.dumps({'event':'state_size','state':key,**summary['states'][key]}),flush=True)
    # Calibration: the existing 12 E circle must be rediscovered from its 11 E prefix.
    if 'points' in CONTEXTS['k0-e11'] and time.monotonic_ns()<deadline:
        context=CONTEXTS['k0-e11']
        index=next(i for i,p in enumerate(context['points']) if p.get('name')=='ggb_C')
        jobs=[{'phase':'one','state':'k0-e11','first':index,'id':'control-known-12e'}]
        records=run_jobs(jobs,args,deadline,summary)
        summary['stages']['positive_control']=stage_summary(records,1)
        summary['positive_control_passed']=any(r.get('hits') for r in records if r['status']=='complete')
        dump_json(RUN/'summary.json',summary)
        if not summary['positive_control_passed']: raise RuntimeError('Known 12 E control not recovered; do not expand search')
    one_jobs=[{'phase':'one','state':key,'first':i,'id':key+'-one-'+str(i)}
              for key,c in CONTEXTS.items() if c['score']<=10 and 'points' in c for i in range(len(c['points']))]
    if time.monotonic_ns()<deadline:
        records=run_jobs(one_jobs,args,deadline,summary)
        summary['stages']['one_step']=stage_summary(records,len(one_jobs)); dump_json(RUN/'summary.json',summary)
    if not args.one_step_only and not summary['shorter_found'] and time.monotonic_ns()<deadline:
        two_jobs=[]
        for key,context in CONTEXTS.items():
            if context['score']!=9 or 'points' not in context: continue
            # Named input points first, then the rest of the exact full closure.
            n=len(context['points'])
            rows=[('line',i,j) for i in range(n) for j in range(i+1,n)]
            rows += [('circle',i,j) for i in range(n) for j in range(n) if i!=j]
            rational=[p['point'].x in QQ and p['point'].y in QQ for p in context['points']]
            rows.sort(key=lambda r:(sum('name' not in context['points'][i] for i in r[1:]),
                                    sum(not rational[i] for i in r[1:]),r[1],r[2],r[0]))
            for op,i,j in rows:
                two_jobs.append({'phase':'two','state':key,'op':op,'inputs':[i,j],'id':key+'-two-'+op+'-'+str(i)+'-'+str(j)})
        # Alternate K branches instead of spending the entire budget on one.
        by_state={key:[j for j in two_jobs if j['state']==key] for key in ('k0-e9','k1-e9')}
        two_jobs=[job for row in itertools.zip_longest(*by_state.values()) for job in row if job is not None]
        records=run_jobs(two_jobs,args,deadline,summary)
        summary['stages']['two_step']=stage_summary(records,len(two_jobs))
    summary['elapsed_seconds']=(time.monotonic_ns()-start)//1000000000
    summary['status']='found' if summary['shorter_found'] else ('budget_exhausted' if time.monotonic_ns()>=deadline else 'selected_jobs_finished')
    dump_json(RUN/'summary.json',summary)
    print(json.dumps({'event':'finished',**summary},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
