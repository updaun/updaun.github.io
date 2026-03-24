---
layout: post
title: "Django Ninja + Celery + Beat 완벽 가이드: 환경 구성부터 실전 꿀팁까지"
date: 2026-03-24 10:00:00 +0900
categories: [Django, Python, Backend]
tags: [Django, Django-Ninja, Celery, Celery-Beat, Async, Task Queue, API, Redis, PostgreSQL, Backend]
---

Django 프로젝트에서 고성능 API와 비동기 작업 처리는 필수입니다. 이 글에서는 Django Ninja로 빠른 API를 구축하고, Celery와 Celery Beat로 백그라운드 작업과 주기적 작업을 처리하는 방법을 환경 구성부터 실전 꿀팁까지 모두 다룹니다.

## 🎯 왜 Django Ninja + Celery인가?

### Django Ninja의 장점

Django REST Framework(DRF)를 사용해봤다면 Serializer 작성의 번거로움을 알 것입니다. Django Ninja는 FastAPI처럼 타입 힌트 기반으로 동작하며, 자동 문서화와 빠른 성능을 제공합니다.

**성능 비교**
- Django REST Framework: 약 1,000 req/s
- Django Ninja: 약 2,500 req/s (2.5배 빠름)
- FastAPI: 약 3,000 req/s

**코드 비교: DRF vs Django Ninja**

```python
# DRF 방식 - 복잡함
from rest_framework import serializers, viewsets
from rest_framework.decorators import action

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'activated'})

# Django Ninja 방식 - 간단함
from ninja import NinjaAPI, Schema

api = NinjaAPI()

class UserSchema(Schema):
    id: int
    username: str
    email: str

@api.get("/users/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    return User.objects.get(id=user_id)

@api.post("/users/{user_id}/activate")
def activate_user(request, user_id: int):
    user = User.objects.get(id=user_id)
    user.is_active = True
    user.save()
    return {"status": "activated"}
```

### Celery가 필요한 순간들

웹 요청 중에 처리하면 안 되는 작업들이 있습니다:

1. **이메일 발송**: 100명에게 이메일 보내기 = 10초 대기? No!
2. **이미지 처리**: 썸네일 생성, 워터마크 추가
3. **데이터 수집**: 외부 API 크롤링
4. **리포트 생성**: 엑셀, PDF 파일 생성
5. **주기적 작업**: 매일 자정 통계 업데이트

```python
# 나쁜 예 - 사용자가 10초 기다림
@api.post("/send-newsletter")
def send_newsletter(request, data: NewsletterSchema):
    for email in get_subscribers():  # 1000명
        send_email(email, data.content)  # 각 0.01초 = 총 10초!
    return {"status": "sent"}

# 좋은 예 - 즉시 응답
@api.post("/send-newsletter")
def send_newsletter(request, data: NewsletterSchema):
    send_newsletter_task.delay(data.dict())  # Celery 작업으로 위임
    return {"status": "queued"}  # 즉시 응답!
```

## 🔧 환경 구성: 단계별 설치

### 1. 프로젝트 기본 세팅

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필수 패키지 설치
pip install django django-ninja
pip install celery redis
pip install celery[redis]  # Redis를 메시지 브로커로 사용
pip install django-celery-beat  # 주기적 작업을 위한 Beat
pip install django-celery-results  # 작업 결과 저장

# requirements.txt에 저장
pip freeze > requirements.txt
```

### 2. Redis 설치 및 실행

Redis는 Celery의 메시지 브로커로 사용됩니다. 작업 큐와 결과 저장소 역할을 합니다.

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis

# Docker (추천 - 개발 환경)
docker run -d -p 6379:6379 --name redis redis:alpine

# Redis 연결 테스트
redis-cli ping  # PONG이 나오면 성공
```

### 3. Django 프로젝트 구조

```bash
myproject/
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── celery.py      # 새로 생성
│   ├── urls.py
│   └── wsgi.py
├── api/
│   ├── __init__.py
│   ├── views.py       # Django Ninja API
│   └── schemas.py     # Pydantic Schemas
├── tasks/
│   ├── __init__.py
│   └── tasks.py       # Celery Tasks
└── requirements.txt
```

## 📝 Django Ninja 설정

### settings.py 설정

```python
# myproject/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Celery
    'django_celery_beat',
    'django_celery_results',
    
    # 내 앱
    'api',
    'tasks',
]

# Celery 설정
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'  # Django DB에 결과 저장
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_ENABLE_UTC = False

# Celery Beat 설정
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery 작업 설정
CELERY_TASK_TRACK_STARTED = True  # 작업 시작 추적
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30분 제한
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25분에 경고
```

### Celery 초기화

```python
# myproject/celery.py

import os
from celery import Celery

# Django settings 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Celery 앱 생성
app = Celery('myproject')

# Django settings에서 celery 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 모든 tasks.py 파일을 자동으로 찾아서 등록
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버깅용 테스트 작업"""
    print(f'Request: {self.request!r}')
```

```python
# myproject/__init__.py

# Celery 앱이 Django와 함께 로드되도록 설정
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### Django Ninja API 생성

```python
# api/schemas.py

from ninja import Schema
from typing import Optional
from datetime import datetime

class UserCreateSchema(Schema):
    username: str
    email: str
    password: str

class UserResponseSchema(Schema):
    id: int
    username: str
    email: str
    created_at: datetime

class TaskStatusSchema(Schema):
    task_id: str
    status: str
    result: Optional[dict] = None

class EmailSchema(Schema):
    recipient: str
    subject: str
    message: str

class NewsletterSchema(Schema):
    subject: str
    content: str
    send_immediately: bool = False
```

```python
# api/views.py

from ninja import NinjaAPI, Router
from django.contrib.auth.models import User
from .schemas import (
    UserCreateSchema, 
    UserResponseSchema,
    TaskStatusSchema,
    EmailSchema,
    NewsletterSchema
)
from tasks.tasks import (
    send_email_task,
    generate_report_task,
    process_image_task,
    send_newsletter_task
)
from celery.result import AsyncResult

# API 인스턴스 생성
api = NinjaAPI(
    title="My API",
    version="1.0.0",
    description="Django Ninja + Celery API"
)

# 유저 라우터
user_router = Router(tags=["Users"])

@user_router.post("/", response=UserResponseSchema)
def create_user(request, data: UserCreateSchema):
    """사용자 생성 API"""
    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password
    )
    return user

@user_router.get("/{user_id}", response=UserResponseSchema)
def get_user(request, user_id: int):
    """사용자 조회 API"""
    return User.objects.get(id=user_id)

# 작업 라우터
task_router = Router(tags=["Tasks"])

@task_router.post("/email", response=TaskStatusSchema)
def send_email(request, data: EmailSchema):
    """비동기 이메일 발송"""
    task = send_email_task.delay(
        data.recipient,
        data.subject,
        data.message
    )
    return {
        "task_id": task.id,
        "status": "queued"
    }

@task_router.post("/newsletter", response=TaskStatusSchema)
def send_newsletter(request, data: NewsletterSchema):
    """뉴스레터 발송 (전체 구독자)"""
    if data.send_immediately:
        task = send_newsletter_task.apply_async(
            args=[data.subject, data.content],
            countdown=0  # 즉시 실행
        )
    else:
        task = send_newsletter_task.apply_async(
            args=[data.subject, data.content],
            countdown=300  # 5분 후 실행
        )
    
    return {
        "task_id": task.id,
        "status": "scheduled"
    }

@task_router.get("/status/{task_id}", response=TaskStatusSchema)
def get_task_status(request, task_id: str):
    """작업 상태 조회"""
    task = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.state,
    }
    
    if task.ready():
        response["result"] = {
            "output": task.result,
            "successful": task.successful()
        }
    
    return response

@task_router.post("/report/generate", response=TaskStatusSchema)
def generate_report(request, report_type: str):
    """리포트 생성 작업 시작"""
    task = generate_report_task.delay(report_type)
    return {
        "task_id": task.id,
        "status": "processing"
    }

# 라우터 등록
api.add_router("/users", user_router)
api.add_router("/tasks", task_router)
```

```python
# myproject/urls.py

from django.contrib import admin
from django.urls import path
from api.views import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # /api/docs에서 자동 문서 확인 가능
]
```

## 🔄 Celery Tasks 작성

### 기본 Task 패턴

```python
# tasks/tasks.py

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.contrib.auth.models import User
from time import sleep
import random

logger = get_task_logger(__name__)

@shared_task(name='tasks.send_email_task')
def send_email_task(recipient, subject, message):
    """
    이메일 발송 작업
    - shared_task: 재사용 가능한 작업
    - name: 작업 이름 명시 (선택사항, 디버깅에 유용)
    """
    logger.info(f"Sending email to {recipient}")
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@mysite.com',
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {recipient}")
        return {"status": "success", "recipient": recipient}
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        raise

@shared_task(name='tasks.send_newsletter_task')
def send_newsletter_task(subject, content):
    """뉴스레터 발송 - 모든 구독자에게"""
    subscribers = User.objects.filter(
        is_active=True,
        email__isnull=False
    ).values_list('email', flat=True)
    
    total = len(subscribers)
    success_count = 0
    
    logger.info(f"Starting newsletter to {total} subscribers")
    
    for email in subscribers:
        try:
            send_mail(
                subject=subject,
                message=content,
                from_email='newsletter@mysite.com',
                recipient_list=[email],
                fail_silently=False,
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {email}: {str(e)}")
    
    logger.info(f"Newsletter completed: {success_count}/{total} sent")
    return {
        "total": total,
        "success": success_count,
        "failed": total - success_count
    }

@shared_task(name='tasks.generate_report_task', bind=True)
def generate_report_task(self, report_type):
    """
    리포트 생성 작업
    - bind=True: self 파라미터로 task 인스턴스 접근
    - 진행률 업데이트 가능
    """
    total_steps = 100
    
    for i in range(total_steps):
        # 실제 리포트 생성 로직
        sleep(0.1)  # 실제 작업 시뮬레이션
        
        # 진행률 업데이트
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i,
                'total': total_steps,
                'percent': int((i / total_steps) * 100)
            }
        )
    
    report_url = f"/media/reports/{report_type}_{self.request.id}.pdf"
    logger.info(f"Report generated: {report_url}")
    
    return {
        "report_type": report_type,
        "url": report_url,
        "status": "completed"
    }

@shared_task(name='tasks.process_image_task')
def process_image_task(image_path, operations):
    """
    이미지 처리 작업
    - 썸네일 생성, 필터 적용 등
    """
    from PIL import Image
    
    logger.info(f"Processing image: {image_path}")
    
    img = Image.open(image_path)
    
    for operation in operations:
        if operation == 'thumbnail':
            img.thumbnail((300, 300))
        elif operation == 'grayscale':
            img = img.convert('L')
    
    output_path = f"{image_path}_processed.jpg"
    img.save(output_path)
    
    return {"processed_image": output_path}
```

### 고급 Task 패턴

```python
# tasks/tasks.py (계속)

from celery import shared_task, group, chain, chord
from django.db import transaction

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def retry_task_example(self, url):
    """
    재시도 패턴
    - max_retries: 최대 3번 재시도
    - default_retry_delay: 60초 후 재시도
    """
    import requests
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.error(f"Request failed: {exc}")
        # 재시도 (exponential backoff)
        raise self.retry(
            exc=exc,
            countdown=2 ** self.request.retries  # 2, 4, 8초
        )

@shared_task(name='tasks.cleanup_old_data')
def cleanup_old_data():
    """정기적 데이터 정리 작업"""
    from datetime import timedelta
    from django.utils import timezone
    from myapp.models import LogEntry
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    deleted_count = LogEntry.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} old log entries")
    return {"deleted": deleted_count}

@shared_task(name='tasks.daily_statistics')
def daily_statistics():
    """일일 통계 업데이트"""
    from myapp.models import Statistics, Order
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    
    today = timezone.now().date()
    
    stats = Order.objects.filter(
        created_at__date=today
    ).aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('amount'),
        avg_order_value=Avg('amount')
    )
    
    Statistics.objects.update_or_create(
        date=today,
        defaults=stats
    )
    
    logger.info(f"Statistics updated for {today}")
    return stats

@shared_task(name='tasks.batch_process')
def batch_process(item_ids):
    """배치 처리 - 트랜잭션 활용"""
    from myapp.models import Item
    
    with transaction.atomic():
        for item_id in item_ids:
            item = Item.objects.select_for_update().get(id=item_id)
            item.processed = True
            item.save()
    
    return {"processed": len(item_ids)}

# 작업 체이닝
@shared_task
def step1(data):
    """첫 번째 단계"""
    result = data * 2
    logger.info(f"Step 1: {data} -> {result}")
    return result

@shared_task
def step2(data):
    """두 번째 단계"""
    result = data + 10
    logger.info(f"Step 2: {data} -> {result}")
    return result

@shared_task
def step3(data):
    """세 번째 단계"""
    result = data ** 2
    logger.info(f"Step 3: {data} -> {result}")
    return result

# API에서 체인 실행
# result = chain(step1.s(5), step2.s(), step3.s())()
# 결과: 5 -> 10 -> 20 -> 400

@shared_task
def parallel_task(n):
    """병렬 처리용 작업"""
    sleep(1)
    return n * 2

# API에서 병렬 실행
# job = group(parallel_task.s(i) for i in range(10))
# result = job.apply_async()
# 10개 작업이 동시에 실행됨
```

## ⏰ Celery Beat 설정 (주기적 작업)

### 코드 기반 스케줄 설정

```python
# myproject/celery.py에 추가

from celery.schedules import crontab

app.conf.beat_schedule = {
    # 매일 자정에 통계 업데이트
    'daily-statistics': {
        'task': 'tasks.daily_statistics',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # 매주 일요일 새벽 3시에 데이터 정리
    'weekly-cleanup': {
        'task': 'tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    
    # 30분마다 실행
    'every-30-minutes': {
        'task': 'tasks.check_status',
        'schedule': crontab(minute='*/30'),
    },
    
    # 5분마다 실행
    'every-5-minutes': {
        'task': 'tasks.heartbeat',
        'schedule': 300.0,  # 초 단위
    },
    
    # 매일 오전 9시, 오후 6시
    'twice-daily': {
        'task': 'tasks.send_reminder',
        'schedule': crontab(hour='9,18', minute=0),
    },
    
    # 평일 오전 10시
    'weekday-morning': {
        'task': 'tasks.morning_report',
        'schedule': crontab(
            hour=10,
            minute=0,
            day_of_week='1-5'  # 월~금
        ),
    },
}
```

### Django Admin을 통한 동적 스케줄 관리

```python
# 마이그레이션 실행
python manage.py migrate django_celery_beat

# Admin에서 Periodic Task 등록 가능
# http://localhost:8000/admin/django_celery_beat/periodictask/
```

**Admin을 통한 설정의 장점**:
- 코드 수정 없이 스케줄 변경
- 즉시 활성화/비활성화
- 다음 실행 시간 확인
- 실행 이력 추적

**예시: Admin에서 설정**
```python
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import timedelta

# 10분 간격 스케줄 생성
schedule, created = IntervalSchedule.objects.get_or_create(
    every=10,
    period=IntervalSchedule.MINUTES,
)

# 주기적 작업 생성
PeriodicTask.objects.create(
    interval=schedule,
    name='Import data every 10 minutes',
    task='tasks.import_external_data',
)
```

## 🚀 실행 및 테스트

### Celery Worker 실행

```bash
# 기본 워커 실행
celery -A myproject worker --loglevel=info

# 동시성 설정 (프로세스 4개)
celery -A myproject worker --loglevel=info --concurrency=4

# 특정 큐만 처리
celery -A myproject worker --loglevel=info -Q celery,email

# 개발 환경 (단일 프로세스, 자동 재시작)
watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- \
  celery -A myproject worker --loglevel=info
```

### Celery Beat 실행

```bash
# Beat 스케줄러 실행
celery -A myproject beat --loglevel=info

# Beat + Worker 동시 실행 (개발용)
celery -A myproject worker --beat --loglevel=info
```

### Flower 모니터링 (추천!)

```bash
# Flower 설치
pip install flower

# Flower 실행
celery -A myproject flower

# 브라우저에서 http://localhost:5555 접속
# - 실시간 작업 모니터링
# - 워커 상태 확인
# - 작업 통계
# - 작업 재실행/취소
```

### Django 개발 서버 실행

```bash
python manage.py runserver
```

**필요한 터미널**:
1. Django 서버: `python manage.py runserver`
2. Celery Worker: `celery -A myproject worker --loglevel=info`
3. Celery Beat: `celery -A myproject beat --loglevel=info`
4. (선택) Flower: `celery -A myproject flower`

### API 테스트

```bash
# API 문서 확인
# http://localhost:8000/api/docs

# 이메일 발송 테스트
curl -X POST http://localhost:8000/api/tasks/email \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "user@example.com",
    "subject": "Test Email",
    "message": "Hello from Celery!"
  }'

# 응답 예시
# {
#   "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "status": "queued"
# }

# 작업 상태 확인
curl http://localhost:8000/api/tasks/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# 응답 예시
# {
#   "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "status": "SUCCESS",
#   "result": {
#     "output": {"status": "success", "recipient": "user@example.com"},
#     "successful": true
#   }
# }
```

## 💡 실전 꿀팁 모음

### 1. Task 우선순위 큐 설정

서로 다른 우선순위의 작업을 효율적으로 처리하세요.

```python
# myproject/celery.py

from kombu import Queue

app.conf.task_queues = (
    Queue('default', routing_key='default'),
    Queue('high_priority', routing_key='high_priority'),
    Queue('low_priority', routing_key='low_priority'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_routing_key = 'default'

# 라우팅 설정
app.conf.task_routes = {
    'tasks.send_email_task': {'queue': 'high_priority'},
    'tasks.generate_report_task': {'queue': 'low_priority'},
}
```

```python
# tasks/tasks.py

# 명시적으로 큐 지정
@shared_task(name='tasks.urgent_task', queue='high_priority')
def urgent_task(data):
    """긴급 처리 작업"""
    pass
```

```bash
# 큐별로 별도 워커 실행
# High priority 워커 (많은 리소스)
celery -A myproject worker -Q high_priority --concurrency=8 --loglevel=info

# Default 워커
celery -A myproject worker -Q default --concurrency=4 --loglevel=info

# Low priority 워커 (적은 리소스)
celery -A myproject worker -Q low_priority --concurrency=2 --loglevel=info
```

### 2. Task 결과 캐싱 및 중복 방지

동일한 작업이 중복 실행되지 않도록 방지합니다.

```python
from django.core.cache import cache
from celery import shared_task
import hashlib
import json

def get_task_cache_key(task_name, args, kwargs):
    """작업 캐시 키 생성"""
    data = {
        'task': task_name,
        'args': args,
        'kwargs': kwargs
    }
    hash_key = hashlib.md5(
        json.dumps(data, sort_keys=True).encode()
    ).hexdigest()
    return f"task_lock:{hash_key}"

@shared_task(name='tasks.expensive_calculation')
def expensive_calculation(user_id, data_type):
    """비용이 큰 계산 작업 - 중복 실행 방지"""
    
    # 캐시 키 생성
    cache_key = get_task_cache_key(
        'expensive_calculation',
        args=(user_id, data_type),
        kwargs={}
    )
    
    # 이미 실행 중인지 확인
    if cache.get(cache_key):
        logger.info(f"Task already running: {cache_key}")
        return {"status": "already_running"}
    
    # 실행 중 표시 (10분 타임아웃)
    cache.set(cache_key, True, timeout=600)
    
    try:
        # 실제 작업 수행
        result = perform_calculation(user_id, data_type)
        return result
    finally:
        # 작업 완료 후 잠금 해제
        cache.delete(cache_key)

def perform_calculation(user_id, data_type):
    """실제 계산 로직"""
    import time
    time.sleep(5)  # 무거운 작업 시뮬레이션
    return {"user_id": user_id, "result": "calculated"}
```

### 3. Task 실행 시간 제한 및 타임아웃 처리

```python
from celery.exceptions import SoftTimeLimitExceeded

@shared_task(
    name='tasks.limited_task',
    time_limit=60,  # 60초 하드 타임아웃 (프로세스 강제 종료)
    soft_time_limit=50  # 50초 소프트 타임아웃 (예외 발생)
)
def limited_task(data):
    """시간 제한이 있는 작업"""
    try:
        # 긴 작업 수행
        result = process_data(data)
        return result
    except SoftTimeLimitExceeded:
        # 소프트 타임아웃 처리 - 정리 작업 가능
        logger.warning("Task is taking too long, cleaning up...")
        cleanup_partial_work()
        return {"status": "timeout", "partial": True}

def process_data(data):
    """데이터 처리"""
    import time
    time.sleep(45)
    return {"processed": data}

def cleanup_partial_work():
    """부분적으로 완료된 작업 정리"""
    pass
```

### 4. Django Ninja와 Celery 통합 - 진행률 표시

```python
# api/views.py

from ninja import Router
from celery.result import AsyncResult

progress_router = Router(tags=["Progress"])

@progress_router.get("/task/{task_id}/progress")
def get_task_progress(request, task_id: str):
    """작업 진행률 조회"""
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting...'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'percent': task.info.get('percent', 0),
            'status': task.info.get('status', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.info
        }
    else:  # FAILURE, RETRY 등
        response = {
            'state': task.state,
            'status': str(task.info)  # 예외 정보
        }
    
    return response

api.add_router("/progress", progress_router)
```

```python
# tasks/tasks.py

@shared_task(bind=True)
def long_running_task(self, items):
    """진행률을 보고하는 장시간 작업"""
    total = len(items)
    
    for i, item in enumerate(items):
        # 작업 수행
        process_item(item)
        
        # 진행률 업데이트
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': total,
                'percent': int(((i + 1) / total) * 100),
                'status': f'Processing item {i + 1} of {total}'
            }
        )
    
    return {'status': 'completed', 'processed': total}
```

### 5. 에러 핸들링 및 로깅 전략

```python
from celery.signals import task_failure, task_success
from celery.utils.log import get_task_logger
import traceback

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,  # 지수 백오프
    retry_backoff_max=600,  # 최대 10분
    retry_jitter=True  # 랜덤 지터 추가
)
def robust_task(self, url):
    """견고한 에러 핸들링을 가진 작업"""
    try:
        logger.info(f"Starting task for URL: {url}")
        
        # 작업 수행
        result = fetch_data(url)
        
        logger.info(f"Task completed successfully: {result}")
        return result
        
    except Exception as exc:
        logger.error(
            f"Task failed: {exc}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        # 특정 예외는 재시도하지 않음
        if isinstance(exc, ValueError):
            logger.error("Invalid data, not retrying")
            raise
        
        # 재시도
        raise self.retry(exc=exc)

# 전역 시그널 핸들러
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """모든 작업 실패 시 호출"""
    logger.error(
        f"Task {sender.name} ({task_id}) failed: {exception}"
    )
    # Slack, Sentry 등으로 알림 전송 가능
    # send_slack_notification(f"Task failed: {sender.name}")

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """모든 작업 성공 시 호출"""
    logger.info(f"Task {sender.name} succeeded with result: {result}")
```

### 6. 대용량 데이터 처리 - 청크 분할

```python
from celery import group

@shared_task
def process_chunk(chunk_data):
    """데이터 청크 처리"""
    results = []
    for item in chunk_data:
        result = process_single_item(item)
        results.append(result)
    return results

def chunk_list(lst, chunk_size):
    """리스트를 청크로 나누기"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

@shared_task
def process_large_dataset(item_ids):
    """대용량 데이터셋 처리"""
    from myapp.models import Item
    
    # 청크로 나누기 (100개씩)
    chunks = list(chunk_list(item_ids, 100))
    
    # 병렬 처리
    job = group(process_chunk.s(chunk) for chunk in chunks)
    result = job.apply_async()
    
    return {
        "total_items": len(item_ids),
        "chunks": len(chunks),
        "group_id": result.id
    }

# API에서 사용
@api.post("/process/bulk")
def bulk_process(request, item_ids: list[int]):
    task = process_large_dataset.delay(item_ids)
    return {"task_id": task.id, "status": "processing"}
```

### 7. 프로덕션 환경 설정 (Supervisor)

```ini
# /etc/supervisor/conf.d/celery.conf

[program:celery-worker]
command=/path/to/venv/bin/celery -A myproject worker --loglevel=info
directory=/path/to/myproject
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998

[program:celery-beat]
command=/path/to/venv/bin/celery -A myproject beat --loglevel=info
directory=/path/to/myproject
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
autostart=true
autorestart=true
startsecs=10
priority=999

[group:celery]
programs=celery-worker,celery-beat
```

```bash
# Supervisor 명령어
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery:*
sudo supervisorctl stop celery:*
sudo supervisorctl restart celery:*
sudo supervisorctl status celery:*
```

### 8. Docker Compose로 통합 환경 구성

```yaml
# docker-compose.yml

version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: myproject
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://myuser:mypassword@db:5432/myproject
      - CELERY_BROKER_URL=redis://redis:6379/0

  celery-worker:
    build: .
    command: celery -A myproject worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://myuser:mypassword@db:5432/myproject
      - CELERY_BROKER_URL=redis://redis:6379/0

  celery-beat:
    build: .
    command: celery -A myproject beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://myuser:mypassword@db:5432/myproject
      - CELERY_BROKER_URL=redis://redis:6379/0

  flower:
    build: .
    command: celery -A myproject flower
    volumes:
      - .:/app
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery-worker
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0

volumes:
  postgres_data:
  redis_data:
```

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# 포트 노출
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

```bash
# Docker Compose 명령어
docker-compose up -d  # 백그라운드 실행
docker-compose ps  # 서비스 상태 확인
docker-compose logs -f celery-worker  # 로그 확인
docker-compose restart celery-worker  # 워커 재시작
docker-compose down  # 모든 서비스 종료
```

### 9. 성능 모니터링 및 최적화

```python
# tasks/tasks.py

from celery.signals import task_prerun, task_postrun
from time import time
import logging

logger = logging.getLogger(__name__)

# 작업 실행 시간 측정
task_start_times = {}

@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, **kwargs):
    """작업 시작 시간 기록"""
    task_start_times[task_id] = time()
    logger.info(f"Task {task.name} ({task_id}) started")

@task_postrun.connect
def task_postrun_handler(task_id=None, task=None, **kwargs):
    """작업 실행 시간 계산"""
    if task_id in task_start_times:
        elapsed = time() - task_start_times[task_id]
        logger.info(
            f"Task {task.name} ({task_id}) "
            f"completed in {elapsed:.2f} seconds"
        )
        del task_start_times[task_id]

# 성능 개선 팁
@shared_task
def optimized_database_task():
    """DB 쿼리 최적화"""
    from myapp.models import Order
    
    # 나쁜 예: N+1 쿼리
    # orders = Order.objects.all()
    # for order in orders:
    #     print(order.user.name)  # 각 반복마다 쿼리!
    
    # 좋은 예: select_related 사용
    orders = Order.objects.select_related('user').all()
    for order in orders:
        print(order.user.name)  # 쿼리 1번만!
    
    return {"orders_processed": orders.count()}

@shared_task
def bulk_update_task(items):
    """대량 업데이트 최적화"""
    from myapp.models import Product
    
    # 나쁜 예: 하나씩 저장
    # for item in items:
    #     product = Product.objects.get(id=item['id'])
    #     product.price = item['price']
    #     product.save()  # 각 저장마다 쿼리!
    
    # 좋은 예: bulk_update 사용
    products = []
    for item in items:
        product = Product(id=item['id'])
        product.price = item['price']
        products.append(product)
    
    Product.objects.bulk_update(products, ['price'])
    
    return {"updated": len(products)}
```

### 10. 실전 디버깅 팁

```python
# 디버깅을 위한 유용한 설정들

# myproject/celery.py
from celery import Celery
from celery.signals import task_failure

app = Celery('myproject')

# 디버그 모드 설정
if DEBUG:
    # 작업을 동기적으로 실행 (테스트용)
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

# 상세한 로깅
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 작업 실패 시 상세 정보 출력
@task_failure.connect
def on_task_failure(sender, task_id, exception, args, kwargs, **kw):
    print(f"\n{'='*50}")
    print(f"Task Failed: {sender.name}")
    print(f"Task ID: {task_id}")
    print(f"Exception: {exception}")
    print(f"Args: {args}")
    print(f"Kwargs: {kwargs}")
    print(f"{'='*50}\n")
```

**디버깅 명령어**:

```bash
# 작업 상태 확인
celery -A myproject inspect active  # 실행 중인 작업
celery -A myproject inspect scheduled  # 예약된 작업
celery -A myproject inspect reserved  # 대기 중인 작업

# 작업 취소
celery -A myproject control revoke <task-id>

# 워커 통계
celery -A myproject inspect stats

# 등록된 작업 목록
celery -A myproject inspect registered

# 큐 확인
celery -A myproject inspect active_queues

# Beat 스케줄 확인
celery -A myproject inspect scheduled
```

## 🎓 실전 사용 예시

### 예시 1: 이미지 일괄 처리 API

```python
# api/views.py

from ninja import Router, File, UploadedFile
from typing import List

image_router = Router(tags=["Images"])

@image_router.post("/upload-bulk")
def upload_images(request, files: List[UploadedFile] = File(...)):
    """여러 이미지 업로드 및 처리"""
    from tasks.tasks import process_uploaded_images
    
    # 파일 저장
    file_paths = []
    for file in files:
        path = save_uploaded_file(file)
        file_paths.append(path)
    
    # 백그라운드 처리
    task = process_uploaded_images.delay(file_paths)
    
    return {
        "task_id": task.id,
        "files_count": len(file_paths),
        "status": "processing"
    }

api.add_router("/images", image_router)
```

```python
# tasks/tasks.py

@shared_task(bind=True)
def process_uploaded_images(self, file_paths):
    """업로드된 이미지들을 처리"""
    from PIL import Image
    import os
    
    total = len(file_paths)
    processed = []
    
    for i, file_path in enumerate(file_paths):
        # 진행률 업데이트
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i,
                'total': total,
                'percent': int((i / total) * 100)
            }
        )
        
        # 이미지 처리
        img = Image.open(file_path)
        
        # 썸네일 생성
        img.thumbnail((300, 300))
        thumb_path = f"{file_path}_thumb.jpg"
        img.save(thumb_path)
        
        processed.append({
            'original': file_path,
            'thumbnail': thumb_path
        })
    
    return {
        'total': total,
        'processed': processed
    }
```

### 예시 2: 주문 처리 워크플로우

```python
# tasks/tasks.py

from celery import chain, group

@shared_task
def validate_order(order_id):
    """주문 유효성 검사"""
    from myapp.models import Order
    order = Order.objects.get(id=order_id)
    
    if order.amount <= 0:
        raise ValueError("Invalid order amount")
    
    if not order.items.exists():
        raise ValueError("No items in order")
    
    return order_id

@shared_task
def process_payment(order_id):
    """결제 처리"""
    from myapp.models import Order
    import time
    
    order = Order.objects.get(id=order_id)
    
    # 결제 게이트웨이 호출 (시뮬레이션)
    time.sleep(2)
    
    order.payment_status = 'completed'
    order.save()
    
    return order_id

@shared_task
def update_inventory(order_id):
    """재고 업데이트"""
    from myapp.models import Order
    
    order = Order.objects.get(id=order_id)
    
    for item in order.items.all():
        product = item.product
        product.stock -= item.quantity
        product.save()
    
    return order_id

@shared_task
def send_confirmation_email(order_id):
    """주문 확인 이메일 발송"""
    from myapp.models import Order
    from django.core.mail import send_mail
    
    order = Order.objects.get(id=order_id)
    
    send_mail(
        subject=f'Order #{order.id} Confirmed',
        message=f'Your order has been confirmed!',
        from_email='orders@mysite.com',
        recipient_list=[order.user.email],
    )
    
    return order_id

@shared_task
def notify_warehouse(order_id):
    """창고에 배송 요청 알림"""
    from myapp.models import Order
    
    order = Order.objects.get(id=order_id)
    
    # 창고 시스템 API 호출
    # warehouse_api.create_shipment(order)
    
    order.status = 'ready_to_ship'
    order.save()
    
    return order_id

# API에서 워크플로우 실행
@api.post("/orders/{order_id}/process")
def process_order(request, order_id: int):
    """주문 처리 워크플로우 시작"""
    
    # 순차 실행 체인
    workflow = chain(
        validate_order.s(order_id),
        process_payment.s(),
        update_inventory.s(),
        group(
            send_confirmation_email.s(),
            notify_warehouse.s()
        )
    )
    
    result = workflow.apply_async()
    
    return {
        "order_id": order_id,
        "workflow_id": result.id,
        "status": "processing"
    }
```

### 예시 3: 데이터 파이프라인

```python
# tasks/tasks.py

@shared_task
def fetch_external_data(source_url):
    """외부 API에서 데이터 가져오기"""
    import requests
    response = requests.get(source_url)
    return response.json()

@shared_task
def transform_data(raw_data):
    """데이터 변환"""
    transformed = []
    for item in raw_data:
        transformed.append({
            'id': item['id'],
            'name': item['name'].upper(),
            'value': float(item['value'])
        })
    return transformed

@shared_task
def save_to_database(transformed_data):
    """데이터베이스에 저장"""
    from myapp.models import DataEntry
    
    entries = [
        DataEntry(**item)
        for item in transformed_data
    ]
    
    DataEntry.objects.bulk_create(entries, ignore_conflicts=True)
    
    return len(entries)

@shared_task
def generate_summary_report(count):
    """요약 리포트 생성"""
    from myapp.models import DataEntry
    from django.db.models import Avg, Sum
    
    stats = DataEntry.objects.aggregate(
        avg_value=Avg('value'),
        total_value=Sum('value')
    )
    
    return {
        'imported': count,
        'statistics': stats
    }

# Beat 스케줄로 매시간 실행
@shared_task
def hourly_data_pipeline():
    """시간마다 실행되는 데이터 파이프라인"""
    
    workflow = chain(
        fetch_external_data.s('https://api.example.com/data'),
        transform_data.s(),
        save_to_database.s(),
        generate_summary_report.s()
    )
    
    return workflow.apply_async()
```

## 🔍 문제 해결 (Troubleshooting)

### 문제 1: 작업이 실행되지 않음

**증상**: API에서 작업을 큐에 추가했지만 실행되지 않음

**해결책**:
```bash
# 1. Redis 연결 확인
redis-cli ping  # PONG이 나와야 함

# 2. Celery 워커가 실행 중인지 확인
ps aux | grep celery

# 3. 작업이 큐에 있는지 확인
celery -A myproject inspect active

# 4. 로그 확인
celery -A myproject worker --loglevel=debug
```

### 문제 2: 작업이 너무 느림

**해결책**:
```python
# 동시성 증가
# celery -A myproject worker --concurrency=10

# 또는 gevent 사용 (I/O 바운드 작업)
# pip install gevent
# celery -A myproject worker --pool=gevent --concurrency=100

# prefetch 설정 조정
app.conf.worker_prefetch_multiplier = 1  # 한 번에 1개만 가져옴
```

### 문제 3: 메모리 부족

**해결책**:
```python
# myproject/celery.py

# 작업 후 메모리 자동 정리
app.conf.worker_max_tasks_per_child = 100  # 100개 작업 후 워커 재시작

# 작업별 메모리 제한
@shared_task
def memory_intensive_task():
    import resource
    # 메모리 제한 (500MB)
    resource.setrlimit(
        resource.RLIMIT_AS,
        (500 * 1024 * 1024, 500 * 1024 * 1024)
    )
```

### 문제 4: Beat 스케줄이 실행되지 않음

**해결책**:
```bash
# 1. Beat가 실행 중인지 확인
ps aux | grep "celery beat"

# 2. Beat 스케줄 DB 초기화
rm celerybeat-schedule  # 파일 기반 스케줄러 사용 시
python manage.py migrate django_celery_beat  # DB 기반

# 3. 타임존 확인
# settings.py에서 CELERY_TIMEZONE 설정 확인
```

## 📚 추가 리소스

### 공식 문서
- [Django Ninja 문서](https://django-ninja.rest-framework.com/)
- [Celery 문서](https://docs.celeryproject.org/)
- [Django Celery Beat](https://django-celery-beat.readthedocs.io/)

### 모니터링 도구
- **Flower**: Celery 작업 모니터링 웹 UI
- **Sentry**: 에러 추적 및 알림
- **Prometheus + Grafana**: 성능 메트릭 수집

### 성능 최적화
```python
# settings.py

# Redis 최적화
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # 1시간
    'fanout_prefix': True,
    'fanout_patterns': True,
}

# 결과 저장 최적화
CELERY_RESULT_EXPIRES = 3600  # 1시간 후 결과 삭제
CELERY_RESULT_PERSISTENT = False  # 영구 저장 비활성화

# 직렬화 최적화
CELERY_TASK_SERIALIZER = 'msgpack'  # JSON보다 빠름
CELERY_RESULT_SERIALIZER = 'msgpack'
CELERY_ACCEPT_CONTENT = ['msgpack', 'json']
```

## 🎯 마무리

Django Ninja와 Celery, Celery Beat를 함께 사용하면 고성능 API와 효율적인 백그라운드 작업 처리를 구현할 수 있습니다. 이 가이드에서 다룬 내용:

### 핵심 요약
1. **Django Ninja**: FastAPI처럼 빠르고 간단한 API 개발
2. **Celery**: 백그라운드 작업 처리로 응답 속도 향상
3. **Celery Beat**: 주기적 작업 자동화
4. **Redis**: 빠르고 안정적인 메시지 브로커

### 실전 체크리스트
- ✅ Redis 설치 및 실행 확인
- ✅ Celery 설정 파일 작성
- ✅ Task 작성 및 테스트
- ✅ API 엔드포인트 연동
- ✅ Beat 스케줄 설정
- ✅ 모니터링 도구 (Flower) 설정
- ✅ 프로덕션 환경 구성 (Supervisor/Docker)
- ✅ 에러 핸들링 및 로깅

### 다음 단계
- **스케일링**: 워커 수 증가, 큐 분리
- **모니터링**: Sentry, Prometheus 연동
- **최적화**: 쿼리 최적화, 캐싱 전략
- **보안**: 작업 인증, 결과 암호화

이제 여러분의 Django 프로젝트에서 고성능 API와 효율적인 작업 처리 시스템을 구축할 준비가 되었습니다. 실전에서 발생하는 문제들을 해결하면서 더욱 견고한 시스템을 만들어가세요! 🚀
