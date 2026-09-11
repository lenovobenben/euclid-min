"""Independent exact proof from circle equations, without euclid_min imports."""
import json
from pathlib import Path
from sage.all import AA, QQ, QQbar

HERE = Path(__file__).resolve().parent
half = AA(1)/2
sqrt17 = AA(17).sqrt()
k = (sqrt17-3)/4
p_squared = (k+1)**2+1
lx = (sqrt17-9)/16
ly = (4-(lx-1)**2).sqrt()
q_squared = (lx+1)**2+ly**2
mx = (q_squared-2)/2
my = -(1-mx**2).sqrt()
r_squared = (mx-k)**2+my**2
n = k+p_squared.sqrt()
ox = (sqrt17-9)/8
oy = -(2-(ox+2)**2).sqrt()
s_squared = (n-ox)**2+oy**2
# P lies on y=sqrt(3)*(x+1), and on the circle centered at (n,0).
constant = 5+2*ox*(n+2)
discriminant = (n-3)**2-4*constant
px = (n-3-discriminant.sqrt())/4
py = AA(3).sqrt()*(px+1)
t_squared = (px+1)**2+py**2
qx = (t_squared-2)/2
qy = (1-qx**2).sqrt()
for v in (k,lx,ly,mx,my,ox,oy,n,px,py,qx,qy):
    v.simplify()

ring = QQ['X']; X=ring.gen()
polynomial = 256*X**8+128*X**7-448*X**6-192*X**5+240*X**4+80*X**3-40*X**2-8*X+1
z = QQbar.zeta(17)
lower,upper = QQ(-273663)/1000000, QQ(-273662)/1000000
checks = {
    'K_on_circle_k':bool((k+AA(3)/4)**2==AA(17)/16),
    'L_on_circle_e':bool((lx-1)**2+ly**2==4),
    'L_on_circle_p':bool((lx-k)**2+ly**2==p_squared),
    'M_on_unit_circle':bool(mx**2+my**2==1),
    'M_on_circle_q':bool((mx+1)**2+my**2==q_squared),
    'O_on_circle_h':bool((ox+2)**2+oy**2==2),
    'O_on_circle_r':bool((ox-k)**2+oy**2==r_squared),
    'N_on_circle_p':bool((n-k)**2==p_squared),
    'P_on_line_i':bool(py==AA(3).sqrt()*(px+1)),
    'P_on_circle_s':bool((px-n)**2+py**2==s_squared),
    'P_lower_x_branch':bool(discriminant>0 and px<(n-3)/4),
    'Q_on_unit_circle':bool(qx**2+qy**2==1),
    'Q_on_circle_t':bool((qx+1)**2+qy**2==t_squared),
    'cosine_polynomial_vanishes':bool(polynomial(qx)==0),
    'qx_in_isolating_interval':bool(lower<qx<upper),
    'unique_polynomial_root_in_interval':sum(lower<a<upper for a,_ in polynomial.roots(AA))==1,
    'Q_equals_zeta17_power_5':bool(QQbar(qx)+QQbar.gen()*QQbar(qy)==z**5),
    'extension_first_circle':bool(abs(z**10-z**5)**2==abs(1-z**5)**2),
    'extension_second_circle':bool(abs(z**3-z**10)**2==abs(1-z**10)**2),
    'extension_third_circle':bool(abs(z-z**3)**2==abs(z**5-z**3)**2),
}
report = {
    'method':'Independent nested radicals and circle equations in Sage AA/QQbar; no project imports',
    'checks':checks,'all_checks_passed':all(checks.values()),
    'Q_x_minimal_polynomial':str(qx.minpoly()),
    'Q_x_isolating_interval':[str(lower),str(upper)],
    'Q_angle_from_initial_vertex':'10*pi/17 = 5*(2*pi/17)',
    'minor_angle_CAQ':'7*pi/17',
}
(HERE/'independent-radical-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
assert report['all_checks_passed']
