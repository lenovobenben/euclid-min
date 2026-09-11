"""Independent exact proof of the 12 E branch, with no euclid_min imports."""
import json
from pathlib import Path
from sage.all import AA, QQ, QQbar

HERE=Path(__file__).resolve().parent
# Choose the other k-axis intersection: the negative square root of 17.
d=-AA(17).sqrt()
k=(d-3)/4
p2=(k+1)**2+1
lx=(d-9)/16
ly=(4-(lx-1)**2).sqrt()
q2=(lx+1)**2+ly**2
mx=(q2-2)/2
my=-(1-mx**2).sqrt()
r2=(mx-k)**2+my**2
n=k+p2.sqrt()
ox=(d-9)/8
oy=-(2-(ox+2)**2).sqrt()
s2=(n-ox)**2+oy**2
discriminant=(n-3)**2-4*(5+2*ox*(n+2))
# Choose the other s/i intersection: the larger x coordinate.
px=(n-3+discriminant.sqrt())/4
py=AA(3).sqrt()*(px+1)
t2=(px+1)**2+py**2
qx=(t2-2)/2
qy=(1-qx**2).sqrt()
for value in (k,lx,ly,mx,my,n,ox,oy,px,py,qx,qy):
    value.simplify()
z=QQbar.zeta(17)
ring=QQ['X']; X=ring.gen()
poly=256*X**8+128*X**7-448*X**6-192*X**5+240*X**4+80*X**3-40*X**2-8*X+1
lower,upper=QQ(9324)/10000,QQ(9325)/10000
checks={
 'K_on_circle_k':bool((k+AA(3)/4)**2==AA(17)/16),
 'K_negative_branch':bool(k<-AA(3)/4),
 'L_on_circle_e':bool((lx-1)**2+ly**2==4),
 'L_on_circle_p':bool((lx-k)**2+ly**2==p2),
 'M_on_unit_circle':bool(mx**2+my**2==1),
 'M_on_circle_q':bool((mx+1)**2+my**2==q2),
 'O_on_circle_h':bool((ox+2)**2+oy**2==2),
 'O_on_circle_r':bool((ox-k)**2+oy**2==r2),
 'N_on_circle_p':bool((n-k)**2==p2),
 'N_larger_x_branch':bool(n>k),
 'P_on_line_i':bool(py==AA(3).sqrt()*(px+1)),
 'P_on_circle_s':bool((px-n)**2+py**2==s2),
 'P_larger_x_branch':bool(discriminant>0 and px>(n-3)/4),
 'Q_on_unit_circle':bool(qx**2+qy**2==1),
 'Q_on_circle_t':bool((qx+1)**2+qy**2==t2),
 'cosine_polynomial_vanishes':bool(poly(qx)==0),
 'qx_in_isolating_interval':bool(lower<qx<upper),
 'unique_polynomial_root_in_interval':sum(lower<a<upper for a,_ in poly.roots(AA))==1,
 'Q_equals_zeta17':bool(QQbar(qx)+QQbar.gen()*QQbar(qy)==z),
 'R_equals_inverse_zeta17':bool(QQbar(qx)-QQbar.gen()*QQbar(qy)==z**(-1)),
}
report={
 'method':'Independent circle equations and nested radicals using Sage AA/QQbar; no project imports',
 'source':'QQ discussion group supplied file; original creator not established',
 'branch_change':{'K':{'original_index':1,'new_index':0},'P':{'original_index':0,'new_index':1}},
 'checks':checks,'all_checks_passed':all(checks.values()),
 'Q_x_minimal_polynomial':str(qx.minpoly()),
 'Q_x_isolating_interval':[str(lower),str(upper)],
 'score':{'lines':3,'paid_circles':9,'e_move':12},
}
(HERE/'independent-12e-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
assert report['all_checks_passed']
