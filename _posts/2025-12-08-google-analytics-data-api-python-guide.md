---
layout: post
title: "Python으로 Google Analytics Data API 활용하기 - 완벽 가이드"
date: 2025-12-08 14:00:00 +0900
categories: [Analytics, Python]
tags: [google-analytics, ga4, python, data-api, analytics, reporting]
image: "/assets/img/posts/2025-12-08-google-analytics-data-api-python-guide.webp"
---

## 1. Google Analytics Data API란?

### 1.1 개요

Google Analytics Data API (GA4 Data API)는 **Google Analytics 4 속성의 데이터를 프로그래밍 방식으로 조회**할 수 있는 공식 API입니다. 웹 UI에서 수동으로 리포트를 확인하는 대신, Python 코드로 데이터를 자동으로 수집하고 분석할 수 있습니다.

```python
# 간단한 예시
from google.analytics.data_v1beta import BetaAnalyticsDataClient

client = BetaAnalyticsDataClient(credentials=credentials)
response = client.run_report(request)

# 이제 Python에서 GA4 데이터를 자유롭게 분석!
for row in response.rows:
    print(f"페이지: {row.dimension_values[0].value}")
```

**중요:** 이 API는 **GA4 (Google Analytics 4) 전용**입니다. 구버전 Universal Analytics(UA)와는 호환되지 않습니다.

### 1.2 왜 GA4 Data API를 사용해야 할까?

**GA4 웹 UI의 한계:**

```yaml
문제점:
  - 수동 작업: 매일/매주 리포트를 수동으로 확인해야 함
  - 제한된 커스터마이징: UI에서 제공하는 리포트만 사용 가능
  - 데이터 결합 어려움: 다른 데이터 소스와 통합 불가
  - 자동화 불가: 알림, 대시보드 자동 업데이트 어려움
```

**GA4 Data API의 장점:**

```python
# 1. 자동화 - 매일 아침 8시 자동 리포트
import schedule

def daily_report():
    response = client.run_report(request)
    send_email(create_report(response))

schedule.every().day.at("08:00").do(daily_report)


# 2. 커스텀 대시보드 - Streamlit, Dash 등
import streamlit as st

data = get_ga4_data()
st.line_chart(data)  # 실시간 대시보드


# 3. 데이터 통합 - 매출 데이터 + GA4 트래픽
sales_data = get_sales_from_db()
traffic_data = get_ga4_traffic()
merged = pd.merge(sales_data, traffic_data, on='date')


# 4. 머신러닝 - 트래픽 예측, 이상 감지
from sklearn.ensemble import RandomForestRegressor

model = RandomForestRegressor()
model.fit(X_train, y_train)  # GA4 데이터로 학습
predictions = model.predict(X_test)
```

### 1.3 실제 사용 사례

```yaml
마케팅 자동화:
  - 광고 성과 일일 리포트 (이메일/슬랙 전송)
  - 전환율 하락 시 자동 알림
  - 캠페인별 ROI 대시보드

비즈니스 인텔리전스:
  - 실시간 매출 모니터링 대시보드
  - 주간/월간 경영진 리포트 자동화
  - 사용자 행동 패턴 분석

개발/운영:
  - 페이지 성능 모니터링 (로딩 속도, 이탈률)
  - A/B 테스트 결과 자동 분석
  - 에러 트래킹 및 알림

데이터 과학:
  - 사용자 세그멘테이션 (클러스터링)
  - 이탈 예측 모델
  - 추천 시스템 (다음 방문 페이지 예측)
```

### 1.4 주요 기능

```python
# ============================================
# 1. runReport - 기본 리포트 조회
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='2025-12-01', end_date='2025-12-08')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')]
)
response = client.run_report(request)


# ============================================
# 2. runRealtimeReport - 실시간 데이터 (최근 30분)
# ============================================
realtime_request = RunRealtimeReportRequest(
    property=f'properties/{PROPERTY_ID}',
    dimensions=[Dimension(name='country')],
    metrics=[Metric(name='activeUsers')]
)
realtime_response = client.run_realtime_report(realtime_request)


# ============================================
# 3. batchRunReports - 여러 리포트 한 번에
# ============================================
batch_request = BatchRunReportsRequest(
    property=f'properties/{PROPERTY_ID}',
    requests=[
        request1,  # 페이지뷰 리포트
        request2,  # 사용자 리포트
        request3   # 전환 리포트
    ]
)
batch_response = client.batch_run_reports(batch_request)


# ============================================
# 4. runPivotReport - 피벗 테이블 (고급)
# ============================================
pivot_request = RunPivotReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    pivots=[
        Pivot(
            field_names=['country'],
            limit=10
        )
    ],
    dimensions=[Dimension(name='date'), Dimension(name='country')],
    metrics=[Metric(name='sessions')]
)


# ============================================
# 5. getMetadata - 사용 가능한 dimensions/metrics 확인
# ============================================
metadata_request = GetMetadataRequest(
    name=f'properties/{PROPERTY_ID}/metadata'
)
metadata = client.get_metadata(metadata_request)

for dimension in metadata.dimensions:
    print(f"{dimension.api_name}: {dimension.ui_name}")
```

---

## 2. 환경 설정 - GCP부터 Python까지

### 2.1 Google Cloud Platform (GCP) 프로젝트 설정

#### Step 1: GCP 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 상단 프로젝트 선택 → **새 프로젝트** 클릭
3. 프로젝트 이름 입력 (예: `my-ga4-analytics`)
4. **만들기** 클릭

#### Step 2: Google Analytics Data API 활성화

```bash
# 방법 1: 웹 콘솔에서
# 1. 좌측 메뉴 → API 및 서비스 → 라이브러리
# 2. "Google Analytics Data API" 검색
# 3. "사용 설정" 클릭

# 방법 2: gcloud CLI로 (터미널)
gcloud services enable analyticsdata.googleapis.com
```

#### Step 3: 서비스 계정 생성

```bash
# 1. 웹 콘솔: API 및 서비스 → 사용자 인증 정보
# 2. "+ 사용자 인증 정보 만들기" → "서비스 계정"
# 3. 서비스 계정 세부정보 입력:
#    - 이름: ga4-data-api-service
#    - 설명: GA4 Data API 접근용 서비스 계정
# 4. "만들기 및 계속하기" 클릭
# 5. 역할 선택: "뷰어" (읽기 전용)
# 6. "완료" 클릭

# 또는 gcloud CLI로:
gcloud iam service-accounts create ga4-data-api-service \
    --display-name="GA4 Data API Service Account"
```

#### Step 4: JSON 키 파일 다운로드

```bash
# 웹 콘솔:
# 1. 생성된 서비스 계정 클릭
# 2. "키" 탭 → "키 추가" → "새 키 만들기"
# 3. 키 유형: JSON 선택
# 4. "만들기" → 자동으로 파일 다운로드됨

# 다운로드된 파일 이름 변경 및 이동
mv ~/Downloads/my-ga4-analytics-abc123.json ~/.config/gcp/ga4-service-account.json
chmod 600 ~/.config/gcp/ga4-service-account.json  # 권한 제한
```

**다운로드된 JSON 파일 구조:**

```json
{
  "type": "service_account",
  "project_id": "my-ga4-analytics",
  "private_key_id": "abc123def456...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...",
  "client_email": "ga4-data-api-service@my-ga4-analytics.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

### 2.2 Google Analytics 4 속성 설정

#### Step 1: GA4 Property ID 확인

```bash
# 1. Google Analytics (https://analytics.google.com/) 접속
# 2. 좌측 하단 "관리" (⚙️) 클릭
# 3. "속성 설정" 클릭
# 4. "속성 ID" 복사 (예: 123456789)

# Property ID는 숫자만 포함됩니다 (예: 123456789)
# API 요청 시 'properties/123456789' 형식으로 사용
```

#### Step 2: 서비스 계정에 GA4 권한 부여

```bash
# 1. GA4 관리 화면에서 "속성 액세스 관리" 클릭
# 2. 우측 상단 "+" 버튼 → "사용자 추가"
# 3. 이메일 주소에 서비스 계정 이메일 입력:
#    ga4-data-api-service@my-ga4-analytics.iam.gserviceaccount.com
# 4. 역할 선택:
#    - "뷰어" (읽기 전용) - 데이터 조회만
#    - "분석가" - 리포트 생성 가능
#    - "편집자" - 설정 변경 가능 (일반적으로 불필요)
# 5. "추가" 클릭
```

**중요:** 서비스 계정 이메일을 정확히 입력해야 합니다. `client_email` 값을 JSON 파일에서 복사하세요.

### 2.3 Python 환경 설정

#### Step 1: 라이브러리 설치

```bash
# Google Analytics Data API 클라이언트 라이브러리
pip install google-analytics-data

# 추가로 유용한 라이브러리들
pip install pandas numpy matplotlib  # 데이터 분석 및 시각화
```

#### Step 2: 인증 설정 (3가지 방법)

**방법 1: 환경 변수 설정 (권장)**

```bash
# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account-key.json"

# Windows (CMD)
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account-key.json
```

```python
# Python 코드 - 환경 변수 사용 시 자동 인증
from google.analytics.data_v1beta import BetaAnalyticsDataClient

client = BetaAnalyticsDataClient()  # 자동으로 환경 변수에서 인증 정보 로드
```

**방법 2: 코드에서 직접 지정**

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.oauth2 import service_account

# 서비스 계정 인증 정보 로드
credentials = service_account.Credentials.from_service_account_file(
    '/path/to/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

# 클라이언트 생성
client = BetaAnalyticsDataClient(credentials=credentials)
```

**방법 3: 환경 변수 + Python 코드 (유연함)**

```python
import os
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient

# .env 파일이나 환경 변수에서 경로 가져오기
key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

credentials = service_account.Credentials.from_service_account_file(
    key_path,
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

client = BetaAnalyticsDataClient(credentials=credentials)
```

#### Step 3: 연결 테스트

```python
"""
GA4 Data API 연결 테스트
"""
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)
from google.oauth2 import service_account

# 설정
PROPERTY_ID = '123456789'  # 여기에 실제 Property ID 입력
KEY_FILE_PATH = '/path/to/service-account-key.json'

# 인증
credentials = service_account.Credentials.from_service_account_file(
    KEY_FILE_PATH,
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

# 클라이언트 생성
client = BetaAnalyticsDataClient(credentials=credentials)

# 간단한 리포트 요청 (최근 7일 활성 사용자)
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[Dimension(name='date')],
    metrics=[Metric(name='activeUsers')]
)

try:
    response = client.run_report(request)
    print("✅ 연결 성공!")
    print(f"\n데이터 행 수: {len(response.rows)}")
    
    # 첫 5개 행 출력
    print("\n최근 7일 활성 사용자:")
    for row in response.rows[:5]:
        date = row.dimension_values[0].value
        users = row.metric_values[0].value
        print(f"  {date}: {users}명")
        
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    print("\n확인 사항:")
    print("1. Property ID가 올바른지 확인")
    print("2. 서비스 계정이 GA4 속성에 추가되었는지 확인")
    print("3. JSON 키 파일 경로가 올바른지 확인")
```

**실행 결과 (성공 시):**

```
✅ 연결 성공!

데이터 행 수: 7

최근 7일 활성 사용자:
  20251202: 1234명
  20251203: 1567명
  20251204: 1489명
  20251205: 1623명
  20251206: 1701명
```

---

## 3. 기본 사용법 - 데이터 조회의 모든 것

### 3.1 Dimensions와 Metrics 이해하기

GA4 Data API의 핵심 개념은 **Dimensions(차원)**과 **Metrics(측정항목)**입니다.

```yaml
Dimensions (차원):
  정의: 데이터를 그룹화하는 기준
  예시:
    - date: 날짜별
    - pagePath: 페이지 경로별
    - country: 국가별
    - deviceCategory: 기기 종류별
  
  특징: 문자열 값 (예: '2025-12-08', '/blog/post-1', 'South Korea')

Metrics (측정항목):
  정의: 수치로 측정되는 데이터
  예시:
    - activeUsers: 활성 사용자 수
    - sessions: 세션 수
    - screenPageViews: 페이지뷰 수
    - averageSessionDuration: 평균 세션 시간
  
  특징: 숫자 값 (예: 1234, 5678, 3.5)
```

**SQL과 비교:**

```sql
-- SQL 쿼리
SELECT 
    date,           -- Dimension
    country,        -- Dimension
    COUNT(*) as users,        -- Metric
    AVG(duration) as avg_time -- Metric
FROM analytics_data
GROUP BY date, country;

-- GA4 Data API (동일한 개념)
dimensions = [
    Dimension(name='date'),
    Dimension(name='country')
]
metrics = [
    Metric(name='activeUsers'),
    Metric(name='averageSessionDuration')
]
```

### 3.2 주요 Dimensions 100개+ 중 자주 쓰는 것들

```python
# ============================================
# 시간 관련 Dimensions
# ============================================
'date'              # 날짜 (YYYYMMDD)
'year'              # 연도 (2025)
'month'             # 월 (01-12)
'week'              # 주 (01-53)
'day'               # 일 (01-31)
'hour'              # 시간 (00-23)
'dayOfWeek'         # 요일 (0=일요일, 6=토요일)
'dayOfWeekName'     # 요일 이름 (Sunday, Monday...)


# ============================================
# 사용자/세션 관련
# ============================================
'country'           # 국가
'city'              # 도시
'region'            # 지역/주
'language'          # 언어
'deviceCategory'    # 기기 (Desktop, Mobile, Tablet)
'operatingSystem'   # OS (Windows, Android, iOS...)
'browser'           # 브라우저 (Chrome, Safari...)
'newVsReturning'    # 신규/재방문 (new, returning)


# ============================================
# 페이지/콘텐츠 관련
# ============================================
'pagePath'                    # 페이지 경로 (/blog/post-1)
'pageTitle'                   # 페이지 제목
'pagePathPlusQueryString'     # 경로 + 쿼리스트링
'landingPage'                 # 랜딩 페이지
'hostname'                    # 도메인


# ============================================
# 트래픽 소스 관련
# ============================================
'source'                      # 소스 (google, facebook...)
'medium'                      # 매체 (organic, cpc, referral...)
'sourceMedium'                # 소스 / 매체 조합
'campaignName'                # 캠페인 이름
'defaultChannelGroup'         # 기본 채널 그룹 (Organic Search, Direct...)


# ============================================
# 이벤트 관련
# ============================================
'eventName'                   # 이벤트 이름
'linkUrl'                     # 클릭한 링크 URL
'searchTerm'                  # 검색어


# ============================================
# 전자상거래 관련
# ============================================
'itemName'                    # 상품명
'itemCategory'                # 상품 카테고리
'transactionId'               # 거래 ID
```

### 3.3 주요 Metrics 200개+ 중 필수 항목

```python
# ============================================
# 사용자 관련 Metrics
# ============================================
'activeUsers'                 # 활성 사용자
'newUsers'                    # 신규 사용자
'totalUsers'                  # 전체 사용자
'active1DayUsers'             # 1일 활성 사용자
'active7DayUsers'             # 7일 활성 사용자
'active28DayUsers'            # 28일 활성 사용자


# ============================================
# 세션 관련
# ============================================
'sessions'                    # 세션 수
'sessionsPerUser'             # 사용자당 세션
'engagedSessions'             # 참여 세션
'engagementRate'              # 참여율 (0.0 ~ 1.0)
'averageSessionDuration'      # 평균 세션 시간 (초)
'bounceRate'                  # 이탈률 (0.0 ~ 1.0)


# ============================================
# 페이지뷰 관련
# ============================================
'screenPageViews'             # 페이지뷰
'screenPageViewsPerSession'   # 세션당 페이지뷰
'screenPageViewsPerUser'      # 사용자당 페이지뷰


# ============================================
# 이벤트 관련
# ============================================
'eventCount'                  # 이벤트 수
'eventCountPerUser'           # 사용자당 이벤트
'eventsPerSession'            # 세션당 이벤트
'keyEvents'                   # 주요 이벤트 (구 전환)


# ============================================
# 전자상거래 관련
# ============================================
'totalRevenue'                # 총 수익
'purchaseRevenue'             # 구매 수익
'transactions'                # 거래 수
'ecommercePurchases'          # 전자상거래 구매 수
'addToCarts'                  # 장바구니 추가
'checkouts'                   # 체크아웃
'itemsViewed'                 # 상품 조회 수
'itemsPurchased'              # 구매한 상품 수


# ============================================
# 광고 관련
# ============================================
'advertiserAdCost'            # 광고 비용
'advertiserAdClicks'          # 광고 클릭
'advertiserAdImpressions'     # 광고 노출
'returnOnAdSpend'             # ROAS (광고 수익률)
```

### 3.4 기본 데이터 조회 예제

#### 예제 1: 날짜별 활성 사용자

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)
from google.oauth2 import service_account

# 인증
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)
client = BetaAnalyticsDataClient(credentials=credentials)

# Property ID
PROPERTY_ID = '123456789'

# 리포트 요청
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='2025-12-01', end_date='2025-12-08')],
    dimensions=[Dimension(name='date')],
    metrics=[
        Metric(name='activeUsers'),
        Metric(name='sessions'),
        Metric(name='screenPageViews')
    ]
)

# 실행
response = client.run_report(request)

# 결과 출력
print("날짜별 트래픽 현황")
print("=" * 60)
for row in response.rows:
    date = row.dimension_values[0].value
    users = row.metric_values[0].value
    sessions = row.metric_values[1].value
    pageviews = row.metric_values[2].value
    
    # 날짜 포맷팅 (20251201 → 2025-12-01)
    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    
    print(f"{formatted_date} | 사용자: {users:>5} | 세션: {sessions:>5} | PV: {pageviews:>6}")
```

**출력 결과:**

```
날짜별 트래픽 현황
============================================================
2025-12-01 | 사용자:  1234 | 세션:  1456 | PV:   3456
2025-12-02 | 사용자:  1567 | 세션:  1789 | PV:   4123
2025-12-03 | 사용자:  1489 | 세션:  1698 | PV:   3987
2025-12-04 | 사용자:  1623 | 세션:  1842 | PV:   4234
2025-12-05 | 사용자:  1701 | 세션:  1923 | PV:   4567
2025-12-06 | 사용자:  1834 | 세션:  2056 | PV:   4891
2025-12-07 | 사용자:  1678 | 세션:  1891 | PV:   4456
2025-12-08 | 사용자:  1523 | 세션:  1734 | PV:   4098
```

#### 예제 2: 페이지별 성과

```python
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[
        Metric(name='screenPageViews'),
        Metric(name='activeUsers'),
        Metric(name='averageSessionDuration'),
        Metric(name='bounceRate')
    ],
    limit=10  # 상위 10개 페이지만
)

response = client.run_report(request)

print("\n인기 페이지 Top 10 (최근 30일)")
print("=" * 80)
print(f"{'페이지':<40} {'PV':>8} {'사용자':>8} {'평균시간':>10} {'이탈률':>8}")
print("-" * 80)

for row in response.rows:
    page = row.dimension_values[0].value
    pageviews = row.metric_values[0].value
    users = row.metric_values[1].value
    avg_duration = float(row.metric_values[2].value)
    bounce_rate = float(row.metric_values[3].value) * 100  # 백분율로 변환
    
    # 시간 포맷팅 (초 → 분:초)
    minutes = int(avg_duration // 60)
    seconds = int(avg_duration % 60)
    
    print(f"{page:<40} {pageviews:>8} {users:>8} {minutes:>2}m {seconds:>2}s   {bounce_rate:>6.1f}%")
```

**출력 결과:**

```
인기 페이지 Top 10 (최근 30일)
================================================================================
페이지                                          PV   사용자    평균시간    이탈률
--------------------------------------------------------------------------------
/                                             45678    12345  2m 34s     45.2%
/blog/post-1                                  23456     8901  4m 12s     32.1%
/blog/post-2                                  18923     7234  3m 45s     38.5%
/products/item-a                              15678     6123  5m 23s     28.3%
/about                                        12456     5234  1m 56s     52.7%
/contact                                       9876     4123  2m 12s     48.9%
/blog/category/tech                            8765     3456  3m 34s     41.2%
/products/item-b                               7654     2987  4m 56s     31.5%
/blog/post-3                                   6543     2567  4m 01s     35.8%
/faq                                           5432     2123  2m 45s     44.3%
```

#### 예제 3: 국가별/기기별 사용자

```python
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[
        Dimension(name='country'),
        Dimension(name='deviceCategory')
    ],
    metrics=[
        Metric(name='activeUsers'),
        Metric(name='sessions'),
        Metric(name='engagementRate')
    ],
    limit=20
)

response = client.run_report(request)

print("\n국가별/기기별 사용자 분석 (최근 7일)")
print("=" * 70)
print(f"{'국가':<20} {'기기':<10} {'사용자':>10} {'세션':>10} {'참여율':>10}")
print("-" * 70)

for row in response.rows:
    country = row.dimension_values[0].value
    device = row.dimension_values[1].value
    users = row.metric_values[0].value
    sessions = row.metric_values[1].value
    engagement = float(row.metric_values[2].value) * 100
    
    print(f"{country:<20} {device:<10} {users:>10} {sessions:>10} {engagement:>9.1f}%")
```

**출력 결과:**

```
국가별/기기별 사용자 분석 (최근 7일)
======================================================================
국가                   기기           사용자         세션       참여율
----------------------------------------------------------------------
South Korea          desktop          5678       6234      72.3%
South Korea          mobile           4567       5123      68.5%
United States        desktop          3456       3789      74.1%
United States        mobile           2345       2678      65.2%
Japan                mobile           1987       2234      71.8%
Japan                desktop          1678       1823      69.4%
United Kingdom       desktop          1234       1345      73.5%
...
```

#### 예제 4: 트래픽 소스 분석

```python
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[
        Dimension(name='sessionDefaultChannelGroup'),
        Dimension(name='sessionSourceMedium')
    ],
    metrics=[
        Metric(name='sessions'),
        Metric(name='activeUsers'),
        Metric(name='keyEvents'),  # 전환
        Metric(name='bounceRate')
    ],
    limit=15
)

response = client.run_report(request)

print("\n트래픽 소스별 성과 (최근 30일)")
print("=" * 90)
print(f"{'채널':<20} {'소스/매체':<25} {'세션':>10} {'사용자':>10} {'전환':>8} {'이탈률':>8}")
print("-" * 90)

for row in response.rows:
    channel = row.dimension_values[0].value
    source_medium = row.dimension_values[1].value
    sessions = row.metric_values[0].value
    users = row.metric_values[1].value
    conversions = row.metric_values[2].value
    bounce_rate = float(row.metric_values[3].value) * 100
    
    print(f"{channel:<20} {source_medium:<25} {sessions:>10} {users:>10} {conversions:>8} {bounce_rate:>7.1f}%")
```

**출력 결과:**

```
트래픽 소스별 성과 (최근 30일)
==========================================================================================
채널                   소스/매체                      세션       사용자      전환    이탈률
------------------------------------------------------------------------------------------
Organic Search       google / organic            15678      12345      234     38.5%
Direct               (direct) / (none)           12456      10234      189     42.3%
Referral             medium.com / referral        8765       7123      156     35.2%
Social               facebook / social            6543       5678       98     48.9%
Paid Search          google / cpc                 5432       4567      201     28.7%
Email                newsletter / email           3456       2987      145     31.5%
...
```

### 3.5 Pandas로 데이터 변환

API 응답을 Pandas DataFrame으로 변환하면 분석이 훨씬 쉬워집니다.

```python
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)

def ga4_to_dataframe(response):
    """
    GA4 API 응답을 Pandas DataFrame으로 변환
    """
    # Dimension 이름 추출
    dimension_names = [d.name for d in response.dimension_headers]
    
    # Metric 이름 추출
    metric_names = [m.name for m in response.metric_headers]
    
    # 데이터 추출
    data = []
    for row in response.rows:
        row_data = {}
        
        # Dimensions
        for i, dim_value in enumerate(row.dimension_values):
            row_data[dimension_names[i]] = dim_value.value
        
        # Metrics
        for i, metric_value in enumerate(row.metric_values):
            row_data[metric_names[i]] = metric_value.value
        
        data.append(row_data)
    
    return pd.DataFrame(data)


# 사용 예시
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='date'), Dimension(name='deviceCategory')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')]
)

response = client.run_report(request)
df = ga4_to_dataframe(response)

# Pandas로 분석
print(df.head(10))

# 날짜 컬럼을 datetime으로 변환
df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

# Numeric 변환
df['activeUsers'] = pd.to_numeric(df['activeUsers'])
df['sessions'] = pd.to_numeric(df['sessions'])

# 기기별 합계
device_summary = df.groupby('deviceCategory').agg({
    'activeUsers': 'sum',
    'sessions': 'sum'
}).reset_index()

print("\n기기별 합계:")
print(device_summary)

# 일별 추이 (모든 기기 합산)
daily_summary = df.groupby('date').agg({
    'activeUsers': 'sum',
    'sessions': 'sum'
}).reset_index()

print("\n일별 추이:")
print(daily_summary)

# CSV 저장
df.to_csv('ga4_data.csv', index=False)
```

**출력 결과:**

```
        date deviceCategory activeUsers sessions
0  20251109        desktop        1234     1456
1  20251109         mobile        2345     2678
2  20251109         tablet         123      145
3  20251110        desktop        1345     1567
4  20251110         mobile        2456     2789
...

기기별 합계:
  deviceCategory  activeUsers  sessions
0        desktop        45678     52341
1         mobile        78901     89234
2         tablet         5678      6234

일별 추이:
        date  activeUsers  sessions
0 2025-11-09         3702      4279
1 2025-11-10         4256      4901
2 2025-11-11         3987      4567
...
```

---

## 4. 고급 활용 - 필터링, 정렬, 실시간 데이터

### 4.1 필터링 (FilterExpression)

특정 조건에 맞는 데이터만 조회하려면 `dimension_filter` 또는 `metric_filter`를 사용합니다.

```python
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    FilterExpressionList,
    Filter,
)

# ============================================
# 예제 1: 특정 국가 데이터만 (한국)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='city')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')],
    
    # Dimension 필터: 국가가 "South Korea"인 데이터만
    dimension_filter=FilterExpression(
        filter=Filter(
            field_name='country',
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value='South Korea'
            )
        )
    ),
    limit=10
)

response = client.run_report(request)

print("한국 도시별 사용자 Top 10")
print("=" * 50)
for row in response.rows:
    city = row.dimension_values[0].value
    users = row.metric_values[0].value
    sessions = row.metric_values[1].value
    print(f"{city:<20} 사용자: {users:>6} | 세션: {sessions:>6}")


# ============================================
# 예제 2: 모바일 트래픽만
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[Dimension(name='date')],
    metrics=[Metric(name='activeUsers'), Metric(name='bounceRate')],
    
    dimension_filter=FilterExpression(
        filter=Filter(
            field_name='deviceCategory',
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value='mobile'
            )
        )
    )
)


# ============================================
# 예제 3: 특정 페이지 경로 포함 (블로그 글만)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath'), Dimension(name='pageTitle')],
    metrics=[Metric(name='screenPageViews'), Metric(name='activeUsers')],
    
    # pagePath가 "/blog/"로 시작하는 데이터만
    dimension_filter=FilterExpression(
        filter=Filter(
            field_name='pagePath',
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
                value='/blog/'
            )
        )
    ),
    limit=20
)

response = client.run_report(request)

print("\n블로그 페이지별 성과 Top 20")
print("=" * 80)
for row in response.rows:
    path = row.dimension_values[0].value
    title = row.dimension_values[1].value
    pageviews = row.metric_values[0].value
    users = row.metric_values[1].value
    print(f"{path:<40} {title:<30} PV: {pageviews:>5} | 사용자: {users:>5}")


# ============================================
# 예제 4: Metric 필터 - 사용자 100명 이상인 페이지만
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')],
    
    # activeUsers >= 100
    metric_filter=FilterExpression(
        filter=Filter(
            field_name='activeUsers',
            numeric_filter=Filter.NumericFilter(
                operation=Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL,
                value=Filter.NumericFilter.NumericValue(int64_value=100)
            )
        )
    )
)


# ============================================
# 예제 5: 복합 필터 (AND 조건)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath'), Dimension(name='deviceCategory')],
    metrics=[Metric(name='activeUsers'), Metric(name='bounceRate')],
    
    # 조건: 모바일 AND 이탈률 < 50%
    dimension_filter=FilterExpression(
        and_group=FilterExpressionList(
            expressions=[
                # 조건 1: 모바일
                FilterExpression(
                    filter=Filter(
                        field_name='deviceCategory',
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.EXACT,
                            value='mobile'
                        )
                    )
                ),
                # 조건 2: 이탈률 < 0.5 (50%)
                FilterExpression(
                    filter=Filter(
                        field_name='bounceRate',
                        numeric_filter=Filter.NumericFilter(
                            operation=Filter.NumericFilter.Operation.LESS_THAN,
                            value=Filter.NumericFilter.NumericValue(double_value=0.5)
                        )
                    )
                )
            ]
        )
    )
)


# ============================================
# 예제 6: 복합 필터 (OR 조건)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[Dimension(name='country')],
    metrics=[Metric(name='activeUsers')],
    
    # 조건: 한국 OR 미국 OR 일본
    dimension_filter=FilterExpression(
        or_group=FilterExpressionList(
            expressions=[
                FilterExpression(
                    filter=Filter(
                        field_name='country',
                        string_filter=Filter.StringFilter(value='South Korea')
                    )
                ),
                FilterExpression(
                    filter=Filter(
                        field_name='country',
                        string_filter=Filter.StringFilter(value='United States')
                    )
                ),
                FilterExpression(
                    filter=Filter(
                        field_name='country',
                        string_filter=Filter.StringFilter(value='Japan')
                    )
                )
            ]
        )
    )
)
```

**필터 매치 타입:**

```python
Filter.StringFilter.MatchType.EXACT           # 정확히 일치
Filter.StringFilter.MatchType.BEGINS_WITH     # ~로 시작
Filter.StringFilter.MatchType.ENDS_WITH       # ~로 끝남
Filter.StringFilter.MatchType.CONTAINS        # 포함
Filter.StringFilter.MatchType.FULL_REGEXP     # 정규표현식
```

### 4.2 정렬 (OrderBy)

```python
from google.analytics.data_v1beta.types import OrderBy

# ============================================
# 예제 1: 활성 사용자 수 내림차순 (많은 순)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')],
    
    order_bys=[
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='activeUsers'),
            desc=True  # 내림차순 (큰 값 → 작은 값)
        )
    ],
    limit=10  # Top 10
)

response = client.run_report(request)

print("인기 페이지 Top 10 (사용자 수 기준)")
print("=" * 60)
for i, row in enumerate(response.rows, 1):
    page = row.dimension_values[0].value
    users = row.metric_values[0].value
    sessions = row.metric_values[1].value
    print(f"{i:>2}. {page:<40} 사용자: {users:>6} | 세션: {sessions:>6}")


# ============================================
# 예제 2: 이탈률 오름차순 (낮은 순 = 좋은 페이지)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='activeUsers'), Metric(name='bounceRate')],
    
    # 사용자 100명 이상인 페이지만
    metric_filter=FilterExpression(
        filter=Filter(
            field_name='activeUsers',
            numeric_filter=Filter.NumericFilter(
                operation=Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL,
                value=Filter.NumericFilter.NumericValue(int64_value=100)
            )
        )
    ),
    
    # 이탈률 낮은 순 정렬
    order_bys=[
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='bounceRate'),
            desc=False  # 오름차순 (작은 값 → 큰 값)
        )
    ],
    limit=10
)

response = client.run_report(request)

print("\n이탈률 낮은 페이지 Top 10 (사용자 100명 이상)")
print("=" * 70)
for i, row in enumerate(response.rows, 1):
    page = row.dimension_values[0].value
    users = row.metric_values[0].value
    bounce_rate = float(row.metric_values[1].value) * 100
    print(f"{i:>2}. {page:<40} 사용자: {users:>5} | 이탈률: {bounce_rate:>5.1f}%")


# ============================================
# 예제 3: 복수 정렬 (날짜 오름차순 → 사용자 내림차순)
# ============================================
request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[Dimension(name='date'), Dimension(name='country')],
    metrics=[Metric(name='activeUsers')],
    
    order_bys=[
        # 1순위: 날짜 오름차순
        OrderBy(
            dimension=OrderBy.DimensionOrderBy(dimension_name='date'),
            desc=False
        ),
        # 2순위: 사용자 내림차순
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='activeUsers'),
            desc=True
        )
    ]
)

response = client.run_report(request)

print("\n날짜별 국가 순위 (사용자 기준)")
print("=" * 60)
current_date = None
for row in response.rows:
    date = row.dimension_values[0].value
    country = row.dimension_values[1].value
    users = row.metric_values[0].value
    
    # 날짜가 바뀌면 구분선
    if current_date != date:
        if current_date is not None:
            print("-" * 60)
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        print(f"\n[{formatted_date}]")
        current_date = date
    
    print(f"  {country:<30} {users:>8}명")
```

### 4.3 페이지네이션 (대량 데이터 조회)

API는 한 번에 최대 100,000행을 반환하지만, `offset`을 사용해 순차적으로 조회할 수 있습니다.

```python
def fetch_all_data(client, base_request, page_size=10000):
    """
    모든 데이터를 페이지네이션으로 조회
    """
    all_rows = []
    offset = 0
    
    while True:
        # 요청 설정
        request = base_request
        request.limit = page_size
        request.offset = offset
        
        # API 호출
        response = client.run_report(request)
        
        # 데이터 추가
        all_rows.extend(response.rows)
        
        print(f"조회됨: {offset + len(response.rows)} / {response.row_count} 행")
        
        # 마지막 페이지인지 확인
        if len(response.rows) < page_size:
            break
        
        offset += page_size
    
    return all_rows


# 사용 예시
base_request = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')],
    order_bys=[
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='activeUsers'),
            desc=True
        )
    ]
)

all_rows = fetch_all_data(client, base_request)

print(f"\n총 {len(all_rows)}개 페이지 데이터 조회 완료")

# DataFrame으로 변환
data = []
for row in all_rows:
    data.append({
        'pagePath': row.dimension_values[0].value,
        'activeUsers': int(row.metric_values[0].value),
        'sessions': int(row.metric_values[1].value)
    })

df = pd.DataFrame(data)
df.to_csv('all_pages_data.csv', index=False)
```

### 4.4 실시간 데이터 (runRealtimeReport)

**최근 30분 데이터**를 조회합니다 (GA4 360은 최대 60분).

```python
from google.analytics.data_v1beta.types import RunRealtimeReportRequest

# ============================================
# 예제 1: 현재 활성 사용자 (국가별)
# ============================================
realtime_request = RunRealtimeReportRequest(
    property=f'properties/{PROPERTY_ID}',
    dimensions=[Dimension(name='country')],
    metrics=[Metric(name='activeUsers')],
    limit=10
)

response = client.run_realtime_report(realtime_request)

print("실시간 활성 사용자 (국가별 Top 10)")
print("=" * 50)
total_users = 0
for row in response.rows:
    country = row.dimension_values[0].value
    users = int(row.metric_values[0].value)
    total_users += users
    print(f"{country:<30} {users:>5}명")

print(f"\n총 실시간 사용자: {total_users}명")


# ============================================
# 예제 2: 실시간 페이지뷰 (페이지별)
# ============================================
realtime_request = RunRealtimeReportRequest(
    property=f'properties/{PROPERTY_ID}',
    dimensions=[Dimension(name='pagePath'), Dimension(name='pageTitle')],
    metrics=[Metric(name='activeUsers'), Metric(name='screenPageViews')],
    order_bys=[
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'),
            desc=True
        )
    ],
    limit=10
)

response = client.run_realtime_report(realtime_request)

print("\n실시간 인기 페이지 Top 10")
print("=" * 80)
for i, row in enumerate(response.rows, 1):
    path = row.dimension_values[0].value
    title = row.dimension_values[1].value
    users = row.metric_values[0].value
    pageviews = row.metric_values[1].value
    print(f"{i:>2}. {path:<40} {title:<25} PV: {pageviews:>4} | 사용자: {users:>3}")


# ============================================
# 예제 3: 실시간 트래픽 소스
# ============================================
realtime_request = RunRealtimeReportRequest(
    property=f'properties/{PROPERTY_ID}',
    dimensions=[Dimension(name='sessionSourceMedium')],
    metrics=[Metric(name='activeUsers')],
    order_bys=[
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='activeUsers'),
            desc=True
        )
    ],
    limit=10
)

response = client.run_realtime_report(realtime_request)

print("\n실시간 트래픽 소스 Top 10")
print("=" * 60)
for i, row in enumerate(response.rows, 1):
    source_medium = row.dimension_values[0].value
    users = row.metric_values[0].value
    print(f"{i:>2}. {source_medium:<45} {users:>5}명")


# ============================================
# 예제 4: 실시간 모니터링 (30초마다 갱신)
# ============================================
import time
from datetime import datetime

def realtime_monitor(client, property_id, interval=30):
    """
    실시간 트래픽 모니터링 (Ctrl+C로 중단)
    """
    print("실시간 트래픽 모니터링 시작 (Ctrl+C로 중단)")
    print("=" * 70)
    
    try:
        while True:
            request = RunRealtimeReportRequest(
                property=f'properties/{property_id}',
                dimensions=[Dimension(name='deviceCategory')],
                metrics=[
                    Metric(name='activeUsers'),
                    Metric(name='screenPageViews')
                ]
            )
            
            response = client.run_realtime_report(request)
            
            # 현재 시간
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 데이터 출력
            print(f"\n[{now}]")
            total_users = 0
            total_pageviews = 0
            
            for row in response.rows:
                device = row.dimension_values[0].value
                users = int(row.metric_values[0].value)
                pageviews = int(row.metric_values[1].value)
                
                total_users += users
                total_pageviews += pageviews
                
                print(f"  {device:<10} 사용자: {users:>4} | PV: {pageviews:>5}")
            
            print(f"  {'합계':<10} 사용자: {total_users:>4} | PV: {total_pageviews:>5}")
            print("-" * 70)
            
            # 대기
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n모니터링 종료")


# 실행 (30초마다 갱신)
realtime_monitor(client, PROPERTY_ID, interval=30)
```

**실행 결과:**

```
실시간 트래픽 모니터링 시작 (Ctrl+C로 중단)
======================================================================

[2025-12-08 14:30:00]
  desktop    사용자:   45 | PV:   123
  mobile     사용자:   78 | PV:   234
  tablet     사용자:    8 | PV:    21
  합계        사용자:  131 | PV:   378
----------------------------------------------------------------------

[2025-12-08 14:30:30]
  desktop    사용자:   48 | PV:   135
  mobile     사용자:   82 | PV:   251
  tablet     사용자:    9 | PV:    23
  합계        사용자:  139 | PV:   409
----------------------------------------------------------------------

[2025-12-08 14:31:00]
  desktop    사용자:   51 | PV:   142
  mobile     사용자:   85 | PV:   267
  tablet     사용자:   10 | PV:    25
  합계        사용자:  146 | PV:   434
----------------------------------------------------------------------
```

### 4.5 Batch 요청 (여러 리포트 한 번에)

```python
from google.analytics.data_v1beta.types import BatchRunReportsRequest

# ============================================
# 여러 리포트를 한 번에 조회
# ============================================

# 리포트 1: 날짜별 사용자
request1 = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
    dimensions=[Dimension(name='date')],
    metrics=[Metric(name='activeUsers'), Metric(name='sessions')]
)

# 리포트 2: 페이지별 성과
request2 = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='pagePath')],
    metrics=[Metric(name='screenPageViews'), Metric(name='activeUsers')],
    limit=10
)

# 리포트 3: 트래픽 소스
request3 = RunReportRequest(
    property=f'properties/{PROPERTY_ID}',
    date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
    dimensions=[Dimension(name='sessionDefaultChannelGroup')],
    metrics=[Metric(name='sessions'), Metric(name='keyEvents')]
)

# Batch 요청
batch_request = BatchRunReportsRequest(
    property=f'properties/{PROPERTY_ID}',
    requests=[request1, request2, request3]
)

batch_response = client.batch_run_reports(batch_request)

# 결과 처리
print("=== 리포트 1: 날짜별 사용자 ===")
for row in batch_response.reports[0].rows:
    date = row.dimension_values[0].value
    users = row.metric_values[0].value
    print(f"{date}: {users}명")

print("\n=== 리포트 2: 인기 페이지 Top 10 ===")
for row in batch_response.reports[1].rows:
    page = row.dimension_values[0].value
    pageviews = row.metric_values[0].value
    print(f"{page}: {pageviews} PV")

print("\n=== 리포트 3: 채널별 전환 ===")
for row in batch_response.reports[2].rows:
    channel = row.dimension_values[0].value
    sessions = row.metric_values[0].value
    conversions = row.metric_values[1].value
    print(f"{channel}: 세션 {sessions} | 전환 {conversions}")
```

---

## 5. 실전 예제 - 자동화, 대시보드, 시각화

### 5.1 일일 리포트 이메일 자동 전송

```python
"""
매일 아침 8시 GA4 리포트를 이메일로 전송하는 스크립트
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from google.oauth2 import service_account

# GA4 설정
PROPERTY_ID = '123456789'
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)
client = BetaAnalyticsDataClient(credentials=credentials)

# 이메일 설정
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = 'your-email@gmail.com'
SENDER_PASSWORD = 'your-app-password'  # Gmail 앱 비밀번호
RECEIVER_EMAIL = 'manager@company.com'


def get_daily_summary(property_id, date='yesterday'):
    """
    일일 요약 데이터 조회
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=date, end_date=date)],
        dimensions=[Dimension(name='date')],
        metrics=[
            Metric(name='activeUsers'),
            Metric(name='newUsers'),
            Metric(name='sessions'),
            Metric(name='screenPageViews'),
            Metric(name='engagementRate'),
            Metric(name='averageSessionDuration')
        ]
    )
    
    response = client.run_report(request)
    
    if not response.rows:
        return None
    
    row = response.rows[0]
    return {
        'date': row.dimension_values[0].value,
        'activeUsers': int(row.metric_values[0].value),
        'newUsers': int(row.metric_values[1].value),
        'sessions': int(row.metric_values[2].value),
        'pageViews': int(row.metric_values[3].value),
        'engagementRate': float(row.metric_values[4].value) * 100,
        'avgSessionDuration': int(float(row.metric_values[5].value))
    }


def get_top_pages(property_id, date='yesterday', limit=10):
    """
    인기 페이지 Top 10
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=date, end_date=date)],
        dimensions=[Dimension(name='pagePath'), Dimension(name='pageTitle')],
        metrics=[
            Metric(name='screenPageViews'),
            Metric(name='activeUsers'),
            Metric(name='averageSessionDuration')
        ],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'),
            desc=True
        )],
        limit=limit
    )
    
    response = client.run_report(request)
    
    pages = []
    for row in response.rows:
        pages.append({
            'path': row.dimension_values[0].value,
            'title': row.dimension_values[1].value,
            'pageViews': int(row.metric_values[0].value),
            'users': int(row.metric_values[1].value),
            'avgDuration': int(float(row.metric_values[2].value))
        })
    
    return pages


def get_traffic_sources(property_id, date='yesterday', limit=10):
    """
    트래픽 소스 Top 10
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=date, end_date=date)],
        dimensions=[Dimension(name='sessionDefaultChannelGroup')],
        metrics=[
            Metric(name='sessions'),
            Metric(name='activeUsers'),
            Metric(name='keyEvents')
        ],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='sessions'),
            desc=True
        )],
        limit=limit
    )
    
    response = client.run_report(request)
    
    sources = []
    for row in response.rows:
        sources.append({
            'channel': row.dimension_values[0].value,
            'sessions': int(row.metric_values[0].value),
            'users': int(row.metric_values[1].value),
            'conversions': int(row.metric_values[2].value)
        })
    
    return sources


def create_html_report(summary, top_pages, traffic_sources, report_date):
    """
    HTML 리포트 생성
    """
    # 날짜 포맷팅
    formatted_date = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    
    # 평균 세션 시간 포맷팅 (초 → 분:초)
    minutes = summary['avgSessionDuration'] // 60
    seconds = summary['avgSessionDuration'] % 60
    
    html = f"""
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            h1 { color: #4285f4; }
            h2 { color: #34a853; margin-top: 30px; }
            table { border-collapse: collapse; width: 100%; margin-top: 10px; }
            th { background-color: #4285f4; color: white; padding: 12px; text-align: left; }
            td { padding: 10px; border-bottom: 1px solid #ddd; }
            tr:hover { background-color: #f5f5f5; }
            .metric-box { 
                display: inline-block; 
                background: #f8f9fa; 
                padding: 15px 20px; 
                margin: 10px 10px 10px 0; 
                border-radius: 5px;
                border-left: 4px solid #4285f4;
            }
            .metric-label { color: #666; font-size: 14px; }
            .metric-value { font-size: 24px; font-weight: bold; color: #333; }
        </style>
    </head>
    <body>
        <h1>📊 Google Analytics 일일 리포트</h1>
        <p><strong>보고 날짜:</strong> {formatted_date}</p>
        
        <h2>📈 주요 지표</h2>
        <div class="metric-box">
            <div class="metric-label">활성 사용자</div>
            <div class="metric-value">{summary['activeUsers']:,}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">신규 사용자</div>
            <div class="metric-value">{summary['newUsers']:,}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">세션</div>
            <div class="metric-value">{summary['sessions']:,}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">페이지뷰</div>
            <div class="metric-value">{summary['pageViews']:,}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">참여율</div>
            <div class="metric-value">{summary['engagementRate']:.1f}%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">평균 세션 시간</div>
            <div class="metric-value">{minutes}m {seconds}s</div>
        </div>
        
        <h2>📄 인기 페이지 Top 10</h2>
        <table>
            <tr>
                <th>순위</th>
                <th>페이지</th>
                <th>페이지뷰</th>
                <th>사용자</th>
                <th>평균 체류시간</th>
            </tr>
    """
    
    for i, page in enumerate(top_pages, 1):
        page_minutes = page['avgDuration'] // 60
        page_seconds = page['avgDuration'] % 60
        html += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{page['title']}</strong><br/><small style="color:#666">{page['path']}</small></td>
                <td>{page['pageViews']:,}</td>
                <td>{page['users']:,}</td>
                <td>{page_minutes}m {page_seconds}s</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>🚀 트래픽 소스 Top 10</h2>
        <table>
            <tr>
                <th>채널</th>
                <th>세션</th>
                <th>사용자</th>
                <th>전환</th>
            </tr>
    """
    
    for source in traffic_sources:
        html += f"""
            <tr>
                <td>{source['channel']}</td>
                <td>{source['sessions']:,}</td>
                <td>{source['users']:,}</td>
                <td>{source['conversions']:,}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <hr style="margin-top: 40px; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">
            이 리포트는 Google Analytics Data API를 통해 자동으로 생성되었습니다.
        </p>
    </body>
    </html>
    """
    
    return html


def send_email(subject, html_content, sender, password, receiver):
    """
    이메일 전송
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print(f"✅ 이메일 전송 완료: {receiver}")
    except Exception as e:
        print(f"❌ 이메일 전송 실패: {e}")


def main():
    """
    메인 실행 함수
    """
    # 어제 날짜 계산
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📊 {yesterday} 리포트 생성 중...")
    
    # 데이터 조회
    summary = get_daily_summary(PROPERTY_ID, date='yesterday')
    if not summary:
        print("❌ 데이터가 없습니다.")
        return
    
    top_pages = get_top_pages(PROPERTY_ID, date='yesterday', limit=10)
    traffic_sources = get_traffic_sources(PROPERTY_ID, date='yesterday', limit=10)
    
    # HTML 리포트 생성
    html_report = create_html_report(
        summary, 
        top_pages, 
        traffic_sources, 
        summary['date']
    )
    
    # 이메일 전송
    subject = f"📊 Google Analytics 일일 리포트 - {yesterday}"
    send_email(
        subject,
        html_report,
        SENDER_EMAIL,
        SENDER_PASSWORD,
        RECEIVER_EMAIL
    )
    
    print("✅ 리포트 생성 및 전송 완료!")


if __name__ == '__main__':
    main()
```

**cron 설정 (매일 아침 8시 실행):**

```bash
# Linux/Mac - crontab -e
0 8 * * * /usr/bin/python3 /path/to/daily_ga4_report.py

# Windows - Task Scheduler
# 동작: "프로그램 시작"
# 프로그램/스크립트: C:\Python39\python.exe
# 인수 추가: C:\path\to\daily_ga4_report.py
# 트리거: 매일 오전 8:00
```

### 5.2 시각화 - Matplotlib으로 차트 생성

```python
"""
GA4 데이터 시각화 예제
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from google.oauth2 import service_account

# 한글 폰트 설정 (Mac)
plt.rc('font', family='AppleGothic')
# Windows: plt.rc('font', family='Malgun Gothic')
# Linux: plt.rc('font', family='NanumGothic')

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# GA4 클라이언트
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)
client = BetaAnalyticsDataClient(credentials=credentials)
PROPERTY_ID = '123456789'


def plot_daily_traffic(property_id, start_date='30daysAgo', end_date='today'):
    """
    일별 트래픽 추이 그래프
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name='date')],
        metrics=[
            Metric(name='activeUsers'),
            Metric(name='sessions'),
            Metric(name='screenPageViews')
        ]
    )
    
    response = client.run_report(request)
    
    # 데이터 추출
    dates = []
    users = []
    sessions = []
    pageviews = []
    
    for row in response.rows:
        date_str = row.dimension_values[0].value
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        
        dates.append(date_obj)
        users.append(int(row.metric_values[0].value))
        sessions.append(int(row.metric_values[1].value))
        pageviews.append(int(row.metric_values[2].value))
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(dates, users, marker='o', linewidth=2, label='활성 사용자')
    ax.plot(dates, sessions, marker='s', linewidth=2, label='세션')
    ax.plot(dates, pageviews, marker='^', linewidth=2, label='페이지뷰')
    
    ax.set_xlabel('날짜', fontsize=12)
    ax.set_ylabel('수', fontsize=12)
    ax.set_title('일별 트래픽 추이 (최근 30일)', fontsize=16, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 날짜 포맷
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig('ga4_daily_traffic.png', dpi=300)
    print("✅ 그래프 저장: ga4_daily_traffic.png")
    plt.show()


def plot_device_breakdown(property_id, start_date='30daysAgo', end_date='today'):
    """
    기기별 사용자 분포 파이 차트
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name='deviceCategory')],
        metrics=[Metric(name='activeUsers')]
    )
    
    response = client.run_report(request)
    
    # 데이터 추출
    devices = []
    users = []
    
    for row in response.rows:
        devices.append(row.dimension_values[0].value)
        users.append(int(row.metric_values[0].value))
    
    # 파이 차트
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = ['#4285f4', '#34a853', '#fbbc04', '#ea4335']
    explode = [0.05] * len(devices)  # 약간 분리
    
    wedges, texts, autotexts = ax.pie(
        users,
        labels=devices,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors[:len(devices)],
        explode=explode,
        textprops={'fontsize': 12}
    )
    
    # 퍼센트 텍스트 스타일
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(14)
    
    ax.set_title('기기별 사용자 분포 (최근 30일)', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('ga4_device_breakdown.png', dpi=300)
    print("✅ 그래프 저장: ga4_device_breakdown.png")
    plt.show()


def plot_traffic_sources(property_id, start_date='30daysAgo', end_date='today'):
    """
    트래픽 소스별 세션 막대 그래프
    """
    request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name='sessionDefaultChannelGroup')],
        metrics=[Metric(name='sessions')],
        order_bys=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name='sessions'),
            desc=True
        )],
        limit=10
    )
    
    response = client.run_report(request)
    
    # 데이터 추출
    channels = []
    sessions = []
    
    for row in response.rows:
        channels.append(row.dimension_values[0].value)
        sessions.append(int(row.metric_values[0].value))
    
    # 막대 그래프
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bars = ax.barh(channels, sessions, color='#4285f4')
    
    # 값 표시
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, 
                f'{sessions[i]:,}',
                ha='left', va='center', fontsize=11, fontweight='bold')
    
    ax.set_xlabel('세션 수', fontsize=12)
    ax.set_title('트래픽 소스별 세션 (최근 30일)', fontsize=16, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ga4_traffic_sources.png', dpi=300)
    print("✅ 그래프 저장: ga4_traffic_sources.png")
    plt.show()


def plot_weekly_comparison(property_id):
    """
    주별 비교 그래프 (이번 주 vs 지난 주)
    """
    # 이번 주
    this_week_request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date='7daysAgo', end_date='today')],
        dimensions=[Dimension(name='dayOfWeekName')],
        metrics=[Metric(name='activeUsers')]
    )
    
    # 지난 주
    last_week_request = RunReportRequest(
        property=f'properties/{property_id}',
        date_ranges=[DateRange(start_date='14daysAgo', end_date='8daysAgo')],
        dimensions=[Dimension(name='dayOfWeekName')],
        metrics=[Metric(name='activeUsers')]
    )
    
    this_week_response = client.run_report(this_week_request)
    last_week_response = client.run_report(last_week_request)
    
    # 요일 순서
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                 'Thursday', 'Friday', 'Saturday']
    
    # 데이터 추출
    this_week_data = {row.dimension_values[0].value: int(row.metric_values[0].value) 
                      for row in this_week_response.rows}
    last_week_data = {row.dimension_values[0].value: int(row.metric_values[0].value) 
                      for row in last_week_response.rows}
    
    this_week_users = [this_week_data.get(day, 0) for day in day_order]
    last_week_users = [last_week_data.get(day, 0) for day in day_order]
    
    # 요일 한글 변환
    day_names_kr = ['일', '월', '화', '수', '목', '금', '토']
    
    # 그래프
    fig, ax = plt.subplots(figsize=(14, 6))
    
    x = range(len(day_names_kr))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], last_week_users, 
                    width, label='지난 주', color='#ea4335', alpha=0.7)
    bars2 = ax.bar([i + width/2 for i in x], this_week_users, 
                    width, label='이번 주', color='#34a853', alpha=0.7)
    
    # 값 표시
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height,
                    f'{int(height):,}',
                    ha='center', va='bottom', fontsize=10)
    
    ax.set_ylabel('활성 사용자', fontsize=12)
    ax.set_title('요일별 사용자 비교 (이번 주 vs 지난 주)', fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(day_names_kr)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ga4_weekly_comparison.png', dpi=300)
    print("✅ 그래프 저장: ga4_weekly_comparison.png")
    plt.show()


# 실행
if __name__ == '__main__':
    print("📊 GA4 시각화 시작...\n")
    
    plot_daily_traffic(PROPERTY_ID)
    plot_device_breakdown(PROPERTY_ID)
    plot_traffic_sources(PROPERTY_ID)
    plot_weekly_comparison(PROPERTY_ID)
    
    print("\n✅ 모든 그래프 생성 완료!")
```

### 5.3 자주 사용하는 Helper 함수 모음

```python
"""
GA4 Data API Helper 함수 모음
"""
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    Filter,
    OrderBy
)
import pandas as pd


class GA4Helper:
    """
    GA4 Data API 편의 함수 모음
    """
    
    def __init__(self, property_id, credentials):
        self.property_id = property_id
        self.client = BetaAnalyticsDataClient(credentials=credentials)
    
    def to_dataframe(self, response):
        """응답을 DataFrame으로 변환"""
        dimension_names = [d.name for d in response.dimension_headers]
        metric_names = [m.name for m in response.metric_headers]
        
        data = []
        for row in response.rows:
            row_data = {}
            for i, dim in enumerate(row.dimension_values):
                row_data[dimension_names[i]] = dim.value
            for i, metric in enumerate(row.metric_values):
                row_data[metric_names[i]] = metric.value
            data.append(row_data)
        
        return pd.DataFrame(data)
    
    def get_total_users(self, start_date='30daysAgo', end_date='today'):
        """전체 사용자 수"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name='totalUsers')]
        )
        response = self.client.run_report(request)
        return int(response.rows[0].metric_values[0].value) if response.rows else 0
    
    def get_top_pages(self, start_date='30daysAgo', end_date='today', limit=10):
        """인기 페이지 Top N"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name='pagePath'), Dimension(name='pageTitle')],
            metrics=[Metric(name='screenPageViews'), Metric(name='activeUsers')],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'),
                desc=True
            )],
            limit=limit
        )
        response = self.client.run_report(request)
        return self.to_dataframe(response)
    
    def get_realtime_users(self):
        """실시간 사용자 수"""
        from google.analytics.data_v1beta.types import RunRealtimeReportRequest
        
        request = RunRealtimeReportRequest(
            property=f'properties/{self.property_id}',
            metrics=[Metric(name='activeUsers')]
        )
        response = self.client.run_realtime_report(request)
        return int(response.rows[0].metric_values[0].value) if response.rows else 0
    
    def get_conversion_rate(self, start_date='30daysAgo', end_date='today'):
        """전환율 계산"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name='sessions'),
                Metric(name='keyEvents')
            ]
        )
        response = self.client.run_report(request)
        
        if not response.rows:
            return 0.0
        
        sessions = int(response.rows[0].metric_values[0].value)
        conversions = int(response.rows[0].metric_values[1].value)
        
        return (conversions / sessions * 100) if sessions > 0 else 0.0
    
    def get_page_performance(self, page_path, start_date='30daysAgo', end_date='today'):
        """특정 페이지 성능 분석"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name='pagePath')],
            metrics=[
                Metric(name='screenPageViews'),
                Metric(name='activeUsers'),
                Metric(name='averageSessionDuration'),
                Metric(name='bounceRate')
            ],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name='pagePath',
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value=page_path
                    )
                )
            )
        )
        response = self.client.run_report(request)
        
        if not response.rows:
            return None
        
        row = response.rows[0]
        return {
            'pageViews': int(row.metric_values[0].value),
            'users': int(row.metric_values[1].value),
            'avgDuration': float(row.metric_values[2].value),
            'bounceRate': float(row.metric_values[3].value) * 100
        }


# 사용 예시
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

helper = GA4Helper(property_id='123456789', credentials=credentials)

# 전체 사용자
total_users = helper.get_total_users()
print(f"전체 사용자: {total_users:,}명")

# 실시간 사용자
realtime_users = helper.get_realtime_users()
print(f"실시간 사용자: {realtime_users:,}명")

# 전환율
conversion_rate = helper.get_conversion_rate()
print(f"전환율: {conversion_rate:.2f}%")

# 인기 페이지
top_pages_df = helper.get_top_pages(limit=5)
print("\n인기 페이지 Top 5:")
print(top_pages_df)

# 특정 페이지 성능
page_perf = helper.get_page_performance('/blog/post-1')
if page_perf:
    print(f"\n'/blog/post-1' 페이지 성능:")
    print(f"  페이지뷰: {page_perf['pageViews']:,}")
    print(f"  사용자: {page_perf['users']:,}")
    print(f"  평균 체류: {page_perf['avgDuration']:.0f}초")
    print(f"  이탈률: {page_perf['bounceRate']:.1f}%")
```

---

## 6. 마무리

### 6.1 주요 포인트 정리

```yaml
1. 환경 설정:
   - GCP 프로젝트 생성
   - Analytics Data API 활성화
   - 서비스 계정 생성 및 GA4 권한 부여
   - Python 라이브러리 설치: google-analytics-data

2. 핵심 개념:
   - Dimensions: 데이터 그룹화 기준 (date, pagePath, country...)
   - Metrics: 측정 항목 (activeUsers, sessions, pageViews...)
   - Property ID: GA4 속성 식별자

3. 주요 기능:
   - runReport: 기본 리포트 조회
   - runRealtimeReport: 실시간 데이터 (최근 30분)
   - batchRunReports: 여러 리포트 동시 조회
   - Filtering: 특정 조건 데이터만 조회
   - Ordering: 정렬
   - Pagination: 대량 데이터 순차 조회

4. 실전 활용:
   - 일일 리포트 이메일 자동화
   - Pandas DataFrame 변환 및 분석
   - Matplotlib 시각화
   - Helper 클래스로 재사용성 향상
```

### 6.2 더 알아보기

- **공식 문서**: [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- **API Schema**: [모든 Dimensions & Metrics 목록](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
- **Python Client Library**: [google-analytics-data PyPI](https://pypi.org/project/google-analytics-data/)
- **Quota 관리**: [API 할당량 및 제한](https://developers.google.com/analytics/devguides/reporting/data/v1/quotas)

### 6.3 자주 하는 질문

**Q1: Universal Analytics(UA) 데이터도 조회할 수 있나요?**
- A: 아니요. 이 API는 GA4 전용입니다. UA는 [Reporting API v4](https://developers.google.com/analytics/devguides/reporting/core/v4)를 사용해야 합니다.

**Q2: API 호출 제한이 있나요?**
- A: 네. 하루 25,000 요청, 시간당 1,250 요청 제한이 있습니다. 자세한 내용은 [Quota 문서](https://developers.google.com/analytics/devguides/reporting/data/v1/quotas)를 참고하세요.

**Q3: 비용이 발생하나요?**
- A: Google Analytics Data API 자체는 무료입니다. 단, GCP 프로젝트 생성과 서비스 계정 사용은 무료입니다.

**Q4: 과거 데이터는 얼마나 조회할 수 있나요?**
- A: GA4 속성이 생성된 시점부터 모든 데이터를 조회할 수 있습니다 (최대 14개월, GA4 360은 50개월).

**Q5: Custom Dimensions/Metrics도 조회할 수 있나요?**
- A: 네. `customEvent:parameter_name`, `customUser:parameter_name` 형식으로 조회 가능합니다.

---

이제 Python으로 Google Analytics 데이터를 자유자재로 활용할 수 있습니다! 🚀

자동화, 대시보드, 머신러닝 등 무궁무진한 활용이 가능하니 여러분의 프로젝트에 적용해보세요.



