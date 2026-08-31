# Euclid-Min

Euclid-Min 是一个专门研究正十七边形相邻顶点最短尺规构造的计算数学项目。

项目固定初始对象为单位圆

\[
O=(0,0),\qquad A=(1,0),\qquad \Gamma:x^2+y^2=1,
\]

并研究：只使用无刻度直尺与可折叠圆规，至少需要多少次基础作图操作，才能得到 (A) 在单位圆上的任意一个相邻正十七边形顶点。

当前阶段的首要目标不是宣称全局最优，而是建立一条可复现的研究链路：

```text
形式规范 → Sage 精确验证器 → 已知构造 baseline → 自动搜索 → 可验证证书
```

## 当前状态

项目已完成 **M0：形式规范冻结**、**M1：Sage 精确几何内核**、**M2：验证闭环**、**M3：首个可信 baseline**、**M4：基础搜索器**、**M5：profiling 与启发式搜索**和 **M6：新的已验证上界**，并已推进到 **M7 P2：终层反向约束**。DeTemple 1991 修改版的 Carlyle 圆构造经当前 profile 转写、依赖清理和局部精确窗口替换后，由 Sage verifier 精确重放为 **19 E**（8 条直线、11 个圆），比原 32 E baseline 短 13 E。

唯一规范 profile 为：

```text
regular-17-e-fixed-v1
```

该 profile 使用 E-move 计分：

- 画一条合法直线：1 E；
- 画一个合法基础圆：1 E；
- 选择或命名已经自动产生的交点：0 E；
- 初始点 (O,A) 和单位圆免费提供。

## 规范文件

- [研究设计](docs/euclid-min-design.md)：项目定位、研究范围和长期路线；
- [正式模型](docs/FORMAL_MODEL.md)：对象、状态、操作、交点和目标的规范语义；
- [计分规则](docs/METRICS.md)：E-move 的权威计分规则；
- [证书格式](docs/CERTIFICATE_FORMAT.md)：构造程序、哈希和验证输出约定；
- [文献与 baseline 台账](docs/LITERATURE.md)：检索规则、来源状态和可比性记录；
- [实施路线](docs/ROADMAP.md)：从规范到搜索器的阶段计划；
- [基础搜索器](docs/SEARCH.md)：M4 状态、候选、去重、checkpoint 和 CLI；
- [M5 Profiling](docs/M5_PROFILING.md)：固定实验、热点结论和启发式边界；
- [E12 并行后缀搜索](docs/M6_SUFFIX_SEARCH.md)：18 E 联合窗口、进程并行、候选多样化和证据边界；
- [M7 Proof Mode](docs/M7_PROOF_MODE.md)：有界完备枚举、安全归约、证明记录和参考重放；
- [首份小深度证明记录](proofs/regular-17-through-4e.json)：参考 checker 可重放的 4 E 有界穷尽产物；
- [19 E 新上界说明](baselines/regular-17/detemple-1991-carlyle-improved-converted/explanation.md)：M6 证书、推导、计分与依赖主链；
- [固定 profile](profiles/regular-17-e-fixed-v1.yaml)：当前唯一可比较的研究实例；
- [固定 profile 摘要](profiles/regular-17-e-fixed-v1.sha256)；
- [Profile Schema](schemas/profile-v1.schema.json)；
- [Certificate Schema](schemas/certificate-v1.schema.json)；
- [Verification Report Schema](schemas/verification-report-v1.schema.json)；
- [Search Checkpoint Schema](schemas/search-checkpoint-v1.schema.json)；
- [Search Profile Schema](schemas/search-profile-v1.schema.json)；
- [Bounded Proof Schema](schemas/bounded-proof-v1.schema.json)；
- [Suffix Search Summary Schema](schemas/suffix-search-summary-v1.schema.json)；
- [Suffix Restart Matrix Config Schema](schemas/suffix-restart-matrix-config-v1.schema.json)；
- [Suffix Restart Matrix Summary Schema](schemas/suffix-restart-matrix-summary-v1.schema.json)；
- [Dependency Graph Schema](schemas/dependency-graph-v1.schema.json)；
- [Sage 内核运行说明](sage/README.md)。

若研究设计与版本化规范冲突，以 profile、Schema、`FORMAL_MODEL.md`、`METRICS.md` 和 `CERTIFICATE_FORMAT.md` 中更具体的规则为准。

## 技术边界

- 全部 Python 代码统一运行在 SageMath 自带的 Python 环境中；
- SageMath 同时承载精确内核、Schema 校验、CLI、报告和第一版搜索器；
- 本地普通 Python 和 Go 都不属于当前支持的运行路径；只有 profiling 证明有必要时才重新评估 Go；
- 浮点计算只能用于绘图、启发式排序或非权威 hash 分桶，不能决定几何相等、构造合法性、状态合并或目标命中；
- 没有完备 lower-bound proof 时，只能发布“已验证构造”或“新的已验证上界”，不能声称全局最优。

## 近期里程碑

1. **M0：规范闭环**——冻结正式模型、profile、证书格式和计分规则；
2. **M1：精确几何内核**——实现三类精确求交及退化处理；
3. **M2：验证闭环**——实现证书重放、目标判断和验证报告；
4. **M3：首个 baseline**——完整录入并验证一个正十七边形已知构造；
5. **M4：基础搜索**——实现小深度可审计搜索和证书导出；
6. **M5：profiling 与启发式搜索**——定位热点并实现非证明 beam；
7. **M6：新的已验证上界**——把论文修改转写、清理无效分支、加入局部精确窗口替换并验证为 19 E。
8. **M7：Proof Mode**——以安全归约、完备枚举记录和参考重放逐步建立下界证据。

M5 profile 显示当前主要热点在 Sage 精确子状态展开，而非 Python 队列；目前不引入 Go。E12 后缀搜索已经支持 16-worker 容量的确定性 restart 矩阵；六配置复杂度实验实测峰值约 1212% Docker CPU。最后又对 E12→`M0_4` 三步窗口和 E16→目标两步窗口进行了有界专用搜索，仍未找到 18 E。由于当前启发式无法重新发现已知 19 E 后缀，项目已按停止条件结束盲目扩宽；所有 M6 启发式负结果均不是下界。M6 的 19 E 来自可审计的构造化简、依赖清理和局部精确枚举，不依赖启发式搜索成功。M7 已实现小深度 proof record、线性精确参考重放、横轴镜像归约、目标依赖祖先审计和终层精确入射裁剪；当前固定产物完整排除到 4 E，尚未穷尽 18 E，因此 19 E 仍不是已证明最优值。

更完整的验收条件见 [实施路线](docs/ROADMAP.md)。

## 运行精确内核测试

当前参考环境为 SageMath 10.7。使用 Docker 运行：

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m unittest discover -s tests -v
```

更多容器运行说明和目录说明见 [Sage 内核运行说明](sage/README.md)。

## 运行证书验证器

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python -m euclid_min verify `
  --profile profiles/regular-17-e-fixed-v1.yaml `
  tests/fixtures/certificates/not-target.json
```

成功基线可把最后一个参数替换为：

```text
baselines/regular-17/detemple-1991-carlyle-improved-converted/construction.json
```

原 fixture 专门测试“结构合法但未达到目标”的失败路径，因此命令应返回 `target_not_reached` 和退出码 1。

## 研究声明

仓库当前给出一个在固定 profile 下重算为 19 E 的新已验证上界，并保留 32 E 首个 baseline 供差分审计。项目尚未完成系统文献检索，也没有 lower-bound proof，因此不声称 19 E 是文献最短、最短已知或全局最优。
