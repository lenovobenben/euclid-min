"""Read and replay the actual certificate without importing any project code.

Geometry is recomputed in exact Sage AA. Line/circle intersections use direct
coordinate substitution into a quadratic. Targets come from a rational
polynomial and an exact root-of-unity identity, not decimal coordinates.
"""
import copy
import hashlib
import json
from pathlib import Path

from sage.all import AA, QQ, QQbar, LaurentPolynomialRing

HERE=Path(__file__).resolve().parent
CERTIFICATE=HERE/'construction-12e-011.json'


def require(condition,code):
    if not condition:
        raise ValueError(code)


def unique_object(pairs):
    result={}
    for k,v in pairs:
        require(k not in result,'duplicate_json_key')
        result[k]=v
    return result


def simplify(values):
    for v in values:
        v.simplify()
    return tuple(values)


def make_line(p,q):
    require(p!=q,'coincident_points')
    x,y=p; u,v=q
    values=(y-v,u-x,x*v-u*y)
    scale=values[0] if values[0]!=0 else values[1]
    return simplify(tuple(a/scale for a in values))


def quadratic(a,b,c):
    require(a!=0,'zero_quadratic_coefficient')
    discriminant=b*b-4*a*c
    if discriminant<0:
        return []
    if discriminant==0:
        return [-b/(2*a)]
    d=discriminant.sqrt()
    return [(-b-d)/(2*a),(-b+d)/(2*a)]


def line_circle(line,circle):
    a,b,c=line; u,v,r2=circle
    if b!=0:
        m,n=-a/b,-c/b
        roots=quadratic(1+m*m,2*(m*(n-v)-u),u*u+(n-v)**2-r2)
        return [(x,m*x+n) for x in roots]
    x=-c/a
    return [(x,y) for y in quadratic(AA(1),-2*v,v*v+(x-u)**2-r2)]


def intersection(first,second):
    kind1,p=first; kind2,q=second
    require(first!=second,'coincident_objects')
    if kind1==kind2=='line':
        a,b,c=p; d,e,f=q
        determinant=a*e-b*d
        points=[] if determinant==0 else [((b*f-c*e)/determinant,(c*d-a*f)/determinant)]
    elif kind1==kind2=='circle':
        x,y,r2=p; u,v,s2=q
        if x==u and y==v:
            points=[]
        else:
            radical=(2*(u-x),2*(v-y),x*x+y*y-r2-u*u-v*v+s2)
            points=line_circle(radical,p)
    else:
        points=line_circle(p,q) if kind1=='line' else line_circle(q,p)
    points=sorted(simplify(point) for point in points)
    return [p for i,p in enumerate(points) if i==0 or p!=points[i-1]]


def contains(obj,point):
    kind,value=obj; x,y=point
    if kind=='line':
        a,b,c=value
        return a*x+b*y+c==0
    u,v,r2=value
    return (x-u)**2+(y-v)**2==r2


ring=QQ['X']; X=ring.gen()
cosine_polynomial=256*X**8+128*X**7-448*X**6-192*X**5+240*X**4+80*X**3-40*X**2-8*X+1
laurent=LaurentPolynomialRing(QQ,'Z'); Z=laurent.gen()
require(Z**8*cosine_polynomial((Z+Z**(-1))/2)==sum(Z**i for i in range(17)),
        'cyclotomic_polynomial_identity')
roots=sorted(cosine_polynomial.roots(AA,multiplicities=False))
require(len(roots)==8,'expected_eight_distinct_real_roots')
tx=roots[-1]
require(QQ(9324)/10000<tx<QQ(9325)/10000,'isolating_interval')
ty=(1-tx*tx).sqrt()
TARGETS={'B_plus':(tx,ty),'B_minus':(tx,-ty)}


def replay(certificate):
    names={'O':('point',(AA(0),AA(0))),'A':('point',(AA(1),AA(0))),
           'unit_circle':('circle',(AA(0),AA(0),AA(1)))}
    objects=[names['unit_circle']]
    score=0; lines=0; circles=0; duplicates=0; first_target=None
    reached=set(); steps=[]
    def ref(name,expected):
        require(name in names,'unknown_reference')
        kind,value=names[name]
        require(kind in expected,'wrong_reference_type')
        return value
    for index,entry in enumerate(certificate['construction']['program']):
        identifier=entry['id']; op=entry['op']
        require(identifier not in names,'duplicate_id')
        row={'program_index':index,'id':identifier,'op':op}
        if op=='line':
            require(set(entry)=={'id','op','through'} and len(entry['through'])==2,'invalid_line_fields')
            p,q=[ref(n,('point',)) for n in entry['through']]
            obj=('line',make_line(p,q)); lines+=1
        elif op=='circle':
            require(set(entry)=={'id','op','center','through'},'invalid_circle_fields')
            center=ref(entry['center'],('point',)); through=ref(entry['through'],('point',))
            require(center!=through,'coincident_points')
            u,v=center; x,y=through
            obj=('circle',simplify((u,v,(x-u)**2+(y-v)**2))); circles+=1
        elif op=='intersect':
            require(set(entry)=={'id','op','objects','index'} and len(entry['objects'])==2,'invalid_intersect_fields')
            for n in entry['objects']: ref(n,('line','circle'))
            pair=[names[n] for n in entry['objects']]
            points=intersection(*pair)
            selected=entry['index']
            require(type(selected) is int and 0<=selected<len(points),'invalid_intersection_index')
            obj=('point',points[selected])
            require(all(contains(o,obj[1]) for o in pair),'intersection_incidence_failed')
            row.update({'intersection_count':len(points),'selected_exact_lex_index':selected})
        else:
            raise ValueError('unsupported_operation')
        names[identifier]=obj
        if op in ('line','circle'):
            score+=1
            if obj in objects:
                duplicates+=1
            else:
                objects.append(obj)
                for name,target in TARGETS.items():
                    if sum(contains(o,target) for o in objects)>=2:
                        reached.add(name)
                if reached and first_target is None:
                    first_target=score
        row['e_move']=score
        steps.append(row)
    require(score==certificate['assertions']['score']['e_move'],'score_assertion_mismatch')
    require(bool(reached),'target_not_reached')
    require(reached==set(certificate['assertions']['targets']),'target_assertion_mismatch')
    return {'lines':lines,'paid_circles':circles,'score':score,'duplicate_draws':duplicates,
            'first_target_e_move':first_target,'targets':sorted(reached),'steps':steps},names


def radical_points():
    d=-AA(17).sqrt(); k=(d-3)/4
    lx=(d-9)/16; mx=(d-1)/8; u=(d-9)/8
    n=k+((k+1)**2+1).sqrt()
    px=(n-3+((n-3)**2-4*(5+2*u*(n+2))).sqrt())/4
    qx=2*(px+1)**2-1; qy=(1-qx*qx).sqrt()
    values={'O':(AA(0),AA(0)),'A':(AA(1),AA(0)),
      'ggb_C':(-1,0),'ggb_D':(-QQ(3)/4,AA(15).sqrt()/4),
      'ggb_E':(-QQ(3)/4,-AA(15).sqrt()/4),'ggb_F':(-2,0),
      'ggb_G':(-QQ(3)/4,AA(7).sqrt()/4),'ggb_H':(-QQ(1)/2,AA(3).sqrt()/2),
      'ggb_I':(-QQ(3)/4,0),'ggb_J':(-1,1),'ggb_K':(k,0),
      'ggb_L':(lx,(4-(lx-1)**2).sqrt()),'ggb_M':(mx,-(1-mx*mx).sqrt()),
      'ggb_N':(n,0),'ggb_O':(u,-(2-(u+2)**2).sqrt()),
      'ggb_P':(px,AA(3).sqrt()*(px+1)),'ggb_Q':(qx,qy),'ggb_R':(qx,-qy)}
    return {name:simplify(tuple(AA(v) for v in point)) for name,point in values.items()}


def main():
    raw=CERTIFICATE.read_bytes()
    certificate=json.loads(raw.decode('utf-8'),object_pairs_hook=unique_object)
    result,names=replay(certificate)
    expected=radical_points()
    correspondence={name:names[name]==('point',point) for name,point in expected.items()}
    require(all(correspondence.values()),'radical_certificate_correspondence_failed')
    point=names['ggb_Q'][1]
    complex_point=QQbar(point[0])+QQbar.gen()*QQbar(point[1])
    require(complex_point**17==1 and complex_point!=1,'not_a_primitive_17th_root')
    controls={}
    mutants=[]
    old_branch=copy.deepcopy(certificate)
    for entry in old_branch['construction']['program']:
        if entry['id']=='ggb_K': entry['index']=1
        if entry['id']=='ggb_P': entry['index']=0
    mutants.append(('original_nonadjacent_branch',old_branch,'target_not_reached'))
    bad_score=copy.deepcopy(certificate); bad_score['assertions']['score']['e_move']=11
    mutants.append(('false_11_e_score',bad_score,'score_assertion_mismatch'))
    bad_index=copy.deepcopy(certificate)
    next(e for e in bad_index['construction']['program'] if e['id']=='ggb_K')['index']=2
    mutants.append(('out_of_range_intersection',bad_index,'invalid_intersection_index'))
    bad_circle=copy.deepcopy(certificate)
    next(e for e in bad_circle['construction']['program'] if e['id']=='ggb_d')['through']='ggb_C'
    mutants.append(('zero_radius_circle',bad_circle,'coincident_points'))
    for label,mutant,expected_error in mutants:
        try:
            replay(mutant)
            raise AssertionError('Mutant was accepted: '+label)
        except ValueError as error:
            require(str(error)==expected_error,'unexpected_negative_control_failure')
            controls[label]={'rejected':True,'reason':str(error)}
    report={
      'method':'Independent direct substitution into exact AA quadratics; no euclid_min imports, no floats, no tolerances',
      'scope':'Mathematical replay of the actual JSON certificate; project CLI separately validates its schema and JCS hashes',
      'certificate_sha256':hashlib.sha256(raw).hexdigest(),
      'construction_sha256_declared':certificate['integrity']['construction_sha256'],
      'result':result,'all_18_points_match_independent_radicals':all(correspondence.values()),
      'point_correspondence':correspondence,
      'cyclotomic_polynomial_identity':True,'Q_is_nontrivial_17th_root':True,
      'Q_x_is_largest_of_8_cosine_roots':bool(point[0]==tx),
      'negative_controls':controls,'all_checks_passed':True,
    }
    (HERE/'independent-certificate-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('point_correspondence','result')},indent=2),flush=True)
    print(json.dumps({k:v for k,v in result.items() if k!='steps'},indent=2),flush=True)


if __name__=='__main__':
    main()
