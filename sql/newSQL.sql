-- [1. Core Reference Table]
-- 공격/스킬 범위 데이터 (JSON의 range_table 매핑)
-- 다른 테이블에서 참조하므로 가장 먼저 생성해야 함
CREATE TABLE ranges (
    range_id         VARCHAR(50) PRIMARY KEY,  -- JSON의 "id"
    grids            JSONB NOT NULL,           -- JSON의 "grids": [{"row": 1, "col": 0}, ...]
    
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- [2. Operator Master Table]
-- character_table.json 매핑
CREATE TABLE operators (
    operator_id      VARCHAR(50) PRIMARY KEY, -- "char_002_amiya"
    name_ko          VARCHAR(100) NOT NULL,
    name_en          VARCHAR(100),            -- "appellation"
    app_index        VARCHAR(20),             -- 도감 번호 (B001 등 String일 수 있음)
    
    -- 분류 정보
    rarity           SMALLINT NOT NULL,       -- "rarity" (0~5 -> 실제 1~6성)
    profession       VARCHAR(20) NOT NULL,    -- "profession" (WARRIOR, SNIPER...)
    sub_profession   VARCHAR(50),             -- "subProfessionId" (archetype)
    position         VARCHAR(20),             -- "position" (MELEE, RANGED)
    team_id          VARCHAR(50),             -- "groupId" (진영/팀 정보)
    
    -- 속성 및 플래그
    is_sp_char       BOOLEAN DEFAULT FALSE,
    can_use_default  BOOLEAN DEFAULT TRUE,    -- 일반 작전 사용 가능 여부
    description      TEXT,                    -- "itemUsage"
    
    -- 관계형 링크
    range_id         VARCHAR(50),             -- 기본 공격 범위
    
    -- [JSONB 최적화] 복잡한 스탯 데이터
    -- 1. phases_data: 정예화 재료 및 단계별 해금 정보
    -- 2. talents_data: 재능 목록 ("talents")
    -- 3. potential_data: 잠재 능력 효과 ("potentialItemId" 및 상세 수치)
    -- 4. trust_data: 신뢰도 보너스 ("favorKeyFrames")
    phases_data      JSONB, 
    talents_data     JSONB,
    potential_data   JSONB,
    trust_data       JSONB,
    
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (range_id) REFERENCES ranges(range_id)
);

-- 인덱스 최적화: 필터링 및 정렬 빈도가 높은 컬럼
CREATE INDEX idx_ops_filter ON operators (rarity DESC, profession, sub_profession);
CREATE INDEX idx_ops_team ON operators (team_id);


-- [3. Operator Growth Stats]
-- character_table의 레벨별 스탯 보간용 데이터
CREATE TABLE operator_stats (
    operator_id   VARCHAR(50) NOT NULL,
    phase         SMALLINT NOT NULL, -- 0, 1, 2
    
    max_level     SMALLINT NOT NULL, 
    
    -- Base Stats (Level 1)
    base_hp       INT NOT NULL,
    base_atk      INT NOT NULL,
    base_def      INT NOT NULL,
    base_res      DECIMAL(5, 1) DEFAULT 0,
    
    -- Max Stats (Max Level)
    max_hp        INT NOT NULL,
    max_atk       INT NOT NULL,
    max_def       INT NOT NULL,
    max_res       DECIMAL(5, 1) DEFAULT 0,
    
    -- Fixed Stats per Phase
    cost          SMALLINT NOT NULL,
    block_cnt     SMALLINT NOT NULL,
    attack_speed  SMALLINT NOT NULL,
    respawn_time  SMALLINT NOT NULL,
    
    -- 정예화 시 변경되는 범위
    range_id      VARCHAR(50),
    
    PRIMARY KEY (operator_id, phase),
    FOREIGN KEY (operator_id) REFERENCES operators(operator_id) ON DELETE CASCADE,
    FOREIGN KEY (range_id) REFERENCES ranges(range_id)
);

-- [4. Skills]
-- skill_table.json 매핑
CREATE TABLE skills (
    skill_id          VARCHAR(50) PRIMARY KEY,
    icon_id           VARCHAR(50),
    name_ko           VARCHAR(100) NOT NULL,
    
    -- 스킬 메커니즘 분류
    sp_type           VARCHAR(20) NOT NULL,   -- AUTO, OFFENSIVE...
    duration_type     VARCHAR(20) NOT NULL,
    
    -- levels 1~10 데이터 (blackboard 포함)
    levels_data       JSONB NOT NULL,
    
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_skills_lookup ON skills (sp_type);

-- [5. Operator-Skill Relation]
-- character_table의 "skills" 리스트 매핑
CREATE TABLE operator_skills (
    operator_id       VARCHAR(50),
    skill_id          VARCHAR(50),
    
    skill_index       SMALLINT NOT NULL, -- 0, 1, 2 (JSON 인덱스)
    unlock_phase      SMALLINT NOT NULL, -- 해금 정예화 단계
    
    PRIMARY KEY (operator_id, skill_id),
    FOREIGN KEY (operator_id) REFERENCES operators(operator_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- [6. Items]
-- item_table.json 매핑
CREATE TABLE items (
    item_id          VARCHAR(50) PRIMARY KEY,
    name_ko          VARCHAR(100) NOT NULL,
    description      TEXT,
    
    rarity           SMALLINT NOT NULL,       -- "rarity"
    item_type        VARCHAR(30) NOT NULL,    -- "classifyType"
    sort_id          INT NOT NULL,            -- "sortId"
    
    icon_id          VARCHAR(100),
    stack_limit      INT DEFAULT 99,
    obtain_approach  TEXT,
    
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_items_sort ON items (item_type, sort_id);

-- [7. Crafting & Workshop]
-- building_data.json 또는 수동 데이터 매핑
CREATE TABLE workshop_formulas (
    target_item_id   VARCHAR(50) PRIMARY KEY,
    
    gold_cost        INT DEFAULT 0,
    yield_prob       DECIMAL(3, 2) DEFAULT 1.0,
    ingredients      JSONB NOT NULL,          -- [{"id": "...", "count": 1}]
    unlock_cond      VARCHAR(50),
    
    FOREIGN KEY (target_item_id) REFERENCES items(item_id)
);

-- [8. Consumption / Recipe]
-- 캐릭터 육성 재료 (Operator <-> Item N:M)
CREATE TABLE operator_consumptions (
    id               BIGSERIAL PRIMARY KEY,
    operator_id      VARCHAR(50) NOT NULL,
    
    cost_type        VARCHAR(20) NOT NULL, -- ELITE, SKILL, MASTERY, MODULE
    reference_id     VARCHAR(50),          -- skill_id or module_id
    level            SMALLINT NOT NULL,
    
    ingredients      JSONB NOT NULL DEFAULT '[]',
    
    FOREIGN KEY (operator_id) REFERENCES operators(operator_id) ON DELETE CASCADE
);
CREATE INDEX idx_costs_lookup ON operator_consumptions (operator_id, cost_type);

-- [9. Modules]
-- uniequip_table.json 매핑
-- 1. 전역 설정을 위한 테이블 (필요시)
CREATE TABLE modules (
    module_id       VARCHAR(50) PRIMARY KEY, -- 원본 데이터 ID 유지 (Join 편의성)
    operator_id     VARCHAR(50) NOT NULL,
    
    -- 기본 메타데이터
    icon_id         VARCHAR(100),
    type_icon_id    VARCHAR(50), 
    sort_id         INT DEFAULT 0,
    
    -- 텍스트 데이터 (JSONB로 통합 관리하여 유연성 확보)
    -- 구조: {"ko": {"name": "...", "desc": "..."}, "en": {...}}
    display_text    JSONB NOT NULL, 
    
    -- 조건 및 데이터
    unlock_cond     JSONB, 
    -- levels_data는 데이터 양이 많으므로 별도 테이블 분리 혹은 TOAST 최적화 고려
    levels_data     JSONB NOT NULL, 
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 성능 향상을 위한 인덱스 설계
CREATE INDEX idx_modules_operator_id ON modules(operator_id);
-- JSONB 내부의 특정 필드 검색이 잦을 경우 GIN 인덱스 활용
CREATE INDEX idx_modules_display_text ON modules USING GIN (display_text);
-- [10. Zones & Stages]
-- stage_table.json 매핑
CREATE TABLE zones (
    zone_id          VARCHAR(50) PRIMARY KEY,
    name_ko          VARCHAR(100) NOT NULL,
    type             VARCHAR(20) NOT NULL,    -- "zoneType"
    
    start_time       TIMESTAMP,
    end_time         TIMESTAMP,
    zone_index       INT NOT NULL
);

CREATE TABLE stages (
    stage_id         VARCHAR(50) PRIMARY KEY,
    zone_id          VARCHAR(50) NOT NULL,
    
    code             VARCHAR(20) NOT NULL,
    name_ko          VARCHAR(100),
    description      TEXT,
    
    stage_type       VARCHAR(20) NOT NULL,    -- "stageType"
    ap_cost          SMALLINT NOT NULL,       -- "apCost"
    rec_level        VARCHAR(50),
    hazard_type      VARCHAR(20),             -- "dangerLevel"
    
    hard_stage_id    VARCHAR(50),
    
    drops_data       JSONB NOT NULL DEFAULT '{}', -- "stageDropInfo"
    
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
);
CREATE INDEX idx_stages_find ON stages (code);
CREATE INDEX idx_stages_drop_search ON stages USING GIN (drops_data);

-- [11. Skins]
-- skin_table.json 매핑
CREATE TABLE skin_brands (
    brand_id         VARCHAR(50) PRIMARY KEY, -- "displaySkin.brandId"
    name_ko          VARCHAR(100) NOT NULL,
    sort_id          INT NOT NULL,
    logo_id          VARCHAR(100),
    description      TEXT
);

CREATE TABLE skins (
    skin_id          VARCHAR(100) PRIMARY KEY,
    operator_id      VARCHAR(50) NOT NULL,
    brand_id         VARCHAR(50),
    
    name_ko          VARCHAR(100),
    illustrator      VARCHAR(50),
    
    category         VARCHAR(20) NOT NULL,
    is_dynamic       BOOLEAN DEFAULT FALSE,
    cost             SMALLINT DEFAULT 0,
    
    display_data     JSONB NOT NULL,          -- avatar, portrait 등 파일명
    
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (operator_id) REFERENCES operators(operator_id) ON DELETE CASCADE,
    FOREIGN KEY (brand_id) REFERENCES skin_brands(brand_id)
);