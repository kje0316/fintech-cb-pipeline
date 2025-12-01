"""
DWH → DM 파이프라인 설정 (Spark 버전)
lake_to_dwh2와 동일한 설정 구조 사용
"""

# ========================================
# 스키마 설정
# ========================================
DWH_SCHEMA = "dwh2"
DM_SCHEMA = "dm"

# ========================================
# 복사할 테이블 목록
# ========================================
TABLES_TO_COPY = [
    'dim_company',
    'dim_industry',
    'dim_time',
    'fact_credit_behavior',
    'fact_financial_statement'
]

# ========================================
# 파이프라인 옵션
# ========================================
ENABLE_CONSTRAINTS = True
ENABLE_VALIDATION = True
CREATE_INDEXES = False  # Spark/Delta Lake는 인덱스 대신 파티셔닝 사용

# ========================================
# Spark 실행 모드 선택
# ========================================
# "spark" : Spark + Delta Lake (권장)
# "hybrid" : Spark 처리 + PostgreSQL 저장
EXECUTION_MODE = "hybrid"  # lake_to_dwh2와 동일하게 hybrid 사용

# ========================================
# Delta Lake 설정 (EXECUTION_MODE = "spark" 일 때)
# ========================================
# 로컬 경로 또는 S3/HDFS 경로
DELTA_BASE_PATH = "/data/delta/dm"  # 로컬
# DELTA_BASE_PATH = "s3://your-bucket/dm"  # S3
# DELTA_BASE_PATH = "hdfs://namenode:9000/dm"  # HDFS

# ========================================
# JDBC 읽기 최적화 설정
# ========================================
# 대용량 테이블 병렬 읽기 설정
JDBC_PARTITION_CONFIGS = {
    'fact_financial_statement': {
        'partitionColumn': 'company_sk',
        'lowerBound': 1,
        'upperBound': 100000,
        'numPartitions': 20
    },
    'fact_credit_behavior': {
        'partitionColumn': 'company_sk',
        'lowerBound': 1,
        'upperBound': 100000,
        'numPartitions': 20
    }
}

# ========================================
# Delta Lake 파티셔닝 설정
# ========================================
PARTITION_CONFIGS = {
    'fact_financial_statement': ['time_sk'],
    'fact_credit_behavior': ['time_sk'],
    'derived_data': ['time_sk']
}
