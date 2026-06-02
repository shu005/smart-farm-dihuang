import sqlite3
from datetime import datetime, timedelta

# ================= 📜 专家知识库 (基于三份报告深度融合) =================
CONFIG = {
    # --- 传感器物理阈值校准 ---
    'SENSOR_CALIBRATION': {
        'SOIL_WET_LIMIT': 38,  # 只有超过这个值才算"渍水"
        'SOIL_DRY_LIMIT': 15,  # 低于这个值算"干旱"
        'HIGH_RH_CHRONIC': 75, # 慢性高湿阈值
        'HIGH_RH_ACUTE': 90    # 急性高湿阈值
    },

    # --- 1. 土壤病害 (根部) ---
    'ROOT_ROT': { 
        'TEMP_MIN': 15, 'TEMP_MAX': 25, 
        'DURATION': 48, 
        'TEMP_STRESS': 28 
    },
    'PHYTOPHTHORA': { 
        'TEMP_MIN': 15, 'TEMP_MAX': 20, 
        'DURATION': 48
    },

    # --- 2. 叶部病害 (冠层) ---
    'LEAF_SPOT': { 
        'TEMP_MIN': 18, 'TEMP_MAX': 25,
        'LIGHT_WEAK': 20000, 
        'DURATION_CHRONIC': 48, 
        'DURATION_ACUTE': 12    
    },
    'RING_ROT': { 
        'TEMP_MIN': 20, 'TEMP_MAX': 30,
        'DURATION': 48
    },
    'ANTHRACNOSE': { 
        'TEMP_MIN': 20, 'TEMP_MAX': 28
    },

    # --- 3. 虫害与病毒 (干旱诱发) ---
    'VIRUS_APHID': {
        'TEMP_MIN': 20, 'TEMP_MAX': 28,
        'AIR_HUM_MAX': 50, 
        'DURATION': 168    
    },

    # --- 4. 生理性病害 (环境胁迫) ---
    'ABIOTIC': {
        'EC_LIMIT': 2500,  
        'SUNBURN_TEMP': 35,
        'SUNBURN_LIGHT': 80000 
    }
}

class FarmBrain:
    def __init__(self, db_path):
        self.db_path = db_path

    # --- 🕒 核心工具：计算持续时间 ---
    def _calculate_duration(self, table, condition, hours_back):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                time_threshold = (datetime.now() - timedelta(hours=hours_back)).strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp > ?", (time_threshold,))
                res = cursor.fetchone()
                total = res[0] if res else 0
                if total == 0: return 0, 0, 0.0
                
                query = f"SELECT COUNT(*) FROM {table} WHERE timestamp > ? AND {condition}"
                cursor.execute(query, (time_threshold,))
                bad_res = cursor.fetchone()
                bad_count = bad_res[0] if bad_res else 0
                
                return bad_count, total, bad_count / total
        except Exception as e:
            print(f"DB Query Error: {e}")
            return 0, 0, 0.0

    # --- 1. 根腐病 ---
    def check_root_rot(self, st, sh, ec):
        cfg = CONFIG['ROOT_ROT']
        cal = CONFIG['SENSOR_CALIBRATION']
        
        if sh < cal['SOIL_WET_LIMIT']: return "低风险", []
        
        reasons = []
        risk = "低风险"

        if st > cfg['TEMP_STRESS']:
            _, _, ratio = self._calculate_duration('table_soil', f"soil_temp > {cfg['TEMP_STRESS']} AND soil_hum > {cal['SOIL_WET_LIMIT']}", 24)
            if ratio > 0.8: 
                return "高风险", ["致命组合：高温(>28℃)且积水，根系面临窒息"]

        if cfg['TEMP_MIN'] <= st <= cfg['TEMP_MAX']:
            _, _, ratio = self._calculate_duration('table_soil', f"soil_temp BETWEEN {cfg['TEMP_MIN']} AND {cfg['TEMP_MAX']} AND soil_hum > {cal['SOIL_WET_LIMIT']}", cfg['DURATION'])
            hours = ratio * cfg['DURATION']
            
            if hours > 36: 
                risk = "高风险"
                reasons.append(f"湿热环境已持续 {hours:.1f}小时，适宜镰刀菌繁殖")
            elif hours > 12:
                risk = "中风险"
                reasons.append(f"土壤持续潮湿，根腐病风险上升")

        if ec > CONFIG['ABIOTIC']['EC_LIMIT']:
            reasons.append(f"盐分过高(EC>{ec})造成根系微伤口，加速侵染")
            if risk == "中风险": risk = "高风险"

        return risk, reasons

    # --- 2. 斑枯病 ---
    def check_leaf_spot(self, at, ah, light):
        cfg = CONFIG['LEAF_SPOT']
        cal = CONFIG['SENSOR_CALIBRATION']
        
        if at < cfg['TEMP_MIN'] or at > cfg['TEMP_MAX']: return "低风险", []

        reasons = []
        risk = "低风险"

        if ah > cal['HIGH_RH_ACUTE']:
            _, _, ratio = self._calculate_duration('table_hum', f"value > {cal['HIGH_RH_ACUTE']}", cfg['DURATION_ACUTE'])
            if ratio > 0.6:
                return "高风险", ["空气极湿(>90%)，叶面可能已结露，孢子极易萌发"]

        if ah > cal['HIGH_RH_CHRONIC']:
            _, _, ratio = self._calculate_duration('table_hum', f"value > {cal['HIGH_RH_CHRONIC']}", cfg['DURATION_CHRONIC'])
            hours = ratio * cfg['DURATION_CHRONIC']
            
            if hours > 24:
                risk = "中风险"
                reasons.append(f"高湿环境持续 {hours:.1f}小时")
                if light < cfg['LIGHT_WEAK']:
                    risk = "高风险"
                    reasons.append("持续阴雨弱光，植株抗性下降")
        
        return risk, reasons

    # --- 3. 病毒病/蚜虫 ---
    def check_virus(self, at, ah, sh):
        cfg = CONFIG['VIRUS_APHID']
        cal = CONFIG['SENSOR_CALIBRATION']

        if not (cfg['TEMP_MIN'] <= at <= cfg['TEMP_MAX']): return "低风险", []
        if ah > cfg['AIR_HUM_MAX']: return "低风险", []
        if sh > cal['SOIL_DRY_LIMIT']: return "低风险", []

        _, _, ratio = self._calculate_duration('table_soil', f"soil_hum < 25", 168)
        
        if ratio > 0.9: 
            return "高风险", ["长期高温干旱(>7天)，极易爆发蚜虫并传播病毒病"]
        elif ratio > 0.5:
            return "中风险", ["环境趋于干旱，注意防范虫害"]
            
        return "低风险", []

    # --- 🧠 主分析函数 ---
    def analyze(self, sensors):
        score = 100
        suggestions = []
        limit_factors = []
        risks = {'root': '低风险', 'spot': '低风险'}
        
        st, sh = sensors.get('soil_temp', 0), sensors.get('soil_hum', 0)
        sec = sensors.get('soil_ec', 0)
        at, ah = sensors.get('air_temp', 0), sensors.get('air_hum', 0)
        light = sensors.get('light', 0)
        
        # 1. 确定生长阶段 (Internal Code)
        month = datetime.now().month
        stage_code = 'EXPANSION'
        if month in [4, 5]: stage_code = 'SEEDLING'
        elif month in [9, 10, 11]: stage_code = 'MATURITY'
        
        # 🔥 优化点：提前定义映射，用于生成中文建议
        stage_name_map = {
            'SEEDLING': '苗期',
            'EXPANSION': '块茎膨大期',
            'MATURITY': '成熟收获期'
        }
        # 获取中文名称 (如果找不到就显示"生长期")
        stage_cn_name = stage_name_map.get(stage_code, '生长期')

        # 2. 病害检测
        r_risk, r_msg = self.check_root_rot(st, sh, sec)
        if r_risk == "高风险":
            score -= 40
            risks['root'] = "高风险"
            limit_factors.append("根腐病爆发")
            suggestions.insert(0, r_msg[0])
        elif r_risk == "中风险":
            score -= 15
            risks['root'] = "中风险"
            suggestions.append(r_msg[0])

        l_risk, l_msg = self.check_leaf_spot(at, ah, light)
        if l_risk == "高风险":
            score -= 30
            risks['spot'] = "高风险"
            limit_factors.append("斑枯病高危")
            if not suggestions: suggestions.append(l_msg[0])
        elif l_risk == "中风险":
            score -= 10
            risks['spot'] = "中风险"
            suggestions.append("冠层湿度过高，建议通风")

        v_risk, v_msg = self.check_virus(at, ah, sh)
        if v_risk != "低风险":
            deduction = 20 if v_risk == "高风险" else 10
            score -= deduction
            limit_factors.append("虫害/病毒风险")
            suggestions.append(v_msg[0])

        # 3. 辅助病害
        ring_cfg = CONFIG['RING_ROT']
        cal = CONFIG['SENSOR_CALIBRATION']
        if (ring_cfg['TEMP_MIN'] <= at <= ring_cfg['TEMP_MAX']) and ah > cal['HIGH_RH_CHRONIC']:
             _, _, ratio = self._calculate_duration('table_hum', f"value > {cal['HIGH_RH_CHRONIC']}", 24)
             if ratio > 0.8:
                 score -= 10
                 limit_factors.append("轮纹病风险")

        phy_cfg = CONFIG['PHYTOPHTHORA']
        if (phy_cfg['TEMP_MIN'] <= at <= phy_cfg['TEMP_MAX']) and sh > cal['SOIL_WET_LIMIT']:
             score -= 20
             limit_factors.append("疫病风险")
             suggestions.append("低温高湿，警惕疫病")

        # 4. 生理性病害
        ab_cfg = CONFIG['ABIOTIC']
        if light > ab_cfg['SUNBURN_LIGHT'] and at > ab_cfg['SUNBURN_TEMP'] and sh < cal['SOIL_WET_LIMIT']:
            score -= 15
            limit_factors.append("日灼风险")
            suggestions.append("光照过强且缺水，易发生日灼，请遮阴喷灌")

        # ========== 结果汇总 ==========
        if score < 0: score = 0
        
        if not limit_factors: 
            limit_factors.append("暂无明显胁迫") 
            
        if not suggestions: 
            # 🔥 修复点：这里直接使用中文 stage_cn_name
            suggestions.append(f"当前处于{stage_cn_name}，各项指标优良，请继续保持。")

        return {
            "score": int(score),
            "limit_factor": " | ".join(limit_factors[:2]),
            "suggestion": suggestions[0],
            "risk_root": risks['root'], 
            "risk_spot": risks['spot'],
            "stage_name": stage_cn_name 
        }