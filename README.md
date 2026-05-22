# 霓虹弹珠竞速 (Neon Race)

## 作者：[@依然匹萨吧](https://space.bilibili.com/6297797)

## 功能介绍

**[演示视频](https://www.bilibili.com/video/BV1LrGC67EXY)**

**霓虹弹珠竞速 (Neon Race)** 是一款基于 PyQt6 和 Pymunk 物理引擎开发的桌面级弹珠竞速模拟软件。灵感来源于 **Simple Marble Race**，它将硬核的刚体物理模拟与炫酷的霓虹发光视觉效果相结合，并支持随音乐律动的视听反馈，为你带来极具观赏性的弹珠比赛体验。

### 1. 自定义赛道构建
- **多形态模块**：内置丰富的趣味赛段模块，如扇形传送门 (Sector Portals)、弹珠漏斗 (Plinko Funnel)、旋转分离环 (Rotating Split Rings)、脉冲阵列 (Pulsing Balls Array)、挡板迷宫 (Baffle Maze) 和齿轮室 (Replica Gear Chamber) 等。
- **自由编排**：支持在可视化 UI 界面中自由添加、删除、排序赛段，更提供了一键 **“Randomize (随机化)”** 生成随机赛道组合功能。

### 2. 个性化弹珠配置
- **多弹珠同场**：支持 2~12 颗弹珠同台竞速。
- **全面自定义**：每颗弹珠可独立设置名称、专属的霓虹颜色、外观皮肤（支持导入 png/jpg 图像素材），以及专属的 BGM（音乐文件）。

### 3. 视听律动视效
- **动态霓虹光效**：利用底层 Catmull-Rom 样条曲线插值和多层高斯模糊缓存技术，实现了高性能的 2D 霓虹发光渲染，并支持赛道起终点颜色的极坐标渐变配置。
- **音乐节拍反馈**：内置实时音频峰值检测引擎（AudioPeakThread），物理环境中的光效会根据当前弹珠 BGM 的音量大小与节奏实时产生律动反馈（Beat Ripple），实时播放当前领先的小球的音乐，省去了后期配乐剪辑的麻烦。

## 文件说明

```text
├── main.py                       # 主程序入口及游戏核心物理、渲染引擎
├── build.spec                    # PyInstaller 打包配置
├── requirements.txt              # Python 依赖列表
├── run.bat                       # Windows 快速启动脚本
├── run.sh                        # Linux/macOS 快速启动脚本
├── README.md                     # 项目说明文件
├── LICENSE                       # 许可证文件
└── neon_race.ico                 # 游戏图标文件
```

## 环境要求

- **操作系统**: Windows 10/11, macOS, 或 Linux
- **Python**: 3.10 或更高版本
- **底层依赖**: 依赖 PyQt6 进行硬件加速渲染及多媒体播放，依赖 Pymunk 进行 2D 物理碰撞及运动计算。

## 快速开始

### 运行发布版本（EXE）
直接下载最新打包版本的执行文件及依赖压缩包，解压后双击运行主程序即可体验。

### 从源码运行

**方法一**：
在 Windows 环境下，直接双击运行项目目录中的 [`run.bat`](run.bat)。
在 macOS/Linux 环境下，通过终端执行 `./run.sh`。

**方法二（手动纯命令行操作）**：

1. **获取项目代码**
   
   ```bash
   git clone https://github.com/PizzaDark/NeonRace.git
cd NeonRace
   ```
   
2. **安装依赖**
   ```bash
   # 推荐使用 Python 3.10+
   python -m venv .venv
   .venv\Scripts\activate # Windows
   source .venv/bin/activate # macOS/Linux
   
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

## 构建可执行文件

本项目支持使用 PyInstaller 打包为独立的桌面程序：

```bash
pyinstaller build.spec
```

打包完成后，独立的 `.exe` 程序及相关依赖将生成在 `dist/` 目录下。

## 依赖库

| 依赖包 | 用途 |
|--------|------|
| PyQt6 | 核心 GUI 界面构建、QGraphicsScene 光效实时渲染及音视频媒体播放 |
| pymunk | 2D 物理引擎底座，负责引力、各类多边形挡板碰撞、摩擦力等核心物理计算 |
| numpy | 用于音频数据流计算与音乐节拍律动峰值提取分析 (AudioPeakThread) |

## 声明与开源许可证

**声明：本软件免费且非官方，禁止商用贩卖，使用代表同意自行承担所有后果。**

本项目采用 **[知识共享 署名 - 非商业性使用 - 相同方式共享 4.0 国际许可证 (CC BY-NC-SA 4.0)](LICENSE)** 授权。

### 核心条款说明

1. **允许的行为**：你可以自由复制、修改、分发本项目的代码 / 程序，前提是满足以下条件；
2. **禁止的行为**：严禁将本项目（包括修改后的衍生版本）用于任何商业目的（如出售、付费分发、商业运营等）；
3. **必须遵守**：
   - **署名**：必须保留原作者信息（[@依然匹萨吧](https://space.bilibili.com/6297797)）；
   - **相同方式共享**：若你修改 / 衍生本项目，必须采用与本协议相同的许可证发布。

请查看官方协议全文：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans

本项目仅供学习交流使用，禁止商用或贩卖。