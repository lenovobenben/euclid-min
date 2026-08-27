# Euclid-Min：正十七边形最短尺规构造研究设计

> 项目代号：**Euclid-Min**
>
> 项目类型：计算数学 / 自动搜索 / 精确几何验证
>
> 唯一研究对象：**正十七边形的相邻顶点构造**
>
> 第一目标：在严格固定的规则下，寻找并验证更短的已知构造
>
> 长期目标：在可行的受限模型中研究严格的最小步数

---

## 1. 项目定位

Euclid-Min 不是通用动态几何软件，也不是面向大量经典题目的题库。

当前版本只研究一个问题：

> 给定单位圆、圆心和圆上一个起始点，仅使用无刻度直尺与可折叠圆规，构造正十七边形在该起始点旁边的一个相邻顶点，最少需要多少次基础作图操作？

项目把这个问题形式化为：

```text
固定初始几何对象
        ↓
合法的画线 / 画圆操作
        ↓
自动获得新的交点
        ↓
形成新的精确几何状态
        ↓
判断目标顶点是否出现
```

系统分为两个必须解耦的部分：

```text
┌────────────────────────┐
│ Construction Search    │
│ 搜索更短的候选构造       │
└────────────┬───────────┘
             │ certificate
             ▼
┌────────────────────────┐
│ Exact Verifier         │
│ 独立重放并严格验证       │
└────────────┬───────────┘
             ▼
      可复现的构造与分数
```

搜索器可以使用启发式、随机化或 AI；验证器必须使用精确数学判断。

---

## 2. 唯一研究问题

### 2.1 固定实例

第一版只研究固定、归一化的单位圆实例：

\[
O=(0,0),\qquad A=(1,0),\qquad
\Gamma:x^2+y^2=1.
\]

初始可见对象为：

- 点 \(O\)；
- 点 \(A\)；
- 圆 \(\Gamma\)，圆心为 \(O\)，经过 \(A\)。

这些初始对象免费提供，不计入构造分数。

### 2.2 目标

目标是构造以下两个点中的任意一个：

\[
B_+=\left(\cos\frac{2\pi}{17},\sin\frac{2\pi}{17}\right),
\]

或

\[
B_-=\left(\cos\frac{2\pi}{17},-\sin\frac{2\pi}{17}\right).
\]

它们分别是从 \(A\) 沿单位圆两个方向得到的相邻顶点。

验证器可以使用这两个精确代数点判断目标是否达到，但搜索器不得把目标坐标当成可直接使用的已知点。

### 2.3 不要求构造完整多边形

当前目标不要求：

- 画出全部 17 个顶点；
- 画出 17 条边；
- 沿圆周重复搬运边长；
- 输出完整正十七边形图形。

只要状态中精确出现 \(B_+\) 或 \(B_-\)，即认为达到目标。

### 2.4 为什么采用固定实例

固定实例可以把第一阶段限制在具体实代数数上，避免同时处理一般参数族、自由点连续变化和符号恒等证明。

这并不降低问题的数学价值。正十七边形仍然涉及非平凡的二次扩张塔、复杂的构造依赖关系和巨大的组合搜索空间。

---

## 3. 当前范围

### 3.1 项目要做的事情

当前项目只做：

1. 形式化正十七边形相邻顶点问题；
2. 实现固定实例的精确构造验证器；
3. 建立正十七边形历史构造 baseline；
4. 自动重新计算构造分数；
5. 搜索比已复核 baseline 更短的构造；
6. 输出第三方可以重放的构造证书；
7. 在条件成熟时研究受限模型下的最小性证明。

### 3.2 当前明确不做的事情

当前版本不做：

- Apollonius 三圆问题；
- Malfatti 三圆问题；
- Cramer–Castillon 问题；
- 三角形反构问题；
- 其他正多边形的最短构造研究；
- 通用尺规作图题库；
- 自然语言题目自动形式化；
- 一般参数族的符号验证；
- 任意点或半自由点；
- non-collapsing compass 搜索；
- 第一版中的 GPU 或 AI 模型；
- 未经完备证明的 global minimum 声明。

简单的中点、垂线、正三角形等构造可以作为内核测试，但它们不是项目研究对象，也不建立公开纪录。

### 3.3 延后不等于预先设计

被排除的问题不要求当前架构提前兼容。

特别是，不为三圆问题提前引入：

- 通用输入参数；
- 参数化代数函数；
- 输入连续变化下的分支跟踪；
- 通用切触目标语言；
- 八类内切/外切分支。

只有正十七边形研究闭环完成后，才重新评估是否扩展项目范围。

---

## 4. 正式 Profile

第一版唯一具有规范意义的 profile 暂定为：

```yaml
id: regular-17-e-fixed-v1

problem:
  type: regular_polygon_adjacent_vertex
  n: 17
  semantics: fixed_instance

initial_objects:
  points:
    O: [0, 0]
    A: [1, 0]
  circles:
    unit_circle:
      center: O
      through: A

tools:
  straightedge: true
  collapsing_compass: true
  non_collapsing_compass: false

points:
  intersections_only: true
  arbitrary_points: false
  half_generic_points: false

metric:
  primary: e_move

target:
  type: either_adjacent_vertex
  start: A
  center: O
  circle: unit_circle
  n: 17
```

任何正式结果都必须绑定 profile ID 和 profile 内容哈希。

修改以下任一内容，都必须产生新的 profile：

- 初始对象；
- 可见对象；
- 工具集合；
- 圆规模型；
- 自由点规则；
- 交点规则；
- 目标条件；
- 计步规则。

不同 profile 的分数不能直接比较。

---

## 5. 基础操作模型

### 5.1 直尺操作

```text
Line(P, Q)
```

前置条件：

- \(P\) 和 \(Q\) 都是当前状态中的已有点；
- \(P\ne Q\)。

结果是唯一经过 \(P,Q\) 的直线。

成本：

```text
1 E-move
```

### 5.2 可折叠圆规操作

```text
Circle(center=P, through=Q)
```

前置条件：

- \(P\) 和 \(Q\) 都是当前状态中的已有点；
- \(P\ne Q\)。

结果是以 \(P\) 为圆心、以 \(|PQ|\) 为半径的圆。

成本：

```text
1 E-move
```

### 5.3 不支持直接搬运距离

第一版不允许一步执行：

```text
Circle(center=C, radius=AB)
```

除非 \(C\) 本身就是 \(A,B\) 中的一个端点，并用另一个端点作为圆上的已知点。

也就是说，第一版没有 non-collapsing compass 工具。需要搬运距离时，必须展开成基础直尺和可折叠圆规操作。

### 5.4 重复对象

再次画出已经存在的直线或圆，在语义上可以被识别，但不会产生新状态。

搜索器可以把这种操作作为显然受支配的候选排除。验证器如果读到这种操作，应当：

- 仍然计算其成本；
- 标记结果对象与已有对象相同；
- 不产生新的交点。

---

## 6. 点与交点语义

### 6.1 只允许确定点

除了初始点 \(O,A\)，所有新点都必须来自：

- line-line intersection；
- line-circle intersection；
- circle-circle intersection。

第一版禁止：

- 平面上任取一点；
- 直线上任取一点；
- 圆上任取一点。

因此在给定步数上界时，候选操作集合保持有限。

### 6.2 自动交点闭包

每画出一个新对象后，系统把它与所有已有直线和圆求交：

```text
new object
    ↓
intersect with existing objects
    ↓
obtain 0 / 1 / 2 finite real points
    ↓
exact canonicalization
    ↓
add new points to state
```

交点定义不计 E-move。

### 6.3 退化情况

验证器必须精确区分：

- 无实交点；
- 一个相切交点；
- 两个不同实交点；
- 平行直线；
- 重合直线；
- 重合圆；
- 半径为零的非法圆。

欧氏平面中的无穷远点不加入状态。

### 6.4 稳定的交点标识

证书不能依赖数值求根器返回的 `intersection 0` 或 `intersection 1`。

固定实例中，两个交点按精确字典序命名：

1. 先比较精确 \(x\) 坐标；
2. 若 \(x\) 相等，再比较精确 \(y\) 坐标。

可使用：

```text
lower / upper
left / right
first_lexicographic / second_lexicographic
```

作为人类可读别名，但验证器最终以精确坐标序关系决定身份。

---

## 7. E-move Metric

第一阶段只优化 E-move：

```text
画一条合法直线 = 1 E
画一个合法基础圆 = 1 E
定义交点         = 0 E
```

构造总分为：

\[
E = \#\text{Lines Drawn} + \#\text{Circles Drawn}.
\]

高级宏操作不能天然视为一步。例如：

- 中点；
- 垂直平分线；
- 垂线；
- 平行线；
- 角平分线；
- 距离搬运。

如果 DSL 或 UI 将来提供这些宏，它们必须展开为基础操作后再计算 E-score。

### 7.1 Lemoine simplicity 的位置

Lemoine simplicity 只用于未来的历史 profile，不是 `regular-17-e-fixed-v1` 的实现前置条件。

在正式支持前，必须从原始资料确认：

- 基本动作的严格定义；
- 初始对象如何计数；
- 圆规和直尺的动作约定；
- DeTemple 构造的实际初始条件；
- 论文报告分数能否被项目独立重算。

在完成上述工作前，文档和 README 不写未经复核的具体 Lemoine baseline 数字。

---

## 8. 数学声明等级

每个结果必须明确标记其声明等级。

### Level 0：Verified Construction

找到并精确验证了一个合法构造。

可声明：

```text
A verified N-move construction.
```

### Level 1：Shorter Than a Verified Baseline

项目已经在相同 profile 下重放某个文献或公开构造，并找到严格更短的构造。

可声明：

```text
Shorter than baseline X under profile Y.
```

### Level 2：Shortest Known in Reviewed Literature

完成充分、可公开检查的文献检索后，可以谨慎声明：

```text
Shortest known in the reviewed literature under profile Y.
```

必须同时公开检索范围和截止日期。

### Level 3：Globally Minimal

只有同时具有：

1. 一个长度为 \(N\) 的合法构造；
2. 一个严格、可验证的证明，排除全部长度小于 \(N\) 的构造；

才能声明：

\[
OPT=N.
\]

### 8.1 禁止的表述

没有 lower-bound proof 时，禁止使用：

```text
minimum construction
optimal construction
God's Number = N
```

应使用：

```text
shortest construction found by Euclid-Min
shortest known in the reviewed literature
new verified upper bound
```

---

## 9. Exact Algebra

### 9.1 基本要求

尺规构造产生的坐标属于有限次二次扩张得到的实代数数。

最终验证禁止使用：

```python
abs(x - y) < epsilon
```

来决定：

- 两个点是否相同；
- 点是否在线上；
- 点是否在圆上；
- 两条直线是否相同；
- 两个圆是否相同；
- 目标点是否已经构造出来。

### 9.2 必须支持的精确判断

数学内核至少需要：

- 实代数数四则运算；
- 精确平方根；
- 相等判断；
- 符号和序关系判断；
- line-line 精确求交；
- line-circle 精确求交；
- circle-circle 精确求交；
- 重根和相切判断；
- 目标代数点比较。

### 9.3 表示策略

概念上，一个实代数数需要能够由以下信息唯一确定：

- 定义表达式或多项式；
- 选择的实根；
- 必要的隔离区间或符号信息。

表达式 DAG 可以用于保存构造来源和减少重复计算，但不能仅依靠字符串形式判断两个代数数是否相等。

### 9.4 SageMath 的角色

第一版使用 SageMath 作为 reference mathematical kernel，负责：

- Algebraic Real Field；
- 精确交点；
- 相等和序关系；
- 目标点构造；
- 构造重放；
- 回归测试中的权威结果。

首要目标是正确性，不是速度。

### 9.5 Go 的角色

Go 可以在搜索规模需要时负责：

- 搜索队列；
- 状态索引；
- 并发；
- checkpoint；
- CLI；
- 性能 profiling。

第一版不要求立即在 Go 中重新实现完整实代数数内核。

如果以后实现 Go exact kernel，必须与 SageMath 做 differential testing。任何不一致都视为 bug。

---

## 10. 几何对象模型

### 10.1 Point

```text
Point {
    id
    exact_x
    exact_y
    provenance
}
```

点的数学身份由精确坐标决定，`id` 只用于证书引用。

### 10.2 Line

数学形式：

\[
ax+by+c=0.
\]

实现必须处理系数整体缩放造成的等价性。

两个 line 表达式是否相同必须通过精确比例关系或规范化表示判断，不能通过浮点归一化判断。

### 10.3 Circle

推荐形式：

\[
(x-u)^2+(y-v)^2=r^2,
\]

内部保存：

```text
center = (u, v)
radius_squared = r2
```

使用 \(r^2\) 可以减少不必要的平方根。

### 10.4 Provenance

每个非初始对象记录：

- 产生它的操作；
- 直接依赖对象；
- 所属步骤；
- 精确交点选择信息。

provenance 用于生成证书，不替代对象的数学相等判断。

---

## 11. Construction Language

项目需要一个简单、确定、可版本化的构造 DSL。

概念示例：

```text
circle c1 center=A through=O
point P = intersection(c1, unit_circle, upper)
line l1 through=A,P
```

正式格式优先采用 YAML 或 JSON；人类可读文本 DSL 可以后续生成。

要求：

- 人可以阅读；
- 程序可以无歧义重放；
- Git diff 友好；
- 不依赖 GUI；
- 不依赖浮点坐标；
- 所有对象引用都指向更早出现的对象；
- profile 与证书格式都有版本号。

---

## 12. Construction Certificate

每个正式结果必须生成构造证书，包括：

- schema version；
- problem ID；
- profile ID；
- profile 内容哈希；
- 初始对象；
- 每一步基础操作；
- 新产生的精确交点引用；
- 最终目标点；
- E-score；
- solver version；
- verifier version；
- 构造内容哈希；
- exact verification result；
- optimality claim 等级。

示例：

```yaml
schema: euclid-min-certificate/v1
problem: regular-17-adjacent-vertex
profile: regular-17-e-fixed-v1

score:
  e_move: 13

result:
  verified: true
  target: B_plus
  claim: verified_construction
  global_optimality: not_claimed

software:
  solver: 0.1.0
  verifier: 0.1.0
```

这里的数字仅为格式示例，不表示项目已经得到 13 步构造。

证书哈希用于检测文件变化，不作为数学正确性的证明；第三方 verifier 必须重新计算所有几何对象。

---

## 13. 搜索状态

搜索状态的数学部分为：

\[
S=(P,L,C),
\]

其中：

- \(P\)：当前所有不同的精确点；
- \(L\)：当前所有不同的直线；
- \(C\)：当前所有不同的圆。

工程状态还包括：

- 当前 E-score；
- 最佳前驱；
- 构造 DAG；
- canonical key；
- 搜索元数据。

在当前操作模型下，后续合法候选只依赖 \((P,L,C)\)，而不依赖产生对象的历史顺序。因此：

- 几何集合用于判断状态等价；
- 最佳前驱和构造 DAG 用于恢复最低成本证书；
- 相同几何状态只保留成本不劣的标签。

---

## 14. Candidate Generation

对当前点集：

\[
P=\{P_1,P_2,\dots,P_n\},
\]

生成：

```text
Line(Pi, Pj),                  i < j
Circle(center=Pi, through=Pj), i != j
```

排除：

- 输入点重合；
- 与已有对象精确相同的候选；
- profile 不允许的工具；
- 无法满足操作前置条件的候选。

注意：

> 一个新对象当前没有产生新交点，不代表它以后没有用。

因此，“没有立即产生新点”只能作为启发式模式中的排序信号，不能在 proof mode 中作为永久删除分支的理由。

---

## 15. Canonicalization

Canonicalization 是控制状态爆炸的核心。

### 15.1 对象级去重

严格消除：

- 坐标相同的点；
- 方程等价的直线；
- 圆心和半径平方相同的圆。

### 15.2 操作顺序去重

如果两条不同操作序列最终得到完全相同的 \((P,L,C)\)，则它们属于同一个搜索状态。

搜索器保留其中最低成本的前驱；成本相同的多条路径可以只保留一个确定性代表。

### 15.3 初始对称性

固定初始配置关于直线 \(OA\) 反射对称。

项目可以研究把互为镜像的状态合并，但必须：

- 精确定义反射作用；
- 证明它保持初始对象、操作合法性、目标集合和 E-score；
- 在 proof mode 中输出或实现可审计的等价规则。

未经证明的“看起来对称”不能用于完备剪枝。

### 15.4 Hash 不是相等证明

hash 只用于快速索引。

发生 hash 命中后，必须通过精确对象比较确认状态相同。不能因为摘要碰撞而合并数学状态。

---

## 16. 搜索算法

第一阶段只追求更短的合法构造，不要求完备性。

可以依次尝试：

1. IDDFS；
2. best-first search；
3. beam search；
4. random restart；
5. hand-written heuristic；
6. symmetry-aware ordering；
7. pattern database 或目标相关评分；
8. AI candidate ranking。

### 16.1 启发式目标信号

可能的非证明性信号包括：

- 新点的代数次数；
- 点到目标点的数值距离；
- 新对象与目标相关的近似入射关系；
- 是否产生新的方向、长度或子域元素；
- 构造 DAG 的深度和复用程度；
- 历史构造中常见局部模式。

这些信号只能决定搜索顺序或启发式保留范围。

### 16.2 AI 的边界

AI 可以：

- 对候选操作排序；
- 预测哪些状态更可能接近目标；
- 从已知构造生成训练样本；
- 建议可解释的局部构造模式。

AI 不能：

- 决定几何相等；
- 决定构造是否合法；
- 替代 exact verifier；
- 在 proof mode 中无证明地永久删除分支。

第一版在手写启发式和搜索 profiling 完成前不引入 AI 或 GPU。

---

## 17. Proof Mode

Proof Mode 是长期、可选目标，与寻找 upper bound 的普通搜索严格分离。

### 17.1 基本原则

> 所有未搜索分支的删除都必须有可证明的安全依据。

允许：

- 精确重复对象消除；
- 严格状态等价；
- 已证明的初始对称群 reduction；
- 已证明的 dominance rule；
- 可证明非法的操作；
- 完备的深度有界枚举；
- SAT/SMT 编码及可验证 UNSAT certificate。

不允许：

- beam width；
- random sampling；
- AI 低分剪枝；
- 数值近似相等；
- 经验性“无用对象”判断；
- 仅因长期没有找到解就宣布不存在。

### 17.2 最小性证明结构

若已找到一个 \(N\) 步构造，则：

\[
OPT\le N.
\]

若完备排除所有少于 \(N\) 步的构造，则：

\[
OPT\ge N.
\]

两者同时成立才能得到：

\[
OPT=N.
\]

第一阶段不以完成该证明为成功条件。

---

## 18. Baseline 研究

正式搜索前必须先建立正十七边形 baseline。

### 18.1 Baseline 条目

每个条目记录：

- 作者；
- 标题；
- 年代；
- 原始来源；
- 初始对象；
- 可见对象；
- 圆规模型；
- 自由点规则；
- 原文 metric；
- 原文 reported score；
- 项目重新计算的 score；
- 完整构造步骤；
- 项目验证状态；
- 与当前 profile 是否可直接比较。

### 18.2 必须独立重放

在声明“比某文献更短”之前，项目必须：

1. 获取可核对的原始构造；
2. 明确原文初始条件；
3. 明确原文计步规则；
4. 把构造录入证书格式；
5. 用 verifier 重放；
6. 用 metric engine 重新计分；
7. 公开所有不能确认的解释选择。

不能只抄录论文中的一个数字作为已验证 baseline。

### 18.3 两类 profile 分开维护

项目预计维护：

```text
regular-17-e-fixed-v1
```

用于机器搜索，以及未来某个：

```text
regular-17-detemple-YYYY-v1
```

用于历史 Lemoine 对照。

两者的初始信息和 metric 可能不同，因此结果不能交叉比较。

---

## 19. 内核测试

虽然项目只研究正十七边形，数学内核仍需要小型回归测试。

测试可以覆盖：

- 两条直线唯一交点；
- 平行线无有限交点；
- 直线与圆的 0/1/2 个交点；
- 两圆的 0/1/2 个交点；
- 重合对象；
- 正三角形的已知构造；
- 中点和垂直平分线；
- 反射对称状态；
- 重复对象计费；
- 目标点正例和近似但不相等的反例。

这些测试只验证系统，不进入研究结果数据库。

---

## 20. 验证策略

重要结果至少通过三条路径检查：

```text
Sage exact verifier
        +
independent implementation or differential test
        +
human-readable construction explanation
```

正式发布内容包括：

1. construction certificate；
2. profile 文件；
3. 自动验证日志；
4. E-score 明细；
5. 构造依赖 DAG；
6. SVG 或逐步动画；
7. 人类可读步骤；
8. baseline 对照；
9. 软件版本和内容哈希。

---

## 21. 可复现原则

每个正式结果必须满足：

```text
clone repository
      ↓
select pinned verifier version
      ↓
verify certificate
      ↓
obtain the same legality result
      ↓
obtain the same E-score
      ↓
obtain the same exact target identity
```

不能只发布：

- 一张几何图；
- 浮点坐标列表；
- 搜索器自己的成功日志；
- 无法重放的自然语言描述。

---

## 22. 仓库结构

建议结构收束为：

```text
euclid-min/
│
├── README.md
├── LICENSE
│
├── docs/
│   ├── euclid-min-design.md
│   ├── FORMAL_MODEL.md
│   ├── METRICS.md
│   └── LITERATURE.md
│
├── profiles/
│   ├── regular-17-e-fixed-v1.yaml
│   └── historical/
│
├── problems/
│   └── regular-17/
│       ├── problem.yaml
│       └── target.sage
│
├── baselines/
│   └── regular-17/
│
├── certificates/
│   └── regular-17/
│
├── sage/
│   ├── reference/
│   └── experiments/
│
├── go/
│   ├── cmd/
│   ├── search/
│   ├── state/
│   └── metrics/
│
└── tests/
    ├── kernel/
    └── regular-17/
```

当前不创建其他研究问题的占位目录。

---

## 23. CLI 设想

验证：

```bash
euclid-min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  certificates/regular-17/candidate.yaml
```

输出：

```text
Construction valid: YES
Profile: regular-17-e-fixed-v1

Objects drawn:
    Lines:    4
    Circles:  9

Score:
    E-move: 13

Target:
    B_plus: VERIFIED

Claim:
    VERIFIED CONSTRUCTION
    GLOBAL OPTIMALITY NOT CLAIMED
```

以上分数仅为界面示例。

搜索：

```bash
euclid-min search \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --max-score 14 \
  --strategy best-first
```

---

## 24. Visualizer

可视化不是第一阶段验证依据，但对人工审查和传播很重要。

后续静态 Web Viewer 可以：

- 逐步播放构造；
- 显示点、线、圆和步骤编号；
- 高亮本步新对象和新交点；
- 展示构造依赖 DAG；
- 显示当前 E-score；
- 切换 \(B_+\) 和 \(B_-\)；
- 导出 SVG；
- 显示证书和 verifier 版本。

Visualizer 使用浮点近似绘图，但不得参与最终数学判断。

---

## 25. 性能风险

主要风险按优先级包括：

1. 状态数量爆炸；
2. 点数增长导致候选数量平方增长；
3. 圆与圆相交产生大量新点；
4. 实代数表达式快速膨胀；
5. 精确相等和序关系过慢；
6. canonical key 太大；
7. 等价状态无法充分合并；
8. 构造 DAG 和状态占用大量内存；
9. 启发式无法有效接近目标；
10. 历史 profile 的计步规则无法无歧义复现。

### 25.1 优化顺序

```text
形式定义
   ↓
正确性
   ↓
可验证性
   ↓
baseline 重放
   ↓
小规模搜索
   ↓
profiling
   ↓
状态与代数优化
   ↓
启发式
   ↓
AI / GPU（如果确有收益）
```

---

## 26. 技术路线

### Phase 0：冻结形式模型

完成：

- `regular-17-e-fixed-v1` profile；
- 初始对象语义；
- 操作前置条件；
- 交点和退化语义；
- 目标精确定义；
- E-move 规范；
- certificate schema；
- claim policy。

验收标准：

> 两个独立实现者仅阅读规范，就能对同一证书得到相同的合法性和分数判断。

### Phase 1：Sage Reference Verifier

实现：

- Point / Line / Circle；
- exact intersection；
- equality 和 ordering；
- construction replay；
- target verification；
- E-score；
- certificate validation。

验收标准：

> 可以手工录入并严格验证一个已知正十七边形构造。

### Phase 2：Baseline

完成：

- 正十七边形文献表；
- 至少一个可完整重放的构造；
- 初始条件和 metric 对照；
- 项目自行计算的分数；
- 人类可读构造说明。

验收标准：

> 项目拥有至少一个可信、可复现的搜索上界。

### Phase 3：Basic Search

实现：

- candidate generation；
- automatic intersection closure；
- state hash；
- exact duplicate detection；
- IDDFS 或 best-first；
- checkpoint；
- 小深度 exhaustive regression。

验收标准：

> 搜索器能够自动重新发现小型局部构造模式，并输出 verifier 可接受的证书。

### Phase 4：Heuristic Search

实现：

- 目标相关评分；
- 镜像对称 reduction；
- beam / random restart；
- 状态压缩；
- 搜索性能 profiling；
- 必要时的 Go 搜索引擎。

验收标准：

> 可以稳定运行长时间搜索，并产生不劣于 baseline 的候选。

### Phase 5：历史 Metric

在获得和读懂原始资料后实现：

- Lemoine 动作规范；
- DeTemple-compatible profile；
- 历史构造重放；
- 历史分数独立重算。

验收标准：

> 可以对历史 profile 给出有来源、可审计的比较结论。

### Phase 6：新 Upper Bound

目标：

> 在某个已经独立复核的 profile 下，找到严格更短且可公开验证的正十七边形相邻顶点构造。

### Phase 7：Proof Mode（可选）

仅在状态空间、对称性和完备枚举机制足够成熟后尝试。

不把它作为项目必须完成的里程碑。

---

## 27. 成功标准

### Success A：形式模型成立

问题、操作、目标、metric 和证书没有关键歧义。

### Success B：Verifier 成立

能够精确重放正十七边形构造，并由回归测试保护。

### Success C：Baseline 成立

至少一个公开构造被项目独立录入、验证和计分。

### Success D：Search 成立

搜索器能够自动产生合法构造或重新发现 baseline 的核心结构。

### Success E：新 Upper Bound

找到比相同 profile 下可信 baseline 更短的构造。

### Success F：Global Minimum

在严格受限模型中同时给出构造上界和完备 lower-bound proof。

Success A–D 已经足以形成有价值的开源计算数学项目；Success E 是首要研究突破；Success F 是长期最高目标。

---

## 28. 最重要的研究原则

### 原则 1

> 只研究一个问题，也必须把问题定义完整。

### 原则 2

> 先保证 verifier 正确，再追求 solver 聪明。

### 原则 3

> AI 可以寻找答案，但不能决定答案是否正确。

### 原则 4

> 没有完备搜索或独立 lower-bound certificate，就不能声称最小。

### 原则 5

> 没有相同 profile，就不能比较步数。

### 原则 6

> 历史数字必须重新计算，示例数字不能变成 baseline。

### 原则 7

> 任何正式结果都必须可重放、可验证、可复现。

### 原则 8

> 固定实例的成功不能被表述成一般参数族的证明。

---

## 29. 近期工作清单

按顺序完成：

1. 编写 `docs/FORMAL_MODEL.md`；
2. 编写 `profiles/regular-17-e-fixed-v1.yaml`；
3. 定义 certificate JSON Schema 或 YAML Schema；
4. 在 SageMath 中定义精确目标点 \(B_+,B_-\)；
5. 实现三类精确求交；
6. 实现构造重放和 E-score；
7. 录入第一个已知正十七边形构造；
8. 建立 `docs/LITERATURE.md`；
9. 确认第一个可信搜索上界；
10. 再开始实现自动搜索。

搜索器不是第一项开发任务。

---

## 30. 文献起点

1. Émile Lemoine — *Géométrographie*。
2. Duane W. DeTemple (1991) — *Carlyle Circles and the Lemoine Simplicity of Polygon Constructions*，The American Mathematical Monthly 98(2), 97–108，DOI: `10.1080/00029890.1991.11995711`。
3. François Labelle — *On the Complexity of Straightedge and Compass Constructions*；在正式引用前继续核对版本、发表信息和原始链接。
4. Erik D. Demaine, Victor Luo (2025) — *Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*，Journal of Information Processing 33, 1110–1117，DOI: `10.2197/ipsjjip.33.1110`。
5. 正十七边形经典构造及其现代变体的原始资料。

正式宣称任何 `shortest known` 前，必须进行系统文献检索，并公开：

- 检索数据库；
- 检索关键词；
- 检索时间范围；
- 纳入和排除标准；
- 无法获得全文的资料；
- baseline 可比性判断。

---

## 31. 一句话总结

> **Euclid-Min 是一个专门研究正十七边形相邻顶点最短尺规构造的开源计算数学项目：在固定、有限分支的 E-move 模型中搜索更短构造，使用精确代数验证生成可复现证书，并严格区分“新的已验证上界”与“全局最优证明”。**
