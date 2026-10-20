# SageMath 精确内核与运行说明

参考环境固定为 SageMath 10.7，镜像为：

```text
sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528
```

`euclid_min` 使用 Sage `AA` 精确实代数数，不接受 Python float 作为几何输入。普通 Python 可以运行 Manim 数据适配器，但不能替代 Sage 进行数学核验。运行下列命令时设置 `PYTHONPATH=<仓库>/sage`。

| 模块 | 职责 |
|---|---|
| `exact.py`、`geometry.py`、`intersections.py` | 精确数、点线圆、三类求交与退化关系 |
| `state.py` | 搜索用完整显式闭包与验证用惰性闭包 |
| `formats.py`、`canonical_json.py` | Schema、严格加载、JCS 和 SHA-256 |
| `replay.py`、`verifier.py` | 名称引用、逐条重放、计数、首次目标与报告 |
| `geometry_algebra_ir.py` | 通用表达式与完整闭包转移审计 |
| `search/` | 候选、精确 BFS、非证明 beam、依赖与有界证明 |

## 验证 12 E

```sh
sage -python -m euclid_min verify \
  --profile profiles/regular-17-e-fixed-v1.yaml \
  qq-ggb/construction-12e-011.json --json
```

退出码 0 表示通过，1 表示构造或证书失败，2 表示命令行或报告写入错误。`--report <路径>` 可保存报告。

生成分支证书及独立检查：

```sh
sage -python qq-ggb/search_branches.py
sage -python qq-ggb/independent_12e_check.py
sage -python qq-ggb/independent_certificate_check.py
```

## 测试

```sh
sage -python -m unittest discover -s tests -v
```

## 搜索与证明

```sh
sage -python -m euclid_min search --profile profiles/regular-17-e-fixed-v1.yaml --max-score 3 --json
sage -python -m euclid_min search --profile profiles/regular-17-e-fixed-v1.yaml --max-score 6 --strategy beam --beam-width 32 --json
sage -python -m euclid_min check-proof --profile profiles/regular-17-e-fixed-v1.yaml --workers 8 proofs/regular-17-through-5e.json --json
```

BFS 触及状态上限返回 `state_limit`，beam 未命中返回 `heuristic_limit`，二者都不能用来声明下界。当前严格范围为 `5 < OPT ≤ 12`；全局 6–11 E 证明待完成。详见[搜索语义](../docs/SEARCH.md)与[证明模式](../docs/M7_PROOF_MODE.md)。
