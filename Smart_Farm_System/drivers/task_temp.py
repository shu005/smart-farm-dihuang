import time
import sqlite3
import glob
import os
from datetime import datetime

# ================= 🔧 基础配置 =================
DB_PATH = '/home/henan/Desktop/Smart_Farm_System/database/smart_farm.db'

# ================= 🌡️ 传感器初始化 (保持您原有的逻辑) =================
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
try:
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'
except:
    print("❌ 错误：未找到 DS18B20 温度传感器！")
    device_file = None

def read_temp_raw():
    try:
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
    except:
        return []

def read_temp():
    """读取 DS18B20 温度"""
    if device_file is None: return None
    try:
        lines = read_temp_raw()
        if not lines: return None
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            return float(lines[1][equals_pos+2:]) / 1000.0
    except:
        return None

def save_to_db(val):
    """保存温度到数据库"""
    try:
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS table_temp 
                           (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            timestamp DATETIME, 
                            value REAL)''')
            conn.execute("INSERT INTO table_temp (timestamp, value) VALUES (?, ?)", 
                         (local_time, val))
        return local_time
    except Exception as e:
        print(f"DB Error: {e}")
        return None

# ================= 🚀 主循环 =================
if __name__ == '__main__':
    print(f"🚀 温度采集服务已启动 (PID: {os.getpid()})")
    
    while True:
        temp = read_temp()
        if temp is not None:
            t_str = save_to_db(temp)
            if t_str:
                print(f"[{t_str}] 🌡️当前气温: {temp:.2f}°C")
        else:
            print("⚠️ 传感器读取失败")
            
        time.sleep(2) # 每2秒采集一次
