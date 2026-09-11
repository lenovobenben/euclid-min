"""Exercise restore from a compact ledger with all exact pair caches absent."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import search_exact_budget_v2 as support

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/exact-local-v2-2026-09-11'


def main():
    start=time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix='qq-restore-check-') as temporary:
        directory=Path(temporary)
        for name in ('manifest.json','job-ledger.jsonl.gz'):
            shutil.copyfile(RUN/name,directory/name)
        for path in RUN.glob('candidate-*.json'):
            shutil.copyfile(path,directory/path.name)
        result=subprocess.run([sys.executable,str(HERE/'summarize_exact_search.py'),'--restore',str(directory)],
          text=True,capture_output=True,timeout=30,check=True)
        restoration=json.loads(result.stdout)
        assert not list((directory/'jobs').glob('*-pair-*.json'))
        result=subprocess.run([sys.executable,str(HERE/'search_exact_budget_v2.py'),
          '--run-dir',str(directory),'--seconds','40','--workers','2','--one-step-only'],
          text=True,capture_output=True,timeout=60)
        if result.returncode: raise AssertionError(result.stdout+result.stderr)
        summary=json.loads((directory/'summary.json').read_text())
        assert summary['positive_control_passed']
        assert summary['stages']['closure']['complete']==266
        assert all(state['full_closure'] for state in summary['states'].values())
        assert summary['stages']['one_step']['complete']==234
        assert summary['stages']['one_step']['tested_parameterizations']==20451
        assert not summary['shorter_found']
        report={'status':'passed','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'restored_non_pair_jobs':restoration['restored_non_pair_jobs'],
          'pair_caches_initially_absent':True,'exact_pair_jobs_regenerated':266,
          'one_step_cached_jobs':234,'positive_control_reverified':True,
          'elapsed_ms':(time.monotonic_ns()-start)//1000000}
    support.dump_json(RUN/'checkpoint-restore-report.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
