# 상생나침반 (Winwin Compass)

> 1인 창업자와 소상공인을 위한 AI 지역상권 의사결정 코파일럿

상생나침반은 서울시 공공데이터를 기반으로 폐업 위험을 조기에 감지하고, 위험 원인을 설명하며, 맞춤형 지원사업을 연결하고, 마케팅 실행까지 돕는 소상공인 위기 대응 AI 서비스입니다.

## 라이브 서비스

| 구분 | URL |
|---|---|
| 서비스 | https://winwin-compass.vercel.app |
| API 문서 | https://winwin-compass-production.up.railway.app/docs |
| API 헬스체크 | https://winwin-compass-production.up.railway.app/health |
| SUS 테스트 | https://winwin-compass.vercel.app/ux-test |

## 핵심 기능

- 폐업 위험 예측 스코어: 매출 감소, 유동인구 변화, 주변 폐업 증가, 상권 생존율 하락 등을 0~100점으로 제시
- 원인 분석: XGBoost/SHAP 기반 주요 위험 요인을 자연어로 설명
- 정책 매칭: 위험도, 업종, 지역, 사용자 조건을 바탕으로 정부·서울시·자치구·보증기관 지원사업 추천
- AI 상담: 자연어 질문을 Text-to-SQL, 리포트 생성, 정책 RAG, 비교 분석으로 처리
- 마케팅 자동화: SNS 홍보문, 리뷰 답변, 전단 문구, 메뉴 소개 문구 생성
- 접근성: Web Speech API 음성 입력과 디지털 약자 모드 지원

## 활용 공공데이터

서울 열린데이터광장 상권분석서비스를 중심으로 산업·경제, 인구, 입지, 정책 데이터를 결합합니다.

- 상권 추정매출
- 상권 점포 및 개·폐업률
- 생활인구 및 직장인구
- 소상공인 정책자금 및 지원사업 정보
- 데모 안정화를 위한 2026년 1분기 기준 샘플 데이터 폴백

## AI 기술 스택

- GPT-4o: 자연어 상담, 리포트 생성, 정책 설명
- LangChain Text-to-SQL: 상권 데이터 질의 변환
- pgvector RAG: 정책/지원사업 검색과 매칭
- Prophet: 향후 12개월 매출 예측
- XGBoost + SHAP: 폐업 위험 점수와 원인 설명
- Web Speech API: 브라우저 기반 음성 입력

## 기술 스택

- Frontend: Next.js 14, TypeScript, Tailwind CSS, Mapbox/Leaflet, Recharts
- Backend: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis
- ML/Data: Prophet, XGBoost, pandas, scikit-learn
- Deploy: Vercel, Railway, GitHub Actions CI/CD

## 프로젝트 구조

```text
frontend/        Next.js App Router UI
backend/         FastAPI API, AI, data pipeline, ML pipeline
backend/scripts/ Demo seed, smoke test, evaluation, screenshot tools
docker/          Local PostgreSQL initialization
.github/         GitHub Actions workflows
```

세부 구조는 각 디렉토리의 `README.md`를 참고하세요.

## 로컬 실행

```bash
cp .env.example .env
docker-compose up -d

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

## 검증 자료

```bash
cd backend
python scripts/seed_demo_data.py
bash scripts/smoke_test.sh https://winwin-compass-production.up.railway.app
python scripts/evaluate_accuracy.py \
  --url https://winwin-compass-production.up.railway.app \
  --output EVAL_REPORT.md
node scripts/capture_screenshots.js
```

- AI 응답 평가: `backend/EVAL_REPORT.md`
- 제출 체크리스트: `SUBMISSION_CHECKLIST.md`
- 데모 시나리오: `DEMO_SCENARIOS.md`
- 화면 캡처: `screenshots/`
