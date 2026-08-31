# 正 257 边形 69E 视频恢复记录

本目录记录对 Bilibili 视频《正257边形 69E 尺规作图》的逐步恢复与精确核验。视频地址：

- <https://www.bilibili.com/video/BV1CARsYJEVe/>

正 257 边形专属的说明、步骤表、验证脚本和测试集中保存在本目录。视频原片、
拆帧及分析过程文件位于 Git 忽略的 `tmp/`，不进入正式提交。

当前研究对象已由 [DESIGN.md](DESIGN.md) 和 [profile.yaml](profile.yaml)
冻结为“非锚定正 257 边形边问题”：目标是在给定圆上构造任意一对相邻顶点，
不要求邻接初始圆上点。[profile.schema.json](profile.schema.json) 固定机器可检验
的数据结构，[target.py](target.py) 则在精确分圆域中实现目标弦判据。

截至 2026-08-31，公开视频页面没有给出 Manim 源码、构造证书或逐步文本附件。本目录的 69 步表来自对视频画面、E 计数器、点名和底部操作说明的逐帧核对，不依赖向作者索取未公开材料。

## 已确认的结果

- 计数器从约 69.0 秒的 1E 连续增长到约 475.0 秒的 69E，没有缺号或跳号；
- 69 个计费动作由 **65 条直线和 4 个圆**组成；
- 4 个圆分别是第 2、4、34、69 步；
- [video-69e-steps.csv](video-69e-steps.csv) 给出每一步的对象、定义点、免费交点和视频起始时间；
- [verify_69e.py](verify_69e.py) 在 `Q(zeta_257)` 中精确检查全部 69 步的关联关系、视频展示的周期方程和最终角度关系。
- [construction-69e.json](construction-69e.json) 把视频转写为 150 条声明式程序：69 个计费对象和 81 个免费交点绑定；
- [verification-69e.json](verification-69e.json) 记录专用重放器对 Schema、哈希、显式交点索引、计分和最终目标见证的精确验证结果。

这里的“精确”不是提高浮点精度。验证器使用第 257 次分圆域中的代数恒等式；浮点近似只用于输出便于人工阅读的数值。

## 视频采用的坐标与编码

动画免费给出目标圆 `c0`、圆心 `C` 和圆上点 `B`。核验时采用与画面一致的相似坐标：

\[
C=(0,-1),\qquad B=(0,1),\qquad c_0:(x^2+(y+1)^2=4).
\]

前 6E 构造坐标框架和编码单位圆：

\[
A=(0,0),\qquad c:x^2+y^2=1,\qquad b:y=-1.
\]

对 `c` 上且不等于 `C` 的点 `P=(x,y)`，视频使用

\[
\phi(P)=\frac{x}{y+1}
\]

作为代数值。反向参数化为

\[
P(t)=\left(\frac{2t}{1+t^2},\frac{1-t^2}{1+t^2}\right).
\]

这使画面中的直线作法能够完成加法、乘法和二次方程求根，同时所有新点仍是既有直线或圆的确定交点。

## 分圆周期路径

令

\[
\zeta=e^{2\pi i/257},\qquad
g_j=\zeta^{3^j}+\zeta^{-3^j}.
\]

递归定义

\[
\begin{aligned}
f_j&=g_j+g_{j+64}, &0\le j<64,\\
e_j&=f_j+f_{j+32}, &0\le j<32,\\
d_j&=e_j+e_{j+16}, &0\le j<16,\\
c_j&=d_j+d_{j+8},  &0\le j<8,\\
b_j&=c_j+c_{j+4},  &0\le j<4,\\
a_j&=b_j+b_{j+2},  &0\le j<2.
\end{aligned}
\]

视频从 `a` 层逐级二次分裂到 `g` 层，最终得到

\[
g_0=\zeta+\zeta^{-1}=2\cos\frac{2\pi}{257}.
\]

第 68 步把编码点 `G0` 投影到 `b` 上得到 `V2`；第 69 步作以 `V2` 为圆心、经过 `C` 的圆。该圆与 `c0` 的根轴精确为

\[
x=g_0.
\]

而 `c0` 的半径是 2，右端点为第 5 步得到的 `G=(2,-1)`，因此两个最终交点 `W2±` 满足

\[
\cos\angle GCW_{2\pm}=\frac{g_0}{2}
=\cos\frac{2\pi}{257}.
\]

这精确验证了视频所声称的正 257 边形中心角。

## 口径边界

视频结果和仓库现有的正 17 边形 profile 不能直接比较。

视频先从初始点 `B` 构造出右端点 `G`，最终得到 `G` 的正 257 边形相邻点。也就是说，它解决的是“在给定圆上构造任意一对相邻顶点/一个中心角”的非锚定问题。它没有要求最终相邻点必须邻接最初给出的 `B`。

仓库当前的 `regular-17-e-fixed-v1` 则明确要求目标邻接初始免费点。若为 257 建立 profile，必须把下列两种问题分开命名：

1. 非锚定：构造圆上任意一对正 257 边形相邻顶点；
2. 锚定：必须构造初始给定圆上点的相邻顶点。

本目录只把 69E 表述为“已恢复并精确验证的视频构造”。当前证书已经验证所有
显式绑定和最终目标见证，但尚未枚举完整自动交点闭包，也未确认 0–68E 是否存在
未绑定的更早目标。因此暂不把它表述为正式 baseline、公开纪录或全局最优值。

## 复现

在仓库已挂载到 SageMath 容器 `/workspace` 的情况下运行：

```powershell
docker exec `
  boring_wing `
  sage -python regular-257/verify_69e.py
```

预期关键输出：

```text
steps=69 lines=65 circles=4
target_axis_x_equals_g0=True
exact_incidence_check=true
displayed_period_relations=true
```

重新生成并验证 JSON 证书：

```powershell
docker exec `
  -e PYTHONPATH=/workspace/sage `
  boring_wing `
  sage -python regular-257/build_69e_certificate.py

docker exec `
  -e PYTHONPATH=/workspace/sage `
  boring_wing `
  sage -python regular-257/verify_69e_certificate.py
```

验证器使用 `CyclotomicField(257)` 处理主路径，只在 `sqrt(3)` 和最终正弦坐标
需要时提升到 `UniversalCyclotomicField`。它不使用浮点容差或 `AA` 根隔离。

运行本目录测试：

```powershell
docker exec `
  -e PYTHONPATH=/workspace/sage `
  boring_wing `
  sage -python -m unittest discover -s regular-257 -p "test_*.py" -v
```

## 后续工作

- 实现完整自动交点闭包，并检查 0–68E 是否出现未绑定的更早目标；
- 精确去重全部作图对象并生成依赖图；
- 独立核对 69E 的文献优先权与是否存在更短公开构造。
