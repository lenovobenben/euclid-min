# SageMath 精确参考内核

`sage/euclid_min/` 是 Euclid-Min 的权威精确几何内核。M1 固定使用 SageMath Algebraic Real Field `AA`，不接受 Python `float` 作为几何坐标输入。

## 模块

```text
euclid_min/
  exact.py          AA 转换、精确比较和平方根
  geometry.py       Point、Line、Circle
  intersections.py 三类求交及退化关系
  state.py          精确去重、显式闭包和验证器惰性闭包
  target.py         B_plus、B_minus 精确目标
  canonical_json.py JCS 规范化和 SHA-256
  formats.py        profile、证书和 Schema 严格加载
  replay.py         名称环境、程序重放和 E-score
  verifier.py       断言校验和验证报告
  cli.py            命令行入口
  search/           候选生成、精确 BFS、checkpoint 和证书导出
```

当前已经覆盖 M1 数学内核、M2 验证闭环、M3 首个可信 baseline、M4 基础
搜索器、M5 profiling/启发式搜索、M6 已验证上界（先得到 19 E，后更新为
17 E），以及 M7 小深度证明记录、横轴镜像归约、目标祖先审计、终层目标入射
裁剪、反向 DAG 切分接口和两步 AND/OR 义务展开。17 E 构造的可视化已经发布
在 [`animations/e17`](../animations/e17/README.md)。尚未实现：

- 能够完备排除 6–16 E 的全局 lower-bound proof mode。

M7 全局最优性证明当前标记为**待完成（暂停）**；现有严格边界为
\(5 < \operatorname{OPT}\le 17\)，恢复前需要新的理论归约。

## 参考环境

开发验证版本：

```text
SageMath 10.7
sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528
```

固定摘要用于复现实验。交互开发和 Jupyter 实验也应使用同一 SageMath 10.7 容器；正式验证必须记录实际版本和镜像摘要。

镜像内已固定并使用：

```text
PyYAML 6.0.1
jsonschema 4.17.3
```

JCS 编码器由项目内部实现，并有字符串转义、UTF-16 键排序、安全整数和 profile 摘要回归测试。

## 运行测试

在仓库根目录执行：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m unittest discover -s tests -v
```

项目不要求也不支持使用本地普通 Python 执行这些模块。交互实验可以使用同一 SageMath 容器中的 Jupyter，但正式代码、测试和验证仍通过 `sage -python` 运行。

## 运行 verifier

容器中的核心命令为：

```bash
sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  baselines/regular-17/eddy119-2026-adapted-17e/construction.json
```

可选参数：

- `--json`：把完整报告输出到 stdout；
- `--report result.json`：保存独立验证报告。

退出码 0 表示验证成功，1 表示证书或构造验证失败，2 表示 CLI 或报告写入错误。

当前 17 E 证书由以下命令确定性生成：

```bash
sage -python baselines/regular-17/eddy119-2026-adapted-17e/make_certificate.py
```

生成后仍须使用上述 `euclid_min verify` 命令从磁盘独立重放。

M3 基线的证书由以下命令确定性生成：

```bash
sage -python sage/experiments/build_detemple_1991_baseline.py
```

生成后仍须通过独立的 `euclid_min verify` 命令重放；生成器本身不是验证结论。

M6 的历史 19 E 证书与依赖 DAG 由以下命令确定性生成：

```bash
sage -python sage/experiments/build_detemple_1991_improved.py
```

输出仍须由独立 verifier 进程从磁盘重放。

## 运行小深度搜索

```bash
sage -python -m euclid_min search \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --max-score 1 \
  --json
```

`max_states` 是状态软上限；触发时返回退出码 3 和 `state_limit`，不能解释为
指定深度已穷尽。完整规则和 checkpoint 用法见 `docs/SEARCH.md`。

目标相关 beam 模式：

```bash
sage -python -m euclid_min search \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --max-score 6 \
  --strategy beam \
  --beam-width 32 \
  --json
```

beam 删除过分支，未命中时返回 `heuristic_limit` 和退出码 4。它不能用于下界或
最优性声明。固定 profiling 由 `sage/experiments/profile_search.py` 生成。

## 运行小深度 Proof Mode

```bash
sage -python -m euclid_min prove \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --max-score 5 \
  --workers 8 \
  --output proofs/regular-17-through-5e.json \
  --json

sage -python -m euclid_min check-proof \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  --workers 8 \
  proofs/regular-17-through-5e.json \
  --json
```

生成器没有状态上限、超时或启发式剪枝，并精确合并关于横轴互为镜像的状态；
最后一层只展开精确经过允许目标的候选。checker 使用线性精确参考枚举重新计算
全部层计数和终层入射。另有反向依赖 DAG 接口，用于按自动闭包最早可用分数
导出具体见证的前向/后向边界；两步 AND/OR 入口则完整枚举有限状态上的全部首步
对象和终步入射义务。v2 checker 改用线性前向枚举，并实际构造每个终步对象后
检查 `contains`；当前固定证明严格排除到 5 E，但不代表 6–16 E 已经穷尽。设计和
证据边界见 `docs/M7_PROOF_MODE.md`。

重建深度 3 frontier 并以 8 个进程完整扫描两步 AND/OR 义务：

```bash
sage -python sage/experiments/scan_m7_two_step_obligations.py --workers 8
```

该命令保留 P3b 的生成器侧中间产物；正式结论应引用已经独立重放的
`proofs/regular-17-through-5e.json`。

从 19 E 构造的精确 E12 前缀发起 6 E 并行联合后缀搜索：

```bash
sage -python sage/experiments/search_detemple_suffix.py \
  --max-total-score 18 \
  --beam-width 4 \
  --candidate-width 8 \
  --workers 8 \
  --state-timeout-seconds 8 \
  --max-input-level 8 \
  --candidate-strategy diverse
```

该实验使用浮点预筛、生成层级门、beam 截断和运行时超时，始终属于
`heuristic_nonproof`。完整设计与首轮结果见 `docs/M6_SUFFIX_SEARCH.md`。

同时运行四个确定性配置、合计最多 16 个精确 worker：

```bash
sage -python sage/experiments/search_detemple_suffix_matrix.py
```

可先增加 `--smoke` 只跑一层，检查嵌套子进程、产物路径和 Schema。正式矩阵
配置位于 `sage/experiments/configs/e12-suffix-restart-matrix-v1.json`。

增加 `--complexity-order` 可让已选候选按廉价 provenance 复杂度优先进入 worker；
该选项不调用最小多项式，也不改变候选评分的最终确定性顺序。六配置对照使用
`sage/experiments/configs/e12-suffix-complexity-matrix-v1.json`。

最后一次有界尝试使用以下三个入口：

```bash
sage -python sage/experiments/audit_detemple_suffix_ranks.py
sage -python sage/experiments/search_m04_three_step.py
sage -python sage/experiments/search_final_tail_two_step.py
```

排名审计确认当前通用启发式无法重新发现已知 19 E 后缀；两个分别可直接节省
1 E 的局部窗口也未命中。项目因此停止继续扩大当前 beam，详见
`docs/M6_SUFFIX_SEARCH.md` 第 8 节。

## 几何—代数 IR 与可恢复分片搜索

确定性生成 19E 基线的完整闭包、二次关系和上下文成本：

```bash
sage -python sage/experiments/build_regular17_geometry_algebra_ir.py
```

精确穷尽固定 17E 状态的全部一步目标扩展：

```bash
sage -python sage/experiments/search_e17_one_step_target_extension.py
```

固定 17E 一步搜索使用原子分片检查点。运行中断后重复同一命令会从未完成分片
继续；使用 `--max-shards 1` 可以演示完成一个新分片后主动暂停。

耗时更长的固定 16E 两步搜索使用候选级追加日志：

```bash
sage -python sage/experiments/search_e16_two_step_target_extension_v2.py \
  --workers 8
```

每个首步候选完成后立即 `fsync`，日志以 SHA-256 链校验。`Ctrl+C`、Docker 异常
退出或整机死机后，重复同一命令即可恢复，最多重算中断时正在 worker 中执行的
候选。未能由严格区间裁决的等式会写入 `deferred`，不会被误报为排除结论。输入
文件、算法脚本、profile 或配置变化时，任务签名校验会拒绝错误续跑。设计和当前
结论见 `docs/GEOMETRY_ALGEBRA_IR.md`。

该搜索现已完成：22,454 个首步候选和 202,855,848 个受限末笔参数化全部覆盖，
0 命中、0 未决关系。它严格排除的是已验证固定 16E 前缀之后的至多两笔扩展。
这只是对历史 19 E 路线固定前缀的局部 18 E 排除，不是 6–16 E 的全局下界。

## 精确性边界

- 所有几何坐标进入对象时立即转换为 `AA`；
- Python `float` 被明确拒绝；
- 直线通过精确比例归一化；
- 圆保存半径平方；
- 交点按精确 (x,y) 字典序排列；
- 相切重根只返回一个点；
- 状态去重使用数学相等，当前参考实现优先采用线性精确比较；
- verifier 用惰性精确闭包避免物化无关的高次数交点；绑定时仍精确求交，
  目标则以两个已构造对象的精确公共点判定；
- 搜索状态摘要中的浮点投影只用于分桶，命中后仍逐项精确确认；
- hash、字符串和浮点近似均不参与数学结论。
