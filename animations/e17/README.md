# E17 Manim 演示动画

本目录把已验证的 17 E 构造制作成一段中文 Manim 动画。第一页说明研究对象以及
项目上界从 19 E 更新到 17 E；这两个数字只在 `regular-17-e-fixed-v1` 内比较，
不表示 17 E 已经证明为全局最小。正片沿用上一版的全屏作图、右上角单一计数器、
配色、定位点提示和镜头跟随规范，几何线条比上一版略细。

几何数据不是在动画里手工估算：`geometry.json` 由 SageMath 从正式证书精确重放后
导出，Manim 只负责把坐标转换成屏幕图形。免费单位圆使用独立洋红色；每次作直线
前高亮两个定线点，每次作圆前高亮圆心和圆上一点并临时显示半径。最后一笔连接
O 与对径点 N，切出目标 B，并以 `∠AOB = 2π/17` 收束。

构造的几何主干来自 Eddy119 公开的 37-move 完整正十七边形构造。Euclid-Min 将
相关前缀转换为当前 profile 的 18 E，再删除一个无用圆得到 17 E，并完成证书与
精确证明。完整归属见
[`source.yaml`](../../baselines/regular-17/eddy119-2026-adapted-17e/source.yaml)。

## 文件

- `STORYBOARD.md`：权威 17 步文字说明、表述口径和分镜；
- `export_geometry.py`：从正式证书导出数值几何快照；
- `geometry.json`：已导出的动画输入；
- `e17_progress.py`：Manim Community v0.21.0 场景；
- `Dockerfile`：固定 Manim 镜像并补充中文字体；
- `manim.cfg`：4K（3840×2160）、30 fps 和输出目录。

## 重新导出几何数据

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python animations/e17/export_geometry.py
```

## 构建渲染环境

```powershell
docker build -t euclid-min-manim:0.21.0 animations/e17
```

## 渲染

快速预览：

```powershell
docker run --rm `
  -v "${PWD}:/manim" `
  -w /manim `
  euclid-min-manim:0.21.0 `
  manim --config_file animations/e17/manim.cfg -ql `
  animations/e17/e17_progress.py E17Progress
```

4K 成片：

```powershell
docker run --rm `
  -v "${PWD}:/manim" `
  -w /manim `
  euclid-min-manim:0.21.0 `
  manim --config_file animations/e17/manim.cfg --fps 30 `
  animations/e17/e17_progress.py E17Progress
```

成片位于
`animations/e17/media/videos/e17_progress/2160p30/E17Progress.mp4`。最终 4K MP4
随代码提交；同一媒体目录内的分段视频、渲染缓存和临时文件由 Git 忽略。
