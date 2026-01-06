#!/usr/bin/env python3
"""
Arknights 게임 데이터를 PostgreSQL에 안전하게 삽입하는 스크립트
방어적 프로그래밍 원칙을 적용하여 작성됨
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import execute_values
import requests
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime
import time

# ==========================================
# 1. 설정 및 로깅
# ==========================================

# 데이터베이스 설정
DB_CONFIG = {
    "host": "localhost",
    "database": "arknights_db",
    "user": "rugsn",
    "password": "support8974@",
    "port": "5432"
}

# 데이터 소스 URL
URLS = {
    "character": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/character_table.json",
    "skill": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/skill_table.json",
    "range": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/range_table.json",
    "skin": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/skin_table.json",
    "uniequip": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/uniequip_table.json",
    "item": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/refs/heads/master/kr/gamedata/excel/item_table.json"
}

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'arknights_loader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초


# ==========================================
# 2. 데이터베이스 연결 관리
# ==========================================

class DatabaseManager:
    """데이터베이스 연결을 안전하게 관리하는 클래스"""
    
    def __init__(self, config: Dict[str, str], min_conn: int = 1, max_conn: int = 5):
        """
        Args:
            config: 데이터베이스 연결 설정
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_conn, max_conn, **config
            )
            logger.info("데이터베이스 연결 풀 생성 완료")
        except psycopg2.Error as e:
            logger.error(f"데이터베이스 연결 풀 생성 실패: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """컨텍스트 매니저를 통한 안전한 연결 관리"""
        conn = None
        try:
            conn = self.pool.getconn()
            if conn is None:
                raise psycopg2.Error("연결 풀에서 연결을 가져올 수 없습니다")
            yield conn
        except psycopg2.Error as e:
            logger.error(f"데이터베이스 연결 오류: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def close_all(self):
        """모든 연결 종료"""
        if self.pool:
            self.pool.closeall()
            logger.info("모든 데이터베이스 연결 종료")


# ==========================================
# 3. 데이터 다운로드 및 검증
# ==========================================

class DataFetcher:
    """외부 데이터를 안전하게 다운로드하고 검증하는 클래스"""
    
    @staticmethod
    def fetch_json(url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        URL에서 JSON 데이터를 다운로드
        
        Args:
            url: 데이터 소스 URL
            timeout: 요청 타임아웃 (초)
            
        Returns:
            JSON 데이터 딕셔너리 또는 None
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"데이터 다운로드 시도 ({attempt}/{MAX_RETRIES}): {url}")
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"데이터 다운로드 성공: {url} (크기: {len(response.content)} bytes)")
                return data
                
            except requests.exceptions.Timeout:
                logger.warning(f"타임아웃 발생 ({attempt}/{MAX_RETRIES}): {url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"요청 오류 ({attempt}/{MAX_RETRIES}): {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                return None
            
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        
        logger.error(f"최대 재시도 횟수 초과: {url}")
        return None
    
    @staticmethod
    def validate_data(data: Any, data_type: str) -> bool:
        """
        다운로드한 데이터의 유효성 검증
        
        Args:
            data: 검증할 데이터
            data_type: 데이터 타입 ('character', 'skill', 'range', 'skin')
            
        Returns:
            유효하면 True, 아니면 False
        """
        if not data:
            logger.error(f"{data_type} 데이터가 비어있습니다")
            return False
        
        if not isinstance(data, dict):
            logger.error(f"{data_type} 데이터가 딕셔너리 형식이 아닙니다")
            return False
        
        logger.info(f"{data_type} 데이터 검증 성공 (항목 수: {len(data)})")
        return True


# ==========================================
# 4. 데이터 변환 유틸리티
# ==========================================

class DataTransformer:
    """데이터를 데이터베이스 형식으로 변환하는 유틸리티 클래스"""
    
    @staticmethod
    def safe_get(data: Dict, key: str, default: Any = None) -> Any:
        """딕셔너리에서 안전하게 값을 가져옴"""
        try:
            value = data.get(key, default)
            # None이나 빈 문자열을 default로 대체
            if value is None or value == "":
                return default
            return value
        except (AttributeError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """안전하게 정수로 변환"""
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전하게 실수로 변환"""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_bool(value: Any, default: bool = False) -> bool:
        """안전하게 불리언으로 변환"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        if isinstance(value, int):
            return value != 0
        return default
    
    @staticmethod
    def safe_json(value: Any) -> Optional[str]:
        """안전하게 JSON 문자열로 변환"""
        try:
            if value is None:
                return None
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON 변환 실패: {e}")
            return None


# ==========================================
# 5. 데이터 삽입 클래스
# ==========================================

class DataLoader:
    """데이터베이스에 데이터를 삽입하는 메인 클래스"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.transformer = DataTransformer()
        self.stats = {
            "range": 0,
            "skill": 0,
            "character": 0,
            "range_grid": 0,
            "character_phase": 0,
            "character_attribute": 0,
            "character_skill": 0,
            "skill_level": 0,
            "character_talent": 0,
            "character_potential": 0,
            "character_tag": 0,
            "skin": 0,
            "item": 0,
            "module": 0,
            "consumption": 0
        }
    
    def clear_all_tables(self, conn) -> bool:
        """모든 테이블 데이터 삭제 (개발/테스트용)"""
        try:
            with conn.cursor() as cur:
                # 외래 키 제약 때문에 순서가 중요
                tables = [
                    'character_consumption',
                    'range_grid',
                    'character_attribute',
                    'character_phase',
                    'character_skill',
                    'skill_level',
                    'character_talent',
                    'character_potential',
                    'character_tag',
                    'skin_table',
                    'module_table',
                    'skill_table',
                    'character',
                    'item_table',
                    'range_table'
                ]
                
                for table in tables:
                    cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
                    logger.info(f"테이블 {table} 데이터 삭제 완료")
                
                conn.commit()
                logger.info("모든 테이블 데이터 삭제 완료")
                return True
                
        except psycopg2.Error as e:
            logger.error(f"테이블 삭제 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_range_data(self, conn, data: Dict[str, Any]) -> bool:
        """공격 범위 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                # range_table 삽입
                range_records = []
                grid_records = []
                
                for range_id, range_info in data.items():
                    if not range_id or not isinstance(range_info, dict):
                        continue
                    
                    direction = self.transformer.safe_int(
                        self.transformer.safe_get(range_info, 'direction', 1), 1
                    )
                    range_records.append((range_id, direction))
                    
                    # range_grid 데이터 준비
                    grids = self.transformer.safe_get(range_info, 'grids', [])
                    if isinstance(grids, list):
                        for grid in grids:
                            if isinstance(grid, dict):
                                row_val = self.transformer.safe_int(grid.get('row', 0))
                                col_val = self.transformer.safe_int(grid.get('col', 0))
                                grid_records.append((range_id, row_val, col_val))
                
                # range_table 일괄 삽입
                if range_records:
                    execute_values(
                        cur,
                        "INSERT INTO range_table (range_id, direction) VALUES %s ON CONFLICT (range_id) DO NOTHING",
                        range_records
                    )
                    self.stats["range"] = len(range_records)
                    logger.info(f"range_table 삽입 완료: {len(range_records)}개")
                
                # range_grid 일괄 삽입
                if grid_records:
                    execute_values(
                        cur,
                        "INSERT INTO range_grid (range_id, row_val, col_val) VALUES %s",
                        grid_records
                    )
                    self.stats["range_grid"] = len(grid_records)
                    logger.info(f"range_grid 삽입 완료: {len(grid_records)}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"range 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_skill_data(self, conn, data: Dict[str, Any]) -> bool:
        """스킬 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                # 먼저 존재하는 range_id 목록을 조회
                cur.execute("SELECT range_id FROM range_table")
                valid_range_ids = set(row[0] for row in cur.fetchall())
                logger.info(f"유효한 범위 ID {len(valid_range_ids)}개 확인됨")
                
                # skill_table 삽입
                skill_records = []
                level_records = []
                skipped_ranges = []
                
                for skill_id, skill_info in data.items():
                    if not skill_id or not isinstance(skill_info, dict):
                        continue
                    
                    icon_id = self.transformer.safe_get(skill_info, 'iconId')
                    hidden = self.transformer.safe_bool(
                        self.transformer.safe_get(skill_info, 'hidden', False)
                    )
                    skill_records.append((skill_id, icon_id, hidden))
                    
                    # skill_level 데이터 준비
                    levels = self.transformer.safe_get(skill_info, 'levels', [])
                    if isinstance(levels, list):
                        for idx, level in enumerate(levels):
                            if not isinstance(level, dict):
                                continue
                            
                            name = self.transformer.safe_get(level, 'name')
                            range_id = self.transformer.safe_get(level, 'rangeId')
                            
                            # range_id가 존재하지 않으면 None으로 설정
                            if range_id and range_id not in valid_range_ids:
                                skipped_ranges.append((skill_id, idx, range_id))
                                range_id = None
                            
                            description = self.transformer.safe_get(level, 'description')
                            
                            sp_data = self.transformer.safe_get(level, 'spData', {})
                            sp_type = self.transformer.safe_int(
                                self.transformer.safe_get(sp_data, 'spType')
                            ) if isinstance(sp_data, dict) else 0
                            sp_cost = self.transformer.safe_int(
                                self.transformer.safe_get(sp_data, 'spCost')
                            ) if isinstance(sp_data, dict) else 0
                            init_sp = self.transformer.safe_int(
                                self.transformer.safe_get(sp_data, 'initSp')
                            ) if isinstance(sp_data, dict) else 0
                            
                            duration = self.transformer.safe_float(
                                self.transformer.safe_get(level, 'duration', 0)
                            )
                            
                            blackboard = self.transformer.safe_get(level, 'blackboard')
                            blackboard_json = self.transformer.safe_json(blackboard)
                            
                            level_records.append((
                                skill_id, idx, name, range_id, description,
                                sp_type, sp_cost, init_sp, duration, blackboard_json
                            ))
                
                # skill_table 일괄 삽입
                if skill_records:
                    execute_values(
                        cur,
                        """INSERT INTO skill_table (skill_id, icon_id, hidden) 
                           VALUES %s ON CONFLICT (skill_id) DO NOTHING""",
                        skill_records
                    )
                    self.stats["skill"] = len(skill_records)
                    logger.info(f"skill_table 삽입 완료: {len(skill_records)}개")
                
                # skill_level 일괄 삽입
                if level_records:
                    execute_values(
                        cur,
                        """INSERT INTO skill_level 
                           (skill_id, level_index, name, range_id, description, 
                            sp_type, sp_cost, init_sp, duration, blackboard)
                           VALUES %s""",
                        level_records
                    )
                    self.stats["skill_level"] = len(level_records)
                    logger.info(f"skill_level 삽입 완료: {len(level_records)}개")
                
                # 건너뛴 범위 경고
                if skipped_ranges:
                    logger.warning(f"스킬에서 존재하지 않는 범위 ID {len(skipped_ranges)}개 건너뜀")
                    # 처음 5개만 표시
                    for skill_id, level_idx, range_id in skipped_ranges[:5]:
                        logger.warning(f"  - 스킬 {skill_id} 레벨 {level_idx}: 범위 {range_id}")
                    if len(skipped_ranges) > 5:
                        logger.warning(f"  ... 외 {len(skipped_ranges) - 5}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"skill 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_character_data(self, conn, data: Dict[str, Any]) -> bool:
        """캐릭터 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                # 먼저 존재하는 skill_id 목록을 조회
                cur.execute("SELECT skill_id FROM skill_table")
                valid_skill_ids = set(row[0] for row in cur.fetchall())
                logger.info(f"유효한 스킬 ID {len(valid_skill_ids)}개 확인됨")
                
                # 먼저 존재하는 range_id 목록을 조회
                cur.execute("SELECT range_id FROM range_table")
                valid_range_ids = set(row[0] for row in cur.fetchall())
                logger.info(f"유효한 범위 ID {len(valid_range_ids)}개 확인됨")
                
                # character 테이블 삽입
                char_records = []
                phase_records = []
                attr_records = []
                skill_records = []
                talent_records = []
                potential_records = []
                tag_records = []
                
                # 통계
                skipped_skills = []
                skipped_ranges = []
                
                for char_id, char_info in data.items():
                    if not char_id or not isinstance(char_info, dict):
                        continue
                    
                    # 기본 캐릭터 정보
                    name = self.transformer.safe_get(char_info, 'name', char_id)
                    appellation = self.transformer.safe_get(char_info, 'appellation')
                    description = self.transformer.safe_get(char_info, 'description')
                    rarity = self.transformer.safe_get(char_info, 'rarity')
                    profession = self.transformer.safe_get(char_info, 'profession')
                    sub_profession_id = self.transformer.safe_get(char_info, 'subProfessionId')
                    position = self.transformer.safe_get(char_info, 'position')
                    nation_id = self.transformer.safe_get(char_info, 'nationId')
                    group_id = self.transformer.safe_get(char_info, 'groupId')
                    team_id = self.transformer.safe_get(char_info, 'teamId')
                    display_number = self.transformer.safe_get(char_info, 'displayNumber')
                    
                    # isSpChar 필드 확인 (여러 가능한 필드명 시도)
                    is_sp_char = False
                    for field_name in ['isSpChar', 'isSpchar', 'isSp']:
                        if field_name in char_info:
                            is_sp_char = self.transformer.safe_bool(char_info[field_name])
                            break
                    
                    char_records.append((
                        char_id, name, appellation, description, rarity,
                        profession, sub_profession_id, position, nation_id,
                        group_id, team_id, display_number, is_sp_char
                    ))
                    
                    # phases (정예화 단계)
                    phases = self.transformer.safe_get(char_info, 'phases', [])
                    if isinstance(phases, list):
                        for phase_idx, phase in enumerate(phases):
                            if not isinstance(phase, dict):
                                continue
                            
                            max_level = self.transformer.safe_int(
                                self.transformer.safe_get(phase, 'maxLevel', 1)
                            )
                            range_id = self.transformer.safe_get(phase, 'rangeId')
                            
                            # range_id가 존재하지 않으면 None으로 설정 (외래 키 제약 조건 허용)
                            if range_id and range_id not in valid_range_ids:
                                skipped_ranges.append((char_id, range_id))
                                range_id = None
                            
                            phase_records.append((
                                char_id, phase_idx, max_level, range_id
                            ))
                            
                            # attributes (스탯)
                            attr_key_table = self.transformer.safe_get(phase, 'attributesKeyFrames', [])
                            if isinstance(attr_key_table, list):
                                for attr_frame in attr_key_table:
                                    if not isinstance(attr_frame, dict):
                                        continue
                                    
                                    level = self.transformer.safe_int(
                                        self.transformer.safe_get(attr_frame, 'level', 1)
                                    )
                                    data_dict = self.transformer.safe_get(attr_frame, 'data', {})
                                    
                                    if isinstance(data_dict, dict):
                                        max_hp = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'maxHp')
                                        )
                                        atk = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'atk')
                                        )
                                        def_val = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'def')
                                        )
                                        magic_resistance = self.transformer.safe_float(
                                            self.transformer.safe_get(data_dict, 'magicResistance')
                                        )
                                        cost = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'cost')
                                        )
                                        block_cnt = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'blockCnt')
                                        )
                                        move_speed = self.transformer.safe_float(
                                            self.transformer.safe_get(data_dict, 'moveSpeed')
                                        )
                                        attack_speed = self.transformer.safe_float(
                                            self.transformer.safe_get(data_dict, 'attackSpeed')
                                        )
                                        base_attack_time = self.transformer.safe_float(
                                            self.transformer.safe_get(data_dict, 'baseAttackTime')
                                        )
                                        respawn_time = self.transformer.safe_int(
                                            self.transformer.safe_get(data_dict, 'respawnTime')
                                        )
                                        
                                        attr_records.append((
                                            char_id, phase_idx, level, max_hp, atk, def_val,
                                            magic_resistance, cost, block_cnt, move_speed,
                                            attack_speed, base_attack_time, respawn_time
                                        ))
                    
                    # skills
                    skills = self.transformer.safe_get(char_info, 'skills', [])
                    if isinstance(skills, list):
                        for skill in skills:
                            if not isinstance(skill, dict):
                                continue
                            
                            skill_id = self.transformer.safe_get(skill, 'skillId')
                            if not skill_id:
                                continue
                            
                            # skill_id가 skill_table에 존재하는지 확인
                            if skill_id not in valid_skill_ids:
                                skipped_skills.append((char_id, skill_id))
                                continue  # 이 스킬은 건너뜀
                            
                            unlock_cond = self.transformer.safe_get(skill, 'unlockCond', {})
                            unlock_phase = 0
                            unlock_level = 1
                            
                            if isinstance(unlock_cond, dict):
                                unlock_phase = self.transformer.safe_int(
                                    self.transformer.safe_get(unlock_cond, 'phase', 0)
                                )
                                unlock_level = self.transformer.safe_int(
                                    self.transformer.safe_get(unlock_cond, 'level', 1)
                                )
                            
                            skill_records.append((
                                char_id, skill_id, unlock_phase, unlock_level
                            ))
                    
                    # talents
                    talents = self.transformer.safe_get(char_info, 'talents', [])
                    if isinstance(talents, list):
                        for talent_idx, talent_list in enumerate(talents):
                            if not isinstance(talent_list, dict):
                                continue
                            
                            candidates = self.transformer.safe_get(talent_list, 'candidates', [])
                            if isinstance(candidates, list):
                                for candidate in candidates:
                                    if not isinstance(candidate, dict):
                                        continue
                                    
                                    unlock_condition = self.transformer.safe_get(
                                        candidate, 'unlockCondition', {}
                                    )
                                    unlock_phase = 0
                                    unlock_level = 1
                                    
                                    if isinstance(unlock_condition, dict):
                                        unlock_phase = self.transformer.safe_int(
                                            self.transformer.safe_get(unlock_condition, 'phase', 0)
                                        )
                                        unlock_level = self.transformer.safe_int(
                                            self.transformer.safe_get(unlock_condition, 'level', 1)
                                        )
                                    
                                    name = self.transformer.safe_get(candidate, 'name')
                                    description = self.transformer.safe_get(candidate, 'description')
                                    required_potential = self.transformer.safe_int(
                                        self.transformer.safe_get(
                                            candidate, 'requiredPotentialRank', 0
                                        )
                                    )
                                    
                                    talent_records.append((
                                        char_id, talent_idx, name, description,
                                        unlock_phase, unlock_level, required_potential
                                    ))
                    
                    # potentials
                    potential_ranks = self.transformer.safe_get(char_info, 'potentialRanks', [])
                    if isinstance(potential_ranks, list):
                        for rank_idx, potential in enumerate(potential_ranks):
                            if not isinstance(potential, dict):
                                continue
                            
                            pot_type = self.transformer.safe_get(potential, 'type')
                            description = self.transformer.safe_get(potential, 'description')
                            
                            potential_records.append((
                                char_id, rank_idx, pot_type, description
                            ))
                    
                    # tags
                    tag_list = self.transformer.safe_get(char_info, 'tagList', [])
                    if isinstance(tag_list, list):
                        for tag in tag_list:
                            if tag:  # 빈 문자열이 아닌 경우에만
                                tag_records.append((char_id, tag))
                
                # 일괄 삽입
                if char_records:
                    execute_values(
                        cur,
                        """INSERT INTO character 
                           (char_id, name, appellation, description, rarity, profession,
                            sub_profession_id, position, nation_id, group_id, team_id,
                            display_number, is_sp_char)
                           VALUES %s ON CONFLICT (char_id) DO NOTHING""",
                        char_records
                    )
                    self.stats["character"] = len(char_records)
                    logger.info(f"character 삽입 완료: {len(char_records)}개")
                
                if phase_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_phase 
                           (char_id, phase_index, max_level, range_id)
                           VALUES %s
                           ON CONFLICT (char_id, phase_index) DO NOTHING""",
                        phase_records
                    )
                    self.stats["character_phase"] = len(phase_records)
                    logger.info(f"character_phase 삽입 완료: {len(phase_records)}개")
                
                # character_attribute는 phase_id가 필요하므로 별도 처리
                if attr_records:
                    for record in attr_records:
                        char_id, phase_idx = record[0], record[1]
                        
                        # phase_id 조회
                        cur.execute(
                            "SELECT phase_id FROM character_phase WHERE char_id = %s AND phase_index = %s",
                            (char_id, phase_idx)
                        )
                        result = cur.fetchone()
                        
                        if result:
                            phase_id = result[0]
                            cur.execute(
                                """INSERT INTO character_attribute 
                                   (phase_id, level, max_hp, atk, def, magic_resistance,
                                    cost, block_cnt, move_speed, attack_speed,
                                    base_attack_time, respawn_time)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                (phase_id,) + record[2:]
                            )
                    
                    self.stats["character_attribute"] = len(attr_records)
                    logger.info(f"character_attribute 삽입 완료: {len(attr_records)}개")
                
                if skill_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_skill 
                           (char_id, skill_id, unlock_phase, unlock_level)
                           VALUES %s""",
                        skill_records
                    )
                    self.stats["character_skill"] = len(skill_records)
                    logger.info(f"character_skill 삽입 완료: {len(skill_records)}개")
                
                if talent_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_talent 
                           (char_id, talent_index, name, description,
                            unlock_phase, unlock_level, required_potential)
                           VALUES %s""",
                        talent_records
                    )
                    self.stats["character_talent"] = len(talent_records)
                    logger.info(f"character_talent 삽입 완료: {len(talent_records)}개")
                
                if potential_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_potential 
                           (char_id, rank_index, type, description)
                           VALUES %s""",
                        potential_records
                    )
                    self.stats["character_potential"] = len(potential_records)
                    logger.info(f"character_potential 삽입 완료: {len(potential_records)}개")
                
                if tag_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_tag (char_id, tag_name) VALUES %s""",
                        tag_records
                    )
                    self.stats["character_tag"] = len(tag_records)
                    logger.info(f"character_tag 삽입 완료: {len(tag_records)}개")
                
                # 건너뛴 데이터 경고
                if skipped_skills:
                    logger.warning(f"존재하지 않는 스킬 ID {len(skipped_skills)}개 건너뜀")
                    # 처음 5개만 표시
                    for char_id, skill_id in skipped_skills[:5]:
                        logger.warning(f"  - 캐릭터 {char_id}: 스킬 {skill_id}")
                    if len(skipped_skills) > 5:
                        logger.warning(f"  ... 외 {len(skipped_skills) - 5}개")
                
                if skipped_ranges:
                    logger.warning(f"존재하지 않는 범위 ID {len(skipped_ranges)}개 건너뜀")
                    # 처음 5개만 표시
                    for char_id, range_id in skipped_ranges[:5]:
                        logger.warning(f"  - 캐릭터 {char_id}: 범위 {range_id}")
                    if len(skipped_ranges) > 5:
                        logger.warning(f"  ... 외 {len(skipped_ranges) - 5}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"character 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_skin_data(self, conn, data: Dict[str, Any]) -> bool:
        """스킨 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                skin_records = []
                
                # charSkins 딕셔너리 처리
                char_skins = self.transformer.safe_get(data, 'charSkins', {})
                if not isinstance(char_skins, dict):
                    logger.warning("charSkins가 딕셔너리가 아닙니다")
                    return False
                
                for skin_id, skin_info in char_skins.items():
                    if not skin_id or not isinstance(skin_info, dict):
                        continue
                    
                    char_id = self.transformer.safe_get(skin_info, 'charId')
                    if not char_id:
                        continue
                    
                    name = self.transformer.safe_get(skin_info, 'displaySkin', {})
                    if isinstance(name, dict):
                        name = self.transformer.safe_get(name, 'skinName', skin_id)
                    else:
                        name = skin_id
                    
                    description = self.transformer.safe_get(skin_info, 'content')
                    group_name = self.transformer.safe_get(skin_info, 'displaySkin', {})
                    if isinstance(group_name, dict):
                        group_name = self.transformer.safe_get(group_name, 'skinGroupName')
                    else:
                        group_name = None
                    
                    illust_id = self.transformer.safe_get(skin_info, 'illustId')
                    avatar_id = self.transformer.safe_get(skin_info, 'avatarId')
                    portrait_id = self.transformer.safe_get(skin_info, 'portraitId')
                    model_id = self.transformer.safe_get(skin_info, 'modelId')
                    
                    drawer_list = self.transformer.safe_get(
                        self.transformer.safe_get(skin_info, 'displaySkin', {}),
                        'drawerList'
                    )
                    if not isinstance(drawer_list, list):
                        drawer_list = None
                    
                    skin_records.append((
                        skin_id, char_id, name, description, group_name,
                        illust_id, avatar_id, portrait_id, model_id, drawer_list
                    ))
                
                if skin_records:
                    execute_values(
                        cur,
                        """INSERT INTO skin_table 
                           (skin_id, char_id, name, description, group_name,
                            illust_id, avatar_id, portrait_id, model_id, drawer_list)
                           VALUES %s ON CONFLICT (skin_id) DO NOTHING""",
                        skin_records
                    )
                    self.stats["skin"] = len(skin_records)
                    logger.info(f"skin_table 삽입 완료: {len(skin_records)}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"skin 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    

    
    def load_item_data(self, conn, data: Dict[str, Any]) -> bool:
        """아이템 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                item_records = []
                
                # items 딕셔너리 처리
                items = self.transformer.safe_get(data, 'items', {})
                if not isinstance(items, dict):
                    logger.warning("items가 딕셔너리가 아닙니다")
                    return False
                
                for item_id, item_info in items.items():
                    if not item_id or not isinstance(item_info, dict):
                        continue
                    
                    name = self.transformer.safe_get(item_info, 'name')
                    description = self.transformer.safe_get(item_info, 'description')
                    usage = self.transformer.safe_get(item_info, 'usage')
                    obtain_approach = self.transformer.safe_get(item_info, 'obtainApproach')
                    
                    classify_type = self.transformer.safe_get(item_info, 'classifyType')
                    item_type = self.transformer.safe_get(item_info, 'itemType')
                    rarity = self.transformer.safe_int(
                        self.transformer.safe_get(item_info, 'rarity', 0)
                    )
                    sort_id = self.transformer.safe_int(
                        self.transformer.safe_get(item_info, 'sortId', 0)
                    )
                    icon_id = self.transformer.safe_get(item_info, 'iconId')
                    
                    item_records.append((
                        item_id, name, description, usage, obtain_approach,
                        classify_type, item_type, rarity, sort_id, icon_id
                    ))
                
                if item_records:
                    execute_values(
                        cur,
                        """INSERT INTO item_table 
                           (item_id, name, description, usage, obtain_approach,
                            classify_type, item_type, rarity, sort_id, icon_id)
                           VALUES %s ON CONFLICT (item_id) DO NOTHING""",
                        item_records
                    )
                    self.stats["item"] = len(item_records)
                    logger.info(f"item_table 삽입 완료: {len(item_records)}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"item 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_module_data(self, conn, data: Dict[str, Any]) -> bool:
        """모듈 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                # 먼저 존재하는 char_id 목록을 조회
                cur.execute("SELECT char_id FROM character")
                valid_char_ids = set(row[0] for row in cur.fetchall())
                logger.info(f"유효한 캐릭터 ID {len(valid_char_ids)}개 확인됨")
                
                module_records = []
                skipped_chars = []
                
                # equipDict 딕셔너리 처리
                equip_dict = self.transformer.safe_get(data, 'equipDict', {})
                if not isinstance(equip_dict, dict):
                    logger.warning("equipDict가 딕셔너리가 아닙니다")
                    return False
                
                for module_id, module_info in equip_dict.items():
                    if not module_id or not isinstance(module_info, dict):
                        continue
                    
                    char_id = self.transformer.safe_get(module_info, 'charId')
                    if not char_id:
                        continue
                    
                    # 캐릭터 ID 검증
                    if char_id not in valid_char_ids:
                        skipped_chars.append((module_id, char_id))
                        continue
                    
                    name = self.transformer.safe_get(module_info, 'uniEquipName')
                    type_icon = self.transformer.safe_get(module_info, 'typeIcon')
                    description = self.transformer.safe_get(module_info, 'uniEquipDesc')
                    sort_id = self.transformer.safe_int(
                        self.transformer.safe_get(module_info, 'sortId', 0)
                    )
                    
                    module_records.append((
                        module_id, char_id, name, type_icon, description, sort_id
                    ))
                
                if module_records:
                    execute_values(
                        cur,
                        """INSERT INTO module_table 
                           (module_id, char_id, name, type_icon, description, sort_id)
                           VALUES %s ON CONFLICT (module_id) DO NOTHING""",
                        module_records
                    )
                    self.stats["module"] = len(module_records)
                    logger.info(f"module_table 삽입 완료: {len(module_records)}개")
                
                # 건너뛴 캐릭터 경고
                if skipped_chars:
                    logger.warning(f"존재하지 않는 캐릭터 ID {len(skipped_chars)}개 건너뜀")
                    for module_id, char_id in skipped_chars[:5]:
                        logger.warning(f"  - 모듈 {module_id}: 캐릭터 {char_id}")
                    if len(skipped_chars) > 5:
                        logger.warning(f"  ... 외 {len(skipped_chars) - 5}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"module 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False
    
    def load_consumption_data(self, conn, character_data: Dict[str, Any], 
                              module_data: Dict[str, Any]) -> bool:
        """소모품(재료) 데이터 삽입"""
        try:
            with conn.cursor() as cur:
                # 유효한 외래 키 조회
                cur.execute("SELECT char_id FROM character")
                valid_char_ids = set(row[0] for row in cur.fetchall())
                
                cur.execute("SELECT item_id FROM item_table")
                valid_item_ids = set(row[0] for row in cur.fetchall())
                
                cur.execute("SELECT skill_id FROM skill_table")
                valid_skill_ids = set(row[0] for row in cur.fetchall())
                
                cur.execute("SELECT module_id FROM module_table")
                valid_module_ids = set(row[0] for row in cur.fetchall())
                
                logger.info(f"유효한 ID 확인: 캐릭터({len(valid_char_ids)}), "
                          f"아이템({len(valid_item_ids)}), 스킬({len(valid_skill_ids)}), "
                          f"모듈({len(valid_module_ids)})")
                
                consumption_records = []
                skipped_records = []
                
                # 1. 캐릭터 데이터에서 정예화/스킬 재료 추출
                for char_id, char_info in character_data.items():
                    if not isinstance(char_info, dict) or char_id not in valid_char_ids:
                        continue
                    
                    # 정예화 재료 (phases -> evolveCost)
                    phases = self.transformer.safe_get(char_info, 'phases', [])
                    if isinstance(phases, list):
                        for phase_idx, phase in enumerate(phases):
                            if not isinstance(phase, dict):
                                continue
                            
                            evolve_cost = self.transformer.safe_get(phase, 'evolveCost')
                            if isinstance(evolve_cost, list):
                                for cost_item in evolve_cost:
                                    if not isinstance(cost_item, dict):
                                        continue
                                    
                                    item_id = self.transformer.safe_get(cost_item, 'id')
                                    count = self.transformer.safe_int(
                                        self.transformer.safe_get(cost_item, 'count', 0)
                                    )
                                    
                                    if item_id and item_id in valid_item_ids and count > 0:
                                        consumption_records.append((
                                            char_id, 'EVOLVE', phase_idx, None, 
                                            item_id, count, None
                                        ))
                                    elif item_id and count > 0:
                                        skipped_records.append((char_id, item_id, '정예화'))
                    
                    # 스킬 공통 재료 (allSkillLvlup)
                    all_skill_lvlup = self.transformer.safe_get(char_info, 'allSkillLvlup', [])
                    if isinstance(all_skill_lvlup, list):
                        for skill_idx, skill_costs in enumerate(all_skill_lvlup):
                            if not isinstance(skill_costs, dict):
                                continue
                            
                            lv_up_cost = self.transformer.safe_get(skill_costs, 'lvlUpCost')
                            if isinstance(lv_up_cost, list):
                                for cost_item in lv_up_cost:
                                    if not isinstance(cost_item, dict):
                                        continue
                                    
                                    item_id = self.transformer.safe_get(cost_item, 'id')
                                    count = self.transformer.safe_int(
                                        self.transformer.safe_get(cost_item, 'count', 0)
                                    )
                                    
                                    if item_id and item_id in valid_item_ids and count > 0:
                                        consumption_records.append((
                                            char_id, 'SKILL_COMMON', skill_idx + 2, None,
                                            item_id, count, None
                                        ))
                                    elif item_id and count > 0:
                                        skipped_records.append((char_id, item_id, '스킬'))
                    
                    # 스킬 마스터리 재료 (skills -> levelUpCostCond)
                    skills = self.transformer.safe_get(char_info, 'skills', [])
                    if isinstance(skills, list):
                        for skill in skills:
                            if not isinstance(skill, dict):
                                continue
                            
                            skill_id = self.transformer.safe_get(skill, 'skillId')
                            if not skill_id or skill_id not in valid_skill_ids:
                                continue
                            
                            level_up_cost_cond = self.transformer.safe_get(
                                skill, 'levelUpCostCond', []
                            )
                            if isinstance(level_up_cost_cond, list):
                                for mastery_idx, mastery_cost in enumerate(level_up_cost_cond):
                                    if not isinstance(mastery_cost, dict):
                                        continue
                                    
                                    lv_up_cost = self.transformer.safe_get(
                                        mastery_cost, 'levelUpCost'
                                    )
                                    if isinstance(lv_up_cost, list):
                                        for cost_item in lv_up_cost:
                                            if not isinstance(cost_item, dict):
                                                continue
                                            
                                            item_id = self.transformer.safe_get(cost_item, 'id')
                                            count = self.transformer.safe_int(
                                                self.transformer.safe_get(cost_item, 'count', 0)
                                            )
                                            
                                            if item_id and item_id in valid_item_ids and count > 0:
                                                consumption_records.append((
                                                    char_id, 'SKILL_MASTERY', mastery_idx + 1,
                                                    skill_id, item_id, count, None
                                                ))
                                            elif item_id and count > 0:
                                                skipped_records.append((char_id, item_id, '마스터리'))
                
                # 2. 모듈 데이터에서 재료 추출
                if module_data:
                    equip_dict = self.transformer.safe_get(module_data, 'equipDict', {})
                    if isinstance(equip_dict, dict):
                        for module_id, module_info in equip_dict.items():
                            if not isinstance(module_info, dict):
                                continue
                            
                            if module_id not in valid_module_ids:
                                continue
                            
                            char_id = self.transformer.safe_get(module_info, 'charId')
                            if not char_id or char_id not in valid_char_ids:
                                continue
                            
                            # 모듈 각 단계별 재료
                            item_cost = self.transformer.safe_get(module_info, 'itemCost', {})
                            if isinstance(item_cost, dict):
                                for stage_key, stage_costs in item_cost.items():
                                    if not isinstance(stage_costs, list):
                                        continue
                                    
                                    # stage_key는 보통 "1", "2", "3" 형태
                                    stage_num = self.transformer.safe_int(stage_key, 0)
                                    
                                    for cost_item in stage_costs:
                                        if not isinstance(cost_item, dict):
                                            continue
                                        
                                        item_id = self.transformer.safe_get(cost_item, 'id')
                                        count = self.transformer.safe_int(
                                            self.transformer.safe_get(cost_item, 'count', 0)
                                        )
                                        
                                        if item_id and item_id in valid_item_ids and count > 0:
                                            consumption_records.append((
                                                char_id, 'MODULE', stage_num, None,
                                                item_id, count, module_id
                                            ))
                                        elif item_id and count > 0:
                                            skipped_records.append((char_id, item_id, '모듈'))
                
                # 일괄 삽입
                if consumption_records:
                    execute_values(
                        cur,
                        """INSERT INTO character_consumption 
                           (char_id, type, level, skill_id, item_id, count, module_id)
                           VALUES %s""",
                        consumption_records
                    )
                    self.stats["consumption"] = len(consumption_records)
                    logger.info(f"character_consumption 삽입 완료: {len(consumption_records)}개")
                
                # 건너뛴 아이템 경고
                if skipped_records:
                    logger.warning(f"존재하지 않는 아이템 ID {len(skipped_records)}개 건너뜀")
                    unique_skipped = list(set(skipped_records))[:5]
                    for char_id, item_id, cons_type in unique_skipped:
                        logger.warning(f"  - 캐릭터 {char_id} ({cons_type}): 아이템 {item_id}")
                    if len(skipped_records) > 5:
                        logger.warning(f"  ... 외 {len(skipped_records) - 5}개")
                
                conn.commit()
                return True
                
        except psycopg2.Error as e:
            logger.error(f"consumption 데이터 삽입 중 오류: {e}")
            conn.rollback()
            return False

    def print_statistics(self):
        """삽입 통계 출력"""
        logger.info("=" * 50)
        logger.info("데이터 삽입 통계")
        logger.info("=" * 50)
        for table, count in self.stats.items():
            logger.info(f"{table:25s}: {count:6d}개")
        logger.info("=" * 50)


# ==========================================
# 6. 메인 실행 함수
# ==========================================

def main():
    """메인 실행 함수"""
    start_time = time.time()
    
    logger.info("=" * 50)
    logger.info("Arknights 데이터 로더 시작")
    logger.info("=" * 50)
    
    db_manager = None
    
    try:
        # 1. 데이터베이스 연결
        logger.info("데이터베이스 연결 중...")
        db_manager = DatabaseManager(DB_CONFIG)
        
        # 2. 데이터 다운로드
        logger.info("데이터 다운로드 중...")
        fetcher = DataFetcher()
        
        range_data = fetcher.fetch_json(URLS["range"])
        skill_data = fetcher.fetch_json(URLS["skill"])
        character_data = fetcher.fetch_json(URLS["character"])
        skin_data = fetcher.fetch_json(URLS["skin"])
        item_data = fetcher.fetch_json(URLS["item"])
        uniequip_data = fetcher.fetch_json(URLS["uniequip"])
        
        # 3. 데이터 검증
        if not all([
            fetcher.validate_data(range_data, "range"),
            fetcher.validate_data(skill_data, "skill"),
            fetcher.validate_data(character_data, "character"),
            fetcher.validate_data(skin_data, "skin"),
            fetcher.validate_data(item_data, "item"),
            fetcher.validate_data(uniequip_data, "uniequip")
        ]):
            logger.error("데이터 검증 실패")
            return 1
        
        # 4. 데이터 삽입
        with db_manager.get_connection() as conn:
            loader = DataLoader(db_manager)
            
            # 기존 데이터 삭제 (필요한 경우)
            logger.info("기존 데이터 삭제 중...")
            if not loader.clear_all_tables(conn):
                logger.error("기존 데이터 삭제 실패")
                return 1
            
            # 순서대로 삽입 (외래 키 제약 고려)
            logger.info("range 데이터 삽입 중...")
            if not loader.load_range_data(conn, range_data):
                logger.error("range 데이터 삽입 실패")
                return 1
            
            logger.info("skill 데이터 삽입 중...")
            if not loader.load_skill_data(conn, skill_data):
                logger.error("skill 데이터 삽입 실패")
                return 1
            
            logger.info("character 데이터 삽입 중...")
            if not loader.load_character_data(conn, character_data):
                logger.error("character 데이터 삽입 실패")
                return 1
            
            logger.info("skin 데이터 삽입 중...")
            if not loader.load_skin_data(conn, skin_data):
                logger.error("skin 데이터 삽입 실패")
                return 1

            logger.info("item 데이터 삽입 중...")
            if not loader.load_item_data(conn, item_data):
                logger.error("item 데이터 삽입 실패")
                return 1

            logger.info("module 데이터 삽입 중...")
            if not loader.load_module_data(conn, uniequip_data):
                logger.error("module 데이터 삽입 실패")
                return 1

            logger.info("consumption 데이터 삽입 중...")
            if not loader.load_consumption_data(conn, character_data, uniequip_data):
                logger.error("consumption 데이터 삽입 실패")
                return 1
                logger.error("skin 데이터 삽입 실패")
                return 1
            
            # 통계 출력
            loader.print_statistics()
        
        elapsed_time = time.time() - start_time
        logger.info("=" * 50)
        logger.info(f"전체 작업 완료! (소요 시간: {elapsed_time:.2f}초)")
        logger.info("=" * 50)
        return 0
        
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        return 1
        
    finally:
        if db_manager:
            db_manager.close_all()


if __name__ == "__main__":
    sys.exit(main())