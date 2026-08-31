# E19 Manim 演示动画

本目录把已验证的 19 E 构造制作成一段中文 Manim 动画。第一页说明研究对象以及
“项目基线 32 E”到“当前证书 19 E”的进展；这两个数字只在
`regular-17-e-fixed-v1` 内比较，不表示世界纪录。正片只保留全屏作图和右上角的单个步数计数器。几何数据
不是在动画里手工估算：`geometry.json` 由 SageMath 从正式证书精确重放后导出，
Manim 只负责把这些坐标转换成屏幕图形。免费单位圆使用独立洋红色，镜头会跟随
关键局部自动缩放，最后以 `∠AOB = 2π/17` 说明所求相邻顶点。

## 文件

- `STORYBOARD.md`：权威 19 步文字说明、表述口径和分镜；
- `export_geometry.py`：从正式证书导出数值几何快照；
- `geometry.json`：已导出的动画输入；
- `e19_progress.py`：Manim Community v0.21.0 场景；
- `Dockerfile`：固定 Manim 镜像并补充中文字体；
- `manim.cfg`：1080p、30 fps 和输出目录。

## 重新导出几何数据

```powershell
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  -e PYTHONPATH=/workspace/sage `
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 `
  sage -python animations/e19/export_geometry.py
```

## 构建渲染环境

```powershell
docker build -t euclid-min-manim:0.21.0 animations/e19
```

## 渲染

快速预览：

```powershell
docker run --rm `
  -v "${PWD}:/manim" `
  -w /manim `
  euclid-min-manim:0.21.0 `
  manim --config_file animations/e19/manim.cfg -ql `
  animations/e19/e19_progress.py E19Progress
```

1080p 成片：

```powershell
docker run --rm `
  -v "${PWD}:/manim" `
  -w /manim `
  euclid-min-manim:0.21.0 `
  manim --config_file animations/e19/manim.cfg -r 1920,1080 --fps 30 `
  animations/e19/e19_progress.py E19Progress
```

成片位于
`animations/e19/media/videos/e19_progress/1080p30/E19Progress.mp4`。媒体目录不提交
Git；代码、分镜和几何快照才是可复现源文件。
