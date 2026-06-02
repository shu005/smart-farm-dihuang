from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import sys
import threading
import time

# ================= 🔌 硬件控制配置 (L293D) =================
try:
    from gpiozero import Motor, OutputDevice
    GPIO_AVAILABLE = True
    # 您的 L293D 引脚配置
    enable_pin = OutputDevice(19, initial_value=True)
    fan_motor = Motor(forward=20, backward=18, pwm=True)
except ImportError:
    print("❌ 警告: 未检测到 gpiozero，将使用模拟模式")
    GPIO_AVAILABLE = False
    fan_motor = None

# ================= 🔧 核心配置 =================
app = Flask(__name__)
CORS(app)

PROJECT_ROOT = '/home/henan/Desktop/Smart_Farm_System'
DB_PATH = os.path.join(PROJECT_ROOT, 'database', 'smart_farm.db')
EVIDENCE_FOLDER = os.path.join(PROJECT_ROOT, 'database', 'evidence_images')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 引入算法大脑
try:
    from analysis_engine import FarmBrain
    brain = FarmBrain(DB_PATH)
except ImportError:
    brain = None

# ================= 🎮 设备状态管理 (全局变量) =================
# 这里存储设备的真实状态，是网页和硬件的“中间人”
DEVICE_STATE = {
    'fan_is_on': False,     # 开关状态 (True/False)
    'fan_mode': 'auto',     # 模式: 'auto'(自动温控) / 'manual'(手动强制)
    'fan_speed': 0.0,       # 当前速度
    'fan_direction': 'stop' # 方向
}

# ================= 🛠️ 硬件执行函数 =================
def execute_fan(speed, direction):
    """底层驱动执行函数：真正去转动电机"""
    # 更新全局状态（让网页能看到）
    DEVICE_STATE['fan_speed'] = speed
    DEVICE_STATE['fan_direction'] = direction
    DEVICE_STATE['fan_is_on'] = (speed > 0)

    if not GPIO_AVAILABLE: return

    if speed == 0:
        fan_motor.stop()
    elif direction == 'forward':
        fan_motor.forward(speed)
    elif direction == 'backward':
        fan_motor.backward(speed)

# ================= 🧠 自动温控线程 (后台运行) =================
def auto_control_loop():
    """后台线程：每3秒检查一次温度，如果是自动模式，就控制风扇"""
    print("🤖 智能温控后台线程已启动...")
    while True:
        try:
            # 只有在【自动模式】下，才由温度决定
            if DEVICE_STATE['fan_mode'] == 'auto':
                # 1. 读最新温度
                if os.path.exists(DB_PATH):
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM table_temp ORDER BY id DESC LIMIT 1")
                    row = cur.fetchone()
                    conn.close()
                    
                    if row:
                        current_temp = row[0]
                        # 🔥 简化的温控逻辑
                        if current_temp > 30.0:
                            # 高温全速正转
                            execute_fan(1.0, 'forward')
                        elif current_temp > 25.0:
                            # 中温低速排气
                            execute_fan(0.5, 'forward')
                        else:
                            # 低温停止
                            execute_fan(0.0, 'stop')
            
            time.sleep(3) # 每3秒检查一次
        except Exception as e:
            print(f"自动控制出错: {e}")
            time.sleep(5)

# 启动后台线程
t = threading.Thread(target=auto_control_loop, daemon=True)
t.start()

# ================= 辅助函数 (保持不变) =================
def get_latest_value(cursor, table):
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone(): return (0, "N/A")
        cursor.execute(f"SELECT value, timestamp FROM {table} ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return (row[0], row[1]) if row else (0, "N/A")
    except: return (0, "N/A")

def get_latest_soil(cursor):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='table_soil'")
        if not cursor.fetchone(): return (0, 0, 0)
        cursor.execute("SELECT soil_temp, soil_hum, soil_ec FROM table_soil ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row: return row[0], row[1], row[2]
        return (0, 0, 0)
    except: return (0, 0, 0)

def get_latest_pest(cursor):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='table_pest'")
        if not cursor.fetchone(): return None
        cursor.execute("SELECT timestamp, class_name, image_file FROM table_pest ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row: return {"time": row[0], "type": row[1], "image": row[2]}
        return None
    except: return None

def get_history_list(cursor, table, limit=24):
    try:
        cursor.execute(f"SELECT value, timestamp FROM {table} ORDER BY id DESC LIMIT {limit}")
        return cursor.fetchall()[::-1]
    except: return []

def get_history_soil(cursor, limit=24):
    try:
        cursor.execute(f"SELECT soil_temp, soil_hum, soil_ec FROM table_soil ORDER BY id DESC LIMIT {limit}")
        return cursor.fetchall()[::-1]
    except: return []

# ================= 🚀 API 接口 =================

@app.route('/')
def index():
    return "🚀 Smart Farm API (IoT Control Enabled)"

@app.route('/evidence/<path:filename>')
def serve_evidence(filename):
    return send_from_directory(EVIDENCE_FOLDER, filename)

# 🔥 新增：设备控制接口 (接收网页指令)
@app.route('/control', methods=['POST'])
def control_device():
    """
    接收网页发来的控制指令
    数据格式: {"device": "fan", "action": "on"}
    """
    data = request.json
    target = data.get('device')
    action = data.get('action') # 'on', 'off'
    
    if target == 'fan':
        # 只要人为控制了，就切换到【手动模式】，防止自动逻辑马上把它改回去
        DEVICE_STATE['fan_mode'] = 'manual'
        
        if action == 'on':
            execute_fan(1.0, 'forward') # 手动开启 = 全速
            print("👋 [手动] 网页指令 -> 开启风扇")
        elif action == 'off':
            execute_fan(0.0, 'stop')    # 手动关闭
            print("👋 [手动] 网页指令 -> 关闭风扇")
            
    return jsonify({"status": "success", "state": DEVICE_STATE})

@app.route('/now', methods=['GET'])
def get_now():
    if not os.path.exists(DB_PATH): return jsonify({"error": "No DB"}), 500
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    air_temp, time_val = get_latest_value(cur, 'table_temp')
    air_hum, _ = get_latest_value(cur, 'table_hum')
    light, _ = get_latest_value(cur, 'table_light')
    soil_temp, soil_hum, soil_ec = get_latest_soil(cur)
    pest_info = get_latest_pest(cur)
    conn.close()

    # 算法分析
    analysis_result = {
        "score": 90, "limit_factor": "数据同步中...", 
        "suggestion": "系统正在接入传感器数据...", "risk_root": "低风险", "risk_spot": "低风险"
    }
    if brain:
        sensor_pack = {'air_temp': air_temp, 'air_hum': air_hum, 'light': light, 'soil_temp': soil_temp, 'soil_hum': soil_hum, 'soil_ec': soil_ec}
        analysis_result = brain.analyze(sensor_pack)

    # 🔥 状态转换：生成显示给网页看的文字
    fan_text = "已停止"
    if DEVICE_STATE['fan_is_on']:
        fan_text = "运行中"
    
    # 加上模式标记
    fan_text += " (自动)" if DEVICE_STATE['fan_mode'] == 'auto' else " (手动)"

    data = {
        "air_temp": round(air_temp, 1),
        "air_hum":  round(air_hum, 1),
        "light":    int(light),
        "soil_temp": round(soil_temp, 1),
        "soil_hum":  round(soil_hum, 1),
        "soil_ec":   int(soil_ec),
        "timestamp": time_val.split(' ')[1] if ' ' in str(time_val) else str(time_val),
        
        "env_score": analysis_result['score'],
        "limit_factor": analysis_result['limit_factor'],
        "suggestion": analysis_result['suggestion'],
        "risk_root": analysis_result['risk_root'],
        "risk_spot": analysis_result['risk_spot'],
        "growth_stage": analysis_result.get('stage_name', "块茎膨大期"),
        
        # 🔥 关键：上传真实状态给网页
        "fan_status": fan_text,              # 文字描述 (例如：运行中 (自动))
        "fan_is_on": DEVICE_STATE['fan_is_on'], # 开关状态 (True/False)
        
        "pump_status": "待机中",
        "light_status": "关闭",
        "pest_data": pest_info 
    }
    return jsonify(data)

@app.route('/history', methods=['GET'])
def get_history():
    # ... (保持原有的 get_history 逻辑不变，用于画图) ...
    if not os.path.exists(DB_PATH): return jsonify({"error": "No DB"}), 500
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    LIMIT = 24
    raw_temp = get_history_list(cur, 'table_temp', LIMIT)
    raw_hum  = get_history_list(cur, 'table_hum', LIMIT)
    raw_light= get_history_list(cur, 'table_light', LIMIT)
    raw_soil = get_history_soil(cur, LIMIT)
    conn.close()
    time_labels = []
    source = raw_temp if raw_temp else (get_history_list(cur, 'table_soil', LIMIT) if raw_soil else [])
    for r in source:
        t = r[1] if len(r)>1 else ""
        time_labels.append(t.split(' ')[1][:5] if ' ' in t else t)
    if raw_soil:
        s_temp = [r[0] for r in raw_soil]
        s_hum = [r[1] for r in raw_soil]
        s_ec = [r[2] for r in raw_soil]
    else:
        s_temp, s_hum, s_ec = [], [], []
    return jsonify({
        "time": time_labels,
        "air_temp": [r[0] for r in raw_temp],
        "air_hum": [r[0] for r in raw_hum],
        "light": [r[0] for r in raw_light],
        "soil_temp": s_temp, "soil_hum": s_hum, "soil_ec": s_ec 
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
