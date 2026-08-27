# 尺规作图最短步骤搜索项目设计文档

> 项目代号：**Euclid-Min**（暂定）  
> 项目类型：开源 IT / 数学计算 / 自动搜索 / 可验证几何  
> 首要目标：**寻找经典尺规作图问题的更短已知构造（shortest-known construction）**  
> 长期目标：在部分问题上进一步尝试证明真正的最小步数

---

## 1. 项目背景

尺规作图中的大量经典问题已经有数百年甚至两千多年的历史，例如：

- 正十七边形；
- 阿波罗尼乌斯三圆问题；
- Malfatti 三圆问题；
- Cramer–Castillon 问题；
- 各类三角形反构问题。

传统数学通常关注：

1. 一个目标是否尺规可作；
2. 如何给出一个优美、可理解的经典构造；
3. 构造背后的代数、射影、反演或圆几何结构。

但另一个非常自然的问题长期没有被系统解决：

> **在给定严格计步规则的前提下，一个尺规作图问题最少究竟需要多少步？**

这与魔方中的 HTM/QTM 和 God's Number 很相似。

对于很多经典尺规问题，人们知道很多构造，也知道某些构造比另一些更短，但：

- “目前已知最短”往往没有统一整理；
- “严格最短”通常更难；
- 即使问题本身极其经典，其最小尺规步数也可能未知。

本项目把这一问题视为一个工程化的搜索与验证问题，而不是首先视为一篇数学论文。

项目最终可以仅以 GitHub 开源项目形式存在；如果产生有价值的新结果，再考虑进一步整理为论文、技术报告或公开文章。

---

# 2. 项目核心思想

本项目把尺规作图形式化为一个可执行的状态空间搜索问题：

```text
初始几何对象
    ↓
合法尺规操作
    ↓
产生新的直线 / 圆
    ↓
自动产生新的交点
    ↓
形成新的几何状态
    ↓
判断是否达到目标
```

整个系统由两部分构成：

```text
                ┌──────────────────────┐
                │   Construction Search │
                │  搜索更短的构造方案   │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Exact Verifier       │
                │ 严格验证每一步是否合法 │
                └──────────┬───────────┘
                           │
                           ▼
                    可复现构造证书
```

搜索算法可以是启发式的、随机的、AI 驱动的。

但验证器必须是严格的。

---

# 3. 项目目标

## 3.1 第一阶段目标

第一阶段**不要求证明 global minimum**。

主要目标：

> **在明确、权威或可对照的 metric 下，找到比公开文献中更短的经典尺规作图。**

例如：

```text
Literature best:
    45 Lemoine simplicity

New construction:
    42 Lemoine simplicity

Verification:
    PASS
```

只要规则一致、构造合法、结果可重放，即使不能证明 42 是绝对最小，也已经得到一个新的 upper bound：

\[
OPT \le 42
\]

这已经具有实际价值。

---

## 3.2 第二阶段目标

建立一个通用的：

> **Straightedge-and-Compass Construction Verifier**

输入：

- 初始几何对象；
- 一系列尺规操作；
- 目标条件。

输出：

- 每一步是否合法；
- 所有中间对象；
- 最终目标是否严格满足；
- 构造步数；
- 各 metric 下的 score。

验证器必须尽可能独立于搜索器。

---

## 3.3 第三阶段目标

实现自动搜索器：

> **Automatic Short Construction Search**

可以：

- 枚举合法操作；
- 自动生成候选构造；
- 进行状态去重；
- 使用启发式剪枝；
- 使用随机搜索；
- 使用 beam search；
- 使用 A* / IDDFS / branch-and-bound；
- 使用 AI 对候选操作排序；
- 尝试刷新 shortest-known construction。

此阶段允许不完备搜索。

因此结果只能声明：

> **shortest found / shortest known**

不能声明：

> **global minimum**

---

## 3.4 长期目标

如果项目成熟，可以尝试：

> **Minimum-Step Proof**

即同时得到：

1. 一个长度为 \(N\) 的合法构造；
2. 一个严格证明，说明所有 \(N-1\) 步及以下构造均不可能。

从而得到：

\[
OPT = N
\]

这一目标难度非常高，不作为项目是否成功的判断标准。

---

# 4. 非目标

第一版明确不做以下事情：

- 不试图形式化全部古典欧氏几何；
- 不支持所有可能的尺规传统习惯；
- 不把自然语言题目直接自动转换成形式化问题；
- 不要求 AI 自己证明几何正确性；
- 不要求第一版证明最小步数；
- 不首先追求 GPU 加速；
- 不首先追求论文发表；
- 不把“搜索很多但没找到”当作“不存在”的证明。

尤其必须坚持：

> **没有完备覆盖，就不能声称 lower bound。**

AI 搜了十亿个方案但没找到，不等于证明不存在。

---

# 5. Metric 设计

项目应区分：

1. **内部搜索 metric**
2. **公开比较 metric**

内部 metric 可以更适合计算机。

公开比较必须尽量采用已有文献中的标准，否则新纪录缺乏可比性。

---

# 6. Metric A：E-move

建议把现代计算机搜索的基础 metric 设为 E-move。

基本思想：

```text
通过两个已有点画直线       = 1 E
以已有点为圆心画合法圆     = 1 E
交点                        = 0 E
```

高级宏操作必须展开成基础尺规操作，或者按照已有正式定义计算 E-score。

例如：

- 中点；
- 垂线；
- 垂直平分线；
- 平行线；
- 角平分线；
- 距离搬运；

不能天然视作 1 步。

E-move 的优点：

- 对搜索器非常自然；
- 适合构造 DAG；
- 不依赖尺子和圆规的“当前物理状态”；
- 易于做 canonicalization；
- 易于比较不同搜索策略；
- 已经出现在现代最短尺规构造复杂度研究中。

---

# 7. Metric B：Lemoine Geometrography

为了与历史文献比较，项目必须支持 Lemoine simplicity。

Lemoine 把实际尺规动作拆成：

```text
S1：让直尺边通过一个指定点
S2：沿直尺画一条直线

C1：把圆规的一只脚放到指定点
C2：把圆规的一只脚放到某条已知轨迹上的任意点
C3：画一个圆
```

simplicity：

\[
L = m_1 + m_2 + n_1 + n_2 + n_3
\]

其中：

```text
m1 = S1 次数
m2 = S2 次数
n1 = C1 次数
n2 = C2 次数
n3 = C3 次数
```

---

# 8. 为什么必须同时支持两种 metric

内部搜索最适合：

```text
E-move
```

历史比较最适合：

```text
Lemoine simplicity
```

最终一个构造应该报告：

```text
E-score:        13
Lemoine score:  42
Lines:           4
Circles:         9
```

如果出现：

```text
E-score 更低
Lemoine score 更高
```

也没有问题。

这说明它在两种不同优化目标下表现不同。

项目不应该把它们混成一个数字。

---

# 9. Metric Profile

不同历史文献可能存在不同初始条件、圆规模型和目标条件。

因此项目必须引入：

```text
Metric Profile
```

例如：

```yaml
profile: detemple-1991

metric:
  primary: lemoine

compass:
  mode: non-collapsing

initial_objects:
  - unit_circle
  - horizontal_diameter
  - vertical_diameter

target:
  type: adjacent_vertex_of_regular_polygon
  n: 17
```

而机器内部测试可以使用：

```yaml
profile: minimal-euclidean

metric:
  primary: e-move

compass:
  mode: collapsing

initial_objects:
  - center
  - one_point_on_circle
  - circle

target:
  type: adjacent_vertex_of_regular_polygon
  n: 17
```

---

# 10. 不同 Profile 的结果不能直接比较

例如：

```text
Profile A:
单位圆 + 两条垂直直径免费

Profile B:
只有圆心 + 圆上一点 + 单位圆
```

那么：

```text
A 的 13 步
```

不能直接宣布优于：

```text
B 的 14 步
```

因为初始信息不同。

所有公开纪录必须绑定 profile。

建议结果统一写成：

```text
Problem:
    Regular 17-gon

Profile:
    DeTemple-1991-compatible

Metric:
    Lemoine

Score:
    42

Status:
    Verified construction
    Global optimality NOT claimed
```

---

# 11. 圆规模型

必须明确支持至少两类。

## 11.1 Collapsing Compass

圆规离开纸面后半径不能保留。

基础圆：

```text
Circle(A, B)
```

表示：

> 以已有点 A 为圆心，以 AB 为半径画圆。

---

## 11.2 Non-Collapsing Compass

允许把已有距离：

\[
|AB|
\]

搬到另一个圆心 \(C\)。

例如：

```text
Circle(center=C, radius=AB)
```

可能作为直接操作。

历史文献中可能采用这一模型。

因此 verifier 和 metric calculator 必须区分两者。

---

# 12. 任意点问题

经典尺规作图常出现：

> 在线上任取一点 P。

这会让搜索空间从有限分支变成连续无限分支。

第一版建议：

```text
arbitrary_points = false
```

即禁止自由点。

所有新点必须来自：

- line-line intersection；
- line-circle intersection；
- circle-circle intersection。

如果未来支持任意点，必须单独作为 profile。

---

# 13. 几何对象模型

核心类型：

```text
Point
Line
Circle
```

---

## 13.1 Point

逻辑表示：

```text
Point {
    id
    exact_x
    exact_y
    provenance
}
```

坐标必须支持 exact representation。

禁止使用 `float64` 作为最终真实性判断依据。

---

## 13.2 Line

推荐标准形式：

\[
ax + by + c = 0
\]

必须 canonicalize，例如：

- 统一符号；
- 约分；
- 归一化代数表达式。

---

## 13.3 Circle

标准形式：

\[
(x-a)^2 + (y-b)^2 = r^2
\]

或者一般形式：

\[
x^2+y^2+Dx+Ey+F=0
\]

根据 exact algebra 实现选择。

---

# 14. Exact Algebra

这是项目最关键的基础设施之一。

尺规构造产生的坐标属于通过有限次二次扩张得到的代数数。

不能使用：

```python
abs(x - y) < 1e-12
```

判断两个点是否相同。

必须能够严格判断：

\[
x = y
\]

以及：

\[
x < y
\]

必要时还要判断：

- 点是否在线上；
- 点是否在圆上；
- 两圆是否相切；
- 两对象是否相同；
- 两点是否重合。

---

# 15. SageMath 的角色

第一版建议使用现有 SageMath + Python 环境作为：

> **Reference Mathematical Kernel**

SageMath 负责：

- Algebraic Real Field；
- Number Field；
- polynomial；
- minimal polynomial；
- exact square root；
- symbolic verification；
- 高精度辅助调试。

第一阶段不追求 Sage 的速度。

目标是：

> **先把数学做对。**

---

# 16. Go 的角色

Go 作为正式 solver 的主要候选语言。

适合：

- 搜索状态管理；
- hash；
- canonical state；
- 并发；
- checkpoint；
- 长时间任务；
- CLI；
- benchmark；
- 单二进制发布。

推荐路线：

```text
Sage/Python reference
        ↓
Go production solver
```

---

# 17. Differential Testing

正式 Go kernel 实现后，必须与 Sage reference 做随机对照。

流程：

```text
随机生成合法 construction
        │
        ├──────────────┐
        ▼              ▼
      Sage            Go
        │              │
        └───────┬──────┘
                ▼
          exact result compare
```

任何不一致都视为 bug。

---

# 18. Construction Language

项目需要一个非常简单、可读、可版本化的 DSL。

例如：

```text
circle c1 A B
circle c2 B A

point P = intersect(c1, c2, 0)
point Q = intersect(c1, c2, 1)

line l1 P Q
```

或者 JSON/YAML 版本。

要求：

- 人可以读；
- 程序可以重放；
- Git diff 友好；
- 不依赖 GUI；
- 易于第三方 verifier 实现。

---

# 19. Construction Certificate

每一个正式结果必须生成：

```text
construction certificate
```

包括：

- Problem ID；
- Metric profile；
- 初始对象；
- 每一步操作；
- 新产生的交点；
- 最终目标对象；
- E-score；
- Lemoine score；
- exact verification result；
- solver version；
- verifier version；
- hash。

例如：

```yaml
problem: regular-17-gon
profile: detemple-1991
solver_version: 0.4.2
verifier_version: 0.3.8

score:
  e_move: 13
  lemoine: 42

verified: true
optimality_claimed: false
```

---

# 20. 搜索状态

一个状态包含：

```text
Points
Lines
Circles
Construction DAG
Score
```

理论表示：

\[
S=(P,L,C)
\]

其中：

```text
P = 当前所有可用点
L = 当前所有直线
C = 当前所有圆
```

---

# 21. Candidate Generation

对于已有点集：

```text
P = {P1, P2, ... Pn}
```

基础候选：

```text
Line(Pi, Pj)
Circle(Pi, Pj)
```

如果 profile 支持 non-collapsing compass：

```text
Circle(center=Pi, radius=PjPk)
```

也可以进入候选集。

---

# 22. 自动交点闭包

新建一个 line/circle 后：

```text
new_object
    ↓
与所有已有对象求交
    ↓
产生 0 / 1 / 2 个新点
    ↓
canonicalize
    ↓
加入 Point Set
```

交点本身默认不计 E-move。

Lemoine 是否计入额外操作由具体 profile 决定。

---

# 23. Canonicalization

必须严格消除：

- 重复点；
- 重复直线；
- 重复圆；
- 等价状态；
- 不同操作顺序产生的相同状态。

例如：

```text
先画 AB
再画 CD
```

与：

```text
先画 CD
再画 AB
```

如果最终得到完全相同的几何闭包，应尽可能 canonicalize 为同一状态。

这是控制状态爆炸的核心技术。

---

# 24. 搜索算法

第一阶段目标是找短解，不要求完备性。

可以大胆使用：

- DFS；
- IDDFS；
- beam search；
- best-first search；
- A*；
- random restart；
- Monte Carlo；
- MCTS；
- genetic search；
- simulated annealing；
- heuristic scoring；
- AI ranking。

任何能找到合法短解的方法都可以使用。

---

# 25. AI 的角色

AI 不应该负责：

```text
最终几何正确性
```

AI 应该负责：

```text
候选操作排序
```

模型输入：

```text
current state
goal
candidate operation
```

输出：

```text
probability / heuristic score
```

例如：

```text
Line(O1,O2)        0.92
Circle(A,B)        0.88
Line(P3,P8)        0.41
Circle(P7,P9)      0.01
```

搜索器优先探索高分操作。

---

# 26. AI 不能做的剪枝

如果最终想证明 global minimum，则不能因为：

```text
AI score 很低
```

就永久删除该分支。

AI 可以改变搜索顺序。

AI 不能在没有数学证明的情况下决定：

```text
这个分支永远不需要搜索
```

否则搜索结果只能用于 upper bound。

---

# 27. GPU 的角色

第一版不依赖 GPU。

核心 exhaustive / exact geometry 更可能受限于：

- CPU；
- RAM；
- hash；
- canonicalization；
- exact algebra；
- memory bandwidth。

GPU 更适合：

```text
heuristic model
```

未来可以使用 4060 Ti：

- PyTorch；
- policy model；
- value model；
- batch candidate scoring。

---

# 28. Proof Mode

未来如果尝试 lower bound，必须单独进入：

```text
proof mode
```

Proof Mode 的原则：

> **所有未搜索分支的删除都必须有可证明的安全依据。**

允许：

- 严格状态等价；
- 对称群 reduction；
- mathematically proven dominance；
- 可证明无效操作；
- SAT/SMT 等价编码；
- 可验证 UNSAT certificate。

不允许：

- AI 猜测；
- 概率剪枝；
- beam width；
- random sampling；
- 经验性 pruning。

---

# 29. “证明最小”的正式结构

如果找到一个 \(N\) 步构造：

\[
OPT \le N
\]

若还能完备证明：

\[
\text{不存在长度}<N\text{ 的构造}
\]

则：

\[
OPT \ge N
\]

最终：

\[
OPT = N
\]

这一功能属于长期研究目标。

---

# 30. Benchmark 分级

建议把问题分为四档。

## Tier 0：Kernel Test

只用于验证系统正确性。

例如：

- 两圆交点；
- 中点；
- 垂线；
- 垂直平分线；
- 角平分线。

---

## Tier 1：基础经典题

例如：

- 正三角形；
- 正方形；
- 正五边形；
- 黄金分割；
- 三角形外心；
- 三角形内心。

主要用于：

- verifier；
- exact algebra；
- state search；
- regression test。

---

## Tier 2：中级 benchmark

例如：

- 三中线反构三角形；
- 三高反构三角形；
- mixtilinear incircle；
- 较复杂三角形 reconstruction。

---

## Tier 3：Boss Problems

重点项目目标：

### Regular 17-gon

高斯经典问题。

### Apollonius CCC

三个互不相交、不包含的圆，指定：

> 求一个包含三个输入圆、并分别与三个输入圆内切的大圆。

### Malfatti Circles

给定三角形，构造三个彼此相切且分别与两边相切的圆。

### Cramer–Castillon

给定圆和三个点，在圆上构造三角形，使三边分别经过给定点。

---

# 31. 第一主攻目标：正十七边形

建议第一个真正挑战的问题是：

```text
Regular 17-gon
```

原因：

- 极其经典；
- 数学背景成熟；
- 输入简单；
- 可作性明确；
- 文献多；
- 可以获得历史 baseline；
- 很适合公开传播；
- 搜索状态比 Apollonius 更干净。

---

# 32. 正十七边形目标定义

建议同时保留两个 profile。

## Profile A：Historical

尽可能严格复现某篇历史构造文献的初始条件和 metric。

用于：

> 刷新历史纪录。

---

## Profile B：Minimal Formal

例如：

```text
Given:
    center O
    point A
    circle C(O,A)

Goal:
    construct B on C
    such that angle AOB = 2π/17
```

目标只要求得到相邻顶点。

不要求：

- 画出 17 条边；
- 重复沿圆周复制边长。

这样更能体现核心数学复杂度。

---

# 33. 第二主攻目标：Apollonius CCC

输入：

```text
Circle C1
Circle C2
Circle C3
```

约束：

```text
三个圆互不相交
互不包含
一般位置
```

目标：

```text
construct Circle X
```

满足：

```text
X contains C1, C2, C3
X internally tangent to C1
X internally tangent to C2
X internally tangent to C3
```

这是 Apollonius 八解中的固定一个 branch。

---

# 34. 文献 Baseline 数据库

项目必须建立：

```text
benchmarks/
```

每个问题记录：

- 文献；
- 作者；
- 年代；
- 初始条件；
- compass model；
- metric；
- reported score；
- 构造步骤；
- 是否已经自行复核；
- 是否存在更短文献。

例如：

```yaml
problem: regular-17-gon

baseline:
  author: DeTemple
  year: 1991
  metric: Lemoine
  score: 45
  verified_by_project: false
```

在正式宣称“刷新纪录”前：

> baseline 必须由项目自己重新计算一遍。

不能只引用论文中的数字。

---

# 35. Literature Claim 等级

建议对公开结论分等级。

## Level 0

```text
Found construction
```

只是找到一个合法构造。

---

## Level 1

```text
Shorter than selected baseline
```

比某一篇明确文献短。

---

## Level 2

```text
Shortest known in reviewed literature
```

完成较充分文献检索后，可以谨慎使用。

---

## Level 3

```text
Globally minimal
```

只有在存在严格 lower-bound proof 时才能使用。

---

# 36. README 中禁止的表述

没有证明时不要写：

```text
minimum construction
optimal construction
God's Number = N
```

应该写：

```text
shortest construction found by this project
shortest known construction in reviewed literature
new upper bound
```

---

# 37. GitHub 项目定位

推荐 README 一句话：

> **Search for shorter straightedge-and-compass constructions of classical geometric problems, with exact machine verification.**

中文：

> **使用精确几何验证和自动搜索，寻找经典尺规作图问题的更短构造。**

项目重点不是“AI 会画图”。

而是：

```text
formal rules
+
exact verifier
+
automatic search
+
reproducible certificates
```

---

# 38. 仓库结构建议

```text
euclid-min/
│
├── README.md
├── LICENSE
├── docs/
│   ├── DESIGN.md
│   ├── METRICS.md
│   ├── FORMAL_MODEL.md
│   └── PROOF_MODE.md
│
├── problems/
│   ├── regular-17/
│   ├── apollonius-ccc/
│   ├── malfatti/
│   └── cramer-castillon/
│
├── baselines/
│   ├── detemple-1991/
│   └── ...
│
├── certificates/
│   ├── regular-17/
│   └── ...
│
├── sage/
│   ├── notebooks/
│   └── reference/
│
├── python/
│   ├── experiments/
│   └── ai/
│
├── go/
│   ├── cmd/
│   ├── geometry/
│   ├── algebra/
│   ├── verifier/
│   ├── search/
│   └── metrics/
│
└── tests/
```

---

# 39. CLI 设想

例如：

```bash
euclid-min verify \
  --problem regular-17 \
  --profile detemple-1991 \
  construction.yaml
```

输出：

```text
Construction valid: YES

Objects:
    Lines:    4
    Circles:  9

Scores:
    E-move:          13
    Lemoine:         42

Target:
    VERIFIED

Optimality:
    NOT CLAIMED
```

搜索：

```bash
euclid-min search \
  --problem regular-17 \
  --profile e-move-minimal \
  --max-score 14
```

---

# 40. Web Visualizer

后续可以提供一个静态 Web Viewer。

功能：

- 逐步播放构造；
- 显示当前点/线/圆；
- 显示步骤编号；
- 显示 metric；
- 显示依赖关系；
- 导出 SVG；
- 生成分享链接。

这对于公众验证非常有帮助。

---

# 41. 可复现原则

所有正式纪录必须做到：

```text
clone repo
    ↓
run verifier
    ↓
得到完全相同 score
    ↓
得到完全相同 final geometry
```

不能只发布一张几何图。

---

# 42. 第三方验证

如果项目真的找到重要新构造，优先采用公开验证，而不是只依赖作者自己的程序。

建议提供：

1. construction certificate；
2. 几何图；
3. 动画；
4. 完整 metric 计算；
5. 独立 verifier；
6. Sage notebook；
7. 人类可阅读步骤；
8. 文献 baseline 对照。

然后邀请社区验证。

---

# 43. 社区验证对象

可以邀请：

- 数学专业网友；
- 几何爱好者；
- Math StackExchange 用户；
- GitHub contributors；
- Bilibili 数学科普作者；
- 数学教师；
- 自动定理证明研究者。

如果未来真的出现非常漂亮的新纪录，也可以尝试联系：

- 李永乐老师；
- 妈咪说；
- 钰子一；
- 漫士沉思录；

以及其他数学科普创作者。

目的不是把他们当作“权威认证机构”，而是：

> **让更多懂数学的人公开复核构造、发现漏洞、传播结果。**

---

# 44. 多重验证策略

一个重要结果最好通过三条独立路径验证：

```text
Go Verifier
    +
SageMath Reference
    +
Human-readable proof
```

如果三者一致，可信度会明显提高。

未来还可以让社区编写：

```text
third-party verifier
```

---

# 45. 安全性与可信度

项目最危险的 bug：

> 两个本来不同的代数点因为近似误差被认为相同。

因此：

```text
float64
```

只能用于：

- UI；
- 绘图；
- heuristic；
- 预览。

不能用于：

- 最终相等判断；
- 构造合法性；
- target verification；
- proof mode。

---

# 46. 性能风险

可能的主要瓶颈：

1. 状态数爆炸；
2. 交点数量爆炸；
3. exact algebra 太慢；
4. hash key 太大；
5. canonicalization 成本过高；
6. 内存耗尽；
7. 大量等价状态；
8. AI heuristic 不够有效。

---

# 47. 优化顺序

不要过早优化。

推荐：

```text
正确性
  ↓
可验证性
  ↓
baseline 重现
  ↓
小规模搜索
  ↓
profiling
  ↓
性能优化
  ↓
AI
  ↓
GPU
```

---

# 48. 第一阶段技术路线

## Phase 0：项目定义

完成：

- metric specification；
- compass model；
- arbitrary point policy；
- problem format；
- target format。

---

## Phase 1：Sage Reference Verifier

实现：

- Point；
- Line；
- Circle；
- exact intersection；
- equality；
- construction replay；
- target verification。

完成后，可以手工输入一个经典构造并严格验证。

---

## Phase 2：Metric Engine

实现：

- E-score；
- Lemoine score；
- metric profile；
- historical compatibility。

目标：

> 自动重新计算文献构造的 score。

---

## Phase 3：Go Verifier

将核心 verifier 移植到 Go。

要求：

- 与 Sage differential test；
- CLI 可用；
- construction certificate 可用。

---

## Phase 4：Basic Search

实现：

- candidate generation；
- BFS / IDDFS；
- state hash；
- canonicalization；
- small benchmark。

先从非常小的问题开始。

---

## Phase 5：Heuristic Search

实现：

- best-first；
- beam；
- random restart；
- hand-written heuristic；
- symmetry heuristic。

目标：

> 在中型问题上找到较短构造。

---

## Phase 6：AI Search

使用：

- Python；
- PyTorch；
- 4060 Ti。

训练或运行：

```text
policy heuristic
```

只负责候选排序。

---

## Phase 7：Boss Problem

首先挑战：

```text
regular-17
```

目标不是证明最小。

目标：

> **打破至少一个可靠文献 baseline。**

---

# 49. 项目成功标准

项目不应该只有“解决开放问题”才算成功。

分级如下。

## Success A

成功实现可靠的：

```text
exact straightedge-and-compass verifier
```

项目成立。

---

## Success B

能自动重新发现一些经典构造。

项目已经很有趣。

---

## Success C

找到比部分传统构造更短的方案。

项目有实际研究价值。

---

## Success D

刷新某个经典问题的公开 shortest-known upper bound。

这是明确的新结果。

---

## Success E

证明某个非平凡经典问题的 global minimum。

这是长期最高目标。

---

# 50. 最重要的工程原则

## 原则 1

> **先保证 verifier 正确，再追求 solver 聪明。**

---

## 原则 2

> **AI 可以找答案，但不能决定答案是否正确。**

---

## 原则 3

> **没有完备搜索，就不能声称 lower bound。**

---

## 原则 4

> **没有统一 profile，就不能比较步数。**

---

## 原则 5

> **任何纪录都必须可重放、可验证、可复现。**

---

## 原则 6

> **对外尽量使用已有文献 metric，而不是只使用项目自定义 metric。**

---

# 51. 当前最现实的项目定位

本项目第一阶段最合适的目标不是：

> “解决尺规作图最小步数问题。”

而是：

> **建立一套可靠的计算机尺规构造描述、验证与搜索框架，并尝试刷新经典问题的 shortest-known construction。**

这已经足够困难，也足够有价值。

---

# 52. 推荐第一个正式 Benchmark

建议：

```text
Regular 17-gon
```

第一步不是搜索。

而是：

1. 收集重要历史构造；
2. 精确确认各自初始条件；
3. 精确确认 metric；
4. 将构造录入 verifier；
5. 自动重算 score；
6. 建立可信 baseline。

只有 baseline 可信以后，才开始搜索。

---

# 53. 关于论文

项目不以论文为首要目标。

优先：

```text
GitHub
+
source code
+
certificates
+
benchmarks
+
visualizer
+
public verification
```

如果未来出现：

- 新的经典问题最短已知构造；
- 新的通用搜索算法；
- 新的 canonicalization 方法；
- 新的严格 lower bound；
- global minimum proof；

再根据成果决定是否写论文。

---

# 54. 最终愿景

理想状态下，项目可以形成一个公开数据库：

```text
Classical Construction Database
```

每个问题展示：

```text
Problem
Known constructions
Metric profiles
Historical best
Project best
Verified certificates
Optimality status
```

例如：

```text
Regular 17-gon

Historical:
    DeTemple 1991
    Lemoine: 45

Project:
    Candidate A
    E-score: 13
    Lemoine: 42
    Verified: YES

Optimality:
    UNKNOWN
```

这样即使永远无法解决 global minimum，这个项目本身仍然可以长期积累成果。

---

# 55. 一句话总结

> **Euclid-Min 是一个面向经典尺规作图问题的开源自动搜索与精确验证项目：内部使用机器友好的形式模型寻找更短构造，对外使用已有权威 metric 与历史文献公平比较；第一阶段追求新的 shortest-known construction，而不是强求 global optimality proof。**

---

# 参考资料起点

后续正式建仓后，应单独整理 `docs/LITERATURE.md`，至少从以下资料开始：

1. Émile Lemoine — Geometrography / Géométrographie
2. Duane W. DeTemple (1991) — *Carlyle Circles and Lemoine Simplicity of Polygon Constructions*
3. François Labelle — *On the Complexity of Straightedge and Compass Constructions*
4. Erik D. Demaine, Yaqiao Luo (2025) — *Computational Complexity of Optimizing Compass and Straightedge Constructions*
5. Malfatti circles 的自动化构造改进工作
6. Cramer–Castillon 与自动尺规构造相关文献
7. Euclidea solver / automatic construction search 项目

正式宣称任何 “best known” 前，必须重新进行系统文献检索。
