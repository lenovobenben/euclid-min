# Euclid-Min 计分规范 v1

本文定义 `regular-17-e-fixed-v1` 的唯一正式指标：E-move。

## 1. 定义

构造程序的 E-score 为：

\[
E=\#\operatorname{Line}+\#\operatorname{Circle}.
\]

只有基础画线和基础画圆消耗 E-move。

| 程序条目 | 成本 |
|---|---:|
| `line` | 1 E |
| `circle` | 1 E |
| `intersect` | 0 E |
| 初始对象 | 0 E |
| 自动交点闭包 | 0 E |

## 2. 计分对象

计分针对证书中完整、有序的 `construction.program`。

验证器必须自己逐条计数，不得信任证书的 `assertions.score.e_move`。声明分数与重算分数不同，证书验证失败并返回 `score_assertion_mismatch`。

## 3. 初始对象

以下对象免费：

- (O=(0,0))；
- (A=(1,0))；
- 以 (O) 为圆心、经过 (A) 的单位圆 `unit_circle`。

它们不作为隐含历史步骤计分。

## 4. 重复对象

再次画出数学上已经存在的直线或圆，仍然消耗 1 E。

例如，一份程序先后两次执行同一对点的 `line`，只会得到一个不同的数学直线对象，但分数增加 2 E。

这一区分必须同时出现在验证报告中：

```text
draw_operations.lines
draw_operations.circles
draw_operations.total
distinct_objects.lines
distinct_objects.circles
duplicate_draws
```

正式 E-score 使用 `draw_operations.total`，不使用不同对象数量。

## 5. 交点和点命名

交点在新对象加入状态后自动产生，成本为 0 E。`intersect` 条目只是确定性选择并命名一个已有交点，也为 0 E。

证书可以给同一个数学点绑定多个不同名称；这些别名不计分。

## 6. 高级宏

中点、垂线、垂直平分线、平行线、角平分线、距离搬运等都不是当前 profile 的基础操作。

如果 UI、搜索器或人类说明使用宏，正式计分前必须将宏完全展开为 `line`、`circle` 和零成本 `intersect` 条目。宏名称本身没有分数。

## 7. 目标提前出现

如果目标在第 (k) 次画图后出现，但程序之后还有合法画图步骤：

- 构造仍然可以有效；
- `first_target_e_move` 为 (k)；
- 正式 `score.e_move` 是完整程序中的全部画图步骤数；
- 验证器不得自动截断或忽略后续步骤。

发布最短构造时，应当提交在首次命中目标后立即结束的裁剪版本。

## 8. 非法程序

非法程序没有正式分数。验证器可以报告：

- `consumed_e_moves_before_error`；
- `error_program_index`。

它们只是诊断数据，不得作为可比较的 E-score。

对单条 `line` 或 `circle`，前置条件校验发生在计费之前。因此导致该条目非法的画图操作不计入诊断用的 `consumed_e_moves_before_error`。

## 9. 可比性

两个数字只有同时满足以下条件时才能直接比较：

- profile ID 相同；
- profile 内容哈希相同；
- 两份程序都通过精确验证；
- 分数都由符合本规范的验证器重新计算。

不同的初始对象、自由点规则、圆规模型、目标条件或 metric 都构成不同 profile。不得把不同 profile 的数字写成直接的优劣关系。

## 10. 与历史指标的关系

Lemoine simplicity、DeTemple 的历史计分及其他几何复杂度指标不属于本规范。将来如需实现，必须建立独立 profile 和独立 metric 文档，不能修改 `regular-17-e-fixed-v1` 的既有含义。

## 11. 正式报告最小字段

成功验证的报告至少包含：

```json
{
  "valid": true,
  "draw_operations": {
    "lines": 0,
    "circles": 0,
    "total": 0
  },
  "score": {
    "metric": "e_move",
    "e_move": 0
  },
  "first_target_e_move": 0,
  "target": ["B_plus"]
}
```

上例中的零值仅说明字段结构，不代表存在零步构造。
