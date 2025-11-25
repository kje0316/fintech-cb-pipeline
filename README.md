# 🏦 Fintech CB Pipeline: 중소기업 재무 데이터 분석 플랫폼

60만 건의 기업 신용평가(CB) 데이터를 처리하는 End-to-End 데이터 파이프라인과 ML 기반 부도 예측 분석 시스템

---

## 📌 프로젝트 개요

본 프로젝트는 중소기업의 재무 건전성 분석 및 부도 위험 예측을 위한 **데이터 엔지니어링 + 머신러닝 통합 플랫폼**입니다.

60만 건의 기업 신용 데이터를 **[Data Lake → Data Warehouse → Data Mart]** 아키텍처로 처리하고, ML 모델을 통해 부도 예측 및 재무 인사이트를 제공하며, Next.js 대시보드로 시각화합니다.

### 핵심 가치

- **데이터 엔지니어링**: Spark 기반 대용량 데이터 처리 파이프라인 (60만 건)
- **ML 분석**: XGBoost 기반 부도 예측 모델 (F1: 0.138, AUC: 0.80)
- **설명 가능한 AI**: SHAP을 활용한 예측 해석 및 개선 방안 제시
- **실시간 대시보드**: 업종별 부도율, KPI, 위험 트렌드 모니터링

---

## ✨ 주요 기능

| 기능 | 설명 | 상태 |
| :--- | :--- | :---: |
| **🏗️ 데이터 파이프라인** | Lake(CSV) → DWH(PostgreSQL, Star Schema) → Mart(집계 테이블) 자동화 처리 | ✅ |
| **🤖 부도 예측 모델** | XGBoost 기반 ML 모델, SHAP 분석을 통한 설명 가능한 예측 | ✅ |
| **📊 대시보드** | Next.js 기반 업종별 부도율, KPI, 월별 추세 시각화 | ✅ |
| **🔍 벤치마킹 API** | 업종/규모별 재무 지표 백분위 비교 분석 API | ✅ |
| **📈 위험 분석** | 업종별 리스크 랭킹 및 월별 부도율 추세 분석 | ✅ |

---

## 🧱 기술 스택

### 데이터 엔지니어링
- **Data Lake**: CSV 원본 데이터 저장
- **Data Warehouse**: PostgreSQL (Star Schema: 5개 Dimension, 1개 Fact)
- **Data Processing**: PySpark (데이터 정제, 변환, 검증)
- **Data Mart**: PostgreSQL (집계 테이블 7개)

### 머신러닝
- **피처 선택**: 5가지 통계 방법론 (MI, F-test, RF, Correlation, Variance) + 도메인 검증
- **모델**: XGBoost, LightGBM, Random Forest, Logistic Regression
- **해석**: SHAP (Feature Importance, Waterfall Plot)
- **전처리**: Scikit-learn (SMOTE, StandardScaler, LabelEncoder)

### 백엔드 & 프론트엔드
- **API**: FastAPI (벤치마킹, 메타데이터, 대시보드 API)
- **Dashboard**: Next.js 14 + TypeScript + Tailwind CSS
- **Charts**: Recharts (라인, 파이, 히트맵, 바 차트)

### 인프라
- **Database**: PostgreSQL
- **Version Control**: Git, GitHub

---

## 📁 프로젝트 구조

```bash
fintech-cb-pipeline/
│
├── README.md                      # 프로젝트 메인 문서
├── requirements.txt               # Python 의존성
│
├── docs/                          # 설계 문서
│
├── data/                          # 원본 데이터 (CSV)
│   └── raw/                       # 60만 건 기업 CB 데이터
│
├── etl/                           # 데이터 파이프라인
│   ├── lake_to_dwh/              # Lake → DWH 처리
│   │   └── scripts/              # 추출, 정제, DW 빌드 스크립트
│   ├── dwh_to_mart/              # DWH → Mart 집계
│   │   ├── python/               # Mart 생성 스크립트 (7개)
│   │   └── scripts/              # 재무 벤치마크, 위험 분석
│   └── run_full_pipeline.py      # 전체 파이프라인 실행
│
├── ml/                            # 머신러닝 모듈 (통계적 피처 선택 기반)
│   ├── data/                      # 학습/검증 데이터 (Parquet)
│   │   ├── raw_data_full_20210801.parquet          # 전체 159개 피처
│   │   ├── feature_selection_report.csv            # ⭐ 피처 선택 리포트 (발표용)
│   │   └── engineered_features_20210801.parquet    # 최종 피처 + 파생변수
│   ├── models/                    # 학습된 모델 및 SHAP 결과
│   │   ├── default_model_best.pkl                  # 최적 모델
│   │   ├── feature_importance.csv                  # 피처 중요도
│   │   └── training_summary.txt                    # 학습 요약
│   ├── notebooks/                 # EDA, 피처 엔지니어링, 모델 해석
│   ├── scripts/                   # 6단계 ML 파이프라인
│   │   ├── 01_extract_training_data.py             # 데이터 추출 (159개)
│   │   ├── 02a_statistical_preprocessing.py        # 통계적 전처리
│   │   ├── 02b_statistical_feature_selection.py    # 5가지 방법론 선택
│   │   ├── 02c_domain_validation.py                # 도메인 검증
│   │   ├── 03_feature_engineering.py               # 파생 변수 생성
│   │   ├── 04_train_default_model.py               # 모델 학습
│   │   └── run_full_ml_pipeline.py                 # 전체 실행
│   └── README.md                  # ML 파이프라인 상세 문서
│
├── service/                       # 웹 서비스
│   ├── api/                       # FastAPI 백엔드
│   │   ├── routers/              # API 엔드포인트
│   │   ├── services/             # 비즈니스 로직
│   │   └── main.py               # FastAPI 앱
│   └── dashboard/                 # Next.js 대시보드
│       ├── app/                   # Next.js App Router
│       ├── components/            # React 컴포넌트
│       └── lib/                   # API 연동 및 타입
│
└── config/                        # 환경 설정 (DB 연결 정보 등)
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/kje0316/fintech-cb-pipeline.git
cd fintech-cb-pipeline

# Python 의존성 설치
pip install -r requirements.txt

# PostgreSQL 설정 (config/database.py 참고)
# DB 연결 정보 설정 필요
```

### 2. 전체 파이프라인 실행

```bash
# Lake → DWH → Mart 전체 파이프라인 실행
python etl/run_full_pipeline.py

# 실행 시간: 약 15-20분 (60만 건 기준)
```

### 3. ML 모델 학습

```bash
# 1. DWH에서 학습 데이터 추출
python ml/scripts/01_extract_training_data.py

# 2. 피처 엔지니어링
python ml/scripts/02_feature_engineering.py

# 3. 모델 학습
python ml/scripts/02_train_default_model.py

# 4. SHAP 분석 (Jupyter 노트북)
jupyter notebook ml/notebooks/03_model_interpretation.ipynb
```

### 4. 웹 서비스 실행

```bash
# 백엔드 API 실행 (FastAPI)
cd service/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 대시보드 실행 (Next.js)
cd service/dashboard
npm install
npm run dev
```

브라우저에서 접속:
- **API 문서**: http://localhost:8000/docs
- **대시보드**: http://localhost:3000

---

## 📊 데이터 아키텍처

### Data Warehouse (Star Schema)

**Dimension Tables (5개)**
- `dim_company` - 기업 기본 정보
- `dim_date` - 날짜 차원
- `dim_industry` - 업종 정보
- `dim_major_category` - 대분류 업종
- `dim_region` - 지역 정보

**Fact Table (1개)**
- `fact_company_financials` - 재무 지표 (60만 행)

### Data Marts (7개)

| Mart 테이블 | 설명 | 용도 |
| :--- | :--- | :--- |
| `mart_market_kpi_monthly` | 월별 시장 KPI (기업 수, 부도율 등) | 대시보드 KPI |
| `mart_industry_default_trend` | 업종별 월별 부도율 추세 | 트렌드 차트 |
| `mart_industry_risk_ranking` | 업종별 리스크 랭킹 | 위험 업종 분석 |
| `mart_credit_grade_distribution` | 신용등급 분포 | 등급별 통계 |
| `mart_industry_financial_stats` | 업종별 재무 지표 통계 | 벤치마킹 |
| `mart_financial_benchmarks` | 업종/규모별 백분위 | API 벤치마킹 |
| `mart_risk_profile` | 기업별 종합 위험 프로필 | 위험 평가 |

---

## 🤖 ML 모델 성능

### 부도 예측 모델 (XGBoost)

```
Training Data: 50,000 기업 (2021-08)
부도율: 1.52% (758개 부도 / 49,242개 정상)

Model Performance:
├─ Accuracy:  0.9588
├─ Precision: 0.1012
├─ Recall:    0.2171
├─ F1-Score:  0.1381
└─ AUC-ROC:   0.8025
```

### 주요 예측 변수 (Top 5)

1. **신용등급** (31.5%) - 가장 강력한 예측 인자
2. **감사 여부** (7.6%) - 외부 감사 실시 여부
3. **단기차입금 의존도** (4.9%) - 레버리지 지표
4. **공공신용이벤트** (4.7%) - 신용 이상 징후
5. **종업원 수** (4.2%) - 기업 규모

### SHAP 분석 예시

```
부도 확률 35% 기업의 위험 요인:
├─ 신용등급 7등급     → +12%p
├─ 단기차입금 85%     → +8%p
├─ 유동비율 90%       → +5%p
└─ 매출채권회전율 2.5 → +3%p

개선 시나리오:
신용등급 5등급 개선 → 부도 확률 22%로 감소 (-13%p)
```

---

## 📈 대시보드 주요 화면

### 1. KPI 요약 카드
- 총 기업 수
- 평균 신용등급
- 전체 부도율
- 고위험 기업 비율

### 2. 시계열 분석
- 월별 부도율 추세 (상위 5개 고위험 업종)
- 업종별 리스크 변화 추이

### 3. 업종 분석
- 업종 구성비 (파이 차트)
- 업종별 평균 부도율 (막대 그래프)
- 월별 × 업종별 부도율 히트맵

---

## 🔧 주요 API 엔드포인트

### 메타데이터
```
GET /api/v1/metadata/industries        # 업종 목록
GET /api/v1/metadata/industries/{code} # 업종 상세 정보
```

### 벤치마킹
```
POST /api/v1/benchmark/financial       # 재무 지표 백분위 조회
```

Request:
```json
{
  "industry_code": "C10",
  "company_size": "MEDIUM",
  "metrics": {
    "debt_ratio": 150.5,
    "current_ratio": 120.3
  }
}
```

Response:
```json
{
  "industry_name": "식료품 제조업",
  "percentiles": {
    "debt_ratio": 65.2,
    "current_ratio": 42.8
  }
}
```

### 대시보드 데이터
```
GET /api/v1/dashboard/kpi                      # KPI 데이터
GET /api/v1/dashboard/top-industries-trend     # 상위 업종 추세
GET /api/v1/dashboard/industry-composition     # 업종 구성비
GET /api/v1/dashboard/heatmap                  # 히트맵 데이터
GET /api/v1/dashboard/industry-default-rates   # 업종별 부도율
```

---

## 📚 문서

- **[빠른 시작 가이드](docs/QUICK_START.md)**: 프로젝트 초기 설정
- **[ETL 실행 가이드](docs/ETL_EXECUTION_GUIDE.md)**: 파이프라인 실행 방법
- **[ML 모델 문서](ml/README.md)**: 부도 예측 모델 상세 설명
- **[대시보드 가이드](service/dashboard/README.md)**: Next.js 대시보드 실행 방법
- **[데이터 정제 전략](docs/data_cleansing_strategy.md)**: 데이터 품질 관리

---

## 🛠️ 향후 개선 방향

### 데이터 파이프라인
- [ ] Airflow를 통한 스케줄링 자동화
- [ ] 데이터 품질 모니터링 대시보드
- [ ] 증분(incremental) 처리 로직

### ML 모델
- [ ] 하이퍼파라미터 튜닝 (GridSearchCV)
- [ ] 앙상블 모델 (XGBoost + LightGBM + RF)
- [ ] Threshold 최적화 (비용-편익 분석)
- [ ] 시계열 피처 추가 (전년 대비 변화율)

### 서비스
- [ ] 실시간 부도 예측 API 구축
- [ ] SHAP 기반 설명 API 제공
- [ ] 사용자 인증 및 권한 관리
- [ ] 대시보드 필터링 기능 (날짜 범위, 업종 선택)

---

## 👥 기여

프로젝트 개선 제안 및 버그 리포트는 [Issues](https://github.com/kje0316/fintech-cb-pipeline/issues)에서 환영합니다.

---

## 📄 라이선스

이 프로젝트는 교육 목적으로 작성되었습니다.