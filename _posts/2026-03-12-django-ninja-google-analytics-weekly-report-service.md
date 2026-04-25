---
layout: post
title: "Django Ninja로 Google Analytics 주간 성과 분석 서비스 만들기"
date: 2026-03-12 10:00:00 +0900
render_with_liquid: false
categories: [Django, Python, API, Analytics]
tags: [Django Ninja, Google Analytics, API, Data Analysis, Backend, Python, Weekly Report, Business Intelligence]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-03-12-django-ninja-google-analytics-weekly-report-service.webp"
---

웹사이트나 앱을 운영하다 보면 데이터 기반의 의사결정이 필수입니다. Google Analytics는 풍부한 사용자 데이터를 제공하지만, 매주 대시보드에 접속해서 데이터를 확인하고 비교하는 것은 번거로운 일입니다. 이 글에서는 Django Ninja를 활용하여 Google Analytics 데이터를 자동으로 수집하고, 지난주와 이번주의 성과를 비교하는 보고서를 생성하는 서비스를 구축하는 과정을 단계별로 살펴보겠습니다.

## 🎯 프로젝트 개요

### 구축할 서비스의 주요 기능

이번 프로젝트에서 구축할 서비스는 다음과 같은 핵심 기능을 제공합니다:

1. **자동 데이터 수집**: Google Analytics API를 통해 일별 웹사이트 통계 데이터를 자동으로 수집
2. **데이터베이스 저장**: 수집한 데이터를 Django ORM을 통해 PostgreSQL/MySQL에 구조화하여 저장
3. **주간 성과 비교**: 지난주(Week -1)와 이번주(Week 0)의 주요 지표를 비교 분석
4. **RESTful API 제공**: Django Ninja를 활용한 고성능 API 엔드포인트 제공
5. **보고서 자동 생성**: 주요 지표를 시각화하고 인사이트를 제공하는 주간 보고서 생성

### 기술 스택

```python
# 주요 기술 스택
{
    "Backend Framework": "Django 5.0+",
    "API Framework": "Django Ninja 1.0+",
    "Analytics API": "Google Analytics Data API (GA4)",
    "Database": "PostgreSQL 15+",
    "Task Scheduler": "Celery + Redis",
    "Authentication": "OAuth 2.0",
    "Data Processing": "Pandas",
    "Python Version": "3.11+"
}
```

Django Ninja를 선택한 이유는 FastAPI와 유사한 직관적인 문법을 제공하면서도 Django의 강력한 ORM과 생태계를 활용할 수 있기 때문입니다. 특히 자동 API 문서화와 타입 힌팅을 통한 개발 생산성 향상이 큰 장점입니다.

## 📋 1단계: Google Analytics API 설정

### Google Cloud 프로젝트 생성 및 API 활성화

먼저 Google Cloud Console에서 프로젝트를 생성하고 Analytics Data API를 활성화해야 합니다.

```bash
# 1. Google Cloud Console 접속
# https://console.cloud.google.com/

# 2. 새 프로젝트 생성
# - 프로젝트 이름: analytics-report-service
# - 조직: 개인 또는 회사 계정

# 3. Google Analytics Data API 활성화
# API 및 서비스 > 라이브러리 > "Google Analytics Data API" 검색 > 사용 설정

# 4. 서비스 계정 생성
# IAM 및 관리자 > 서비스 계정 > 서비스 계정 만들기
# - 서비스 계정 이름: analytics-reader
# - 역할: 뷰어 (Viewer)

# 5. JSON 키 파일 다운로드
# 서비스 계정 > 키 > 키 추가 > JSON 생성
# 다운로드한 파일을 프로젝트의 credentials/ 폴더에 저장
```

### Google Analytics 4 속성 연결

```python
# Google Analytics 4 관리 페이지에서 설정
# 1. GA4 속성 선택
# 2. 관리 > 속성 액세스 관리
# 3. 서비스 계정 이메일 추가 (예: analytics-reader@project-id.iam.gserviceaccount.com)
# 4. 뷰어 권한 부여
# 5. 속성 ID 확인 (예: 123456789)
```

### 환경 변수 설정

서비스 계정 인증 정보와 GA4 속성 ID를 환경 변수로 관리합니다:

```python
# .env 파일
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials/analytics-service-account.json
GA4_PROPERTY_ID=123456789
DJANGO_SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/analytics_db
REDIS_URL=redis://localhost:6379/0
```

```python
# settings.py - 환경 변수 로드
import os
from pathlib import Path
from environ import Env

env = Env()
env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

# Google Analytics 설정
GOOGLE_APPLICATION_CREDENTIALS = env('GOOGLE_APPLICATION_CREDENTIALS')
GA4_PROPERTY_ID = env('GA4_PROPERTY_ID')

# 보안 설정
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', False)

# 데이터베이스 설정
DATABASES = {
    'default': env.db('DATABASE_URL')
}
```

## 💾 2단계: Django 모델 설계

### Analytics 데이터 모델

GA4에서 수집할 데이터를 저장하기 위한 Django 모델을 설계합니다:

```python
# analytics/models.py
from django.db import models
from django.utils import timezone
from datetime import date

class AnalyticsDailyReport(models.Model):
    """일별 Google Analytics 데이터"""
    
    # 기본 정보
    report_date = models.DateField(
        unique=True,
        db_index=True,
        help_text="데이터 수집 날짜"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 사용자 지표
    total_users = models.IntegerField(
        default=0,
        help_text="총 사용자 수"
    )
    new_users = models.IntegerField(
        default=0,
        help_text="신규 사용자 수"
    )
    active_users = models.IntegerField(
        default=0,
        help_text="활성 사용자 수"
    )
    
    # 세션 지표
    sessions = models.IntegerField(
        default=0,
        help_text="총 세션 수"
    )
    sessions_per_user = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="사용자당 세션 수"
    )
    average_session_duration = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="평균 세션 시간 (초)"
    )
    
    # 페이지뷰 지표
    page_views = models.IntegerField(
        default=0,
        help_text="페이지뷰 수"
    )
    pages_per_session = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="세션당 페이지뷰"
    )
    bounce_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="이탈률 (%)"
    )
    
    # 전환 지표
    conversions = models.IntegerField(
        default=0,
        help_text="전환 수"
    )
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="전환율 (%)"
    )
    
    # 수익 지표
    total_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="총 수익"
    )
    
    class Meta:
        db_table = 'analytics_daily_report'
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['-report_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Analytics Report - {self.report_date}"
    
    @property
    def week_number(self):
        """해당 날짜의 주차 계산"""
        return self.report_date.isocalendar()[1]
    
    @property
    def year(self):
        """해당 날짜의 연도"""
        return self.report_date.year


class WeeklyComparison(models.Model):
    """주간 성과 비교 보고서"""
    
    # 기본 정보
    report_week = models.IntegerField(
        help_text="보고서 주차 (ISO 8601)"
    )
    report_year = models.IntegerField(
        help_text="보고서 연도"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 이번주 데이터
    current_week_start = models.DateField()
    current_week_end = models.DateField()
    current_total_users = models.IntegerField(default=0)
    current_new_users = models.IntegerField(default=0)
    current_sessions = models.IntegerField(default=0)
    current_page_views = models.IntegerField(default=0)
    current_conversions = models.IntegerField(default=0)
    current_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # 지난주 데이터
    previous_week_start = models.DateField()
    previous_week_end = models.DateField()
    previous_total_users = models.IntegerField(default=0)
    previous_new_users = models.IntegerField(default=0)
    previous_sessions = models.IntegerField(default=0)
    previous_page_views = models.IntegerField(default=0)
    previous_conversions = models.IntegerField(default=0)
    previous_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # 변화율 (%)
    users_change_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sessions_change_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    page_views_change_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversions_change_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    revenue_change_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # 인사이트
    summary = models.TextField(
        blank=True,
        help_text="주간 성과 요약"
    )
    
    class Meta:
        db_table = 'weekly_comparison'
        unique_together = [['report_year', 'report_week']]
        ordering = ['-report_year', '-report_week']
    
    def __str__(self):
        return f"Weekly Report - {self.report_year}W{self.report_week:02d}"
```

### 마이그레이션 생성 및 적용

```bash
# 모델 생성 후 마이그레이션 파일 생성
python manage.py makemigrations analytics

# 마이그레이션 적용
python manage.py migrate analytics

# 결과 확인
python manage.py showmigrations analytics
```

## 🔌 3단계: Google Analytics API 클라이언트 구현

### Analytics API 클라이언트 클래스

GA4 API를 사용하여 데이터를 가져오는 클라이언트를 구현합니다:

```python
# analytics/services/ga4_client.py
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
from django.conf import settings
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class GA4Client:
    """Google Analytics 4 API 클라이언트"""
    
    def __init__(self):
        """서비스 계정 인증으로 클라이언트 초기화"""
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        self.property_id = settings.GA4_PROPERTY_ID
    
    def get_daily_report(self, target_date: datetime.date) -> Dict:
        """특정 날짜의 일별 리포트 조회"""
        
        date_str = target_date.strftime('%Y-%m-%d')
        
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="date"),
            ],
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="sessionsPerUser"),
                Metric(name="screenPageViews"),
                Metric(name="screenPageViewsPerSession"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
            date_ranges=[
                DateRange(start_date=date_str, end_date=date_str)
            ],
        )
        
        try:
            response = self.client.run_report(request)
            
            if not response.rows:
                logger.warning(f"No data found for date: {date_str}")
                return self._empty_report(target_date)
            
            row = response.rows[0]
            
            # 메트릭 값 추출
            metrics = row.metric_values
            
            return {
                'report_date': target_date,
                'total_users': int(metrics[0].value),
                'new_users': int(metrics[1].value),
                'active_users': int(metrics[2].value),
                'sessions': int(metrics[3].value),
                'sessions_per_user': float(metrics[4].value),
                'page_views': int(metrics[5].value),
                'pages_per_session': float(metrics[6].value),
                'average_session_duration': float(metrics[7].value),
                'bounce_rate': float(metrics[8].value) * 100,  # 퍼센트로 변환
                'conversions': int(metrics[9].value),
                'total_revenue': float(metrics[10].value),
            }
            
        except Exception as e:
            logger.error(f"Error fetching GA4 data for {date_str}: {str(e)}")
            raise
    
    def get_date_range_report(
        self, 
        start_date: datetime.date, 
        end_date: datetime.date
    ) -> List[Dict]:
        """날짜 범위의 일별 리포트 조회"""
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="date"),
            ],
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="sessionsPerUser"),
                Metric(name="screenPageViews"),
                Metric(name="screenPageViewsPerSession"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
            date_ranges=[
                DateRange(start_date=start_str, end_date=end_str)
            ],
        )
        
        try:
            response = self.client.run_report(request)
            
            results = []
            for row in response.rows:
                date_value = row.dimension_values[0].value
                report_date = datetime.strptime(date_value, '%Y%m%d').date()
                
                metrics = row.metric_values
                
                results.append({
                    'report_date': report_date,
                    'total_users': int(metrics[0].value),
                    'new_users': int(metrics[1].value),
                    'active_users': int(metrics[2].value),
                    'sessions': int(metrics[3].value),
                    'sessions_per_user': float(metrics[4].value),
                    'page_views': int(metrics[5].value),
                    'pages_per_session': float(metrics[6].value),
                    'average_session_duration': float(metrics[7].value),
                    'bounce_rate': float(metrics[8].value) * 100,
                    'conversions': int(metrics[9].value),
                    'total_revenue': float(metrics[10].value),
                })
            
            return results
            
        except Exception as e:
            logger.error(
                f"Error fetching GA4 data from {start_str} to {end_str}: {str(e)}"
            )
            raise
    
    def _empty_report(self, target_date: datetime.date) -> Dict:
        """빈 리포트 반환 (데이터가 없을 때)"""
        return {
            'report_date': target_date,
            'total_users': 0,
            'new_users': 0,
            'active_users': 0,
            'sessions': 0,
            'sessions_per_user': 0.0,
            'page_views': 0,
            'pages_per_session': 0.0,
            'average_session_duration': 0.0,
            'bounce_rate': 0.0,
            'conversions': 0,
            'total_revenue': 0.0,
        }
```

### 데이터 수집 서비스

API 클라이언트를 사용하여 데이터를 수집하고 데이터베이스에 저장하는 서비스:

```python
# analytics/services/data_collector.py
from datetime import datetime, timedelta, date
from typing import Optional
from django.db import transaction
from django.utils import timezone
from analytics.models import AnalyticsDailyReport
from analytics.services.ga4_client import GA4Client
import logging

logger = logging.getLogger(__name__)


class AnalyticsDataCollector:
    """Analytics 데이터 수집 및 저장 서비스"""
    
    def __init__(self):
        self.ga4_client = GA4Client()
    
    def collect_daily_data(self, target_date: Optional[date] = None) -> AnalyticsDailyReport:
        """특정 날짜의 데이터 수집 및 저장"""
        
        if target_date is None:
            # 어제 날짜 (GA4 데이터는 보통 하루 지연됨)
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        logger.info(f"Collecting analytics data for {target_date}")
        
        # GA4에서 데이터 가져오기
        data = self.ga4_client.get_daily_report(target_date)
        
        # 데이터베이스에 저장 (있으면 업데이트, 없으면 생성)
        report, created = AnalyticsDailyReport.objects.update_or_create(
            report_date=target_date,
            defaults=data
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} analytics report for {target_date}")
        
        return report
    
    def collect_date_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> int:
        """날짜 범위의 데이터 일괄 수집"""
        
        logger.info(f"Collecting analytics data from {start_date} to {end_date}")
        
        # GA4에서 범위 데이터 가져오기
        reports_data = self.ga4_client.get_date_range_report(start_date, end_date)
        
        # 데이터베이스에 일괄 저장
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for data in reports_data:
                report, created = AnalyticsDailyReport.objects.update_or_create(
                    report_date=data['report_date'],
                    defaults=data
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        logger.info(
            f"Bulk collection completed: "
            f"{created_count} created, {updated_count} updated"
        )
        
        return len(reports_data)
    
    def collect_last_n_days(self, days: int = 7) -> int:
        """최근 N일간의 데이터 수집"""
        
        end_date = (timezone.now() - timedelta(days=1)).date()
        start_date = end_date - timedelta(days=days - 1)
        
        return self.collect_date_range(start_date, end_date)
    
    def backfill_missing_dates(
        self, 
        start_date: date, 
        end_date: Optional[date] = None
    ) -> int:
        """누락된 날짜의 데이터 보충"""
        
        if end_date is None:
            end_date = (timezone.now() - timedelta(days=1)).date()
        
        # 이미 존재하는 날짜들 조회
        existing_dates = set(
            AnalyticsDailyReport.objects.filter(
                report_date__range=[start_date, end_date]
            ).values_list('report_date', flat=True)
        )
        
        # 누락된 날짜들 찾기
        current_date = start_date
        missing_dates = []
        
        while current_date <= end_date:
            if current_date not in existing_dates:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)
        
        if not missing_dates:
            logger.info("No missing dates found")
            return 0
        
        logger.info(f"Found {len(missing_dates)} missing dates, backfilling...")
        
        # 누락된 날짜들 수집
        collected_count = 0
        for missing_date in missing_dates:
            try:
                self.collect_daily_data(missing_date)
                collected_count += 1
            except Exception as e:
                logger.error(f"Error collecting data for {missing_date}: {str(e)}")
        
        logger.info(f"Backfill completed: {collected_count} reports collected")
        
        return collected_count
```

## 📊 4단계: 주간 성과 비교 로직 구현

### 주간 데이터 집계 서비스

지난주와 이번주의 데이터를 집계하고 비교하는 서비스를 구현합니다:

```python
# analytics/services/weekly_analyzer.py
from datetime import datetime, timedelta, date
from typing import Dict, Tuple
from decimal import Decimal
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from analytics.models import AnalyticsDailyReport, WeeklyComparison
import logging

logger = logging.getLogger(__name__)


class WeeklyAnalyzer:
    """주간 성과 분석 및 비교 서비스"""
    
    @staticmethod
    def get_week_boundaries(target_date: date) -> Tuple[date, date]:
        """주차의 시작일(월요일)과 종료일(일요일) 계산"""
        # ISO 8601: 월요일이 주의 시작
        weekday = target_date.weekday()  # 0 = 월요일, 6 = 일요일
        week_start = target_date - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
    
    def aggregate_week_data(self, start_date: date, end_date: date) -> Dict:
        """특정 주차의 데이터 집계"""
        
        reports = AnalyticsDailyReport.objects.filter(
            report_date__range=[start_date, end_date]
        )
        
        if not reports.exists():
            logger.warning(f"No data found for week {start_date} to {end_date}")
            return self._empty_week_data(start_date, end_date)
        
        # 합계 지표 집계
        aggregated = reports.aggregate(
            total_users=Sum('total_users'),
            new_users=Sum('new_users'),
            sessions=Sum('sessions'),
            page_views=Sum('page_views'),
            conversions=Sum('conversions'),
            revenue=Sum('total_revenue'),
        )
        
        # 평균 지표 집계
        averages = reports.aggregate(
            avg_session_duration=Avg('average_session_duration'),
            avg_bounce_rate=Avg('bounce_rate'),
            avg_sessions_per_user=Avg('sessions_per_user'),
        )
        
        return {
            'week_start': start_date,
            'week_end': end_date,
            'total_users': aggregated['total_users'] or 0,
            'new_users': aggregated['new_users'] or 0,
            'sessions': aggregated['sessions'] or 0,
            'page_views': aggregated['page_views'] or 0,
            'conversions': aggregated['conversions'] or 0,
            'revenue': aggregated['revenue'] or Decimal('0'),
            'avg_session_duration': averages['avg_session_duration'] or 0,
            'avg_bounce_rate': averages['avg_bounce_rate'] or 0,
            'avg_sessions_per_user': averages['avg_sessions_per_user'] or 0,
            'data_points': reports.count(),
        }
    
    def calculate_change_rate(
        self, 
        current_value: float, 
        previous_value: float
    ) -> Decimal:
        """변화율 계산 (%)"""
        
        if previous_value == 0:
            if current_value == 0:
                return Decimal('0')
            return Decimal('100')  # 0에서 값이 생긴 경우
        
        change = ((current_value - previous_value) / previous_value) * 100
        return Decimal(str(round(change, 2)))
    
    def generate_weekly_comparison(
        self, 
        target_date: Optional[date] = None
    ) -> WeeklyComparison:
        """주간 비교 보고서 생성"""
        
        if target_date is None:
            target_date = timezone.now().date()
        
        # 이번주와 지난주의 범위 계산
        current_start, current_end = self.get_week_boundaries(target_date)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_end - timedelta(days=7)
        
        logger.info(
            f"Generating weekly comparison: "
            f"Current ({current_start} to {current_end}) vs "
            f"Previous ({previous_start} to {previous_end})"
        )
        
        # 이번주 데이터 집계
        current_data = self.aggregate_week_data(current_start, current_end)
        
        # 지난주 데이터 집계
        previous_data = self.aggregate_week_data(previous_start, previous_end)
        
        # 변화율 계산
        users_change = self.calculate_change_rate(
            current_data['total_users'],
            previous_data['total_users']
        )
        sessions_change = self.calculate_change_rate(
            current_data['sessions'],
            previous_data['sessions']
        )
        page_views_change = self.calculate_change_rate(
            current_data['page_views'],
            previous_data['page_views']
        )
        conversions_change = self.calculate_change_rate(
            current_data['conversions'],
            previous_data['conversions']
        )
        revenue_change = self.calculate_change_rate(
            float(current_data['revenue']),
            float(previous_data['revenue'])
        )
        
        # 인사이트 생성
        summary = self._generate_summary(
            current_data, previous_data,
            users_change, sessions_change, revenue_change
        )
        
        # 보고서 저장
        year, week, _ = current_start.isocalendar()
        
        comparison, created = WeeklyComparison.objects.update_or_create(
            report_year=year,
            report_week=week,
            defaults={
                # 이번주 데이터
                'current_week_start': current_start,
                'current_week_end': current_end,
                'current_total_users': current_data['total_users'],
                'current_new_users': current_data['new_users'],
                'current_sessions': current_data['sessions'],
                'current_page_views': current_data['page_views'],
                'current_conversions': current_data['conversions'],
                'current_revenue': current_data['revenue'],
                
                # 지난주 데이터
                'previous_week_start': previous_start,
                'previous_week_end': previous_end,
                'previous_total_users': previous_data['total_users'],
                'previous_new_users': previous_data['new_users'],
                'previous_sessions': previous_data['sessions'],
                'previous_page_views': previous_data['page_views'],
                'previous_conversions': previous_data['conversions'],
                'previous_revenue': previous_data['revenue'],
                
                # 변화율
                'users_change_rate': users_change,
                'sessions_change_rate': sessions_change,
                'page_views_change_rate': page_views_change,
                'conversions_change_rate': conversions_change,
                'revenue_change_rate': revenue_change,
                
                # 인사이트
                'summary': summary,
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} weekly comparison for {year}W{week:02d}")
        
        return comparison
    
    def _generate_summary(
        self,
        current: Dict,
        previous: Dict,
        users_change: Decimal,
        sessions_change: Decimal,
        revenue_change: Decimal
    ) -> str:
        """주간 성과 요약 생성"""
        
        summary_parts = []
        
        # 사용자 증감
        if users_change > 0:
            summary_parts.append(
                f"총 사용자가 지난주 대비 {users_change}% 증가했습니다. "
                f"({previous['total_users']:,} → {current['total_users']:,})"
            )
        elif users_change < 0:
            summary_parts.append(
                f"총 사용자가 지난주 대비 {abs(users_change)}% 감소했습니다. "
                f"({previous['total_users']:,} → {current['total_users']:,})"
            )
        else:
            summary_parts.append("총 사용자는 지난주와 동일합니다.")
        
        # 세션 증감
        if sessions_change > 10:
            summary_parts.append(
                f"세션이 {sessions_change}% 크게 증가하여 사용자 참여도가 향상되었습니다."
            )
        elif sessions_change < -10:
            summary_parts.append(
                f"세션이 {abs(sessions_change)}% 감소했습니다. 사용자 참여 전략 재검토가 필요합니다."
            )
        
        # 수익 증감
        if revenue_change > 0:
            summary_parts.append(
                f"수익이 {revenue_change}% 증가했습니다. "
                f"(₩{float(previous['revenue']):,.0f} → ₩{float(current['revenue']):,.0f})"
            )
        elif revenue_change < 0:
            summary_parts.append(
                f"수익이 {abs(revenue_change)}% 감소했습니다. "
                f"전환 최적화가 필요합니다."
            )
        
        # 주요 지표 요약
        conversion_rate = (
            (current['conversions'] / current['sessions'] * 100)
            if current['sessions'] > 0 else 0
        )
        
        summary_parts.append(
            f"\n\n이번주 주요 지표:\n"
            f"- 전환율: {conversion_rate:.2f}%\n"
            f"- 평균 세션 시간: {current['avg_session_duration']:.0f}초\n"
            f"- 이탈률: {current['avg_bounce_rate']:.2f}%"
        )
        
        return " ".join(summary_parts)
    
    def _empty_week_data(self, start_date: date, end_date: date) -> Dict:
        """빈 주간 데이터 반환"""
        return {
            'week_start': start_date,
            'week_end': end_date,
            'total_users': 0,
            'new_users': 0,
            'sessions': 0,
            'page_views': 0,
            'conversions': 0,
            'revenue': Decimal('0'),
            'avg_session_duration': 0,
            'avg_bounce_rate': 0,
            'avg_sessions_per_user': 0,
            'data_points': 0,
        }
```

## 🚀 5단계: Django Ninja API 엔드포인트 구현

### Pydantic 스키마 정의

API 요청/응답에 사용할 스키마를 정의합니다:

```python
# analytics/schemas.py
from ninja import Schema
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


class DailyReportResponse(Schema):
    """일별 리포트 응답 스키마"""
    report_date: date
    total_users: int
    new_users: int
    active_users: int
    sessions: int
    sessions_per_user: Decimal
    page_views: int
    pages_per_session: Decimal
    average_session_duration: Decimal
    bounce_rate: Decimal
    conversions: int
    conversion_rate: Decimal
    total_revenue: Decimal
    created_at: datetime
    updated_at: datetime


class WeeklyComparisonResponse(Schema):
    """주간 비교 응답 스키마"""
    report_year: int
    report_week: int
    
    # 이번주
    current_week_start: date
    current_week_end: date
    current_total_users: int
    current_new_users: int
    current_sessions: int
    current_page_views: int
    current_conversions: int
    current_revenue: Decimal
    
    # 지난주
    previous_week_start: date
    previous_week_end: date
    previous_total_users: int
    previous_new_users: int
    previous_sessions: int
    previous_page_views: int
    previous_conversions: int
    previous_revenue: Decimal
    
    # 변화율
    users_change_rate: Decimal
    sessions_change_rate: Decimal
    page_views_change_rate: Decimal
    conversions_change_rate: Decimal
    revenue_change_rate: Decimal
    
    # 인사이트
    summary: str
    created_at: datetime


class CollectionTriggerResponse(Schema):
    """데이터 수집 트리거 응답"""
    success: bool
    message: str
    collected_count: int
    target_date: Optional[date] = None


class ErrorResponse(Schema):
    """에러 응답 스키마"""
    error: str
    detail: Optional[str] = None


class DateRangeRequest(Schema):
    """날짜 범위 요청 스키마"""
    start_date: date
    end_date: date


class DailyReportListResponse(Schema):
    """일별 리포트 목록 응답"""
    count: int
    reports: List[DailyReportResponse]
```

### API 라우터 구현

Django Ninja를 사용한 RESTful API 엔드포인트를 구현합니다:

```python
# analytics/api.py
from ninja import NinjaAPI, Query
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date, timedelta
from typing import List, Optional
import logging

from analytics.models import AnalyticsDailyReport, WeeklyComparison
from analytics.schemas import (
    DailyReportResponse,
    WeeklyComparisonResponse,
    CollectionTriggerResponse,
    ErrorResponse,
    DateRangeRequest,
    DailyReportListResponse,
)
from analytics.services.data_collector import AnalyticsDataCollector
from analytics.services.weekly_analyzer import WeeklyAnalyzer

logger = logging.getLogger(__name__)

# API 인스턴스 생성
api = NinjaAPI(
    title="Analytics Report API",
    version="1.0.0",
    description="Google Analytics 데이터 수집 및 주간 성과 비교 API"
)


# ===== 일별 리포트 API =====

@api.get(
    "/reports/daily/{report_date}",
    response={200: DailyReportResponse, 404: ErrorResponse},
    tags=["Daily Reports"]
)
def get_daily_report(request, report_date: date):
    """특정 날짜의 일별 리포트 조회"""
    
    try:
        report = get_object_or_404(AnalyticsDailyReport, report_date=report_date)
        return 200, report
    except Exception as e:
        logger.error(f"Error fetching daily report: {str(e)}")
        return 404, {"error": "Report not found", "detail": str(e)}


@api.get(
    "/reports/daily",
    response={200: DailyReportListResponse, 400: ErrorResponse},
    tags=["Daily Reports"]
)
def list_daily_reports(
    request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(30, ge=1, le=365)
):
    """일별 리포트 목록 조회 (기본: 최근 30일)"""
    
    try:
        if end_date is None:
            end_date = timezone.now().date()
        
        if start_date is None:
            start_date = end_date - timedelta(days=limit - 1)
        
        reports = AnalyticsDailyReport.objects.filter(
            report_date__range=[start_date, end_date]
        ).order_by('-report_date')[:limit]
        
        return 200, {
            "count": reports.count(),
            "reports": list(reports)
        }
    
    except Exception as e:
        logger.error(f"Error listing daily reports: {str(e)}")
        return 400, {"error": "Invalid request", "detail": str(e)}


@api.post(
    "/reports/daily/collect",
    response={200: CollectionTriggerResponse, 400: ErrorResponse},
    tags=["Daily Reports"]
)
def trigger_daily_collection(
    request,
    target_date: Optional[date] = Query(None, description="수집할 날짜 (기본: 어제)")
):
    """일별 데이터 수집 트리거"""
    
    try:
        collector = AnalyticsDataCollector()
        report = collector.collect_daily_data(target_date)
        
        return 200, {
            "success": True,
            "message": f"Successfully collected data for {report.report_date}",
            "collected_count": 1,
            "target_date": report.report_date
        }
    
    except Exception as e:
        logger.error(f"Error collecting daily data: {str(e)}")
        return 400, {"error": "Collection failed", "detail": str(e)}


@api.post(
    "/reports/daily/collect-range",
    response={200: CollectionTriggerResponse, 400: ErrorResponse},
    tags=["Daily Reports"]
)
def trigger_range_collection(request, payload: DateRangeRequest):
    """날짜 범위 데이터 일괄 수집"""
    
    try:
        collector = AnalyticsDataCollector()
        count = collector.collect_date_range(
            payload.start_date,
            payload.end_date
        )
        
        return 200, {
            "success": True,
            "message": f"Successfully collected {count} reports",
            "collected_count": count,
            "target_date": None
        }
    
    except Exception as e:
        logger.error(f"Error collecting range data: {str(e)}")
        return 400, {"error": "Range collection failed", "detail": str(e)}


# ===== 주간 비교 API =====

@api.get(
    "/reports/weekly/current",
    response={200: WeeklyComparisonResponse, 404: ErrorResponse},
    tags=["Weekly Reports"]
)
def get_current_week_comparison(request):
    """현재 주차의 주간 비교 리포트 조회"""
    
    try:
        today = timezone.now().date()
        year, week, _ = today.isocalendar()
        
        comparison = get_object_or_404(
            WeeklyComparison,
            report_year=year,
            report_week=week
        )
        
        return 200, comparison
    
    except Exception as e:
        logger.error(f"Error fetching current week comparison: {str(e)}")
        return 404, {"error": "Comparison not found", "detail": str(e)}


@api.get(
    "/reports/weekly/{year}/{week}",
    response={200: WeeklyComparisonResponse, 404: ErrorResponse},
    tags=["Weekly Reports"]
)
def get_weekly_comparison(request, year: int, week: int):
    """특정 주차의 주간 비교 리포트 조회"""
    
    try:
        comparison = get_object_or_404(
            WeeklyComparison,
            report_year=year,
            report_week=week
        )
        
        return 200, comparison
    
    except Exception as e:
        logger.error(f"Error fetching weekly comparison: {str(e)}")
        return 404, {"error": "Comparison not found", "detail": str(e)}


@api.get(
    "/reports/weekly/list",
    response={200: List[WeeklyComparisonResponse], 400: ErrorResponse},
    tags=["Weekly Reports"]
)
def list_weekly_comparisons(
    request,
    limit: int = Query(12, ge=1, le=52, description="조회할 주차 수")
):
    """주간 비교 리포트 목록 조회"""
    
    try:
        comparisons = WeeklyComparison.objects.all().order_by(
            '-report_year',
            '-report_week'
        )[:limit]
        
        return 200, list(comparisons)
    
    except Exception as e:
        logger.error(f"Error listing weekly comparisons: {str(e)}")
        return 400, {"error": "Invalid request", "detail": str(e)}


@api.post(
    "/reports/weekly/generate",
    response={200: WeeklyComparisonResponse, 400: ErrorResponse},
    tags=["Weekly Reports"]
)
def generate_weekly_comparison(
    request,
    target_date: Optional[date] = Query(None, description="분석할 주차의 날짜")
):
    """주간 비교 리포트 생성"""
    
    try:
        analyzer = WeeklyAnalyzer()
        comparison = analyzer.generate_weekly_comparison(target_date)
        
        return 200, comparison
    
    except Exception as e:
        logger.error(f"Error generating weekly comparison: {str(e)}")
        return 400, {"error": "Generation failed", "detail": str(e)}


# ===== 헬스체크 API =====

@api.get("/health", tags=["System"])
def health_check(request):
    """API 헬스체크"""
    return {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "version": "1.0.0"
    }


@api.get("/stats", tags=["System"])
def get_statistics(request):
    """데이터베이스 통계"""
    
    daily_report_count = AnalyticsDailyReport.objects.count()
    weekly_comparison_count = WeeklyComparison.objects.count()
    
    latest_report = AnalyticsDailyReport.objects.order_by('-report_date').first()
    latest_comparison = WeeklyComparison.objects.order_by(
        '-report_year', '-report_week'
    ).first()
    
    return {
        "daily_reports_count": daily_report_count,
        "weekly_comparisons_count": weekly_comparison_count,
        "latest_report_date": latest_report.report_date if latest_report else None,
        "latest_comparison_week": (
            f"{latest_comparison.report_year}W{latest_comparison.report_week:02d}"
            if latest_comparison else None
        )
    }
```

### URL 설정

```python
# urls.py (프로젝트 루트)
from django.contrib import admin
from django.urls import path
from analytics.api import api as analytics_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', analytics_api.urls),  # API 라우트 등록
]
```

## ⚙️ 6단계: Celery를 통한 자동화 및 스케줄링

### Celery 설정

정기적인 데이터 수집을 위해 Celery와 Celery Beat를 설정합니다:

```python
# celery.py (프로젝트 루트)
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('analytics_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    'collect-daily-analytics': {
        'task': 'analytics.tasks.collect_yesterday_data',
        'schedule': crontab(hour=2, minute=0),  # 매일 오전 2시
    },
    'generate-weekly-report': {
        'task': 'analytics.tasks.generate_weekly_report',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),  # 매주 월요일 오전 3시
    },
}

app.conf.timezone = 'Asia/Seoul'
```

### Celery 태스크 구현

```python
# analytics/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from analytics.services.data_collector import AnalyticsDataCollector
from analytics.services.weekly_analyzer import WeeklyAnalyzer
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def collect_yesterday_data(self):
    """어제 날짜의 Analytics 데이터 수집"""
    
    try:
        yesterday = (timezone.now() - timedelta(days=1)).date()
        
        logger.info(f"Starting daily data collection for {yesterday}")
        
        collector = AnalyticsDataCollector()
        report = collector.collect_daily_data(yesterday)
        
        logger.info(
            f"Successfully collected data for {yesterday}: "
            f"{report.total_users} users, {report.sessions} sessions"
        )
        
        return {
            'success': True,
            'date': str(yesterday),
            'users': report.total_users,
            'sessions': report.sessions
        }
    
    except Exception as e:
        logger.error(f"Error in daily collection task: {str(e)}")
        
        # 재시도 (최대 3회)
        raise self.retry(exc=e, countdown=300)  # 5분 후 재시도


@shared_task(bind=True, max_retries=3)
def collect_date_range(self, start_date_str: str, end_date_str: str):
    """날짜 범위의 데이터 수집 (비동기)"""
    
    from datetime import datetime
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        logger.info(f"Starting range collection from {start_date} to {end_date}")
        
        collector = AnalyticsDataCollector()
        count = collector.collect_date_range(start_date, end_date)
        
        logger.info(f"Successfully collected {count} reports")
        
        return {
            'success': True,
            'count': count,
            'start_date': start_date_str,
            'end_date': end_date_str
        }
    
    except Exception as e:
        logger.error(f"Error in range collection task: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def generate_weekly_report(self):
    """주간 비교 리포트 생성"""
    
    try:
        today = timezone.now().date()
        
        logger.info(f"Starting weekly report generation for week of {today}")
        
        # 먼저 지난주와 이번주 데이터가 모두 있는지 확인
        analyzer = WeeklyAnalyzer()
        comparison = analyzer.generate_weekly_comparison(today)
        
        logger.info(
            f"Successfully generated weekly report for "
            f"{comparison.report_year}W{comparison.report_week:02d}"
        )
        
        return {
            'success': True,
            'year': comparison.report_year,
            'week': comparison.report_week,
            'users_change': float(comparison.users_change_rate),
            'revenue_change': float(comparison.revenue_change_rate)
        }
    
    except Exception as e:
        logger.error(f"Error in weekly report task: {str(e)}")
        raise self.retry(exc=e, countdown=600)  # 10분 후 재시도


@shared_task
def backfill_missing_data(start_date_str: str, end_date_str: str = None):
    """누락된 데이터 보충"""
    
    from datetime import datetime
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = (
            datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if end_date_str else None
        )
        
        logger.info(f"Starting backfill from {start_date}")
        
        collector = AnalyticsDataCollector()
        count = collector.backfill_missing_dates(start_date, end_date)
        
        logger.info(f"Backfilled {count} missing reports")
        
        return {
            'success': True,
            'backfilled_count': count
        }
    
    except Exception as e:
        logger.error(f"Error in backfill task: {str(e)}")
        raise
```

### Celery 실행 명령어

```bash
# Celery Worker 실행 (비동기 작업 처리)
celery -A config worker --loglevel=info

# Celery Beat 실행 (스케줄러)
celery -A config beat --loglevel=info

# 또는 하나의 명령어로 실행
celery -A config worker -B --loglevel=info

# 프로덕션 환경에서는 별도 프로세스로 실행 권장
# Worker
celery -A config worker --loglevel=info --concurrency=4

# Beat (스케줄러)
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 📈 7단계: Django Admin 인터페이스 구성

### Admin 설정

수집된 데이터를 관리하기 위한 Django Admin 인터페이스를 구성합니다:

```python
# analytics/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Avg
from analytics.models import AnalyticsDailyReport, WeeklyComparison


@admin.register(AnalyticsDailyReport)
class AnalyticsDailyReportAdmin(admin.ModelAdmin):
    """일별 리포트 관리"""
    
    list_display = [
        'report_date',
        'total_users_formatted',
        'new_users_formatted',
        'sessions_formatted',
        'page_views_formatted',
        'conversions_formatted',
        'revenue_formatted',
        'bounce_rate_formatted',
        'created_at',
    ]
    
    list_filter = [
        'report_date',
        'created_at',
    ]
    
    search_fields = [
        'report_date',
    ]
    
    readonly_fields = [
        'report_date',
        'created_at',
        'updated_at',
    ]
    
    date_hierarchy = 'report_date'
    
    ordering = ['-report_date']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('report_date', 'created_at', 'updated_at')
        }),
        ('사용자 지표', {
            'fields': (
                'total_users',
                'new_users',
                'active_users',
            )
        }),
        ('세션 지표', {
            'fields': (
                'sessions',
                'sessions_per_user',
                'average_session_duration',
            )
        }),
        ('페이지뷰 지표', {
            'fields': (
                'page_views',
                'pages_per_session',
                'bounce_rate',
            )
        }),
        ('전환 & 수익', {
            'fields': (
                'conversions',
                'conversion_rate',
                'total_revenue',
            )
        }),
    )
    
    def total_users_formatted(self, obj):
        return f"{obj.total_users:,}"
    total_users_formatted.short_description = '총 사용자'
    total_users_formatted.admin_order_field = 'total_users'
    
    def new_users_formatted(self, obj):
        return f"{obj.new_users:,}"
    new_users_formatted.short_description = '신규 사용자'
    new_users_formatted.admin_order_field = 'new_users'
    
    def sessions_formatted(self, obj):
        return f"{obj.sessions:,}"
    sessions_formatted.short_description = '세션'
    sessions_formatted.admin_order_field = 'sessions'
    
    def page_views_formatted(self, obj):
        return f"{obj.page_views:,}"
    page_views_formatted.short_description = '페이지뷰'
    page_views_formatted.admin_order_field = 'page_views'
    
    def conversions_formatted(self, obj):
        return f"{obj.conversions:,}"
    conversions_formatted.short_description = '전환'
    conversions_formatted.admin_order_field = 'conversions'
    
    def revenue_formatted(self, obj):
        return f"₩{obj.total_revenue:,.0f}"
    revenue_formatted.short_description = '수익'
    revenue_formatted.admin_order_field = 'total_revenue'
    
    def bounce_rate_formatted(self, obj):
        return f"{obj.bounce_rate:.2f}%"
    bounce_rate_formatted.short_description = '이탈률'
    bounce_rate_formatted.admin_order_field = 'bounce_rate'
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related()
    
    def changelist_view(self, request, extra_context=None):
        """목록 뷰에 집계 정보 추가"""
        extra_context = extra_context or {}
        
        # 현재 필터링된 쿼리셋의 집계
        cl = self.get_changelist_instance(request)
        queryset = cl.get_queryset(request)
        
        stats = queryset.aggregate(
            total_users=Sum('total_users'),
            total_sessions=Sum('sessions'),
            total_page_views=Sum('page_views'),
            total_conversions=Sum('conversions'),
            total_revenue=Sum('total_revenue'),
            avg_bounce_rate=Avg('bounce_rate'),
        )
        
        extra_context['stats'] = stats
        
        return super().changelist_view(request, extra_context)


@admin.register(WeeklyComparison)
class WeeklyComparisonAdmin(admin.ModelAdmin):
    """주간 비교 관리"""
    
    list_display = [
        'week_identifier',
        'date_range',
        'users_comparison',
        'sessions_comparison',
        'revenue_comparison',
        'performance_indicator',
        'created_at',
    ]
    
    list_filter = [
        'report_year',
        'created_at',
    ]
    
    search_fields = [
        'report_year',
        'report_week',
    ]
    
    readonly_fields = [
        'report_year',
        'report_week',
        'created_at',
    ]
    
    ordering = ['-report_year', '-report_week']
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'report_year',
                'report_week',
                'created_at',
            )
        }),
        ('이번주 데이터', {
            'fields': (
                ('current_week_start', 'current_week_end'),
                'current_total_users',
                'current_new_users',
                'current_sessions',
                'current_page_views',
                'current_conversions',
                'current_revenue',
            )
        }),
        ('지난주 데이터', {
            'fields': (
                ('previous_week_start', 'previous_week_end'),
                'previous_total_users',
                'previous_new_users',
                'previous_sessions',
                'previous_page_views',
                'previous_conversions',
                'previous_revenue',
            )
        }),
        ('변화율', {
            'fields': (
                'users_change_rate',
                'sessions_change_rate',
                'page_views_change_rate',
                'conversions_change_rate',
                'revenue_change_rate',
            )
        }),
        ('인사이트', {
            'fields': ('summary',)
        }),
    )
    
    def week_identifier(self, obj):
        return f"{obj.report_year}W{obj.report_week:02d}"
    week_identifier.short_description = '주차'
    week_identifier.admin_order_field = 'report_week'
    
    def date_range(self, obj):
        return f"{obj.current_week_start} ~ {obj.current_week_end}"
    date_range.short_description = '기간'
    
    def users_comparison(self, obj):
        change = obj.users_change_rate
        arrow = '↑' if change > 0 else '↓' if change < 0 else '→'
        color = 'green' if change > 0 else 'red' if change < 0 else 'gray'
        
        return format_html(
            '<span style="color: {};">{:,} {} {:,} ({}{}%)</span>',
            color,
            obj.previous_total_users,
            arrow,
            obj.current_total_users,
            '+' if change > 0 else '',
            change
        )
    users_comparison.short_description = '사용자 변화'
    
    def sessions_comparison(self, obj):
        change = obj.sessions_change_rate
        arrow = '↑' if change > 0 else '↓' if change < 0 else '→'
        color = 'green' if change > 0 else 'red' if change < 0 else 'gray'
        
        return format_html(
            '<span style="color: {};">{:,} {} {:,} ({}{}%)</span>',
            color,
            obj.previous_sessions,
            arrow,
            obj.current_sessions,
            '+' if change > 0 else '',
            change
        )
    sessions_comparison.short_description = '세션 변화'
    
    def revenue_comparison(self, obj):
        change = obj.revenue_change_rate
        arrow = '↑' if change > 0 else '↓' if change < 0 else '→'
        color = 'green' if change > 0 else 'red' if change < 0 else 'gray'
        
        return format_html(
            '<span style="color: {};">₩{:,.0f} {} ₩{:,.0f} ({}{}%)</span>',
            color,
            obj.previous_revenue,
            arrow,
            obj.current_revenue,
            '+' if change > 0 else '',
            change
        )
    revenue_comparison.short_description = '수익 변화'
    
    def performance_indicator(self, obj):
        """종합 성과 지표"""
        # 주요 지표들의 평균 변화율
        avg_change = (
            obj.users_change_rate +
            obj.sessions_change_rate +
            obj.revenue_change_rate
        ) / 3
        
        if avg_change > 10:
            return format_html('<span style="color: green; font-weight: bold;">📈 우수</span>')
        elif avg_change > 0:
            return format_html('<span style="color: blue;">📊 양호</span>')
        elif avg_change > -10:
            return format_html('<span style="color: orange;">📉 보통</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ 주의</span>')
    
    performance_indicator.short_description = '성과'
```

## 🧪 8단계: 테스트 및 운영

### 유닛 테스트 작성

```python
# analytics/tests/test_services.py
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from analytics.models import AnalyticsDailyReport, WeeklyComparison
from analytics.services.data_collector import AnalyticsDataCollector
from analytics.services.weekly_analyzer import WeeklyAnalyzer


class DataCollectorTestCase(TestCase):
    """데이터 수집 서비스 테스트"""
    
    def setUp(self):
        self.collector = AnalyticsDataCollector()
        self.test_date = date(2026, 3, 10)
    
    @patch('analytics.services.data_collector.GA4Client')
    def test_collect_daily_data(self, mock_ga4):
        """일별 데이터 수집 테스트"""
        
        # Mock 데이터 설정
        mock_ga4.return_value.get_daily_report.return_value = {
            'report_date': self.test_date,
            'total_users': 1000,
            'new_users': 200,
            'active_users': 800,
            'sessions': 1500,
            'sessions_per_user': 1.5,
            'page_views': 5000,
            'pages_per_session': 3.33,
            'average_session_duration': 120.5,
            'bounce_rate': 45.2,
            'conversions': 50,
            'total_revenue': 100000.0,
        }
        
        # 데이터 수집 실행
        report = self.collector.collect_daily_data(self.test_date)
        
        # 검증
        self.assertEqual(report.report_date, self.test_date)
        self.assertEqual(report.total_users, 1000)
        self.assertEqual(report.new_users, 200)
        self.assertEqual(report.sessions, 1500)
        self.assertEqual(report.conversions, 50)
        
        # DB에 저장되었는지 확인
        self.assertTrue(
            AnalyticsDailyReport.objects.filter(
                report_date=self.test_date
            ).exists()
        )


class WeeklyAnalyzerTestCase(TestCase):
    """주간 분석 서비스 테스트"""
    
    def setUp(self):
        self.analyzer = WeeklyAnalyzer()
        
        # 테스트 데이터 생성 (2주간)
        base_date = date(2026, 3, 3)  # 월요일
        
        for i in range(14):
            current_date = base_date + timedelta(days=i)
            AnalyticsDailyReport.objects.create(
                report_date=current_date,
                total_users=1000 + i * 10,
                new_users=200 + i * 5,
                sessions=1500 + i * 20,
                page_views=5000 + i * 50,
                conversions=50 + i,
                total_revenue=100000 + i * 1000,
                sessions_per_user=1.5,
                average_session_duration=120,
                bounce_rate=45.0,
            )
    
    def test_get_week_boundaries(self):
        """주차 경계 계산 테스트"""
        
        test_date = date(2026, 3, 11)  # 수요일
        start, end = self.analyzer.get_week_boundaries(test_date)
        
        self.assertEqual(start, date(2026, 3, 9))  # 월요일
        self.assertEqual(end, date(2026, 3, 15))   # 일요일
    
    def test_aggregate_week_data(self):
        """주간 데이터 집계 테스트"""
        
        start_date = date(2026, 3, 3)
        end_date = date(2026, 3, 9)
        
        result = self.analyzer.aggregate_week_data(start_date, end_date)
        
        self.assertEqual(result['week_start'], start_date)
        self.assertEqual(result['week_end'], end_date)
        self.assertGreater(result['total_users'], 0)
        self.assertGreater(result['sessions'], 0)
        self.assertEqual(result['data_points'], 7)  # 7일
    
    def test_calculate_change_rate(self):
        """변화율 계산 테스트"""
        
        # 증가
        change = self.analyzer.calculate_change_rate(150, 100)
        self.assertEqual(change, Decimal('50.00'))
        
        # 감소
        change = self.analyzer.calculate_change_rate(75, 100)
        self.assertEqual(change, Decimal('-25.00'))
        
        # 동일
        change = self.analyzer.calculate_change_rate(100, 100)
        self.assertEqual(change, Decimal('0'))
        
        # 0에서 값 생성
        change = self.analyzer.calculate_change_rate(100, 0)
        self.assertEqual(change, Decimal('100'))
    
    def test_generate_weekly_comparison(self):
        """주간 비교 생성 테스트"""
        
        target_date = date(2026, 3, 11)  # 두 번째 주
        comparison = self.analyzer.generate_weekly_comparison(target_date)
        
        self.assertIsInstance(comparison, WeeklyComparison)
        self.assertEqual(comparison.report_year, 2026)
        self.assertGreater(comparison.current_total_users, 0)
        self.assertGreater(comparison.previous_total_users, 0)
        self.assertIsNotNone(comparison.users_change_rate)
        self.assertIsNotNone(comparison.summary)
```

### API 테스트

```python
# analytics/tests/test_api.py
from django.test import TestCase
from ninja.testing import TestClient
from datetime import date, timedelta

from analytics.api import api
from analytics.models import AnalyticsDailyReport, WeeklyComparison


class APITestCase(TestCase):
    """API 엔드포인트 테스트"""
    
    def setUp(self):
        self.client = TestClient(api)
        
        # 테스트 데이터 생성
        self.test_date = date(2026, 3, 10)
        self.report = AnalyticsDailyReport.objects.create(
            report_date=self.test_date,
            total_users=1000,
            new_users=200,
            sessions=1500,
            page_views=5000,
            conversions=50,
            total_revenue=100000,
            sessions_per_user=1.5,
            average_session_duration=120,
            bounce_rate=45.0,
        )
    
    def test_get_daily_report(self):
        """일별 리포트 조회 API 테스트"""
        
        response = self.client.get(f"/reports/daily/{self.test_date}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_users'], 1000)
        self.assertEqual(data['sessions'], 1500)
    
    def test_list_daily_reports(self):
        """일별 리포트 목록 API 테스트"""
        
        response = self.client.get("/reports/daily")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data['count'], 0)
        self.assertIsInstance(data['reports'], list)
    
    def test_health_check(self):
        """헬스체크 API 테스트"""
        
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_get_statistics(self):
        """통계 API 테스트"""
        
        response = self.client.get("/stats")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data['daily_reports_count'], 1)
```

### 실제 운영 명령어

```bash
# 1. 프로젝트 초기 설정
python manage.py migrate
python manage.py createsuperuser

# 2. 과거 데이터 백필 (최근 30일)
python manage.py shell
>>> from analytics.services.data_collector import AnalyticsDataCollector
>>> from datetime import date, timedelta
>>> collector = AnalyticsDataCollector()
>>> collector.collect_last_n_days(30)

# 3. 주간 보고서 생성
>>> from analytics.services.weekly_analyzer import WeeklyAnalyzer
>>> analyzer = WeeklyAnalyzer()
>>> analyzer.generate_weekly_comparison()

# 4. 개발 서버 실행
python manage.py runserver

# 5. API 문서 확인
# http://localhost:8000/api/docs

# 6. Celery 실행 (백그라운드 작업)
celery -A config worker -B --loglevel=info

# 7. 프로덕션 배포 (Gunicorn + Nginx)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## 🎨 9단계: 결과 시각화 및 보고서 출력

### HTML 보고서 템플릿

주간 보고서를 이메일이나 웹으로 전송하기 위한 템플릿을 생성합니다:

```python
# analytics/services/report_generator.py
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from analytics.models import WeeklyComparison, AnalyticsDailyReport
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """보고서 생성 및 전송 서비스"""
    
    def generate_html_report(self, comparison: WeeklyComparison) -> str:
        """HTML 형식의 주간 보고서 생성"""
        
        # 일별 데이터 조회 (차트용)
        daily_reports = AnalyticsDailyReport.objects.filter(
            report_date__range=[
                comparison.previous_week_start,
                comparison.current_week_end
            ]
        ).order_by('report_date')
        
        context = {
            'comparison': comparison,
            'daily_reports': daily_reports,
            'week_identifier': f"{comparison.report_year}W{comparison.report_week:02d}",
        }
        
        html_content = render_to_string(
            'analytics/weekly_report.html',
            context
        )
        
        return html_content
    
    def send_email_report(
        self,
        comparison: WeeklyComparison,
        recipients: list[str],
        subject: Optional[str] = None
    ):
        """이메일로 주간 보고서 전송"""
        
        if subject is None:
            subject = (
                f"📊 주간 성과 보고서 - "
                f"{comparison.report_year}년 {comparison.report_week}주차"
            )
        
        html_content = self.generate_html_report(comparison)
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        
        email.content_subtype = 'html'
        
        try:
            email.send()
            logger.info(f"Weekly report sent to {', '.join(recipients)}")
        except Exception as e:
            logger.error(f"Failed to send email report: {str(e)}")
            raise
```

### 보고서 HTML 템플릿

```html
<!-- templates/analytics/weekly_report.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주간 성과 보고서 - {{ week_identifier }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .summary {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .metric-card {
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
        }
        .metric-title {
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 10px;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-change {
            font-size: 14px;
            margin-top: 10px;
        }
        .positive {
            color: #27ae60;
        }
        .negative {
            color: #e74c3c;
        }
        .neutral {
            color: #95a5a6;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: right;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #3498db;
            color: white;
            font-weight: bold;
        }
        th:first-child, td:first-child {
            text-align: left;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #7f8c8d;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 주간 성과 보고서</h1>
        
        <p>
            <strong>보고 주차:</strong> {{ comparison.report_year }}년 {{ comparison.report_week }}주차<br>
            <strong>기간:</strong> {{ comparison.current_week_start }} ~ {{ comparison.current_week_end }}
        </p>
        
        <div class="summary">
            <h2>📝 요약</h2>
            <p>{{ comparison.summary|linebreaks }}</p>
        </div>
        
        <h2>📈 주요 지표</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-title">총 사용자</div>
                <div class="metric-value">{{ comparison.current_total_users|floatformat:0|intcomma }}</div>
                <div class="metric-change {% if comparison.users_change_rate > 0 %}positive{% elif comparison.users_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                    {% if comparison.users_change_rate > 0 %}↑{% elif comparison.users_change_rate < 0 %}↓{% else %}→{% endif %}
                    {{ comparison.users_change_rate|floatformat:2 }}%
                    ({{ comparison.previous_total_users|floatformat:0|intcomma }})
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">세션</div>
                <div class="metric-value">{{ comparison.current_sessions|floatformat:0|intcomma }}</div>
                <div class="metric-change {% if comparison.sessions_change_rate > 0 %}positive{% elif comparison.sessions_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                    {% if comparison.sessions_change_rate > 0 %}↑{% elif comparison.sessions_change_rate < 0 %}↓{% else %}→{% endif %}
                    {{ comparison.sessions_change_rate|floatformat:2 }}%
                    ({{ comparison.previous_sessions|floatformat:0|intcomma }})
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">페이지뷰</div>
                <div class="metric-value">{{ comparison.current_page_views|floatformat:0|intcomma }}</div>
                <div class="metric-change {% if comparison.page_views_change_rate > 0 %}positive{% elif comparison.page_views_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                    {% if comparison.page_views_change_rate > 0 %}↑{% elif comparison.page_views_change_rate < 0 %}↓{% else %}→{% endif %}
                    {{ comparison.page_views_change_rate|floatformat:2 }}%
                    ({{ comparison.previous_page_views|floatformat:0|intcomma }})
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">수익</div>
                <div class="metric-value">₩{{ comparison.current_revenue|floatformat:0|intcomma }}</div>
                <div class="metric-change {% if comparison.revenue_change_rate > 0 %}positive{% elif comparison.revenue_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                    {% if comparison.revenue_change_rate > 0 %}↑{% elif comparison.revenue_change_rate < 0 %}↓{% else %}→{% endif %}
                    {{ comparison.revenue_change_rate|floatformat:2 }}%
                    (₩{{ comparison.previous_revenue|floatformat:0|intcomma }})
                </div>
            </div>
        </div>
        
        <h2>📊 상세 비교</h2>
        <table>
            <thead>
                <tr>
                    <th>지표</th>
                    <th>지난주</th>
                    <th>이번주</th>
                    <th>변화율</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>총 사용자</td>
                    <td>{{ comparison.previous_total_users|floatformat:0|intcomma }}</td>
                    <td>{{ comparison.current_total_users|floatformat:0|intcomma }}</td>
                    <td class="{% if comparison.users_change_rate > 0 %}positive{% elif comparison.users_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                        {{ comparison.users_change_rate|floatformat:2 }}%
                    </td>
                </tr>
                <tr>
                    <td>신규 사용자</td>
                    <td>{{ comparison.previous_new_users|floatformat:0|intcomma }}</td>
                    <td>{{ comparison.current_new_users|floatformat:0|intcomma }}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>세션</td>
                    <td>{{ comparison.previous_sessions|floatformat:0|intcomma }}</td>
                    <td>{{ comparison.current_sessions|floatformat:0|intcomma }}</td>
                    <td class="{% if comparison.sessions_change_rate > 0 %}positive{% elif comparison.sessions_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                        {{ comparison.sessions_change_rate|floatformat:2 }}%
                    </td>
                </tr>
                <tr>
                    <td>페이지뷰</td>
                    <td>{{ comparison.previous_page_views|floatformat:0|intcomma }}</td>
                    <td>{{ comparison.current_page_views|floatformat:0|intcomma }}</td>
                    <td class="{% if comparison.page_views_change_rate > 0 %}positive{% elif comparison.page_views_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                        {{ comparison.page_views_change_rate|floatformat:2 }}%
                    </td>
                </tr>
                <tr>
                    <td>전환</td>
                    <td>{{ comparison.previous_conversions|floatformat:0|intcomma }}</td>
                    <td>{{ comparison.current_conversions|floatformat:0|intcomma }}</td>
                    <td class="{% if comparison.conversions_change_rate > 0 %}positive{% elif comparison.conversions_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                        {{ comparison.conversions_change_rate|floatformat:2 }}%
                    </td>
                </tr>
                <tr>
                    <td>수익</td>
                    <td>₩{{ comparison.previous_revenue|floatformat:0|intcomma }}</td>
                    <td>₩{{ comparison.current_revenue|floatformat:0|intcomma }}</td>
                    <td class="{% if comparison.revenue_change_rate > 0 %}positive{% elif comparison.revenue_change_rate < 0 %}negative{% else %}neutral{% endif %}">
                        {{ comparison.revenue_change_rate|floatformat:2 }}%
                    </td>
                </tr>
            </tbody>
        </table>
        
        <div class="footer">
            <p>
                이 보고서는 자동으로 생성되었습니다.<br>
                생성 시간: {{ comparison.created_at|date:"Y년 m월 d일 H:i" }}
            </p>
        </div>
    </div>
</body>
</html>
```

## 🎯 결론 및 확장 가능성

이 글에서는 Django Ninja와 Google Analytics API를 활용하여 주간 성과 분석 서비스를 구축하는 전 과정을 살펴보았습니다. 구현한 시스템은 다음과 같은 기능을 제공합니다:

### 핵심 성과

1. **자동화된 데이터 파이프라인**: Celery를 통해 매일 자동으로 Analytics 데이터를 수집하고 DB에 저장
2. **주간 비교 분석**: 지난주와 이번주의 성과를 자동으로 비교하고 인사이트 생성
3. **RESTful API**: Django Ninja로 구현한 고성능 API로 프론트엔드나 외부 시스템과 연동 가능
4. **관리자 인터페이스**: Django Admin을 통한 직관적인 데이터 확인 및 관리

### 추가 확장 아이디어

```python
# 확장 가능한 기능들

# 1. 실시간 알림
class AlertService:
    """주요 지표 이상 감지 시 알림"""
    def check_anomalies(self, report):
        if report.bounce_rate > 70:
            send_slack_alert("이탈률이 70%를 초과했습니다!")
        if report.conversions < expected_threshold:
            send_email_alert("전환이 예상치보다 낮습니다.")

# 2. 예측 분석
class PredictiveAnalyzer:
    """머신러닝 기반 트래픽 예측"""
    def predict_next_week(self):
        # ARIMA, Prophet 등을 활용한 시계열 예측
        pass

# 3. A/B 테스트 분석
class ABTestAnalyzer:
    """실험군/대조군 성과 비교"""
    def compare_variants(self, experiment_id):
        # Google Optimize 데이터와 연동
        pass

# 4. 다중 속성 지원
class MultiPropertyCollector:
    """여러 GA4 속성 동시 관리"""
    def collect_all_properties(self):
        for property_id in settings.GA4_PROPERTIES:
            # 각 속성별 데이터 수집
            pass

# 5. 커스텀 대시보드
class DashboardAPI:
    """React/Vue 프론트엔드용 대시보드 API"""
    @api.get("/dashboard/overview")
    def get_dashboard_data(self, date_range):
        # 차트와 위젯에 필요한 데이터 제공
        pass
```

### 프로덕션 배포 체크리스트

```bash
# 보안 설정
- [ ] SECRET_KEY 환경 변수로 관리
- [ ] DEBUG = False 설정
- [ ] ALLOWED_HOSTS 설정
- [ ] HTTPS 강제 (SECURE_SSL_REDIRECT = True)
- [ ] Google 서비스 계정 키 안전하게 보관

# 성능 최적화
- [ ] 데이터베이스 인덱스 확인
- [ ] Redis 캐싱 활성화
- [ ] Gunicorn 워커 수 조정
- [ ] Nginx 리버스 프록시 설정
- [ ] 정적 파일 CDN 배포

# 모니터링
- [ ] Sentry 에러 추적 설정
- [ ] Prometheus/Grafana 메트릭 수집
- [ ] 로그 중앙화 (ELK Stack)
- [ ] 업타임 모니터링 (UptimeRobot)
- [ ] API 요청 수 제한 (Rate Limiting)

# 백업 및 복구
- [ ] 데이터베이스 자동 백업 설정
- [ ] GA4 데이터 주기적 백업
- [ ] 재해 복구 계획 수립
```

### 마치며

Django Ninja의 간결한 문법과 Google Analytics의 강력한 데이터를 결합하면, 마케팅 팀과 경영진이 의사결정에 활용할 수 있는 실질적인 인사이트 플랫폼을 빠르게 구축할 수 있습니다. 이 시스템을 기반으로 더 복잡한 비즈니스 인텔리전스 도구로 발전시킬 수 있으며, 다양한 데이터 소스(Google Ads, Facebook Ads, 내부 거래 데이터 등)와 통합하여 통합 분석 플랫폼으로 확장할 수 있습니다.

데이터 기반 의사결정의 첫 걸음, 지금 시작해보세요! 🚀
