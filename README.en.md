# Euclid-Min

[简体中文](README.md) · **English**

Euclid-Min is an open-source computational mathematics project for studying **short straightedge-and-compass constructions**. It fixes the meaning of a move in a machine-readable rule profile, expands every constructed line and circle into elementary operations, and replays construction certificates exactly in SageMath.

The main result is currently a **17 E construction** of a vertex adjacent to a fixed vertex of a regular 17-gon. The repository also preserves an independent study of a regular 257-gon, while the regular 17-gon remains the primary focus.

> **Regular 17-gon: 17 E, consisting of 7 lines and 10 circles, verified exactly in SageMath.**

[Watch the 4K animation](animations/e17/media/videos/e17_progress/2160p30/E17Progress.mp4) · [View the certificate](baselines/regular-17/eddy119-2026-adapted-17e/construction.json) · [View the verification report](baselines/regular-17/eddy119-2026-adapted-17e/verification.json) · [Read the provenance, adaptation, and exact derivation](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md)

## Current results

| Problem | Rule profile | Verified result | Scope of the claim |
|---|---|---:|---|
| A vertex adjacent to a fixed vertex of a regular 17-gon | `regular-17-e-fixed-v1` | **17 E** | Current upper bound; global minimality has not been proved |
| Any adjacent pair of vertices of a regular 257-gon | `regular-257-free-edge-e-fixed-v1` | **69 E** | Reproducible baseline recovered from a public video; not presented as an optimization record |

The regular 17-gon construction contains 7 lines and 10 circles. It first reaches the target at exactly 17 E and does not redraw any existing object. It was extracted from the relevant prefix of Eddy119's public complete 37-move construction. Direct conversion to this project's target gives 18 E; dependency analysis then removes one unused circle, producing 17 E. The original author did not claim a 17 E result. The baseline directory records the original geometry, the project's adaptation, and the respective verification responsibilities separately. The earlier 19 E DeTemple adaptation is retained as a historical upper bound.

The repository also contains:

- a strict bounded exhaustive search through 5 E;
- replay of the 17 E certificate by the project verifier and an independent radical check;
- a complete geometry-algebra IR for the earlier 19 E certificate;
- all 32,193 one-move parameterizations from a fixed 17 E state;
- all 22,454 first-move objects and 202,855,848 restricted final-move parameterizations from a fixed 16 E prefix;
- a 4K Manim animation generated from the formal 17 E certificate.

The fixed-prefix searches rigorously exclude one- or two-move compressions of the earlier **19 E route**. They do not cover every possible earlier construction prefix and do not prove that 17 E is optimal.

## The regular 17-gon problem

The following objects are given for free:

\[
O=(0,0),\qquad A=(1,0),
\]

and the unit circle centered at \(O\) through \(A\):

\[
\Gamma_0:x^2+y^2=1.
\]

The goal is to construct either vertex of the regular 17-gon adjacent to \(A\) on \(\Gamma_0\):

\[
B_\pm=
\left(
\cos\frac{2\pi}{17},
\ \pm\sin\frac{2\pi}{17}
\right).
\]

The complete 17-gon does not have to be drawn. The construction succeeds as soon as either \(B_+\) or \(B_-\) appears as a determined intersection of existing lines or circles.

## What is an E-move?

This project uses the E-move, or elementary-move, count:

\[
E=\text{number of lines actually drawn}+\text{number of circles actually drawn}.
\]

| Operation | Cost |
|---|---:|
| Draw a line through two existing distinct points | 1 E |
| Draw a circle centered at one existing point through another existing point | 1 E |
| Compute or name a determined intersection of existing objects | 0 E |
| Initial points and the initial circle | 0 E |

The compass is **collapsible**: its opening cannot be retained to transfer a distance. The only elementary circle operation is

\[
\operatorname{Circle}(P,Q):
\quad\text{the circle centered at an existing point }P\text{ through an existing point }Q.
\]

A length \(|AB|\) cannot be measured and then used directly as the radius of a circle centered at a third point \(C\). Any such transfer must be expanded into legal elementary line and circle operations.

The following familiar instructions are not single moves in this model:

- construct a midpoint;
- construct a perpendicular, perpendicular bisector, or parallel line;
- bisect an angle;
- reflect a point;
- transfer an existing length;
- choose an arbitrary point in the plane, on a line, or on a circle.

Apart from the free initial points, every new point must be a determined intersection of previously drawn lines or circles. See the [metric specification](docs/METRICS.md) and [formal model](docs/FORMAL_MODEL.md) for the complete definitions.

### A simple example

If only two distinct points \(P,Q\) are given, constructing their midpoint requires:

1. draw the line \(PQ\): 1 E;
2. draw the two circles centered at \(P\) and \(Q\), each through the other point: 2 E;
3. connect the two circle-circle intersections: 1 E.

The total is 4 E; all intersection operations cost 0 E. If the line \(PQ\) were also given initially, the same task would cost 3 E. This is why move counts are directly comparable only when the initial objects, tool capabilities, free-point rules, target, and counting method all agree.

## Evidence chain for 17 E

The 17 E count is not based on manually counting a diagram. It is an exact result that can be replayed from scratch:

1. the [rule profile](profiles/regular-17-e-fixed-v1.yaml) fixes the initial objects, legal operations, and target;
2. the [source record](baselines/regular-17/eddy119-2026-adapted-17e/source.yaml) distinguishes the author's 37-move construction from this project's 18-to-17 E adaptation;
3. the [construction certificate](baselines/regular-17/eddy119-2026-adapted-17e/construction.json) records every line, circle, and intersection binding;
4. the SageMath verifier recomputes every geometric object and does not trust the score declared in the certificate;
5. the [verification report](baselines/regular-17/eddy119-2026-adapted-17e/verification.json) confirms legality, an E-score of 17, and an exact hit on \(B_+\);
6. the [independent radical report](baselines/regular-17/eddy119-2026-adapted-17e/independent_radical_report.json) does not import project code and separately proves that the target coordinates equal \((\cos(2\pi/17),\sin(2\pi/17))\);
7. the [human-readable derivation](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md) explains the 17 moves, metric conversion, and exact algebraic verification.

The construction content hash is:

```text
99c80e4ef288e73c3657f2da056b1ec3b9609cd5f7231bcad690f6bc0a722252
```

Floating-point arithmetic is used only for animation, heuristic ordering, and non-authoritative bucketing. Geometric equality, construction legality, state merging, and target detection use exact mathematical predicates.

## Literature and internet review

As of **September 5, 2026**, the public-source review conducted for this project found no reproducible construction with an E-score of 16 or less that simultaneously has:

- the same initial objects as `regular-17-e-fixed-v1`;
- only an unmarked straightedge and a collapsible compass;
- no arbitrary points or direct distance transfer;
- the same adjacent-vertex target on the unit circle;
- a complete step-by-step construction that can be checked.

Common “15-step” descriptions count compound operations such as constructing a perpendicular bisector or quartering an angle, and sometimes include drawing the remaining vertices. Lemoine scores such as 45, 50, 53, and 58 use a different weighted metric. Some constructions with few geometric objects allow a non-collapsible compass to transfer distances. These numbers cannot be read as E-scores under the current profile.

François Labelle's 1997 page, [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html), uses the same elementary counting core. Its historical regular 17-gon problem, however, asks for the complete polygon and charges for the first unit circle, so its published scores are not directly comparable.

In 2026, Eddy119 published a complete 37-move regular 17-gon construction with replay links. After recovering its geometric dependencies, this project found that the relevant first 18 geometric objects become an 18 E construction when converted to the current target. Circle `d17` has no downstream dependency; removing it gives 17 E. **The construction idea and relevant prefix are credited to Eddy119. The 18-to-17 E dependency pruning, current-profile certificate, and exact proof were completed by this project.**

The strongest statement supported by the current evidence is:

> Under `regular-17-e-fixed-v1`, the project has verified a 17 E construction adapted from the relevant prefix of a public 37-move construction through a rule conversion and one dependency-pruning step. As of the public-source review completed on September 5, 2026, no reproducible construction of 16 E or less under the same rules had been found.

This does not prove that 17 E is globally minimal. A public-source review cannot establish that unpublished constructions do not exist. Global optimality would require a complete exclusion of 0–16 E; the current strict lower bound excludes only 0–5 E.

## Public basis for the metric

The E-move metric was not introduced ad hoc for this result.

- François Labelle's 1997 [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html) defines complexity as the number of line and circle operations actually performed, using a collapsible compass and free intersections.
- Sava Grozdev and Deko Dekov's 2015 paper [*The Computer Improves the Steiner's Construction of the Malfatti Circles*](https://azbuki.bg/wp-content/uploads/2015/02/azbuki.bg_dmdocuments_MathInfo012015_Grozdev_Dekov.pdf) uses Labelle's metric: each line or circle costs 1 and intersections cost 0.
- Erik D. Demaine and Victor Luo's 2025 paper [*Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*](https://doi.org/10.2197/ipsjjip.33.1110) formally uses the term **E-move**: one elementary straightedge or compass operation costs 1 E, while point definitions are excluded from the E-score.

These sources support the elementary counting principle. Each source still has its own initial figure, target, and permitted operations, so similar counting terminology alone does not make final scores comparable.

## Regular 257-gon study

The [regular-257](regular-257/README.md) directory preserves a frame-by-frame recovery of a 69 E regular 257-gon construction from a public video, exact cyclotomic-field verification, a certificate, dependency analysis, and local 68 E searches.

That study uses a separate profile, `regular-257-free-edge-e-fixed-v1`. Its target is any pair of adjacent vertices on the given circle; neither vertex has to equal the free initial point on the circle. It is therefore a different problem from the regular 17-gon result, and the scores are not directly comparable.

The current 69 E baseline contains 65 lines and 4 circles. The existing 68 E searches exclude several explicitly frozen local replacements and candidate frontiers; they do not prove that 69 E is optimal.

## Reproducing the result locally

The reference environment is SageMath 10.7. All Python code in this repository is intended to run with the Python interpreter bundled with SageMath.

### Verify the regular 17-gon certificate

From the repository root, run:

```bash
docker run --rm --network none \
  -v "$PWD:/workspace:ro" \
  -w /workspace \
  -e PYTHONPATH=/workspace/sage \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  baselines/regular-17/eddy119-2026-adapted-17e/construction.json
```

Successful output includes:

```text
valid: true
lines: 7
circles: 10
e_move: 17
first_target_e_move: 17
target: B_plus
```

### Run the complete regular 17-gon test suite

```bash
docker run --rm --network none \
  -v "$PWD:/workspace:ro" \
  -w /workspace \
  -e PYTHONPATH=/workspace/sage \
  -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m unittest discover -s tests -v
```

See the [regular 257-gon documentation](regular-257/README.md) for its separate verification and test commands.

## Documentation index

Most detailed research notes are currently written in Chinese. The formal profiles, schemas, certificates, reports, and commands are machine-readable or language-independent.

| Topic | Document |
|---|---|
| Research scope, claim levels, and technical plan | [Research design](docs/euclid-min-design.md) |
| Formal semantics of objects, states, operations, and targets | [Formal model](docs/FORMAL_MODEL.md) |
| Authoritative E-move definition and comparability rules | [Metric specification](docs/METRICS.md) |
| Construction certificate and content-hash format | [Certificate format](docs/CERTIFICATE_FORMAT.md) |
| Source status and baseline conversion ledger | [Literature and baseline ledger](docs/LITERATURE.md) |
| 17 E provenance, adaptation, and exact derivation | [17 E baseline explanation](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md) |
| 17 E animation, storyboard, and reproduction | [Manim animation documentation](animations/e17/README.md) |
| Complete geometry-algebra IR for the earlier 19 E route | [Geometry-algebra IR](docs/GEOMETRY_ALGEBRA_IR.md) |
| Search and proof milestones | [Roadmap](docs/ROADMAP.md) |
| Strict bounded result through 5 E | [Bounded proof record](proofs/regular-17-through-5e.json) |
| SageMath usage | [SageMath reference-kernel guide](sage/README.md) |
| Independent regular 257-gon study | [regular-257](regular-257/README.md) |
| License boundaries | [License scope](LICENSE-SCOPE.md) |
| Citation metadata | [CITATION.cff](CITATION.cff) |

If narrative documentation conflicts with a versioned specification, the corresponding rule profile, schema, formal model, and metric specification take precedence.

## License and citation

This repository uses two licenses for different kinds of material:

- source code, tests, build scripts, configurations, and schemas are licensed under the [Apache License 2.0](LICENSE);
- mathematical documentation, construction certificates, search data, figures, and animations are licensed under the [Creative Commons Attribution 4.0 International License](LICENSE-CONTENT).

See [LICENSE-SCOPE.md](LICENSE-SCOPE.md) for the complete boundary and treatment of third-party material. If you use results from this project, cite it using [CITATION.cff](CITATION.cff) and identify the commit or release used. A license permits use and adaptation; it does not replace scholarly attribution.

## Project principle

> **Heuristics may guide the search, but every conclusion must be exactly replayable. Do not compare scores without matching rules, and do not claim minimality without a complete lower bound.**
