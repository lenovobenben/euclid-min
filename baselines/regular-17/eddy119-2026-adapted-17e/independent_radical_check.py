"""Independent exact check of the 17 E adaptation of Eddy119's construction.

No euclid-min modules or target predicates are imported.  The radicals below
come directly from the equations of the construction's circles and lines.

Public source: Eddy119, February 28, 2026, full 37-move polygon construction:
https://gist.github.com/mrflip/a973b1c60f4a38fc3277ddd57ce65b28?permalink_comment_id=6006486

Adaptation: give d1 for free, omit unused d17, then draw the diameter through
the lower intersection of d1 and d18.  This is 10 circles plus 7 lines.
"""

import json

from sage.all import AA, QQ, QQbar


half = AA(1) / 2
sqrt17 = AA(17).sqrt()

# d8: center (3/4, 0), through (1/2, -1).
left = (3 - sqrt17) / 4
right = (3 + sqrt17) / 4

# Right intersections of d9 and d10 with the horizontal axis.
h = left + ((half - left) ** 2 + 1).sqrt()
u = h - half
v = right + ((right - half) ** 2 + 1).sqrt()

# d13 is y=u/2.  Intersecting it with d14, through (1/2,u) and
# (v,0), produces d15's center.  Circle d15 passes through O.
cx = (half + v) / 2
cy = u / 2

# Substitute x=1 into d15: y^2 - 2*cy*y + 1 - 2*cx = 0.
# Select the upper root, point 134 = (1,t).
t = cy + (cy**2 + 2 * cx - 1).sqrt()

# d18 has center A=(1,0) and radius t.  On the unit circle its
# intersection x coordinate is 1-t^2/2.  A diameter gives its antipode.
c = t**2 / 2 - 1
positive_y = (1 - c * c).sqrt()

R = QQ["X"]
X = R.gen()
p = (
    256 * X**8 + 128 * X**7 - 448 * X**6 - 192 * X**5
    + 240 * X**4 + 80 * X**3 - 40 * X**2 - 8 * X + 1
)
lower = QQ(9324) / 10000
upper = QQ(9325) / 10000
roots_in_interval = [
    (root, multiplicity)
    for root, multiplicity in p.roots(AA)
    if lower < root < upper
]

# Independent cyclotomic comparison, without the project's target code.
z = QQbar.zeta(17)
checks = {
    "circle_d15_equation_at_point_134": bool(1 + t*t - 2*cx - 2*cy*t == 0),
    "cosine_polynomial_zero": bool(p(c) == 0),
    "c_in_rational_isolating_interval": bool(lower < c < upper),
    "unique_root_in_interval": len(roots_in_interval) == 1,
    "root_in_interval_is_simple": len(roots_in_interval) == 1
        and roots_in_interval[0][1] == 1,
    "z_is_nontrivial_17th_root": bool(z**17 == 1 and z != 1),
    "c_equals_primitive_root_real_part": bool(QQbar(c) == (z + z**(-1)) / 2),
    "positive_y_equals_primitive_root_imag_part": bool(QQbar(positive_y) == z.imag()),
}

report = {
    "source_url": "https://gist.github.com/mrflip/a973b1c60f4a38fc3277ddd57ce65b28?permalink_comment_id=6006486",
    "method": "Independent circle equations and exact nested radicals using Sage AA and QQbar; no project imports",
    "adapted_draw_count": {"lines": 7, "circles": 10, "E": 17},
    "checks": checks,
    "all_checks_passed": all(checks.values()),
    "isolating_interval": {"lower": str(lower), "upper": str(upper)},
    "distinct_real_roots_in_interval": len(roots_in_interval),
    "real_root_multiplicities_in_interval": [int(m) for _, m in roots_in_interval],
    "cosine_polynomial": str(p),
    "c_minimal_polynomial": str(c.minpoly()),
    "approximate_values_for_display_only": {
        "left": str(left), "right": str(right), "h": str(h),
        "u": str(u), "v": str(v), "d15_center_x": str(cx),
        "d15_center_y": str(cy), "point_134_y": str(t),
        "target_x": str(c), "target_y": str(positive_y),
    },
}
print(json.dumps(report, indent=2, ensure_ascii=False))
assert report["all_checks_passed"], "An independent exact check failed"
