#!/usr/bin/env python3
"""
Arknights skin_table.json 데이터를 PostgreSQL character_skins 테이블에 삽입하는 스크립트
"""

import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

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


class SkinDataImporter:
    """Skin 데이터 임포터"""
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Args:
            db_config: 데이터베이스 연결 설정
                - host: 호스트
                - port: 포트
                - database: 데이터베이스명
                - user: 사용자명
                - password: 비밀번호
        """
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
    
    def extract_skin_data(self, skin_code: str, skin_data: Dict, cache: CharacterIdCache) -> Optional[tuple]:
        """스킨 데이터 추출 및 변환"""
        char_id = skin_data.get('charId')
        if not char_id:
            return None
        
        # 캐릭터 ID 조회
        character_id = cache.get_character_id(char_id)
        if character_id is None:
            print(f"⚠️  캐릭터를 찾을 수 없음: {char_id} (스킨: {skin_code})")
            return None
        
        # displaySkin에서 정보 추출
        display_skin = skin_data.get('displaySkin', {}) or {}
        
        skin_name = display_skin.get('skinName')
        series_name = display_skin.get('skinGroupName')
        
        # drawerList에서 첫 번째 일러스트레이터 가져오기
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
    
    def insert_skins(self, skins_data: Dict[str, Dict]):
        """스킨 데이터 삽입"""
        cache = CharacterIdCache(self.cursor)
        
        # 삽입할 데이터 준비
        insert_data = []
        skip_count = 0
        
        print("📋 데이터 추출 중...")
        for skin_code, skin_data in skins_data.items():
            extracted = self.extract_skin_data(skin_code, skin_data, cache)
            if extracted:
                insert_data.append(extracted)
            else:
                skip_count += 1
        
        if not insert_data:
            print("❌ 삽입할 데이터가 없습니다.")
            return
        
        # 배치 삽입
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
        
        print(f"✨ 총 {len(insert_data)}개 스킨 삽입/업데이트됨")
        if skip_count > 0:
            print(f"⚠️  {skip_count}개 스킨 스킵됨 (캐릭터 미존재)")
    
    def import_from_file(self, json_path: str):
        """JSON 파일에서 데이터 가져와 DB에 삽입"""
        try:
            # JSON 로드
            data = self.load_json(json_path)
            char_skins = data.get('charSkins', {})
            
            if not char_skins:
                print("❌ charSkins 데이터가 없습니다.")
                return
            
            # 데이터베이스 연결
            self.connect()
            
            # 트랜잭션 시작
            try:
                self.insert_skins(char_skins)
                self.connection.commit()
                print("✅ 삽입 완료!")
                
            except Exception as e:
                self.connection.rollback()
                print(f"❌ 오류 발생, 롤백됨: {e}")
                raise
            
        finally:
            self.disconnect()


def main():
    """메인 실행 함수"""
    
    # 데이터베이스 연결 설정
    DB_CONFIG = {
        "host": HOST,
        "database": DBNAME,
        "user":  USER,
        "password": PASSWORD,
        "port":  PORT
    }

    
    # JSON 파일 경로
    json_file_path = 'C:\\Users\\rugsn\\Documents\\GitHub\\Arknight-BE\\data\\skin_table.json'
    
    # 임포터 실행
    importer = SkinDataImporter(DB_CONFIG)
    
    try:
        importer.import_from_file(json_file_path)
    except Exception as e:
        print(f"🔥 작업 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()