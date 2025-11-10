# 🏦 Fintech-cb-pipeline: 중소기업 재무 분석 및 솔루션 플랫폼

데이터 파이프라인 구축을 통해 기업 CB 데이터를 처리하고, AI/통계 분석을 기반으로 중소기업에 가장 필요한 재무 인사이트를 제공하는 솔루션을 제안합니다.

---

## 📌 프로젝트 개요 (Overview)

국내 기업의 99%는 중소기업이지만, 많은 중소기업이 자사의 재무 상태를 동종 업계와 객관적으로 비교하기 어렵고, 신용/재무 문제 발생 시 명확한 솔루션을 얻기 힘든 '정보 사각지대'에 놓여있습니다.

본 프로젝트는 이러한 문제를 해결하기 위해, 60만 건의 기업 CB(신용) 데이터를 기반으로 **'데이터 파이프라인(DE)'**과 **'분석 서비스(API/ML)'**를 결합한 MLOps 플랫폼을 구축합니다.

우리의 최종 목표는 수집된 데이터를 **[Lake → DWH → Mart]**로 이어지는 자동화된 파이프라인으로 처리하고, 이 데이터를 기반으로 **[1. 재무 벤치마킹]**과 **[2. 신용 개선 솔루션]**을 제공하여, 중소기업이 데이터에 기반한 합리적인 의사결정을 내릴 수 있도록 돕는 것입니다.

---

## ✨ 주요 기능 (Key Features)

> [!NOTE]
> 본 프로젝트는 '베이스 파이프라인'을 먼저 구축한 뒤, 서비스 기능을 점진적으로 고도화하는 것을 목표로 합니다.

| 기능 (모듈) | 설명 |
| :--- | :--- |
| **🏭 데이터 엔지니어링 파이프라인 ** | (핵심 기반) 60만 건의 원본(CSV) 데이터를 **[Lake(HDFS) → DWH(Hive/Star Schema) → Mart(집계/피처)]**로 처리하는 자동화된 Spark 파이프라인을 구축합니다. |
| **📊 재무 벤치마킹 API ** | (MVP 기능 1) 사용자가 업종/규모를 입력하면, 동종/동급 기업 대비 **자사의 재무 상태 위치(Percentile)**를 실시간으로 비교 분석해주는 API와 대시보드를 제공합니다. |
| **🔮 신용 개선 솔루션 ** | (고도화 기능) ML 모델(SHAP 등)을 기반으로, 현재 재무 상태에서 **신용 등급/부도 확률에 가장 큰 영향을 미치는 요소를 분석**하고 개선 방향을 제시합니다. |
| **🖥️ 데이터 품질(DQ) 모니터링 ** | (기반 기능) 파이프라인 전 과정에서 `음수 값`, `결측치` 등 멘토링에서 발견된 데이터 이슈를 자동으로 탐지하고 처리/리포트하는 모듈을 탑재합니다. |

---

## 🧱 기술 스택 (Tech Stack)

| 구성 요소 | 사용 기술 |
| :--- | :--- |
| **Data Lake** | Hadoop (HDFS) |
| **Data Warehouse** | Hive, HDFS (Parquet) |
| **Data Processing** | **Spark (PySpark, Spark SQL)** |
| **Data Mart** | Hive, (or PostgreSQL/MySQL) |
| **Backend API** | **Python, FastAPI** |
| **Frontend** | **Streamlit** |
| **Orchestration** | Airflow |
| **ML** | Scikit-learn (PCA, K-Means), MLflow |
| **Infra / Tools** | Docker, Git, GitHub |

---

## 📁 디렉토리 구조 (Directory Structure)



```bash
fintech-cb-pipeline/
│
├── README.md                # 프로젝트 개요 (현재 파일)
├── .gitignore
├── docker-compose.yml       # 로컬 개발 환경 (Hadoop, Spark, API 등)
├── requirements.txt         # Python 의존성 (전체 공통)
├── setup.py                 # 모듈간 import를 위한 설치형 패키지
│
├── docs/                    # 모든 설계 문서 (Wiki 역할)
│   ├── 01_architecture.md   # 전체 아키텍처 다이어그램 (Mermaid)
│   ├── 02_dwh_schema.md     # (P1→P2) DWH 스키마 약속
│   └── 03_datamart_schema.md  # (P2→P3) Data Mart 스키마 약속
│
├── config/                  # 환경 설정 (DB, Spark, HDFS 연결 정보)
│
├── data/                    # 로컬 데이터 (Git ignore)
│   ├── raw/                 # 원본 CSV
│   └── mock/                # P3 API 개발용 가짜 데이터
│
├── etl/                     # 데이터 파이프라인 
│   ├── lake_to_dwh/         # DWH 구축 (정제, 정규화)
│   ├── dwh_to_mart/         # Data Mart 구축 (집계, 비정규화)
│   └── common/              # (ETL 공통) Spark 세션 등
│
├── service/                 # API 및 대시보드 
│   ├── api/                 # (Backend) FastAPI
│   └── dashboard/           # (Frontend) Streamlit
│
├── ml/                      # 머신러닝 
│   ├── features/
│   ├── models/
│   ├── train.py
│   └── predict.py
│
├── shared/                  # 🔗 전역 공통 모듈 (로거, 설정 로더 등)
│
├── tests/                   # 🧪 테스트 코드
│   ├── test_etl/
│   └── test_service/
│
└── notebooks/               # 📓 실험실 (EDA, 모델 프로토타이핑)
    ├── eda/
    └── experiments/