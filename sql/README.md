# Arknights 데이터 로더 (업데이트 버전)

## 개요
이 스크립트는 Arknights 게임 데이터를 GitHub에서 다운로드하여 PostgreSQL 데이터베이스에 안전하게 삽입합니다.

## 최신 업데이트 (2026-01-06)

### 🆕 새로 추가된 기능

1. **아이템 테이블** (`item_table`)
   - 재료, 작전기록 등 게임 아이템 정보
   - 아이템 분류, 레어도, 획득 방법 등

2. **모듈 테이블** (`module_table`)
   - 캐릭터 모듈 (UniEquip) 정보
   - 모듈 타입, 설명 등

3. **소모품 테이블** (`character_consumption`)
   - 캐릭터 성장에 필요한 재료 정보
   - 정예화, 스킬 레벨업, 마스터리, 모듈 강화 재료
   - 각 단계별 필요 재료 수량

### 📊 삽입되는 데이터

#### 기존 데이터
- **range_table**: 공격 범위 메타 정보 (67개)
- **range_grid**: 공격 범위 좌표 (758개)
- **skill_table**: 스킬 메타 정보 (1,574개)
- **skill_level**: 스킬 레벨별 상세 (9,981개)
- **character**: 캐릭터 기본 정보 (1,100개)
- **character_phase**: 정예화 단계 (2,034개)
- **character_attribute**: 캐릭터 스탯 (4,143개)
- **character_skill**: 캐릭터 보유 스킬 (2,500+개)
- **character_talent**: 캐릭터 재능
- **character_potential**: 캐릭터 잠재능력
- **character_tag**: 캐릭터 태그
- **skin_table**: 스킨 정보

#### 🆕 신규 데이터
- **item_table**: 아이템 정보 (1,000+개)
- **module_table**: 모듈 정보 (400+개)
- **character_consumption**: 소모품 정보 (10,000+개)
  - 정예화 재료 (EVOLVE)
  - 스킬 공통 재료 (SKILL_COMMON)
  - 스킬 마스터리 재료 (SKILL_MASTERY)
  - 모듈 강화 재료 (MODULE)

## 주요 특징

### 1. 방어적 프로그래밍
- **예외 처리**: 모든 데이터베이스 작업과 네트워크 요청에 try-except 구문 적용
- **타입 검증**: 모든 데이터에 대해 타입 검증 및 안전한 변환
- **Null 처리**: None, 빈 문자열, 누락된 키에 대한 안전한 처리
- **외래 키 검증**: 존재하지 않는 외래 키 참조 방지
- **트랜잭션 관리**: 오류 발생 시 자동 롤백

### 2. 재시도 메커니즘
- 네트워크 오류 시 최대 3회 재시도
- 지수 백오프 적용 (2초, 4초, 6초)
- 타임아웃 설정 (30초)

### 3. 연결 풀 관리
- ThreadedConnectionPool 사용으로 효율적인 연결 관리
- Context Manager를 통한 안전한 연결 획득/반환
- 자동 연결 정리

### 4. 로깅
- 파일 및 콘솔 동시 출력
- 타임스탬프가 포함된 로그 파일 자동 생성
- 상세한 작업 진행 상황 기록
- 건너뛴 데이터에 대한 경고

### 5. 데이터 검증
- JSON 파싱 전 데이터 유효성 검증
- 외래 키 제약 조건 고려한 삽입 순서
- 중복 데이터 방지 (ON CONFLICT 처리)
- 존재하지 않는 외래 키 자동 필터링

### 6. 일괄 삽입
- execute_values를 사용한 대량 데이터 효율적 삽입
- 네트워크 왕복 횟수 최소화

## 필수 라이브러리

```bash
pip install psycopg2-binary requests --break-system-packages
```

## 사용 방법

### 1. 데이터베이스 설정 확인
스크립트 상단의 `DB_CONFIG` 딕셔너리를 본인의 환경에 맞게 수정:

```python
DB_CONFIG = {
    "host": "localhost",
    "database": "arknights_db",
    "user": "your_username",
    "password": "your_password",
    "port": "5432"
}
```

### 2. 스키마 생성
먼저 제공된 SQL 스크립트로 테이블을 생성해야 합니다:

```bash
psql -U your_username -d arknights_db -f model.sql
```

### 3. 스크립트 실행

```bash
python3 import_data.py
```

### 4. 로그 확인
실행 후 생성된 로그 파일에서 상세 정보 확인:

```bash
cat arknights_loader_20260106_*.log
```

## 데이터 삽입 순서

외래 키 제약 조건 때문에 다음 순서로 삽입됩니다:

1. **range_table** → 공격 범위 메타 정보
2. **range_grid** → 공격 범위 좌표
3. **skill_table** → 스킬 메타 정보
4. **skill_level** → 스킬 레벨별 상세
5. **character** → 캐릭터 기본 정보
6. **character_phase** → 정예화 단계
7. **character_attribute** → 캐릭터 스탯
8. **character_skill** → 캐릭터 보유 스킬
9. **character_talent** → 캐릭터 재능
10. **character_potential** → 캐릭터 잠재능력
11. **character_tag** → 캐릭터 태그
12. **skin_table** → 스킨 정보
13. **🆕 item_table** → 아이템 정보
14. **🆕 module_table** → 모듈 정보
15. **🆕 character_consumption** → 소모품 정보

## 데이터 소스

모든 데이터는 공식 Arknights 게임 데이터 저장소에서 가져옵니다:

```python
URLS = {
    "character": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../character_table.json",
    "skill": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../skill_table.json",
    "range": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../range_table.json",
    "skin": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../skin_table.json",
    "item": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../item_table.json",  # 신규
    "uniequip": "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/.../uniequip_table.json"  # 신규
}
```

## 에러 처리

### 연결 실패
```
ERROR - 데이터베이스 연결 풀 생성 실패: ...
```
→ PostgreSQL 서버 실행 여부 및 연결 정보 확인

### 데이터 다운로드 실패
```
ERROR - 최대 재시도 횟수 초과: ...
```
→ 네트워크 연결 및 URL 확인

### 외래 키 제약 위반
```
ERROR - 존재하지 않는 스킬 ID 1개 건너뜀
WARNING -   - 캐릭터 char_xxx: 스킬 skill_yyy
```
→ 정상 동작입니다. 존재하지 않는 외래 키는 자동으로 건너뜁니다.

### JSON 파싱 오류
```
ERROR - JSON 파싱 오류: ...
```
→ 다운로드한 데이터가 유효한 JSON인지 확인

## 주요 클래스 설명

### DatabaseManager
- 데이터베이스 연결 풀 관리
- Context Manager를 통한 안전한 연결 관리

### DataFetcher
- URL에서 JSON 데이터 다운로드
- 재시도 로직 및 타임아웃 처리
- 데이터 검증

### DataTransformer
- 안전한 타입 변환 유틸리티
- None/빈 값 처리
- JSON 직렬화

### DataLoader
- 실제 데이터 삽입 로직
- 일괄 삽입으로 성능 최적화
- 외래 키 검증
- 통계 수집

**🆕 새로운 메서드:**
- `load_item_data()`: 아이템 데이터 삽입
- `load_module_data()`: 모듈 데이터 삽입
- `load_consumption_data()`: 소모품 데이터 삽입

## 데이터 활용 예시

### 캐릭터의 정예화 2 재료 조회
```sql
SELECT 
    c.name AS 캐릭터명,
    i.name AS 재료명,
    cc.count AS 필요수량
FROM character_consumption cc
JOIN character c ON cc.char_id = c.char_id
JOIN item_table i ON cc.item_id = i.item_id
WHERE cc.type = 'EVOLVE' AND cc.level = 2
    AND c.char_id = 'char_002_amiya';
```

### 특정 스킬의 마스터리 3 재료 조회
```sql
SELECT 
    c.name AS 캐릭터명,
    s.skill_id AS 스킬ID,
    i.name AS 재료명,
    cc.count AS 필요수량
FROM character_consumption cc
JOIN character c ON cc.char_id = c.char_id
JOIN skill_table s ON cc.skill_id = s.skill_id
JOIN item_table i ON cc.item_id = i.item_id
WHERE cc.type = 'SKILL_MASTERY' AND cc.level = 3;
```

### 캐릭터의 모듈 정보 조회
```sql
SELECT 
    c.name AS 캐릭터명,
    m.name AS 모듈명,
    m.type_icon AS 타입,
    m.description AS 설명
FROM module_table m
JOIN character c ON m.char_id = c.char_id
WHERE c.char_id = 'char_002_amiya';
```

### 특정 재료가 필요한 캐릭터 목록
```sql
SELECT DISTINCT
    c.name AS 캐릭터명,
    cc.type AS 용도,
    cc.level AS 단계,
    cc.count AS 필요수량
FROM character_consumption cc
JOIN character c ON cc.char_id = c.char_id
WHERE cc.item_id = '30012'  -- 예: 포도당
ORDER BY c.name;
```

## 성능 최적화

1. **일괄 삽입**: `execute_values` 사용
2. **인덱스**: 자주 조회되는 컬럼에 인덱스 생성
3. **트랜잭션**: 각 테이블 그룹별로 커밋
4. **연결 풀**: 재사용 가능한 연결 유지

## 보안 고려사항

1. **비밀번호**: 프로덕션 환경에서는 환경 변수 사용 권장
   ```python
   import os
   DB_CONFIG = {
       "password": os.getenv("DB_PASSWORD")
   }
   ```

2. **SQL Injection**: 파라미터화된 쿼리 사용으로 방지

3. **로그**: 민감한 정보가 로그에 기록되지 않도록 주의

## 문제 해결

### 메모리 부족
대량 데이터 처리 시 메모리 부족이 발생하면 배치 크기 조정:

```python
# 데이터를 청크로 나누어 처리
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    execute_values(cur, query, batch)
```

### 느린 삽입 속도
1. 인덱스를 임시로 삭제 후 삽입 완료 후 재생성
2. `synchronous_commit = off` 설정 (데이터 손실 위험 있음)
3. `checkpoint_completion_target` 조정

### 외래 키 제약 위반
스크립트는 자동으로 존재하지 않는 외래 키를 건너뛰므로 대부분의 경우 문제없이 실행됩니다. 경고 로그를 확인하여 어떤 데이터가 건너뛰어졌는지 확인할 수 있습니다.

## 변경 내역

### v2.0 (2026-01-06)
- ✨ item_table 지원 추가
- ✨ module_table 지원 추가  
- ✨ character_consumption 지원 추가
- 🐛 외래 키 제약 조건 위반 문제 수정
- 🐛 존재하지 않는 skill_id 자동 필터링
- 🐛 존재하지 않는 range_id 자동 필터링
- 📝 경고 로그 추가

### v1.0 (2026-01-06)
- 🎉 초기 릴리스
- 기본 캐릭터, 스킬, 범위, 스킨 데이터 지원

## 라이센스
MIT License

## 기여
버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 참고사항

- 데이터는 한국 서버(kr) 기준입니다
- 정기적으로 업데이트되는 게임 데이터를 반영하려면 스크립트를 주기적으로 실행하세요
- 첫 실행 시 모든 데이터를 다운로드하고 삽입하므로 시간이 걸릴 수 있습니다 (약 2-5분)
