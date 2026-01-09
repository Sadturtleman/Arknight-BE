import requests
import json
import psycopg2
from psycopg2 import extras
from typing import List, Dict, Any, Set

# ==========================================
# 1. DB 연결 설정
# ==========================================
DB_CONFIG = {
    "host": "aws-1-ap-south-1.pooler.supabase.com", # [확인 필요] 본인 프로젝트의 Host 주소 (보통 aws-0...)
    "database": "postgres",
    "user": "postgres.uwykuxiuytgqfwlzlmlf", # [자동 입력됨] 프로젝트 ID 기반 유저명
    "password": "Ay*h8D.5n2Ap2?a",           # [필수] 직접 설정한 DB 비밀번호를 입력하세요!
    "port": "6543"                            # 6543(Pooler) 또는 5432(Direct) 사용
}
URLS = {
    "character": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/character_table.json",
    "skill": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/skill_table.json",
    "range": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/range_table.json",
    "skin": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/skin_table.json",
    "module": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/uniequip_table.json",
    "item": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/item_table.json",
    "map": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/stage_table.json",
    "building": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/building_data.json"
}

# ==========================================
# 2. 헬퍼 함수
# ==========================================
def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"🚨 DB Connection Failed: {e}")
        exit(1)

def fetch_json(url: str) -> Dict[str, Any]:
    try:
        print(f"[Network] Fetching {url.split('/')[-1]}...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"   [Warning] Fetch failed: {e}")
        return {}

def parse_rarity(value):
    if isinstance(value, int): return value
    if isinstance(value, str) and value.startswith("TIER_"):
        try: return int(value.replace("TIER_", "")) - 1
        except: return 0
    return 0

def parse_phase(value):
    if isinstance(value, int): return value
    if isinstance(value, str) and value.startswith("PHASE_"):
        try: return int(value.replace("PHASE_", ""))
        except: return 0
    return 0

def db_upsert(conn, table_name: str, data: List[Dict], pk_cols: List[str] = None):
    if not data: return
    
    # 데이터 직렬화
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
    
    if pk_cols:
        constraint = ', '.join(pk_cols)
        update_cols = [k for k in keys if k not in pk_cols]
        if update_cols:
            updates = ', '.join([f"{k} = EXCLUDED.{k}" for k in update_cols])
            sql = f"INSERT INTO {table_name} ({columns}) VALUES %s ON CONFLICT ({constraint}) DO UPDATE SET {updates}"
        else:
            sql = f"INSERT INTO {table_name} ({columns}) VALUES %s ON CONFLICT ({constraint}) DO NOTHING"
    else:
        sql = f"INSERT INTO {table_name} ({columns}) VALUES %s"

    print(f" >> Upserting {table_name}: {len(data)} rows...")
    try:
        with conn.cursor() as cur:
            tuple_data = [[row[k] for k in keys] for row in processed_data]
            extras.execute_values(cur, sql, tuple_data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"    [Error] SQL Execution failed: {e}")
        # 디버깅을 위해 첫 번째 실패 데이터 출력
        if data: print(f"    [Sample Data] {data[0]}")
        raise e

def get_valid_operators(conn) -> Set[str]:
    """DB에 실제로 저장된 오퍼레이터 ID 목록 조회"""
    with conn.cursor() as cur:
        cur.execute("SELECT operator_id FROM operators")
        rows = cur.fetchall()
        return {r[0] for r in rows}

# ==========================================
# 3. 메인 로직
# ==========================================
def run_migration():
    conn = get_connection()
    print("✅ DB Connected.")
    
    # [Pre-Step] 스키마 패치
    with conn.cursor() as cur:
        try:
            # potential_data 타입 변경 (JSONB -> VARCHAR)
            cur.execute("ALTER TABLE operators ALTER COLUMN potential_data TYPE VARCHAR(100);")
            cur.execute("ALTER TABLE skills ALTER COLUMN sp_type TYPE VARCHAR(50);")
            cur.execute("ALTER TABLE skills ALTER COLUMN duration_type TYPE VARCHAR(50);")
            cur.execute("TRUNCATE TABLE operator_consumptions RESTART IDENTITY CASCADE;")
            conn.commit()
            print(" >> [Auto-Fix] Schema patched.")
        except:
            conn.rollback()

    # [Step 1] 기초 테이블 (FK 의존성 없음)
    raw = fetch_json(URLS["range"])
    if raw:
        data = [{"range_id": k, "grids": v["grids"]} for k, v in raw.items()]
        db_upsert(conn, "ranges", data, pk_cols=["range_id"])

    raw = fetch_json(URLS["item"])
    if raw and "items" in raw:
        data = []
        for k, v in raw["items"].items():
            data.append({
                "item_id": k, "name_ko": v.get("name"), "description": v.get("description"),
                "rarity": parse_rarity(v.get("rarity")), 
                "item_type": v.get("classifyType", "NONE"), 
                "sort_id": v.get("sortId", 0), "icon_id": v.get("iconId"),
                "stack_limit": v.get("stackLimit", 99), "obtain_approach": v.get("obtainApproach")
            })
        db_upsert(conn, "items", data, pk_cols=["item_id"])

    raw = fetch_json(URLS["skill"])
    if raw:
        data = []
        for k, v in raw.items():
            lvl0 = v["levels"][0] if v.get("levels") else {}
            data.append({
                "skill_id": k, "icon_id": v.get("iconId"),
                "name_ko": lvl0.get("name", "Unknown"),
                "sp_type": lvl0.get("spData", {}).get("spType", "UNKNOWN"),
                "duration_type": lvl0.get("durationConfig", {}).get("selected", "UNKNOWN"),
                "levels_data": v.get("levels", [])
            })
        db_upsert(conn, "skills", data, pk_cols=["skill_id"])
    
    raw_brand = fetch_json(URLS["skin"])
    if raw_brand and "brandList" in raw_brand:
        data = [{"brand_id": k, "name_ko": v["brandName"], "sort_id": v["sortId"], "logo_id": v.get("brandLogoId"), "description": v.get("description")} for k, v in raw_brand["brandList"].items()]
        db_upsert(conn, "skin_brands", data, pk_cols=["brand_id"])
    
    raw_map = fetch_json(URLS["map"])
    if raw_map and "zones" in raw_map:
        data = [{"zone_id": k, "name_ko": v["zoneNameKo"], "type": v["zoneType"], "zone_index": v["zoneIndex"]} for k, v in raw_map["zones"].items()]
        db_upsert(conn, "zones", data, pk_cols=["zone_id"])
        if "stages" in raw_map:
            stages = []
            for s_id, v in raw_map["stages"].items():
                stages.append({
                    "stage_id": s_id, "zone_id": v["zoneId"],
                    "code": v["code"], "name_ko": v["name"], "description": v["description"],
                    "stage_type": v["stageType"], "ap_cost": v["apCost"],
                    "rec_level": v.get("dangerLevel"), "hazard_type": v.get("dangerLevel"),
                    "hard_stage_id": v.get("hardStagedId"), "drops_data": v.get("stageDropInfo", {})
                })
            db_upsert(conn, "stages", stages, pk_cols=["stage_id"])


    # [Step 2] Operators 삽입 (가장 중요)
    raw_char = fetch_json(URLS["character"])
    if raw_char:
        ops = []
        for op_id, c in raw_char.items():
            # 필터링 조건
            if c.get("isNotObtainable") or op_id.startswith("trap_") or op_id.startswith("token_"): continue
            
            ops.append({
                "operator_id": op_id, "name_ko": c["name"], "name_en": c["appellation"],
                "rarity": parse_rarity(c["rarity"]), 
                "profession": c["profession"], "sub_profession": c["subProfessionId"], 
                "position": c["position"], "team_id": c.get("groupId"), "range_id": c.get("rangeId"),
                "is_sp_char": c.get("isSpChar", False), "description": c.get("itemUsage"),
                "phases_data": c.get("phases"), "talents_data": c.get("talents"),
                "potential_data": c.get("potentialItemId"), "trust_data": c.get("favorKeyFrames")
            })
        db_upsert(conn, "operators", ops, pk_cols=["operator_id"])

    # [Check] 실제로 들어간 Operator ID 목록 확보 (참조 무결성용)
    valid_op_ids = get_valid_operators(conn)
    print(f" >> Valid Operators in DB: {len(valid_op_ids)}")

    # [Step 3] Operators 하위 데이터 (FK 필터링 적용)
    if raw_char:
        stats, op_skills, consumptions = [], [], []
        for op_id, c in raw_char.items():
            # DB에 없는 오퍼레이터면 Skip (FK 에러 방지)
            if op_id not in valid_op_ids: continue

            for i, phase in enumerate(c.get("phases", [])):
                attr0 = phase["attributesKeyFrames"][0]["data"]
                attr1 = phase["attributesKeyFrames"][1]["data"]
                stats.append({
                    "operator_id": op_id, "phase": i, "max_level": phase["maxLevel"],
                    "base_hp": attr0["maxHp"], "base_atk": attr0["atk"], "base_def": attr0["def"], "base_res": attr0["magicResistance"],
                    "max_hp": attr1["maxHp"], "max_atk": attr1["atk"], "max_def": attr1["def"], "max_res": attr1["magicResistance"],
                    "cost": attr0["cost"], "block_cnt": attr0["blockCnt"], "attack_speed": attr0["baseAttackTime"], "respawn_time": attr0["respawnTime"],
                    "range_id": phase.get("rangeId")
                })
                if phase.get("evolveCost"):
                    # [Fix] ingredients가 None이면 []로
                    consumptions.append({"operator_id": op_id, "cost_type": "ELITE", "level": i, "ingredients": phase.get("evolveCost") or []})

            for idx, skill in enumerate(c.get("skills", [])):
                if not skill.get("skillId"): continue
                p_val = parse_phase(skill.get("unlockCond", {}).get("phase", 0))
                op_skills.append({"operator_id": op_id, "skill_id": skill["skillId"], "skill_index": idx, "unlock_phase": p_val})
                
                for m_idx, mastery in enumerate(skill.get("levelUpCostCond", [])):
                    # [Fix] ingredients가 None이면 []로
                    consumptions.append({"operator_id": op_id, "cost_type": "MASTERY", "reference_id": skill["skillId"], "level": m_idx + 1, "ingredients": mastery.get("levelUpCost") or []})

        db_upsert(conn, "operator_stats", stats, pk_cols=["operator_id", "phase"])
        db_upsert(conn, "operator_skills", op_skills, pk_cols=["operator_id", "skill_id"])
        db_upsert(conn, "operator_consumptions", consumptions, pk_cols=None)

    # [Step 4] Skins & Modules (FK 필터링 적용)
    if raw_brand and "charSkins" in raw_brand:
        skins = []
        for s_id, v in raw_brand["charSkins"].items():
            # DB에 없는 오퍼레이터면 Skip
            if v["charId"] not in valid_op_ids: continue
            
            skins.append({
                "skin_id": s_id, "operator_id": v["charId"], "brand_id": v.get("brandId"),
                "name_ko": v.get("displaySkin", {}).get("skinName"),
                "illustrator": v.get("displaySkin", {}).get("illustratorId"),
                "category": v.get("displaySkin", {}).get("category", "NORMAL"),
                "is_dynamic": bool(v.get("dynDisplaySkinInfos")),
                "display_data": v.get("displaySkin", {})
            })
        db_upsert(conn, "skins", skins, pk_cols=["skin_id"])

    raw_mod = fetch_json(URLS["module"])
    if raw_mod and "uniEquip" in raw_mod:
        modules = []
        for m_id, v in raw_mod["uniEquip"].items():
            # DB에 없는 오퍼레이터면 Skip
            if not v.get("charId") or v["charId"] not in valid_op_ids: continue
            
            modules.append({
                "module_id": m_id, "operator_id": v["charId"],
                "icon_id": v["uniEquipIcon"], "type_icon_id": v["typeIcon"], "sort_id": v.get("sortId", 0),
                "display_text": {"ko": {"name": v["uniEquipName"], "desc": v["uniEquipDesc"]}},
                "unlock_cond": {"missions": v.get("missionList", [])}, "levels_data": {}
            })
        db_upsert(conn, "modules", modules, pk_cols=["module_id"])

    # [Step 5] Workshop
    raw_build = fetch_json(URLS["building"])
    if raw_build and "workshopFormulas" in raw_build:
        formulas = {}
        for f_id, v in raw_build["workshopFormulas"].items():
            req_stages = v.get("requireStages", [])
            item_id = v["itemId"]
            formulas[item_id] = {
                "target_item_id": item_id, "gold_cost": v["goldCost"], "yield_prob": 1.0,
                "ingredients": v.get("costs") or [], 
                "unlock_cond": req_stages[-1]["stageId"] if req_stages else None
            }
        db_upsert(conn, "workshop_formulas", list(formulas.values()), pk_cols=["target_item_id"])

    conn.close()
    print("\n✅ [Finish] All Data Successfully Migrated (With FK/Null Safety).")

if __name__ == "__main__":
    run_migration()