# Financial Clustering Pipeline 사용법

이 문서는 `financial_clustering` 파이프라인을 실행하고 사용하는 방법에 대해 설명합니다.

## 1. 프로젝트 구조

- **`configs/`**: `base.yaml` 기본 설정과 각 실험별(`.yaml`) 설정 파일이 위치합니다.
- **`src/`**: 데이터 로딩, 전처리, 모델링 등 파이프라인의 핵심 로직이 모듈화되어 있습니다.
- **`outputs/`**: 모든 결과물이 실험별 하위 폴더에 저장됩니다.
- **`train.py`**: 전체 학습 파이프라인을 실행하는 메인 스크립트입니다.
- **`predict.py`**: 새로운 기업 데이터의 클러스터를 예측하는 스크립트입니다.
- **`visualize.py`**: 학습 완료 후 저장된 결과물을 시각화하는 스크립트입니다.
- **`benchmark_company.py`**: 특정 기업의 재무 포지션을 벤치마킹하는 시각화 스크립트입니다.
- **`generate_report.py`**: 특정 기업에 대한 구조화된 진단 리포트(.md)를 생성합니다.

## 2. 실행 순서

### 1단계: 모델 학습 (실험 선택)

- 클러스터링 모델을 학습시키려면, `--config` 인자로 원하는 실험 설정을 지정합니다.

```bash
python -m ml2.financial_clustering.train --config final_notebook_model
```

### 2단계: 결과 시각화

- 학습된 실험 결과물을 시각화하려면 `--experiment` 인자로 해당 실험을 지정합니다.

```bash
python -m ml2.financial_clustering.visualize --experiment final_notebook_model
```

### 3단계: 신규 데이터 예측

- 새로운 데이터가 담긴 CSV 파일을 예측하려면, 사용할 모델의 `--experiment`와 `[INPUT_CSV_PATH]`를 지정합니다.

```bash
python -m ml2.financial_clustering.predict [INPUT_CSV_PATH] --experiment final_notebook_model
```

### 4단계: 개별 기업 벤치마킹 차트 생성

- 특정 기업의 재무 포지션을 소속 군집 및 전체 평균과 비교하는 레이더 차트를 생성합니다.

```bash
python -m ml2.financial_clustering.benchmark_company [INPUT_CSV_PATH] --experiment final_notebook_model
```

### 5단계: 개별 기업 AI 진단 리포트 생성

- 특정 기업에 대한 요약 진단 리포트(마크다운 파일)를 생성합니다.
- **LLM 기반 요약 추가**: `--summarize` 인자를 추가하여 Gemini LLM을 통한 분석 요약을 리포트에 포함할 수 있습니다.
  - 이 옵션을 사용하면 마크다운 리포트 내에 AI 종합 분석 섹션이 추가되며, AI가 생성한 요약 내용만 별도의 `llm_summary_{회사ID}.txt` 파일로 `reports/[실험이름]/` 폴더에 저장됩니다.

```bash
python -m ml2.financial_clustering.generate_report [USER_INPUT_CSV_PATH] --experiment final_notebook_model --summarize
```

