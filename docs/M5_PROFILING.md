# M5 搜索 Profiling 与启发式边界

## 1. 结论

M5 的固定 SageMath 10.7 profile 表明，当前小深度搜索的主要成本是构造子状态时
执行的精确求交、自动闭包和 AA 去重。Python 队列与调度不是可见热点，因此目前
没有引入 Go 调度层的证据。

目标相关 beam search 已能把每层保留 frontier 限制在固定宽度，但它主动删除
分支，只能用于寻找 upper bound。它的 `heuristic_limit` 不能解释为指定深度已
穷尽，更不能支持 lower bound 或全局最优声明。

## 2. 固定环境

```text
SageMath 10.7
Python 3.12.5
sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528
profile: regular-17-e-fixed-v1
```

实验脚本在计时前预热两个正十七边形目标 AA 常数，避免把一次性的单位根构造
混入每个搜索 case。完整机器相关结果位于
`benchmarks/m5-search-profile-sage-10.7.json`，由
`schemas/search-profile-v1.schema.json` 约束。

复现命令：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python sage/experiments/profile_search.py
```

## 3. 结果摘要

本次固定运行的时间只用于定位热点，不是跨机器性能承诺。

| Case | 状态 | 展开 | 候选 | 接受 | 最大 frontier | 总耗时 |
|---|---|---:|---:|---:|---:|---:|
| BFS，深度 2 | `exhausted` | 3 | 16 | 16 | 13 | 0.167 s |
| BFS，深度 3，状态上限 100 | `state_limit` | 9 | 110 | 101 | 92 | 0.702 s |
| Beam，深度 3，宽度 8 | `heuristic_limit` | 11 | 142 | 126 | 8 | 0.923 s |

深度 3 BFS 样本中：

- 子状态展开约 0.618 s，占总时间约 88.1%；
- 状态摘要和精确索引约 0.058 s，占约 8.2%；
- 候选生成约 0.023 s，占约 3.2%；
- 精确目标判断约 0.002 s。

Beam 样本中，子状态展开仍占约 86.3%，启发式评分约占 2.1%。它评估了 125 个
状态，按宽度删除 107 个，并把保留 frontier 限制为 8。不同 case 展开的状态数
不同，所以不能用总耗时直接声称 beam 比 BFS 更快或更慢。

## 4. 启发式定义

当前评分同时考虑两个镜像目标。对每个状态计算：

1. 已知点到任一目标的最小浮点平方距离；
2. 对每个目标，取两个最接近“通过该目标”的已构造对象，其归一化关联残差之和；
3. 在前两项相同时，以较多已知点作为确定性次级信号。

线的残差为点到线的数值距离，圆的残差为归一化圆方程残差。评分越小越优。
这些浮点量只参与排序和 beam 保留，绝不参与：

- 点、线或圆的数学相等；
- 操作合法性；
- 状态精确合并；
- 目标命中；
- 证书验证。

目标在每个子状态生成后先做精确判断，再进行启发式评分和剪枝。搜索器一旦报告
命中，CLI 仍会生成证书并调用独立 verifier 重放。

## 5. 两种搜索模式

| 模式 | CLI | 分支删除 | 未命中状态 | 可用于有界穷尽 |
|---|---|---|---|---|
| 确定性 BFS | `--strategy bfs` | 仅精确相同状态 | `exhausted` 或 `state_limit` | 未触发状态上限时可以 |
| 目标相关 Beam | `--strategy beam` | 每层超出 `beam_width` 的状态 | `heuristic_limit` 或 `state_limit` | 不可以 |

Beam 示例：

```text
sage -python -m euclid_min search \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --max-score 6 \
  --max-states 5000 \
  --strategy beam \
  --beam-width 32 \
  --json
```

Beam checkpoint 尚未实现；M4 的 frontier checkpoint 继续只支持 BFS。退出码 4
表示启发式保留范围已用尽但没有命中。

## 6. 后续优化顺序

根据当前证据，下一轮应优先：

1. 避免为每个子节点复制和重新比较整个几何状态；
2. 为点和对象增加“数值桶 + 精确确认”的局部索引；
3. 缓存对象对求交和候选对象规范化结果；
4. 再 profile 更深的 beam 运行，观察内存与 checkpoint 成本；
5. 只有 Python 队列、并发调度或序列化成为主瓶颈时再评估 Go。

代数次数、子域信号、随机重启和镜像归约尚未进入默认搜索。尤其是镜像合并，
在作为完备剪枝前仍需单独证明并测试。
