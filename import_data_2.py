#!/usr/bin/env python3
"""
Arknights skin_table.json 데이터를 PostgreSQL에 삽입하는 스크립트
- skin_groups 테이블
- character_skins 테이블
- character_skin_details 테이블
"""

import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from typing import Dict, Optional, Set, List, Tuple
import os
import sys

from dotenv import load_dotenv


load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
DB_CONFIG = {
    "host": HOST,
    "database": DBNAME,
    "user":  USER,
    "password": PASSWORD,
    "port":  PORT
}

class SkinGroupCache:
    """스킨 그룹 ID 조회 및 관리 캐시"""
    
    def __init__(self, cursor):
        self.cursor = cursor
        self.cache: Dict[str, Optional[int]] = {}
    
    def get_or_create_skin_group_id(self, group_name: str) -> Optional[int]:
        """스킨 그룹 이름으로 ID 조회 또는 생성"""
        if not group_name:
            return None
            
        if group_name not in self.cache:
            # 먼저 조회
            self.cursor.execute(
                "SELECT skin_group_id FROM skin_groups WHERE name_ko = %s",
                (group_name,)
            )
            result = self.cursor.fetchone()
            
            if result:
                self.cache[group_name] = result[0]
            else:
                # 없으면 생성
                self.cursor.execute(
                    "INSERT INTO skin_groups (name_ko, created_at) VALUES (%s, %s) RETURNING skin_group_id",
                    (group_name, datetime.now())
                )
                self.cache[group_name] = self.cursor.fetchone()[0]
        
        return self.cache[group_name]


class CharacterIdCache:
    """캐릭터 ID 조회 캐시"""
    
    def __init__(self, cursor):
        self.cursor = cursor
        self.cache: Dict[str, Optional[int]] = {}
    
    def get_character_id(self, char_code: str) -> Optional[int]:
        """캐릭터 코드로 character_id 조회"""
        if char_code not in self.cache:
            self.cursor.execute(
                "SELECT character_id FROM characters WHERE code = %s",
                (char_code,)
            )
            result = self.cursor.fetchone()
            self.cache[char_code] = result[0] if result else None
        
        return self.cache[char_code]


class SkinIdCache:
    """스킨 ID 조회 캐시"""
    
    def __init__(self, cursor):
        self.cursor = cursor
        self.cache: Dict[str, Optional[int]] = {}
    
    def get_skin_id(self, skin_code: str) -> Optional[int]:
        """스킨 코드로 skin_id 조회"""
        if skin_code not in self.cache:
            self.cursor.execute(
                "SELECT skin_id FROM character_skins WHERE skin_code = %s",
                (skin_code,)
            )
            result = self.cursor.fetchone()
            self.cache[skin_code] = result[0] if result else None
        
        return self.cache[skin_code]


class CompleteSkinDataImporter:
    """완전한 스킨 데이터 임포터"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """데이터베이스 연결"""
        print("💾 데이터베이스 연결 중...")
        self.connection = psycopg2.connect(**self.db_config)
        self.cursor = self.connection.cursor()
    
    def disconnect(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def load_json(self, json_path: str) -> Dict:
        """JSON 파일 로드"""
        print(f"📥 JSON 파일 읽는 중: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def insert_skin_groups(self, skins_data: Dict[str, Dict]) -> SkinGroupCache:
        """스킨 그룹 데이터 추출 및 삽입"""
        print("\n=== 1단계: 스킨 그룹 삽입 ===")
        
        # 고유한 스킨 그룹 이름 추출
        skin_groups: Set[str] = set()
        for skin_data in skins_data.values():
            display_skin = skin_data.get('displaySkin', {})
            if display_skin:
                group_name = display_skin.get('skinGroupName')
                if group_name:
                    skin_groups.add(group_name)
        
        print(f"📋 {len(skin_groups)}개의 고유 스킨 그룹 발견")
        
        # 캐시 생성 (자동으로 삽입됨)
        cache = SkinGroupCache(self.cursor)
        inserted_count = 0
        
        for group_name in sorted(skin_groups):
            group_id = cache.get_or_create_skin_group_id(group_name)
            if group_id:
                inserted_count += 1
        
        print(f"✨ {inserted_count}개 스킨 그룹 처리 완료")
        return cache
    
    def extract_skin_data(
        self, 
        skin_code: str, 
        skin_data: Dict, 
        char_cache: CharacterIdCache
    ) -> Optional[Tuple]:
        """character_skins 테이블용 데이터 추출"""
        char_id = skin_data.get('charId')
        if not char_id:
            return None
        
        character_id = char_cache.get_character_id(char_id)
        if character_id is None:
            print(f"⚠️  캐릭터를 찾을 수 없음: {char_id} (스킨: {skin_code})")
            return None
        
        display_skin = skin_data.get('displaySkin', {}) or {}
        
        skin_name = display_skin.get('skinName')
        series_name = display_skin.get('skinGroupName')
        
        drawer_list = display_skin.get('drawerList', [])
        illustrator = drawer_list[0] if drawer_list else None
        
        portrait_id = skin_data.get('portraitId')
        avatar_id = skin_data.get('avatarId')
        
        now = datetime.now()
        
        return (
            skin_code,
            character_id,
            skin_name,
            series_name,
            illustrator,
            portrait_id,
            avatar_id,
            now,
            now
        )
    
    def insert_character_skins(
        self, 
        skins_data: Dict[str, Dict],
        char_cache: CharacterIdCache
    ) -> int:
        """character_skins 테이블에 데이터 삽입"""
        print("\n=== 2단계: 캐릭터 스킨 삽입 ===")
        
        insert_data = []
        skip_count = 0
        
        print("📋 데이터 추출 중...")
        for skin_code, skin_data in skins_data.items():
            extracted = self.extract_skin_data(skin_code, skin_data, char_cache)
            if extracted:
                insert_data.append(extracted)
            else:
                skip_count += 1
        
        if not insert_data:
            print("❌ 삽입할 데이터가 없습니다.")
            return 0
        
        insert_sql = """
            INSERT INTO character_skins (
                skin_code, character_id, name_ko, series_name, 
                illustrator, portrait_id, avatar_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (skin_code) 
            DO UPDATE SET
                character_id = EXCLUDED.character_id,
                name_ko = EXCLUDED.name_ko,
                series_name = EXCLUDED.series_name,
                illustrator = EXCLUDED.illustrator,
                portrait_id = EXCLUDED.portrait_id,
                avatar_id = EXCLUDED.avatar_id,
                updated_at = EXCLUDED.updated_at
        """
        
        print(f"💾 {len(insert_data)}개의 스킨 데이터 삽입 중...")
        execute_batch(self.cursor, insert_sql, insert_data, page_size=100)
        
        print(f"✨ {len(insert_data)}개 스킨 삽입/업데이트 완료")
        if skip_count > 0:
            print(f"⚠️  {skip_count}개 스킨 스킵됨 (캐릭터 미존재)")
        
        return len(insert_data)
    
    def extract_skin_detail_data(
        self,
        skin_code: str,
        skin_data: Dict,
        skin_cache: SkinIdCache,
        group_cache: SkinGroupCache
    ) -> Optional[Tuple]:
        """character_skin_details 테이블용 데이터 추출"""
        skin_id = skin_cache.get_skin_id(skin_code)
        if skin_id is None:
            return None
        
        display_skin = skin_data.get('displaySkin', {}) or {}
        
        # 스킨 그룹 ID 조회
        group_name = display_skin.get('skinGroupName')
        skin_group_id = group_cache.get_or_create_skin_group_id(group_name) if group_name else None
        
        # 상세 정보 추출
        content = display_skin.get('content')
        dialog = display_skin.get('dialog')
        description = display_skin.get('description')
        usage_text = display_skin.get('usage')
        
        now = datetime.now()
        
        return (
            skin_id,
            skin_group_id,
            content,
            dialog,
            description,
            usage_text,
            now,
            now
        )
    
    def insert_character_skin_details(
        self,
        skins_data: Dict[str, Dict],
        skin_cache: SkinIdCache,
        group_cache: SkinGroupCache
    ) -> int:
        """character_skin_details 테이블에 데이터 삽입"""
        print("\n=== 3단계: 스킨 상세 정보 삽입 ===")
        
        insert_data = []
        skip_count = 0
        
        print("📋 데이터 추출 중...")
        for skin_code, skin_data in skins_data.items():
            extracted = self.extract_skin_detail_data(
                skin_code, skin_data, skin_cache, group_cache
            )
            if extracted:
                insert_data.append(extracted)
            else:
                skip_count += 1
        
        if not insert_data:
            print("❌ 삽입할 데이터가 없습니다.")
            return 0
        
        insert_sql = """
            INSERT INTO character_skin_details (
                skin_id, skin_group_id, content, dialog, 
                description, usage_text, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (skin_id) 
            DO UPDATE SET
                skin_group_id = EXCLUDED.skin_group_id,
                content = EXCLUDED.content,
                dialog = EXCLUDED.dialog,
                description = EXCLUDED.description,
                usage_text = EXCLUDED.usage_text,
                updated_at = EXCLUDED.updated_at
        """
        
        print(f"💾 {len(insert_data)}개의 스킨 상세 정보 삽입 중...")
        execute_batch(self.cursor, insert_sql, insert_data, page_size=100)
        
        print(f"✨ {len(insert_data)}개 스킨 상세 정보 삽입/업데이트 완료")
        if skip_count > 0:
            print(f"⚠️  {skip_count}개 스킵됨")
        
        return len(insert_data)
    
    def import_from_file(self, json_path: str):
        """JSON 파일에서 데이터 가져와 DB에 삽입"""
        try:
            # JSON 로드
            data = self.load_json(json_path)
            char_skins = data.get('charSkins', {})
            
            if not char_skins:
                print("❌ charSkins 데이터가 없습니다.")
                return
            
            print(f"총 {len(char_skins)}개의 스킨 데이터 발견\n")
            
            # 데이터베이스 연결
            self.connect()
            
            try:
                # 1단계: 스킨 그룹 삽입
                group_cache = self.insert_skin_groups(char_skins)
                
                # 2단계: 캐릭터 스킨 삽입
                char_cache = CharacterIdCache(self.cursor)
                skin_count = self.insert_character_skins(char_skins, char_cache)
                
                # 3단계: 스킨 상세 정보 삽입
                skin_cache = SkinIdCache(self.cursor)
                detail_count = self.insert_character_skin_details(
                    char_skins, skin_cache, group_cache
                )
                
                # 커밋
                self.connection.commit()
                
                print("\n" + "="*50)
                print("✅ 모든 데이터 삽입 완료!")
                print(f"   - 스킨 그룹: {len(group_cache.cache)}개")
                print(f"   - 캐릭터 스킨: {skin_count}개")
                print(f"   - 스킨 상세 정보: {detail_count}개")
                print("="*50)
                
            except Exception as e:
                self.connection.rollback()
                print(f"\n❌ 오류 발생, 롤백됨: {e}")
                raise
            
        finally:
            self.disconnect()


def get_db_config_from_env() -> Dict[str, str]:
    """환경 변수에서 DB 설정 가져오기"""
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        print("\n환경 변수 설정 예시:")
        print("export DB_HOST=localhost")
        print("export DB_PORT=5432")
        print("export DB_NAME=arknights")
        print("export DB_USER=your_username")
        print("export DB_PASSWORD=your_password")
        sys.exit(1)
    
    return {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }


def main():
    """메인 실행 함수"""
    
    # 명령줄 인자로 JSON 파일 경로 받기
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        json_file_path = 'C:\\Users\\rugsn\\Documents\\GitHub\\Arknight-BE\\data\\skin_table.json'
    
    if not os.path.exists(json_file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
        sys.exit(1)
    
    # 환경 변수에서 DB 설정 가져오기

    # 임포터 실행
    importer = CompleteSkinDataImporter(DB_CONFIG)
    
    try:
        importer.import_from_file(json_file_path)
    except Exception as e:
        print(f"\n🔥 작업 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()