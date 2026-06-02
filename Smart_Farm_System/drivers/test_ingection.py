import sqlite3
import random
import os
from datetime import datetime, timedelta

# 数据库路径
DB_PATH = '/home/henan/Desktop/Smart_Farm_System/database/smart_farm.db'

def inject_root_rot_data():
    print("💉 正在注入【根腐病】高危数据 (模拟过去24小时)...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 模拟过去 25 小时的数据，每小时一条
    # 设定环境：土温 29℃ (高危)，土湿 40% (高危)，EC 3.0 (高危)
    now = datetime.now()
    
    for i in range(25):
        # 从25小时前开始，一直到现在
        fake_time = (now - timedelta(hours=25-i)).strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入土壤表
        cursor.execute(
            "INSERT INTO table_soil (timestamp, soil_temp, soil_hum, soil_ec) VALUES (?, ?, ?, ?)",
            (fake_time, 29.5, 45.0, 3.1)
        )
        
        # 写入空气表 (顺便模拟一下高温)
        cursor.execute(
            "INSERT INTO table_temp (timestamp, value) VALUES (?, ?)",
            (fake_time, 36.5)
        )

    conn.commit()
    conn.close()
    print("✅ 注入完成！您的数据库现在包含了'严重的根腐病前兆'数据。")

if __name__ == "__main__":
    inject_root_rot_data()