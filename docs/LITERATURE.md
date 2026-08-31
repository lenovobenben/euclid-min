# 正十七边形构造文献与基线台账

本文记录 Euclid-Min 的文献检索范围、来源状态、构造转写和规则配置可比性。

## 1. 当前状态

```text
系统检索：尚未开始
定向来源复核：DeTemple 1991 构造、Labelle 计数、Grozdev–Dekov 2015 和 Demaine–Luo 2025 已核对
已录入构造：2
已通过验证器的构造：2
可用于同一规则配置比较的条目：2（经转换）
```

当前项目的已验证构造上界为 19 E，原 32 E 条目作为首个项目基线保留。系统文献检索尚未完成，因此不能把 19 E 称为文献最短、最短已知或世界纪录。

### 已验证构造基线

| ID | 来源 | 可比性 | 当前规则重算 | 状态 |
|---|---|---|---:|---|
| `detemple-1991-carlyle-converted` | DeTemple, 1991, §4, pp. 102–104, Fig. 3, steps (i)–(x) | `converted` | 32 E | Sage 验证器通过 |
| `detemple-1991-carlyle-improved-converted` | DeTemple, 1991, §4, p. 104，再加入项目内的依赖清理和局部精确替换 | `converted` | 19 E | Sage 验证器通过；项目当前上界 |

原文从单位圆和两条坐标轴开始，使用现代不折叠圆规，并报告未经修改构造的 Lemoine 简洁度为 51、修改版为 45。本项目两条转写均把坐标轴计费：未经修改路线并展开两次距离搬运后为 32 E；应用原文修改、删除被取代分支，并以局部精确窗口替换中段和末段后为 19 E。原文 51/45 与本项目的 32/19 E 只能并列记录，不能跨指标直接比较；本项目内部的 32 E 与 19 E 使用同一规则配置，可以直接比较。

## 2. E 步计数法的来源

本项目的 E 步具有两层来源：计费原则来自 Labelle 一类“只数画线和画圆”的复杂度，名称直接采用 Demaine–Luo 所定义的 E-move。

| 来源 | 原文采用的计数 | 与本项目的关系 |
|---|---|---|
| François Labelle, [*The Complexity of Geometric Constructions*](https://www.cs.mcgill.ca/~sqrt/cons/constructions.html), 1997 | 复杂度等于执行的画线和画圆次数；使用可折叠圆规；交点视为已构造点 | 基础工具和计费公式相同；具体题目的初始对象另行判断 |
| Sava Grozdev, Deko Dekov, [*The Computer Improves the Steiner’s Construction of the Malfatti Circles*](https://azbuki.bg/wp-content/uploads/2015/02/azbuki.bg_dmdocuments_MathInfo012015_Grozdev_Dekov.pdf), *Mathematics and Informatics* 58(1), 2015, 40–51 | 论文实际使用 Labelle 指标；表中直线/圆为 1，交点为 0 | 证明该计数法确实用于公开论文；其 Malfatti 问题与本项目分数不可直接比较 |
| Erik D. Demaine, Victor Luo, [*Euclidea is APX-hard: Complexity of Optimizing Euclidean Constructions*](https://doi.org/10.2197/ipsjjip.33.1110), *Journal of Information Processing* 33, 2025, 1110–1117 | 一次直尺或圆规基础操作为 1 E；解的 E-score 不含点定义 | E-move 名称和基础计费方式相同；论文的一般模型允许的点类型更广 |

这些来源支持“每画一条线或一个圆计 1 E，点定义计 0 E”这一核心计数法。它们不自动固定本项目的免费初始对象、确定点限制和目标条件；完整可比性仍必须由 `regular-17-e-fixed-v1` 决定。

## 3. 研究问题

检索只围绕以下问题展开：

> 给定 (O=(0,0))、(A=(1,0)) 和以 (O) 为圆心经过 (A) 的单位圆，使用无刻度直尺和可折叠圆规、只取确定交点，构造 (A) 的任意一个正十七边形相邻顶点。

其他初始条件、不折叠圆规、自由点或其他指标下的构造可以作为历史材料记录，但不得直接与 `regular-17-e-fixed-v1` 的 E 分数比较。

## 4. 检索记录要求

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

## 5. 候选来源起点

下表同时记录待核对入口和已经完成定向复核的来源；“当前状态”列是判断资料能否使用的依据：

| ID | 候选来源 | 当前状态 | 预期用途 |
|---|---|---|---|
| `lemoine-geometrographie` | Émile Lemoine，*Géométrographie* | 待获取、待核对 | 历史指标与原始动作定义 |
| `detemple-1991-carlyle` | Duane W. DeTemple，Carlyle 圆与多边形构造论文 | 全文、步骤和工具假设已核对；首个基线已验证 | 历史构造和 Lemoine 简洁度 |
| `labelle-complexity` | François Labelle，*The Complexity of Geometric Constructions* | 作者网页和规则已核对 | E 步基础计费原则的早期明确来源 |
| `grozdev-dekov-2015` | Sava Grozdev、Deko Dekov，Malfatti 圆构造论文 | 全文和 Labelle 指标用法已核对 | 公开论文采用相同基础计数法的实例 |
| `demaine-luo-euclidea` | Erik D. Demaine、Victor Luo，Euclidea 优化复杂度论文 | 正式论文全文和 E-move 定义已核对 | E-move 名称、形式定义与复杂度背景 |
| `classical-heptadecagon` | Gauss 之后的经典正十七边形构造原始或可靠二手资料 | 待系统检索 | 首个可重放构造候选 |

正式引用时必须补齐作者、标题、出版物、年份、卷期页码、DOI/稳定链接和访问状态；不得直接把本表的简写作为最终参考文献。

## 6. 基线条目模板

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

## 7. 转写和验证流程

一个条目只有完成以下全部步骤，才能成为“已验证基线”：

1. 获得能够核对构造步骤的原始来源或可靠版本；
2. 定位具体页码、图号、定理或步骤；
3. 明确初始对象和允许工具；
4. 明确任意点、半自由点和距离搬运规则；
5. 明确原文指标及报告分数的含义；
6. 把所有高级宏展开为当前规则配置的基础操作；
7. 对不兼容的初始条件明确给出转换步骤；
8. 生成 `euclid-min-certificate/v1`；
9. 使用 Sage 参考验证器重放；
10. 保存验证报告和人类可读说明；
11. 由第二人或独立实现复核关键解释选择。

只抄录论文或网页中的一个步数，不构成项目基线。

## 8. 可比性分类

每个条目必须标记以下一种状态：

| 状态 | 含义 |
|---|---|
| `direct` | 原始条件与当前规则配置相同，可以直接转写计分 |
| `converted` | 经公开的基础操作转换后可在当前规则配置下计分 |
| `historical_only` | 初始条件或指标不同，只能作为历史对照 |
| `insufficient_information` | 步骤或规则不足，无法可靠重放 |

`converted` 条目必须把转换成本计入当前 E 分数。不同规则配置的原始报告分数只能并列展示，不能写成直接优劣关系。

## 9. 声明门槛

- 至少一个构造通过验证：可以称为“已验证构造”；
- 同一规则配置的基线与新构造均通过验证，且新分数更低：可以称为“比已验证基线更短”；
- 完成公开、充分的文献检索：才可以谨慎讨论“已审阅文献中的最短已知”；
- 具有完备下界证明：才可以声称全局最优。

当前项目满足“比已验证基线更短”的门槛，并可把 19 E 作为同一规则配置下后续结果的比较上界；尚不满足“已审阅文献中的最短已知”或“全局最优”的声明门槛。
