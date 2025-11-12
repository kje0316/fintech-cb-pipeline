# GEMINI.md

## 프로젝트 개요

이 프로젝트는 기업 신용 정보에 대한 재무 데이터 분석입니다. 주요 목표는 합성 신용 등급 정보 데이터 세트를 기반으로 기업의 재무 건전성을 분석하는 것입니다. 분석은 Jupyter 노트북과 Python 데이터 과학 스택(pandas, numpy, matplotlib, seaborn)을 사용하여 수행됩니다.

이 데이터 세트의 주요 과제는 각 회사에 대한 고유 식별자가 없다는 것입니다. 모든 행을 다른 회사로 고려하여, 처음 데이터를 불러올 때 고유한 ID를 부여합니다. 

## 빌드 및 실행

분석을 실행하려면 필요한 라이브러리가 설치된 Python 환경이 필요합니다. 이 프로젝트는 `venv` 디렉토리에 있는 가상 환경을 사용합니다.

1.  **가상 환경 활성화:**
    ```bash
    source venv/bin/activate
    ```

2.  **의존성 설치:**
    필요한 라이브러리는 `requirements.txt` 파일에 나열되어 있습니다.
    ```bash
    pip install -r requirements.txt
    ```

3.  **.env 파일 설정:**
    데이터베이스 접속 정보 및 기타 환경 변수를 `.env` 파일에 설정합니다.
    ```
    DB_USER="your_db_user"
    DB_PASSWORD="your_db_password"
    DB_HOST="localhost"
    DB_PORT="5432"
    DB_NAME="your_db_name"
    ```

4.  **ETL 파이프라인 실행:**
    데이터 추출, 정제, 변환 및 PostgreSQL 적재를 위한 ETL 파이프라인을 실행합니다.
    ```bash
    python run_pipe.py
    ```

    PostgreSQL에 적재한 테이블을 불러옵니다. (파일 내 table_name 설정 필요)
    ```bash
    python scripts/import_type.py
    ```

## 개발 규칙

*   **데이터:** 
*   데이터는 `data` 디렉토리에 있습니다. 
*   기본 데이터 세트는 `data/기업신용평가정보_합성데이터.csv`이며, `data/202109_기업CB.csv`는 컬럼명 참조용으로 사용됩니다.

## 주요 파일

*   `.env`: 데이터베이스 접속 정보 등 환경 변수를 저장합니다.
*   `scripts/build_dw.py`: 차원 테이블과 사실 테이블을 생성하는 역할을 합니다. 
*   `scripts/extract_data.py`: 원본 데이터를 추출하고 컬럼명을 통일하는 역할을 합니다.
*   `scripts/cleansing.py`: 추출된 데이터를 정제하고 데이터 웨어하우스 스키마에 맞게 변환합니다.
*   `scripts/load_to_postgres.py`: 변환된 데이터를 PostgreSQL 데이터베이스에 적재하고 불러오는 함수를 정의합니다.
*   `run_pipe.py`: ETL 파이프라인의 전체 흐름을 조정하는 메인 스크립트입니다.
*   `data/기업신용평가정보_합성데이터.csv`: 분석에 사용되는 기본 데이터 세트입니다.
*   `data/202109_기업CB.csv`: 컬럼명 참조용