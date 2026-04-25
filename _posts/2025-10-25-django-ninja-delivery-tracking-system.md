---
layout: post
title: "Django Ninja로 실시간 배송추적 시스템 구축하기 - 스마트택배 API 완벽 활용"
subtitle: "외부 택배사 API 연동으로 고도화된 배송 추적 서비스 개발"
date: 2025-10-25 10:00:00 +0900
background: '/img/posts/django-ninja-delivery-bg.jpg'
categories: [Django, API, Logistics]
tags: [django-ninja, delivery-tracking, smartparcel-api, fastapi, logistics, shipping]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-25-django-ninja-delivery-tracking-system.webp"
---

# 🚚 Django Ninja로 실시간 배송추적 시스템 구축하기

현대 e-커머스에서 **배송 추적**은 필수 기능입니다. 고객들은 주문한 상품이 어디에 있는지 실시간으로 확인하고 싶어하죠. 

이번 포스트에서는 **Django Ninja**와 **스마트택배 API**를 활용하여 **실무급 배송추적 시스템**을 구축해보겠습니다.

## 🎯 구현할 기능 개요

- **다중 택배사 지원** (CJ대한통운, 로젠, 한진택배 등)
- **실시간 배송 상태 추적**
- **자동 배송 상태 업데이트**
- **고객 알림 시스템** (SMS, 푸시, 이메일)
- **배송 예상 시간 계산**
- **배송 지연 감지 및 알림**

---

## 📦 1. 프로젝트 설정 및 기본 구조

먼저 프로젝트의 기본 구조를 설정하고 필요한 의존성을 설치하겠습니다.

### 1.1 의존성 설치

```bash
# requirements.txt
django==4.2.7
django-ninja==1.0.1
redis==5.0.1
celery==5.3.4
requests==2.31.0
python-decouple==3.8
django-model-utils==4.3.1
django-extensions==3.2.3

# 알림 서비스용
twilio==8.10.0
django-push-notifications==3.0.2

# 데이터베이스
psycopg2-binary==2.9.9
```

### 1.2 Django 설정

```python
# settings/base.py
from decouple import config

# 스마트택배 API 설정
SMARTPARCEL_API_KEY = config('SMARTPARCEL_API_KEY')
SMARTPARCEL_BASE_URL = 'https://info.sweettracker.co.kr/api'

# Celery 설정 (비동기 작업용)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')

# 알림 서비스 설정
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'ninja',
    'django_extensions',
    
    # Local apps
    'apps.accounts',
    'apps.orders',
    'apps.delivery',  # 새로 생성할 앱
    'apps.notifications',
]
```

### 1.3 프로젝트 구조

```
delivery_tracking/
├── apps/
│   ├── delivery/
│   │   ├── models.py          # 배송 관련 모델
│   │   ├── services.py        # 택배사 API 서비스
│   │   ├── api.py            # Django Ninja API
│   │   ├── tasks.py          # Celery 비동기 작업
│   │   └── schemas.py        # Pydantic 스키마
│   ├── orders/
│   │   └── models.py         # 주문 모델
│   └── notifications/
│       └── services.py       # 알림 서비스
├── config/
│   ├── settings/
│   ├── urls.py
│   └── celery.py
└── requirements.txt
```

---

## 🏗️ 2. 데이터 모델 설계

배송 추적을 위한 핵심 모델들을 설계해보겠습니다.

### 2.1 택배사 정보 모델

```python
# apps/delivery/models.py
from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel
from model_utils import Choices

class DeliveryCompany(TimeStampedModel):
    """택배회사 정보"""
    
    # 스마트택배 API에서 제공하는 택배사 코드
    COMPANY_CODES = Choices(
        ('04', 'cj', 'CJ대한통운'),
        ('05', 'hanjin', '한진택배'),
        ('08', 'lotte', '롯데택배'),
        ('01', 'ems', '우체국택배'),
        ('06', 'logen', '로젠택배'),
        ('11', 'ilyang', '일양로지스'),
        ('14', 'kunyoung', '건영택배'),
        ('16', 'gspostbox', 'GS Postbox'),
        ('18', 'cvsnet', 'CVSnet 편의점택배'),
        ('23', 'kyungdong', '경동택배'),
        ('32', 'gsethd', 'GSETHD'),
        ('46', 'cjlogistics', 'CJ대한통운'),
    )
    
    code = models.CharField(
        max_length=10, 
        choices=COMPANY_CODES,
        unique=True,
        help_text="스마트택배 API 회사 코드"
    )
    name = models.CharField(max_length=100, verbose_name="택배회사명")
    phone = models.CharField(max_length=20, blank=True, verbose_name="고객센터 전화번호")
    website = models.URLField(blank=True, verbose_name="웹사이트")
    tracking_url = models.URLField(blank=True, verbose_name="배송조회 URL 템플릿")
    is_active = models.BooleanField(default=True, verbose_name="사용 여부")
    
    # API 호출 제한 관련
    rate_limit_per_minute = models.IntegerField(default=60, verbose_name="분당 API 호출 제한")
    
    class Meta:
        verbose_name = "택배회사"
        verbose_name_plural = "택배회사들"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_tracking_url(self, invoice_number):
        """배송조회 URL 생성"""
        if self.tracking_url:
            return self.tracking_url.format(invoice_number=invoice_number)
        return None

class DeliveryShipment(TimeStampedModel):
    """배송 정보"""
    
    STATUS_CHOICES = Choices(
        ('preparing', '배송준비중'),
        ('collected', '집화완료'),
        ('in_transit', '배송중'),
        ('out_for_delivery', '배송출발'),
        ('delivered', '배송완료'),
        ('failed', '배송실패'),
        ('returned', '반송'),
        ('cancelled', '취소'),
    )
    
    # 기본 정보
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='shipments',
        verbose_name="주문"
    )
    delivery_company = models.ForeignKey(
        DeliveryCompany,
        on_delete=models.PROTECT,
        verbose_name="택배회사"
    )
    invoice_number = models.CharField(
        max_length=50,
        verbose_name="송장번호",
        db_index=True
    )
    
    # 배송 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES.preparing,
        verbose_name="배송상태"
    )
    
    # 발송자/수취인 정보
    sender_name = models.CharField(max_length=100, verbose_name="발송자명")
    sender_phone = models.CharField(max_length=20, verbose_name="발송자 연락처")
    
    recipient_name = models.CharField(max_length=100, verbose_name="수취인명")
    recipient_phone = models.CharField(max_length=20, verbose_name="수취인 연락처")
    recipient_address = models.TextField(verbose_name="배송주소")
    
    # 배송 일정
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="발송일시")
    estimated_delivery = models.DateTimeField(null=True, blank=True, verbose_name="배송예정일시")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="배송완료일시")
    
    # 추가 정보
    special_instructions = models.TextField(blank=True, verbose_name="배송 요청사항")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="배송비")
    
    # API 관련
    last_tracking_update = models.DateTimeField(null=True, blank=True, verbose_name="마지막 추적 업데이트")
    tracking_failed_count = models.IntegerField(default=0, verbose_name="추적 실패 횟수")
    
    class Meta:
        verbose_name = "배송정보"
        verbose_name_plural = "배송정보들"
        unique_together = ['delivery_company', 'invoice_number']
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.delivery_company.name} - {self.invoice_number}"
    
    @property
    def tracking_url(self):
        """배송조회 URL"""
        return self.delivery_company.get_tracking_url(self.invoice_number)
    
    @property
    def is_delivered(self):
        """배송완료 여부"""
        return self.status == self.STATUS_CHOICES.delivered
    
    @property
    def is_in_transit(self):
        """배송중 여부"""
        return self.status in [
            self.STATUS_CHOICES.collected,
            self.STATUS_CHOICES.in_transit,
            self.STATUS_CHOICES.out_for_delivery
        ]

class DeliveryTrackingHistory(TimeStampedModel):
    """배송 추적 이력"""
    
    shipment = models.ForeignKey(
        DeliveryShipment,
        on_delete=models.CASCADE,
        related_name='tracking_history',
        verbose_name="배송정보"
    )
    
    # 추적 정보
    status_code = models.CharField(max_length=20, verbose_name="상태코드")
    status_text = models.CharField(max_length=200, verbose_name="상태메시지")
    location = models.CharField(max_length=200, blank=True, verbose_name="현재위치")
    
    # 시간 정보
    occurred_at = models.DateTimeField(verbose_name="발생일시")
    
    # 추가 정보
    details = models.TextField(blank=True, verbose_name="상세정보")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="담당자 연락처")
    
    # API 원본 데이터 보관
    raw_data = models.JSONField(null=True, blank=True, verbose_name="원본 API 응답")
    
    class Meta:
        verbose_name = "배송추적이력"
        verbose_name_plural = "배송추적이력들"
        ordering = ['-occurred_at']
        unique_together = ['shipment', 'occurred_at', 'status_code']
    
    def __str__(self):
        return f"{self.shipment.invoice_number} - {self.status_text}"

class DeliveryNotification(TimeStampedModel):
    """배송 알림 이력"""
    
    NOTIFICATION_TYPES = Choices(
        ('sms', 'SMS'),
        ('email', '이메일'),
        ('push', '푸시알림'),
        ('webhook', '웹훅'),
    )
    
    STATUS_CHOICES = Choices(
        ('pending', '대기'),
        ('sent', '발송완료'),
        ('failed', '발송실패'),
    )
    
    shipment = models.ForeignKey(
        DeliveryShipment,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="배송정보"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="사용자"
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name="알림유형"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES.pending,
        verbose_name="발송상태"
    )
    
    # 알림 내용
    title = models.CharField(max_length=200, verbose_name="제목")
    message = models.TextField(verbose_name="메시지")
    
    # 발송 정보
    recipient = models.CharField(max_length=200, verbose_name="수신자")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="발송일시")
    error_message = models.TextField(blank=True, verbose_name="오류메시지")
    
    class Meta:
        verbose_name = "배송알림"
        verbose_name_plural = "배송알림들"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.shipment.invoice_number} - {self.notification_type} - {self.status}"
```

### 2.2 모델 마이그레이션

```bash
# 마이그레이션 생성 및 적용
python manage.py makemigrations delivery
python manage.py migrate
```

### 2.3 초기 데이터 설정

```python
# apps/delivery/management/commands/setup_delivery_companies.py
from django.core.management.base import BaseCommand
from apps.delivery.models import DeliveryCompany

class Command(BaseCommand):
    help = '택배회사 초기 데이터 설정'
    
    def handle(self, *args, **options):
        companies = [
            {
                'code': '04',
                'name': 'CJ대한통운',
                'phone': '1588-1255',
                'website': 'https://www.cjlogistics.com',
                'tracking_url': 'https://www.cjlogistics.com/ko/tool/parcel/tracking?number={invoice_number}',
            },
            {
                'code': '05',
                'name': '한진택배',
                'phone': '1588-0011',
                'website': 'https://www.hanjin.co.kr',
                'tracking_url': 'https://www.hanjin.co.kr/kor/CMS/DeliveryMgr/WaybillResult.do?mCode=MN038&wblnumText2={invoice_number}',
            },
            {
                'code': '08',
                'name': '롯데택배',
                'phone': '1588-2121',
                'website': 'https://www.lotteglogis.com',
                'tracking_url': 'https://www.lotteglogis.com/home/reservation/tracking/index?InvNo={invoice_number}',
            },
            {
                'code': '01',
                'name': '우체국택배',
                'phone': '1588-1300',
                'website': 'https://service.epost.go.kr',
                'tracking_url': 'https://service.epost.go.kr/trace.RetrieveDomRigiTraceList.comm?sid1={invoice_number}',
            },
        ]
        
        for company_data in companies:
            company, created = DeliveryCompany.objects.get_or_create(
                code=company_data['code'],
                defaults=company_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created delivery company: {company.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Delivery company already exists: {company.name}')
                )
```

---

## 🔌 3. 스마트택배 API 연동 서비스

이제 스마트택배 API를 연동하여 실시간 배송 추적 기능을 구현해보겠습니다.

### 3.1 기본 API 클라이언트

```python
# apps/delivery/services/smartparcel_client.py
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import json

logger = logging.getLogger(__name__)

class SmartParcelAPIClient:
    """스마트택배 API 클라이언트"""
    
    def __init__(self):
        self.api_key = settings.SMARTPARCEL_API_KEY
        self.base_url = settings.SMARTPARCEL_BASE_URL
        self.session = requests.Session()
        self.session.timeout = 30
        
        # 기본 헤더 설정
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Django-Delivery-Tracker/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """API 요청 실행"""
        url = f"{self.base_url}/{endpoint}"
        
        # API 키 추가
        if params is None:
            params = {}
        params['t_key'] = self.api_key
        
        try:
            logger.info(f"Making API request to {url} with params: {params}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # API 에러 체크
            if data.get('status') == False:
                error_msg = data.get('msg', 'Unknown API error')
                logger.error(f"SmartParcel API error: {error_msg}")
                raise SmartParcelAPIError(error_msg)
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise SmartParcelAPIError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            raise SmartParcelAPIError(f"Invalid API response: {str(e)}")
    
    def get_company_list(self) -> List[Dict]:
        """택배회사 목록 조회"""
        cache_key = 'smartparcel_companies'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            data = self._make_request('v1/companylist')
            companies = data.get('Company', [])
            
            # 6시간 캐싱
            cache.set(cache_key, companies, 21600)
            return companies
            
        except SmartParcelAPIError:
            # 캐시된 백업 데이터 반환
            return self._get_fallback_companies()
    
    def get_tracking_info(self, company_code: str, invoice_number: str) -> Dict:
        """배송 추적 정보 조회"""
        cache_key = f'tracking_{company_code}_{invoice_number}'
        
        # 캐시 확인 (10분 캐싱)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        params = {
            't_code': company_code,
            't_invoice': invoice_number
        }
        
        try:
            data = self._make_request('v1/trackingInfo', params)
            
            # 정상 응답인 경우만 캐싱
            if data.get('status') and data.get('trackingDetails'):
                cache.set(cache_key, data, 600)  # 10분 캐싱
            
            return data
            
        except SmartParcelAPIError as e:
            logger.error(f"Failed to get tracking info for {company_code}-{invoice_number}: {str(e)}")
            raise
    
    def get_recommendation_list(self, invoice_number: str) -> List[Dict]:
        """송장번호로 택배회사 추천"""
        params = {'t_invoice': invoice_number}
        
        try:
            data = self._make_request('v1/recommend', params)
            return data.get('Recommend', [])
            
        except SmartParcelAPIError as e:
            logger.error(f"Failed to get recommendations for {invoice_number}: {str(e)}")
            return []
    
    def _get_fallback_companies(self) -> List[Dict]:
        """API 실패시 기본 택배회사 목록"""
        return [
            {'Code': '04', 'Name': 'CJ대한통운'},
            {'Code': '05', 'Name': '한진택배'},
            {'Code': '08', 'Name': '롯데택배'},
            {'Code': '01', 'Name': '우체국택배'},
            {'Code': '06', 'Name': '로젠택배'},
        ]

class SmartParcelAPIError(Exception):
    """스마트택배 API 에러"""
    pass
```

### 3.2 배송 추적 서비스

```python
# apps/delivery/services/tracking_service.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from django.utils import timezone as django_timezone
from django.db import transaction
from apps.delivery.models import DeliveryShipment, DeliveryTrackingHistory, DeliveryCompany
from apps.delivery.services.smartparcel_client import SmartParcelAPIClient, SmartParcelAPIError
import logging

logger = logging.getLogger(__name__)

class DeliveryTrackingService:
    """배송 추적 서비스"""
    
    def __init__(self):
        self.api_client = SmartParcelAPIClient()
        
        # 상태 매핑 (API 응답 -> 우리 모델)
        self.status_mapping = {
            '배송준비': 'preparing',
            '집화완료': 'collected', 
            '간선상차': 'in_transit',
            '간선하차': 'in_transit',
            '배송출발': 'out_for_delivery',
            '배송완료': 'delivered',
            '미배송': 'failed',
            '반송': 'returned',
        }
    
    def create_shipment(self, order_id: int, company_code: str, invoice_number: str, 
                       recipient_info: Dict) -> DeliveryShipment:
        """새 배송 정보 생성"""
        try:
            with transaction.atomic():
                # 택배회사 조회
                company = DeliveryCompany.objects.get(code=company_code)
                
                # 배송 정보 생성
                shipment = DeliveryShipment.objects.create(
                    order_id=order_id,
                    delivery_company=company,
                    invoice_number=invoice_number,
                    recipient_name=recipient_info.get('name', ''),
                    recipient_phone=recipient_info.get('phone', ''),
                    recipient_address=recipient_info.get('address', ''),
                    special_instructions=recipient_info.get('instructions', ''),
                    shipped_at=django_timezone.now()
                )
                
                # 초기 추적 정보 업데이트
                self.update_tracking_info(shipment.id)
                
                logger.info(f"Created shipment: {shipment.id} - {invoice_number}")
                return shipment
                
        except DeliveryCompany.DoesNotExist:
            raise ValueError(f"Unknown delivery company code: {company_code}")
        except Exception as e:
            logger.error(f"Failed to create shipment: {str(e)}")
            raise
    
    def update_tracking_info(self, shipment_id: int) -> Tuple[bool, str]:
        """배송 추적 정보 업데이트"""
        try:
            shipment = DeliveryShipment.objects.select_related('delivery_company').get(id=shipment_id)
            
            # API로 최신 정보 조회
            tracking_data = self.api_client.get_tracking_info(
                shipment.delivery_company.code,
                shipment.invoice_number
            )
            
            if not tracking_data.get('trackingDetails'):
                return False, "No tracking information available"
            
            # 추적 정보 파싱 및 저장
            details = tracking_data['trackingDetails']
            updated_count = self._process_tracking_details(shipment, details)
            
            # 배송 상태 업데이트
            latest_status = self._get_latest_status(details)
            if latest_status and shipment.status != latest_status:
                shipment.status = latest_status
                
                # 배송완료시 완료 시간 기록
                if latest_status == 'delivered':
                    shipment.delivered_at = django_timezone.now()
                
                shipment.save(update_fields=['status', 'delivered_at'])
                logger.info(f"Updated shipment {shipment.id} status to {latest_status}")
            
            # 마지막 업데이트 시간 기록
            shipment.last_tracking_update = django_timezone.now()
            shipment.tracking_failed_count = 0  # 성공시 실패 카운트 리셋
            shipment.save(update_fields=['last_tracking_update', 'tracking_failed_count'])
            
            return True, f"Updated {updated_count} tracking records"
            
        except DeliveryShipment.DoesNotExist:
            return False, "Shipment not found"
        except SmartParcelAPIError as e:
            # API 실패 카운트 증가
            shipment.tracking_failed_count += 1
            shipment.save(update_fields=['tracking_failed_count'])
            logger.error(f"API error updating shipment {shipment_id}: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error updating tracking info for shipment {shipment_id}: {str(e)}")
            return False, str(e)
    
    def _process_tracking_details(self, shipment: DeliveryShipment, details: List[Dict]) -> int:
        """추적 상세 정보 처리"""
        updated_count = 0
        
        for detail in details:
            try:
                # 시간 파싱
                time_str = detail.get('timeString', '')
                occurred_at = self._parse_datetime(time_str)
                
                if not occurred_at:
                    continue
                
                # 중복 체크
                exists = DeliveryTrackingHistory.objects.filter(
                    shipment=shipment,
                    occurred_at=occurred_at,
                    status_code=detail.get('kind', '')
                ).exists()
                
                if not exists:
                    DeliveryTrackingHistory.objects.create(
                        shipment=shipment,
                        status_code=detail.get('kind', ''),
                        status_text=detail.get('where', ''),
                        location=detail.get('where', ''),
                        occurred_at=occurred_at,
                        details=detail.get('telno', ''),
                        phone_number=detail.get('telno2', ''),
                        raw_data=detail
                    )
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing tracking detail: {str(e)}")
                continue
        
        return updated_count
    
    def _get_latest_status(self, details: List[Dict]) -> Optional[str]:
        """최신 배송 상태 추출"""
        if not details:
            return None
        
        # 가장 최신 상태 (첫 번째 항목)
        latest_kind = details[0].get('kind', '')
        return self.status_mapping.get(latest_kind, 'in_transit')
    
    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """시간 문자열 파싱"""
        try:
            # 스마트택배 API 시간 형식: "2023-10-25 14:30:00"
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    
    def get_shipment_details(self, shipment_id: int) -> Dict:
        """배송 정보 상세 조회"""
        try:
            shipment = DeliveryShipment.objects.select_related('delivery_company', 'order').get(id=shipment_id)
            
            # 최신 추적 이력 조회
            tracking_history = shipment.tracking_history.all()[:10]  # 최근 10개
            
            return {
                'shipment': shipment,
                'tracking_history': tracking_history,
                'tracking_url': shipment.tracking_url,
                'estimated_delivery': self._calculate_estimated_delivery(shipment),
                'is_delayed': self._check_delivery_delay(shipment)
            }
            
        except DeliveryShipment.DoesNotExist:
            raise ValueError("Shipment not found")
    
    def _calculate_estimated_delivery(self, shipment: DeliveryShipment) -> Optional[datetime]:
        """배송 예상 시간 계산"""
        if shipment.estimated_delivery:
            return shipment.estimated_delivery
        
        # 기본 배송 예상 시간 (택배회사별 다르게 설정 가능)
        if shipment.shipped_at:
            # 평균 2-3일 소요
            estimated = shipment.shipped_at + timedelta(days=2)
            return estimated
        
        return None
    
    def _check_delivery_delay(self, shipment: DeliveryShipment) -> bool:
        """배송 지연 여부 확인"""
        estimated = self._calculate_estimated_delivery(shipment)
        if estimated and django_timezone.now() > estimated:
            return True
        return False
    
    def auto_recommend_company(self, invoice_number: str) -> List[Dict]:
        """송장번호로 택배회사 자동 추천"""
        try:
            recommendations = self.api_client.get_recommendation_list(invoice_number)
            
            # 우리 DB의 택배회사와 매칭
            matched_companies = []
            for rec in recommendations:
                try:
                    company = DeliveryCompany.objects.get(code=rec.get('Code'))
                    matched_companies.append({
                        'company': company,
                        'confidence': rec.get('rate', 0)
                    })
                except DeliveryCompany.DoesNotExist:
                    continue
            
            return matched_companies
            
        except SmartParcelAPIError as e:
            logger.error(f"Failed to get company recommendations: {str(e)}")
            return []
```

### 3.3 배송 추적 스케줄러

```python
# apps/delivery/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.delivery.models import DeliveryShipment
from apps.delivery.services.tracking_service import DeliveryTrackingService
from apps.notifications.services import NotificationService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def update_shipment_tracking(self, shipment_id: int):
    """개별 배송 추적 정보 업데이트"""
    try:
        tracking_service = DeliveryTrackingService()
        success, message = tracking_service.update_tracking_info(shipment_id)
        
        if success:
            logger.info(f"Successfully updated tracking for shipment {shipment_id}")
        else:
            logger.warning(f"Failed to update tracking for shipment {shipment_id}: {message}")
            
    except Exception as e:
        logger.error(f"Error in update_shipment_tracking for {shipment_id}: {str(e)}")
        # 재시도
        raise self.retry(countdown=60 * (self.request.retries + 1))

@shared_task
def bulk_update_active_shipments():
    """활성 배송들의 추적 정보 일괄 업데이트"""
    # 배송중인 건들만 업데이트
    active_shipments = DeliveryShipment.objects.filter(
        status__in=['preparing', 'collected', 'in_transit', 'out_for_delivery'],
        tracking_failed_count__lt=5  # 5회 이상 실패한 건은 제외
    ).values_list('id', flat=True)
    
    logger.info(f"Starting bulk update for {active_shipments.count()} shipments")
    
    # 개별 작업으로 분산 처리
    for shipment_id in active_shipments:
        update_shipment_tracking.delay(shipment_id)

@shared_task
def check_delivery_delays():
    """배송 지연 감지 및 알림"""
    # 예상 배송일 지난 건들 조회
    delayed_shipments = DeliveryShipment.objects.filter(
        status__in=['in_transit', 'out_for_delivery'],
        estimated_delivery__lt=timezone.now(),
        delivered_at__isnull=True
    ).select_related('order__user')
    
    notification_service = NotificationService()
    
    for shipment in delayed_shipments:
        try:
            # 지연 알림 발송
            notification_service.send_delay_notification(shipment)
            logger.info(f"Sent delay notification for shipment {shipment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send delay notification for shipment {shipment.id}: {str(e)}")

@shared_task
def cleanup_old_tracking_data():
    """오래된 추적 데이터 정리"""
    # 6개월 이전 완료된 배송의 상세 추적 이력 삭제
    cutoff_date = timezone.now() - timedelta(days=180)
    
    from apps.delivery.models import DeliveryTrackingHistory
    
    deleted_count = DeliveryTrackingHistory.objects.filter(
        shipment__status='delivered',
        shipment__delivered_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old tracking records")
```

---

## 🎯 4. Django Ninja API 엔드포인트

이제 Django Ninja를 사용하여 클린하고 현대적인 API를 구현해보겠습니다.

### 4.1 Pydantic 스키마 정의

```python
# apps/delivery/schemas.py
from ninja import Schema, Field
from typing import List, Optional
from datetime import datetime
from pydantic import validator

class DeliveryCompanySchema(Schema):
    """택배회사 스키마"""
    id: int
    code: str
    name: str
    phone: Optional[str] = None
    website: Optional[str] = None
    is_active: bool

class TrackingHistorySchema(Schema):
    """배송 추적 이력 스키마"""
    id: int
    status_code: str
    status_text: str
    location: Optional[str] = None
    occurred_at: datetime
    details: Optional[str] = None
    phone_number: Optional[str] = None

class ShipmentStatusSchema(Schema):
    """배송 상태 스키마"""
    status: str
    status_display: str
    is_delivered: bool
    is_in_transit: bool

class ShipmentCreateSchema(Schema):
    """배송 생성 요청 스키마"""
    order_id: int
    company_code: str = Field(..., description="택배회사 코드")
    invoice_number: str = Field(..., min_length=8, max_length=50, description="송장번호")
    recipient_name: str = Field(..., min_length=1, max_length=100)
    recipient_phone: str = Field(..., description="수취인 연락처")
    recipient_address: str = Field(..., description="배송주소")
    special_instructions: Optional[str] = Field(None, max_length=500)
    delivery_fee: Optional[float] = Field(0, ge=0)
    
    @validator('invoice_number')
    def validate_invoice_number(cls, v):
        # 송장번호 형식 검증
        if not v.isdigit():
            raise ValueError('송장번호는 숫자여야 합니다')
        return v

class ShipmentUpdateSchema(Schema):
    """배송 정보 수정 스키마"""
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[str] = None
    special_instructions: Optional[str] = None

class ShipmentResponseSchema(Schema):
    """배송 정보 응답 스키마"""
    id: int
    order_id: int
    delivery_company: DeliveryCompanySchema
    invoice_number: str
    status: str
    status_display: str
    
    # 수취인 정보
    recipient_name: str
    recipient_phone: str
    recipient_address: str
    special_instructions: Optional[str] = None
    
    # 시간 정보
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # 추가 정보
    tracking_url: Optional[str] = None
    delivery_fee: float
    created: datetime
    
    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()
    
    @staticmethod
    def resolve_tracking_url(obj):
        return obj.tracking_url

class ShipmentDetailSchema(ShipmentResponseSchema):
    """배송 상세 정보 스키마"""
    tracking_history: List[TrackingHistorySchema]
    is_delayed: bool
    last_tracking_update: Optional[datetime] = None

class TrackingUpdateRequestSchema(Schema):
    """추적 정보 업데이트 요청 스키마"""
    force_update: Optional[bool] = Field(False, description="강제 업데이트 여부")

class TrackingUpdateResponseSchema(Schema):
    """추적 정보 업데이트 응답 스키마"""
    success: bool
    message: str
    updated_at: datetime

class CompanyRecommendationSchema(Schema):
    """택배회사 추천 스키마"""
    company: DeliveryCompanySchema
    confidence: float = Field(..., description="추천 신뢰도 (0-100)")

class DeliverySearchSchema(Schema):
    """배송 검색 스키마"""
    company_code: Optional[str] = None
    status: Optional[str] = None
    order_id: Optional[int] = None
    invoice_number: Optional[str] = None
    recipient_phone: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class PaginatedShipmentSchema(Schema):
    """페이지네이션된 배송 목록 스키마"""
    items: List[ShipmentResponseSchema]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

class ErrorResponseSchema(Schema):
    """에러 응답 스키마"""
    error: bool = True
    message: str
    code: Optional[str] = None
    details: Optional[dict] = None
```

### 4.2 Django Ninja API 구현

```python
# apps/delivery/api.py
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError
from typing import List, Optional

from apps.delivery.models import DeliveryShipment, DeliveryCompany
from apps.delivery.services.tracking_service import DeliveryTrackingService
from apps.delivery.schemas import *
from apps.delivery.tasks import update_shipment_tracking
from apps.accounts.auth import AuthBearer

import logging

logger = logging.getLogger(__name__)

router = Router(tags=["Delivery Tracking"])

# 서비스 인스턴스
tracking_service = DeliveryTrackingService()

@router.get("/companies", response=List[DeliveryCompanySchema])
def list_delivery_companies(request):
    """택배회사 목록 조회"""
    companies = DeliveryCompany.objects.filter(is_active=True).order_by('name')
    return companies

@router.get("/companies/{company_code}/recommend", response=List[CompanyRecommendationSchema])
def recommend_companies(request, invoice_number: str = Query(..., description="송장번호")):
    """송장번호로 택배회사 추천"""
    try:
        recommendations = tracking_service.auto_recommend_company(invoice_number)
        return recommendations
    except Exception as e:
        logger.error(f"Company recommendation error: {str(e)}")
        raise HttpError(500, "택배회사 추천 중 오류가 발생했습니다")

@router.post("/shipments", response=ShipmentResponseSchema, auth=AuthBearer())
def create_shipment(request, payload: ShipmentCreateSchema):
    """새 배송 정보 생성"""
    try:
        # 권한 확인 (주문 소유자 또는 관리자)
        if not request.user.is_staff:
            # 추가 권한 검증 로직
            pass
        
        recipient_info = {
            'name': payload.recipient_name,
            'phone': payload.recipient_phone,
            'address': payload.recipient_address,
            'instructions': payload.special_instructions or '',
        }
        
        shipment = tracking_service.create_shipment(
            order_id=payload.order_id,
            company_code=payload.company_code,
            invoice_number=payload.invoice_number,
            recipient_info=recipient_info
        )
        
        # 배송비 설정
        if payload.delivery_fee:
            shipment.delivery_fee = payload.delivery_fee
            shipment.save(update_fields=['delivery_fee'])
        
        return shipment
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Shipment creation error: {str(e)}")
        raise HttpError(500, "배송 정보 생성 중 오류가 발생했습니다")

@router.get("/shipments", response=PaginatedShipmentSchema, auth=AuthBearer())
@paginate(PageNumberPagination, page_size=20)
def list_shipments(request, filters: DeliverySearchSchema = Query(...)):
    """배송 목록 조회"""
    queryset = DeliveryShipment.objects.select_related('delivery_company', 'order')
    
    # 일반 사용자는 본인 주문만 조회
    if not request.user.is_staff:
        queryset = queryset.filter(order__user=request.user)
    
    # 필터 적용
    if filters.company_code:
        queryset = queryset.filter(delivery_company__code=filters.company_code)
    
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    
    if filters.order_id:
        queryset = queryset.filter(order_id=filters.order_id)
    
    if filters.invoice_number:
        queryset = queryset.filter(invoice_number__icontains=filters.invoice_number)
    
    if filters.recipient_phone:
        queryset = queryset.filter(recipient_phone__icontains=filters.recipient_phone)
    
    if filters.date_from:
        queryset = queryset.filter(created__gte=filters.date_from)
    
    if filters.date_to:
        queryset = queryset.filter(created__lte=filters.date_to)
    
    return queryset.order_by('-created')

@router.get("/shipments/{int:shipment_id}", response=ShipmentDetailSchema, auth=AuthBearer())
def get_shipment_detail(request, shipment_id: int):
    """배송 상세 정보 조회"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인
        if not request.user.is_staff and shipment.order.user != request.user:
            raise HttpError(403, "접근 권한이 없습니다")
        
        # 상세 정보 조회
        details = tracking_service.get_shipment_details(shipment_id)
        
        # 응답 데이터 구성
        response_data = ShipmentDetailSchema.from_orm(details['shipment'])
        response_data.tracking_history = details['tracking_history']
        response_data.is_delayed = details['is_delayed']
        
        return response_data
        
    except ValueError as e:
        raise HttpError(404, str(e))
    except Exception as e:
        logger.error(f"Shipment detail error: {str(e)}")
        raise HttpError(500, "배송 정보 조회 중 오류가 발생했습니다")

@router.put("/shipments/{int:shipment_id}", response=ShipmentResponseSchema, auth=AuthBearer())
def update_shipment(request, shipment_id: int, payload: ShipmentUpdateSchema):
    """배송 정보 수정"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인
        if not request.user.is_staff and shipment.order.user != request.user:
            raise HttpError(403, "수정 권한이 없습니다")
        
        # 배송완료 후에는 수정 불가
        if shipment.is_delivered:
            raise HttpError(400, "배송완료된 건은 수정할 수 없습니다")
        
        # 수정 가능한 필드만 업데이트
        update_fields = []
        
        if payload.recipient_name is not None:
            shipment.recipient_name = payload.recipient_name
            update_fields.append('recipient_name')
        
        if payload.recipient_phone is not None:
            shipment.recipient_phone = payload.recipient_phone
            update_fields.append('recipient_phone')
        
        if payload.recipient_address is not None:
            shipment.recipient_address = payload.recipient_address
            update_fields.append('recipient_address')
        
        if payload.special_instructions is not None:
            shipment.special_instructions = payload.special_instructions
            update_fields.append('special_instructions')
        
        if update_fields:
            shipment.save(update_fields=update_fields)
        
        return shipment
        
    except Exception as e:
        logger.error(f"Shipment update error: {str(e)}")
        raise HttpError(500, "배송 정보 수정 중 오류가 발생했습니다")

@router.post("/shipments/{int:shipment_id}/update-tracking", 
            response=TrackingUpdateResponseSchema, 
            auth=AuthBearer())
def update_tracking_info(request, shipment_id: int, payload: TrackingUpdateRequestSchema):
    """배송 추적 정보 업데이트"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인
        if not request.user.is_staff and shipment.order.user != request.user:
            raise HttpError(403, "접근 권한이 없습니다")
        
        if payload.force_update:
            # 강제 업데이트 (즉시 실행)
            success, message = tracking_service.update_tracking_info(shipment_id)
        else:
            # 백그라운드에서 업데이트
            update_shipment_tracking.delay(shipment_id)
            success, message = True, "배송 추적 정보 업데이트를 요청했습니다"
        
        return TrackingUpdateResponseSchema(
            success=success,
            message=message,
            updated_at=timezone.now()
        )
        
    except Exception as e:
        logger.error(f"Tracking update error: {str(e)}")
        raise HttpError(500, "추적 정보 업데이트 중 오류가 발생했습니다")

@router.get("/shipments/{int:shipment_id}/tracking-history", 
           response=List[TrackingHistorySchema],
           auth=AuthBearer())
def get_tracking_history(request, shipment_id: int, limit: int = Query(20, le=100)):
    """배송 추적 이력 조회"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인
        if not request.user.is_staff and shipment.order.user != request.user:
            raise HttpError(403, "접근 권한이 없습니다")
        
        tracking_history = shipment.tracking_history.all()[:limit]
        return tracking_history
        
    except Exception as e:
        logger.error(f"Tracking history error: {str(e)}")
        raise HttpError(500, "추적 이력 조회 중 오류가 발생했습니다")

@router.delete("/shipments/{int:shipment_id}", auth=AuthBearer())
def delete_shipment(request, shipment_id: int):
    """배송 정보 삭제 (관리자만)"""
    if not request.user.is_staff:
        raise HttpError(403, "관리자만 삭제할 수 있습니다")
    
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 배송중인 건은 삭제 불가
        if shipment.is_in_transit:
            raise HttpError(400, "배송중인 건은 삭제할 수 없습니다")
        
        shipment.delete()
        return {"success": True, "message": "배송 정보가 삭제되었습니다"}
        
    except Exception as e:
        logger.error(f"Shipment deletion error: {str(e)}")
        raise HttpError(500, "배송 정보 삭제 중 오류가 발생했습니다")

# 공개 API (인증 불필요)
@router.get("/public/track/{company_code}/{invoice_number}", response=ShipmentDetailSchema)
def public_track_shipment(request, company_code: str, invoice_number: str):
    """공개 배송 추적 (송장번호로 조회)"""
    try:
        shipment = get_object_or_404(
            DeliveryShipment,
            delivery_company__code=company_code,
            invoice_number=invoice_number
        )
        
        # 상세 정보 조회 (개인정보는 마스킹)
        details = tracking_service.get_shipment_details(shipment.id)
        
        # 개인정보 마스킹
        masked_shipment = details['shipment']
        masked_shipment.recipient_name = self._mask_name(masked_shipment.recipient_name)
        masked_shipment.recipient_phone = self._mask_phone(masked_shipment.recipient_phone)
        masked_shipment.recipient_address = self._mask_address(masked_shipment.recipient_address)
        
        response_data = ShipmentDetailSchema.from_orm(masked_shipment)
        response_data.tracking_history = details['tracking_history']
        response_data.is_delayed = details['is_delayed']
        
        return response_data
        
    except Exception as e:
        logger.error(f"Public tracking error: {str(e)}")
        raise HttpError(404, "배송 정보를 찾을 수 없습니다")

def _mask_name(name: str) -> str:
    """이름 마스킹"""
    if len(name) <= 2:
        return name[0] + '*'
    return name[0] + '*' * (len(name) - 2) + name[-1]

def _mask_phone(phone: str) -> str:
    """전화번호 마스킹"""
    if len(phone) >= 8:
        return phone[:3] + '****' + phone[-4:]
    return phone[:2] + '****'

def _mask_address(address: str) -> str:
    """주소 마스킹"""
    parts = address.split(' ')
    if len(parts) >= 2:
        return parts[0] + ' ' + parts[1] + ' ****'
    return address[:10] + ' ****'
```

### 4.3 URL 설정

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from apps.delivery.api import router as delivery_router

api = NinjaAPI(
    title="배송 추적 API",
    version="1.0.0",
    description="Django Ninja 기반 실시간 배송 추적 시스템",
    docs_url="/api/docs/"
)

# API 라우터 등록
api.add_router("/delivery", delivery_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

---

## 📱 5. 알림 시스템 구현

배송 상태 변경시 고객에게 실시간으로 알림을 보내는 시스템을 구현해보겠습니다.

### 5.1 알림 서비스

```python
# apps/notifications/services.py
from typing import Dict, List, Optional
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone
from twilio.rest import Client
from apps.delivery.models import DeliveryShipment, DeliveryNotification
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """알림 서비스"""
    
    def __init__(self):
        # Twilio SMS 클라이언트
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
        else:
            self.twilio_client = None
    
    def send_shipment_notification(self, shipment: DeliveryShipment, event_type: str):
        """배송 이벤트별 알림 발송"""
        try:
            # 알림 메시지 생성
            notification_data = self._generate_notification_content(shipment, event_type)
            
            if not notification_data:
                return
            
            # 사용자 알림 설정 확인
            user = shipment.order.user
            notification_preferences = self._get_user_notification_preferences(user)
            
            # SMS 알림
            if notification_preferences.get('sms_enabled', True):
                self._send_sms_notification(shipment, notification_data)
            
            # 이메일 알림
            if notification_preferences.get('email_enabled', True):
                self._send_email_notification(shipment, notification_data)
            
            # 푸시 알림
            if notification_preferences.get('push_enabled', True):
                self._send_push_notification(shipment, notification_data)
            
            logger.info(f"Sent notifications for shipment {shipment.id}, event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to send notifications for shipment {shipment.id}: {str(e)}")
    
    def _generate_notification_content(self, shipment: DeliveryShipment, event_type: str) -> Optional[Dict]:
        """이벤트별 알림 내용 생성"""
        
        templates = {
            'shipped': {
                'title': '상품이 발송되었습니다',
                'sms_template': '[배송알림] {product_name} 상품이 발송되었습니다. 송장번호: {invoice_number} ({company_name})',
                'email_template': 'emails/shipment_shipped.html',
            },
            'in_transit': {
                'title': '상품이 배송중입니다',
                'sms_template': '[배송알림] {product_name} 상품이 배송중입니다. 현재위치: {location}',
                'email_template': 'emails/shipment_in_transit.html',
            },
            'out_for_delivery': {
                'title': '상품이 배송 출발했습니다',
                'sms_template': '[배송알림] {product_name} 상품이 배송출발했습니다. 곧 도착예정입니다.',
                'email_template': 'emails/shipment_out_for_delivery.html',
            },
            'delivered': {
                'title': '상품이 배송완료되었습니다',
                'sms_template': '[배송완료] {product_name} 상품이 배송완료되었습니다. 확인해주세요!',
                'email_template': 'emails/shipment_delivered.html',
            },
            'delayed': {
                'title': '배송이 지연되고 있습니다',
                'sms_template': '[배송지연] {product_name} 상품 배송이 지연되고 있습니다. 양해 부탁드립니다.',
                'email_template': 'emails/shipment_delayed.html',
            },
            'failed': {
                'title': '배송에 실패했습니다',
                'sms_template': '[배송실패] {product_name} 상품 배송에 실패했습니다. 고객센터로 문의해주세요.',
                'email_template': 'emails/shipment_failed.html',
            }
        }
        
        template_data = templates.get(event_type)
        if not template_data:
            return None
        
        # 상품명 가져오기 (첫 번째 주문 아이템)
        product_name = "주문상품"
        if hasattr(shipment.order, 'items') and shipment.order.items.exists():
            product_name = shipment.order.items.first().product_name
        
        # 최신 위치 정보
        location = "배송중"
        latest_history = shipment.tracking_history.first()
        if latest_history:
            location = latest_history.location or "배송중"
        
        context = {
            'shipment': shipment,
            'product_name': product_name,
            'invoice_number': shipment.invoice_number,
            'company_name': shipment.delivery_company.name,
            'location': location,
            'tracking_url': shipment.tracking_url,
            'recipient_name': shipment.recipient_name,
        }
        
        return {
            'title': template_data['title'],
            'sms_message': template_data['sms_template'].format(**context),
            'email_template': template_data['email_template'],
            'context': context
        }
    
    def _send_sms_notification(self, shipment: DeliveryShipment, notification_data: Dict):
        """SMS 알림 발송"""
        if not self.twilio_client:
            logger.warning("Twilio client not configured, skipping SMS")
            return
        
        try:
            message = self.twilio_client.messages.create(
                body=notification_data['sms_message'],
                from_=settings.TWILIO_FROM_NUMBER,
                to=shipment.recipient_phone
            )
            
            # 발송 이력 저장
            DeliveryNotification.objects.create(
                shipment=shipment,
                user=shipment.order.user,
                notification_type='sms',
                status='sent',
                title=notification_data['title'],
                message=notification_data['sms_message'],
                recipient=shipment.recipient_phone,
                sent_at=timezone.now()
            )
            
            logger.info(f"SMS sent successfully: {message.sid}")
            
        except Exception as e:
            # 실패 이력 저장
            DeliveryNotification.objects.create(
                shipment=shipment,
                user=shipment.order.user,
                notification_type='sms',
                status='failed',
                title=notification_data['title'],
                message=notification_data['sms_message'],
                recipient=shipment.recipient_phone,
                error_message=str(e)
            )
            
            logger.error(f"Failed to send SMS: {str(e)}")
    
    def _send_email_notification(self, shipment: DeliveryShipment, notification_data: Dict):
        """이메일 알림 발송"""
        try:
            # HTML 이메일 템플릿 렌더링
            html_message = render_to_string(
                notification_data['email_template'],
                notification_data['context']
            )
            
            # 텍스트 버전 (HTML 태그 제거)
            from django.utils.html import strip_tags
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=notification_data['title'],
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[shipment.order.user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # 발송 이력 저장
            DeliveryNotification.objects.create(
                shipment=shipment,
                user=shipment.order.user,
                notification_type='email',
                status='sent',
                title=notification_data['title'],
                message=plain_message,
                recipient=shipment.order.user.email,
                sent_at=timezone.now()
            )
            
            logger.info(f"Email sent successfully to {shipment.order.user.email}")
            
        except Exception as e:
            # 실패 이력 저장
            DeliveryNotification.objects.create(
                shipment=shipment,
                user=shipment.order.user,
                notification_type='email',
                status='failed',
                title=notification_data['title'],
                message=notification_data.get('sms_message', ''),
                recipient=shipment.order.user.email,
                error_message=str(e)
            )
            
            logger.error(f"Failed to send email: {str(e)}")
    
    def _send_push_notification(self, shipment: DeliveryShipment, notification_data: Dict):
        """푸시 알림 발송"""
        try:
            from push_notifications.models import APNSDevice, GCMDevice
            
            # iOS 디바이스
            ios_devices = APNSDevice.objects.filter(user=shipment.order.user, active=True)
            if ios_devices.exists():
                ios_devices.send_message(
                    message=notification_data['sms_message'],
                    badge=1,
                    sound='default',
                    extra={
                        'shipment_id': shipment.id,
                        'invoice_number': shipment.invoice_number,
                        'type': 'delivery_update'
                    }
                )
            
            # Android 디바이스
            android_devices = GCMDevice.objects.filter(user=shipment.order.user, active=True)
            if android_devices.exists():
                android_devices.send_message(
                    message=notification_data['sms_message'],
                    title=notification_data['title'],
                    extra={
                        'shipment_id': shipment.id,
                        'invoice_number': shipment.invoice_number,
                        'type': 'delivery_update'
                    }
                )
            
            # 발송 이력 저장
            if ios_devices.exists() or android_devices.exists():
                DeliveryNotification.objects.create(
                    shipment=shipment,
                    user=shipment.order.user,
                    notification_type='push',
                    status='sent',
                    title=notification_data['title'],
                    message=notification_data['sms_message'],
                    recipient=f"user_{shipment.order.user.id}",
                    sent_at=timezone.now()
                )
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}")
    
    def _get_user_notification_preferences(self, user) -> Dict:
        """사용자 알림 설정 조회"""
        # 사용자 프로필에서 알림 설정 조회
        # 기본값으로 모든 알림 활성화
        try:
            if hasattr(user, 'profile'):
                return {
                    'sms_enabled': getattr(user.profile, 'sms_notifications', True),
                    'email_enabled': getattr(user.profile, 'email_notifications', True),
                    'push_enabled': getattr(user.profile, 'push_notifications', True),
                }
        except:
            pass
        
        return {
            'sms_enabled': True,
            'email_enabled': True,
            'push_enabled': True,
        }
    
    def send_delay_notification(self, shipment: DeliveryShipment):
        """배송 지연 알림"""
        self.send_shipment_notification(shipment, 'delayed')
    
    def send_bulk_notifications(self, shipments: List[DeliveryShipment], event_type: str):
        """대량 알림 발송"""
        for shipment in shipments:
            try:
                self.send_shipment_notification(shipment, event_type)
            except Exception as e:
                logger.error(f"Failed to send bulk notification for shipment {shipment.id}: {str(e)}")
```

### 5.2 알림 템플릿

```html
<!-- templates/emails/shipment_shipped.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>상품 발송 알림</title>
    <style>
        .container { max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .info-box { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .button { 
            display: inline-block; 
            background: #2196F3; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 5px; 
        }
        .footer { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📦 상품이 발송되었습니다!</h2>
        </div>
        
        <div class="content">
            <p>안녕하세요 {{ shipment.recipient_name }}님,</p>
            <p>주문하신 상품이 발송되었습니다.</p>
            
            <div class="info-box">
                <h3>📋 배송 정보</h3>
                <p><strong>상품:</strong> {{ product_name }}</p>
                <p><strong>택배회사:</strong> {{ shipment.delivery_company.name }}</p>
                <p><strong>송장번호:</strong> {{ shipment.invoice_number }}</p>
                <p><strong>수취인:</strong> {{ shipment.recipient_name }}</p>
                <p><strong>배송주소:</strong> {{ shipment.recipient_address }}</p>
                {% if shipment.estimated_delivery %}
                <p><strong>예상도착:</strong> {{ shipment.estimated_delivery|date:"Y년 m월 d일" }}</p>
                {% endif %}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                {% if tracking_url %}
                <a href="{{ tracking_url }}" class="button">🔍 배송 추적하기</a>
                {% endif %}
            </div>
            
            {% if shipment.special_instructions %}
            <div class="info-box">
                <h3>📝 배송 요청사항</h3>
                <p>{{ shipment.special_instructions }}</p>
            </div>
            {% endif %}
            
            <p>배송 상태는 실시간으로 업데이트되며, 상태 변경시 알림을 받으실 수 있습니다.</p>
        </div>
        
        <div class="footer">
            <p>궁금한 점이 있으시면 고객센터로 연락해주세요.</p>
            <p>{{ shipment.delivery_company.name }} 고객센터: {{ shipment.delivery_company.phone }}</p>
        </div>
    </div>
</body>
</html>
```

```html
<!-- templates/emails/shipment_delivered.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>배송 완료 알림</title>
    <style>
        .container { max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .success-box { background: #E8F5E8; border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
        .info-box { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .button { 
            display: inline-block; 
            background: #FF9800; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 5px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🎉 배송이 완료되었습니다!</h2>
        </div>
        
        <div class="content">
            <div class="success-box">
                <h3>✅ 배송 완료</h3>
                <p>{{ product_name }} 상품이 성공적으로 배송되었습니다.</p>
                <p><strong>배송완료시간:</strong> {{ shipment.delivered_at|date:"Y년 m월 d일 H시 i분" }}</p>
            </div>
            
            <p>안녕하세요 {{ shipment.recipient_name }}님,</p>
            <p>주문하신 상품이 배송지에 도착했습니다.</p>
            
            <div class="info-box">
                <h3>📦 배송 정보</h3>
                <p><strong>송장번호:</strong> {{ shipment.invoice_number }}</p>
                <p><strong>택배회사:</strong> {{ shipment.delivery_company.name }}</p>
                <p><strong>배송주소:</strong> {{ shipment.recipient_address }}</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" class="button">⭐ 상품 리뷰 작성하기</a>
            </div>
            
            <p>상품에 만족하셨다면 리뷰를 남겨주세요. 다른 고객들에게 큰 도움이 됩니다!</p>
            <p>문제가 있으시면 고객센터로 언제든지 연락해주세요.</p>
        </div>
        
        <div class="footer">
            <p>저희 쇼핑몰을 이용해주셔서 감사합니다! 🙏</p>
        </div>
    </div>
</body>
</html>
```

### 5.3 배송 상태 변경 시그널

```python
# apps/delivery/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.delivery.models import DeliveryShipment, DeliveryTrackingHistory
from apps.notifications.services import NotificationService

notification_service = NotificationService()

@receiver(post_save, sender=DeliveryShipment)
def shipment_status_changed(sender, instance, created, **kwargs):
    """배송 상태 변경시 알림 발송"""
    if not created:  # 업데이트인 경우만
        # 이전 상태와 비교하여 변경된 경우만 알림
        if hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
            # 상태별 알림 발송
            status_event_map = {
                'collected': 'shipped',
                'in_transit': 'in_transit',
                'out_for_delivery': 'out_for_delivery',
                'delivered': 'delivered',
                'failed': 'failed',
            }
            
            event_type = status_event_map.get(instance.status)
            if event_type:
                notification_service.send_shipment_notification(instance, event_type)

@receiver(post_save, sender=DeliveryTrackingHistory)
def tracking_history_added(sender, instance, created, **kwargs):
    """새로운 추적 이력 추가시"""
    if created:
        # 중요한 상태 변경인 경우만 알림
        important_statuses = ['배송출발', '배송완료', '미배송']
        if instance.status_text in important_statuses:
            event_map = {
                '배송출발': 'out_for_delivery',
                '배송완료': 'delivered',
                '미배송': 'failed',
            }
            
            event_type = event_map.get(instance.status_text)
            if event_type:
                notification_service.send_shipment_notification(instance.shipment, event_type)
```

### 5.4 알림 설정 API

```python
# apps/delivery/api.py에 추가
@router.get("/notifications/{int:shipment_id}", response=List[Dict], auth=AuthBearer())
def get_shipment_notifications(request, shipment_id: int):
    """배송 알림 이력 조회"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인
        if not request.user.is_staff and shipment.order.user != request.user:
            raise HttpError(403, "접근 권한이 없습니다")
        
        notifications = shipment.notifications.order_by('-created')
        
        return [
            {
                'id': notif.id,
                'type': notif.notification_type,
                'status': notif.status,
                'title': notif.title,
                'message': notif.message,
                'recipient': notif.recipient,
                'sent_at': notif.sent_at,
                'created': notif.created,
                'error_message': notif.error_message
            }
            for notif in notifications
        ]
        
    except Exception as e:
        logger.error(f"Notification history error: {str(e)}")
        raise HttpError(500, "알림 이력 조회 중 오류가 발생했습니다")

@router.post("/notifications/{int:shipment_id}/resend", auth=AuthBearer())
def resend_notifications(request, shipment_id: int, notification_type: str = Query(...)):
    """알림 재발송"""
    try:
        shipment = get_object_or_404(DeliveryShipment, id=shipment_id)
        
        # 권한 확인 (관리자만)
        if not request.user.is_staff:
            raise HttpError(403, "관리자만 알림을 재발송할 수 있습니다")
        
        # 현재 상태에 맞는 알림 발송
        status_event_map = {
            'preparing': 'shipped',
            'collected': 'shipped', 
            'in_transit': 'in_transit',
            'out_for_delivery': 'out_for_delivery',
            'delivered': 'delivered',
            'failed': 'failed',
        }
        
        event_type = status_event_map.get(shipment.status, 'in_transit')
        notification_service.send_shipment_notification(shipment, event_type)
        
        return {"success": True, "message": "알림이 재발송되었습니다"}
        
    except Exception as e:
        logger.error(f"Notification resend error: {str(e)}")
        raise HttpError(500, "알림 재발송 중 오류가 발생했습니다")
```

---

## 🚀 6. 배포 및 운영 가이드

실제 서비스 운영을 위한 배포 설정과 모니터링 방법을 알아보겠습니다.

### 6.1 Docker 배포 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 데이터베이스
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: delivery_tracking
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - delivery_network
    restart: unless-stopped

  # Redis (캐시 및 Celery 브로커)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - delivery_network
    restart: unless-stopped

  # Django 웹 애플리케이션
  web:
    build: .
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/delivery_tracking
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - SMARTPARCEL_API_KEY=${SMARTPARCEL_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - db
      - redis
    networks:
      - delivery_network
    restart: unless-stopped

  # Celery Worker (비동기 작업 처리)
  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/delivery_tracking
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - SMARTPARCEL_API_KEY=${SMARTPARCEL_API_KEY}
    depends_on:
      - db
      - redis
    networks:
      - delivery_network
    restart: unless-stopped

  # Celery Beat (스케줄 작업)
  celery_beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/delivery_tracking
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    networks:
      - delivery_network
    restart: unless-stopped

  # Nginx (리버스 프록시)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ssl_certs:/etc/nginx/ssl
    depends_on:
      - web
    networks:
      - delivery_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  ssl_certs:

networks:
  delivery_network:
    driver: bridge
```

### 6.2 Nginx 설정

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 로그 설정
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types application/json application/javascript text/css text/javascript;

    # 업스트림 서버
    upstream django {
        server web:8000;
    }

    # HTTP -> HTTPS 리다이렉트
    server {
        listen 80;
        server_name delivery-tracking.example.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS 서버
    server {
        listen 443 ssl http2;
        server_name delivery-tracking.example.com;

        # SSL 설정
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        # 정적 파일 서빙
        location /static/ {
            alias /app/staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /app/media/;
            expires 7d;
        }

        # API 엔드포인트
        location /api/ {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # API 응답 캐싱 (GET 요청만)
            location ~* ^/api/.*/shipments/.*$ {
                proxy_cache_methods GET HEAD;
                proxy_cache_valid 200 5m;
                add_header X-Cache-Status $upstream_cache_status;
                proxy_pass http://django;
            }
        }

        # 메인 애플리케이션
        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 헬스체크
        location /health/ {
            access_log off;
            proxy_pass http://django;
        }
    }
}
```

### 6.3 모니터링 설정

```python
# config/settings/monitoring.py
import logging
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

# Sentry 설정 (에러 모니터링)
if SENTRY_DSN := config('SENTRY_DSN', default=''):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(auto_enabling=True),
            CeleryIntegration(monitor_beat_tasks=True),
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment=config('ENVIRONMENT', default='production'),
        release=config('VERSION', default='unknown'),
    )

# 구조화된 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'apps.delivery': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# 헬스체크 설정
HEALTH_CHECKS = {
    'database': 'apps.core.health.DatabaseHealthCheck',
    'redis': 'apps.core.health.RedisHealthCheck',
    'external_api': 'apps.delivery.health.SmartParcelHealthCheck',
}
```

```python
# apps/core/health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from apps.delivery.services.smartparcel_client import SmartParcelAPIClient
import redis
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """전체 시스템 헬스체크"""
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'external_api': check_smartparcel_api(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JsonResponse({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': timezone.now().isoformat()
    }, status=status_code)

def check_database():
    """데이터베이스 연결 확인"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False

def check_redis():
    """Redis 연결 확인"""
    try:
        cache.get('health_check')
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False

def check_smartparcel_api():
    """스마트택배 API 연결 확인"""
    try:
        client = SmartParcelAPIClient()
        client.get_company_list()
        return True
    except Exception as e:
        logger.error(f"SmartParcel API health check failed: {str(e)}")
        return False
```

### 6.4 성능 최적화

```python
# apps/delivery/optimizations.py
from django.core.cache import cache
from django.db import models
from django.db.models import Prefetch
from functools import wraps
import hashlib

def cache_result(timeout=300, key_prefix=''):
    """결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 캐시에서 조회
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 함수 실행 후 캐시 저장
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

class OptimizedDeliveryQueries:
    """최적화된 배송 쿼리"""
    
    @staticmethod
    @cache_result(timeout=600, key_prefix='delivery')
    def get_active_shipments_summary():
        """활성 배송 요약 정보 (캐싱)"""
        from apps.delivery.models import DeliveryShipment
        
        return DeliveryShipment.objects.filter(
            status__in=['preparing', 'collected', 'in_transit', 'out_for_delivery']
        ).values('status').annotate(count=models.Count('id'))
    
    @staticmethod
    def get_shipments_with_tracking(user_id=None, limit=20):
        """추적 정보 포함 배송 목록"""
        from apps.delivery.models import DeliveryShipment, DeliveryTrackingHistory
        
        queryset = DeliveryShipment.objects.select_related(
            'delivery_company',
            'order'
        ).prefetch_related(
            Prefetch(
                'tracking_history',
                queryset=DeliveryTrackingHistory.objects.order_by('-occurred_at')[:3],
                to_attr='latest_tracking'
            )
        )
        
        if user_id:
            queryset = queryset.filter(order__user_id=user_id)
        
        return queryset.order_by('-created')[:limit]

# 인덱스 최적화
class Meta:
    indexes = [
        models.Index(fields=['delivery_company', 'invoice_number']),
        models.Index(fields=['status', 'created']),
        models.Index(fields=['order', 'status']),
        models.Index(fields=['last_tracking_update']),
    ]
```

### 6.5 운영 스크립트

```bash
#!/bin/bash
# scripts/deploy.sh
set -e

echo "🚀 Starting deployment..."

# 환경 변수 로드
source .env.production

# Docker 컨테이너 빌드 및 배포
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml build --no-cache
docker-compose -f docker-compose.yml up -d

# 데이터베이스 마이그레이션
echo "📦 Running migrations..."
docker-compose exec web python manage.py migrate --no-input

# 정적 파일 수집
echo "📦 Collecting static files..."
docker-compose exec web python manage.py collectstatic --no-input

# 초기 데이터 설정
echo "📦 Setting up delivery companies..."
docker-compose exec web python manage.py setup_delivery_companies

# 헬스체크
echo "🔍 Health check..."
sleep 10
curl -f http://localhost/health/ || exit 1

echo "✅ Deployment completed!"

# Celery 작업 스케줄 설정
echo "⏰ Setting up scheduled tasks..."
docker-compose exec celery_beat python manage.py shell << EOF
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# 배송 추적 업데이트 (10분마다)
schedule, created = IntervalSchedule.objects.get_or_create(
    every=10,
    period=IntervalSchedule.MINUTES,
)
PeriodicTask.objects.get_or_create(
    name='Update Active Shipments',
    task='apps.delivery.tasks.bulk_update_active_shipments',
    interval=schedule,
)

# 배송 지연 체크 (1시간마다)
schedule, created = IntervalSchedule.objects.get_or_create(
    every=1,
    period=IntervalSchedule.HOURS,
)
PeriodicTask.objects.get_or_create(
    name='Check Delivery Delays',
    task='apps.delivery.tasks.check_delivery_delays',
    interval=schedule,
)
EOF

echo "✅ All tasks completed!"
```

```bash
#!/bin/bash
# scripts/backup.sh
# 데이터베이스 백업 스크립트

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/postgres"
CONTAINER_NAME="delivery_tracking_db_1"

mkdir -p $BACKUP_DIR

echo "🗄️ Creating database backup..."
docker exec $CONTAINER_NAME pg_dump -U postgres delivery_tracking > $BACKUP_DIR/backup_$DATE.sql

# 압축
gzip $BACKUP_DIR/backup_$DATE.sql

# 7일 이상 된 백업 파일 삭제
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "✅ Backup completed: backup_$DATE.sql.gz"
```

## ✅ 마무리

이번 포스트에서 구현한 **Django Ninja 배송추적 시스템**의 핵심 기능들:

### 🎯 완성된 기능들

#### 🏗️ **견고한 시스템 아키텍처**
- 확장 가능한 모델 설계
- 다중 택배사 지원 구조
- 실시간 데이터 동기화

#### 🔌 **스마트택배 API 완벽 연동**
- 실시간 배송 추적
- 자동 택배사 추천
- 에러 처리 및 재시도 로직

#### ⚡ **현대적 Django Ninja API**
- 타입 안전한 Pydantic 스키마
- 자동 API 문서화
- RESTful 엔드포인트 설계

#### 📱 **실시간 알림 시스템**
- SMS, 이메일, 푸시 멀티채널
- 상태별 맞춤 알림
- 실패 처리 및 재발송

#### 🚀 **운영 최적화**
- Docker 컨테이너 배포
- 성능 최적화 및 캐싱
- 모니터링 및 헬스체크

### 🌟 실무 적용 포인트

1. **확장성**: 새로운 택배사 추가가 간단
2. **안정성**: 외부 API 장애에 대한 복원력
3. **사용자 경험**: 실시간 추적 및 알림
4. **운영 편의성**: 자동화된 배포 및 모니터링

이 시스템은 **실제 e-커머스 서비스**에 바로 적용할 수 있는 수준으로 설계되었습니다. Django Ninja의 **현대적 API 개발 방식**과 **외부 API 연동 노하우**를 모두 담았습니다.

---

> 💬 **배송 추적 관련 질문이나 개선 아이디어가 있으시다면** 댓글로 공유해주세요!  
> 🔔 **실무 Django 개발 팁을 받아보고 싶다면** 구독해주세요!

**관련 포스트:**
- [Django Ninja 쇼핑몰 중급편]({% post_url 2025-10-23-django-ninja-advanced-shopping-mall %}) ← 이전 포스트
- [Django 외부 API 연동 완벽 가이드](#) ← 다음 예정
- [실시간 알림 시스템 구축하기](#) ← 다음 예정
