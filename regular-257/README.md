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
- [verification-69e.json](verification-69e.json) 记录专用重放器对 Schema、哈希、显式交点索引、计分、对象去重和自动闭包首次目标命中的精确验证结果；
- 完整目标审计确认 69 个付费动作互不重复，并且 0–68E 均未出现目标，首次命中恰在 69E。
- [dependency-graph-69e.json](dependency-graph-69e.json) 给出 153 个节点和 300 条依赖边的机器可读分析；[dependency-graph-69e.dot](dependency-graph-69e.dot) 则把免费交点收缩为 69 个付费节点，便于查看主路径。
- [semantic-dependencies-69e.json](semantic-dependencies-69e.json) 精确枚举具名点的替代来源和既有对象的替代定义，并证明在该有限对象/具名点宇宙内不能删除任何一个付费对象。
- [full-intersection-closure-69e.json](full-intersection-closure-69e.json) 把现有 70 个对象之间的全部有限实交点纳入闭包，并证明即使使用所有未命名交点，也不能删除任何一个现有付费对象。
- [named-new-object-search-69e.json](named-new-object-search-69e.json) 首次允许加入一个证书之外的新直线或圆；在由 83 个具名点定义且能额外命中具名点的 147 个候选中，穷尽 344,862 次删二闭包，没有找到 68E 替换。
- [full-point-candidate-frontier-69e.json](full-point-candidate-frontier-69e.json) 穷尽完整 2287 点宇宙中的 2346 个删二状态，量化加入新对象以前真正可用的精确定义点和对象前沿，为 M257-8 长搜索选定首个严格分片。
- [final-pair-line-chord-search-68e.json](final-pair-line-chord-search-68e.json) 穷尽最大前沿中的 1,546,161 个直线定义，排除“最后一条新直线与目标圆直接截出一条目标边”的全部方案。
- [final-pair-line-adjacent-search-68e.json](final-pair-line-adjacent-search-68e.json) 对同一批直线穷尽“新交点邻接已有目标圆点”的另一类方案；[final-pair-circle-search-68e.json](final-pair-circle-search-68e.json) 则同时穷尽 3,092,322 个有向圆定义的两类目标事件。
- [final-pair-direct-search-68e.json](final-pair-direct-search-68e.json) 汇总上述结果：最大前沿中由 1759 个已物化精确点定义的 4,638,483 个直线或圆定义，均不能作为最后的第 68E 直接产生目标边。
- [residual-point-ball-audit-68e.json](residual-point-ball-audit-68e.json) 进一步为最大前沿中的 344 个抽象残余点建立严格实球包围，并验证全部 2103 个可用点互相可区分、4338 条对象关联均被包围。
- [all-point-direct-search-68e.json](all-point-direct-search-68e.json) 汇总完整最大前沿：由全部 2103 个可用点定义的 6,630,759 个直线或圆定义均已穷尽，未找到解且没有未决项。
- [geometry-algebra-baseline-69e.json](geometry-algebra-baseline-69e.json) 首次把 17 组结构化二次关系、42 个代数—几何表示、69 笔付费转移和 2285 个免费闭包增量放进同一份可重放 IR；[GEOMETRY-ALGEBRA-IR.md](GEOMETRY-ALGEBRA-IR.md) 给出状态化 E 成本的正式定义。
- [geometry-gadgets-tail-69e.json](geometry-gadgets-tail-69e.json) 把两个对称 9E 尾部提取为带显式代数/几何边界的可执行 gadget，并分别从 46E、55E 前缀状态精确重放和动态计价。
- [tail-cross-pair-direct-search-46e.json](tail-cross-pair-direct-search-46e.json) 穷尽两个尾部 6×6 个根对在 46E 具名前缀中的一笔联合产出；所有 1080 个圆定义都只是重画编码圆 `c`，精确去重后没有新候选。
- [tail-cross-pair-all-point-line-search-46e.json](tail-cross-pair-all-point-line-search-46e.json) 把直线审计扩展到 46E 完整闭包的 989 个点；36 条跨尾部目标弦共完成 35,604 次严格关联判定，没有任何可用点落在其中。
- [tail-cross-pair-all-point-circle-search-46e.json](tail-cross-pair-all-point-circle-search-46e.json) 对同一批根对和全部 989 个可用圆心审计垂直平分线条件；仅有的 36 次关联都是原有圆心 `A`，所得圆均精确等于已有编码圆 `c`。
- [tail-cross-pair-two-object-line-bridge-search-46e.json](tail-cross-pair-two-object-line-bridge-search-46e.json) 继续穷尽“首笔新对象产生两个定位点、次笔画跨尾部目标直线”的最小 2E 桥接模板；44,611,812 个圆心—桥接点对经严格筛选只留下 136 项，全部精确等于已有四圆，仍无新候选。
- [synthesis-live-slice-68e.json](synthesis-live-slice-68e.json) 从 `g_0` 反向提取代数活跃根和基线几何依赖：17 组二次关系全部活跃，但 34 个根中只有 23 个继续服务于目标，另外 11 个只是免费共轭产物；由此把 47–64E 联合替换的外部输出从 12 个量缩为 `F0、F56` 两个点，并冻结“从 46E 状态以至多 17E 交付两点”的 68E 合成契约。
- [tail-quadratic-chord-ir-68e.json](tail-quadratic-chord-ir-68e.json) 把尾部六组二次方程的根和、根积精确编译为编码圆根载线及两轴截点表达式；六条公式载线全部等于证书直线。46E 前缀只在 `AJ2、AQ2` 上已有同一个点 `A`，没有任何载线已有两个定位点。
- [shared-locator-line-search-46e.json](shared-locator-line-search-46e.json) 穷尽一条新直线同时产生两条根载线定位点的模板；27,305 个候选出现中，643 个可画出现全部精确等于 46E 前缀已有直线，新共享定位直线为 0。
- 共享定位圆搜索目前只有部分结论：前 7/15 个任务对已精确排除新圆；第 8 对在强制将抽象圆心从 `QQbar` 降到 `CyclotomicField(257)` 时陷入高成本数域合成。这次运行已主动终止，不得将其解读为第 8 对或全部圆模板的否定结论。

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

本目录把 69E 表述为冻结口径下**已恢复、可重放且精确验证的 baseline**。证书不仅
验证显式绑定和最终目标见证，还对每一个付费动作执行了完整的目标闭包审计，确认
0–68E 没有未绑定的更早目标，并确认全部 69 个付费对象互不重复。

目标审计不需要物化所有与目标无关的附带交点。任何落在目标圆 `c0` 上的新点，
必定来自某条新直线与 `c0` 的交点，或某个新圆与 `c0` 的公共弦；后者由该圆和
`c0` 的根轴唯一承载。因此，只需精确审计这些“目标弦载线”，并检查任意两条载线
是否承载相差 $2\pi/257$ 的圆上点，就已经完整覆盖自动闭包中的所有目标候选。

这项结论只确立 69E 是本仓库后续研究的可复核上界和基线；它不表示 69E 是公开
纪录，更不表示已经证明全局最优。

## 依赖图结论

声明式依赖图从每条指令直接引用的点或对象反向追踪。分析得到：

- 最终圆 `target_transfer` 的依赖锥包含全部 69 个付费对象；
- 无论选择目标点对 `G, W2_minus` 还是 `G, W2_plus`，都仍需全部 69 个付费对象；
- 两个见证分支各自只会留下另一个最终交点的显式绑定未使用，但交点绑定为 0E，且该点仍会由自动闭包产生；
- 因而现有证书中没有完全脱离主路径、可以直接删除的付费支路。

这个结论的范围仅限证书声明的绑定关系。一个点可能同时是其他既有对象对的交点；
如果改用这种替代来源，依赖关系可能发生变化。因此“没有语法死支路”不等于“69
步都在数学上不可替代”，更不构成 69E 下界证明。

## 语义依赖超图结论

语义超图进一步精确枚举：

- 81 个具名交点在原绑定时刻都只有声明中的唯一对象对来源；
- 即使允许把免费绑定延迟到第一次付费使用之前，81 个点仍都没有第二种来源；
- 在 69E 全部完成后的几何状态中，共有 401 条点生产超边，78 个点出现多个来源；
- 69 个付费对象可以由具名点形成 694 条精确定义超边，每个对象都有多种具名点画法。

最终状态中的许多替代来源具有因果循环，例如先用点画出一条线，再想借这条线反过来
生成该点。验证器因此不直接把“最终关联”当作合法重绑，而是从初始状态做单调前向
闭包：对象或点必须先可用，才能参与下一次构造。

在这个模型中，允许 69 个付费对象任意重排，也允许使用全部 83 个具名点和上述所有
精确替代定义。逐一删除 69 个对象中的任意一个并保留其余全部对象，69 次试验都无法
到达目标。由于可构造闭包关于允许对象集合单调，这证明在**现有 69 个付费对象与 83
个具名点组成的有限宇宙内**，最小值严格为 69。

它仍不是原问题的 69E 下界：模型没有引入新的直线或圆，也没有把证书未命名的自动
交点纳入对象替代定义。真正的全局更短构造完全可能使用另一套几何对象。

## 完整未命名交点闭包结论

M257-6 消除了上一节的“未命名交点”限制。现有 65 条直线和 5 个圆（包括初始圆）
共有 2415 对对象。精确安排得到：

- 按对象对和交点分支计，共有 2706 个有限实交点事件；
- 合并重合坐标后得到 2287 个不同点；
- 其中 83 个已有名字，2204 个是此前未绑定的自动交点；
- 这些点为现有 69 个付费对象提供 133,558 种合法定义点组。

含圆对象的无关交点不强行写出高次数根式。验证器使用精确判别式确定 0、1、2 个实
分支，用两圆根轴和齐次交点合并落在既有直线或第三个圆上的分支；完全孤立的两个
分支保留为不同的抽象精确点。全过程不使用浮点容差。

在完整交点安排上，允许 69 个付费对象任意重排并使用任意合法交点重新定义。逐一
删除其中任意一个对象的 69 次试验仍全部失败。由单调性可知：在**固定这 69 个付费
对象、但开放它们之间全部有限实交点**的宇宙内，最小值仍严格为 69。

因此，继续降到 68E 或更低不能只靠“发现视频已经画出的对象之间还有一个被忽略的
交点”。新的更短构造必须引入至少一个当前 69E 对象集合之外的新直线或新圆。这个
结论依然不是所有尺规构造的 69E 全局下界。

## 具名点单新对象替换结论

M257-7 首次把对象宇宙向外扩展：删除两个现有付费对象，再加入一个由现有具名点
定义的新直线或新圆，净计数为 68E。为了在具名点闭包内做到完备且避免枚举无效
对象，只保留能够命中定义点之外至少一个具名点的候选：新直线至少通过 3 个具名点，
新圆在具名圆心之外至少通过 2 个同半径具名点。只通过定义点的新对象不能在这个闭包
中产生任何新具名点，故可严格剪枝。

枚举 83 个具名点的 91,881 个三点组后，得到 2,786 个共线三元组和 69 条至少通过
3 个具名点的直线几何，其中 65 条已经存在，只有 4 条是新直线。对每个具名圆心比较
其余 82 个点的半径，共有 275,643 对半径候选；严格实球区间先排除 274,718 对，
其余 925 对再做精确分圆域等值判断，最终得到 143 个新圆。实球区间只用于证明值不等；
凡区间仍可能相等者都回退到精确判定，不使用浮点容差。

搜索对全部 $\binom{69}{2}=2346$ 个删二组合与 147 个新对象逐一执行单调前向闭包，
共完成 344,862 次试验，未找到目标。由闭包关于保留旧对象集合的单调性，如果删除
三个或更多旧对象并加入同一个候选能够成功，那么补回旧对象直至只删除两个仍会成功；
因此本轮空结果同时排除了这个候选宇宙内“删至少两个、只加一个”的全部净降步方案。

结论的边界必须保留：M257-7 的点宇宙仍只有 83 个具名点，没有使用新对象与旧对象
产生的未命名交点，也没有同时加入两个或更多新对象。因此它是一个严格的有限宇宙
排除结果，不是 69E 的全局下界证明。

## 完整点候选前沿

M257-8 先不盲目物化数百万个新对象，而是对全部删二状态计算“画新对象以前”的完整
闭包。M257-6 的 2287 个安排点中，1813 个已有可直接恢复的精确坐标，另外 474 个
是为避免高次数开方而保留的抽象圆交点分支。全部 $\binom{69}{2}=2346$ 个删二状态
在加入新对象以前都没有命中目标；可用精确坐标点数从 2 到 1759 不等。

最大前沿来自删除最后两步 `BG0` 与 `target_transfer`：前 67 个付费对象仍全部可构造，
没有对象停滞；共有 2103 个点可用，其中 1759 个已有精确坐标，目标圆上已有 115 个
点。因此第一个长搜索分片固定保留前 67E，把一个新对象作为最后的第 68E。它只需
检查新对象与目标圆产生的点能否与已有点或彼此组成目标边，不需要猜测后续对象重排。

这个分片共有 $\binom{1759}{2}=1,546,161$ 个直线定义和
$1759\times1758=3,092,322$ 个有向圆定义，合计 4,638,483 个定义。搜索逐一定义
覆盖；同一几何对象即使有多个定义也会被重复检查，因此不会因去重规则漏掉候选。

M257-8 的第一个直接目标族已经穷尽：从 1759 个精确点中任取两点画直线，检查该
直线与目标圆的两个公共点是否彼此相差 $2\pi/257$。对一条目标圆心坐标系中的直线
$ax+by+d=0$，目标弦条件可写成

\[
d^2=(a^2+b^2)\,2\left(1+\cos\frac{2\pi}{257}\right).
\]

搜索先用 128 位严格实球计算等式两边的差；只要所得区间不含 0，就已经严格证明该
定义不是目标弦。区间仍含 0 时才回退到通用分圆域做精确等值判断。1,546,161 个定义
全部被实球区间排除，没有精确模糊项，也没有找到 68E 方案。人工构造的精确目标弦
正向测试会通过区间筛并通过精确判定，确认筛选器不会把真正等式排除。

直线的另一类事件也已穷尽：把已有 67 条目标弦载线旋转
$\pm2\pi/257$，检查候选直线是否经过相应的邻点。全部 1,546,161 个定义经过
210,277,896 次严格载线关系检查后均由实球区间排除，没有精确回退项，也没有候选。

圆搜索在一次扫描中同时检查两类事件：候选圆与目标圆的两个新公共点彼此相邻，或其中
一个新公共点邻接已有目标圆点。3,092,322 个有向圆定义共触发 423,647,298 次严格
关系检查；3,092,316 个定义直接由实球区间排除，余下 6 个进入精确判定。它们分别是
以 `C` 为圆心、经过 `B`、`M1`、`G`、`F`、`q_c0_left`、`q_c0_right` 的定义，实际
都只是重新画目标圆 `c0`，不会产生新交点；最终仍无候选。

这两类事件在本分片中是完备的：加入候选以前尚无目标边，而候选又是最后一个付费对象，
所以首次出现的目标边必须含至少一个候选与目标圆的新交点；另一端只能是另一个新交点，
或加入候选以前已有的目标圆点。由此，直线和圆的三份空结果共同排除了这个精确点分片
中的全部单个最终对象方案。

第二阶段补齐了上述精确点分片的最后边界。最大前沿的另外 344 个可用点由 340 个
直线—圆残余交点和 4 个圆—圆残余交点组成，分属 186 个生产者组。它们不必强行写成
高次数根式：由生产对象直接计算 128 位严格实球包围即可。审计确认全部 2103 个点的
包围两两可分，且对既有对象的 4338 条关联残差都包含 0，因此这些球可以安全用于严格
否定筛选；真正包含 0 的候选关系仍会保留为未决，不会被误删。

扩展后的直线宇宙有 $\binom{2103}{2}=2,210,253$ 个定义。目标弦检查全部直接排除；
邻接已有点检查执行 300,594,408 次严格载线关系判断，同样全部排除，二者均无未决项。
圆宇宙有 $2103\times2102=4,420,506$ 个有向定义：4,420,391 个由严格区间排除，
余下 115 个都能从安排关联表精确识别为“以 `C` 为圆心、经过已有目标圆点”，也就是
重新画 `c0`，不会产生新交点。圆搜索亦无未决项。

因此最大前沿中的 6,630,759 个直线或圆定义已经全部覆盖，且两个可能的首次目标事件
都已排除。这里的“全部点”包括该状态下可用的 344 个抽象残余点；完整安排中其余抽象
点在删除最后两步后尚不可用，所以不能定义第 68E。

结论仍不是全局 69E 下界。本轮只覆盖删除第 68、69 步的最大前沿，还没有覆盖其余
2345 个删二状态中“新对象先解锁停滞旧对象”的可能性，也没有允许同时加入两个或更多
新对象。

## 几何—代数统一搜索主线

局部替换搜索已经暴露出一个更根本的问题：视频的代数分解和真实 E 成本此前只在
最终证书处相遇。代数层知道需要哪些根和周期量，却不知道已有几何痕迹；几何层能够
精确计数和闭包，却不知道换一条代数分解是否能整体节省对象。

新主线由 [GEOMETRY-ALGEBRA-IR.md](GEOMETRY-ALGEBRA-IR.md) 定义。成本不再错误地
附着到孤立的加、乘、开方操作，而定义为程序相对于输入几何状态实际新增的不同直线和
圆数量。已有对象永久保留，一笔作图产生的全部有限实交点免费加入状态，同一个对象的
多种定义也只按其精确几何实体计费一次。

第一份 [geometry-algebra-baseline-69e.json](geometry-algebra-baseline-69e.json) 已经
可以从证书重新生成并通过 Schema 验证。它精确记录：

- 69 个付费对象在固定顺序下的定义点及其最早出生时刻；
- 2287 个完整安排点中，除初始 `B`、`C` 外的 2285 个点分别在哪一笔后免费出现；
- 17 组由表达式树描述的二次根对关系及其精确分圆域核验；
- 编码圆上的周期量、`V2.x=2/g_0` 和最终根轴 `x=g_0` 共 42 个几何表示；其中不仅
  精确识别出视频未赋代数名的 `K2=e_1+e_{23}` 与 `R2=e_{15}+e_{25}`，还把每条
  二次载线与编码圆产生但未命名的另一个根全部纳入状态；
- 138 次定义点引用只涉及 81 个不同点，明确保留了痕迹复用，而不是把每次使用重复计费。

当前结果是可执行的 69E 成本基线，不是优化结果。下一步是在这份 IR 上建立首批几何
gadget：每个 gadget 声明前置表示和产出表示，但边际 E 成本必须通过状态执行得到。
随后才能对周期分裂顺序和辅助量做等价改写，并用“更强表示、更少对象”的状态支配
关系剪枝。

基线已先按实际步骤切出 11 个观察宏，恰好覆盖 69 个对象。最适合作为第一个编译
实验的是两个对称尾部：47–55E 用 9E 得到 `E0、K2、F0`，56–64E 也用 9E 得到
`E24、R2、F56`。这里既有清楚的代数同构，又有可能共享或改写的辅助量；先让编译器
重现这两个宏的上下文成本，再尝试改变周期配对，比继续无结构地扩大数百万点对搜索
更容易判断新方法是否真的有效。

进一步核对表明，17 条二次载线每条都会免费产生一对根。视频证书只给后续使用的根
命名，但另外 11 个共轭根同样已经位于完整交点闭包中；现在它们都拥有稳定的安排点
ID 和精确代数表示。例如取得 `E0` 的同一笔同时得到 `E16`，取得 `F0` 的同一笔同时
得到 `F32`，最后取得 `G0` 的同一笔也同时得到 `G64`。这正是统一状态模型相对于
“逐个计算代数量”模型的首个实质收益：这些根后续可直接复用，成本为 0E。

[geometry-gadgets-tail-69e.json](geometry-gadgets-tail-69e.json) 已把两个尾部从观察宏
推进为可执行 gadget。每个片段包含 9 条付费直线和 9 个显式交点绑定；低尾部在其
46E 前缀状态中产生 435 个完整免费闭包点，高尾部在 55E 前缀状态中产生 500 个。
两者的共同几何边界是点 `A、B、D、E、G` 和对象 `a、b、c`，但各自新增的 18 条
直线没有重合。因而仅仅交换或交错现有步骤不会降步；真正的联合优化必须改变至少一条
代数配对或几何载线，使两个分支共享新的付费对象或直接联合产出所需量。

第一类联合改写已经完成有限穷举。两个 gadget 各自实际产出 6 个根，因此共有 36 个
跨分支根对。对每一对都精确检查：连接两根的直线是否经过至少两个 46E 具名点，以及
是否存在由“具名圆心 + 具名圆上点”定义并同时经过两根的圆。59 个可用具名点中没有
任何直线定义；圆的定义语法共命中 1080 次，但每次都是以 `A` 为圆心、经过编码圆上
既有点而重画 `c`。按精确几何实体去重后，新直线、新圆和有效根对均为 0。

完整点分片现已完成。46E 免费闭包共有 989 个可用点，其中 763 个已有精确坐标，
226 个以严格实球和交点生产者保留。对 36 条跨根对直线共检查 35,604 个“目标线—
可用点”关联，严格实球已经全部排除，因而连定义目标线所需的第一个可用点都不存在。

圆分片没有盲枚举 989 平方个“圆心—圆上点”定义，而先使用必要条件：同时经过一对
根的圆，其圆心必在该根对的垂直平分线上。相同的 35,604 次审计只有 36 次命中，
每个根对都只命中圆心 `A`；由 `A` 和该根对确定的圆精确等于已有编码圆 `c`。因此
不存在需要继续检查等半径圆上点的新圆心，完整点层的一笔直线和一笔圆捷径均已排除。

两对象目标直线桥接分片也已完成。由于目标直线上原先没有可用点，第一笔若为直线，
至多只能与目标直线产生一个交点，不足以定义第二笔目标直线；因此第一笔只需穷尽圆。
对每条目标直线，搜索器先求它与 47 个既有对象的 49 或 51 个不同桥接点，再审计全部
989 个可用圆心到任意两桥接点是否等距。逻辑空间共 44,611,812 项，128 位严格实球
只留下 136 项；在目标直线参数上用二次多项式消元后，136 项全部精确成立。

这些等距关系没有形成新圆：它们分别精确等于已有 `c0`、`c`、`q` 各 36 次，以及
`c_M1L1` 28 次。按几何实体去重后，新首笔圆、2E 桥接程序和有效根对仍全为 0。
搜索由 8 个 Linux `fork` 工作进程共享父进程的 989 点状态，实测约占 9 个 CPU 核、
1.3 GiB 内存。这仍不证明两个尾部的 18E 最优。

新的 [synthesis-live-slice-68e.json](synthesis-live-slice-68e.json) 已把目标反向切到真正
被消费的代数输出。当前分解中的 17 个二次关系全部活跃，说明不能删去一整层关系；但
34 个二次根中只有 23 个被后续关系消费，另外 11 个只是解活跃根对时免费出现的共轭根。
宏原先列出的全部产物因此不再被误当作合成器必须交付的接口。

对 47–64E 联合尾部而言，`E0、K2、E24、R2` 是片段内部临时量，六个共轭根只是免费
副产物；后续 65–69E 真正需要的外部输出只有 `F0` 和 `F56`。声明式几何反向切片同时
确认，原程序的 18 条尾部直线仍全部服务于这两个点，没有可直接删除的死对象。因此
下一阶段冻结为明确的生成任务：从完整 46E 前缀状态出发，用至多 17 个不同新对象精确
物化 `F0、F56`，再复用原来的 5E 后缀，从而得到可验证的 68E 构造。两对象第二笔圆的
排除审计仍可保留为辅助分片，但不再优先于直接合成。

[tail-quadratic-chord-ir-68e.json](tail-quadratic-chord-ir-68e.json) 进一步把每个活跃尾部
二次关系编译成真实直线。若编码圆参数的两根满足

\[
t^2-st+p=0,
\]

则两根的弦线精确为

\[
-sx+(p-1)y+(p+1)=0.
\]

它与基线 `b:y=-1`、纵轴 `a:x=0` 的规范截点分别是
`(2/s,-1)` 与 `(0,(p+1)/(1-p))`。生成器已在分圆域中核对六条公式线分别等于
`H2Y1、AJ2、L2I2、M2O2、AQ2、S2P2`，并核对每条线上的两个精确根。这就把“解二次
方程”落实成了“物化两个定位点，再画一条根载线”的可计价指令，而不是给开平方指定
一个虚构固定单价。

46E 的 989 点状态在这六条线上没有隐藏的直接捷径：`AJ2、AQ2` 因根积为 `-1` 而都
经过已有点 `A`，其余四条没有任何前缀点；没有一条线已经拥有两个可用定位点。下一步
因此转向定位点生产程序：枚举一条新对象能否通过与既有轴、圆和载线相交，同时生成
两项或更多后续载线所需的定位点，从共享前处理而非删除根载线本身争取 1E。

## 46E 共享定位对象的当前结论

共享直线分片已经完成。六条根载线两两配对，它们与 46E 前缀直线产生
`43、42、43、43、42、43` 个桥接点。15 个任务对一共给出 27,306 个桥接点对；
除 `AJ2、AQ2` 共有点 `A` 的一个重合项外，其余 27,305 项均构成候选直线。
26,394,189 次 128 位严格实球关联检查留下 1,696 次精确坐标回退；其中 643 个
可画出现全部精确等于已有前缀直线。因此，在“桥接点由根载线与前缀直线产生”
这一完整模板内，新共享定位直线为 0。这不覆盖只能由前缀圆产生的桥接点。

共享圆分片尚未完成。它将包含“只有圆见证”的分支在内的全部桥接点加入，并穷尽
“46E 可用圆心 + 46E 可用圆上点”定义的一笔圆。任务对按六条根载线的固定顺序
`H2Y1、AJ2、L2I2、M2O2、AQ2、S2P2` 字典式排列。前 7 对的严格半径幸存数依次为
`16、16、12、16、16、16、12`，合计 104；精确可画判定没有产生任何新圆。这 7 对
可以排除。

第 8 对是 `AJ2` 与 `AQ2`。它留下了至少一个圆心为抽象圆—圆交点的严格半径
候选。当前实现调用 `_exact_available_point` 物化该圆心，随后由 `_prefer_main_field`
尝试把 `QQbar` 坐标降到 `CyclotomicField(257)`。PARI 的 `rnfequation` 在 1 GiB 和
2 GiB 栈上均溢出；6 GiB 栈运行约 3 小时 7 分钟、容器实际内存稳定在约
5.29 GiB 时仍未返回，因边际价值过低而主动终止。

这次中止只证明“强制降回主分圆域”是不合适的实现路径，不是第 8 对的排除证明，
更不是 15 对的完整圆搜索结论。下一版必须在重精确化之前落盘“任务对、圆心生产对象、
分支实球、两个桥接点”，然后直接使用生产圆方程和目标线参数二次式做抽象消元。
只有消元确认为可画新圆时，才应当物化具体坐标并进入 17E 联合尾部调度。

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

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_dependency_graph.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_semantic_dependencies.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_full_intersection_closure.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_69e_named_new_object_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_full_point_candidate_frontier.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_final_pair_line_chord_search.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_final_pair_line_adjacent_search.py --chunk-size 1000

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_final_pair_circle_search.py --chunk-size 1000

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_68e_final_pair_direct_search_summary.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_68e_residual_point_ball_audit.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_all_point_line_chord_search.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_all_point_line_adjacent_search.py

docker exec `
  -e PYTHONPATH=/workspace/sage:/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/run_68e_all_point_circle_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_68e_all_point_direct_search_summary.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_geometry_algebra_ir.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_69e_tail_gadgets.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_46e_tail_cross_pair_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_46e_tail_cross_pair_all_point_line_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_46e_tail_cross_pair_all_point_circle_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_46e_tail_cross_pair_two_object_line_bridge_search.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_68e_synthesis_live_slice.py

docker exec `
  -e PYTHONPATH=/workspace/regular-257 `
  boring_wing `
  sage -python regular-257/build_68e_tail_quadratic_chord_ir.py
```

完整交点闭包需要对 2080 个直线对做高次分圆域精确运算，当前机器上重算约需 3–4
分钟。生成器会输出阶段进度。

M257-7 搜索可以安全暂停和恢复。默认每扫描 2500 个三点组原子写入一次
`regular-257/tmp/m257-7-named-search-checkpoint.json`；候选枚举完成后保存完整候选
列表，删二搜索每 100 对保存一次游标和累计结果。该文件位于 Git 忽略目录，不污染
正式产物。再次运行同一命令会核对输入哈希和算法版本后自动续跑；单实例锁会拒绝两个
进程同时写同一检查点。若只想运行一个扫描块，可附加 `--max-chunks 1`。

M257-8 直线目标弦搜索把 1759 个点的严格实球缓存到 Git 忽略的
`regular-257/tmp/m257-8-final-pair-point-balls.json`，定义扫描游标另存为
`m257-8-final-pair-line-chord.json`。缓存每 10 个点保存，定义默认每 5000 个保存；
同样支持 `--max-chunks 1` 和单实例锁。

直线邻接和圆搜索复用同一实球缓存，分别把稳定的 1000 定义分片保存到
`m257-8-final-pair-line-adjacent-parallel.json` 和
`m257-8-final-pair-circle-parallel.json`。默认启用 8 个 Linux `fork` 工作进程；每个
完成分片都会原子写入检查点，中断后以相同 `--chunk-size 1000` 重启即可继续，也可用
`--max-chunks` 限制本轮新处理的分片数。单实例锁会阻止两个进程写入同一个检查点。

全部点阶段把 2103 个点的包围缓存到
`regular-257/tmp/m257-8-final-pair-all-point-balls.json`。目标弦、直线邻接和圆搜索的
检查点分别是 `m257-8-all-point-line-chord-parallel.json`、
`m257-8-all-point-line-adjacent-parallel.json` 与
`m257-8-all-point-circle-parallel.json`；三者同样默认使用 8 个工作进程、每块 1000
个定义，并支持 `--max-chunks` 和断点恢复。

验证器使用 `CyclotomicField(257)` 处理主路径，只在 `sqrt(3)` 和最终正弦坐标
需要时提升到 `UniversalCyclotomicField`。闭包审计把目标弦载线旋转
$\pm2\pi/257$ 后做精确齐次相交判定。整个过程不使用浮点容差或 `AA` 根隔离。

新版证书验证器的关键输出还应包含：

```text
automatic_closure_first_target_e_move=69
duplicate_draws=0
```

运行本目录测试：

```powershell
docker exec `
  -e PYTHONPATH=/workspace/sage `
  boring_wing `
  sage -python -m unittest discover -s regular-257 -p "test_*.py" -v
```

## 后续工作

- 以 [synthesis-live-slice-68e.json](synthesis-live-slice-68e.json) 为固定接口，先生成联合尾部的等价代数表达与替代根配对；
- 以 [tail-quadratic-chord-ir-68e.json](tail-quadratic-chord-ir-68e.json) 的六条根载线为任务，优先搜索一笔多定位点的共享前处理；
- 把候选编译成从精确 46E 状态开始的真实直线/圆程序，只保留能在至多 17E 内产生 `F0、F56` 的状态；
- 用“已有表示集合 + 几何状态 + 上下文 E 成本”的支配关系，以及 Beam/A* 启发式剪掉不可能优于 18E 的双尾状态；
- 把“第一笔产生新圆心、第二笔圆跨两个尾部根”的审计保留为原语模板扩展，而非当前首要路线；
- 保留其余 2345 个删二状态和多新对象搜索作为原语层验证手段，不再把它们作为唯一主线；
- 独立核对 69E 的文献优先权与是否存在更短公开构造。
