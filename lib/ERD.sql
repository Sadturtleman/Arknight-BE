-- ==========================================
-- 1. 공용 함수 및 초기화
-- ==========================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- 2. 독립 마스터 테이블 (참조를 위해 최상단 배치)
-- ==========================================
CREATE TABLE profession (
    profession_id SERIAL PRIMARY KEY,
    name_ko VARCHAR(16) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sub_profession (
    sub_profession_id SERIAL PRIMARY KEY,
    name_ko VARCHAR(16) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tag (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(16) NOT NULL UNIQUE
);

CREATE TABLE items (
    item_id SERIAL PRIMARY KEY,
    item_code VARCHAR(64) NOT NULL UNIQUE,
    name_ko VARCHAR(64) NOT NULL,
    rarity SMALLINT DEFAULT 0,
    icon_id VARCHAR(128),
    item_type VARCHAR(32),
    classify_type VARCHAR(32),
    usage_text TEXT,
    description TEXT,
    obtain_approach TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ranges (
    range_id VARCHAR(32) PRIMARY KEY,
    grids JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE zones (
    zone_id SERIAL PRIMARY KEY,
    zone_code VARCHAR(64) NOT NULL UNIQUE,
    name_ko VARCHAR(64) NOT NULL,
    zone_type VARCHAR(20),
    zone_index INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 3. 메인 캐릭터 및 관련 테이블
-- ==========================================
CREATE TABLE characters (
    character_id SERIAL PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,
    name_ko VARCHAR(64) NOT NULL,
    class_description VARCHAR(255),
    rarity SMALLINT CHECK (rarity BETWEEN 1 AND 6),
    profession_id INT REFERENCES profession(profession_id),
    sub_profession_id INT REFERENCES sub_profession(sub_profession_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE characters_detail (
    character_id INT PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    item_usage TEXT,
    item_desc TEXT
);

CREATE TABLE character_stats (
    character_stat_id SERIAL PRIMARY KEY,
    character_id INT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 0 AND 2),
    max_level SMALLINT NOT NULL CHECK (max_level BETWEEN 0 AND 90),
    range_id VARCHAR(32) REFERENCES ranges(range_id), -- 사거리 연결
    base_hp INT NOT NULL, base_atk INT NOT NULL, base_def INT NOT NULL,
    max_hp INT NOT NULL, max_atk INT NOT NULL, max_def INT NOT NULL,
    magic_resistance SMALLINT NOT NULL,
    cost SMALLINT NOT NULL,
    block_cnt SMALLINT NOT NULL,
    attack_speed SMALLINT NOT NULL,
    UNIQUE (character_id, phase)
);

CREATE TABLE character_skill (
    character_id INT PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    phase_0_code VARCHAR(32),
    phase_1_code VARCHAR(32),
    phase_2_code VARCHAR(32)
);

-- ==========================================
-- 4. 성장 및 스탯 보너스 테이블
-- ==========================================
CREATE TABLE character_favor_templates (
    character_id INT PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    max_favor_level SMALLINT NOT NULL DEFAULT 50,
    bonus_hp INT DEFAULT 0,
    bonus_atk INT DEFAULT 0,
    bonus_def INT DEFAULT 0,
    extra_bonuses JSONB
);

CREATE TABLE character_talents (
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    talent_index SMALLINT NOT NULL,
    candidate_index SMALLINT NOT NULL,
    unlock_phase SMALLINT NOT NULL,
    unlock_level SMALLINT NOT NULL,
    required_potential SMALLINT NOT NULL,
    range_id VARCHAR(32) REFERENCES ranges(range_id), -- 재능 범위 추가
    name VARCHAR(64) NOT NULL,
    description TEXT,
    blackboard JSONB
);

-- ==========================================
-- 5. 스킬 및 모듈 테이블
-- ==========================================
CREATE TABLE skills (
    skill_id SERIAL PRIMARY KEY,
    skill_code VARCHAR(64) NOT NULL UNIQUE,
    name_ko VARCHAR(64) NOT NULL,
    icon_id VARCHAR(128),
    skill_type SMALLINT,
    sp_type SMALLINT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skill_levels (
    id SERIAL PRIMARY KEY,
    skill_id INT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    level SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 10),
    sp_cost SMALLINT NOT NULL,
    initial_sp SMALLINT DEFAULT 0,
    duration NUMERIC(5,2) DEFAULT 0,
    range_id VARCHAR(32) REFERENCES ranges(range_id), -- 스킬 사거리 추가
    description TEXT,
    blackboard JSONB,
    UNIQUE (skill_id, level)
);

CREATE TABLE character_modules (
    module_id SERIAL PRIMARY KEY,
    module_code VARCHAR(64) NOT NULL UNIQUE,
    character_id INT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    name_ko VARCHAR(64) NOT NULL,
    icon_id VARCHAR(128),
    description TEXT
);

-- ==========================================
-- 6. 비용 및 맵 데이터 테이블
-- ==========================================
CREATE TABLE character_promotion_costs (
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    target_phase SMALLINT NOT NULL,
    item_id INT NOT NULL REFERENCES items(item_id),
    count INT NOT NULL
);

CREATE TABLE character_module_costs (
    id SERIAL PRIMARY KEY,
    module_id INT NOT NULL REFERENCES character_modules(module_id) ON DELETE CASCADE,
    level SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 3),
    item_id INT NOT NULL REFERENCES items(item_id), -- item_id로 참조 통일
    count INT NOT NULL
);

CREATE TABLE stages (
    stage_id SERIAL PRIMARY KEY,
    stage_code VARCHAR(64) NOT NULL UNIQUE,
    zone_id INT NOT NULL REFERENCES zones(zone_id) ON DELETE CASCADE,
    display_code VARCHAR(16) NOT NULL,
    name_ko VARCHAR(64) NOT NULL,
    description TEXT,
    ap_cost SMALLINT DEFAULT 0,
    danger_level VARCHAR(32)
);

-- ==========================================
-- 7. 중간 테이블 및 인덱스
-- ==========================================
CREATE TABLE character_tag (
    tag_id INT NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
    character_id INT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    PRIMARY KEY (character_id, tag_id),
    UNIQUE (tag_id, character_id)
);

-- 인덱스 설정
CREATE INDEX idx_characters_name_ko ON characters(name_ko);
CREATE INDEX idx_talent_lookup ON character_talents (character_id, unlock_phase, required_potential);
CREATE INDEX idx_skill_levels_lookup ON skill_levels(skill_id, level);
CREATE INDEX idx_items_code ON items(item_code);

-- 트리거 설정
CREATE TRIGGER trg_characters_updated_at
BEFORE UPDATE ON characters
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();