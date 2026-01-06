# 빠른 시작 가이드

## 1단계: 환경 준비

### PostgreSQL 설치 확인
```bash
psql --version
```

### Python 라이브러리 설치
```bash
pip install psycopg2-binary requests --break-system-packages
```

## 2단계: 데이터베이스 생성

```bash
# PostgreSQL에 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE arknights_db;

# 사용자 권한 부여 (필요한 경우)
GRANT ALL PRIVILEGES ON DATABASE arknights_db TO rugsn;

# 종료
\q
```

## 3단계: 스키마 생성

```bash
psql -U rugsn -d arknights_db -f model.sql
```

성공하면 다음과 같은 메시지가 표시됩니다:
```
CREATE SCHEMA
SET
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
...
```

## 4단계: 설정 파일 수정

`import_data.py` 파일을 열어 데이터베이스 설정을 수정하세요:

```python
DB_CONFIG = {
    "host": "localhost",
    "database": "arknights_db",
    "user": "rugsn",           # 본인의 사용자명
    "password": "your_password",  # 본인의 비밀번호
    "port": "5432"
}
```

## 5단계: 스크립트 실행

```bash
python3 import_data.py
```

### 예상 출력

```
==================================================
Arknights 데이터 로더 시작
==================================================
데이터베이스 연결 중...
데이터베이스 연결 풀 생성 완료
데이터 다운로드 중...
데이터 다운로드 시도 (1/3): https://raw.githubusercontent.com/...
데이터 다운로드 성공: ... (크기: 48083 bytes)
...
range 데이터 검증 성공 (항목 수: 67)
skill 데이터 검증 성공 (항목 수: 1574)
character 데이터 검증 성공 (항목 수: 1100)
skin 데이터 검증 성공 (항목 수: 7)
item 데이터 검증 성공 (항목 수: 1000+)
uniequip 데이터 검증 성공 (항목 수: 400+)
기존 데이터 삭제 중...
...
==================================================
데이터 삽입 통계
==================================================
range                    :     67개
skill                    :   1574개
character                :   1100개
range_grid               :    758개
character_phase          :   2034개
character_attribute      :   4143개
character_skill          :   2500+개
skill_level              :   9981개
character_talent         :   XXXX개
character_potential      :   XXXX개
character_tag            :   XXXX개
skin                     :    XXX개
item                     :   1000+개
module                   :    400+개
consumption              :  10000+개
==================================================
전체 작업 완료! (소요 시간: XX.XX초)
==================================================
```

## 6단계: 데이터 확인

```bash
psql -U rugsn -d arknights_db
```

### 기본 확인 쿼리

```sql
-- 캐릭터 수 확인
SELECT COUNT(*) FROM character;

-- 아이템 수 확인
SELECT COUNT(*) FROM item_table;

-- 모듈 수 확인
SELECT COUNT(*) FROM module_table;

-- 소모품 정보 수 확인
SELECT COUNT(*) FROM character_consumption;

-- 특정 캐릭터의 정보 조회
SELECT * FROM character WHERE name LIKE '%아미야%';

-- 특정 캐릭터의 정예화 재료 조회
SELECT 
    c.name AS 캐릭터명,
    cc.type AS 용도,
    cc.level AS 단계,
    i.name AS 재료명,
    cc.count AS 수량
FROM character_consumption cc
JOIN character c ON cc.char_id = c.char_id
JOIN item_table i ON cc.item_id = i.item_id
WHERE c.name LIKE '%아미야%' AND cc.type = 'EVOLVE'
ORDER BY cc.level;
```

## 문제 해결

### 문제 1: 연결 실패

**오류:**
```
ERROR - 데이터베이스 연결 풀 생성 실패: could not connect to server
```

**해결:**
1. PostgreSQL 서버가 실행 중인지 확인:
   ```bash
   sudo systemctl status postgresql
   # 또는
   pg_ctl status
   ```

2. 실행되지 않았다면 시작:
   ```bash
   sudo systemctl start postgresql
   # 또는
   pg_ctl start
   ```

### 문제 2: 권한 오류

**오류:**
```
ERROR - permission denied for database arknights_db
```

**해결:**
```sql
-- postgres 사용자로 접속
psql -U postgres

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE arknights_db TO rugsn;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rugsn;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rugsn;
```

### 문제 3: 테이블이 없음

**오류:**
```
ERROR - relation "character" does not exist
```

**해결:**
스키마를 먼저 생성하세요:
```bash
psql -U rugsn -d arknights_db -f model.sql
```

### 문제 4: 네트워크 오류

**오류:**
```
ERROR - 최대 재시도 횟수 초과: https://raw.githubusercontent.com/...
```

**해결:**
1. 인터넷 연결 확인
2. GitHub 접속 가능 여부 확인
3. 방화벽 설정 확인

### 문제 5: 이미 데이터가 있음

데이터를 다시 삽입하고 싶다면:

**옵션 1: 스크립트 실행 (자동 삭제)**
```bash
python3 import_data.py
```
스크립트는 기본적으로 기존 데이터를 삭제하고 새로 삽입합니다.

**옵션 2: 수동 삭제**
```sql
-- 모든 데이터 삭제
TRUNCATE TABLE character_consumption CASCADE;
TRUNCATE TABLE range_grid CASCADE;
TRUNCATE TABLE character_attribute CASCADE;
TRUNCATE TABLE character_phase CASCADE;
TRUNCATE TABLE character_skill CASCADE;
TRUNCATE TABLE skill_level CASCADE;
TRUNCATE TABLE character_talent CASCADE;
TRUNCATE TABLE character_potential CASCADE;
TRUNCATE TABLE character_tag CASCADE;
TRUNCATE TABLE skin_table CASCADE;
TRUNCATE TABLE module_table CASCADE;
TRUNCATE TABLE skill_table CASCADE;
TRUNCATE TABLE character CASCADE;
TRUNCATE TABLE item_table CASCADE;
TRUNCATE TABLE range_table CASCADE;
```

## 다음 단계

데이터 삽입이 완료되었습니다! 이제:

1. **API 서버 개발**: 이 데이터를 활용하는 REST API 서버를 개발하세요
2. **앱 개발**: Jetpack Compose로 Android 앱을 개발하세요
3. **데이터 분석**: SQL 쿼리로 다양한 통계를 추출하세요

### 유용한 쿼리 예제

```sql
-- 1. 레어도별 캐릭터 수
SELECT rarity, COUNT(*) as 캐릭터수
FROM character
GROUP BY rarity
ORDER BY rarity;

-- 2. 직업별 캐릭터 수
SELECT profession, COUNT(*) as 캐릭터수
FROM character
GROUP BY profession
ORDER BY 캐릭터수 DESC;

-- 3. 가장 많이 필요한 재료 TOP 10
SELECT 
    i.name AS 재료명,
    SUM(cc.count) AS 총필요수량,
    COUNT(DISTINCT cc.char_id) AS 사용캐릭터수
FROM character_consumption cc
JOIN item_table i ON cc.item_id = i.item_id
GROUP BY i.item_id, i.name
ORDER BY 총필요수량 DESC
LIMIT 10;

-- 4. 특정 캐릭터의 완전한 성장 재료
SELECT 
    cc.type AS 용도,
    cc.level AS 단계,
    i.name AS 재료명,
    i.rarity AS 레어도,
    cc.count AS 수량
FROM character_consumption cc
JOIN character c ON cc.char_id = c.char_id
JOIN item_table i ON cc.item_id = i.item_id
WHERE c.name LIKE '%아미야%'
ORDER BY 
    CASE cc.type
        WHEN 'EVOLVE' THEN 1
        WHEN 'SKILL_COMMON' THEN 2
        WHEN 'SKILL_MASTERY' THEN 3
        WHEN 'MODULE' THEN 4
    END,
    cc.level;

-- 5. 모듈이 있는 캐릭터 목록
SELECT DISTINCT
    c.name AS 캐릭터명,
    c.profession AS 직업,
    COUNT(m.module_id) AS 모듈수
FROM character c
JOIN module_table m ON c.char_id = m.char_id
GROUP BY c.char_id, c.name, c.profession
ORDER BY 모듈수 DESC, c.name;
```

## 주기적 업데이트

게임 데이터가 업데이트되면:

```bash
# 스크립트를 다시 실행하면 자동으로 최신 데이터로 업데이트됩니다
python3 import_data.py
```

## 도움말

추가 도움이 필요하면:
- README.md 참조
- CHANGELOG.md에서 변경 사항 확인
- 로그 파일 확인: `arknights_loader_*.log`
