# Euclid-Min · 正十七边形 12 E

**简体中文** · [English](README.en.md)

Euclid-Min 围绕正十七边形相邻顶点的 **12 E 尺规构造**，提供精确证书、独立核验、交互网页、GeoGebra 和 Manim 动画。

> **3 条直线 + 9 个付费圆，首次在第 12 E 同时得到两个相邻顶点。**

[离线交互网页](qq-ggb/web/README.md) · [4K Manim 动画](animations/e12/README.md) · [GeoGebra](qq-ggb/ggb/README.md) · [构造证书](qq-ggb/construction-12e-011.json) · [精确验证报告](qq-ggb/verification-12e.json)

[![12 E 构造结果](animations/e12/preview.png)](animations/e12/E12Construction-4K.mp4)

## 问题与计数

免费给出圆心 O=(0,0)、圆上一点 A=(1,0) 和单位圆。目标是构造 A 的任意一个正十七边形相邻顶点：

\[
B_\pm=\left(\cos\frac{2\pi}{17},\ \pm\sin\frac{2\pi}{17}\right).
\]

画一条经过两个已有不同点的直线，或以一个已有点为圆心、经过另一个已有点画圆，各记 **1 E**；已有图元的确定交点免费。采用塌圆规，不允许直接搬运距离、任取点或把中点、垂线等复合操作算成一步。目标点出现即完成任务，不要求补齐整个多边形。

完整规则固定在 [profile](profiles/regular-17-e-fixed-v1.yaml)、[正式模型](docs/FORMAL_MODEL.md)和[计分规范](docs/METRICS.md)中。

## 当前成果与边界

12 E 构造通过 SageMath 精确重放、独立根式核验和另一套独立证书重放。全部 18 个具名点得到交叉检查，首次命中为 12 E，无重复绘制。

几何主体来自 QQ 讨论组提供的 GGB 文件，原作者和最初公开出处未确认。项目调整 K、P 的交点分支，使相同的十二笔直接得到固定初始顶点的两个相邻顶点，并完成证书、核验和演示。来源和分支表见 [QQ-GGB 说明](qq-ggb/README.md)。

已有独立参考检查器严格排除 0–5 E，当前边界为 **`5 < OPT ≤ 12`**。6–11 E 尚未全局排除；12 E 是已验证上界，未证明全局最小，也不宣称世界纪录。[局部搜索](qq-ggb/search-hour-2026-09-11.md)的负结果仅适用于其中明确记载的范围。

## 观看与使用

- **网页**：下载 [index.html](qq-ggb/web/index.html)，用浏览器打开即可离线逐步播放、平移缩放和查看证书。
- **Manim**：观看 [4K MP4](animations/e12/E12Construction-4K.mp4)；深蓝底、洋红初始圆、金色当前一笔，逐笔显示定位点和圆规半径，最后同时展示 B₊、B₋。见[分镜与渲染说明](animations/e12/README.md)。
- **GeoGebra**：打开[可编辑构造](qq-ggb/ggb/正十七边形-12E.ggb)，查看原生尺规依赖或拖动初始点。

展示只消费精确核验后导出的坐标，浮点运算用于投影和动画，不参与数学正确性判断。

## 复现

参考环境为 SageMath 10.7。以下命令从仓库根目录运行，仅读取证书并输出 JSON：

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  qq-ggb/construction-12e-011.json --json
```

应得到 `valid: true`、`lines: 3`、`circles: 9`、`first_target_e_move: 12`，目标包含 `B_plus`、`B_minus`。运行测试时，将最后三行替换为 `sage -python -m unittest discover -s tests -v`。

独立证明、八种分支枚举见 [QQ-GGB 复现说明](qq-ggb/README.md#复现)；动画重建见 [Manim 说明](animations/e12/README.md)。

## 代码与文档

| 位置 | 内容 |
|---|---|
| `qq-ggb/` | 12 E 来源、证书、独立证明、局部搜索、网页和 GeoGebra |
| `animations/e12/` | Manim 数据适配、场景、分镜与 4K 成片 |
| `sage/euclid_min/` | 精确几何内核、重放器、验证器与搜索基础设施 |
| `profiles/`、`schemas/` | 固定规则和版本化文件格式 |
| `proofs/` | 0–5 E 严格排除记录 |
| `tests/` | 几何、12 E 核验、搜索和动画数据回归测试 |

[证书格式](docs/CERTIFICATE_FORMAT.md) · [搜索边界](docs/SEARCH.md) · [下界证明](docs/M7_PROOF_MODE.md) · [实施状态](docs/ROADMAP.md) · [Sage 运行说明](sage/README.md)

## 许可与引用

代码、测试、配置和 Schema 使用 [Apache 2.0](LICENSE)；数学文档、证书、研究数据和动画使用 [CC BY 4.0](LICENSE-CONTENT)。第三方原始材料的权利不受本项目许可改变，完整说明见[许可范围](LICENSE-SCOPE.md)。引用请使用 [CITATION.cff](CITATION.cff)，并注明实际使用的提交或版本。

> 搜索可以使用启发式，结论必须精确重放；没有完备下界就不声称最小。
