#!/bin/bash

# 定义基础路径 (根据您的实际情况)
BASE_DIR="/home/henan/Desktop/Smart_Farm_System"

echo "=========================================="
echo "   正在启动地黄产业数智监测系统..."
echo "=========================================="

# 1. 清理旧进程 (防止重复启动报错)
echo "1. 清理后台残留进程..."
sudo pkill -f api_server.py
sudo pkill -f task_temp.py
sudo pkill -f task_light.py
sudo pkill -f task_humidity.py
sudo pkill -f task_soil.py
sudo pkill -f task_pest_detection.py  # <--- 新增这一行

# 清理底层驱动残留 (防止 DHT11 报错)
pkill -f libgpiod_pulsein

# 等待2秒，让资源释放
sleep 2

# 2. 启动后端 API 服务
echo "2. 启动 API 服务器..."
python3 $BASE_DIR/server/api_server.py > /dev/null 2>&1 &

# 3. 启动各个驱动模块
echo "3. 启动传感器驱动..."

# (1) 空气温控 + 风扇
echo "   -> 启动空气温控 (L293D)..."
python3 $BASE_DIR/drivers/task_temp.py > /dev/null 2>&1 &

# (2) 土壤传感器 (RS485)
echo "   -> 启动土壤传感器..."
python3 $BASE_DIR/drivers/task_soil.py > /dev/null 2>&1 &

# (3) 光照传感器（光敏电阻）
echo "   -> 启动 MCP3008 (光照)..."
python3 $BASE_DIR/drivers/task_light.py &

# (4) 湿度传感器（DHT11）
echo "   -> 启动 DHT11 (湿度)..."  
python3 $BASE_DIR/drivers/task_humidity.py &

# (5) 病虫害监测 (YOLO摄像头) - 新增
echo "   -> 启动病虫害AI监测..."
# 注意：摄像头启动较慢，且占用资源，放在最后
python3 $BASE_DIR/drivers/task_pest_detection.py > /dev/null 2>&1 &

echo "=========================================="
echo "✅ 所有服务已启动!"
echo "💡 请使用 cpolar http 5000 穿透内网"
echo "=========================================="