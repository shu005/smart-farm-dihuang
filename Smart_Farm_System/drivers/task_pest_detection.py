import time
import cv2
import os
import csv
import sqlite3
from datetime import datetime
from picamera2 import Picamera2
from ultralytics import YOLO
from gpiozero import Buzzer

# ================= ⚙️ 核心配置区域 =================

# 1. 硬件引脚
BUZZER_PIN = 6  # 务必确认接在 GPIO 6

# 2. 识别参数
# "wormhole" 必须和您训练模型时的标签一致
TARGET_CLASSES = ["item"]  
CONF_THRESHOLD = 0.5   # 置信度
SAVE_INTERVAL = 3.0    # 报警冷却时间 (秒)

# 3. 📂 路径配置 (使用绝对路径，确保稳定)
# 项目根目录
PROJECT_ROOT = '/home/henan/Desktop/Smart_Farm_System'

# [输入] 模型文件路径 -> server 文件夹
MODEL_PATH = os.path.join(PROJECT_ROOT, 'server', 'best.pt')

# [输出] 图片保存路径 -> database/evidence_images 文件夹 (方案B核心：图存这里)
IMAGE_DIR = os.path.join(PROJECT_ROOT, 'database', 'evidence_images')

# [输出] 日志文件路径
LOG_FILE = os.path.join(PROJECT_ROOT, 'database', 'detection_log.csv')
DB_PATH = os.path.join(PROJECT_ROOT, 'database', 'smart_farm.db')

# ===================================================

def init_hardware():
    print("🔌 正在初始化硬件...")
    try:
        # active_high=False: 适配低电平触发蜂鸣器
        bz = Buzzer(BUZZER_PIN, initial_value=False, active_high=False)
        # 启动自检
        bz.beep(on_time=0.2, off_time=0.2, n=2)
        return bz
    except Exception as e:
        print(f"❌ 蜂鸣器初始化失败: {e}")
        return None

def init_camera():
    print("📷 正在初始化摄像头...")
    try:
        picam = Picamera2()
        config = picam.create_preview_configuration(main={"size": (640, 640), "format": "BGR888"})
        picam.configure(config)
        picam.start()
        return picam
    except Exception as e:
        print(f"❌ 摄像头启动失败: {e}")
        exit(1)

# 🔥 方案B核心函数：只存文件名到数据库
def save_alert_to_db(class_name, confidence, filename):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # 建立表结构：image_file 是 TEXT 类型，只存名字
            conn.execute('''CREATE TABLE IF NOT EXISTS table_pest 
                           (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            timestamp DATETIME, 
                            class_name TEXT,
                            confidence REAL,
                            image_file TEXT)''')
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO table_pest (timestamp, class_name, confidence, image_file) VALUES (?, ?, ?, ?)", 
                         (timestamp, class_name, confidence, filename))
            print(f"✅ 数据库记录已添加: {filename}")
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")

def main():
    # 1. 准备环境
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR, exist_ok=True)
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            csv.writer(f).writerow(["Time", "Class", "Confidence", "Image_Filename"])

    # 2. 初始化
    buzzer = init_hardware()
    picam2 = init_camera()

    # 3. 加载模型
    print(f"🧠 加载模型: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 错误：找不到模型文件！请确认路径。")
        exit(1)
        
    try:
        model = YOLO(MODEL_PATH)
    except Exception as e:
        print(f"❌ 模型加载出错: {e}")
        exit(1)

    print("🚀 监测启动中 (方案B: 图片存硬盘，路径存数据库)...")
    last_save_time = 0

    try:
        while True:
            frame = picam2.capture_array()
            results = model(frame, imgsz=320, conf=CONF_THRESHOLD, verbose=False)
            
            detected = False
            target_info = None

            if len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    cls_id = int(box.cls)
                    name = model.names[cls_id]
                    conf = float(box.conf)
                    if TARGET_CLASSES is None or name in TARGET_CLASSES:
                        detected = True
                        target_info = (name, conf)
                        break 

            if detected:
                # ==========================================
                # 👇👇👇 修改区域：蜂鸣器急促双响逻辑 👇👇👇
                # ==========================================
                if buzzer:
                    print(f"⚠️ 发现 {target_info[0]}! 报警!")
                    
                    # 之前的 beep 是后台运行，现在改为前台控制节奏
                    # 节奏：嘀-嘀-...... (占用约0.4秒)
                    
                    buzzer.on()      # 响
                    time.sleep(0.1)
                    buzzer.off()     # 停
                    time.sleep(0.1)
                    
                    buzzer.on()      # 响
                    time.sleep(0.1)
                    buzzer.off()     # 停
                    
                    # 稍微停顿一下，避免连成一片
                    time.sleep(0.1)
                # ==========================================
                
                # 2. 证据留存
                if time.time() - last_save_time > SAVE_INTERVAL:
                    class_name, conf = target_info
                    
                    annotated = results[0].plot()
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{class_name}_{timestamp_str}.jpg"
                    
                    # A. 图片物理存到文件夹
                    save_path = os.path.join(IMAGE_DIR, filename)
                    cv2.imwrite(save_path, annotated)
                    
                    # B. 文件名存到数据库 (方案B)
                    save_alert_to_db(class_name, conf, filename)
                    
                    # C. 写日志备份
                    with open(LOG_FILE, 'a', newline='') as f:
                        csv.writer(f).writerow([timestamp_str, class_name, f"{conf:.2f}", filename])
                    
                    print(f"💾 证据已保存: {filename}")
                    last_save_time = time.time()
            else:
                if buzzer and buzzer.is_active:
                    buzzer.off()

            # 这里不需要太长的 sleep，因为上面的报警逻辑已经有延时了
            # 如果没检测到，快速进入下一帧
            if not detected:
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n👋 用户停止")
    finally:
        picam2.stop()
        if buzzer: buzzer.off()

if __name__ == "__main__":
    main()