# DWH → DM 파이프라인

데이터 웨어하우스(DWH)에서 데이터 마트(DM)로 데이터를 추출, 변환, 적재하는 ETL 파이프라인

## 📁 프로젝트 구조

```
dwh_to_dm/
├── run_pipeline.py          # 메인 실행 파일
├── config.py                 # 설정 파일
├── queries.sql               # 파생 데이터 생성 SQL
├── scripts/                  # 스크립트 모듈
│   ├── __init__.py
│   ├── extract.py           # DWH 테이블 추출
│   ├── validate.py          # 데이터 품질 검증
│   ├── constraints.py       # 제약조건 추가
│   └── transform.py         # 파생 데이터 변환
└── README.md
```

## 🚀 실행 방법

### 기본 실행

```bash
python -m dwh_to_dm.run_pipeline
```

### 설정 변경

`config.py` 파일에서 설정을 변경할 수 있습니다:

```python
# 스키마 설정
DWH_SCHEMA = "dwh2"  # 소스 스키마
DM_SCHEMA = "dm"     # 타겟 스키마

# 기능 활성화/비활성화
ENABLE_CONSTRAINTS = True   # 제약조건 추가
ENABLE_VALIDATION = True    # 데이터 검증
CREATE_INDEXES = True       # 인덱스 생성
```

## 📊 파이프라인 단계

### STEP 1: 테이블 복사
- DWH 스키마의 5개 테이블을 DM으로 복사
- 테이블: dim_company, dim_industry, dim_time, fact_credit_behavior, fact_financial_statement

### STEP 2: 데이터 품질 검증
- PK 중복 체크
- NULL 값 체크
- FK 참조 무결성 체크

### STEP 3: 제약조건 추가
- Primary Key (PK)
- Foreign Key (FK)
- NOT NULL
- UNIQUE (비즈니스 키)

### STEP 4: 파생 데이터 생성
- `queries.sql`의 SQL을 실행하여 derived_data 테이블 생성
- 재무 지표 계산 (금액, 비율, 성장성, 안정성, 수익성, 활동성)
- 제약조건 및 인덱스 추가

## 🔧 모듈 설명

### `extract.py`
DWH에서 테이블을 추출하여 DM으로 복사
- `copy_dwh_tables_to_dm(engine)`: 테이블 복사 함수

### `validate.py`
데이터 품질을 검증
- `validate_data_quality(engine)`: 검증 함수 (PK, NULL, FK 체크)

### `constraints.py`
제약조건을 추가
- `add_constraints_to_dm(engine)`: 기본 테이블 제약조건
- `add_derived_data_constraints(engine)`: derived_data 제약조건

### `transform.py`
파생 데이터를 생성하고 변환
- `create_derived_data(engine)`: queries.sql 실행
- `create_indexes(engine)`: 인덱스 생성

## 📝 SQL 쿼리

`queries.sql` 파일에 파생 데이터 생성 쿼리가 저장되어 있습니다.
- 금액 파생: fn1_10, fn1_13, fn1_19, fn1_24, fn2_5, fn2_10 등
- 비율 파생: r001~r023 (성장성, 안정성, 수익성, 활동성)
- 추가 지표: n001~n012

## ⚙️ 요구사항

```bash
pip install sqlalchemy psycopg2-binary python-dotenv
```

## 🔐 환경 변수

`.env` 파일에 DB 연결 정보 설정:
```
DB_URL=postgresql://user:password@localhost:5432/dbname
```

## 📈 성능 최적화

- SQL 직접 실행으로 고속 처리
- Python 메모리 사용 최소화
- 인덱스 자동 생성
- Bulk INSERT 사용

## 🛠️ 트러블슈팅

### 제약조건 추가 실패
```
❌ 오류: duplicate key value violates unique constraint
```
→ STEP 2 검증 결과 확인, 중복 데이터 제거

### FK 참조 무결성 위반
```
❌ 오류: insert or update on table violates foreign key constraint
```
→ dim 테이블 먼저 적재 확인, orphan records 제거

### 모듈 import 오류
```
❌ 오류: No module named 'dwh_to_dm'
```
→ 프로젝트 루트에서 실행: `python -m dwh_to_dm.run_pipeline`

## 📌 주의사항

1. **데이터 백업**: 기존 DM 테이블은 `DROP CASCADE`로 삭제됩니다
2. **검증 필수**: 프로덕션 환경에서는 `ENABLE_VALIDATION = True` 권장
3. **순서 중요**: dim → fact → derived 순서로 생성됩니다
4. **트랜잭션**: 각 단계는 트랜잭션 내에서 실행됩니다

## 📧 문의

이슈가 있을 경우 관리자에게 문의하세요.
