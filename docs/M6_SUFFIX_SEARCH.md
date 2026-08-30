# E12 起点的并行联合后缀搜索

本文记录在 19 E 已验证上界基础上，对固定前 12 E 精确前缀发起的 6 E
联合后缀搜索。目标是在不预设 `Y`、`M0_4`、`H4_8` 等传统中间量的条件下，
直接寻找总分不超过 18 E 的完整构造。

## 1. 证据边界

该实验属于 `heuristic_nonproof`：候选浮点预筛、beam 截断、生成层级门和
运行时超时都会永久删除分支。未命中只能说明指定参数下没有保留下来并完成
精确计算的候选，不能推出 18 E 不存在，也不能支持 19 E 全局最优声明。

任何命中必须重新生成完整证书，并由独立 Sage verifier 从磁盘精确重放；
浮点残差、worker 返回值和搜索器自身的目标判断都不能替代 verifier。

## 2. 为什么从 E12 开始

19 E 构造在第 12 E 已得到 `H0_4` 与 `H1_4`。现有后缀还需 7 E，分别用于：

1. 得到 `Y`；
2. 定位最后一个 Carlyle 圆心；
3. 产生最后一对根；
4. 作经过目标的辅助对象。

把 E12 状态作为搜索根并限制总分为 18，等价于寻找一个至多 6 E 的联合替代，
同时允许完全绕过上述命名中间量。精确前缀通过正式构造程序重放，再按搜索器的
完整自动交点闭包语义重建；当前根状态含 69 个点和 7,038 个原始点对操作。

## 3. 并行搜索结构

`ParallelHeuristicBeamSearch` 使用进程级并行而非线程：

- 父进程对点对做浮点评分和数值规范键去重，不构造高次数精确对象；
- 每个候选由独立 worker 执行 Sage `AA` 精确展开、目标检测和状态评分；
- worker 只返回候选定义、评分和命中标志，不传输完整 `AA` 子状态；
- 每层只在父进程重建最终保留的少量状态；
- 单个父状态设有墙钟时间上限，未完成候选计入 `candidate_timeouts`；
- 点的生成依赖层级在交点产生时记录，作为 O(1) 的复杂度代理，不进入数学
  状态相等、证书或 verifier 结论。

候选多样化配置把每个 8 项批次分为：4 个目标残差最小候选、2 个低层级直线、
2 个低层级圆。这样可以避免全部 worker 同时卡在同一类高次数近目标对象上。

## 4. 复现命令

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python sage/experiments/search_detemple_suffix.py `
  --max-total-score 18 `
  --beam-width 4 `
  --candidate-width 8 `
  --workers 8 `
  --state-timeout-seconds 8 `
  --max-input-level 8 `
  --candidate-strategy diverse `
  --summary-output benchmarks/e12-suffix-search.json
```

实验逐层输出点数、最大生成层级、原始点对数、通过层级门的点对数、精确候选数
和超时数。退出状态 `heuristic_limit` 明确表示启发式范围结束，而不是穷尽。

## 5. 首轮结果

固定 SageMath 10.7 镜像上的三次完整 6 E 搜索如下：

| 候选策略 | 墙钟秒 | 完成评分 | 超时 | 到达 E18 | 命中 18E |
|---|---:|---:|---:|---|---|
| 仅目标残差 | 209.50 | 46 | 122 | 是 | 否 |
| 目标 + 低层级线圆 | 183.06 | 100 | 68 | 是 | 否 |
| 目标 + 低层级线圆（beam 8 / candidate 12） | 455.84 | 298 | 194 | 是 | 否 |

多样化后完成评分的候选增加到两倍以上，墙钟时间下降约 12.6%，并稳定维持
4 个状态到 E18。运行期间曾观察到约 700% Docker CPU，占用约 7 个逻辑核心；
GPU 未参与 Sage `AA` 计算。

更宽的第三次搜索扩展 41 个父状态，对 1,060,449 个原始操作执行浮点预筛，
精确启动 492 个候选并完成其中 298 个，最终保留 8 个 E18 状态，仍未命中。
完整环境、参数和计时见
[`e12-suffix-search-wide-sage-10.7.json`](../benchmarks/e12-suffix-search-wide-sage-10.7.json)，
其格式由
[`suffix-search-summary-v1.schema.json`](../schemas/suffix-search-summary-v1.schema.json)
约束。三次负结果均不能作为 18 E 不存在的证据。

## 6. 确定性 restart 矩阵

为了让不同结构窗口同时使用 CPU，新增了四配置调度器：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python sage/experiments/search_detemple_suffix_matrix.py
```

每个 run 使用 4 个精确 worker，最多同时运行 4 个 run，总容量 16 worker。
固定配置见
[`e12-suffix-restart-matrix-v1.json`](../sage/experiments/configs/e12-suffix-restart-matrix-v1.json)。
正式结果如下：

| Run | 层级门 | 候选策略 | 状态启发式 | 墙钟秒 | 完成评分 | 超时 | 命中 |
|---|---:|---|---|---:|---:|---:|---|
| level6-diverse-one-move | 6 | 多样化 | one-move | 92.42 | 239 | 9 | 否 |
| level10-diverse-one-move | 10 | 多样化 | one-move | 102.61 | 22 | 82 | 否 |
| level8-target-one-move | 8 | 仅目标残差 | one-move | 357.32 | 88 | 160 | 否 |
| level8-diverse-regular | 8 | 多样化 | regular | 296.58 | 83 | 165 | 否 |

矩阵总墙钟为 359.89 秒，各 run 耗时之和为 848.93 秒，墙钟缩短约 2.36 倍；
运行中观察到最高约 1155% Docker CPU。四个 run 累计预筛 2,415,174 个操作，
精确启动 848 个候选，完成评分 432 个，超时 416 个，未命中 18 E。
总汇总见
[`e12-suffix-restart-matrix-sage-10.7.json`](../benchmarks/e12-suffix-restart-matrix-sage-10.7.json)，
四个子结果位于同名目录。

该对照表明层级门 6 的吞吐显著更好：它完成 239 个候选且仅超时 9 个；层级门
放宽到 10 后，高代数复杂度候选占用大部分预算，只完成 22 个。仅按目标残差
选候选以及使用普通状态启发式也更容易进入昂贵分支。后续扩大搜索应优先围绕
低层级、多样化、one-move 组合，而不是无条件提高层级门。

## 7. 下一步

当前结果说明并行执行框架已经可用，但 beam 宽度 4、每状态 8 个候选仍然很窄。
后续应按以下顺序扩大覆盖：

1. 在层级门 5、6、7 附近增加候选复杂度预测，优先跳过大概率超时的操作；
2. 为矩阵准备多于并发槽数的配置池，减少长短 run 不均产生的尾部空闲；
3. 对高吞吐配置逐步增加 `beam_width`，同时改变线/圆配额以扩大结构覆盖；
4. 一旦命中，立即导出完整证书并调用独立 verifier；
5. 若多个结构化窗口均未命中，只记录对应窗口内的负结果，不升级为全局下界。
