# SageMath 精确参考内核

`sage/euclid_min/` 是 Euclid-Min 的权威精确几何内核。M1 固定使用 SageMath Algebraic Real Field `AA`，不接受 Python `float` 作为几何坐标输入。

## 模块

```text
euclid_min/
  exact.py          AA 转换、精确比较和平方根
  geometry.py       Point、Line、Circle
  intersections.py 三类求交及退化关系
  state.py          精确去重和自动交点闭包
  target.py         B_plus、B_minus 精确目标
```

当前模块只实现数学内核，不负责：

- profile 和 JSON Schema 加载；
- 证书 ID 名称环境；
- 顺序程序重放；
- E-score；
- 验证报告和 CLI。

这些内容属于 M2。

## 参考环境

开发验证版本：

```text
SageMath 10.7
sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528
```

固定摘要用于复现实验。可以在本地交互开发时使用兼容的 SageMath 10.7 环境，但正式验证应记录实际版本和镜像摘要。

## 运行测试

在仓库根目录执行：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m unittest discover -s tests/kernel -v
```

项目不要求也不支持使用本地普通 Python 执行这些模块。交互实验可以使用同一 SageMath 容器中的 Jupyter，但正式代码、测试和验证仍通过 `sage -python` 运行。

## 精确性边界

- 所有几何坐标进入对象时立即转换为 `AA`；
- Python `float` 被明确拒绝；
- 直线通过精确比例归一化；
- 圆保存半径平方；
- 交点按精确 (x,y) 字典序排列；
- 相切重根只返回一个点；
- 状态去重使用数学相等，当前参考实现优先采用线性精确比较；
- hash、字符串和浮点近似均不参与数学结论。
