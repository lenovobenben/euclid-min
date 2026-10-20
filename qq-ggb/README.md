# 正十七边形 12 E 构造与精确核验

**3 条直线 + 9 个付费圆，首次在第 12 E 同时得到固定初始顶点的两个相邻顶点。**

[离线网页](web/README.md) · [Manim 动画](../animations/e12/README.md) · [可编辑 GeoGebra](ggb/README.md) · [证书](construction-12e-011.json) · [验证报告](verification-12e.json)

规则为 [`regular-17-e-fixed-v1`](../profiles/regular-17-e-fixed-v1.yaml)。免费给出圆心 O、圆上一点 A 和单位圆；交点免费，禁止自由点和直接搬运长度。目标点出现即结束计数，不包含补齐多边形的工作。

## 来源与项目贡献

原文件 [正17边形.ggb](正17边形.ggb)由 QQ 讨论组网友提供给用户，再由用户提供给本项目。原作者、最初公开出处与提供者是否首创均未确认，只能标记这一获取渠道。第三方材料的许可状态也未确认。来源记录见 [source.yaml](source.yaml)。

原始文件保持原样，SHA-256：

```text
4142700f7f7de84fa65b8546ecafd87b1abc037e6722b81fe9940b98483eb838
```

## 本项目改了什么，价值在哪里

把免费初始圆上点记为 0 号顶点，令 θ=2π/17。原图也是十二笔，但最终得到第 5、12 号顶点。本项目保持十二笔的顺序与输入引用，只把 K、P 各改选为另一个交点，N 保持原分支。后续对象随之重新计算，最终直接得到第 1、16 号顶点，即当前任务要求的相邻点。

几何主体归于原始 GGB；本项目完成分支改写、目标适配、证书生成、精确核验、局部搜索与演示。这里没有重新发明整套几何构造，也未确认分支改写的文献优先权。

## 三个交点选择

原 GGB 的 A、B 分别对应证书 O、A，辅助名字加 `ggb_`。以下索引是归一化后先按 x、再按 y 升序的精确字典序索引，从 0 开始；它们不是 GeoGebra 的交点编号。

| K | N | P | 最终 Q 的顶点编号 | 结果 |
|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 2 | 非相邻 |
| 0 | 0 | 1 | 8 | 非相邻 |
| 0 | 1 | 0 | 4 | 非相邻 |
| **0** | **1** | **1** | **1** | **相邻顶点** |
| 1 | 0 | 0 | 6 | 非相邻 |
| 1 | 0 | 1 | 7 | 非相邻 |
| 1 | 1 | 0 | 5 | 原文件分支 |
| 1 | 1 | 1 | 3 | 非相邻 |

[八分支报告](branch-search-report.json)确认八个合法程序覆盖八对不同顶点。选 `(0,1,1)` 精确得到 Q=ζ₁₇、R=ζ₁₇⁻¹，即 B₊、B₋。

## 精确证据

| 文件 | 内容 |
|---|---|
| [construction-12e-011.json](construction-12e-011.json) | 十二笔及免费交点绑定 |
| [verification-12e.json](verification-12e.json) | 项目验证器重放：合法、12 E、首次命中 12 E、双目标、0 重复 |
| [independent_12e_check.py](independent_12e_check.py) | 不导入项目代码的圆方程、嵌套根式和分圆数核验 |
| [independent-12e-report.json](independent-12e-report.json) | 20 项独立核验全部通过 |
| [independent_certificate_check.py](independent_certificate_check.py) | 另一套精确求交实现，读取实际 JSON 重放 |
| [independent-certificate-report.json](independent-certificate-report.json) | 28 条程序、18 个点一致，4 个错误对照被拒绝 |
| [named-object-deletion-report.json](named-object-deletion-report.json) | 固定具名点和图元集合的删一步检查 |

构造内容摘要：

```text
58e9af20902ca9de9843dd16c4dbb931cb3164287f0aa86db906a0492fd93df2
```

几何相等、求交、排序、去重和目标识别使用 Sage `AA`、`QQbar` 或 `QQ` 精确计算。证书不包含输入近似坐标。独立证书重放器以直接代入圆方程解精确二次式，与项目实现分离；通过整数多项式和第十七次分圆多项式恒等式识别目标，并逐一比较全部 18 个点。错误对照覆盖原始非相邻分支、谎报 11 E、越界交点索引和零半径圆。

独立根式证明取

\[
d=-\sqrt{17},\quad k=(d-3)/4,\quad
n=k+\sqrt{(k+1)^2+1},\quad u=(d-9)/8,
\]
\[
p_x=\frac{n-3+\sqrt{(n-3)^2-4(5+2u(n+2))}}4,
\qquad x_Q=2(p_x+1)^2-1.
\]

由对应圆和直线方程验证关联后，精确证明 x_Q=cos(2π/17)，正纵坐标为 sin(2π/17)。

## 最优性与局部搜索

当前严格边界为 **`5 < OPT ≤ 12`**。0–5 E 的[有界证明](../proofs/regular-17-through-5e.json)已独立重放；6–11 E 尚未全局排除。

固定 18 个具名点与 13 个图元（含初始圆），允许改用已有点定义图元和重排顺序时，逐一删除十二个付费对象均无法命中。这只是有限集合内的否定结果，没有覆盖所有未命名交点或新图元。

更广的前缀与替换检查见[局部搜索记录](search-hour-2026-09-11.md)。其中有未完成候选；运行时间与局部失败都不能解释成全局最优证明。

## 复现

从仓库根目录，在 SageMath 10.7 环境并设置 `PYTHONPATH=<仓库>/sage` 后执行：

```sh
sage -python -m euclid_min verify --profile profiles/regular-17-e-fixed-v1.yaml qq-ggb/construction-12e-011.json --json
sage -python qq-ggb/independent_12e_check.py
sage -python qq-ggb/independent_certificate_check.py
```

重建八分支报告和成功证书：

```sh
sage -python qq-ggb/search_branches.py
```

`source_program.py` 只读取原始 GGB 内的 XML，固定原文件摘要与原分支索引，不执行嵌入 JavaScript。`search_branches.py` 枚举 K、N、P；生成器不是验证结论，输出仍需由验证器独立重放。

Docker 完整命令见[项目首页](../README.md#复现)。网页、GeoGebra 和 Manim 的生成方法分别见各自目录。网页与动画的屏幕计算不参与数学正确性判断。
