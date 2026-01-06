# 변경 사항 (CHANGELOG)

## v2.0 (2026-01-06) - 아이템 및 모듈 지원 추가

### ✨ 새로운 기능

#### 1. 아이템 테이블 지원 (`item_table`)
- **추가된 메서드**: `load_item_data()`
- **데이터 소스**: `item_table.json`
- **저장 항목**:
  - 아이템 ID, 이름, 설명
  - 분류 타입, 아이템 타입
  - 레어도, 정렬 순서
  - 아이콘 ID, 사용처, 획득 방법
- **삽입 데이터 수**: 약 1,000개 이상

#### 2. 모듈 테이블 지원 (`module_table`)
- **추가된 메서드**: `load_module_data()`
- **데이터 소스**: `uniequip_table.json`
- **저장 항목**:
  - 모듈 ID, 캐릭터 ID
  - 모듈 이름, 타입 아이콘
  - 모듈 설명, 정렬 순서
- **삽입 데이터 수**: 약 400개 이상
- **외래 키 검증**: 존재하지 않는 캐릭터 ID 자동 필터링

#### 3. 소모품 테이블 지원 (`character_consumption`)
- **추가된 메서드**: `load_consumption_data()`
- **데이터 소스**: `character_table.json`, `uniequip_table.json`
- **저장 항목**:
  - 정예화 재료 (EVOLVE): phases → evolveCost
  - 스킬 공통 재료 (SKILL_COMMON): allSkillLvlup → lvlUpCost
  - 스킬 마스터리 재료 (SKILL_MASTERY): skills → levelUpCostCond
  - 모듈 강화 재료 (MODULE): itemCost
- **삽입 데이터 수**: 약 10,000개 이상
- **외래 키 검증**: 
  - 존재하지 않는 캐릭터 ID 필터링
  - 존재하지 않는 아이템 ID 필터링
  - 존재하지 않는 스킬 ID 필터링
  - 존재하지 않는 모듈 ID 필터링

### 🔧 개선 사항

#### 외래 키 검증 강화
- **모든 외래 키 참조 사전 검증**
  ```python
  # 예: 모듈 데이터 삽입 시
  cur.execute("SELECT char_id FROM character")
  valid_char_ids = set(row[0] for row in cur.fetchall())
  
  if char_id not in valid_char_ids:
      skipped_chars.append((module_id, char_id))
      continue  # 건너뜀
  ```

#### 상세한 경고 로그
- **건너뛴 데이터 추적**
  ```
  WARNING - 존재하지 않는 아이템 ID 5개 건너뜀
  WARNING -   - 캐릭터 char_xxx (정예화): 아이템 item_yyy
  WARNING -   - 캐릭터 char_aaa (스킬): 아이템 item_bbb
  WARNING -   ... 외 3개
  ```

#### 통계 출력 확장
- 새로 추가된 테이블의 삽입 통계 포함
  ```
  item                     :   1234개
  module                   :    456개
  consumption              :  12345개
  ```

### 📝 데이터 모델 변경

#### character_consumption 테이블 구조
```sql
CREATE TABLE character_consumption (
    cons_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL,        -- 'EVOLVE', 'SKILL_COMMON', 'SKILL_MASTERY', 'MODULE'
    level INTEGER NOT NULL,           -- 단계 (정예화: 1-2, 스킬: 2-7, 마스터리: 1-3, 모듈: 1-3)
    skill_id VARCHAR(50),             -- 마스터리일 경우 스킬 ID
    item_id VARCHAR(50) NOT NULL,     -- 필요한 아이템 ID
    count INTEGER NOT NULL,           -- 필요 개수
    module_id VARCHAR(50),            -- 모듈일 경우 모듈 ID
    
    FOREIGN KEY (char_id) REFERENCES character(char_id),
    FOREIGN KEY (item_id) REFERENCES item_table(item_id),
    FOREIGN KEY (skill_id) REFERENCES skill_table(skill_id),
    FOREIGN KEY (module_id) REFERENCES module_table(module_id)
);
```

### 🗂️ 파일 구조 변경

#### import_data.py
```python
# 기존
URLS = {
    "character": "...",
    "skill": "...",
    "range": "...",
    "skin": "..."
}

# 변경 후
URLS = {
    "character": "...",
    "skill": "...",
    "range": "...",
    "skin": "...",
    "item": "...",        # 신규
    "uniequip": "..."     # 신규
}
```

#### DataLoader 클래스
```python
class DataLoader:
    def __init__(self, db_manager):
        self.stats = {
            # ... 기존 stats ...
            "item": 0,           # 신규
            "module": 0,         # 신규
            "consumption": 0     # 신규
        }
    
    # 신규 메서드
    def load_item_data(self, conn, data): ...
    def load_module_data(self, conn, data): ...
    def load_consumption_data(self, conn, character_data, module_data): ...
```

#### clear_all_tables 메서드
```python
tables = [
    'character_consumption',  # 신규 - 맨 처음 삭제
    'range_grid',
    'character_attribute',
    'character_phase',
    'character_skill',
    'skill_level',
    'character_talent',
    'character_potential',
    'character_tag',
    'skin_table',
    'module_table',           # 신규
    'skill_table',
    'character',
    'item_table',             # 신규
    'range_table'
]
```

### 🚀 실행 흐름 변경

#### 기존 흐름
```
1. range 다운로드/삽입
2. skill 다운로드/삽입
3. character 다운로드/삽입
4. skin 다운로드/삽입
5. 완료
```

#### 새로운 흐름
```
1. range 다운로드/삽입
2. skill 다운로드/삽입
3. character 다운로드/삽입
4. skin 다운로드/삽입
5. item 다운로드/삽입          ← 신규
6. module 다운로드/삽입         ← 신규
7. consumption 삽입             ← 신규 (character, module 데이터 활용)
8. 완료
```

### 📊 데이터 추출 로직

#### 정예화 재료 추출
```python
phases = char_info.get('phases', [])
for phase_idx, phase in enumerate(phases):
    evolve_cost = phase.get('evolveCost', [])
    for cost_item in evolve_cost:
        # (char_id, 'EVOLVE', phase_idx, None, item_id, count, None)
```

#### 스킬 공통 재료 추출
```python
all_skill_lvlup = char_info.get('allSkillLvlup', [])
for skill_idx, skill_costs in enumerate(all_skill_lvlup):
    lv_up_cost = skill_costs.get('lvlUpCost', [])
    for cost_item in lv_up_cost:
        # (char_id, 'SKILL_COMMON', skill_idx + 2, None, item_id, count, None)
```

#### 스킬 마스터리 재료 추출
```python
skills = char_info.get('skills', [])
for skill in skills:
    skill_id = skill.get('skillId')
    level_up_cost_cond = skill.get('levelUpCostCond', [])
    for mastery_idx, mastery_cost in enumerate(level_up_cost_cond):
        lv_up_cost = mastery_cost.get('levelUpCost', [])
        for cost_item in lv_up_cost:
            # (char_id, 'SKILL_MASTERY', mastery_idx + 1, skill_id, item_id, count, None)
```

#### 모듈 재료 추출
```python
equip_dict = module_data.get('equipDict', {})
for module_id, module_info in equip_dict.items():
    item_cost = module_info.get('itemCost', {})
    for stage_key, stage_costs in item_cost.items():
        for cost_item in stage_costs:
            # (char_id, 'MODULE', stage_num, None, item_id, count, module_id)
```

## v1.1 (2026-01-06) - 외래 키 제약 조건 위반 문제 수정

### 🐛 버그 수정

#### 문제 상황
실행 중 다음 오류 발생:
```
ERROR - character 데이터 삽입 중 오류: "character_skill" 테이블에서 자료 추가, 갱신 작업이 
"fk_char_skill_id" 참조 키(foreign key) 제약 조건을 위배했습니다
DETAIL: (skill_id)=(sktok_cdsoul) 키가 "skill_table" 테이블에 없습니다.
```

#### 원인
- 캐릭터 데이터가 참조하는 `skill_id`가 실제 `skill_table`에 존재하지 않음
- 캐릭터/스킬 데이터가 참조하는 `range_id`가 실제 `range_table`에 존재하지 않음
- 데이터 소스 간 불일치 또는 누락된 데이터

#### 해결 방법

1. **skill_id 검증 추가** (`load_character_data`)
   ```python
   cur.execute("SELECT skill_id FROM skill_table")
   valid_skill_ids = set(row[0] for row in cur.fetchall())
   
   if skill_id not in valid_skill_ids:
       skipped_skills.append((char_id, skill_id))
       continue  # 건너뜀
   ```

2. **range_id 검증 추가** (`load_skill_data`, `load_character_data`)
   ```python
   cur.execute("SELECT range_id FROM range_table")
   valid_range_ids = set(row[0] for row in cur.fetchall())
   
   if range_id and range_id not in valid_range_ids:
       skipped_ranges.append((skill_id, range_id))
       range_id = None  # NULL로 설정 (외래 키는 NULL 허용)
   ```

3. **경고 로그 추가**
   ```python
   if skipped_skills:
       logger.warning(f"존재하지 않는 스킬 ID {len(skipped_skills)}개 건너뜀")
       for char_id, skill_id in skipped_skills[:5]:
           logger.warning(f"  - 캐릭터 {char_id}: 스킬 {skill_id}")
   ```

### ✅ 개선 효과

1. **데이터 무결성 보장**: 외래 키 제약 조건 위반 방지
2. **부분 삽입 허용**: 일부 데이터에 문제가 있어도 나머지 데이터는 정상 삽입
3. **디버깅 용이**: 어떤 데이터가 건너뛰어졌는지 명확히 표시
4. **안전성 향상**: 예상치 못한 데이터 형식에도 안정적으로 동작

## v1.0 (2026-01-06) - 초기 릴리스

### 🎉 주요 기능

1. **데이터 다운로드**
   - GitHub Raw 파일에서 JSON 데이터 자동 다운로드
   - 재시도 메커니즘 (최대 3회, 지수 백오프)
   - 타임아웃 설정 (30초)

2. **데이터 삽입**
   - 방어적 프로그래밍 원칙 적용
   - 모든 작업에 예외 처리
   - 트랜잭션 관리 (오류 시 자동 롤백)
   - 일괄 삽입 (execute_values)

3. **지원 테이블**
   - range_table (공격 범위)
   - range_grid (범위 좌표)
   - skill_table (스킬 메타)
   - skill_level (스킬 레벨)
   - character (캐릭터 기본)
   - character_phase (정예화 단계)
   - character_attribute (스탯)
   - character_skill (보유 스킬)
   - character_talent (재능)
   - character_potential (잠재능력)
   - character_tag (태그)
   - skin_table (스킨)

4. **로깅**
   - 파일 및 콘솔 동시 출력
   - 타임스탬프가 포함된 로그 파일
   - 상세한 작업 진행 상황

5. **연결 관리**
   - ThreadedConnectionPool 사용
   - Context Manager를 통한 안전한 연결 관리
   - 자동 연결 정리

## 마이그레이션 가이드

### v1.x → v2.0

#### 1. 데이터베이스 스키마 업데이트
```bash
# model.sql을 다시 실행하여 새 테이블 생성
psql -U rugsn -d arknights_db -f model.sql
```

#### 2. 스크립트 업데이트
```bash
# 새 버전의 import_data.py 사용
python3 import_data.py
```

#### 3. 데이터 확인
```sql
-- 새 테이블 확인
SELECT COUNT(*) FROM item_table;
SELECT COUNT(*) FROM module_table;
SELECT COUNT(*) FROM character_consumption;
```

#### 4. 기존 애플리케이션 영향
- **하위 호환성**: 기존 테이블은 변경 없음
- **새 기능**: 아이템, 모듈, 소모품 정보 활용 가능

## 알려진 문제

### v2.0
- 일부 캐릭터의 모듈 데이터가 누락될 수 있음 (데이터 소스 이슈)
- 특수 아이템의 분류가 명확하지 않을 수 있음

### v1.x
- 일부 스킬 ID가 누락되어 건너뛰어질 수 있음 (해결됨 in v1.1)
- 범위 ID 누락 시 NULL 처리 (해결됨 in v1.1)

## 향후 계획

### v2.1 (예정)
- [ ] 스테이지 정보 테이블 추가
- [ ] 적 정보 테이블 추가
- [ ] 기지 스킬 정보 추가

### v2.2 (예정)
- [ ] 증분 업데이트 지원
- [ ] 변경 사항만 업데이트
- [ ] 버전 관리 시스템

### v3.0 (검토 중)
- [ ] REST API 서버 통합
- [ ] 실시간 데이터 동기화
- [ ] 웹 대시보드

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

### 보고할 내용
- 버전 정보
- 오류 메시지 (로그 파일 첨부)
- 재현 단계
- 예상 동작 vs 실제 동작
