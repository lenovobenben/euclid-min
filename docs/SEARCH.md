# M4 基础搜索器

本文描述 `euclid_min search` 的当前实现边界。M4 建立可审计的小深度搜索闭环，
M5 在其上增加阶段计时和明确标记为非证明模式的目标相关 beam search。

## 1. 搜索状态

搜索器使用正式模型中的完整数学状态

\[
S=(P,L,C).
\]

与 verifier 的惰性闭包不同，搜索状态通过 `GeometryState` 显式物化每个新对象
与全部既有对象的有限实交点。原因是下一步候选必须从完整点集生成。两种实现的
数学语义相同，但承担不同职责：搜索器不能漏候选，verifier 不必物化永远不会
被证书引用的高次数交点。

## 2. 候选生成

对精确排序后的不同点集生成：

```text
Line(Pi, Pj),                  i < j
Circle(center=Pi, through=Pj), i != j
```

排除已有对象。同一条新直线或同一个新圆可能由多组点参数化；它们成本相同，
加入状态后得到完全相同的闭包，因此只保留确定性顺序中的第一个代表。当前没有
使用“本步没有新点”、数值距离、镜像对称或其他启发式删除分支。

## 3. 状态索引

`state_fingerprint` 使用几何对象的数值投影生成 SHA-256 分桶摘要。它只减少候选
比较范围，不是数学身份：摘要命中后，索引仍忽略插入顺序并逐项精确比较
\((P,L,C)\)。摘要碰撞不会导致状态被错误合并。

基础模式按 E-score 做确定性广度优先展开。未触发 `max_states` 时，对给定
`max_score` 的基础操作空间完备；触发限制时状态为 `state_limit`，不得解释为
深度已经穷尽。

M5 的 `beam` 模式按目标关联残差、最近点距离和点数信号排序，每层只保留
`beam_width` 个状态。它会永久删除分支，始终属于 `heuristic_nonproof`。

## 4. Provenance 与证书

搜索路径保存每项基础操作的两个精确输入点。导出时从历史对象对中确定性寻找
这些点的来源，并插入零成本 `intersect` 绑定，再生成
`euclid-min-certificate/v1`。只有搜索状态已经命中当前正十七边形目标时才允许
生成正式证书。

CLI 对候选证书执行独立的 `verify_files` 重放；只有验证成功后才写入 `--output`。
搜索器自己的目标检测或日志不能替代 verifier。

## 5. Checkpoint

在 BFS 模式中，状态软上限只在一个节点的候选全部展开后生效，因而 checkpoint 保存的是完整
frontier，不会遗漏半个节点。文件使用
`euclid-min-search-checkpoint/v1`，受
`schemas/search-checkpoint-v1.schema.json` 约束，并固定 profile ID 和摘要。

每个 frontier 节点保存可重放 program。恢复时程序先由重放器还原为搜索步骤，
再用完整闭包重建状态。checkpoint 不把 AA 的内部表示或浮点坐标当作权威数据。
Beam 模式当前不支持 checkpoint。

## 6. CLI

小深度穷尽示例：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m euclid_min search `
  --profile profiles/regular-17-e-fixed-v1.yaml `
  --max-score 1 `
  --json
```

保存与恢复：

```text
euclid-min search --profile <profile> --max-score 3 \
  --max-states 100 --checkpoint search.json

euclid-min search --profile <profile> --max-score 3 \
  --max-states 100 --resume search.json --checkpoint search-next.json
```

退出码：

| 退出码 | 含义 |
|---:|---|
| 0 | 找到候选且独立 verifier 通过 |
| 1 | 在给定 `max_score` 内穷尽，未命中 |
| 2 | 参数、profile、checkpoint、写入或验证错误 |
| 3 | 达到状态软上限，搜索可继续 |
| 4 | 启发式保留范围已用尽，未命中；不代表穷尽 |

## 7. 当前限制

- 完整闭包和候选数量增长极快，当前实现只承诺小深度可审计性；
- checkpoint 以可移植和可核对为先，不追求紧凑；
- 统计是单次运行统计，恢复后不会伪装成累计完备证明；
- 尚无代数次数/子域信号、随机重启、严格完备的镜像归约、Go 调度器或 proof mode；
- BFS 没有触发 `state_limit` 时只能说明指定深度被当前规则穷尽，不能直接推出与当前 19 E 上界相匹配的下界；beam 永远不提供穷尽结论。

## 8. E12 并行联合后缀实验

为继续攻击 18 E，上界搜索已经支持从带分数的精确中间节点启动，并新增专用的
进程级 `ParallelHeuristicBeamSearch`。它在 worker 内执行 Sage 精确展开，只向
父进程返回路径摘要；候选预筛使用数值规范键、生成依赖层级、目标残差和线圆
配额。运行时超时及所有被删除分支均被显式统计。

该模式严格属于 `heuristic_nonproof`，不改变本页第 3 节对完备搜索和 lower bound
的要求。固定 E12 前缀的首轮六层结果、复现命令和性能数据见
[`M6_SUFFIX_SEARCH.md`](M6_SUFFIX_SEARCH.md)。

多个确定性配置可由 `search_detemple_suffix_matrix.py` 作为独立子进程并行运行；
每个子进程内部再使用自己的 Sage 精确 worker。配置、子结果和总汇总均受 JSON
Schema 约束。当前四配置矩阵的总容量为 16 worker，实测峰值约 1155% Docker
CPU；它扩大的是启发式结构覆盖，仍不具备穷尽性。

可选的 `complexity_order` 根据搜索路径同步维护的有界 provenance 复杂度安排
已选候选的 worker 提交顺序。该值不读取 `AA` 最小多项式，不进入状态相等或
剪枝；当前 A/B 实验未证明它单独改善吞吐，主要性能信号仍来自生成层级门。

最终排名审计显示：宽度不超过 32 的当前预筛不会保留已知 19 E 后缀中的任何
一步。随后两个专用局部窗口也未找到 18 E。该结果触发了预先设定的停止条件；
除非出现新的结构假设或可校准启发式，不再继续扩大本搜索器的非证明 beam。

M5 的固定 profiling 结果、启发式公式和解释边界见 `docs/M5_PROFILING.md`。
