# Fintech Dashboard

Next.js + TypeScript 기반 중소기업 재무 건전성 분석 대시보드

## 기술 스택

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Data Fetching**: Axios
- **Backend**: FastAPI (service/api/)

## 대시보드 구성

### 1. KPI 카드 (4개)
- 총 기업 수
- 평균 신용등급
- 부도율
- 고위험 기업 비율

### 2. 월별 부도율 추세 (라인 차트)
- 상위 5개 고위험 업종의 월별 부도율 변화 추이

### 3. 업종 구성비 (파이 차트)
- 대분류 업종별 기업 수 분포 (상위 10개)
- 업종별 설명 및 비율 표시

### 4. 월별 × 업종별 부도율 히트맵
- 19개 대분류 업종 × 12개월
- 색상 그라데이션으로 부도율 시각화

### 5. 업종별 부도율 (막대 그래프)
- 대분류 업종별 평균 부도율
- 총 기업 수 정보 포함

## 실행 방법

### 1. 의존성 설치
```bash
cd service/dashboard
npm install
```

### 2. FastAPI 백엔드 실행 (필수)
```bash
# 별도 터미널에서
cd service/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Next.js 개발 서버 실행
```bash
cd service/dashboard
npm run dev
```

브라우저에서 http://localhost:3000 접속

## 프로젝트 구조

```
service/dashboard/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # 루트 레이아웃 (헤더/푸터)
│   ├── page.tsx           # 메인 대시보드 페이지
│   └── globals.css        # 전역 스타일
├── components/
│   └── dashboard/         # 대시보드 컴포넌트
│       ├── KPICard.tsx               # KPI 지표 카드
│       ├── DefaultTrendChart.tsx     # 라인 차트
│       ├── IndustryPieChart.tsx      # 파이 차트
│       ├── DefaultHeatmap.tsx        # 히트맵
│       └── IndustryBarChart.tsx      # 막대 그래프
├── lib/
│   ├── api.ts             # FastAPI 연동 함수
│   └── types.ts           # TypeScript 타입 정의
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## API 엔드포인트

FastAPI 백엔드에서 제공하는 5개 엔드포인트:

1. `GET /api/v1/dashboard/kpi` - KPI 데이터
2. `GET /api/v1/dashboard/top-industries-trend` - 상위 5개 업종 추세
3. `GET /api/v1/dashboard/industry-composition` - 업종 구성비
4. `GET /api/v1/dashboard/heatmap` - 히트맵 데이터
5. `GET /api/v1/dashboard/industry-default-rates` - 업종별 부도율

## 데이터 마트

대시보드는 다음 PostgreSQL 마트 테이블을 사용합니다:

- `marts.mart_market_kpi_monthly` - 월별 시장 KPI
- `marts.mart_industry_default_trend` - 업종별 월별 부도 추세
- `marts.mart_industry_risk_ranking` - 업종별 리스크 랭킹
- `dwh.dim_major_category` - 대분류 업종 메타데이터

## 환경 변수 (선택사항)

`.env.local` 파일에서 API URL 설정 가능:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 빌드 및 배포

### 개발 빌드
```bash
npm run dev
```

### 프로덕션 빌드
```bash
npm run build
npm run start
```

## 문제 해결

### CORS 오류
FastAPI에서 CORS가 설정되어 있습니다 (`service/api/main.py`). 포트를 변경한 경우 `allow_origins`를 수정하세요.

### API 연결 오류
1. FastAPI 서버가 실행 중인지 확인: http://localhost:8000/docs
2. 데이터 마트가 적재되었는지 확인:
   ```bash
   python etl/dwh_to_mart/run_all_marts.py
   ```

### 타입 오류
TypeScript 컴파일 오류 시:
```bash
npm run build
```

## 향후 개선사항

- [ ] 날짜 범위 필터 추가
- [ ] 업종 선택 기능
- [ ] 데이터 내보내기 (CSV/Excel)
- [ ] 실시간 업데이트 (WebSocket)
- [ ] 반응형 모바일 최적화
