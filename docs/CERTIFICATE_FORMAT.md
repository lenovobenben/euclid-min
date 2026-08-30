# Euclid-Min 构造证书格式 v1

本文定义 `euclid-min-certificate/v1`。证书是一个可重放的声明性 JSON 文档；它不包含可信坐标，验证器必须从 profile 和程序步骤重新计算全部几何对象。

## 1. 文件编码与 Schema

- 文件格式：JSON；
- 文本编码：UTF-8；
- Schema：`schemas/certificate-v1.schema.json`；
- `schema` 固定为 `euclid-min-certificate/v1`；
- 正式证书文件建议使用 `.json` 后缀。

JSON Schema 只检查结构。引用顺序、几何类型、精确相等、交点索引、分数、目标和哈希仍必须由 verifier 做语义校验。

## 2. 顶层结构

```json
{
  "schema": "euclid-min-certificate/v1",
  "problem": "regular-17-adjacent-vertex",
  "profile": {
    "id": "regular-17-e-fixed-v1",
    "sha256": "<64 个小写十六进制字符>"
  },
  "construction": {
    "id": "example-construction",
    "title": "示例构造",
    "program": []
  },
  "assertions": {
    "score": {
      "metric": "e_move",
      "e_move": 0
    },
    "targets": ["B_plus"],
    "claim": "verified_construction"
  },
  "software": {
    "producer": {
      "name": "manual",
      "version": "1"
    }
  },
  "integrity": {
    "construction_sha256": "<64 个小写十六进制字符>"
  }
}
```

上例只说明字段结构，不是一份有效的零步构造证书。

## 3. Profile 绑定

`profile.id` 必须与加载的 profile 的 `id` 完全一致。

`profile.sha256` 是 profile 解析后完整数据模型的摘要。计算步骤为：

1. 把 YAML profile 解析为 JSON 兼容的数据模型；
2. 按 RFC 8785 JSON Canonicalization Scheme（JCS）序列化；
3. 将规范化结果编码为 UTF-8；
4. 计算 SHA-256；
5. 以 64 位小写十六进制字符串保存。

profile 文件本身不保存自己的摘要，因此不存在自引用。空白、注释和 YAML 键顺序不影响摘要；解析后的值、数组顺序和字段内容会影响摘要。

仓库同时保存同名 `.sha256` 旁车文件，便于人工和 CI 快速核对。当前 profile 的规范摘要见 `profiles/regular-17-e-fixed-v1.sha256`；旁车文件不参与 profile 自身摘要。

v1 profile 和证书哈希域只使用字符串、安全整数、布尔值、对象和数组，以避免 YAML 类型和 JCS 数字边界产生歧义。安全整数范围是 ([-9007199254740991,9007199254740991])。加载器必须使用安全模式，并拒绝自定义 YAML tag；规范化器不得接受浮点数。

## 4. Construction 内容哈希

`integrity.construction_sha256` 只覆盖顶层 `construction` 对象，计算方法同样是：

```text
JCS(construction) → UTF-8 → SHA-256 → 小写十六进制
```

因此，程序步骤、construction ID、标题或说明变化都会改变构造哈希；提交者声明、生产软件信息和哈希字段本身不参与该摘要。

哈希只用于检测内容变化，不证明数学正确性。验证器必须同时重放构造。

## 5. 程序模型

`construction.program` 是严格有序的条目数组。所有 ID 位于同一个全局命名空间，且只能引用此前已经声明的 ID。

文档和验证报告中的 `program_index` 均指 JSON 数组的从 0 开始索引。面向人的界面可以同时显示从 1 开始的“第几条”，但必须与规范索引明确区分。

初始名称环境固定包含：

| ID | 类型 | 数学对象 |
|---|---|---|
| `O` | point | ((0,0)) |
| `A` | point | ((1,0)) |
| `unit_circle` | circle | 圆心 `O`、经过 `A` |

### 5.1 画直线

```json
{
  "id": "l1",
  "op": "line",
  "through": ["O", "A"]
}
```

`through` 中两个 ID 必须已经绑定为数学上不同的点。条目成本为 1 E。

点的顺序不改变所得数学直线，但数组顺序属于证书字节内容，因此会影响 construction hash。

### 5.2 画圆

```json
{
  "id": "c1",
  "op": "circle",
  "center": "A",
  "through": "O"
}
```

`center` 和 `through` 必须已经绑定为数学上不同的点。半径是两点的距离。条目成本为 1 E。

### 5.3 绑定交点

```json
{
  "id": "P",
  "op": "intersect",
  "objects": ["c1", "unit_circle"],
  "index": 1
}
```

`objects` 中两个 ID 必须已经绑定为直线或圆。验证器精确求交，按 (x)、再按 (y) 升序排列不同的有限实交点，并用从 0 开始的 `index` 选择。

该条目只建立点别名，成本为 0 E。对象数组顺序不影响交点排序。

证书不允许直接提供交点坐标，因为坐标会重复数学事实并引入伪造或近似误差的入口。

## 6. 自动闭包与绑定的关系

画出一个新数学对象后，它与所有既有不同直线和圆的有限实交点自动加入状态。`intersect` 不是“现在才求交”，而是给其中一个已经存在的点命名，以便后续步骤引用。

因此：

- 目标点自动出现时已经达成目标，不要求再绑定名称；
- 绑定一个已存在交点不改变数学状态；
- 可以给同一个点绑定多个名称；
- 重复画出的对象不会触发第二次闭包；
- 重合对象没有可按索引选择的孤立交点。

## 7. Assertions

`assertions` 是证书提交者对预期结果的声明，不是可信验证结果。

### 7.1 分数

```json
"score": {
  "metric": "e_move",
  "e_move": 13
}
```

验证器必须重算分数。不同则验证失败。

### 7.2 目标

`targets` 是提交者声称在最终状态中出现的精确目标集合，只允许：

```text
B_plus
B_minus
```

数组必须去重。验证器必须精确重算实际命中集合，并要求它与声明集合完全相同。这样可以发现证书内容或分支选择被意外修改。

### 7.3 声明等级

`claim` 允许以下值：

| 值 | 含义 |
|---|---|
| `verified_construction` | Level 0：请求验证一个合法构造 |
| `shorter_than_verified_baseline` | Level 1：请求结合指定 baseline 证明更短 |
| `shortest_known_reviewed_literature` | Level 2：需要额外文献检索记录 |
| `globally_minimal` | Level 3：需要额外完备 lower-bound 证明 |

基础几何 verifier 只能独立确认 Level 0。更高等级不能仅凭该枚举字段成立，必须在结果包中附加相应证据。证据不足时，几何构造本身可以验证成功，但验证报告必须把“支持的最高声明等级”限制在实际证据等级。

## 8. Software 元数据

`software.producer` 描述生成证书程序的人或软件。手工证书可以使用：

```json
{
  "name": "manual",
  "version": "1"
}
```

搜索器可以额外填写 `software.solver`。这些字段用于复现，不参与数学判断，也不参与 construction hash。

verifier 的名称、版本和运行结果不写回输入证书，而是写入独立验证报告。这样可以让同一不可变证书被多个 verifier 独立核验。

## 9. 验证顺序

参考 verifier 必须按以下顺序处理：

1. 解析 JSON，并拒绝重复 JSON object key；
2. 用 certificate Schema 校验结构；
3. 安全解析 profile，并用 profile Schema 校验；
4. 校验 problem、profile ID 和 profile hash；
5. 校验 construction hash；
6. 初始化固定数学状态；
7. 顺序重放 program；
8. 重算分数和目标集合；
9. 校验 assertions；
10. 生成独立验证报告。

解析器不得采用“后一个重复键覆盖前一个”的宽松行为。

## 10. 验证报告

验证报告不是输入证书的一部分，其结构由 `schemas/verification-report-v1.schema.json` 约束。成功报告至少应包含：

```json
{
  "schema": "euclid-min-verification-report/v1",
  "certificate_sha256": "<完整证书文件内容的 SHA-256>",
  "construction_sha256": "<已核验的构造摘要>",
  "profile": {
    "id": "regular-17-e-fixed-v1",
    "sha256": "<已核验的 profile 摘要>"
  },
  "verifier": {
    "name": "euclid-min-sage-verifier",
    "version": "0.5.0",
    "sage_version": "10.7"
  },
  "valid": true,
  "distinct_objects": {
    "lines": 11,
    "circles": 22
  },
  "bound_points": 29,
  "closure_strategy": "implicit_exact",
  "score": {
    "metric": "e_move",
    "e_move": 13
  },
  "targets": ["B_plus"],
  "first_target_program_index": 20,
  "first_target_e_move": 13,
  "supported_claim": "verified_construction"
}
```

`certificate_sha256` 对原始 UTF-8 文件字节计算，用于确定实际验证的是哪一个文件；语义身份仍由规范化的 profile 和 construction 摘要承担。

`distinct_objects` 只统计不同的已构造直线和圆，其中包含 profile 免费提供的对象。
`bound_points` 是初始点和证书显式绑定的不同点数，不是数学闭包中全部交点的
数量。`closure_strategy: implicit_exact` 表示 verifier 按正式模型保留隐式闭包，
只在绑定时精确物化指定对象对的交点；该策略不改变构造语义或目标判定。

失败报告至少应包含：

- `valid: false`；
- 稳定错误代码；
- 可用时的 `program_index` 和条目 ID；
- 面向人的错误说明；
- 非正式的 `consumed_e_moves_before_error`。

## 11. 完整结构示例

以下程序只演示语法，不构造正十七边形目标，因此不能作为有效正式证书：

```json
{
  "schema": "euclid-min-certificate/v1",
  "problem": "regular-17-adjacent-vertex",
  "profile": {
    "id": "regular-17-e-fixed-v1",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "construction": {
    "id": "syntax-example",
    "title": "仅用于说明格式",
    "program": [
      {
        "id": "c1",
        "op": "circle",
        "center": "A",
        "through": "O"
      },
      {
        "id": "P",
        "op": "intersect",
        "objects": ["c1", "unit_circle"],
        "index": 1
      },
      {
        "id": "l1",
        "op": "line",
        "through": ["A", "P"]
      }
    ]
  },
  "assertions": {
    "score": {
      "metric": "e_move",
      "e_move": 2
    },
    "targets": ["B_plus"],
    "claim": "verified_construction"
  },
  "software": {
    "producer": {
      "name": "manual",
      "version": "1"
    }
  },
  "integrity": {
    "construction_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

示例中的零哈希、目标声明和最终验证结果故意无效，防止格式示例被误当成研究结果。
