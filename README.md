# 🌿 智慧农业地黄环境监测与病害预测系统

> 基于物联网与 AI 的怀地黄种植智能监控平台 —— 实时环境感知 · 病害风险预警 · 自动环控联动

[![GitHub](https://img.shields.io/badge/GitHub-shu005%2Fsmart--farm--dihuang-blue)](https://github.com/shu005/smart-farm-dihuang)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)](https://www.raspberrypi.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-green)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-v12n-orange)](https://docs.ultralytics.com/)

---

## 📖 项目简介

本项目面向**怀地黄（Rehmannia glutinosa）**种植场景，构建了一套"**感知 → 分析 → 预警 → 控制**"一体化的智慧农业系统。系统部署于树莓派（Raspberry Pi），通过多路传感器实时采集田间环境数据，结合 YOLO 视觉检测与专家规则引擎，实现对**根腐病、斑枯病、病毒病**等常见病害的风险预警，并联动风扇等执行器自动调控微环境。

> 项目由**河南工业大学**支持，已完成硬件 PCB 设计、SMT 贴片及实地测试。

---

## 🎯 核心功能

| 功能 | 说明 |
|------|------|
| 🌡️ **多维度环境感知** | 空气温湿度、光照强度、土壤温湿度、土壤电导率（EC），5 路传感器并行采集 |
| 📷 **AI 虫害视觉检测** | YOLOv12n 目标检测模型，实时识别田间害虫并留存证据图像 |
| 🧠 **病害风险预警** | 基于农学专家知识库的规则引擎，研判根腐病、斑枯病、轮纹病等 6 类病害风险等级 |
| 🌀 **自动环控联动** | 高温自动启动排风扇，支持手动/自动双模式切换 |
| 📊 **可视化大屏** | Web 端实时仪表盘：环境数据卡片 + 历史趋势图 + 健康评分 + 虫害警报 |
| 🗺️ **3D 部署规划** | Three.js 三维可视化展示 LoRa 一拖四传感器网络部署方案 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     📊 Web 仪表盘                        │
│              (Tailwind CSS + Chart.js)                  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP API
┌────────────────────────▼────────────────────────────────┐
│                 🖥️ Flask API 服务 (:5000)               │
│           自动环控线程 · 接口路由 · 图像服务             │
└────────┬───────────────────────────────┬────────────────┘
         │                               │
┌────────▼────────┐            ┌────────▼────────────────┐
│  🧠 分析引擎     │            │  📷 YOLO 视觉检测        │
│  FarmBrain      │            │  YOLOv12n + NCNN        │
│  专家规则库      │            │  害虫识别 + 证据留存     │
└────────┬────────┘            └────────┬────────────────┘
         │                               │
┌────────▼───────────────────────────────▼────────────────┐
│                   🗄️ SQLite 数据库                       │
│      温度 · 湿度 · 光照 · 土壤 · 虫害 · 设备状态         │
└────────┬────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────┐
│                   🔌 传感器采集层 (5 进程并行)            │
│  DS18B20  │  DHT11  │  MCP3008+LDR  │  RS485土壤  │  摄像头  │
│  空气温度  │ 空气湿度 │   光照强度     │ 土壤三参数   │ 图像采集  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 硬件清单

| 硬件 | 型号/接口 | 用途 |
|------|-----------|------|
| 主控 | Raspberry Pi 4B | 数据采集、推理、控制 |
| 温度传感器 | DS18B20（1-Wire） | 环境空气温度 |
| 湿度传感器 | DHT11（GPIO 27） | 环境空气湿度 |
| 光照传感器 | MCP3008 ADC + LDR（SPI） | 光照强度 (Lux) |
| 土壤传感器 | RS485 型 B（Modbus RTU） | 土壤温湿度 + 电导率 |
| 摄像头 | Pi Camera CSI | 虫害图像采集 |
| 风扇控制 | L293D 驱动 + 直流风扇 | 通风降温执行器 |
| 蜂鸣器 | 有源蜂鸣器（GPIO 6） | 虫害声光报警 |
| PCB | 自设计 + 嘉立创 SMT | 传感器集成底板 |

---

## 💻 技术栈

| 层级 | 技术 |
|------|------|
| 后端 API | Python 3.11+ / Flask / Flask-CORS |
| AI 推理 | Ultralytics YOLOv12n / PyTorch / NCNN |
| 数据库 | SQLite3 |
| 前端 | HTML5 / Tailwind CSS / Chart.js / Three.js |
| 硬件接口 | gpiozero / PiCamera2 / minimalmodbus / adafruit_mcp3xxx |
| 部署 | Bash Shell / cpolar 内网穿透 |

---

## 🚀 快速启动

### 环境要求

- Raspberry Pi（推荐 4B 或以上）
- Python 3.11+
- 已连接上述传感器硬件

### 安装依赖

```bash
# 安装系统依赖
sudo apt install -y python3-pip python3-picamera2

# 安装 Python 依赖
pip install flask flask-cors ultralytics gpiozero minimalmodbus adafruit-circuitpython-mcp3xxx
```

### 一键启动

```bash
cd Smart_Farm_System
chmod +x start_all.sh
./start_all.sh
```

启动后访问仪表盘：
- **实时大屏**：打开 `web/地黄数字智监测中枢（演示模式）.html`
- **API 接口**：`http://<树莓派IP>:5000/now`

### 模拟模式（无硬件测试）

```bash
# 注入模拟病害数据
cd Smart_Farm_System/drivers
python test_ingection.py
```

然后打开 `web/地黄数智能监测中枢（模拟）.html` 查看效果。

---

## 📁 项目结构

```
├── Smart_Farm_System/
│   ├── server/              # 后端服务
│   │   ├── api_server.py    # Flask API 主程序
│   │   ├── analysis_engine.py # 病害分析引擎 (FarmBrain)
│   │   └── best.pt          # YOLOv12n 模型权重
│   ├── drivers/             # 传感器驱动脚本
│   │   ├── task_temp.py     # DS18B20 温度采集
│   │   ├── task_humidity.py # DHT11 湿度采集
│   │   ├── task_light.py    # 光照采集
│   │   ├── task_soil.py     # RS485 土壤三参数采集
│   │   └── task_pest_detection.py # YOLO 虫害检测
│   ├── database/            # SQLite 数据库 + 虫害证据图片
│   ├── program_idea/        # 3D 部署方案可视化
│   ├── reference _material/ # 技术文档与设计报告
│   └── start_all.sh         # 一键启动脚本
├── best_ncnn_model/         # NCNN 边缘端优化模型
├── web/                     # 前端可视化大屏
│   ├── 地黄数字智监测中枢（演示模式）.html
│   └── 地黄数智能监测中枢（模拟）.html
├── 项目相关文件/             # PCB 设计文件 / 合同 / 手册
└── README.md
```

---

## 📈 API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/now` | GET | 最新传感器数据 + 病害分析 + 设备状态 |
| `/history` | GET | 24 点历史时序数据（用于曲线图） |
| `/control` | POST | 风扇手动控制 (`{"fan": "on"}` / `{"fan": "off"}`) |
| `/evidence/<filename>` | GET | 虫害证据图像 |

---

## 🎨 界面预览

Web 仪表盘提供：

- 🌡️ 四大环境参数实时卡片（温度 / 湿度 / 光照 / 土壤）
- 💚 环境健康指数仪表盘（0-100 分）
- ⚠️ 病害风险指示灯（根腐病 / 斑枯病）
- 🌀 风扇状态与手动控制面板
- 🐛 虫害检测告警 + 证据图像轮播
- 📈 历史趋势交互图表（支持 Chart.js 缩放）

---

## 👥 团队

- **项目来源**：河南工业大学
- **应用领域**：怀地黄中药材种植智能化管理

---

## 📄 License

本项目仅用于学术研究与教育目的。

---

> 🌱 让传统中药材种植，插上物联网与人工智能的翅膀。
