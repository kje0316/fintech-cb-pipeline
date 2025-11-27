# C.O.R.E - MLOps 기반 AI 경영진단 플랫폼

**Company Operational Risk Engine**

60만 건의 기업 신용평가(CB) 데이터를 활용한 End-to-End MLOps 파이프라인으로, 부도 예측 및 유사 기업군 클러스터링 기반 경영진단 서비스를 제공합니다.

---

## 프로젝트 개요

본 프로젝트는 중소기업의 재무 건전성 분석, 부도 위험 예측, 유사 기업군 비교 분석을 위한 **MLOps 기반 AI 경영진단 플랫폼**입니다.

60만 건의 기업 신용 데이터를 **[Data Lake → Data Warehouse → Feature Store]** 아키텍처로 처리하고, XGBoost 기반 부도 예측과 VAE+K-Means 클러스터링을 통해 경영 인사이트를 제공하며, Airflow/MLflow 기반 MLOps 파이프라인으로 모델 재학습 및 드리프트 모니터링을 자동화합니다.

### 핵심 가치

- **유사 기업군 비교 분석**: VAE + K-Means 클러스터링으로 동일 군집 내 기업 벤치마킹
- **AI 부도 예측**: XGBoost 기반 부도 예측 모델 (AUC: 0.76, Brier Score: 0.0786)
- **설명 가능한 AI**: SHAP 분석을 통한 위험 요인 해석 및 개선 방안 제시
- **MLOps 자동화**: Airflow 스케줄링, MLflow 실험 추적, 데이터 드리프트 모니터링

---

## 주요 기능

| 기능 | 설명 |
| :--- | :--- |
| **데이터 파이프라인** | Lake(CSV) → DWH(PostgreSQL, Star Schema) → Feature Store 자동화 |
| **부도 예측 모델** | XGBoost 기반 ML 모델, SHAP 분석을 통한 설명 가능한 예측 |
| **기업 클러스터링** | VAE + K-Means로 유사 기업군 분류 (8개 클러스터) |
| **MLOps 파이프라인** | Airflow DAG, MLflow 실험 관리, 자동 재학습 |
| **실시간 대시보드** | Next.js 기반 경영진단 대시보드 |
| **REST API** | FastAPI 기반 예측/클러스터링/벤치마킹 API |

---

## 기술 스택

### 데이터 엔지니어링
| 구분 | 기술 |
| :--- | :--- |
| Data Lake | CSV 원본 데이터 (60만 건) |
| Data Warehouse | PostgreSQL (Star Schema) |
| Data Processing | PySpark (정제, 변환, 검증) |
| Feature Store | PostgreSQL (ML 피처 저장소) |

### 머신러닝
| 구분 | 기술 |
| :--- | :--- |
| 부도 예측 | XGBoost (최적 Brier Score: 0.0786) |
| 클러스터링 | VAE (Variational Autoencoder) + K-Means |
| 해석 | SHAP (TreeExplainer) |
| 전처리 | StandardScaler, LabelEncoder, SMOTE |

### MLOps
| 구분 | 기술 |
| :--- | :--- |
| 워크플로우 | Apache Airflow |
| 실험 관리 | MLflow (모델 레지스트리, 실험 추적) |
| 모니터링 | Prometheus + Grafana |
| 드리프트 감지 | PSI (Population Stability Index) |

### 백엔드 & 프론트엔드
| 구분 | 기술 |
| :--- | :--- |
| API | FastAPI (REST API) |
| Dashboard | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts, Chart.js |

---

## 프로젝트 구조

```bash
fintech-cb-pipeline/
│
├── README.md                          # 프로젝트 메인 문서
├── requirements.txt                   # Python 의존성
│
├── data/                              # 원본 데이터
│   └── raw/                           # 60만 건 기업 CB 데이터 (CSV)
│
├── etl/                               # ETL 파이프라인
│   ├── lake_to_dwh/                   # Lake → DWH 처리
│   │   └── scripts/                   # 추출, 정제, DW 빌드 스크립트
│   ├── dwh_to_mart/                   # DWH → Feature Store
│   │   ├── build_feature_store.py     # Feature Store 생성
│   │   └── feature_store_schema.sql   # 스키마 정의
│   └── run_full_pipeline.py           # 전체 파이프라인 실행
│
├── ml/                                # 머신러닝 모듈
│   ├── common/                        # 공통 유틸리티
│   │   ├── config.py                  # 설정 관리
│   │   └── db.py                      # DB 연결
│   │
│   ├── default_prediction/            # 부도 예측 모델
│   │   ├── train.py                   # 모델 학습
│   │   ├── predict.py                 # 예측 실행
│   │   ├── evaluate.py                # 평가 메트릭
│   │   ├── shap_analysis.py           # SHAP 분석
│   │   └── outputs/                   # 시각화 결과물
│   │       ├── model_selection_xgboost.png
│   │       ├── shap_bar_importance.png
│   │       ├── shap_waterfall_default.png
│   │       └── shap_group_importance.png
│   │
│   ├── clustering/                    # 클러스터링 모델
│   │   ├── train.py                   # VAE + K-Means 학습
│   │   ├── predict.py                 # 클러스터 예측
│   │   └── configs/                   # 클러스터 설정
│   │
│   ├── models/                        # 학습된 모델 저장
│   │   ├── default_prediction/        # 부도 예측 모델
│   │   │   ├── model.pkl              # XGBoost 모델
│   │   │   ├── scaler.pkl             # StandardScaler
│   │   │   └── metadata.json          # 모델 메타데이터
│   │   └── clustering/                # 클러스터링 모델
│   │
│   └── templates/                     # LLM 프롬프트 템플릿
│
├── airflow/                           # Airflow DAGs
│   └── dags/
│       ├── etl_feature_store.py       # Feature Store ETL DAG
│       └── model_retraining_with_drift.py  # 모델 재학습 DAG
│
├── monitoring/                        # 모니터링
│   ├── prometheus/                    # Prometheus 설정
│   └── grafana/                       # Grafana 대시보드
│
├── service/                           # 웹 서비스
│   ├── api/                           # FastAPI 백엔드
│   │   ├── main.py                    # FastAPI 앱
│   │   ├── routers/                   # API 라우터
│   │   │   ├── prediction.py          # 부도 예측 API
│   │   │   └── clustering.py          # 클러스터링 API
│   │   ├── services/                  # 비즈니스 로직
│   │   └── middleware/                # 미들웨어
│   │       └── prometheus_middleware.py
│   │
│   └── dashboard/                     # Next.js 대시보드
│       ├── app/                       # App Router
│       │   ├── page.tsx               # 메인 페이지
│       │   ├── upload/                # 파일 업로드
│       │   ├── dashboard/             # 대시보드
│       │   └── result/                # 분석 결과
│       ├── components/                # React 컴포넌트
│       └── lib/                       # API 클라이언트
│
├── notebooks/                         # Jupyter 노트북
│   └── eda_data_quality_visualization.ipynb
│
└── config/                            # 환경 설정
```

---

## 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/kje0316/fintech-cb-pipeline.git
cd fintech-cb-pipeline

# Python 의존성 설치 (uv 사용)
uv sync

# 또는 pip 사용
pip install -r requirements.txt

# PostgreSQL 설정 (config/database.py 참고)
```

### 2. ETL 파이프라인 실행

```bash
# Lake → DWH → Feature Store 전체 파이프라인 실행
python etl/run_full_pipeline.py
```

### 3. ML 모델 학습

```bash
# 부도 예측 모델 학습
uv run python ml/default_prediction/train.py

# 클러스터링 모델 학습
uv run python ml/clustering/train.py
```

### 4. 웹 서비스 실행

```bash
# 백엔드 API 실행 (FastAPI)
cd service/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 대시보드 실행 (Next.js)
cd service/dashboard
npm install && npm run dev
```

### 5. Airflow 실행

```bash
# Airflow 초기화
export AIRFLOW_HOME=$(pwd)/airflow
uv run airflow db init

# 웹서버 및 스케줄러 실행
uv run airflow webserver -p 8080 &
uv run airflow scheduler &
```

브라우저에서 접속:
- **API 문서**: http://localhost:8000/docs
- **대시보드**: http://localhost:3000
- **Airflow**: http://localhost:8080

---

## 모델 성능

### 부도 예측 모델 (XGBoost)

| 메트릭 | 값 |
| :--- | :---: |
| AUC-ROC | 0.7602 |
| Brier Score | 0.0786 (Best) |
| Calibration | Well-calibrated |

**모델 선택 근거**: XGBoost가 LightGBM(0.0820), CatBoost(0.0917) 대비 가장 낮은 Brier Score를 기록하여 확률 보정(Calibration) 성능이 우수함.

### 주요 피처 그룹 (SHAP 분석)

| 피처 그룹 | Mean SHAP |
| :--- | :---: |
| N (파생비율) | 1.635 |
| FN1 (자산/자본) | 1.542 |
| FN3 (손익) | 1.405 |
| R (비율지표) | 1.404 |
| DA/DB (재무상태) | 1.040 |
| FN2 (부채) | 0.692 |

### 클러스터링 모델 (VAE + K-Means)

- **클러스터 수**: 8개
- **Latent Dimension**: 10
- **실루엣 스코어**: 0.45+

---

## 주요 API 엔드포인트

### 부도 예측

```
POST /api/v1/prediction/predict
Content-Type: application/json

{
  "company_id": "C123456",
  "features": {...}
}
```

### 클러스터링

```
POST /api/v1/clustering/predict
Content-Type: application/json

{
  "company_id": "C123456",
  "features": {...}
}
```

### 벤치마킹

```
POST /api/v1/benchmark/financial
Content-Type: application/json

{
  "industry_code": "C10",
  "company_size": "MEDIUM",
  "metrics": {
    "debt_ratio": 150.5,
    "current_ratio": 120.3
  }
}
```

---

## MLOps 파이프라인

### Airflow DAGs

1. **etl_feature_store.py**: Feature Store ETL 자동화
   - 스케줄: 월 1회
   - DWH → Feature Store 데이터 동기화

2. **model_retraining_with_drift.py**: 모델 재학습 및 드리프트 모니터링
   - 스케줄: 주 1회
   - PSI 기반 데이터 드리프트 감지
   - 자동 모델 재학습 및 MLflow 등록

### MLflow 실험 관리

- 모델 버전 관리
- 하이퍼파라미터 추적
- 메트릭 비교
- 모델 레지스트리

---

## 라이선스

이 프로젝트는 교육 목적으로 작성되었습니다.
