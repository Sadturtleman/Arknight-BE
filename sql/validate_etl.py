#!/usr/bin/env python3
"""
ETL 결과 검증 스크립트
- 데이터 무결성 검증
- 통계 확인
- 이상 데이터 탐지
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검증 결과"""
    table: str
    check: str
    passed: bool
    message: str
    details: str = ""


class ETLValidator:
    """ETL 결과 검증"""
    
    def __init__(self, conn_params: Dict):
        self.conn_params = conn_params
        self.results: List[ValidationResult] = []
    
    def connect(self):
        """데이터베이스 연결"""
        return psycopg2.connect(**self.conn_params)
    
    def check_table_count(self, conn, table: str, expected_min: int = 0) -> ValidationResult:
        """테이블 레코드 수 확인"""
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                
                passed = count >= expected_min
                message = f"{table}: {count:,} records"
                
                if not passed:
                    message += f" (expected >= {expected_min})"
                
                return ValidationResult(table, "row_count", passed, message)
        except Exception as e:
            return ValidationResult(table, "row_count", False, str(e))
    
    def check_foreign_keys(self, conn) -> List[ValidationResult]:
        """외래키 무결성 검증"""
        checks = [
            # operators -> ranges
            """
            SELECT COUNT(*) 
            FROM operators o 
            LEFT JOIN ranges r ON o.range_id = r.range_id 
            WHERE o.range_id IS NOT NULL AND r.range_id IS NULL
            """,
            # operator_stats -> operators
            """
            SELECT COUNT(*) 
            FROM operator_stats os 
            LEFT JOIN operators o ON os.operator_id = o.operator_id 
            WHERE o.operator_id IS NULL
            """,
            # operator_skills -> operators
            """
            SELECT COUNT(*) 
            FROM operator_skills os 
            LEFT JOIN operators o ON os.operator_id = o.operator_id 
            WHERE o.operator_id IS NULL
            """,
            # operator_skills -> skills
            """
            SELECT COUNT(*) 
            FROM operator_skills os 
            LEFT JOIN skills s ON os.skill_id = s.skill_id 
            WHERE s.skill_id IS NULL
            """,
            # modules -> operators
            """
            SELECT COUNT(*) 
            FROM modules m 
            LEFT JOIN operators o ON m.operator_id = o.operator_id 
            WHERE o.operator_id IS NULL
            """,
            # stages -> zones
            """
            SELECT COUNT(*) 
            FROM stages s 
            LEFT JOIN zones z ON s.zone_id = z.zone_id 
            WHERE z.zone_id IS NULL
            """,
            # skins -> operators
            """
            SELECT COUNT(*) 
            FROM skins s 
            LEFT JOIN operators o ON s.operator_id = o.operator_id 
            WHERE o.operator_id IS NULL
            """
        ]
        
        results = []
        check_names = [
            "operators.range_id -> ranges",
            "operator_stats.operator_id -> operators",
            "operator_skills.operator_id -> operators",
            "operator_skills.skill_id -> skills",
            "modules.operator_id -> operators",
            "stages.zone_id -> zones",
            "skins.operator_id -> operators"
        ]
        
        try:
            with conn.cursor() as cur:
                for check_sql, check_name in zip(checks, check_names):
                    cur.execute(check_sql)
                    orphan_count = cur.fetchone()[0]
                    
                    passed = orphan_count == 0
                    message = f"FK Check: {check_name}"
                    if not passed:
                        message += f" - Found {orphan_count} orphaned records"
                    
                    results.append(ValidationResult(
                        "foreign_keys", check_name, passed, message
                    ))
        except Exception as e:
            results.append(ValidationResult(
                "foreign_keys", "error", False, f"FK check failed: {e}"
            ))
        
        return results
    
    def check_data_ranges(self, conn) -> List[ValidationResult]:
        """데이터 범위 검증 (레어도, 레벨 등)"""
        checks = [
            ("operators", "rarity", 0, 5),
            ("operator_stats", "phase", 0, 2),
            ("operator_stats", "max_level", 1, 90),
            ("items", "rarity", 0, 5),
        ]
        
        results = []
        
        try:
            with conn.cursor() as cur:
                for table, column, min_val, max_val in checks:
                    cur.execute(f"""
                        SELECT COUNT(*) 
                        FROM {table} 
                        WHERE {column} < {min_val} OR {column} > {max_val}
                    """)
                    invalid_count = cur.fetchone()[0]
                    
                    passed = invalid_count == 0
                    message = f"{table}.{column} in range [{min_val}, {max_val}]"
                    if not passed:
                        message += f" - {invalid_count} out of range"
                    
                    results.append(ValidationResult(
                        table, f"{column}_range", passed, message
                    ))
        except Exception as e:
            results.append(ValidationResult(
                "data_ranges", "error", False, f"Range check failed: {e}"
            ))
        
        return results
    
    def check_jsonb_fields(self, conn) -> List[ValidationResult]:
        """JSONB 필드 검증"""
        checks = [
            ("operators", "phases_data"),
            ("operators", "talents_data"),
            ("skills", "levels_data"),
            ("modules", "levels_data"),
        ]
        
        results = []
        
        try:
            with conn.cursor() as cur:
                for table, column in checks:
                    # NULL 체크
                    cur.execute(f"""
                        SELECT COUNT(*) 
                        FROM {table} 
                        WHERE {column} IS NULL
                    """)
                    null_count = cur.fetchone()[0]
                    
                    # 빈 배열/객체 체크
                    cur.execute(f"""
                        SELECT COUNT(*) 
                        FROM {table} 
                        WHERE {column}::text = '[]' OR {column}::text = '{{}}'
                    """)
                    empty_count = cur.fetchone()[0]
                    
                    message = f"{table}.{column}: {null_count} NULLs, {empty_count} empties"
                    
                    results.append(ValidationResult(
                        table, f"{column}_jsonb", True, message, 
                        f"null={null_count}, empty={empty_count}"
                    ))
        except Exception as e:
            results.append(ValidationResult(
                "jsonb_fields", "error", False, f"JSONB check failed: {e}"
            ))
        
        return results
    
    def get_statistics(self, conn) -> Dict:
        """테이블 통계"""
        stats = {}
        
        tables = [
            'ranges', 'operators', 'operator_stats', 'skills',
            'operator_skills', 'items', 'modules', 'zones',
            'stages', 'skin_brands', 'skins'
        ]
        
        try:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cur.fetchone()[0]
                
                # 추가 통계
                cur.execute("SELECT COUNT(DISTINCT profession) FROM operators")
                stats['unique_professions'] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(DISTINCT rarity) FROM operators")
                stats['unique_rarities'] = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT rarity, COUNT(*) 
                    FROM operators 
                    GROUP BY rarity 
                    ORDER BY rarity
                """)
                stats['operators_by_rarity'] = dict(cur.fetchall())
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
        
        return stats
    
    def run_validation(self) -> Tuple[bool, List[ValidationResult]]:
        """전체 검증 실행"""
        logger.info("Starting ETL validation...")
        
        try:
            conn = self.connect()
            
            # 1. 테이블 레코드 수 확인
            logger.info("Checking table counts...")
            self.results.append(self.check_table_count(conn, "ranges", 10))
            self.results.append(self.check_table_count(conn, "operators", 100))
            self.results.append(self.check_table_count(conn, "operator_stats", 100))
            self.results.append(self.check_table_count(conn, "skills", 100))
            self.results.append(self.check_table_count(conn, "items", 100))
            
            # 2. 외래키 무결성
            logger.info("Checking foreign key integrity...")
            self.results.extend(self.check_foreign_keys(conn))
            
            # 3. 데이터 범위
            logger.info("Checking data ranges...")
            self.results.extend(self.check_data_ranges(conn))
            
            # 4. JSONB 필드
            logger.info("Checking JSONB fields...")
            self.results.extend(self.check_jsonb_fields(conn))
            
            # 5. 통계 출력
            logger.info("Gathering statistics...")
            stats = self.get_statistics(conn)
            
            conn.close()
            
            # 결과 출력
            logger.info("\n" + "=" * 60)
            logger.info("VALIDATION RESULTS")
            logger.info("=" * 60)
            
            passed_count = sum(1 for r in self.results if r.passed)
            total_count = len(self.results)
            
            for result in self.results:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                logger.info(f"{status}: {result.message}")
                if result.details:
                    logger.info(f"       {result.details}")
            
            logger.info("=" * 60)
            logger.info(f"Total: {passed_count}/{total_count} checks passed")
            logger.info("=" * 60)
            
            # 통계 출력
            logger.info("\n" + "=" * 60)
            logger.info("DATABASE STATISTICS")
            logger.info("=" * 60)
            for key, value in stats.items():
                if isinstance(value, dict):
                    logger.info(f"{key}:")
                    for k, v in value.items():
                        logger.info(f"  {k}: {v:,}")
                else:
                    logger.info(f"{key}: {value:,}")
            logger.info("=" * 60)
            
            all_passed = all(r.passed for r in self.results)
            return all_passed, self.results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            return False, self.results


def main():
    """메인 함수"""
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'arknights',
        'user': 'postgres',
        'password': 'postgres'
    }
    
    validator = ETLValidator(conn_params)
    success, results = validator.run_validation()
    
    if not success:
        logger.error("Validation failed!")
        sys.exit(1)
    else:
        logger.info("Validation passed!")
        sys.exit(0)


if __name__ == "__main__":
    import sys
    main()
