SYSTEM_PROMPT = """
당신은 상생나침반의 서울시 골목상권 전문 AI 컨설턴트입니다.
소상공인과 예비창업자가 올바른 창업 결정을 내릴 수 있도록
공공데이터 기반의 정확한 분석과 따뜻한 조언을 제공합니다.

사용 가능한 데이터:
- 서울시 상권별 추정매출 (분기별)
- 상권별 점포수, 개업률, 폐업률
- 상권별 생활인구, 직장인구 (연령대별)
- 소상공인 지원 정책 목록

답변 원칙:
1. 항상 데이터 근거를 명시하세요 ("2026년 1분기 기준")
2. 위험 요소는 솔직하게, 기회 요소는 구체적으로
3. 전문 용어는 쉽게 풀어서 설명
4. 답변 마지막에 관련 지원 정책 1~2개 안내
"""

TEXT_TO_SQL_PROMPT = """
다음 DB 스키마를 참고하여 사용자 질문을 SQL로 변환하세요.

스키마:
{schema}

규칙:
- 항상 SELECT만 사용 (INSERT/UPDATE/DELETE 금지)
- area_cd, area_nm으로 상권 필터링
- year_quarter는 최신 데이터 우선 (DESC LIMIT)
- 결과는 최대 20행
- 집계 시 AVG, SUM 사용

질문: {question}
SQL:
"""

REPORT_PROMPT = """
다음 상권 데이터를 바탕으로 창업자를 위한 분석 리포트를 작성하세요.

상권명: {area_nm}
매출 데이터: {sales_data}
점포 데이터: {store_data}
인구 데이터: {population_data}
위기 점수: {risk_score}/100

리포트 형식 (마크다운):
## 📊 상권 종합 평가
(3줄 요약)

## 💰 매출 현황
(월평균 매출, 피크 시간대, 요일별 특성)

## 👥 유동인구 분석
(주요 연령대, 성별, 직장인/거주자 비율)

## ⚠️ 위험 신호
(폐업률, 경쟁 심화, 매출 감소 추이)

## ✅ 기회 요인
(성장 업종, 틈새 시간대, 인구 특성 활용)

## 🎯 추천 업종
(데이터 근거와 함께 3개)
"""

# TEXT_TO_SQL_PROMPT 의 {schema} 자리에 삽입되는 DB 스키마 설명
DB_SCHEMA = """
1. commercial_areas — 상권 기본 정보
   area_cd   VARCHAR(20) PK   상권코드
   area_nm   VARCHAR(100)     상권명
   gu_nm     VARCHAR(50)      자치구명 (예: 종로구, 마포구)
   area_type VARCHAR(20)      골목상권 | 전통시장 | 발달상권 | 관광특구
   geom_lat  FLOAT            위도
   geom_lng  FLOAT            경도

2. sales_data — 분기별 추정매출 (업종별)
   area_cd          VARCHAR(20) FK → commercial_areas
   industry_cd      VARCHAR(20)   업종코드 (예: CS100001)
   industry_nm      VARCHAR(100)  업종명 (예: 한식음식점)
   year_quarter     VARCHAR(7)    분기 (예: 2024Q3)
   monthly_sales_avg BIGINT       월평균 매출(원)
   daily_sales_avg   BIGINT       일평균 매출(원)
   weekday_sales     BIGINT       평일 매출(원)
   weekend_sales     BIGINT       주말 매출(원)
   time_slot_sales   JSONB        시간대별 매출 {"00-06":..,"06-11":..,"11-14":..,"14-17":..,"17-21":..,"21-24":..}

3. store_counts — 분기별 점포 현황 (업종별)
   area_cd      VARCHAR(20) FK
   year_quarter VARCHAR(7)
   industry_cd  VARCHAR(20)
   store_count  INTEGER    점포 수
   open_rate    FLOAT      개업률(%)
   close_rate   FLOAT      폐업률(%)

4. population_data — 분기별 생활인구
   area_cd          VARCHAR(20) FK
   year_quarter     VARCHAR(7)
   total_population INTEGER    총 생활인구 수
   age_10s          INTEGER    10대 인구
   age_20s          INTEGER    20대 인구
   age_30s          INTEGER    30대 인구
   age_40s          INTEGER    40대 인구
   age_50s          INTEGER    50대 인구
   age_60s          INTEGER    60대 이상 인구
   male_ratio       FLOAT      남성 비율 (0~1)
   female_ratio     FLOAT      여성 비율 (0~1)

5. worker_population — 분기별 직장인구
   area_cd        VARCHAR(20) FK
   year_quarter   VARCHAR(7)
   total_workers  INTEGER    총 직장인구
   age_20s        INTEGER    20대 직장인
   age_30s        INTEGER    30대 직장인
   age_40s        INTEGER    40대 직장인
   age_50s        INTEGER    50대 직장인

6. policy_programs — 소상공인 지원 정책
   program_nm VARCHAR(200)  사업명
   category   VARCHAR(20)   융자 | 보조금 | 컨설팅 | 교육
   target     TEXT          지원 대상
   budget_min BIGINT        최소 지원금(원)
   budget_max BIGINT        최대 지원금(원)
   apply_start DATE         신청 시작일
   apply_end   DATE         신청 마감일
   source_url  VARCHAR(500) 상세 링크
"""
