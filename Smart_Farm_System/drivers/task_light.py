import time
import math
import sqlite3
import busio
import digitalio
import board
from datetime import datetime  # 👈 必须导入这个库
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

# ================= 配置 =================
DB_PATH = '/home/henan/Desktop/Smart_Farm_System/database/smart_farm.db'

# SPI 初始化
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D25) 
try:
    mcp = MCP.MCP3008(spi, cs)
    light_channel = AnalogIn(mcp, MCP.P0)
except:
    print("❌ SPI 连接失败，请检查接线。")
    exit()

# 物理参数
R_FIXED = 10000
V_REF = 3.3
GAMMA = 0.7
RL10 = 25000                                                                                                    

# ================= 核心功能 =================
def get_lux(voltage):
    if voltage <= 0.02 or voltage >= V_REF - 0.02: return 0
    R_ldr = (voltage * R_FIXED) / (V_REF - voltage)
    try:
        return math.pow(10, (math.log10(RL10) - math.log10(R_ldr)) / GAMMA + 1)
    except:
        return 0

def save_to_db(lux_value):
    try:
        # 🟢 获取当前北京时间
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS table_light 
                           (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            timestamp DATETIME, 
                            value REAL)''')
            
            # 🟢 显式插入时间
            conn.execute("INSERT INTO table_light (timestamp, value) VALUES (?, ?)", (local_time, lux_value))
        
        print(f"✅ [Light] {local_time} -> {lux_value:.1f} Lux")
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")

# ================= 主程序 =================
print("🚀 MCP3008 光照采集已启动...")

try:
    while True:
        volts = light_channel.voltage
        lux = get_lux(volts)
        save_to_db(lux)
        time.sleep(2) # 2秒一次

except KeyboardInterrupt:
    print("\n🛑 程序已停止")
except Exception as e:
    print(f"运行出错: {e}")