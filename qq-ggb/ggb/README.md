# 12 E GeoGebra 演示

下载 [正十七边形-12E.ggb](正十七边形-12E.ggb)，再用 GeoGebra Classic 打开。文件包含真正的直线、圆和交点依赖，可以离线使用，也可以拖动初始点 O、A 查看构造随之变化。只需逐步观看时，也可以使用无需安装 GeoGebra 的 [离线网页](../web/README.md)。

## 使用

- 初次打开显示完成的构造：初始圆为洋红色，最近画出的直线或圆为金色，两个相邻顶点 B₊、B₋ 为绿色。
- 使用画布底部 GeoGebra 自带的**构造播放栏**前进、后退或自动播放；播放速度由栏内的时间间隔控制。需要查看每条记录的定义时，打开“构造协议”。
- 文件共有 **31 条原生构造记录**，最后一条就是目标交点 B₋。第 29 条画最后一个圆，第 30、31 条分别标出 B₊、B₋，之后播放结束。
- 原生序号包含初始对象和免费交点；每条付费直线或圆的标题另标有 `1 E` 至 `12 E`。原生第 4 条是第一条直线，对应 1 E；第 29 条对应 12 E。
- 初始点 O、A 可以拖动；保持两点不同。缩放、平移、对象显隐和点名显示使用 GeoGebra 的常规操作。

本文件仅含几何对象，播放栏保存在视图设置中。旧版第 32–44 条的自定义滑块、开关、文字和按钮已移除。需要按 0–12 E 时间轴观看或一键聚焦结果时，可以使用 [离线网页](../web/README.md)。

细线、深色背景、洋红初始圆、金色当前图元和绿色结果延续此前 Manim 与网页展示的配色。播放时保留已经构造的对象，新画出的直线或圆高亮，先前图元显示为淡蓝色。

## 构造与来源

文件来自已经核验的 [12 E 证书](../construction-12e-011.json)：免费给出 O、A 与初始圆，另外绘制 **3 条直线、9 个圆**，首次在第 12 E 同时得到 A 的两个相邻顶点。文件仅含 18 个几何点、3 条直线、10 个圆（包括免费初始圆），合计 31 条构造记录。两初始点、初始圆及 16 个交点免费，付费对象仍为 3 条直线与 9 个圆。

原始 [正17边形.ggb](../正17边形.ggb) 由 QQ 讨论组网友提供给用户，首创者未确认。原文件保持原样。本演示使用项目的 K、P 分支改写；圆心和初始顶点统一称为 O、A，原文件的辅助点 O 改名为 U，最终 Q、R 显示为 B₊、B₋。不主张 12 E 全局最小。

原图本身也是十二笔，但其原分支得到第 5、12 个顶点。项目最初追加三个圆才得到指定相邻顶点；本演示中的分支改写让原有十二笔直接达到同一目标，省去了这三个圆。几何主体仍来自原图，这是一项有限的目标适配改进。具体比较与结论边界见 [本项目改了什么，价值在哪里](../README.md#本项目改了什么价值在哪里)。

## 核验

[export_geometry.py](export_geometry.py) 先检查证书与 profile 摘要，执行项目精确重放和独立证书重放，并把全部 18 个点逐一与独立根式比较。只有这些检查通过后，才输出 [geometry.json](geometry.json) 中用于展示的十进制坐标。

[export_ggb.cjs](export_ggb.cjs) 使用本地安装的 GeoGebra 引擎重新执行原生 `Line`、`Circle`、`Intersect` 命令，匹配交点分支，并由 GeoGebra 自己保存 GGB。随后重新加载实际保存的文件，检查全部 18 个点、图元计数、平移旋转缩放后的对应关系及原生构造播放；结果记录在 [runtime-report.json](runtime-report.json)。

原生构造播放另有回归检查：逐步前进和后退经过从空白到完成的全部 32 个状态，检查对象出现顺序与当前一笔的高亮；同时确认 31 条记录全部为几何对象、两个目标交点位于末尾、视图设置中启用了原生播放栏。对象显隐由原生构造顺序决定，动态颜色通过 `ConstructionStep()` 跟随当前步骤。

生成器还在后台应用中实际点击原生前进、后退、首尾、播放及暂停按钮，确认自动播放在 `31 / 31` 停止。

**Sage 核验是精确数学判断；GeoGebra 运行时核验是带容差的应用兼容性检查。** GeoGebra 的数值计算和缓存坐标不替代数学证书，GeoGebra 的交点编号也不等于证书的精确字典序索引。

## 重新生成

以下命令从仓库根目录执行，适用于安装了 GeoGebra Classic 6 的 macOS：

```sh
qqGgbSageImage='sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528'
docker run --rm --network none \
  -v "$PWD:/workspace" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  "$qqGgbSageImage" sage -python qq-ggb/ggb/export_geometry.py

npm ci --prefix qq-ggb/ggb
cd qq-ggb/ggb
npx playwright install chromium
curl -fsSL https://www.geogebra.org/apps/deployggb.js -o deployggb.js
node export_ggb.cjs
```

`--assets` 可指定 GeoGebra 安装包内含 `web3d/web3d.nocache.js` 的 HTML 资源目录；`--deploy` 可指定已经下载的官方加载脚本。生成器使用临时的后台渲染进程，不打开用户的浏览器或 GeoGebra 窗口；应用资源、构造和测试数据全部通过回环地址加载，渲染期间阻止外网请求。GeoGebra 本身不打包进仓库。

加载脚本与 GGB 的实际 SHA-256 记录在运行报告中。GeoGebra 保存时可能更新内部标识，因此重新生成不保证 GGB 二进制逐字节相同。

格式和接口参考：[GeoGebra 文件格式](https://geogebra.github.io/docs/reference/en/XML/)、[官方应用 API](https://geogebra.github.io/docs/reference/en/GeoGebra_Apps_API/)、[ConstructionStep](https://geogebra.github.io/docs/manual/en/commands/ConstructionStep/)、[SetConstructionStep](https://geogebra.github.io/docs/manual/en/commands/SetConstructionStep/)。
