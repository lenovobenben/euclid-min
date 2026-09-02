# Euclid-Min

Euclid-Min 是一个研究正十七边形相邻顶点短尺规构造的计算数学项目。项目把“什么算一步”固定成可执行的形式规范，用 SageMath 精确重放每一份构造证书，再在同一规则下比较长度。

## 研究问题

初始免费给出

\[
O=(0,0),\qquad A=(1,0),\qquad x^2+y^2=1,
\]

其中单位圆以 \(O\) 为圆心并经过 \(A\)。只能使用无刻度直尺和可折叠圆规，目标是在单位圆上构造 \(A\) 的任意一个正十七边形相邻顶点。

项目不要求画出完整的十七边形。只要精确产生

\[
B_\pm=\left(\cos\frac{2\pi}{17},\ \pm\sin\frac{2\pi}{17}\right)
\]

中的任意一点，就达到目标。

## 什么算一步

本项目采用 **E 步**（E-move，elementary move）计数。权威定义见[计分规范](docs/METRICS.md)，核心规则如下。

| 动作 | 分数 |
|---|---:|
| 经过两个已有不同点画一条直线 | 1 E |
| 以一个已有点为圆心、经过另一个已有点画圆 | 1 E |
| 求出或命名已有直线与圆的确定交点 | 0 E |
| 初始点 \(O,A\) 和单位圆 | 0 E |

因此

\[
E=\text{实际画出的直线数}+\text{实际画出的圆数}
\]

还有几条不能省略的限制：

- 除 \(O,A\) 外，所有新点必须是已有直线或圆的确定交点；不能任取平面点、直线上的点或圆上的点。
- 中点、垂线、垂直平分线、角平分线、平行线和距离搬运都不是一步；必须展开为基础画线、画圆操作。
- 圆规是可折叠圆规。不能一步画“以 \(C\) 为圆心、以 \(|AB|\) 为半径”的圆，除非 \(C\) 就是 \(A,B\) 中的一个端点。
- 重复画出已有直线或圆仍然消耗 1 E。
- 两个数字只有在初始对象、允许工具、自由点规则、目标和计分规则全部相同，并且证书都通过精确验证时，才能直接比较。

一个简单例子：若只免费给出两个点 \(P,Q\)，构造其中点需要画直线 \(PQ\)、两个等半径圆以及两圆交点连线，共 **4 E**；交点本身不另计分。若直线 \(PQ\) 也作为初始对象免费给出，则同一任务是 **3 E**。这说明“初始给了什么”也是步数定义的一部分。

## 这种计数法的文献依据

E 步不是本项目临时创造的宣传数字。

- François Labelle 在 1997 年的 [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html) 中使用可折叠圆规，并把复杂度定义为实际执行的画线和画圆次数；交点直接视为已构造点。这与本项目的计费核心相同。
- Sava Grozdev 与 Deko Dekov 在 2015 年论文 [*The Computer Improves the Steiner’s Construction of the Malfatti Circles*](https://azbuki.bg/wp-content/uploads/2015/02/azbuki.bg_dmdocuments_MathInfo012015_Grozdev_Dekov.pdf) 中实际采用 Labelle 计数：每条直线或每个圆计 1，交点计 0。
- Erik D. Demaine 与 Victor Luo 在 2025 年论文 [*Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*](https://doi.org/10.2197/ipsjjip.33.1110) 中正式使用 **E-move** 一词：一次直尺或圆规基础操作计 1 E，点定义不计入 E-score。本项目沿用这一名称和计费核心。

这些资料的具体初始对象、目标和自由点规则并不都与本项目相同，所以它们证明的是“这种计数原则有明确先例”，不是说其中报告的步数可以直接与本项目比较。尤其是 DeTemple 1991 使用的是 Lemoine 简洁度；其 45 分与本项目的 19 E 不是同一种数字。

## 当前结果

固定规则配置为：

```text
regular-17-e-fixed-v1
```

当前仓库包含一份通过 SageMath 精确验证的 **19 E 构造证书**：8 条直线、11 个圆。它来自对 DeTemple 1991 修改版 Carlyle 圆路线的规则转换、依赖清理和局部精确替换。

项目现已把这份证书编译为第一份几何—代数统一 IR。完整闭包显示，目标迹
\(2\cos(2\pi/17)\) 在第 17 E 已经作为未命名的免费兄弟根出现；固定 17 E
状态的全部 32,193 个一步参数化已经精确穷尽，没有产生新的目标对象。进一步从
固定 16 E 状态穷尽 22,454 个首步对象及 202,855,848 个受限末笔参数化，也没有
命中或未决关系。因此现有固定 16 E 前缀不能在两笔内压成 18 E；不同前缀或更早
的共享痕迹改写仍待搜索。

这里的 32 E 是同一项目规则下对 DeTemple 原路线的转换基线，19 E 是项目对该基线的改进。它们不是“此前世界纪录”和“新的世界纪录”。项目尚未完成系统文献检索，也尚未排除全部 0–18 E 构造，因此目前只能严格表述为：

> 在 `regular-17-e-fixed-v1` 下，项目已经验证一份 19 E 构造；相较同规则下的 32 E 项目基线，减少了 13 E。

完整最优性证明目前暂停。现有证明记录严格排除了 0–5 E，但不能由此推出 19 E 最优。

## 文档入口

- [研究设计](docs/euclid-min-design.md)：研究对象、范围、声明等级和技术路线；
- [正式模型](docs/FORMAL_MODEL.md)：对象、状态、操作、交点和目标的规范语义；
- [计分规范](docs/METRICS.md)：E 步的权威定义、例子和文献关系；
- [证书格式](docs/CERTIFICATE_FORMAT.md)：构造程序、哈希和验证输出约定；
- [文献与基线台账](docs/LITERATURE.md)：来源状态、规则差异和可比性；
- [实施路线](docs/ROADMAP.md)：各阶段的完成状态；
- [19 E 构造说明](baselines/regular-17/detemple-1991-carlyle-improved-converted/explanation.md)：证书、推导和依赖主链；
- [几何—代数统一 IR](docs/GEOMETRY_ALGEBRA_IR.md)：完整闭包、二次塔、上下文成本、候选级断点恢复和 18 E 局部搜索；
- [19 E Manim 动画](animations/e19/README.md)：由 Sage 几何数据生成的可复现动画；
- [5 E 有界证明记录](proofs/regular-17-through-5e.json)：可由独立检查器重放的当前下界产物；
- [SageMath 运行说明](sage/README.md)。

若概述性文档与版本化规范冲突，以规则配置文件、Schema、[正式模型](docs/FORMAL_MODEL.md)、[计分规范](docs/METRICS.md)和[证书格式](docs/CERTIFICATE_FORMAT.md)为准。

## 运行验证

参考环境为 SageMath 10.7。全部 Python 代码统一在 SageMath 自带的 Python 环境中运行。

运行完整测试：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m unittest discover -s tests -v
```

验证 19 E 构造证书：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m euclid_min verify `
  --profile profiles/regular-17-e-fixed-v1.yaml `
  baselines/regular-17/detemple-1991-carlyle-improved-converted/construction.json
```

浮点计算只用于绘图、启发式排序和非权威分桶；几何相等、构造合法性、状态合并和目标命中全部使用精确数学判断。
