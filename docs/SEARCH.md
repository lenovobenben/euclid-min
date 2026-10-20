# M4 基础搜索器

本文描述 `euclid_min search` 的当前实现边界。M4 建立可审计的小深度搜索闭环，
M5 在其上增加阶段计时和明确标记为非证明模式的目标相关 beam search。

QQ-GGB 的独立局部搜索脚本、前缀限制、完成覆盖与未完成任务另见 [12 E 搜索记录](../qq-ggb/search-hour-2026-09-11.md)。那些负结果不扩大本工具的全局下界。

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
- 尚无代数次数/子域信号、Go 调度器或可完备排除 6–11 E 的全局 proof mode；M7 小深度入口已使用严格横轴镜像归约；
- BFS 没有触发 `state_limit` 时只能说明指定深度被当前规则穷尽，不能直接推出与当前 12 E 上界相匹配的下界；beam 永远不提供穷尽结论。

## 8. 小深度 Proof Mode

`euclid-min prove` 与普通 `search` 的 `bfs` 共享正式数学状态，但不接受
`max_states`、checkpoint、超时或任何启发式候选删除。v1 按 E-score 完整分层；
v2 先完整枚举到 3 E，再对剩余两步作有限 AND/OR 义务展开。

`euclid-min check-proof` 不信任这些计数，而使用不含数值摘要的线性精确候选去重
和状态索引从头重放。P1 已把关于横轴互为镜像的状态精确合并，并增加目标依赖
祖先审计；P2 又利用目标始终位于免费单位圆这一事实，只在最后一层展开精确经过
目标的候选；P3a 把具体见证转换为按自动闭包最早可用分数切分的反向 DAG；
P3b 又对有限前向状态完整展开两步 AND/OR 目标义务；P3c 使用线性前向枚举和
逐对象 `contains` 入射检查独立重放全部 5 E 计数。当前固定证明严格排除到 5 E，
仍未穷尽 6–11 E。全局最优性证明现标记为待完成并暂停，只有取得显著压缩
6–11 E 空间的新理论归约后才恢复。规范、命令和可信边界见
`docs/M7_PROOF_MODE.md`。
