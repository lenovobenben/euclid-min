# DeTemple 1991 Carlyle 圆构造的 profile 转写

## 结论与证据等级

本目录把 DeTemple 论文第 4 节、图 3、步骤 (i)–(x) 的未经修改正十七边形构造，转写为 `regular-17-e-fixed-v1`。`construction.json` 已由 SageMath 10.7 reference verifier 精确重放：

```text
直线：11
圆：21
总分：32 E
首次命中：第 32 E
目标：B_plus、B_minus
```

这是一个 `converted` 的已验证构造和搜索上界，不是最优性结论。原文的初始对象、圆规能力和计分法与当前 profile 不同。

## 来源

- Duane W. DeTemple, “Carlyle Circles and the Lemoine Simplicity of Polygon Constructions,” *The American Mathematical Monthly* 98(2), 1991, 97–108；[JSTOR 稳定页](https://www.jstor.org/stable/2323939)。
- 具体构造位于第 102–104 页、图 3、步骤 (i)–(x)；[可核对 PDF](https://sharingthesoul.wordpress.com/wp-content/uploads/2021/03/carlyle-and-lemoine-polygon-constructions-detemple1991.pdf)。

原文以单位圆和两条坐标轴为初始对象，使用 modern non-collapsing compass。它报告未经修改路线的 Lemoine simplicity 为 51，随后修改路线为 45。它们不是 E-move，不能与本项目重算的 32 E 直接比较。

## 数学主线

令

\[
\eta_{i,j}=\sum_{k\equiv i\pmod j}\zeta^{k},\qquad
\zeta=e^{2\pi i/17}.
\]

构造逐层使用二次方程：

\[
\eta_{0,2}+\eta_{1,2}=-1,\qquad
\eta_{0,2}\eta_{1,2}=-4,
\]

\[
\eta_{0,4}+\eta_{2,4}=\eta_{0,2},\quad
\eta_{0,4}\eta_{2,4}=-1,
\]

\[
\eta_{1,4}+\eta_{3,4}=\eta_{1,2},\quad
\eta_{1,4}\eta_{3,4}=-1,
\]

\[
\eta_{0,8}+\eta_{4,8}=\eta_{0,4},\qquad
\eta_{0,8}\eta_{4,8}=\eta_{1,4}.
\]

Carlyle 圆把给定二次多项式的两个实根表现为圆与横轴的交点。最后得到

\[
H_{0,8}=\eta_{0,8}=2\cos(2\pi/17).
\]

以该点为圆心、单位长度为半径的圆与初始单位圆相交，两个交点就是

\[
B_\pm=(\cos(2\pi/17),\ \pm\sin(2\pi/17)).
\]

## 转写与计分

| 分组 | 直线 | 圆 | E |
|---|---:|---:|---:|
| 构造横轴、纵轴 | 2 | 2 | 4 |
| 原步骤 (i)–(v) | 3 | 9 | 12 |
| 步骤 (vi) 第一次距离搬运 | 2 | 3 | 5 |
| 原步骤 (vii)–(ix) | 2 | 3 | 5 |
| 步骤 (x) 单位长度搬运及目标圆 | 2 | 4 | 6 |
| 合计 | 11 | 21 | 32 |

两次距离搬运均按 Euclid I.2 风格展开，只使用 `line`、`circle` 和零成本的确定性交点绑定。证书没有把中点、垂直平分线、Carlyle 圆或距离复制当成免费宏。

## 可复现文件

- `construction.json`：正式构造证书；
- `verification.json`：独立验证报告；
- `source.yaml`：来源、工具假设和可比性台账；
- `sage/experiments/build_detemple_1991_baseline.py`：确定性生成器。
