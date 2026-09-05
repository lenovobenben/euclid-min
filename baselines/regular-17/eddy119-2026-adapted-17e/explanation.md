# 从公开社区构造提取的 17 E 正十七边形相邻顶点构造

核查日期：2026-09-05。

## 来源与本次改写

原始来源是 Eddy119 于 2026-02-28 在以下评论中公开的完整正十七边形 37-move 构造：

https://gist.github.com/mrflip/a973b1c60f4a38fc3277ddd57ce65b28?permalink_comment_id=6006486

原帖附有 Ancient Greek Geometry 可重放链接。本次下载公开游戏代码，在无 GUI 环境重放并恢复几何对象的依赖，然后按 `regular-17-e-fixed-v1` 改写：

1. 保留前 18 个不同绘制对象；初始单位圆 d1 按项目规则免费。
2. 删除圆 d17：它以点 134 为圆心、经过 A；后面的 d18 只需要此前已有的点 134，不使用 d17 的任何交点。
3. d18 与单位圆给出目标的对径点；追加过该点与 O 的直线，得到固定初始点 A 的相邻顶点。

合计为 **18 − 1 − 1 + 1 = 17 E，即 7 条直线、10 个圆**。这是本次从原帖构造提取并改写后的分数；原作者没有在该评论中宣称 17 E。

本方案严格沿用项目初始对象 O=(0,0)、A=(1,0)、单位圆，所有新点均来自此前已绘对象的有限交点，所有圆均由已有圆心和已有圆上点定义。没有任意点，也没有直接搬运距离。

## 17 个计费动作

下表中所有交点的命名免费。正式证书将交点选择展开为 `intersect` 指令，按精确 (x,y) 字典序选择分支。

| E | 对象 | 构造及免费取得的关键点 |
|---|---|---|
| 1 | d2 圆 | 以 A 为圆心经过 O，与单位圆相交 |
| 2 | d3 线 | 直线 OA，即横轴 |
| 3 | d4 线 | 连接 d2 与单位圆的两个交点；得到 x=1/2 和 M=(1/2,0) |
| 4 | d5 圆 | 以 A 为圆心经过 M；横轴右交点为 R=(3/2,0) |
| 5 | d6 圆 | 以 M 为圆心经过 R；与 d4 得到 T=(1/2,-1) |
| 6 | d7 线 | 连接 d2 与 d6 的两个交点；得到 x=3/4 和 K=(3/4,0) |
| 7 | d8 圆 | 以 K 为圆心经过 T；横轴交点为 L=(l,0)、R1=(r,0) |
| 8 | d9 圆 | 以 L 为圆心经过 T；取横轴右交点 H=(h,0) |
| 9 | d10 圆 | 以 R1 为圆心经过 T；取横轴右交点 V=(v,0) |
| 10 | d11 圆 | 以 M 为圆心经过 H；取 d4 上方交点 U=(1/2,u) |
| 11 | d12 圆 | 以 U 为圆心经过 M |
| 12 | d13 线 | 连接 d11 与 d12 的两个交点；得到 y=u/2 |
| 13 | d14 线 | 连接 U 与 V；与 d13 交于 C=((1/2+v)/2,u/2) |
| 14 | d15 圆 | 以 C 为圆心经过 O |
| 15 | d16 线 | d2 与 d8 的上交点是 (1,1)，连接它与 A 得到 x=1；与 d15 的上交点为 W=(1,t) |
| 16 | d18 圆 | 以 A 为圆心经过 W；与单位圆取下交点 N |
| 17 | target_diameter 线 | 连接 O 与 N，另一单位圆交点即 B_plus |

## 独立精确代数核验

`independent_radical_check.py` 不导入任何项目代码，直接由上述圆和直线方程得到：

\[
l=\frac{3-\sqrt{17}}4,\qquad r=\frac{3+\sqrt{17}}4,
\]
\[
h=l+\sqrt{(1/2-l)^2+1},\quad u=h-1/2,\quad
v=r+\sqrt{(r-1/2)^2+1},
\]
\[
t=\frac u2+\sqrt{\frac{u^2}{4}+v-\frac12},\qquad c=\frac{t^2}{2}-1.
\]

d18 与单位圆相交的横坐标为 1−t²/2=−c，所取下交点为 N=(−c,−sqrt(1−c²))。其对径点为 (c,sqrt(1−c²))。

SageMath 的精确实代数数运算确认：

\[
256c^8+128c^7-448c^6-192c^5+240c^4+80c^3-40c^2-8c+1=0.
\]

c 位于有理隔离区间 (0.9324,0.9325)，其中该多项式只有一个实根。另外直接与 `QQbar.zeta(17)` 比较，精确验证：

\[
c=\frac{\zeta_{17}+\zeta_{17}^{-1}}2=\cos\frac{2\pi}{17},
\qquad \sqrt{1-c^2}=\operatorname{Im}(\zeta_{17})=\sin\frac{2\pi}{17}.
\]

独立报告中的 8 项检查均为 true。数值仅用于从游戏数据识别交点分支和展示，最终证书不包含任何近似坐标输入。

## 复现

验证器在每条合法指令后调用 Sage `AA.simplify()` 规约实代数数的内部表示，并按
计算成本更低的字段顺序比较规范化直线。这两项只缩短精确等值判断的时间，不改变
证书、几何公式或目标判断。用固定的 SageMath 10.7 镜像执行标准验证入口：

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/sage -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  baselines/regular-17/eddy119-2026-adapted-17e/construction.json
```

独立根式检查：

```sh
docker run --rm --network none \
  -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONDONTWRITEBYTECODE=1 \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python baselines/regular-17/eddy119-2026-adapted-17e/independent_radical_check.py
```

本结果确认一条同规则更短构造，不包含 17 E 的最小性结论。
