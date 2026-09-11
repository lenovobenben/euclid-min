"""Build a self-contained visual player from the exact 12 E certificate.

Run in Sage Docker. All construction, incidence and target checks use exact AA.
Only the final display serialization quantizes algebraic values to decimal
strings, using integer floor on AA. There is no float geometry or tolerance.
"""
import hashlib
import json
import sys
from pathlib import Path
from sage.all import AA,QQ
from euclid_min.geometry import Point,Line,Circle
from euclid_min.replay import ProgramReplayer
from euclid_min.formats import construction_sha256,load_profile

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
ROOT=SOURCE.parent
sys.path.insert(0,str(SOURCE))
from independent_certificate_check import replay as independent_replay

PLACES=12
SCALE=10**PLACES


def decimal(value):
    """Exact round-to-display only; no approximate arithmetic feeds geometry."""
    n=int((AA(value)*SCALE+QQ(1)/2).floor())
    sign='-' if n<0 else ''; whole,fraction=divmod(abs(n),SCALE)
    return (sign+str(whole)+'.'+str(fraction).zfill(PLACES)).rstrip('0').rstrip('.')


def xy(point): return [decimal(point.x),decimal(-point.y)]


def circle_path(circle,through):
    other=Point(2*circle.center.x-through.x,2*circle.center.y-through.y)
    p,q=xy(through),xy(other); r=decimal(circle.radius_squared.sqrt())
    return f'M {p[0]} {p[1]} A {r} {r} 0 1 1 {q[0]} {q[1]} A {r} {r} 0 1 1 {p[0]} {p[1]}'


def line_ends(line):
    points=[]; limit=QQ(64)
    if line.b!=0:
        for x in (-limit,limit):
            y=(-line.a*x-line.c)/line.b
            if -limit<=y<=limit: points.append(Point(x,y))
    if line.a!=0:
        for y in (-limit,limit):
            x=(-line.b*y-line.c)/line.a
            if -limit<=x<=limit and not any(Point(x,y)==p for p in points): points.append(Point(x,y))
    assert len(points)==2
    return [xy(p) for p in points]


def main():
    path=SOURCE/'construction-12e-011.json'; raw=path.read_bytes()
    certificate=json.loads(raw)
    profile=load_profile(ROOT/'profiles/regular-17-e-fixed-v1.yaml')
    assert profile.sha256==certificate['profile']['sha256']
    assert construction_sha256(certificate['construction'])==certificate['integrity']['construction_sha256']
    program=certificate['construction']['program']
    result=ProgramReplayer().replay(program)
    independent,names=independent_replay(certificate)
    assert (result.e_move,result.line_draws,result.circle_draws,result.first_target_e_move,result.duplicate_draws)==(12,3,9,12,0)
    assert independent['score']==12 and independent['first_target_e_move']==12
    for key,value in result.names.items():
        if isinstance(value,Point): assert names[key]==('point',(value.x,value.y))
    births={'O':0,'A':0,'unit_circle':0}; e=0
    for entry in program:
        if entry['op'] in ('line','circle'): e+=1; births[entry['id']]=e
        else: births[entry['id']]=max(births[n] for n in entry['objects'])
    last_use={}; steps=[]; lines=0; circles=0
    for entry in program:
        if entry['op']=='intersect': continue
        value=result.names[entry['id']]; n=len(steps)+1
        refs=entry['through'] if entry['op']=='line' else [entry['center'],entry['through']]
        assert all(births[r]<n for r in refs)
        for r in refs: last_use[r]=n
        xs=[AA(-1),AA(1)]; ys=[AA(-1),AA(1)]
        for key in refs:
            p=result.names[key]; xs.append(p.x); ys.append(-p.y)
        step={'e':n,'id':entry['id'],'op':entry['op'],'refs':refs}
        if isinstance(value,Circle):
            circles+=1; radius=value.radius_squared.sqrt()
            step.update({'path':circle_path(value,result.names[entry['through']]),
              'center':xy(value.center),'radius':decimal(radius)})
            xs.extend((value.center.x-radius,value.center.x+radius))
            ys.extend((-value.center.y-radius,-value.center.y+radius))
        else:
            lines+=1; step['ends']=line_ends(value)
        for key,point in result.names.items():
            if isinstance(point,Point) and births[key]==n:
                xs.append(point.x); ys.append(-point.y)
        pad=QQ(2)/5
        step['frame']=[decimal(min(xs)-pad),decimal(min(ys)-pad),decimal(max(xs)+pad),decimal(max(ys)+pad)]
        step['counts']={'lines':lines,'circles':circles}
        steps.append(step)
    label_offsets={'O':[-14,22],'A':[15,18],'ggb_C':[-15,21],'ggb_D':[14,-11],
      'ggb_E':[14,20],'ggb_F':[-15,22],'ggb_G':[15,-10],'ggb_H':[14,-12],
      'ggb_I':[14,22],'ggb_J':[-17,-11],'ggb_K':[-12,22],'ggb_L':[14,-14],
      'ggb_M':[-16,22],'ggb_N':[13,22],'ggb_O':[-15,22],'ggb_P':[14,-13],
      'ggb_Q':[20,-12],'ggb_R':[20,22]}
    labels={'ggb_O':'U','ggb_Q':'B₊','ggb_R':'B₋'}
    points={key:{'xy':xy(point),'birth':births[key],'lastUse':last_use.get(key,12),
      'label':labels.get(key,key.removeprefix('ggb_')),'offset':label_offsets[key]}
      for key,point in result.names.items() if isinstance(point,Point)}
    target=result.names['ggb_Q']; rr=QQ(9)/20
    angle_path=f'M {decimal(rr)} 0 A {decimal(rr)} {decimal(rr)} 0 0 0 {decimal(rr*target.x)} {decimal(-rr*target.y)}'
    data={'schema':'euclid-min-web-12e/v1','points':points,'steps':steps,
      'initial':{'path':circle_path(result.names['unit_circle'],result.names['A']),'frame':['-1.65','-1.4','1.65','1.4']},
      'resultFrame':['-1.4','-1.4','1.55','1.4'],'anglePath':angle_path,
      'source':{'certificate_sha256':hashlib.sha256(raw).hexdigest(),'construction_sha256':certificate['integrity']['construction_sha256'],
        'profile_sha256':profile.sha256,'channel':'QQ 讨论组网友提供给用户，首创者未确认。'},
      'verified':{'e':12,'lines':3,'paidCircles':9,'firstTarget':12,'targets':['ggb_Q','ggb_R'],
        'independentReplay':True},'certificate':certificate,
      'display':{'decimalPlaces':PLACES,'method':'Exact AA rounding to decimal strings for display only; no float geometry'}}
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    html=(HERE/'template.html').read_text(encoding='utf-8').replace('/* INLINE_STYLE */',(HERE/'style.css').read_text(encoding='utf-8'))
    html=html.replace('/* INLINE_PLAYER */',(HERE/'player.js').read_text(encoding='utf-8'))
    html=html.replace('/* INLINE_GEOMETRY */',encoded.replace('</','<\\/'))
    assert '/* INLINE_' not in html
    (HERE/'geometry.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'index.html').write_text(html,encoding='utf-8')
    report={'passed':True,'certificate_sha256':data['source']['certificate_sha256'],
      'exact_independent_point_comparisons':len(points),'paid_steps':12,'line_steps':lines,'circle_steps':circles,
      'first_target_e':12,'references_available_before_drawing':True,'display_only_decimal_places':PLACES,
      'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'geometry_sha256':hashlib.sha256((HERE/'geometry.json').read_bytes()).hexdigest()}
    (HERE/'export-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(json.dumps([{k:s[k] for k in ('e','op','frame')} for s in steps]))


if __name__=='__main__': main()
