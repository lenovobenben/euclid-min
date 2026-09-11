# Euclid-Min

**简体中文** · [English](README.en.md)

Euclid-Min 是一个研究**短尺规构造**的开源计算数学项目。项目把“什么算一步”固定为机器可执行的规则，把每条直线和每个圆完全展开，再用 SageMath 精确重放构造证书。

当前主成果是正十七边形相邻顶点的 **12 E 构造**。仓库同时保留正 257 边形的独立研究记录，但正十七边形仍是项目首页和主线。

> **正十七边形：12 E，3 条直线 + 9 个付费圆，SageMath 精确验证通过。**

[12 E GeoGebra 演示](qq-ggb/ggb/README.md) · [12 E 离线网页](qq-ggb/web/README.md) · [查看证书](qq-ggb/construction-12e-011.json) · [查看验证报告](qq-ggb/verification-12e.json) · [阅读来源、改写与精确核验](qq-ggb/README.md)

## 当前结果

| 研究对象 | 规则配置 | 已验证结果 | 结论边界 |
|---|---|---:|---|
| 正十七边形相邻顶点 | `regular-17-e-fixed-v1` | **12 E** | 当前上界；尚未证明全局最小 |
| 正 257 边形任意相邻边 | `regular-257-free-edge-e-fixed-v1` | **69 E** | 从公开视频恢复的可复核基线，不是优化纪录 |

正十七边形的 12 E 构造首次在第 12 E 同时得到固定初始顶点的两个相邻顶点，没有重复绘制。几何主体来自 QQ 讨论组网友提供的 GGB 文件，原作者和最初公开出处尚未确认。

原文件本身也是 12 E，但得到的是第 5、12 号顶点。本项目最初保留原分支，追加三个圆得到目标，形成 15 E 转换方案；随后只调整 K、P 的交点分支，让原有十二笔直接得到第 1、16 号顶点。节省的是到达同一目标之前的三次画圆，计数不包含后续补齐多边形。15 E 未被证明是原分支的最省转换，12 E 也未被证明全局最小。具体贡献与边界见 [QQ-GGB 说明](qq-ggb/README.md#本项目改了什么价值在哪里)。

此前的 Eddy119 改写 17 E 和 DeTemple 改写 19 E、32 E 均作为历史基线保留。结合既有的 0–5 E 严格排除，当前边界为 **`5 < OPT ≤ 12`**；6–11 E 尚未全局排除。

当前还完成了：

- 0–5 E 的严格有界穷尽；
- 12 E 证书的项目验证器重放、独立根式核验与独立证书重放；
- K、N、P 的全部八种分支组合核验，以及范围明确的 [12 E 局部改进搜索](qq-ggb/search-hour-2026-09-11.md)；
- 从 12 E 证书生成的可编辑 GeoGebra 演示与离线网页；
- 此前 19 E 证书的完整几何—代数 IR；
- 历史 19 E 路线固定 17 E 状态的全部 32,193 个一步参数化检查；
- 历史 19 E 路线固定 16 E 前缀的 22,454 个首步对象和 202,855,848 个受限末笔参数化穷尽；
- 从历史 17 E 正式证书生成的 [4K Manim 动画](animations/e17/README.md)。

这些固定前缀和局部搜索的负结果只适用于各自明确记录的范围，不能证明 12 E 最优。

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

## 12 E 的证据链

12 E 的分数和目标由以下证据链精确重放确认：

1. [规则配置](profiles/regular-17-e-fixed-v1.yaml)固定初始对象、合法操作和目标；
2. [来源记录](qq-ggb/source.yaml)记录原始 GGB 的获取渠道和摘要，并区分原始几何与本项目的分支改写；
3. [构造证书](qq-ggb/construction-12e-011.json)逐条记录画线、画圆和交点绑定；
4. SageMath 验证器重新计算全部几何对象，不信任证书里声明的分数；
5. [验证报告](qq-ggb/verification-12e.json)确认构造合法、3 条直线加 9 个付费圆，首次在第 12 E 同时命中 \(B_+\)、\(B_-\)，无重复绘制；
6. [独立根式检查](qq-ggb/independent-12e-report.json)不导入项目代码，另行核验圆方程、嵌套根式和第 17 次单位根的精确关系；
7. [独立证书重放](qq-ggb/independent-certificate-report.json)以另一套精确求交实现重放实际 JSON，将全部 18 个点与独立根式比较，并拒绝四个错误对照；
8. [人类可读说明](qq-ggb/README.md)解释分支选择、计数、精确代数核验和贡献边界。

构造内容摘要为：

```text
58e9af20902ca9de9843dd16c4dbb931cb3164287f0aa86db906a0492fd93df2
```

数学核验中的几何相等、构造合法性、状态合并和目标命中均使用精确判断。展示坐标、GeoGebra 数值运行及兼容性检查，以及部分启发式排序和非权威分桶可以使用浮点计算；它们不替代精确证书。

## 文献与互联网核查

以下为 **2026 年 9 月 5 日的历史检索记录**，早于 QQ-GGB 的 12 E 分支改写。当前来源与构造台账见 [文献与基线台账](docs/LITERATURE.md)；该检索结论仅描述当时已审阅的公开资料。

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

> 在 `regular-17-e-fixed-v1` 下，项目已验证一份 12 E 相邻顶点构造。几何主体来自 QQ 讨论组提供的 GGB 文件；项目通过调整 K、P 的交点分支，将首次已验证的 15 E 目标转换降至 12 E。原作者、最初公开出处和该分支改写的文献优先权尚未确认。

12 E 是当前已验证上界，未据此宣称文献最短或世界纪录。全局最优性还需要完备排除 6–11 E；已有严格下界仅排除 0–5 E，QQ-GGB 的局部搜索没有扩大这一全局排除范围。

## 计数法的公开依据

E 步不是为了得到某个纪录数字而临时设计的宣传口径。

- François Labelle 在 1997 年的 [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html) 中，把复杂度定义为实际执行的画线与画圆次数，并采用塌圆规和免费交点。
- Sava Grozdev 与 Deko Dekov 在 2015 年论文 [*The Computer Improves the Steiner’s Construction of the Malfatti Circles*](https://azbuki.bg/wp-content/uploads/2015/02/azbuki.bg_dmdocuments_MathInfo012015_Grozdev_Dekov.pdf) 中采用 Labelle 指标：直线或圆计 1，交点计 0。
- Erik D. Demaine 与 Victor Luo 在 2025 年论文 [*Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*](https://doi.org/10.2197/ipsjjip.33.1110) 中正式使用 **E-move** 一词：一次基础直尺或圆规操作计 1 E，点定义不计入 E-score。

这些来源支持的是基础计数原则。每项资料仍有自己的初始图形、目标和允许操作，不能仅凭都采用类似计数就直接比较最终数字。

## 正 257 边形研究

[regular-257](regular-257/README.md) 保存了对公开视频中 69E 正 257 边形构造的逐帧恢复、精确分圆域验证、证书、依赖分析和 68E 局部搜索。

这一研究采用独立规则 `regular-257-free-edge-e-fixed-v1`：目标是给定圆上的任意一对相邻顶点，不要求其中一个顶点等于免费初始圆上点。因此它与正十七边形任务不是同一道题，两个数字不能横向比较。

当前 69 E 是由 65 条直线和 4 个圆组成的已验证基线。现有 68E 搜索只排除了若干明确冻结的局部替换和候选前沿，没有证明 69 E 最优。

## 本地复现

参考环境为 SageMath 10.7。数学 Python 脚本在 SageMath 自带的 Python 环境中运行；演示的生成环境见各自说明。

### 验证正十七边形 12 E 证书

从仓库根目录运行，以下命令适用于 macOS/Linux，只读取证书并输出 JSON 报告。PowerShell 命令及完整重建流程见 [QQ-GGB 复现说明](qq-ggb/README.md#代码与复现)。

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  qq-ggb/construction-12e-011.json --json
```

JSON 报告的关键字段应为：

```json
{
  "valid": true,
  "draw_operations": {"lines": 3, "circles": 9, "total": 12},
  "duplicate_draws": 0,
  "score": {"metric": "e_move", "e_move": 12},
  "first_target_e_move": 12,
  "targets": ["B_plus", "B_minus"]
}
```

### 运行正十七边形完整测试

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
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
| 当前 12 E 来源、分支改写、贡献和精确核验 | [QQ-GGB 研究](qq-ggb/README.md) |
| 12 E 演示的使用与生成 | [GeoGebra](qq-ggb/ggb/README.md) · [离线网页](qq-ggb/web/README.md) |
| 12 E 局部搜索的范围、覆盖与实测资源 | [搜索记录](qq-ggb/search-hour-2026-09-11.md) |
| 历史 17 E 来源、改写和精确推导 | [17 E 基线说明](baselines/regular-17/eddy119-2026-adapted-17e/explanation.md) |
| 历史 17 E 动画、分镜与复现方法 | [Manim 动画说明](animations/e17/README.md) |
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
