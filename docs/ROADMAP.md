# Euclid-Min 实施路线

本路线把研究设计拆成可以验收的工程里程碑。顺序原则是：先固定语义和验证能力，再建立可信上界，最后扩大搜索规模。

## 当前进度

| 里程碑 | 状态 |
|---|---|
| M0：规范闭环 | 已完成 |
| M1：Sage 精确几何内核 | 已完成 |
| M2：验证闭环 | 已完成 |
| M3：首个可信 baseline | 已完成 |
| M4：基础搜索 | 已完成 |
| M5：启发式搜索与 profiling | 已完成 |
| M6：新的已验证上界 | 已完成 |
| M7：Proof Mode（长期可选） | 下一阶段 |

## M0：规范闭环

### 交付物

- `docs/FORMAL_MODEL.md`；
- `docs/METRICS.md`；
- `docs/CERTIFICATE_FORMAT.md`；
- `profiles/regular-17-e-fixed-v1.yaml`；
- profile 和 certificate JSON Schema；
- 仓库 README 和规范导航。

### 验收条件

- 初始对象、操作、交点闭包、退化情况、目标和计分没有已知歧义；
- 两个实现者只阅读规范即可对同一证书得出相同结论；
- Schema 可以拒绝结构错误的 profile 和证书；
- profile 与构造内容哈希算法已经固定。

### 暂不包含

- 正十七边形步数纪录；
- 文献 baseline 数字；
- 搜索算法；
- 全局最优声明。

## M1：Sage 精确几何内核

### 实现顺序

1. `AA` 实代数数适配层；
2. Point、Line、Circle；
3. 精确对象相等和去重；
4. line-line 求交；
5. line-circle 求交；
6. circle-circle 求交；
7. 相切、平行、重合和无实交点；
8. 精确字典序；
9. 自动交点闭包；
10. 目标点构造与比较。

### 建议目录

```text
sage/euclid_min/
  exact.py
  geometry.py
  intersections.py
  state.py
  target.py

tests/kernel/
```

### 验收条件

- 三类求交的 0/1/2 点及重合情况都有测试；
- 所有相等和排序判断为精确判断；
- 运行顺序不影响交点排序；
- 近似相等但数学上不同的反例不会被合并。

### 落地结果

- 内核位于 `sage/euclid_min/`；
- 测试位于 `tests/kernel/`；
- 参考运行环境为 SageMath 10.7；
- 三类求交、全部规范退化关系、自动闭包、重复对象和目标精确比较均已有回归测试。

## M2：验证闭环

### 实现内容

- YAML profile 加载；
- JSON Schema 校验；
- profile 哈希校验；
- 构造程序顺序重放；
- ID 和类型检查；
- E-score 重算；
- 目标首次命中记录；
- 构造内容哈希校验；
- JSON 验证报告；
- 面向人的 CLI 摘要。

### 建议命令

```bash
sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  certificates/regular-17/candidate.json
```

### 验收条件

- 合法证书得到确定的对象、分数和目标结果；
- 修改伪造分数、profile hash 或 construction hash 会失败；
- 非法证书返回稳定错误代码和程序位置；
- verifier 不读取或信任提交者提供的浮点坐标。

### 落地结果

- 严格 JSON/YAML 加载会拒绝重复键和非安全输入；
- profile、certificate 和 verification report 均有 Draft 2020-12 Schema；
- JCS 规范化和 SHA-256 由 Sage Python 内部实现并有 Unicode 排序测试；
- 名称环境、三种程序条目、重复对象计分和稳定错误位置均已实现；
- CLI 支持中文摘要、JSON stdout、独立报告文件和规范退出码；
- 结构合法但未命中目标的 fixture 可端到端验证；首份真实成功证书属于 M3 交付物。

## M3：首个可信 baseline

### 工作内容

- 建立 `docs/LITERATURE.md`；
- 选择一个步骤足够完整的正十七边形构造；
- 记录作者、来源、原始初始条件和计步方法；
- 转写为当前 profile 的基础操作；
- 生成构造证书和验证报告；
- 编写人类可读步骤及解释选择。

### 验收条件

- 至少一个构造被 Sage verifier 精确重放；
- 项目自行重算 E-score；
- 所有与原文不同的初始条件或宏展开均被公开；
- baseline 是否可与当前 profile 直接比较有明确结论。

### 落地结果

- 已取得并逐步核对 DeTemple 1991 论文第 4 节的十步 Carlyle 圆构造；
- 原文免费坐标轴已计费，modern non-collapsing compass 的两次距离搬运已按
  collapsing-compass 基础操作展开；
- 转写证书由 SageMath 10.7 verifier 精确重放为 32 E：11 条直线、21 个圆；
- 两个相邻目标点均在第 32 E 首次出现；
- 该条目标为 `converted`，原文 51/45 的 Lemoine simplicity 与 32 E 不直接可比；
- 来源、证书、验证报告和中文解释均保存在
  `baselines/regular-17/detemple-1991-carlyle-converted/`。

## M4：基础搜索

第一版搜索器统一使用 SageMath 自带的 Python 环境，以减少跨语言语义漂移。项目当前不支持脱离 SageMath 的本地普通 Python 运行路径。

### 实现内容

- 从当前点集生成 Line 和 Circle 候选；
- 自动交点闭包；
- 精确重复对象消除；
- 精确状态确认与 hash 索引；
- IDDFS 或 best-first；
- 深度限制和 checkpoint；
- provenance 与证书导出；
- 小深度完备回归测试。

### 验收条件

- 能重新发现正三角形、中点等内核测试构造；
- 所有输出证书均由独立 verifier 接受；
- 在指定小深度上，枚举数量和去重结果可重复；
- 搜索器和 verifier 之间没有共享“成功即正确”的捷径。

### 落地结果

- `sage/euclid_min/search/` 实现完整候选生成、显式自动闭包和确定性 BFS；
- 状态摘要只负责分桶，摘要命中后对 \((P,L,C)\) 做精确集合比较；
- `max_score` 提供深度界，`max_states` 以 `state_limit` 明确暂停而不冒充穷尽；
- frontier checkpoint 具有独立 Schema，可精确恢复并继续；
- 搜索路径可以恢复交点 provenance 并导出正式证书，CLI 写出前调用独立 verifier；
- 回归测试自动重发现 1 E 的等边三角形顶点和 3 E 的中点构造；
- 当前实现仅面向小深度，尚未对 32 E baseline 发起大规模搜索。

## M5：启发式搜索与 profiling

可以逐步加入：

- 目标数值距离；
- 代数次数和子域信号；
- 构造 DAG 深度及复用；
- 镜像对称排序或已证明的归约；
- beam search；
- random restart；
- 长时间运行的恢复和统计。

启发式只决定搜索顺序或非证明模式下的保留范围，不能进入精确验证结论。

### 落地结果

- BFS 和 beam 均记录候选生成、子状态展开、状态索引、目标判断和启发式耗时；
- 固定 SageMath 10.7 profile 表明深度 3 样本约 86%–88% 时间用于子状态精确展开；
- 实现同时面向两个镜像目标的对象关联残差和最近点距离评分；
- 确定性 beam search 每层按固定宽度保留状态，未命中只报告 `heuristic_limit`；
- CLI 用 `complete_bounded` 与 `heuristic_nonproof` 明确区分两种模式；
- 固定 profile、JSON Schema、复现实验脚本和解释文档已落地；
- 当前证据不支持引入 Go，下一轮应先优化几何状态复制、局部索引和求交缓存。

### Go 的进入条件

只有 profiling 显示 Python/Sage 的队列、状态元数据、并发或 checkpoint 是主要瓶颈时，才引入 Go。Go 可以负责：

- 搜索调度；
- 并发 worker；
- 紧凑状态索引；
- checkpoint；
- CLI 和性能统计。

不计划在此阶段用 Go 重写权威实代数内核。Go 搜索器输出候选证书，Sage verifier 给出最终结论。

## M6：新的已验证上界

成功条件是在同一 profile 下：

1. baseline 已被独立验证和计分；
2. 新候选使用更少 E-move；
3. 候选通过 Sage verifier；
4. 发布 profile、证书、报告、依赖图和人类可读说明。

允许声明“比已验证 baseline 更短”或“新的已验证上界”。没有 lower-bound proof 时不得声明全局最优。

### 落地结果

- 核对 DeTemple 1991 第 104 页的两项修改，并把它们翻译为当前可折叠圆规 profile；
- 半尺度 Carlyle 圆直接得到后续所需的两个中点，使原步骤 (ii)–(iv) 的 8 E 分支可由 4 E 替换；
- 复用步骤 (vi) 已有的圆，把原步骤 (vii)–(viii) 从 4 E 降为 3 E；
- 依赖 DAG 审计确认完整尺度根分支已被取代，删除其中两个无后继的计费圆及其零成本交点；
- 用 OH0,8 的中垂线作为单位圆目标弦，把最终单位长度搬运从 6 E 降为 3 E；
- 局部精确枚举找到一个已有点圆直接经过 Y，并以三线窗口定位 M0,4，使步骤 (vi) 及后续圆心构造合计从 9 E 降为 5 E；
- 两步目标窗口利用另一个 Carlyle 根和已有圆作出经过 B_plus 的目标线，把末段从 3 E 降为 2 E；
- 新证书由独立 SageMath 10.7 verifier 精确重放为 19 E：8 条直线、11 个圆；
- B_plus 在第 19 E 首次出现，无重复绘制；profile 只要求任一相邻目标；
- 相比同一 profile 的 32 E baseline，新的已验证上界降低 13 E；
- profile、证书、验证报告、机器可读依赖 DAG、Schema、来源台账、中文说明和回归测试均已发布；
- 该结果不包含 lower-bound proof，不声称 19 E 全局最优或文献最短。

## M7：Proof Mode（长期可选）

只有状态等价、对称性和完备枚举机制足够成熟后才进入。

必须保证每个剪枝都有可审计的安全证明，并输出可独立检查的枚举记录或证明证书。启发式低分、随机抽样、beam width 和数值近似均不能用于排除全部更短构造。

## 每个里程碑的共同完成标准

- 有自动化测试；
- 有固定输入和可复现输出；
- 有面向人的说明；
- 不把示例数字写成研究结论；
- 不混淆 profile；
- 不让搜索器替代 verifier；
- 不在证据等级不足时升级数学声明。
