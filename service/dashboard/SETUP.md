# Dashboard Setup Guide

## 구현 완료 사항

✅ Next.js 14 + TypeScript 프로젝트 구조 생성
✅ 5개 대시보드 컴포넌트 구현
✅ FastAPI 대시보드 엔드포인트 5개 추가
✅ CORS 설정 완료
✅ npm 의존성 설치 완료
✅ TypeScript 빌드 검증 완료

## 실행 단계

### 1. 데이터 마트 적재 확인

대시보드를 실행하기 전에 데이터 마트가 적재되어 있는지 확인하세요:

```bash
cd /Users/kje/coding/project/fintech-cb-pipeline

# 모든 마트 적재
python etl/dwh_to_mart/run_all_marts.py
```

필요한 마트 테이블:
- `marts.mart_market_kpi_monthly` (12 rows)
- `marts.mart_industry_default_trend` (228 rows = 19 industries × 12 months)
- `marts.mart_industry_risk_ranking` (19 rows)

### 2. FastAPI 백엔드 실행

새 터미널에서:

```bash
cd /Users/kje/coding/project/fintech-cb-pipeline/service/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 문서 확인: http://localhost:8000/docs

대시보드 엔드포인트 확인:
- http://localhost:8000/api/v1/dashboard/kpi
- http://localhost:8000/api/v1/dashboard/top-industries-trend
- http://localhost:8000/api/v1/dashboard/industry-composition
- http://localhost:8000/api/v1/dashboard/heatmap
- http://localhost:8000/api/v1/dashboard/industry-default-rates

### 3. Next.js 대시보드 실행

새 터미널에서:

```bash
cd /Users/kje/coding/project/fintech-cb-pipeline/service/dashboard
npm run dev
```

브라우저에서 http://localhost:3000 접속

## 대시보드 구성

### 레이아웃 (상단 → 하단)

1. **KPI 카드 4개** (한 행에 4개)
   - 총 기업 수
   - 평균 신용등급
   - 부도율
   - 고위험 기업 비율

2. **라인 차트** (전체 너비)
   - 상위 5개 위험 업종의 월별 부도율 추세

3. **파이 차트** (전체 너비, 좌우 2분할)
   - 좌측: 파이 차트 (상위 10개 업종 구성비)
   - 우측: 상위 5개 업종 설명

4. **히트맵** (전체 너비)
   - 19개 대분류 업종 × 12개월
   - 부도율을 색상으로 표시

5. **막대 그래프** (전체 너비)
   - 대분류 업종별 부도율 (부도율 높은 순)

## 기술 스택

- **Frontend**: Next.js 14, React 18, TypeScript 5
- **Styling**: Tailwind CSS 3.4
- **Charts**: Recharts 2.12
- **Data Fetching**: Axios 1.6
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL

## 디렉토리 구조

```
service/dashboard/
├── app/
│   ├── layout.tsx          # 헤더/푸터 레이아웃
│   ├── page.tsx            # 메인 대시보드 (클라이언트 컴포넌트)
│   └── globals.css         # Tailwind CSS
├── components/dashboard/
│   ├── KPICard.tsx         # KPI 지표 카드
│   ├── DefaultTrendChart.tsx    # 라인 차트 (Recharts)
│   ├── IndustryPieChart.tsx     # 파이 차트 (Recharts)
│   ├── DefaultHeatmap.tsx       # 히트맵 (Custom Table)
│   └── IndustryBarChart.tsx     # 막대 그래프 (Recharts)
├── lib/
│   ├── api.ts              # FastAPI 호출 함수 (5개)
│   └── types.ts            # TypeScript 타입 정의
├── package.json            # 의존성 (464 packages)
├── tsconfig.json           # TypeScript 설정
├── tailwind.config.ts      # Tailwind 설정
└── next.config.js          # Next.js 설정 (API 프록시)
```

## FastAPI 변경사항

### 새로 추가된 파일

**`service/api/routers/dashboard.py`**
- 5개 대시보드 엔드포인트 구현
- PostgreSQL 마트 테이블 쿼리

### 수정된 파일

**`service/api/main.py`**
- CORS 미들웨어 추가 (Next.js 포트 3000 허용)
- dashboard 라우터 등록

## 문제 해결

### 1. API 연결 오류 (CORS)
→ `service/api/main.py`에서 CORS 설정 확인
→ FastAPI 서버가 8000번 포트에서 실행 중인지 확인

### 2. 데이터가 없음
→ 마트 적재 확인: `python etl/dwh_to_mart/run_all_marts.py`
→ PostgreSQL 연결 확인: `psql -h localhost -U [username] -d fintech_cb_pipeline`

### 3. 빌드 오류
→ TypeScript 오류 확인: `npm run build`
→ 의존성 재설치: `rm -rf node_modules package-lock.json && npm install`

### 4. 차트가 렌더링되지 않음
→ 브라우저 콘솔 확인 (F12)
→ API 응답 데이터 확인 (Network 탭)

## 추가 개발 아이디어

- [ ] 로딩 스피너 개선
- [ ] 에러 바운더리 추가
- [ ] 날짜 범위 필터
- [ ] 업종 선택 필터
- [ ] 데이터 내보내기 (CSV)
- [ ] 반응형 디자인 개선
- [ ] 다크 모드 지원
- [ ] 실시간 데이터 업데이트

## 참고 자료

- Next.js Docs: https://nextjs.org/docs
- Recharts: https://recharts.org/
- Tailwind CSS: https://tailwindcss.com/
- FastAPI: https://fastapi.tiangolo.com/
