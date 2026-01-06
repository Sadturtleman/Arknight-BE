-- 0. Schema Setup
CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Optional: pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1-1. Range Table
CREATE TABLE range_table (
    range_id VARCHAR(50) PRIMARY KEY,
    direction INTEGER DEFAULT 1
);

-- 1-2. Skill Table
CREATE TABLE skill_table (
    skill_id VARCHAR(50) PRIMARY KEY,
    icon_id VARCHAR(50),
    hidden BOOLEAN DEFAULT FALSE
);

-- 1-3. Character Table
CREATE TABLE character (
    char_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    appellation VARCHAR(100),
    description TEXT,
    rarity VARCHAR(20),
    profession VARCHAR(20),
    sub_profession_id VARCHAR(50),
    position VARCHAR(20),
    nation_id VARCHAR(50),
    group_id VARCHAR(50),
    team_id VARCHAR(50),
    display_number VARCHAR(50),
    is_sp_char BOOLEAN DEFAULT FALSE
);

-- 2-1. Range Grid
CREATE TABLE range_grid (
    grid_id SERIAL PRIMARY KEY,
    range_id VARCHAR(50) NOT NULL,
    row_val INTEGER NOT NULL,
    col_val INTEGER NOT NULL,
    CONSTRAINT fk_range_main FOREIGN KEY (range_id) REFERENCES range_table(range_id) ON DELETE CASCADE
);
CREATE INDEX idx_range_grid_id ON range_grid(range_id);

-- 2-2. Character Phase
CREATE TABLE character_phase (
    phase_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    phase_index INTEGER NOT NULL,
    max_level INTEGER NOT NULL,
    range_id VARCHAR(50),
    CONSTRAINT fk_char_phase FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE,
    CONSTRAINT fk_phase_range FOREIGN KEY (range_id) REFERENCES range_table(range_id),
    CONSTRAINT uq_char_phase UNIQUE (char_id, phase_index)
);

-- 2-3. Character Attribute
CREATE TABLE character_attribute (
    attr_id SERIAL PRIMARY KEY,
    phase_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    max_hp INTEGER,
    atk INTEGER,
    def INTEGER,
    magic_resistance NUMERIC(5, 2),
    cost INTEGER,
    block_cnt INTEGER,
    move_speed NUMERIC(4, 2),
    attack_speed NUMERIC(5, 2),
    base_attack_time NUMERIC(4, 2),
    respawn_time INTEGER,
    CONSTRAINT fk_phase_attr FOREIGN KEY (phase_id) REFERENCES character_phase(phase_id) ON DELETE CASCADE
);
CREATE INDEX idx_char_attr_phase_lvl ON character_attribute(phase_id, level);

-- 2-4. Character Skill Relation
CREATE TABLE character_skill (
    record_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    skill_id VARCHAR(50) NOT NULL,
    unlock_phase INTEGER,
    unlock_level INTEGER,
    CONSTRAINT fk_char_skill_char FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE,
    CONSTRAINT fk_char_skill_id FOREIGN KEY (skill_id) REFERENCES skill_table(skill_id) ON DELETE CASCADE
);

-- 2-5. Skill Level Detail
CREATE TABLE skill_level (
    level_id SERIAL PRIMARY KEY,
    skill_id VARCHAR(50) NOT NULL,
    level_index INTEGER NOT NULL,
    name VARCHAR(100),
    range_id VARCHAR(50),
    description TEXT,
    sp_type INTEGER,
    sp_cost INTEGER,
    init_sp INTEGER,
    duration NUMERIC(10, 2),
    blackboard JSONB,
    CONSTRAINT fk_skill_level_main FOREIGN KEY (skill_id) REFERENCES skill_table(skill_id) ON DELETE CASCADE,
    CONSTRAINT fk_skill_level_range FOREIGN KEY (range_id) REFERENCES range_table(range_id)
);
CREATE INDEX idx_skill_level_sid ON skill_level(skill_id);
CREATE INDEX idx_skill_blackboard ON skill_level USING GIN (blackboard);

-- 2-6. Character Talent
CREATE TABLE character_talent (
    talent_record_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    talent_index INTEGER,
    name VARCHAR(100),
    description TEXT,
    unlock_phase INTEGER,
    unlock_level INTEGER,
    required_potential INTEGER,
    CONSTRAINT fk_char_talent FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE
);

-- 2-7. Character Potential
CREATE TABLE character_potential (
    pot_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    rank_index INTEGER NOT NULL,
    type VARCHAR(20),
    description TEXT,
    CONSTRAINT fk_char_potential FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE
);

-- 2-8. Character Tag
CREATE TABLE character_tag (
    tag_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    tag_name VARCHAR(50),
    CONSTRAINT fk_char_tag FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE
);

-- 2-9. Skin Table
CREATE TABLE skin_table (
    skin_id VARCHAR(100) PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    name VARCHAR(100),
    description TEXT,
    group_name VARCHAR(50),
    illust_id VARCHAR(100),
    avatar_id VARCHAR(100),
    portrait_id VARCHAR(100),
    model_id VARCHAR(100),
    drawer_list TEXT[],
    CONSTRAINT fk_skin_char FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE
);
CREATE INDEX idx_skin_char_id ON skin_table(char_id);
CREATE INDEX idx_skin_drawer ON skin_table USING GIN (drawer_list);

-- 4. Item Table
CREATE TABLE item_table (
    item_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    usage TEXT,
    obtain_approach TEXT,
    classify_type VARCHAR(50),
    item_type VARCHAR(50),
    rarity INTEGER,
    sort_id INTEGER,
    icon_id VARCHAR(100)
);
CREATE INDEX idx_item_name ON item_table(name);
CREATE INDEX idx_item_classify ON item_table(classify_type);

-- 5. Module Table
CREATE TABLE module_table (
    module_id VARCHAR(50) PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    name VARCHAR(100),
    type_icon VARCHAR(50),
    description TEXT,
    sort_id INTEGER,
    CONSTRAINT fk_module_char FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE
);

-- 6. Consumption Table
CREATE TABLE character_consumption (
    cons_id SERIAL PRIMARY KEY,
    char_id VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL,
    level INTEGER NOT NULL,
    skill_id VARCHAR(50),
    module_id VARCHAR(50),
    item_id VARCHAR(50) NOT NULL,
    count INTEGER NOT NULL,
    CONSTRAINT fk_cons_char FOREIGN KEY (char_id) REFERENCES character(char_id) ON DELETE CASCADE,
    CONSTRAINT fk_cons_item FOREIGN KEY (item_id) REFERENCES item_table(item_id) ON DELETE CASCADE,
    CONSTRAINT fk_cons_skill FOREIGN KEY (skill_id) REFERENCES skill_table(skill_id) ON DELETE CASCADE,
    CONSTRAINT fk_cons_module FOREIGN KEY (module_id) REFERENCES module_table(module_id) ON DELETE CASCADE
);
CREATE INDEX idx_cons_char_type ON character_consumption(char_id, type);

-- 7. Global Indexes
CREATE INDEX idx_character_rarity ON character(rarity);
CREATE INDEX idx_character_profession ON character(profession);
CREATE INDEX idx_character_name ON character(name);