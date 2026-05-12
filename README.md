# 상생나침반

서울시 공공데이터 기반 골목상권 AI 분석 플랫폼입니다. 예비창업자와 소상공인이 상권 매출, 점포 변화, 인구 흐름, 정책 지원 정보를 한 화면에서 확인하고 AI 상담을 받을 수 있도록 구성했습니다.

## 배포 URL

- 서비스: https://winwin-compass.vercel.app
- API 문서: https://winwin-compass-production.up.railway.app/docs
- API 헬스체크: https://winwin-compass-production.up.railway.app/health

## 주요 기능

- 폐업 위험 조기 감지, 원인 분석, 지원사업 연결, 마케팅 실행 지원으로 이어지는 위기 대응 흐름
- 자연어 기반 AI 창업 상담 및 상권 비교
- 서울 상권 지도, 위험도 마커, 필터 검색
- 상권 리포트, 매출 트렌드, 6~12개월 폐업 위험 예측 스코어
- XGBoost/규칙 기반 위험 점수와 SHAP 기반 주요 위험 요인 설명
- 폐업 위험도, 업종, 지역, 사용자 조건을 반영한 맞춤형 지원사업 추천
- 생성형 AI 기반 SNS 홍보문, 리뷰 답변, 전단 문구, 메뉴 소개 문구 생성
- DB/API 장애 시에도 시연 가능한 데모 샘플 폴백

## 활용 공공데이터

- 서울시 상권분석서비스: 추정매출, 점포, 생활인구, 직장인구
- 서울시 소상공인 정책자금 및 지원사업 정보
- 상권 데이터와 정책/입지 데이터를 결합한 창업 의사결정 지원

## 기술 스택

- Frontend: Next.js, TypeScript, Tailwind CSS, Recharts, Mapbox/Leaflet
- Backend: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis
- AI/ML: GPT-4o, LangChain, pgvector RAG, Prophet, XGBoost, SHAP
- Deploy: Vercel frontend, Railway backend

## 프로젝트 구조

```text
frontend/        Next.js App Router UI
backend/         FastAPI API, AI, data, ML pipeline
docker/          Local PostgreSQL initialization
scripts/         Demo automation scripts
.github/         GitHub Actions workflows
```

세부 구조는 각 디렉토리의 `README.md`를 참고하세요.

## 서비스 흐름

상생나침반은 폐업 위험을 조기에 감지하고, 위험 원인을 설명하며, 맞춤형 지원사업을 연결하고, 마케팅 실행까지 도와주는 소상공인 위기 대응 AI 코파일럿입니다.

1. 폐업 위험 예측 스코어: 매출 감소, 유동인구 감소, 주변 폐업 증가, 상권 생존율 하락 등 위험 신호를 종합해 0~100점으로 제시합니다.
2. 원인 분석: SHAP 기반 Explainable AI로 동일 업종 경쟁 과밀, 점심 유동인구 감소, 20대 방문 감소 등 주요 요인을 자연어로 설명합니다.
3. 지원사업 매칭: 위험도, 업종, 지역, 사용자 조건을 바탕으로 정부·서울시·자치구·신용보증기관·소상공인 지원사업을 추천합니다.
4. 마케팅 실행 지원: 위험 진단에서 끝나지 않고 SNS 홍보문, 리뷰 답변, 전단 문구, 메뉴 소개 문구 등 매출 회복 행동까지 지원합니다.

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

## 데모 데이터와 스모크 테스트

```bash
cd backend
python scripts/seed_demo_data.py
bash scripts/smoke_test.sh http://localhost:8000
bash scripts/smoke_test.sh https://winwin-compass-production.up.railway.app
```

데모 데이터는 2026년 1분기 기준으로 종로3가, 홍대입구, 불광동 상권을 안정적으로 제공합니다.

## 배포

- Frontend: `cd frontend && vercel --prod --yes`
- Backend: `railway up backend --path-as-root --service winwin-compass --detach`

환경변수와 배포 URL은 `DEPLOYMENT.md`, GitHub Secrets는 `SECRETS_GUIDE.md`를 확인하세요.
