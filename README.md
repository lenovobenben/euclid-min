# Euclid-Min

Euclid-Min 是一个研究**短尺规构造**的开源计算数学项目。项目把“什么算一步”固定为机器可执行的规则，把每条直线和每个圆完全展开，再用 SageMath 精确重放构造证书。

当前主成果是正十七边形相邻顶点的 **17 E 构造**。仓库同时保留正 257 边形的独立研究记录，但正十七边形仍是项目首页和主线。

> **正十七边形：17 E，7 条直线 + 10 个圆，SageMath 精确验证通过。**

[观看 4K 动画](animations/e17/media/videos/e17_progress/2160p30/E17Progress.mp4) · [查看证书](baselines/regular-17/eddy119-2026-adapted-17e/construction.json) · [查看验证报告](baselines/regular-17/eddy119-2026-adapted-17e/verification.json) · [阅读来源、改写与精确推导](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md)

## 当前结果

| 研究对象 | 规则配置 | 已验证结果 | 结论边界 |
|---|---|---:|---|
| 正十七边形相邻顶点 | `regular-17-e-fixed-v1` | **17 E** | 当前上界；尚未证明全局最小 |
| 正 257 边形任意相邻边 | `regular-257-free-edge-e-fixed-v1` | **69 E** | 从公开视频恢复的可复核基线，不是优化纪录 |

正十七边形的 17 E 由 7 条直线和 10 个圆组成，首次命中目标恰在第 17 E，没有重复绘制。它从 Eddy119 公开的完整 37-move 构造中提取相关前缀：直接按当前目标转换为 18 E，再由项目依赖分析删除一个无用圆，得到 17 E。原作者没有宣称 17 E；几何来源、项目改写和验证责任在基线目录中分别记录。此前的 DeTemple 改写 19 E 作为历史上界保留。

当前还完成了：

- 0–5 E 的严格有界穷尽；
- 17 E 证书的项目验证器重放和独立根式核验；
- 此前 19 E 证书的完整几何—代数 IR；
- 固定 17 E 状态的全部 32,193 个一步参数化检查；
- 固定 16 E 前缀的 22,454 个首步对象和 202,855,848 个受限末笔参数化穷尽；
- 从 17 E 正式证书生成的 4K Manim 动画。

固定前缀检查严格排除了此前 **19 E 路线**的一步或两步压缩，但没有覆盖所有可能的更早构造前缀，也不构成 17 E 的最优性证明。

## 正十七边形问题

免费给出

\[
O=(0,0),\qquad A=(1,0),
\]

以及以 \(O\) 为圆心、经过 \(A\) 的单位圆

\[
\Gamma_0:x^2+y^2=1.
\]

目标是在 \(\Gamma_0\) 上构造 \(A\) 的任意一个正十七边形相邻顶点：

\[
B_\pm=
\left(
\cos\frac{2\pi}{17},
\ \pm\sin\frac{2\pi}{17}
\right).
\]

项目不要求画出完整的十七边形。只要 \(B_+\) 或 \(B_-\) 中任意一点作为已有直线与圆的确定交点出现，目标就已经完成。

## 什么是 E 步

本项目采用 E 步（E-move，elementary move）计数：

\[
E=\text{实际画出的直线数}+\text{实际画出的圆数}.
\]

| 操作 | 成本 |
|---|---:|
| 经过两个已有不同点画一条直线 | 1 E |
| 以一个已有点为圆心、经过另一个已有点画圆 | 1 E |
| 求出或命名已有对象的确定交点 | 0 E |
| 初始点和初始圆 | 0 E |

这里的圆规是**不能保持开口、不能搬运距离的塌圆规**。唯一合法的基础圆是

\[
\operatorname{Circle}(P,Q):
\quad\text{以已有点 }P\text{ 为圆心并经过已有点 }Q.
\]

不能先量取 \(|AB|\)，再把它直接搬到第三个圆心 \(C\) 上。这样的距离搬运必须展开为若干合法的基础画线和画圆操作。

下列常见说法也都不是本项目中的一步：

- 作中点；
- 作垂线、垂直平分线或平行线；
- 作角平分线；
- 作对称点；
- 搬运一段已有长度；
- 在平面、直线或圆上任取一点。

除免费初始点外，每个新点都必须来自已经画出的直线或圆的确定交点。完整定义见[计分规范](docs/METRICS.md)和[正式模型](docs/FORMAL_MODEL.md)。

### 一个简单例子

如果只免费给出两个不同点 \(P,Q\)，构造其中点需要：

1. 画直线 \(PQ\)：1 E；
2. 分别以 \(P,Q\) 为圆心画两个互过对方的圆：2 E；
3. 连接两圆的两个交点：1 E。

总计 4 E，所有交点均为 0 E。如果直线 \(PQ\) 也作为免费初始对象，同一任务才是 3 E。这说明只有初始对象、工具能力、自由点规则、目标和计数方法全部一致的数字才能直接比较。

## 17 E 的证据链

17 E 不是人工看图计数，而是一份可以从零重放的精确结果：

1. [规则配置](profiles/regular-17-e-fixed-v1.yaml)固定初始对象、合法操作和目标；
2. [来源记录](baselines/regular-17/eddy119-2026-adapted-17e/source.yaml)区分原作者的 37-move 构造和项目完成的 18→17 E 改写；
3. [构造证书](baselines/regular-17/eddy119-2026-adapted-17e/construction.json)逐条记录画线、画圆和交点绑定；
4. SageMath 验证器重新计算全部几何对象，不信任证书里声明的分数；
5. [验证报告](baselines/regular-17/eddy119-2026-adapted-17e/verification.json)确认构造合法、总分为 17 E，并精确命中 \(B_+\)；
6. [独立根式检查](baselines/regular-17/eddy119-2026-adapted-17e/independent_radical_report.json)不导入项目代码，另行证明目标坐标等于 \((\cos(2\pi/17),\sin(2\pi/17))\)；
7. [人类可读推导](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md)解释 17 个动作、计数转换和精确代数核验。

构造内容摘要为：

```text
99c80e4ef288e73c3657f2da056b1ec3b9609cd5f7231bcad690f6bc0a722252
```

浮点计算只用于动画、启发式排序和非权威分桶。几何相等、构造合法性、状态合并和目标命中均使用精确数学判断。

## 文献与互联网核查

截至 **2026 年 9 月 5 日**，本轮公开资料检索没有发现一份同时满足以下条件的 \(\le16\) E 构造：

- 初始对象与 `regular-17-e-fixed-v1` 相同；
- 只使用塌圆规和无刻度直尺；
- 不允许自由点和距离搬运；
- 目标同为单位圆上的相邻顶点；
- 给出能够逐步复核的完整构造。

检索中常见的“15 步”包含垂直平分线、角的四等分和补齐其余顶点等复合任务；Lemoine 的 45、50、53、58 是另一种加权指标；有些低图元构造允许不折叠圆规搬运距离。这些数字均不能直接解释成当前 profile 的 E 分数。

François Labelle 1997 年的 [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html) 与本项目具有相同的基础计费核心，但其正十七边形旧题要求完成整个多边形并把首个单位圆计费，也不能直接比较网页分数。

Eddy119 于 2026 年公开了一份带可重放链接的完整正十七边形 37-move 构造。项目恢复其几何依赖后发现，相关前 18 个图元在计入当前目标转换时构成 18 E；其中圆 `d17` 没有任何后继依赖，删除后得到 17 E。**原构造思路和相关前缀来自 Eddy119，18→17 E 的依赖裁剪、当前 profile 证书与精确证明由本项目完成。**

基于现有证据，可以使用的严谨表述是：

> 在 `regular-17-e-fixed-v1` 下，项目已经验证一份 17 E 构造；它由公开 37-move 构造的相关前缀经规则转换和一步依赖裁剪得到。截至 2026 年 9 月 5 日的本轮公开资料检索，尚未发现可复核的 \(\le16\) E 同口径构造。

这不等于已经证明 17 E 全局最小。公开资料检索不能证明未公开构造不存在；全局最优性仍需要完备排除 0–16 E。目前严格下界仅排除 0–5 E。

## 计数法的公开依据

E 步不是为了得到某个纪录数字而临时设计的宣传口径。

- François Labelle 在 1997 年的 [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html) 中，把复杂度定义为实际执行的画线与画圆次数，并采用塌圆规和免费交点。
- Sava Grozdev 与 Deko Dekov 在 2015 年论文 [*The Computer Improves the Steiner’s Construction of the Malfatti Circles*](https://azbuki.bg/wp-content/uploads/2015/02/azbuki.bg_dmdocuments_MathInfo012015_Grozdev_Dekov.pdf) 中采用 Labelle 指标：直线或圆计 1，交点计 0。
- Erik D. Demaine 与 Victor Luo 在 2025 年论文 [*Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*](https://doi.org/10.2197/ipsjjip.33.1110) 中正式使用 **E-move** 一词：一次基础直尺或圆规操作计 1 E，点定义不计入 E-score。

这些来源支持的是基础计数原则。每项资料仍有自己的初始图形、目标和允许操作，不能仅凭都采用类似计数就直接比较最终数字。

## 正 257 边形研究

[regular-257](regular-257/README.md) 保存了对公开视频中 69E 正 257 边形构造的逐帧恢复、精确分圆域验证、证书、依赖分析和 68E 局部搜索。

这一研究采用独立规则 `regular-257-free-edge-e-fixed-v1`：目标是给定圆上的任意一对相邻顶点，不要求其中一个顶点等于免费初始圆上点。因此它与正十七边形 17 E 不是同一道题，两个数字不能横向比较。

当前 69 E 是由 65 条直线和 4 个圆组成的已验证基线。现有 68E 搜索只排除了若干明确冻结的局部替换和候选前沿，没有证明 69 E 最优。

## 本地复现

参考环境为 SageMath 10.7。仓库中的 Python 代码统一在 SageMath 自带的 Python 环境中运行。

### 验证正十七边形 17 E 证书

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m euclid_min verify `
  --profile profiles/regular-17-e-fixed-v1.yaml `
  baselines/regular-17/eddy119-2026-adapted-17e/construction.json
```

成功结果应包含：

```text
valid: true
lines: 7
circles: 10
e_move: 17
first_target_e_move: 17
target: B_plus
```

### 运行正十七边形完整测试

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m unittest discover -s tests -v
```

正 257 边形的验证和测试命令见其[独立说明](regular-257/README.md)。

## 文档入口

| 内容 | 文档 |
|---|---|
| 研究范围、声明等级和技术路线 | [研究设计](docs/euclid-min-design.md) |
| 对象、状态、操作和目标的规范语义 | [正式模型](docs/FORMAL_MODEL.md) |
| E 步的权威定义和可比性规则 | [计分规范](docs/METRICS.md) |
| 构造证书和内容哈希格式 | [证书格式](docs/CERTIFICATE_FORMAT.md) |
| 来源状态和基线转换 | [文献与基线台账](docs/LITERATURE.md) |
| 17 E 来源、改写和精确推导 | [17 E 基线说明](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md) |
| 17 E 动画、分镜与复现方法 | [Manim 动画说明](animations/e17/README.md) |
| 此前 19 E 的完整几何—代数 IR | [几何—代数统一 IR](docs/GEOMETRY_ALGEBRA_IR.md) |
| 搜索与证明阶段记录 | [实施路线](docs/ROADMAP.md) |
| 0–5 E 严格下界产物 | [有界证明记录](proofs/regular-17-through-5e.json) |
| SageMath 使用方法 | [运行说明](sage/README.md) |
| 正 257 边形独立研究 | [regular-257](regular-257/README.md) |
| 协议适用范围 | [许可范围](LICENSE-SCOPE.md) |
| 项目引用元数据 | [CITATION.cff](CITATION.cff) |

若概述性文字与版本化规范冲突，以对应的规则配置、Schema、正式模型和计分规范为准。

## 许可与引用

本项目采用分范围双协议：

- 源代码、测试、构建脚本、配置和 Schema 使用 [Apache License 2.0](LICENSE)；
- 数学文档、构造证书、搜索数据、图表和动画使用 [Creative Commons Attribution 4.0 International](LICENSE-CONTENT)。

完整边界和第三方材料说明见[许可范围](LICENSE-SCOPE.md)。使用本项目成果时，请按照 [CITATION.cff](CITATION.cff) 引用，并注明实际使用的提交或版本。许可证允许使用和再创作，但许可证本身不能替代学术引用。

## 项目原则

> **搜索可以使用启发式，结论必须能够精确重放；没有相同规则就不比较，没有完备下界就不声称最小。**
