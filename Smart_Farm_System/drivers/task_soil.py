import time
import sqlite3
import minimalmodbus
import serial
import os
from datetime import datetime

# ================= 🔧 最终校准参数 (已验证) =================
# 传感器型号: Model B (0=湿度, 1=温度)
SENSOR_MODEL = 'B'

# 湿度校准系数: 原始值 700 -> 70.0%
HUM_DIVIDER = 10.0 

# 温度校准系数: 原始值 271 -> 27.1℃
TEMP_DIVIDER = 10.0

# ================= ⚙️ 系统配置 =================
DB_PATH = '/home/henan/Desktop/Smart_Farm_System/database/smart_farm.db'
SERIAL_PORT = '/dev/ttyUSB0'
SLAVE_ADDRESS = 1
BAUDRATE = 4800

def init_sensor():
    """初始化传感器连接"""
    try:
        instr = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ADDRESS)
        instr.serial.baudrate = BAUDRATE
        instr.serial.bytesize = 8
        instr.serial.parity   = serial.PARITY_NONE
        instr.serial.stopbits = 1
        instr.serial.timeout  = 1.0 # 1秒超时
        instr.mode = minimalmodbus.MODE_RTU
        instr.serial.reset_input_buffer()
        return instr
    except Exception as e:
        print(f"❌ 串口初始化失败: {e}")
        return None

# 全局传感器对象
sensor = init_sensor()

def save_to_db(temp, hum, ec):
    """将数据存入 SQLite 数据库"""
    try:
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # 自动建表（如果不存在）
            conn.execute('''CREATE TABLE IF NOT EXISTS table_soil 
                           (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            timestamp DATETIME, 
                            soil_temp REAL,
                            soil_hum REAL,
                            soil_ec INTEGER)''')
            # 插入数据
            conn.execute("INSERT INTO table_soil (timestamp, soil_temp, soil_hum, soil_ec) VALUES (?, ?, ?, ?)", 
                         (local_time, temp, hum, ec))
        return local_time
    except Exception as e:
        print(f"💾 数据库写入错误: {e}")
        return None

# ================= 🚀 主程序循环 =================
if __name__ == '__main__':
    print(f"🚀 土壤墒情监测服务已启动 (PID: {os.getpid()})")
    print(f"📍 配置: Model-{SENSOR_MODEL} | 湿度/{HUM_DIVIDER} | 温度/{TEMP_DIVIDER}")
    print("------------------------------------------------------")

    while True:
        try:
            # 1. 传感器掉线重连机制
            if sensor is None:
                sensor = init_sensor()
                time.sleep(5)
                continue

            # 2. 读取寄存器 (读取 3 个数据：湿度、温度、电导率)
            # Function Code 03, Address 0, Length 3
            values = sensor.read_registers(0, 3, functioncode=3)
            
            # 3. 数据解析 (Model B)
            raw_hum = values[0]
            raw_temp = values[1]
            raw_ec = values[2]

            # --- 温度计算 (含负数补码处理) ---
            if raw_temp > 32768:
                raw_temp = raw_temp - 65536
            soil_temp = raw_temp / TEMP_DIVIDER

            # --- 湿度计算 ---
            soil_hum = raw_hum / HUM_DIVIDER
            # 限制范围 0-100%
            if soil_hum > 100: soil_hum = 100.0
            if soil_hum < 0: soil_hum = 0.0

            # --- 电导率 ---
            soil_ec = raw_ec

            # 4. 存入数据库
            t_str = save_to_db(soil_temp, soil_hum, soil_ec)
            
            # 5. 打印日志
            if t_str:
                print(f"[{t_str}] ✅ 监测正常 -> 🌡️温度: {soil_temp:.1f}℃ | 💧湿度: {soil_hum:.1f}% | ⚡EC: {soil_ec} us/cm")
            
        except IOError:
            print("⚠️ 传感器通信超时 (正在重试...)")
            # 遇到通信错误，稍微等久一点再试，或者尝试重置对象
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 运行异常: {e}")
            time.sleep(3)
            
        # 采集频率：每 3 秒一次
        time.sleep(2)