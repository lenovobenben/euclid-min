# 正十七边形构造文献与 Baseline 台账

本文记录 Euclid-Min 的文献检索范围、来源状态、构造转写和 profile 可比性。

## 1. 当前状态

```text
系统检索：尚未开始
定向来源复核：DeTemple 1991 全文及十步构造已核对
已录入构造：2
已通过 verifier 的构造：2
可用于同一 profile 比较的条目：2（converted）
```

当前新的已验证上界为 27 E，原 32 E 条目作为首个 baseline 保留。系统文献检索尚未完成，因此不能把 27 E 称为文献最短或最短已知。

### 已验证 baseline

| ID | 来源 | 可比性 | 当前 profile 重算 | 状态 |
|---|---|---|---:|---|
| `detemple-1991-carlyle-converted` | DeTemple, 1991, §4, pp. 102–104, Fig. 3, steps (i)–(x) | `converted` | 32 E | Sage verifier 通过 |
| `detemple-1991-carlyle-improved-converted` | DeTemple, 1991, §4, p. 104, both stated modifications; superseded branch removed | `converted` | 27 E | Sage verifier 通过；新上界 |

原文从单位圆和两条坐标轴开始，使用 modern non-collapsing compass，并报告未经修改构造的 Lemoine simplicity 为 51、修改版为 45。本项目两条转写均为坐标轴计费并展开两次距离搬运：未经修改路线为 32 E；应用原文两项修改并删除已被半尺度路线取代的完整尺度根分支后为 27 E。原文 51/45 与本项目的 32/27 E 只能并列记录，不能跨 metric 直接比较；本项目内部的 32 E 与 27 E 使用同一 profile，可以直接比较。

## 2. 研究问题

检索只围绕以下问题展开：

> 给定 (O=(0,0))、(A=(1,0)) 和以 (O) 为圆心经过 (A) 的单位圆，使用无刻度直尺和可折叠圆规、只取确定交点，构造 (A) 的任意一个正十七边形相邻顶点。

其他初始条件、non-collapsing compass、自由点或其他 metric 下的构造可以作为历史材料记录，但不得直接与 `regular-17-e-fixed-v1` 的 E-score 比较。

## 3. 检索记录要求

每轮正式检索必须记录：

- 检索日期和截止日期；
- 数据库、图书馆目录、搜索引擎或档案来源；
- 完整检索式和关键词；
- 语言范围；
- 时间范围；
- 纳入和排除标准；
- 去重方法；
- 无法取得全文的条目；
- 从参考文献继续追踪的来源链。

建议关键词至少覆盖：

```text
regular 17-gon construction
heptadecagon construction
straightedge compass complexity 17-gon
minimal construction regular polygon
geometrography 17-gon
Lemoine simplicity heptadecagon
正十七边形 尺规作图
正十七边形 最短构造
```

关键词只是起点，正式检索时必须保存实际使用的数据库语法。

## 4. 候选来源起点

以下条目来自项目研究设计，只表示待核对的入口，不表示已获得全文、已确认 bibliographic metadata 或已验证其中的构造：

| ID | 候选来源 | 当前状态 | 预期用途 |
|---|---|---|---|
| `lemoine-geometrographie` | Émile Lemoine，*Géométrographie* | 待获取、待核对 | 历史 metric 与原始动作定义 |
| `detemple-1991-carlyle` | Duane W. DeTemple，Carlyle circles 与 polygon constructions 论文 | 全文、步骤和工具假设已核对；首个 baseline 已验证 | 历史构造和 Lemoine simplicity |
| `labelle-complexity` | François Labelle，尺规构造复杂度资料 | 待确认版本 | 复杂度框架与相关工作 |
| `demaine-luo-euclidea` | Erik D. Demaine、Victor Luo，Euclidea 优化复杂度论文 | 待核对 | 计算复杂度背景，不一定提供 baseline |
| `classical-heptadecagon` | Gauss 之后的经典正十七边形构造原始或可靠二手资料 | 待系统检索 | 首个可重放构造候选 |

正式引用时必须补齐作者、标题、出版物、年份、卷期页码、DOI/稳定链接和访问状态；不得直接把本表的简写作为最终 bibliography。

## 5. Baseline 条目模板

每个候选构造建立独立目录：

```text
baselines/regular-17/<baseline-id>/
  source.yaml
  construction.json
  verification.json
  explanation.md
```

`source.yaml` 至少记录：

```yaml
id: <baseline-id>
bibliography:
  authors: []
  title: ""
  year: null
  publication: ""
  pages: ""
  doi: ""
  stable_url: ""
access:
  full_text_obtained: false
  accessed_on: ""
construction:
  exact_location: ""
  initial_objects: ""
  tools: ""
  free_point_rules: ""
  original_metric: ""
  reported_score: null
euclid_min:
  target_profile: regular-17-e-fixed-v1
  directly_comparable: false
  conversion_notes: ""
  recomputed_e_score: null
  verification_status: not_entered
```

空值表示尚未确认，不能用推测填充。

## 6. 转写和验证流程

一个条目只有完成以下全部步骤，才能成为“已验证 baseline”：

1. 获得能够核对构造步骤的原始来源或可靠版本；
2. 定位具体页码、图号、定理或步骤；
3. 明确初始对象和允许工具；
4. 明确任意点、半自由点和距离搬运规则；
5. 明确原文 metric 及 reported score 的含义；
6. 把所有高级宏展开为当前 profile 的基础操作；
7. 对不兼容的初始条件明确给出转换步骤；
8. 生成 `euclid-min-certificate/v1`；
9. 使用 Sage reference verifier 重放；
10. 保存验证报告和人类可读说明；
11. 由第二人或独立实现复核关键解释选择。

只抄录论文或网页中的一个步数，不构成项目 baseline。

## 7. 可比性分类

每个条目必须标记以下一种状态：

| 状态 | 含义 |
|---|---|
| `direct` | 原始条件与当前 profile 相同，可以直接转写计分 |
| `converted` | 经公开的基础操作转换后可在当前 profile 下计分 |
| `historical_only` | 初始条件或 metric 不同，只能作为历史对照 |
| `insufficient_information` | 步骤或规则不足，无法可靠重放 |

`converted` 条目必须把转换成本计入当前 E-score。不同 profile 的原始 reported score 只能并列展示，不能写成直接优劣关系。

## 8. 声明门槛

- 至少一个构造通过验证：可以称为“已验证构造”；
- 同 profile 的 baseline 与新构造均通过验证，且新分数更低：可以称为“比已验证 baseline 更短”；
- 完成公开、充分的文献检索：才可以谨慎讨论“已审阅文献中的最短已知”；
- 具有完备 lower-bound proof：才可以声称全局最优。

当前项目满足“比已验证 baseline 更短”的门槛，并可把 27 E 作为同一 profile 下后续结果的比较上界；尚不满足“已审阅文献中的最短已知”或“全局最优”的声明门槛。
