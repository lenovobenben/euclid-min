"""Search the three effective intersection choices of the QQ-provided program."""
import itertools
import json
from pathlib import Path
from sage.all import QQbar
from euclid_min.formats import load_profile, construction_sha256
from euclid_min.replay import ProgramReplayer
from audit_and_convert import build_program, SOURCE_SHA256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
program,_,_=build_program()
profile=load_profile(ROOT/'profiles/regular-17-e-fixed-v1.yaml')
z=QQbar.zeta(17)
reports=[]
for indices in itertools.product(range(2),repeat=3):
    choices=dict(zip(('ggb_K','ggb_N','ggb_P'),indices))
    candidate=[dict(e, index=choices[e['id']]) if e['id'] in choices else dict(e) for e in program]
    print('START',choices,flush=True)
    try:
        replay=ProgramReplayer().replay(candidate)
        point=replay.names['ggb_Q']
        vertex=next((k for k in range(17) if QQbar(point.x)+QQbar.gen()*QQbar(point.y)==z**k),None)
        report={'indices':choices,'valid_program':True,'score':replay.e_move,'Q_vertex':vertex,
                'targets':[t.value for t in replay.targets],'first_target_e_move':replay.first_target_e_move}
        if replay.targets:
            construction={'id':'qq-ggb-12e-branches-'+''.join(map(str,indices)),
                          'title':'QQ 讨论组提供的 GeoGebra 构造变更交点分支得到的 12 E 相邻顶点（首创者未确认）',
                          'program':candidate}
            certificate={'schema':'euclid-min-certificate/v1','problem':'regular-17-adjacent-vertex',
              'profile':{'id':profile.data['id'],'sha256':profile.sha256},'construction':construction,
              'assertions':{'score':{'metric':'e_move','e_move':replay.e_move},'targets':report['targets'],'claim':'verified_construction'},
              'software':{'producer':{'name':'qq-ggb-branch-search','version':'1.0.0'}},
              'integrity':{'construction_sha256':construction_sha256(construction)}}
            filename='construction-12e-'+''.join(map(str,indices))+'.json'
            (HERE/filename).write_text(json.dumps(certificate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            report['certificate']=filename
    except Exception as error:
        report={'indices':choices,'valid_program':False,'error':str(error)}
    reports.append(report)
    print(json.dumps(report),flush=True)
    (HERE/'branch-search-report.json').write_text(json.dumps({
        'source_sha256':SOURCE_SHA256,
        'source_channel':'QQ discussion group; original creator not established',
        'scope':'Only the 8 combinations of K,N,P indices; other source choices fixed',
        'planned_configurations':8,'completed_configurations':len(reports),
        'all_eight_valid':len(reports)==8 and all(r['valid_program'] for r in reports),
        'results':reports},indent=2)+'\n')
assert len(reports)==8 and all(r['valid_program'] for r in reports)
assert sorted(r['Q_vertex'] for r in reports)==list(range(1,9))
