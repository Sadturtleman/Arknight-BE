#!/usr/bin/env python3
"""
Quick Start Script
환경 변수를 사용한 간편 ETL 실행
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# arknights_etl 모듈 임포트
from arknights_etl import ArknightsETL, ETLConfig, setup_logging


def main():
    """환경 변수 기반 ETL 실행"""
    
    # 환경 변수에서 설정 읽기
    config = ETLConfig(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "arknights"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", "postgres"),
        data_dir=Path(os.getenv("DATA_DIR", "./data")),
        batch_size=int(os.getenv("BATCH_SIZE", "500")),
        max_retries=int(os.getenv("MAX_RETRIES", "3"))
    )
    
    # 로깅 설정
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger = setup_logging(log_level)
    
    # 설정 출력
    logger.info("Configuration:")
    logger.info(f"  Database: {config.db_host}:{config.db_port}/{config.db_name}")
    logger.info(f"  Data Directory: {config.data_dir}")
    logger.info(f"  Batch Size: {config.batch_size}")
    
    # ETL 실행
    try:
        etl = ArknightsETL(config)
        etl.run()
        
        logger.info("\n✅ ETL completed successfully!")
        logger.info("Run 'python validate_etl.py' to verify the data.")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  ETL interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ ETL failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
