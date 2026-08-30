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

当前已经覆盖 M1 数学内核、M2 验证闭环、M3 首个可信 baseline、M4 基础搜索器、M5 profiling/启发式搜索和 M6 新的已验证上界。尚未实现：

- 构造可视化；
- lower-bound proof mode。

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
  certificates/example.json
```

可选参数：

- `--json`：把完整报告输出到 stdout；
- `--report result.json`：保存独立验证报告。

退出码 0 表示验证成功，1 表示证书或构造验证失败，2 表示 CLI 或报告写入错误。

M3 基线的证书由以下命令确定性生成：

```bash
sage -python sage/experiments/build_detemple_1991_baseline.py
```

生成后仍须通过独立的 `euclid_min verify` 命令重放；生成器本身不是验证结论。

M6 的 27 E 证书与依赖 DAG 由以下命令确定性生成：

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
