# live-faceswap

在 Apple Silicon Mac 上本地运行的实时换脸部署包，基于开源项目 [Deep-Live-Cam](https://github.com/hacksider/Deep-Live-Cam)，用 CoreML 加速。面向上半身取景的日常闲聊直播场景。

本仓库只包含**安装脚本、启动脚本和辅助工具**。Deep-Live-Cam 源码和模型权重由 `setup.sh` 从官方来源拉取，不随仓库分发。

> **全程本地运行**：人脸检测、换脸推理都在本机完成，摄像头画面不会上传。只有首次安装时需要联网下载模型。

## ⚠️ 使用前必读：合规与许可

1. **只能使用 AI 生成的虚拟人脸，或本人书面授权的成年人照片。** 不要使用网上找到的真人、网红或明星照片，否则涉及肖像权侵权，平台也会处置仿冒账号。
2. **画面中必须显式标注「AI 生成」。** 《人工智能生成合成内容标识办法》（2025-09-01 起施行）把人脸替换列为必须显式标识的内容；抖音要求 AI 生成内容显著标识，虚拟人需注册、背后真人实名并实时驱动。
3. **模型许可只允许非商用。** 默认换脸模型 `inswapper_128` 和人脸分析模型 `buffalo_l` 来自 InsightFace，许可仅限非商业研究。直播打赏、带货等商业用途需要另行向 InsightFace 获取授权，或更换许可允许商用的模型。
4. 不要用于冒充他人、诱导打赏等欺骗行为。

## 环境要求

| 项 | 要求 |
|---|---|
| 硬件 | Apple Silicon（M1–M5）；实测机器为 M4 Pro 20 核 GPU、48GB 内存 |
| 系统 | macOS，已安装 [Homebrew](https://brew.sh) |
| 磁盘 | 约 3GB |

## 快速开始

```bash
git clone https://github.com/xyyylll/live-faceswap.git
cd live-faceswap
./setup.sh          # 加 --with-gpen256 可同时下载 GPEN-256 画质增强模型（可选）
./run.sh
```

`setup.sh` 会依次：
1. 用 brew 安装 `python@3.14`、`python-tk@3.14`、`ffmpeg`；
2. 拉取 Deep-Live-Cam，并固定到实测过的提交 `08896a5`（2026-11-08）；
3. 在 `Deep-Live-Cam/venv` 建虚拟环境并安装依赖，检查 CoreML 加速是否可用；
4. 用 curl 下载模型并核对文件大小。

第一次启动时，macOS 会请求摄像头权限，授予运行脚本的终端即可。

## 界面操作

1. **Select a face** → 选 `faces/` 下的照片；
2. 打开 **Show FPS**；
3. 选摄像头和分辨率 → 点 **Live**（不是 Start，Start 用于处理图片或视频文件）。

### 推荐设置

| 设置 | 推荐值 | 说明 |
|---|---|---|
| Transparency | 拉满 | 换脸比例 100%；拉到 0 等于关闭换脸 |
| Det size | 320×320 | 上半身取景时脸很大，320 足够，检测更快 |
| Resolution | 1280×720 | 640×480 帧率更高，但画面更糊 |
| Face Enhancer | None | 画质增强逐帧同步执行，在 Mac 上会让帧率减半以上 |
| Sharpness | 0.2–0.4 | 补偿 128px 换脸输出放大后的模糊 |
| Async swap | 视情况 | 换脸模型放到后台跑，画面更流畅，但表情和嘴型会慢一拍 |
| Poisson Blend | 视情况 | 脸和脖子之间有色差时打开 |
| Mouth Mask | 0 起步 | 保留本人嘴部区域，口型有时更自然，有时更违和 |

## 实测性能

M4 Pro（20 核 GPU）、CoreML、720p、单张脸，用 `tools/bench_live.py` 离线测得：

| 环节 | 每帧耗时 |
|---|---|
| 人脸检测（Det size 320） | 9.717ms（界面每 1–2 帧才检测一次） |
| 人脸检测（Det size 640） | 25.43ms |
| 换脸 + 贴回 | 48.96ms |
| GPEN-256 画质增强 | 57.31ms |

| 模式 | 预计帧率 |
|---|---|
| 只换脸 | 约 20.42 fps |
| 换脸 + GPEN-256 | 约 9.305 fps |
| 只用 CPU（对照） | 约 4.186 fps |

多次测量会有波动（例如 Det size 320 的检测耗时在 9.717–18.8ms 之间），以自己机器上 `tools/bench_live.py` 的实测为准。瓶颈在换脸模型本身。需要 25 fps 以上或同时开画质增强时，建议换 NVIDIA 显卡的机器。

## 工具

```bash
# 检查源脸照片：人脸数量、脸宽、角度，并生成带标注的拼图
Deep-Live-Cam/venv/bin/python tools/check_faces.py faces --sheet faces_sheet.jpg

# 离线测速（不开摄像头、不保存图片）
Deep-Live-Cam/venv/bin/python tools/bench_live.py --source faces/source_01.jpg --det 320 [--gpen256]
```

## 常见问题

**模型下载报 `CERTIFICATE_VERIFY_FAILED`**
Deep-Live-Cam 自带的 Python 下载器只信任 certifi 证书列表，在使用自定义根证书的网络里会失败。`setup.sh` 改用 curl（走 macOS 系统证书）下载，不关闭任何证书校验。如果在界面里选了没下载的画质增强模型，也会遇到这个问题，可以用 `./setup.sh --with-gpen256` 预先下载。

**加了 `-s` 参数后界面打不开**
Deep-Live-Cam 只要收到 `-s`、`-t`、`-o` 中的任何一个，就会进入无界面的批处理模式。请在界面里选源脸，`run.sh` 会拦截这几个参数。

**换出来的脸“不像照片”或偏糊**
换脸模型只用照片提取身份特征，输出分辨率为 128×128。妆容、肤色、光线沿用摄像头画面。改善办法：打光、调 Sharpness、换更清晰的源照片原图；不建议用 AI 放大源照片，那会凭空生成细节、改变五官。

## 目录结构

```
live-faceswap/
├── setup.sh              # 安装：brew 依赖、固定版本的 Deep-Live-Cam、venv、模型
├── run.sh                # 启动界面（CoreML，Det size 320）
├── faces/                # 源脸照片（AI 生成的测试图）及使用说明
├── tools/
│   ├── check_faces.py    # 源脸质检 + 拼图
│   └── bench_live.py     # 离线测速
└── Deep-Live-Cam/        # setup.sh 拉取，已在 .gitignore 中排除
```

## 上游与许可

- [Deep-Live-Cam](https://github.com/hacksider/Deep-Live-Cam)：AGPL-3.0，本仓库不包含其源码。
- [InsightFace](https://github.com/deepinsight/insightface) 模型（inswapper、buffalo_l）：仅限非商业研究。
- GPEN 模型：使用前请查阅其原始许可。
