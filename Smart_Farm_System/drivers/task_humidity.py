import time
import board
import adafruit_dht
import sqlite3
import subprocess
import os
from datetime import datetime

# ================= 配置区域 =================
# 数据库路径
DB_PATH = '/home/henan/Desktop/Smart_Farm_System/database/smart_farm.db'

# 引脚设置 (使用您指定的 GPIO 27)
PIN = board.D27

# ================= 🛡️ 自动清理函数 =================
def force_cleanup():
    """启动前清理残留的 libgpiod 进程，防止 DHT11 报错"""
    try:
        subprocess.run(['sudo', 'killall', 'libgpiod_pulsein'], 
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        time.sleep(1)
    except Exception:
        pass

# ================= 数据库写入函数 =================
def save_to_db(hum_val):
    try:
        # 1. 获取北京时间
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # 2. 创建表 (如果不存在)
            conn.execute('''CREATE TABLE IF NOT EXISTS table_hum 
                           (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            timestamp DATETIME, 
                            value REAL)''')
            
            # 3. 写入数据
            conn.execute("INSERT INTO table_hum (timestamp, value) VALUES (?, ?)", (local_time, hum_val))
            
        print(f"💧 [DHT11] {local_time} -> 湿度: {hum_val:.1f} %")
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")

# ================= 主程序 =================
if __name__ == '__main__':
    print("🚀 DHT11 湿度采集 (入库版) 启动...")
    print(f"📍 引脚: GPIO 27 | 💾 数据库: smart_farm.db")
    
    # 1. 先清理环境
    force_cleanup()

    # 2. 初始化传感器
    try:
        sensor = adafruit_dht.DHT11(PIN, use_pulseio=False)
    except Exception as e:
        print(f"❌ 传感器初始化失败: {e}")
        exit()

    while True:
        try:
            # 3. 读取湿度
            humidity = sensor.humidity
            
            # 4. 存入数据库
            if humidity is not None:
                save_to_db(humidity)
            else:
                print("⚠️ 读取为空 (忽略)")
                
        except RuntimeError as error:
            # DHT11 读取失败是非常正常的 (Checksum error 等)，忽略即可
            # print(f"临时错误: {error.args[0]}")
            time.sleep(1)
            continue
            
        except Exception as error:
            print(f"❌ 严重错误: {error}")
            # 如果遇到严重错误，销毁对象并尝试重连
            try:
                sensor.exit()
                force_cleanup()
                time.sleep(1)
                sensor = adafruit_dht.DHT11(PIN, use_pulseio=False)
            except:
                pass

        # 5. 休息 3 秒
        time.sleep(2)