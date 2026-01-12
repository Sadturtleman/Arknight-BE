import psycopg2
import requests
import json
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
# ==========================================
# 1. 설정 및 데이터 소스
# ==========================================
DB_CONFIG = {
    "host": HOST,
    "database": DBNAME,
    "user":  USER,
    "password": PASSWORD,
    "port":  PORT
}

URLS = {
    "character": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/character_table.json",
    "skill": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/skill_table.json",
    "range": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/range_table.json",
    "module": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/uniequip_table.json",
    "item": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/item_table.json",
    "map": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/stage_table.json",
    "zone": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/zone_table.json"
}

# DB의 Serial ID와 JSON의 String ID를 매핑하기 위한 메모리 저장소
ID_MAP = {
    "profession": {},
    "sub_profession": {},
    "tag": {},
    "item": {},
    "zone": {},
    "character": {},
    "skill": {},
    "module": {}
}

# ==========================================
# 2. 헬퍼 함수
# ==========================================
def get_json(url):
    print(f"Downloading {url}...")
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return {}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def parse_phase(phase_val):
    """PHASE_1 같은 문자열을 정수 1로 변환"""
    if phase_val is None:
        return 0
    if isinstance(phase_val, int):
        return phase_val
    if isinstance(phase_val, str):
        if phase_val.startswith("PHASE_"):
            try:
                return int(phase_val.split('_')[1])
            except:
                return 0
        elif phase_val.isdigit():
            return int(phase_val)
    return 0

def parse_rarity(rarity_value):
    """JSON의 rarity 값이 정수일 수도 있고, 'TIER_5' 같은 문자열일 수도 있음을 처리"""
    if rarity_value is None:
        return 0
    if isinstance(rarity_value, int):
        return rarity_value
    if isinstance(rarity_value, str):
        if rarity_value.startswith("TIER_"):
            try:
                return int(rarity_value.split('_')[1]) - 1
            except:
                return 0
        elif rarity_value.isdigit():
            return int(rarity_value)
    return 0

def parse_skill_type(val):
    """스킬 타입 파싱"""
    if isinstance(val, int): 
        return val
    if val == "PASSIVE": 
        return 0
    if val == "MANUAL": 
        return 1
    if val == "AUTO": 
        return 2
    return 0

def parse_sp_type(val):
    """SP 타입 파싱"""
    if isinstance(val, int): 
        return val
    if val == "INCREASE_WITH_TIME": 
        return 1
    if val == "INCREASE_WHEN_ATTACK": 
        return 2
    if val == "INCREASE_WHEN_TAKEN_DAMAGE": 
        return 4
    return 8

def pre_load_ids(conn):
    """기존 DB의 ID들을 미리 로드"""
    print(">> Pre-loading existing IDs from DB...")
    cur = conn.cursor()
    
    # Characters
    cur.execute("SELECT code, character_id FROM characters")
    for code, char_id in cur.fetchall():
        ID_MAP["character"][code] = char_id
    
    # Skills
    cur.execute("SELECT skill_code, skill_id FROM skills")
    for code, skill_id in cur.fetchall():
        ID_MAP["skill"][code] = skill_id
    
    # Items
    cur.execute("SELECT item_code, item_id FROM items")
    for code, item_id in cur.fetchall():
        ID_MAP["item"][code] = item_id
    
    print(f"   - Loaded {len(ID_MAP['character'])} characters, {len(ID_MAP['skill'])} skills, {len(ID_MAP['item'])} items")

# ==========================================
# 3. 데이터 로딩 함수 (실행 순서 중요)
# ==========================================

def load_ranges(conn, data):
    print(">> Loading Ranges...")
    cur = conn.cursor()
    values = []
    for range_id, info in data.items():
        grids_json = json.dumps(info.get('grids', []))
        values.append((range_id, grids_json))
    
    query = "INSERT INTO ranges (range_id, grids) VALUES %s ON CONFLICT (range_id) DO NOTHING"
    execute_values(cur, query, values)
    conn.commit()

def load_items(conn, data):
    print(">> Loading Items...")
    cur = conn.cursor()
    items_dict = data.get("items", {})
    
    for item_code, info in items_dict.items():
        if info.get('isDeleted', False): 
            continue

        raw_rarity = info.get('rarity')
        rarity_int = parse_rarity(raw_rarity)

        try:
            cur.execute("""
                INSERT INTO items (item_code, name_ko, rarity, icon_id, item_type, classify_type, usage_text, description, obtain_approach)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_code) DO UPDATE SET name_ko = EXCLUDED.name_ko
                RETURNING item_id
            """, (
                item_code, 
                info.get('name'), 
                rarity_int,
                info.get('iconId'),
                info.get('itemType'), 
                info.get('classifyType'), 
                info.get('usage'), 
                info.get('description'), 
                info.get('obtainApproach')
            ))
            
            db_id = cur.fetchone()[0]
            ID_MAP["item"][item_code] = db_id
            
        except Exception as e:
            print(f"Skipping item {item_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()

def load_zones(conn, data):
    print(">> Loading Zones...")
    cur = conn.cursor()
    zones_dict = data.get("zones", {})
    
    for zone_code, info in zones_dict.items():
        name_ko = info.get('zoneNameSecond')
        if not name_ko:
            name_ko = info.get('zoneNameFirst')
        if not name_ko:
            name_ko = zone_code
            
        try:
            cur.execute("""
                INSERT INTO zones (zone_code, name_ko, zone_type, zone_index)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_code) DO NOTHING
                RETURNING zone_id
            """, (
                zone_code, 
                name_ko, 
                info.get('type'), 
                info.get('zoneIndex')
            ))
            
            row = cur.fetchone()
            if row:
                ID_MAP["zone"][zone_code] = row[0]
            else:
                cur.execute("SELECT zone_id FROM zones WHERE zone_code = %s", (zone_code,))
                res = cur.fetchone()
                if res: 
                    ID_MAP["zone"][zone_code] = res[0]
                
        except Exception as e:
            print(f"Skipping zone {zone_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()

def load_professions_tags(conn, char_data):
    print(">> Loading Professions & Tags...")
    cur = conn.cursor()
    
    profs = {}
    sub_profs = {}
    tags = set()
    
    for char_code, info in char_data.items():
        prof = info.get('profession')
        subprof = info.get('subProfessionId')
        tag_list = info.get('tagList') or []
        
        if prof:
            profs[prof] = info.get('professionName', prof)
        if subprof:
            sub_profs[subprof] = subprof
        for t in tag_list:
            if t:
                tags.add(t)
    
    for code, name in profs.items():
        cur.execute("INSERT INTO professions (code, name_ko) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING RETURNING profession_id", (code, name))
        row = cur.fetchone()
        if row:
            ID_MAP["profession"][code] = row[0]
        else:
            cur.execute("SELECT profession_id FROM professions WHERE code = %s", (code,))
            res = cur.fetchone()
            if res:
                ID_MAP["profession"][code] = res[0]
    
    for code in sub_profs:
        cur.execute("INSERT INTO sub_professions (code, name_ko) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING RETURNING sub_profession_id", (code, code))
        row = cur.fetchone()
        if row:
            ID_MAP["sub_profession"][code] = row[0]
        else:
            cur.execute("SELECT sub_profession_id FROM sub_professions WHERE code = %s", (code,))
            res = cur.fetchone()
            if res:
                ID_MAP["sub_profession"][code] = res[0]
    
    for t in tags:
        cur.execute("INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING tag_id", (t,))
        row = cur.fetchone()
        if row:
            ID_MAP["tag"][t] = row[0]
        else:
            cur.execute("SELECT tag_id FROM tags WHERE name = %s", (t,))
            res = cur.fetchone()
            if res:
                ID_MAP["tag"][t] = res[0]
    
    conn.commit()

def load_characters(conn, data):
    print(">> Loading Characters & Related Data...")
    cur = conn.cursor()
    
    for char_code, info in data.items():
        if info.get('isNotObtainable', False):
            continue
        
        try:
            # 1. Character
            raw_rarity = info.get('rarity')
            rarity_int = parse_rarity(raw_rarity)
            
            prof_id = ID_MAP["profession"].get(info.get('profession'))
            subprof_id = ID_MAP["sub_profession"].get(info.get('subProfessionId'))
            
            cur.execute("""
                INSERT INTO characters (code, name_ko, rarity, profession_id, sub_profession_id, position, description, nation_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET name_ko = EXCLUDED.name_ko
                RETURNING character_id
            """, (
                char_code, info.get('name'), rarity_int, prof_id, subprof_id,
                info.get('position'), info.get('itemDesc'), info.get('nationId')
            ))
            
            char_id = cur.fetchone()[0]
            ID_MAP["character"][char_code] = char_id
            
            # 2. Potential
            pot_ranks = info.get('potentialRanks') or []
            for idx, pot in enumerate(pot_ranks):
                if pot.get('type') == 0:
                    cur.execute("""
                        INSERT INTO character_potentials (character_id, potential_rank, buff_type, buff_value)
                        VALUES (%s, %s, %s, %s) ON CONFLICT (character_id, potential_rank) DO NOTHING
                    """, (char_id, idx, pot.get('type', 0), pot.get('description', '')))
            
            # 3. Stats & Promotion Costs
            phases = info.get('phases') or []
            for idx, phase in enumerate(phases):
                keyframes = phase.get('attributesKeyFrames') or []
                if not keyframes:
                    continue
                
                # Base stats (레벨 1)
                base_data = keyframes[0].get('data', {})
                base_hp = int(base_data.get('maxHp', 0))
                base_atk = int(base_data.get('atk', 0))
                base_def = int(base_data.get('def', 0))
                
                # Max stats (최대 레벨)
                attr = keyframes[-1].get('data', {})
                range_id = phase.get('rangeId')
                
                cur.execute("""
                    INSERT INTO character_stats (character_id, phase, max_level, range_id, 
                                                base_hp, base_atk, base_def,
                                                max_hp, max_atk, max_def, 
                                                magic_resistance, cost, block_count, attack_speed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (character_id, phase) DO UPDATE SET
                        base_hp = EXCLUDED.base_hp,
                        base_atk = EXCLUDED.base_atk,
                        base_def = EXCLUDED.base_def
                """, (
                    char_id, idx, phase.get('maxLevel', 0), range_id,
                    base_hp, base_atk, base_def,
                    int(attr.get('maxHp', 0)), int(attr.get('atk', 0)), int(attr.get('def', 0)),
                    int(attr.get('magicResistance', 0)), int(attr.get('cost', 0)), 
                    int(attr.get('blockCnt', 0)), int(attr.get('attackSpeed', 0))
                ))
                
                # Promotion Costs
                evolve_costs = phase.get('evolveCost') or []
                for req in evolve_costs:
                    item_db_id = ID_MAP["item"].get(req['id'])
                    if item_db_id:
                        cur.execute("""
                            INSERT INTO character_promotion_costs (character_id, target_phase, item_id, count) 
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (char_id, idx, item_db_id, req['count']))

            # 4. Skill Codes
            skills_data = info.get('skills') or []
            safe_skills = [s for s in skills_data if isinstance(s, dict)]
            s_codes = [None, None, None]
            
            for i in range(min(len(safe_skills), 3)):
                s_codes[i] = safe_skills[i].get('skillId')
            
            cur.execute("""
                INSERT INTO character_skill (character_id, phase_0_code, phase_1_code, phase_2_code)
                VALUES (%s, %s, %s, %s) ON CONFLICT (character_id) DO NOTHING
            """, (char_id, s_codes[0], s_codes[1], s_codes[2]))
            
            # 5. Character Skill Costs (레벨 1-7)
            skill_ups = info.get('allSkillLvlup') or []
            for idx, lvl_data in enumerate(skill_ups):
                target_level = idx + 2  # 레벨 2부터 시작
                costs = lvl_data.get('lvlUpCost') or []
                
                for cost in costs:
                    item_code = cost.get('id')
                    qty = cost.get('count')
                    item_db_id = ID_MAP["item"].get(item_code)
                    
                    if item_db_id:
                        cur.execute("""
                            INSERT INTO character_skill_costs (character_id, level, item_id, count)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (char_id, target_level, item_db_id, qty))

            # 6. Talents
            talents = info.get('talents') or []
            for t_idx, talent in enumerate(talents):
                if not talent or 'candidates' not in talent:
                    continue
                
                candidates = talent.get('candidates') or []
                for c_idx, cand in enumerate(candidates):
                    cond = cand.get('unlockCondition', {})
                    raw_phase = cond.get('phase')
                    phase_int = parse_phase(raw_phase)
                    talent_name = cand.get('name') or "Unknown Talent"

                    cur.execute("""
                        INSERT INTO character_talents (character_id, talent_index, candidate_index, 
                                                      unlock_phase, unlock_level, required_potential, 
                                                      range_id, name, description, blackboard)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        char_id, t_idx+1, c_idx+1, phase_int,
                        cond.get('level', 1), cand.get('requiredPotentialRank', 0),
                        cand.get('rangeId'), talent_name, 
                        cand.get('description'), json.dumps(cand.get('blackboard', []))
                    ))
            
            # 7. Tags
            tag_list = info.get('tagList') or []
            for t in tag_list:
                tag_db_id = ID_MAP["tag"].get(t)
                if tag_db_id:
                    cur.execute("""
                        INSERT INTO character_tag (character_id, tag_id) 
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (char_id, tag_db_id))

            # 8. Favor
            favor_frames = info.get('favorKeyFrames') or []
            if favor_frames:
                favor = favor_frames[-1].get('data', {})
                cur.execute("""
                    INSERT INTO character_favor_templates (character_id, max_favor_level, bonus_hp, bonus_atk, bonus_def)
                    VALUES (%s, 100, %s, %s, %s) ON CONFLICT (character_id) DO NOTHING
                """, (char_id, int(favor.get('maxHp', 0)), int(favor.get('atk', 0)), int(favor.get('def', 0))))

        except Exception as e:
            print(f"Skipping char {char_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()

def load_skills(conn, data):
    print(">> Loading Skills & Skill Levels...")
    cur = conn.cursor()
    inserted_skills = 0
    
    for skill_code, info in data.items():
        try:
            lvl0 = info.get('levels', [{}])[0]
            
            raw_skill_type = lvl0.get('skillType', 0)
            raw_sp_type = lvl0.get('spData', {}).get('spType', 0)
            
            final_skill_type = parse_skill_type(raw_skill_type)
            final_sp_type = parse_sp_type(raw_sp_type)

            # 1. Skills 테이블
            cur.execute("""
                INSERT INTO skills (skill_code, name_ko, icon_id, skill_type, sp_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (skill_code) DO NOTHING
                RETURNING skill_id
            """, (
                skill_code, lvl0.get('name'), info.get('iconId'), 
                final_skill_type, final_sp_type
            ))
            
            row = cur.fetchone()
            if row:
                skill_id = row[0]
            else:
                cur.execute("SELECT skill_id FROM skills WHERE skill_code = %s", (skill_code,))
                row = cur.fetchone()
                if not row: 
                    continue
                skill_id = row[0]
            
            ID_MAP["skill"][skill_code] = skill_id
            
            # 2. Skill Levels 테이블
            for idx, lvl_info in enumerate(info.get('levels', [])):
                level_val = idx + 1
                
                # Check Constraint 위반 방지: 레벨이 10을 넘으면 스킵
                if level_val > 10:
                    continue

                sp = lvl_info.get('spData', {})
                
                # Numeric Overflow 방지: duration이 999.99를 넘으면 999.0으로 제한
                raw_duration = lvl_info.get('duration', 0)
                safe_duration = min(float(raw_duration), 999.0)

                cur.execute("""
                    INSERT INTO skill_levels (skill_id, level, sp_cost, initial_sp, duration, 
                                            range_id, description, blackboard)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (skill_id, level) DO NOTHING
                """, (
                    skill_id, level_val, 
                    sp.get('spCost', 0), sp.get('initSp', 0), 
                    safe_duration, lvl_info.get('rangeId'), 
                    lvl_info.get('description'), 
                    json.dumps(lvl_info.get('blackboard', []))
                ))
            
            inserted_skills += 1
            
        except Exception as e:
            print(f"Skipping skill {skill_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"   - Processed {inserted_skills} skills.")

def load_skill_mastery_costs(conn, data):
    """스킬 특화 비용 로드 (레벨 8-10)"""
    print(">> Loading Skill Mastery Costs (Lv 8-10)...")
    cur = conn.cursor()
    count = 0
    
    for char_code, char_info in data.items():
        skills_list = char_info.get('skills', [])
        
        for skill_entry in skills_list:
            skill_code = skill_entry.get('skillId')
            skill_db_id = ID_MAP["skill"].get(skill_code)
            if not skill_db_id: 
                continue

            # levelUpCostCond 파싱
            # Index 0 -> Mastery 1 (Lv 8)
            # Index 1 -> Mastery 2 (Lv 9)
            # Index 2 -> Mastery 3 (Lv 10)
            mastery_conds = skill_entry.get('levelUpCostCond') or []
            
            for idx, cond in enumerate(mastery_conds):
                mastery_level = idx + 1  # 1, 2, 3
                costs = cond.get('levelUpCost') or []
                
                for cost in costs:
                    item_code = cost.get('id')
                    qty = cost.get('count')
                    item_db_id = ID_MAP["item"].get(item_code)
                    
                    if item_db_id:
                        cur.execute("""
                            INSERT INTO skill_mastery_costs (skill_id, mastery_level, item_id, count)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (skill_db_id, mastery_level, item_db_id, qty))
                        count += 1
                    
    conn.commit()
    print(f"   - Inserted {count} mastery cost records.")

def load_modules(conn, data):
    print(">> Loading Modules & Costs...")
    cur = conn.cursor()
    equip_dict = data.get('equipDict', {})
    inserted_modules = 0
    
    for mod_code, info in equip_dict.items():
        char_db_id = ID_MAP["character"].get(info.get('charId'))
        if not char_db_id: 
            continue
        
        try:
            # 1. Character Modules
            cur.execute("""
                INSERT INTO character_modules (module_code, character_id, name_ko, icon_id, description)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (module_code) DO NOTHING
                RETURNING module_id
            """, (
                mod_code, char_db_id, info.get('uniEquipName'), 
                info.get('uniEquipIcon'), info.get('uniEquipDesc')
            ))
            
            row = cur.fetchone()
            if row:
                mod_id = row[0]
            else:
                cur.execute("SELECT module_id FROM character_modules WHERE module_code = %s", (mod_code,))
                row = cur.fetchone()
                if not row: 
                    continue
                mod_id = row[0]
            
            # 2. Module Costs
            item_costs = info.get('itemCost') or {}
            
            for lvl_str, costs in item_costs.items():
                for cost in costs:
                    item_db_id = ID_MAP["item"].get(cost['id'])
                    if item_db_id:
                        cur.execute("""
                            INSERT INTO character_module_costs (module_id, level, item_id, count) 
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (mod_id, int(lvl_str), item_db_id, cost['count']))
                        
            inserted_modules += 1
            
        except Exception as e:
            print(f"Skipping module {mod_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"   - Processed {inserted_modules} modules.")

def load_stages(conn, data):
    print(">> Loading Stages...")
    cur = conn.cursor()
    
    for stage_code, info in data.get('stages', {}).items():
        zone_db_id = ID_MAP["zone"].get(info.get('zoneId'))
        if not zone_db_id: 
            continue
        
        try:
            cur.execute("""
                INSERT INTO stages (stage_code, zone_id, display_code, name_ko, description, ap_cost, danger_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stage_code) DO NOTHING
            """, (
                stage_code, zone_db_id, info.get('code'), 
                info.get('name'), info.get('description'), 
                info.get('apCost', 0), info.get('dangerLevel')
            ))
        except Exception as e:
            print(f"Skipping stage {stage_code}: {e}")
            conn.rollback()
            continue
            
    conn.commit()

# ==========================================
# 4. 실행 진입점
# ==========================================
if __name__ == "__main__":
    conn = None
    try:
        conn = connect_db()
        print("✅ DB Connected Successfully.\n")
        
        # 1. JSON 다운로드
        print("=" * 50)
        print("STEP 1: Downloading JSON files")
        print("=" * 50)
        jsons = {}
        for key, url in URLS.items():
            jsons[key] = get_json(url)
        
        print("\n" + "=" * 50)
        print("STEP 2: Loading Base Data (Ranges, Items, Zones)")
        print("=" * 50)
        # Level 0: 독립 마스터
        load_ranges(conn, jsons["range"])
        load_items(conn, jsons["item"])
        load_zones(conn, jsons["zone"])
        
        print("\n" + "=" * 50)
        print("STEP 3: Loading Professions & Tags")
        print("=" * 50)
        # Level 1: 캐릭터 의존 마스터
        load_professions_tags(conn, jsons["character"])
        
        print("\n" + "=" * 50)
        print("STEP 4: Loading Characters (with Stats & Skill Costs)")
        print("=" * 50)
        # Level 2: 메인 엔티티
        load_characters(conn, jsons["character"])
        
        print("\n" + "=" * 50)
        print("STEP 5: Pre-loading IDs for Cross-references")
        print("=" * 50)
        # ID 매핑 갱신 (스킬/모듈 참조를 위해)
        pre_load_ids(conn)
        
        print("\n" + "=" * 50)
        print("STEP 6: Loading Skills & Skill Levels")
        print("=" * 50)
        load_skills(conn, jsons["skill"])
        
        print("\n" + "=" * 50)
        print("STEP 7: Loading Skill Mastery Costs")
        print("=" * 50)
        load_skill_mastery_costs(conn, jsons["character"])
        
        print("\n" + "=" * 50)
        print("STEP 8: Loading Modules")
        print("=" * 50)
        # Level 3: 종속 엔티티
        load_modules(conn, jsons["module"])
        
        print("\n" + "=" * 50)
        print("STEP 9: Loading Stages")
        print("=" * 50)
        load_stages(conn, jsons["map"])
        
        print("\n" + "=" * 50)
        print("✅ ALL DATA IMPORTED SUCCESSFULLY!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
        if conn: 
            conn.rollback()
    finally:
        if conn: 
            conn.close()
            print("\nDB connection closed.")