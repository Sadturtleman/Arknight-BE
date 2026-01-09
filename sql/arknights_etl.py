import requests
import json
import psycopg2
from psycopg2 import extras
from typing import List, Dict, Any

# ==========================================
# 1. 설정 (비밀번호 확인)
# ==========================================
DB_CONFIG = {
    "host": "aws-1-ap-south-1.pooler.supabase.com", # [확인 필요] 본인 프로젝트의 Host 주소 (보통 aws-0...)
    "database": "postgres",
    "user": "postgres.uwykuxiuytgqfwlzlmlf", # [자동 입력됨] 프로젝트 ID 기반 유저명
    "password": "Ay*h8D.5n2Ap2?a",           # [필수] 직접 설정한 DB 비밀번호를 입력하세요!
    "port": "6543"                            # 6543(Pooler) 또는 5432(Direct) 사용
}
# [수정] 제공해주신 표준 Raw URL 적용
URLS = {
    "zone": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/kr/gamedata/excel/zone_table.json",
    "stage": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/kr/gamedata/excel/stage_table.json"
}

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"🚨 DB Connection Failed: {e}")
        exit(1)

def fetch_json(url: str) -> Dict[str, Any]:
    print(f"[Network] Downloading {url.split('/')[-1]}...", end=" ")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        print(f"OK ({len(data)} keys)")
        return data
    except Exception as e:
        print(f"FAIL ({e})")
        return {}

def db_upsert(conn, table_name, data, pk_cols):
    if not data: return
    
    # JSON 직렬화
    processed_data = []
    for row in data:
        new_row = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                new_row[k] = json.dumps(v, ensure_ascii=False)
            else:
                new_row[k] = v
        processed_data.append(new_row)

    keys = list(processed_data[0].keys())
    columns = ', '.join(keys)
    constraint = ', '.join(pk_cols)
    update_cols = [k for k in keys if k not in pk_cols]
    
    # 중복 시 업데이트 (Upsert)
    updates = ', '.join([f"{k} = EXCLUDED.{k}" for k in update_cols]) if update_cols else "NOTHING"
    sql_update = f"UPDATE SET {updates}" if updates != "NOTHING" else "NOTHING"
    
    sql = f"INSERT INTO {table_name} ({columns}) VALUES %s ON CONFLICT ({constraint}) DO {sql_update}"

    print(f" >> Upserting {table_name}: {len(data)} rows...", end=" ")
    try:
        with conn.cursor() as cur:
            tuple_data = [[row[k] for k in keys] for row in processed_data]
            extras.execute_values(cur, sql, tuple_data)
        conn.commit()
        print("SUCCESS.")
    except Exception as e:
        conn.rollback()
        print(f"\n    🚨 [SQL Error] {e}")

# ==========================================
# 메인 로직 (Null Safety 적용)
# ==========================================
def run_zone_stage_fix():
    conn = get_connection()
    print("✅ DB Connected.\n")

    # 1. Zones 처리 (Safe Handling)
    raw_zones = fetch_json(URLS["zone"])
    if raw_zones and "zones" in raw_zones:
        data = []
        for k, v in raw_zones["zones"].items():
            # [핵심 Fix] 이름이 비어있으면(Null) -> zoneNameSecond -> 그것도 없으면 ID 사용
            safe_name = v.get("zoneNameKo")
            if not safe_name:
                safe_name = v.get("zoneNameSecond") or k 
            
            # [핵심 Fix] 타입이 비어있으면(Null) -> 'NONE' 문자열로 대체
            safe_type = v.get("zoneType") or "NONE"

            data.append({
                "zone_id": k, 
                "name_ko": safe_name, 
                "type": safe_type, 
                "zone_index": v.get("zoneIndex", -1) # 인덱스 없으면 -1
            })
        db_upsert(conn, "zones", data, pk_cols=["zone_id"])
    else:
        print("❌ Failed to parse zones.")

    # 2. Stages 처리
    # Zones가 성공적으로 들어가야만 Stages가 FK 에러 없이 들어감
    raw_stages = fetch_json(URLS["stage"])
    if raw_stages and "stages" in raw_stages:
        data = []
        for s_id, v in raw_stages["stages"].items():
            data.append({
                "stage_id": s_id, 
                "zone_id": v["zoneId"], 
                "code": v["code"], 
                "name_ko": v.get("name"), 
                "description": v.get("description"),
                "stage_type": v["stageType"], 
                "ap_cost": v["apCost"],
                "rec_level": v.get("dangerLevel"), 
                "hazard_type": v.get("dangerLevel"),
                "hard_stage_id": v.get("hardStagedId"), 
                "drops_data": v.get("stageDropInfo", {})
            })
        db_upsert(conn, "stages", data, pk_cols=["stage_id"])

    conn.close()
    print("\n✅ Zone & Stage Restoration Completed.")

if __name__ == "__main__":
    run_zone_stage_fix()