"""Identify provably identical first objects by exact normalized coefficients.

This file does not alter active search checkpoints. The emitted equivalence
groups are a reproducible optimization plan, not a global lower-bound proof.
"""
import hashlib
import itertools
import json
import time
from pathlib import Path
from euclid_min.geometry import Line,Circle
from euclid_min.replay import ProgramReplayer
import search_exact_budget_v2 as support

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/exact-local-v2-2026-09-11'


def main():
    support.RUN=RUN
    start=time.monotonic_ns()
    program=json.loads((HERE/'construction-12e-011.json').read_text())['construction']['program']
    groups=[]; state_reports={}
    for branch in (0,1):
        key='k'+str(branch)+'-e9'
        prefix=support.prefix(program,9)
        for entry in prefix:
            if entry['id']=='ggb_K': entry['index']=branch
        replay=ProgramReplayer().replay(prefix)
        support.CONTEXTS[key]={'program':prefix,'names':replay.names,
          'objects':{n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))}}
        assert support.assemble_points(key)['full_closure']
        points=support.CONTEXTS[key]['points']; n=len(points)
        entries=[]
        for op in ('line','circle'):
            pairs=itertools.combinations(range(n),2) if op=='line' else itertools.permutations(range(n),2)
            rows=[]
            for i,j in pairs:
                obj=support.object_from(op,points[i]['point'],points[j]['point'])
                # Circle centers are indexed by the already exactly distinct
                # prefix points. Lines use the project's normalized equation.
                coefficients=(obj.a,obj.b,obj.c) if op=='line' else (i,obj.radius_squared)
                identifier=key+'-two-'+op+'-'+str(i)+'-'+str(j)
                rows.append((coefficients,identifier))
            rows.sort(key=lambda r:r[0])
            for _,members in itertools.groupby(rows,key=lambda r:r[0]):
                entries.append([r[1] for r in members])
        groups.extend(entries)
        completed={p.stem for p in (RUN/'jobs').glob(key+'-two-*.json') if json.loads(p.read_text())['status']=='complete'}
        transferable=sum(sum(member not in completed for member in g) for g in entries if any(member in completed for member in g))
        state_reports[key]={'parameterizations':3*n*(n-1)//2,'distinct_objects':len(entries),
          'complete_jobs_now':len(completed),'additional_jobs_excluded_by_existing_completed_equivalent':transferable}
        print(json.dumps({'event':'exact_groups','state':key,**state_reports[key]}),flush=True)
    report={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'input_manifest':json.loads((RUN/'manifest.json').read_text()),
      'equality':'Exact AA normalized line coefficients or exact AA squared radius plus exactly distinct center index',
      'states':state_reports,'groups':groups,'elapsed_ms':(time.monotonic_ns()-start)//1000000}
    support.dump_json(RUN/'first-object-equivalence.json',report)
    print(json.dumps({'event':'grouping_done','groups':len(groups),'elapsed_ms':report['elapsed_ms']}),flush=True)


if __name__=='__main__': main()
