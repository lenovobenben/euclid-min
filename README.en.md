# Euclid-Min · A 12 E Regular 17-gon Construction

[简体中文](README.md) · **English**

Euclid-Min focuses on a verified **12 E straightedge-and-compass construction** of the two vertices adjacent to a fixed vertex of a regular 17-gon: **3 lines and 9 paid circles**.

[Offline interactive player](qq-ggb/web/README.md) · [4K Manim animation](animations/e12/E12Construction-4K.mp4) · [GeoGebra](qq-ggb/ggb/README.md) · [Certificate](qq-ggb/construction-12e-011.json) · [Verification report](qq-ggb/verification-12e.json)

## Problem and metric

The free initial objects are O=(0,0), A=(1,0), and their unit circle. The goal is either point (cos(2π/17), ±sin(2π/17)). The complete polygon is not required.

Drawing a line through two existing distinct points or a circle centered at one existing point through another costs 1 E. Intersections are free. The compass collapses; arbitrary points and direct distance transfer are forbidden. Composite tasks such as constructing a midpoint must be expanded into elementary operations.

The authoritative rules are the [profile](profiles/regular-17-e-fixed-v1.yaml), [formal model](docs/FORMAL_MODEL.md), and [metric](docs/METRICS.md).

## Evidence and attribution

The certificate reaches both targets for the first time at 12 E with no duplicate draws. SageMath exact replay, an independent radical proof, and an independent certificate replayer cross-check all 18 named points. Deliberately invalid inputs are rejected.

The underlying geometry comes from a GGB file supplied through a QQ discussion group. Its original creator and earliest publication are unconfirmed. Euclid-Min changes the K and P intersection branches to reach the required adjacent vertices in the same twelve moves, and supplies the certificate, exact checks, and demonstrations. See [provenance and branch enumeration](qq-ggb/README.md).

The rigorous current bounds are **5 < OPT ≤ 12**. Scores 0–5 E have been exhaustively excluded and independently checked; 6–11 E have not. This is a verified upper bound, with no claim of global minimality or a world record. Negative [local searches](qq-ggb/search-hour-2026-09-11.md) apply only to their documented scopes.

## Demonstrations

Download [index.html](qq-ggb/web/index.html) and open it in a browser for an entirely offline interactive player. The [editable GeoGebra file](qq-ggb/ggb/正十七边形-12E.ggb) preserves native dependencies and allows moving the initial points.

The [Manim animation](animations/e12/README.md) uses a dark blue background, magenta initial circle, gold active strokes, compass guides, a move counter, and a final view of both adjacent vertices. Its geometry comes from the same exactly verified decimal snapshot as the web player; Manim performs only presentation calculations.

## Reproduction

Use SageMath 10.7. From the repository root:

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  qq-ggb/construction-12e-011.json --json
```

Expected: `valid: true`, 3 lines, 9 circles, `first_target_e_move: 12`, and both targets. To run tests, replace the command after the image with `sage -python -m unittest discover -s tests -v`.

See [Sage instructions](sage/README.md), [animation reproduction](animations/e12/README.md), [certificate format](docs/CERTIFICATE_FORMAT.md), and [bounded proofs](docs/M7_PROOF_MODE.md).

## Layout and license

`qq-ggb/` contains the construction and its evidence; `animations/e12/` contains the animation; `sage/euclid_min/` contains the exact kernel and search infrastructure; `profiles/`, `schemas/`, `proofs/`, and `tests/` fix semantics and support reproducibility.

Software is licensed under [Apache 2.0](LICENSE); mathematical documents, certificates, research data, and animation outputs under [CC BY 4.0](LICENSE-CONTENT). Third-party material retains its own rights. See [license scope](LICENSE-SCOPE.md). Cite [CITATION.cff](CITATION.cff) and the commit or version used.
