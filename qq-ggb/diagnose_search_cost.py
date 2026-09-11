"""Measure exact search bottlenecks without changing geometry or checkpoints."""
import faulthandler
import argparse
import json
import signal
import time
from pathlib import Path
from euclid_min.geometry import Circle,Line
from euclid_min.replay import ProgramReplayer
from euclid_min.target import adjacent_targets
from euclid_min.formats import load_profile
args=argparse.ArgumentParser()
args.add_argument('--v2',action='store_true')
args.add_argument('--control',action='store_true')
options=args.parse_args()
if options.v2:
    import search_exact_budget_v2 as search
else:
    import search_exact_budget as search

HERE=Path(__file__).resolve().parent
search.RUN=HERE/'runs/exact-local-2026-09-10'
search.TARGETS=adjacent_targets()
search.PROFILE=load_profile(HERE.parent/'profiles/regular-17-e-fixed-v1.yaml')
certificate=json.loads((HERE/'construction-12e-011.json').read_text())
score=10 if options.control else 9
state='k0-e'+str(score)
program=search.prefix(certificate['construction']['program'],score)
replay=ProgramReplayer().replay(program)
search.CONTEXTS[state]={'program':program,'names':replay.names,
 'objects':{n:o for n,o in replay.names.items() if isinstance(o,(Line,Circle))},'score':score}
search.assemble_points(state)
timings={}; calls={}
def instrument(name):
    original=getattr(search,name)
    def measured(*args,**kwargs):
        start=time.monotonic_ns()
        try: return original(*args,**kwargs)
        finally:
            timings[name]=timings.get(name,0)+time.monotonic_ns()-start
            calls[name]=calls.get(name,0)+1
    setattr(search,name,measured)
for name in ('intersect','simplify_point','object_from'):
    instrument(name)
signal.signal(signal.SIGALRM,search.timeout_handler)
faulthandler.dump_traceback_later(15)
start=time.monotonic_ns(); signal.alarm(30)
try:
    records=search.CONTEXTS[state]['points']
    inputs=[next(i for i,p in enumerate(records) if p.get('name')==n) for n in ('ggb_N','ggb_O')] if options.control else [3,12]
    result=search.two_job({'phase':'two','state':state,'op':'circle','inputs':inputs,'id':'diagnostic-control' if options.control else 'diagnostic-only'})
    if options.control:
        assert result['hits'] and all(h['score']==12 for h in result['hits'])
        result['independently_verified']=search.verify_hits(result)
    status='complete'
except TimeoutError:
    result={}; status='deferred'
finally:
    signal.alarm(0); faulthandler.cancel_dump_traceback_later()
report={'version':2 if options.v2 else 1,'control':options.control,'status':status,'elapsed_ms':(time.monotonic_ns()-start)//1000000,
 'measured_ms':{k:v//1000000 for k,v in timings.items()},'calls':calls,'result':result}
search.dump_json(search.RUN/('cost-diagnostic-control-v2.json' if options.control else 'cost-diagnostic-v2.json' if options.v2 else 'cost-diagnostic.json'),report)
print(json.dumps(report,indent=2),flush=True)
