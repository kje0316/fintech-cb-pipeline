"""
DWH → DM 파이프라인 설정
"""

# 스키마 설정
DWH_SCHEMA = "dwh2"
DM_SCHEMA = "dm"

# 복사할 테이블 목록
TABLES_TO_COPY = [
    'dim_company',
    'dim_industry',
    'dim_time',
    'fact_credit_behavior',
    'fact_financial_statement'
]

# 제약조건 설정
ENABLE_CONSTRAINTS = True
ENABLE_VALIDATION = True

# 인덱스 설정
CREATE_INDEXES = True
