# 상생나침반

서울시 공공데이터 기반 골목상권 AI 분석 플랫폼입니다. 예비창업자와 소상공인이 상권 매출, 점포 변화, 인구 흐름, 정책 지원 정보를 한 화면에서 확인하고 AI 상담을 받을 수 있도록 구성했습니다.

## 배포 URL

- 서비스: https://winwin-compass.vercel.app
- API 문서: https://winwin-compass-production.up.railway.app/docs
- API 헬스체크: https://winwin-compass-production.up.railway.app/health

## 활용 공공데이터

- 서울시 상권분석서비스: 추정매출, 점포, 생활인구, 직장인구
- 서울시 소상공인 정책자금 및 지원사업 정보
- 상권 데이터와 정책/입지 데이터를 결합한 창업 의사결정 지원

## AI 기술 활용

- GPT-4o 및 LangChain 기반 자연어 상담
- Text-to-SQL 기반 상권 데이터 질의
- pgvector 기반 정책 RAG 검색
- Prophet 시계열 매출 예측
- XGBoost 기반 폐업 위험 점수
- Web Speech API 기반 음성 입력

## 기술 스택

- Frontend: Next.js, TypeScript, Tailwind CSS, Recharts, Mapbox/Leaflet
- Backend: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis
- ML: Prophet, XGBoost, SHAP, scikit-learn
- Deploy: Vercel frontend, Railway backend

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

## 주요 기능

- AI 창업 상담 및 상권 비교
- 상권 지도와 위험도 마커
- 상권 리포트, 매출 트렌드, 예측 차트
- 맞춤형 소상공인 정책 추천
- DB/API 장애 환경에서도 데모용 샘플 데이터 폴백 제공
