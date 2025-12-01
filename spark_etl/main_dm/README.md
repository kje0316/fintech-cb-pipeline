# DWH → DM 파이프라인 (Spark 버전)

## 📁 프로젝트 구조

```
fintech-cb-pipeline/
├── spark_etl/
│   ├── __init__.py
│   ├── postgresql-42.7.1.jar          # JDBC 드라이버
│   │
│   ├── lake_to_dwh2/                  # Lake → DWH 파이프라인
│   │   └── ...
│   │
│   └── main_dm/                        # ⭐ DWH → DM 파이프라인
│       ├── __init__.py
│       ├── config.py                   # 설정
│       ├── spark_utils.py              # Spark 유틸리티
│       ├── run_pipeline.py             # 메인 실행 스크립트
│       ├── queries.sql                 # SQL 쿼리 (기존 것 사용)
│       │
│       └── scripts/
│           ├── __init__.py
│           ├── extract.py              # DWH 추출
│           ├── validate.py             # 데이터 검증
│           ├── constraints.py          # 제약조건 검증
│           └── transform.py            # 파생 데이터 생성
│
└── shared/
    └── config_loader.py                # DB 설정 (공통)
```

---

## 🔧 lake_to_dwh2와의 일관성

이 프로젝트는 `lake_to_dwh2`와 **동일한 구조와 설정**을 사용합니다:

### 1. Spark 세션 생성
```python
# lake_to_dwh2와 동일
from spark_etl.main_dm.spark_utils import get_spark_session

spark = get_spark_session()
# - AppName: ETL_DWH_to_DM
# - JDBC jar: postgresql-42.7.1.jar
# - config: spark.driver/executor.extraClassPath
```

### 2. DB 연결
```python
# shared.config_loader 사용 (lake_to_dwh2와 동일)
from shared.config_loader import DB_URL
```

### 3. Import 경로
```python
# lake_to_dwh2와 동일한 import 스타일
from spark_etl.main_dm.scripts import copy_dwh_tables_to_dm
```

### 4. JDBC 드라이버
```
postgresql-42.7.1.jar (lake_to_dwh2와 동일 버전)
```

---

## 🚀 실행 방법

### 전제 조건
1. `lake_to_dwh2`가 정상 작동하는 환경
2. `shared/config_loader.py` 설정 완료
3. `postgresql-42.7.1.jar` 존재

### 실행

```bash
# 프로젝트 루트에서
cd fintech-cb-pipeline

# Spark 파이프라인 실행
python -m spark_etl.main_dm.run_pipeline
```

**lake_to_dwh2와 동일한 방식으로 실행됩니다!**

---

## ⚙️ 설정 (config.py)

### 기본 설정
```python
# DWH/DM 스키마
DWH_SCHEMA = "dwh2"  # lake_to_dwh2와 동일
DM_SCHEMA = "dm"

# 복사할 테이블
TABLES_TO_COPY = [
    'dim_company',
    'dim_industry',
    'dim_time',
    'fact_credit_behavior',
    'fact_financial_statement'
]
```

### 실행 모드
```python
# lake_to_dwh2와 동일하게 hybrid 모드 사용
EXECUTION_MODE = "hybrid"  # Spark 처리 + PostgreSQL 저장
```

### JDBC 병렬 읽기
```python
JDBC_PARTITION_CONFIGS = {
    'fact_financial_statement': {
        'partitionColumn': 'company_sk',
        'lowerBound': 1,
        'upperBound': 100000,
        'numPartitions': 10
    }
}
```

---

## 📊 파이프라인 단계

```
STEP 1: DWH 테이블 추출 (Spark JDBC)
  ↓
STEP 2: 데이터 품질 검증 (Spark DataFrame)
  ↓
STEP 3: 제약조건 검증 (Spark 로직)
  ↓
STEP 4: 파생 데이터 생성 (Spark SQL - queries.sql 사용)
  ↓
STEP 5: PostgreSQL 저장 (Spark JDBC Write)
  ↓
완료!
```

---

## 🔑 핵심 포인트

### 1. queries.sql 그대로 사용
```python
# transform.py에서 기존 queries.sql 자동 읽기
# CREATE TABLE 부분만 제거하고 Spark SQL 실행
```

### 2. lake_to_dwh2와 동일한 DB 연결
```python
# shared/config_loader.py의 DB_URL 사용
from shared.config_loader import DB_URL
```

### 3. 동일한 JDBC 드라이버
```
postgresql-42.7.1.jar
```

### 4. 동일한 Spark 설정
```python
# spark.driver/executor.extraClassPath
# AppName 형식: ETL_xxx
```

---

## 📝 주요 파일 설명

### spark_utils.py
- `get_spark_session()`: Spark 세션 생성 (lake_to_dwh2와 동일)
- `get_jdbc_properties()`: JDBC 연결 정보 파싱
- `load_to_postgres()`: DataFrame → PostgreSQL 저장

### scripts/extract.py
- DWH 테이블을 Spark DataFrame으로 추출
- JDBC 병렬 읽기 지원

### scripts/validate.py
- Spark DataFrame으로 데이터 품질 검증
- PK 중복, NULL, FK 참조 무결성 체크

### scripts/transform.py
- `queries.sql` 사용하여 파생 데이터 생성
- Spark SQL 실행

### run_pipeline.py
- 전체 파이프라인 실행
- lake_to_dwh2의 `run_pipe_spark.py`와 동일한 구조

---

## 🔧 lake_to_dwh2와의 차이점

| 항목 | lake_to_dwh2 | main_dm |
|-----|-------------|---------|
| **소스** | Data Lake | DWH (dwh2) |
| **타겟** | DWH (dwh2) | DM (dm) |
| **테이블** | dim, fact | dim, fact, **derived_data** |
| **변환** | cleansing | **파생 지표 계산** (60+ 컬럼) |
| **구조** | 동일 | 동일 |
| **Spark 설정** | 동일 | 동일 |
| **JDBC 드라이버** | 동일 | 동일 |

---

## ⚠️ 주의사항

### 1. queries.sql 필수
- `main_dm/queries.sql` 파일이 필요합니다
- 기존 PostgreSQL 버전의 SQL 파일을 그대로 사용하세요

### 2. shared/config_loader.py
- lake_to_dwh2와 **동일한 DB_URL** 사용
- 별도 설정 불필요

### 3. JDBC 드라이버
- `postgresql-42.7.1.jar`가 프로젝트 루트에 있어야 합니다

---

## ✅ 체크리스트

- [ ] `lake_to_dwh2`가 정상 작동함
- [ ] `shared/config_loader.py` 설정 완료
- [ ] `postgresql-42.7.1.jar` 존재
- [ ] `queries.sql` 파일 준비
- [ ] PySpark 설치
- [ ] psycopg2 설치

---

## 🎯 실행 예시

```bash
$ python -m spark_etl.main_dm.run_pipeline

╔════════════════════════════════════════════════════════════════════╗
║            DWH → DM 구축 시작 (Spark 버전)                        ║
╚════════════════════════════════════════════════════════════════════╝

시작 시간: 2024-11-23 16:30:00
실행 모드: hybrid

✓ SparkSession 초기화 완료
  - App Name: ETL_DWH_to_DM
  - Spark Version: 3.x.x

======================================================================
STEP 1: DWH 테이블 → Spark DataFrame 추출
======================================================================

[추출 중] dwh2.dim_company...
  ✓ dim_company 추출 완료: 12,345행 x 15컬럼

...

✅ 총 5개 테이블 추출 완료

⏱️ STEP 1 소요 시간: 45초

...

╔════════════════════════════════════════════════════════════════════╗
║                      ✓ DM 구축 완료!                              ║
╚════════════════════════════════════════════════════════════════════╝

완료 시간: 2024-11-23 16:34:00
총 소요 시간: 4분 0초
```

---

**lake_to_dwh2와 완벽하게 일치하는 구조입니다!** 🚀
