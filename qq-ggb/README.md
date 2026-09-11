# QQ 讨论组 GGB 构造研究

**当前已验证：12 E，3 条直线 + 9 个付费圆，首次在第 12 E 同时得到固定初始顶点的两个相邻顶点。** 改变原文件中 K、P 的交点分支后，首次 15 E 目标转换方案追加的三个圆全部不再需要。

核验日期：2026-09-10。规则仍为 [`regular-17-e-fixed-v1`](../profiles/regular-17-e-fixed-v1.yaml)，没有改变初始条件、允许操作或计分。

交互式展示：[12 E 网页文件](web/index.html)（单文件，可离线分享）；[操作与生成说明](web/README.md)。在 GitHub 上请先下载 HTML，再用浏览器打开；文件链接显示源码。视觉沿用项目 Manim 动画，支持逐步播放、画面平移缩放和聚焦结果。

可编辑的 GeoGebra 演示：[正十七边形-12E.ggb](ggb/正十七边形-12E.ggb)；[操作与生成说明](ggb/README.md)。保留原生尺规依赖，支持 GeoGebra 原生构造播放及拖动初始点；共 31 条几何记录，完成两个目标交点后即结束，付费对象的标题标注 1–12 E。

## 来源

原文件 [正17边形.ggb](正17边形.ggb) 由 **QQ 讨论组网友提供给用户，再由用户提供给本项目**。提供者是否首创、原作者和最初公开出处均未确认。只能标记这一获取渠道，不能把提供者写为首创者。机器可读来源记录见 [source.yaml](source.yaml)。

文件已从仓库根目录迁入本目录，内容保持原样，SHA-256 为：

```text
4142700f7f7de84fa65b8546ecafd87b1abc037e6722b81fe9940b98483eb838
```

此前 `research/regular17-ggb-2026-09-10` 的核验代码、证书、报告全部迁入本目录。首次分析保存在 [analysis-15e.md](analysis-15e.md)，其中 15 E 是保留原交点分支后的历史转换方案。

## 本项目改了什么，价值在哪里

令 \(\theta=2\pi/17\)，把免费给定的圆上点记作 0 号顶点。本项目的终点是得到它的 1 号或 16 号相邻顶点；归一化到单位圆后，该点的横坐标就是 \(\cos\theta\)。**计数到这个目标出现为止，不包含后续补齐其余顶点和连接多边形边的工作。**

| 方案 | E 计数 | 在这个目标下完成了什么 |
|---|---:|---|
| 收到的原始 GGB，保留原交点分支 | 12 | 得到 5 号、12 号顶点，尚未得到相邻顶点 |
| 本项目首次目标转换 | 15 | 保留原分支，追加三个圆，得到 1 号顶点 |
| 本项目调整 K、P 分支后的方案 | 12 | 原有十二笔直接得到 1 号、16 号顶点 |

原图的几何和十二笔计数都正确。由于 \(\gcd(5,17)=1\)，可以从 0、5 号点出发，反复前进五个顶点并对 17 取模：\(0\to5\to10\to15\to3\to8\to13\to1\to\cdots\)，最终遍历全部十七个顶点。具体操作是以当前点为圆心、经过前一个点画圆，取与初始圆的另一个交点；补齐后按圆周顺序连边即可。不过，每次继续画圆仍须计费，已有一个能生成全体顶点的角度，并不表示目标相邻点已经出现。

本项目的具体修改是：在相同的十二笔操作顺序和点引用下，**K、P 各改选另一交点，N 保持原分支**，其余后续图元随这些点重新计算。原图最终得到的是 \((\cos5\theta,\pm\sin5\theta)\)，改写后直接得到 \((\cos\theta,\pm\sin\theta)\)。省掉的是首次转换方案中**到达目标之前的三次画圆**；初始条件、允许操作、计数方式及终点要求均未改变。

这是一项范围有限、可以复核的改进：几何构造主体来自原始 GGB，本项目完成了交点分支调整、目标适配、证书生成和精确核验。它不代表重新发明了一套正十七边形构造，但在本项目任务下，已验证方案从 15 E 降到 12 E，节省的三笔具有实际意义。

> 在相同初始条件、作图规则和计数方式下，通过调整 K、P 的交点分支，将本项目已验证的 15 E 相邻顶点转换方案降至 12 E，直接得到横坐标为 \(\cos(2\pi/17)\) 的目标点。

这里的 15 E 是一份已验证的转换方案，**尚未证明保留原分支至少需要 15 E**；12 E 也只是已验证上界，未证明全局最小，未确认分支改写的文献优先权。因此不能把成果表述成“原作者用了十五笔，本项目从原图删掉三笔”，也不据此宣称世界纪录。

## 为什么能直接降到 12 E

沿用原 GGB 点名，A 是圆心，B 是初始圆上点。为避免与项目名字混淆，证书把它们分别映射为 `O`、`A`，其余名字加 `ggb_` 前缀。

原文件的 K、N、P 分别由 `k∩f`、`p∩f`、`s∩i` 选出。这三个选择控制根式中的三个正负分支。此前保留了原文件的选择，终点是第 5、12 个顶点；本次枚举全部 8 种组合，恰好得到八对不同的正十七边形顶点。

以下索引是**项目的精确字典序索引**：将原图 A 归一化为 `(0,0)`、B 归一化为 `(1,0)` 后，交点先按 x、再按 y 升序排列，索引从 0 开始。它们不是 GeoGebra 界面的交点编号。

| K 索引 | N 索引 | P 索引 | 最终 Q 的顶点编号（B 为 0） | 结果 |
|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 2 | 非相邻 |
| 0 | 0 | 1 | 8 | 非相邻 |
| 0 | 1 | 0 | 4 | 非相邻 |
| **0** | **1** | **1** | **1** | **12 E 命中相邻顶点** |
| 1 | 0 | 0 | 6 | 非相邻 |
| 1 | 0 | 1 | 7 | 非相邻 |
| 1 | 1 | 0 | 5 | 原文件分支 |
| 1 | 1 | 1 | 3 | 非相邻 |

八个程序都已精确重放。新的分支组合 `(0,1,1)` 只改变 K 和 P，其余操作、点引用与交点索引保持原有规则；后续几何对象由改变后的点重新计算。

令 \(\zeta_{17}=\exp(2\pi i/17)\)。新分支精确得到

\[
Q=\zeta_{17},\qquad R=\zeta_{17}^{-1},
\]

即项目的 `B_plus` 和 `B_minus`。免费初始圆之外仍然只画 3 条直线、9 个圆，没有新增付费动作，也没有重复绘制。

## 当前证据

| 文件 | 内容 |
|---|---|
| [construction-12e-011.json](construction-12e-011.json) | 当前 12 E 成功证书 |
| [verification-12e.json](verification-12e.json) | 未修改的项目验证器在独立进程中重放：合法、12 E、首次命中 12 E、两个目标、0 重复 |
| [branch-search-report.json](branch-search-report.json) | 8 个分支组合的实际结果 |
| [independent_12e_check.py](independent_12e_check.py) | 不导入项目代码的独立圆方程与嵌套根式核验 |
| [independent-12e-report.json](independent-12e-report.json) | 独立核验 20 项全部通过，包括直接与 \(\zeta_{17}\) 比较 |
| [independent_certificate_check.py](independent_certificate_check.py) | 直接读取实际证书，完全不导入项目代码，以另一套精确求交实现逐条重放 |
| [independent-certificate-report.json](independent-certificate-report.json) | 28 条程序条目通过；18 个点逐个与独立根式一致；4 个错误输入对照全部被拒绝 |
| [named-object-deletion-report.json](named-object-deletion-report.json) | 在有限具名点、图元集合内尝试删除一步的结果 |

### 严格计算复核

本目录数学核验与精确搜索中的几何、求交、排序、去重和目标判断均使用 `AA`、`QQbar` 精确代数数或 `QQ` 有理数，不使用 Python 浮点数或浮点容差。原 GGB 的显示坐标也按原始十进制字符串转成精确有理数；仅用精确距离比较核对原文件交点分支，不把缓存坐标作为构造输入。

展示层另有数值计算：[离线网页](web/README.md)使用精确导出的十进制坐标做屏幕投影；[GeoGebra 演示](ggb/README.md)由数值引擎执行原生构造，交点分支匹配和运行时兼容性检查使用容差。这些显示与应用检查不替代 Sage 的精确数学核验。

独立证书重放器从实际 JSON 出发，使用“把直线坐标代入圆方程，解精确二次式”的求交方式。目标通过整数多项式与第 17 次分圆多项式的精确恒等式识别。它还将证书的全部 18 个点与独立根式逐个比较，确认根式证明与证书是同一条构造。

四个错误对照分别是恢复原来的非相邻分支、谎报 11 E、使用越界交点索引和画零半径圆，均按预期被拒绝。项目原有几何、重放及验证器的 28 项相关测试也通过。

12 E 证书的构造内容摘要：

```text
58e9af20902ca9de9843dd16c4dbb931cb3164287f0aa86db906a0492fd93df2
```

独立根式核验取

\[
d=-\sqrt{17},\quad k=\frac{d-3}{4},\quad
n=k+\sqrt{(k+1)^2+1},\quad u=\frac{d-9}{8},
\]
\[
p_x=\frac{n-3+\sqrt{(n-3)^2-4\bigl(5+2u(n+2)\bigr)}}4,
\qquad x_Q=2(p_x+1)^2-1.
\]

由对应的圆和直线方程验证每一项关联后，精确证明 \(x_Q=\cos(2\pi/17)\)，正纵坐标为 \(\sin(2\pi/17)\)。这里相较原文件改变了 \(d\) 的符号和 \(p_x\) 的二次根选择。

## 还能否减少到 11 E

本轮先做了一个小规模、边界明确的检查：固定新 12 E 构造中的 **18 个具名点与 13 个图元（含初始圆）**，允许点使用其他已有对象对作为来源，允许图元使用其他合法点重新定义，并允许重排作图顺序。

在这个有限集合中逐一删除 12 个付费对象，全部无法达到目标。原 12 E 构造作为阳性对照能够重建。

**这个结果只排除了上述有限集合内的删一步方案。** 它没有纳入所有未命名交点，也没有生成新的直线或圆，更不是 0–11 E 的全局下界。结合项目已有的 [0–5 E 有界证明](../proofs/regular-17-through-5e.json)，当前严格边界为 `5 < OPT ≤ 12`；6–11 E 尚未全局排除，未证明 12 E 最小。

2026-09-10 至 11 日又按用户授权进行了约一小时的多核精确搜索，覆盖全部前缀交点、局部两步延伸以及两笔换一笔。具体范围、实测代价、未完成候选和续跑方式见 [一小时搜索记录](search-hour-2026-09-11.md)，机器可读汇总见 [hour-search-summary.json](runs/hour-search-summary.json)。仍不能由局部搜索失败推断 12 E 最小。

## 代码与复现

数学 Python 脚本使用 SageMath 10.7；GeoGebra 生成器还使用 Node.js、Playwright 和本地 GeoGebra 引擎，见其 [生成说明](ggb/README.md#重新生成)。以下命令均从仓库根目录运行，Sage 镜像使用项目已有的固定摘要。

### 最简核验（macOS/Linux）

只读取现有证书并打印 JSON 报告：

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  qq-ggb/construction-12e-011.json --json
```

预期 `valid: true`、`draw_operations` 为 3 条直线和 9 个圆、`first_target_e_move: 12`，`targets` 同时包含 `B_plus` 与 `B_minus`，`duplicate_draws: 0`。

### 重建证书与研究报告（PowerShell）

以下命令会重新生成对应的证书或报告；单纯验证 12 E 正确性只需运行上面的命令。一小时局部搜索的命令与范围另见 [搜索记录](search-hour-2026-09-11.md)。

```powershell
$qqSageImage = 'sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528'

# 恢复原文件与历史 15 E 转换
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python qq-ggb/audit_and_convert.py

# 枚举 8 个分支并生成 12 E 证书
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python qq-ggb/search_branches.py

# 独立进程使用现有项目验证器验证 12 E
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python -m euclid_min verify --profile profiles/regular-17-e-fixed-v1.yaml qq-ggb/construction-12e-011.json --report qq-ggb/verification-12e.json --json

# 独立数学核验
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python qq-ggb/independent_12e_check.py

# 不导入项目代码，直接重放实际证书，并运行错误输入对照
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python qq-ggb/independent_certificate_check.py

# 有限具名点、图元集合内的删一步检查
docker run --rm --network none -v "${PWD}:/workspace" -w /workspace -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 $qqSageImage sage -python qq-ggb/search_named_object_deletions.py
```

原 GGB 是来源材料，脚本不修改它，也不执行其中的 JavaScript。项目证书不含输入近似坐标，精确几何判断由 Sage 重算。
