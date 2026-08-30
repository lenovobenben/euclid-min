# DeTemple 1991 修改版 Carlyle 圆构造的 29 E 转写

## 结论与证据等级

本目录把 DeTemple 论文第 104 页明确给出的两项修改转写为
`regular-17-e-fixed-v1`。SageMath 10.7 reference verifier 从磁盘独立加载证书并精确重放为：

```text
直线：10
圆：19
总分：29 E
首次命中：第 29 E
目标：B_plus、B_minus
重复绘制：0
```

因此 29 E 是同一 profile 下比原 32 E baseline 短 3 E 的新已验证上界。它不是
lower-bound proof，也不支持“全局最优”或“文献最短”声明。

## 来源与模型差异

- Duane W. DeTemple, “Carlyle Circles and the Lemoine Simplicity of Polygon
  Constructions,” *The American Mathematical Monthly* 98(2), 1991, 97–108；
  [JSTOR 稳定页](https://www.jstor.org/stable/2323939)。
- 十七边形主构造在第 102–104 页、图 3、步骤 (i)–(x)；两项修改位于第
  104 页；[可核对 PDF](https://sharingthesoul.wordpress.com/wp-content/uploads/2021/03/carlyle-and-lemoine-polygon-constructions-detemple1991.pdf)。

原文免费给出单位圆和坐标轴，使用 modern non-collapsing compass，并以
Lemoine simplicity 计分。本文为两条坐标轴计费，并把两次任意距离搬运展开成
可折叠圆规基础操作。因此原文修改版的 45 与这里的 29 E 不可直接比较。

## 两项修改为何成立

原路线先由 Carlyle 圆得到

\[
H_{0,2}=\eta_{0,2},\qquad H_{1,2}=\eta_{1,2},
\]

再分别作 (OH_{0,2})、(OH_{1,2}) 的中点。每个中点需要两个圆和一条
中垂线，合计 6 E。

第一项修改把变量缩放为 (x=2m)。由

\[
x^2+x-4=0
\]

得到

\[
m^2+\frac12m-1=0.
\]

该方程的 Carlyle 圆圆心是 (Q''=(-1/4,0))，并经过 (A_y=(0,1))；
它与横轴的两个交点恰好是

\[
M_{0,2}=\frac{\eta_{0,2}}2,\qquad
M_{1,2}=\frac{\eta_{1,2}}2.
\]

先用 3 E 作 (Q'O) 的中垂线得到 (Q'')，再用 1 E 作这个半尺度
Carlyle 圆，总计 4 E，较原步骤净省 2 E。

第二项修改复用步骤 (vi) 已画出的圆：该圆以 (O) 为圆心并经过
(Y=(0,1+\eta_{1,4}))。只需再画以 (Y) 为圆心、经过 (O) 的圆，便可用
一条直线得到 (OY) 的中垂线。直线 (YH_{0,4}) 与这条中垂线的交点为

\[
M_{0,4}=\left(\frac{\eta_{0,4}}2,
\frac{1+\eta_{1,4}}2\right),
\]

正是最后一个 Carlyle 圆的圆心。该段由 4 E 降为 3 E，再省 1 E。

## 计分

| 分组 | 直线 | 圆 | E |
|---|---:|---:|---:|
| 构造横轴、纵轴 | 2 | 2 | 4 |
| 步骤 (i)–(v)，含半尺度修改 | 2 | 8 | 10 |
| 步骤 (vi) 第一次距离搬运 | 2 | 3 | 5 |
| 修改后的步骤 (vii)–(ix) | 2 | 2 | 4 |
| 步骤 (x) 单位长度搬运及目标圆 | 2 | 4 | 6 |
| 合计 | 10 | 19 | 29 |

两次距离搬运仍按 Euclid I.2 风格完全展开。交点绑定为 0 E，但所有用于画线、
画圆的点都可追溯到两个已构造对象的确定性交点。

## 依赖主链

```mermaid
flowchart LR
  I[O, A, 单位圆] --> AX[横轴与纵轴]
  AX --> R2[eta_0,2 与 eta_1,2]
  R2 --> HS[半尺度 Carlyle 圆]
  HS --> R4[eta_0,4 与 eta_1,4]
  R4 --> Y[搬运 QH_1,4 得到 Y]
  Y --> RM[复用 OY 圆得到 M_0,4]
  RM --> R8[eta_0,8 = 2 cos 2pi/17]
  R8 --> TC[搬运单位长度并画目标圆]
  TC --> B[B_plus 与 B_minus]
```

完整的逐条目直接依赖、每个节点的成本和累计 E 值见
`dependency-graph.json`。该 DAG 由生成器从证书 program 确定性导出，并由测试
检查拓扑顺序、引用一致性、构造哈希和总分。

## 可复现文件

- `construction.json`：正式构造证书；
- `verification.json`：独立验证报告；
- `dependency-graph.json`：机器可读依赖 DAG；
- `source.yaml`：来源、工具假设和可比性台账；
- `sage/experiments/build_detemple_1991_improved.py`：确定性生成器。
