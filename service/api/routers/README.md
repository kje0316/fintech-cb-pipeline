# 부도 예측 API 라우터

## 📌 최종 버전 (v2.0.0)

**엑셀 업로드 기반 부도예측**
- 37개 입력 컬럼 → 70개 파생 피처 생성 → 부도 예측
- MLflow Registry의 Production 모델 사용 (CatBoost v4, AUC 0.7466)
- 모델 캐싱으로 100배 성능 향상

---

## 🎯 API 엔드포인트

### 1. 부도 예측 (엑셀 업로드)
```
POST /api/v1/predict/upload/excel
```

**입력**:
- 엑셀 파일 (.xlsx, .xls)
- 37개 필수 컬럼 포함
- '데이터입력' 또는 '샘플데이터' 시트 사용

**출력**:
```json
{
  "default_probability": 0.0018,
  "default_prediction": 0,
  "risk_level": "Low",
  "confidence": 1.0,
  "shap_values": {
    "base_value": 0.5,
    "expected_value": 0.0018,
    "contributions": [...]
  },
  "clustering_features": {...},
  "n_features": 70,
  "model_version": "v4",
  "model_type": "CATBOOST"
}
```

**사용 예시**:
```bash
curl -X POST "http://localhost:8000/api/v1/predict/upload/excel" \
     -F "file=@재무데이터.xlsx"
```

---

### 2. 템플릿 다운로드
```
GET /api/v1/predict/download/excel/template
```

37개 필수 컬럼이 포함된 엑셀 템플릿 파일을 제공합니다.

**사용 예시**:
```bash
curl -O "http://localhost:8000/api/v1/predict/download/excel/template"
```

---

### 3. 모델 정보 조회
```
GET /api/v1/predict/admin/model-info
```

현재 로드된 모델의 버전, 타입, 성능 정보를 조회합니다.

**응답 예시**:
```json
{
  "status": "success",
  "model_info": {
    "version": "v4",
    "type": "CATBOOST",
    "auc_roc": 0.7466490658001624,
    "n_features": 63,
    "source": "mlflow_registry"
  }
}
```

---

### 4. 모델 갱신 (관리자)
```
POST /api/v1/predict/admin/reload-model
```

MLflow Registry에서 새 모델을 Production으로 승격한 후, API 서버를 재시작하지 않고 새 모델을 적용합니다.

**사용 예시**:
```bash
# 1. 새 모델 학습 및 Production 승격
uv run python ml/training/train_predict.py
# MLflow UI에서 best 모델을 Production으로 승격

# 2. API 모델 갱신 (재시작 없이)
curl -X POST http://localhost:8000/api/v1/predict/admin/reload-model
```

**응답 예시**:
```json
{
  "status": "success",
  "message": "모델이 성공적으로 갱신되었습니다",
  "old_model": {
    "version": "v4",
    "type": "CATBOOST",
    "auc": 0.7466
  },
  "new_model": {
    "version": "v5",
    "type": "LIGHTGBM",
    "auc": 0.7520
  },
  "changed": true
}
```

---

### 5. 헬스 체크
```
GET /api/v1/predict/health
```

API 서버 상태를 확인합니다.

**응답**:
```json
{
  "status": "healthy",
  "service": "default-prediction-v2",
  "version": "2.0.0"
}
```

---

## 📊 37개 입력 컬럼 (필수)

### 재무상태표 (12개)
- `fn1_13`: 자산총계(당기)
- `fn1_1`: 유동자산(당기)
- `fn1_4`: 재고자산
- `fn1_11`: 매출채권
- `fn1_19`: 부채총계
- `fn1_24`: 자본총계
- `fn1_14`: 유동부채
- `fn1_15`: 단기차입금
- `fn1_16`: 차입금
- `fn1_유형자산`: 유형자산(당기)
- `fn1_매입채무`: 매입채무
- `fn3_적립금`: 적립금

### 손익계산서 (8개)
- `fn2_1`: 매출액(당기)
- `fn2_2`: 매출원가
- `fn2_2_1`: 매출총이익
- `fn2_3`: 판매비와관리비
- `fn2_5`: 영업이익 당기
- `fn2_5_1`: 영업이익 전기
- `fn2_10`: 당기순이익 당기
- `fn2_10_1`: 당기순이익 전기

### 현금흐름/기타 (6개)
- `fn3_1`: 현금흐름
- `fn3_2`: 영업활동현금흐름
- `fn3_7`: EBIT
- `fn3_8`: EBITDA(당기)
- `fn3_11_1`: 순차입금
- `fn2_4`: 이자비용 (선택적)

### 전년도 데이터 (4개)
- `fn1_13_전기`: 자산총계(전기)
- `fn2_1_전기`: 매출액(전기)
- `fn1_1_전기`: 유동자산(전기)
- `fn3_8_전기`: EBITDA(전기)

### 기업정보 (2개)
- `empe_cnt`: 종업원수
- `wg_gb`: 외감여부

### 연체정보 (7개)
- `da0d00029`: 연체과목수(1년내발생)
- `da0d00026`: 연체과목수(1년내유지)
- `da0d00035_1`: 최장연체일수(1년)
- `da0d00035_2`: 최장연체일수(기타)
- `da0d00033_1`: 최장연체일수(3개월)
- `db0d00006`: 부도/화의/워크아웃정보
- `d2b000002`: 연체정보

---

## 🚀 성능 최적화

### 모델 캐싱
- 매 요청마다 모델을 로드하는 대신, 메모리에 캐싱하여 재사용
- 첫 요청: 1초 (모델 로드)
- 이후 요청: 0.01초 (캐시 사용)
- **100배 성능 향상!**

### 자동 모델 갱신
- Production 모델 변경 시 `/admin/reload-model` 호출
- 서버 재시작 없이 새 모델 적용
- 무중단 모델 업데이트

---

## 🔧 MLOps 통합

### MLflow Registry
- Production 스테이지 모델 자동 로드
- 모델 버전 관리 및 추적
- 실험 메트릭 기록

### 현재 모델
- **타입**: CatBoost
- **버전**: v4
- **AUC-ROC**: 0.7466
- **피처**: 70개 (37개 입력 → 파생 변수 생성)

---

## 📝 제거된 구버전 API

다음 API들은 제거되었습니다:
- `POST /company` - 구버전 예측 API
- `GET /company/{business_number}` - 구버전 조회 API
- `POST /quick` - 간단 예측 API
- `POST /user-friendly` - 사용자 친화 API
- `POST /excel` - JSON 방식 엑셀 API

**최종 버전은 `POST /upload/excel`만 사용합니다.**

---

## 🔗 관련 문서

- [MLflow UI](http://localhost:5000) - 실험 추적 및 모델 레지스트리
- [API Docs](http://localhost:8000/docs) - FastAPI 자동 생성 문서
- [Next.js Dashboard](http://localhost:3000) - 프론트엔드 대시보드
