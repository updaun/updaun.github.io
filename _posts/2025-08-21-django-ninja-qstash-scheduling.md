---
layout: post
title: "Django-Ninja와 QStash를 활용한 스케줄링 간편 구현"
date: 2025-08-21 10:00:00 +0900
categories: [Django, Scheduling, QStash]
tags: [django, ninja, qstash, scheduling, async, webhook, upstash]
excerpt: "Django-Ninja와 QStash를 활용하여 복잡한 스케줄링 시스템을 간단하게 구현하는 방법을 알아봅시다."
---

## 개요

웹 애플리케이션에서 스케줄링은 필수적인 기능입니다. 정기적인 데이터 백업, 이메일 발송, 리포트 생성 등 다양한 작업을 자동화해야 할 때가 있습니다. 전통적으로는 Celery와 Redis/RabbitMQ를 사용하거나 Cron 작업을 설정했지만, 이제 **QStash**와 **Django-Ninja**를 활용하면 더 간편하게 스케줄링을 구현할 수 있습니다.

## QStash란?

**QStash**는 Upstash에서 제공하는 서버리스 메시지 큐 및 스케줄링 서비스입니다. HTTP 기반으로 작동하며, 복잡한 인프라 설정 없이도 강력한 스케줄링 기능을 제공합니다.

### QStash의 주요 특징

- **서버리스**: 별도의 인프라 관리 불필요
- **HTTP 기반**: 웹훅을 통한 간단한 통합
- **스케줄링**: Cron 표현식 지원
- **재시도 메커니즘**: 실패 시 자동 재시도
- **DLQ(Dead Letter Queue)**: 최종 실패 처리
- **Pay-as-you-go**: 사용한 만큼만 비용 지불

## 프로젝트 설정

### 1. 패키지 설치

```bash
pip install django-ninja requests python-dotenv
```

### 2. Django-Ninja 설정

`urls.py`에 Django-Ninja API 설정:

```python
# myproject/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from .api import router

api = NinjaAPI(title="Scheduling API", version="1.0.0")
api.add_router("", router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

### 3. QStash 클라이언트 설정

```python
# utils/qstash.py
import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime
import json

class QStashClient:
    def __init__(self):
        self.token = os.getenv('QSTASH_TOKEN')
        self.base_url = "https://qstash.upstash.io/v2"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def schedule_message(
        self,
        url: str,
        payload: Dict[Any, Any],
        schedule: Optional[str] = None,  # Cron expression
        delay: Optional[int] = None,     # Seconds to delay
        retries: int = 3
    ) -> Dict[str, Any]:
        """스케줄된 메시지 전송"""
        
        endpoint = f"{self.base_url}/publish/{url}"
        
        # 스케줄 또는 딜레이 설정
        if schedule:
            self.headers["Upstash-Cron"] = schedule
        elif delay:
            self.headers["Upstash-Delay"] = f"{delay}s"
        
        # 재시도 설정
        self.headers["Upstash-Retries"] = str(retries)
        
        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload
        )
        
        # 헤더 정리
        self.headers.pop("Upstash-Cron", None)
        self.headers.pop("Upstash-Delay", None)
        self.headers.pop("Upstash-Retries", None)
        
        return response.json()
    
    def cancel_message(self, message_id: str) -> bool:
        """예약된 메시지 취소"""
        endpoint = f"{self.base_url}/messages/{message_id}"
        
        response = requests.delete(endpoint, headers=self.headers)
        return response.status_code == 200
    
    def get_messages(self) -> Dict[str, Any]:
        """대기 중인 메시지 목록 조회"""
        endpoint = f"{self.base_url}/messages"
        
        response = requests.get(endpoint, headers=self.headers)
        return response.json()

# 싱글톤 인스턴스
qstash = QStashClient()
```

## Django 모델 설정

스케줄된 작업을 추적하기 위한 모델을 생성합니다:

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

class ScheduledJob(models.Model):
    TASK_TYPES = [
        ('email', 'Email Notification'),
        ('report', 'Report Generation'),
        ('backup', 'Data Backup'),
        ('cleanup', 'Data Cleanup'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # QStash 메시지 ID
    qstash_message_id = models.CharField(max_length=255, blank=True, null=True)
    
    # 스케줄 정보
    schedule_expression = models.CharField(max_length=100, blank=True, null=True)  # Cron expression
    scheduled_at = models.DateTimeField(blank=True, null=True)
    
    # 작업 데이터
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # 메타데이터
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.task_type} - {self.status}"
```

## API 엔드포인트 구현

### 1. 스케줄링 API

```python
# api/scheduling.py
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from typing import Optional, List
from datetime import datetime, timedelta
import json
import logging

from ..models import ScheduledJob
from ..utils.qstash import qstash

logger = logging.getLogger(__name__)

router = Router(tags=["Scheduling"])

# 스키마 정의
class ScheduleJobRequest(Schema):
    task_type: str
    payload: dict
    schedule_expression: Optional[str] = None  # "0 9 * * 1"  (매주 월요일 9시)
    delay_minutes: Optional[int] = None
    retries: int = 3

class JobResponse(Schema):
    id: str
    task_type: str
    status: str
    qstash_message_id: Optional[str]
    schedule_expression: Optional[str]
    scheduled_at: Optional[datetime]
    created_at: datetime

@router.post("/schedule", response=JobResponse)
def schedule_job(request: HttpRequest, job_request: ScheduleJobRequest):
    """작업 스케줄링"""
    
    # 작업 생성
    job = ScheduledJob.objects.create(
        task_type=job_request.task_type,
        payload=job_request.payload,
        schedule_expression=job_request.schedule_expression,
        created_by=request.user if request.user.is_authenticated else None
    )
    
    # 스케줄 시간 계산
    if job_request.delay_minutes:
        job.scheduled_at = datetime.now() + timedelta(minutes=job_request.delay_minutes)
        job.save()
    
    try:
        # QStash에 메시지 스케줄
        webhook_url = f"{request.build_absolute_uri('/api/webhook/execute')}"
        
        qstash_response = qstash.schedule_message(
            url=webhook_url,
            payload={
                "job_id": str(job.id),
                "task_type": job.task_type,
                "payload": job.payload
            },
            schedule=job_request.schedule_expression,
            delay=job_request.delay_minutes * 60 if job_request.delay_minutes else None,
            retries=job_request.retries
        )
        
        # QStash 메시지 ID 저장
        job.qstash_message_id = qstash_response.get('messageId')
        job.save()
        
        logger.info(f"Job {job.id} scheduled successfully")
        
        return JobResponse(
            id=str(job.id),
            task_type=job.task_type,
            status=job.status,
            qstash_message_id=job.qstash_message_id,
            schedule_expression=job.schedule_expression,
            scheduled_at=job.scheduled_at,
            created_at=job.created_at
        )
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()
        logger.error(f"Failed to schedule job {job.id}: {str(e)}")
        raise

@router.get("/jobs", response=List[JobResponse])
def list_jobs(request: HttpRequest):
    """예약된 작업 목록 조회"""
    jobs = ScheduledJob.objects.all().order_by('-created_at')
    
    return [
        JobResponse(
            id=str(job.id),
            task_type=job.task_type,
            status=job.status,
            qstash_message_id=job.qstash_message_id,
            schedule_expression=job.schedule_expression,
            scheduled_at=job.scheduled_at,
            created_at=job.created_at
        )
        for job in jobs
    ]

@router.delete("/jobs/{job_id}")
def cancel_job(request: HttpRequest, job_id: str):
    """작업 취소"""
    job = get_object_or_404(ScheduledJob, id=job_id)
    
    if job.status == 'completed':
        return {"error": "Cannot cancel completed job"}
    
    try:
        # QStash에서 메시지 취소
        if job.qstash_message_id:
            success = qstash.cancel_message(job.qstash_message_id)
            if not success:
                logger.warning(f"Failed to cancel QStash message {job.qstash_message_id}")
        
        job.status = 'cancelled'
        job.save()
        
        return {"message": "Job cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        return {"error": str(e)}
```

### 2. 웹훅 엔드포인트

```python
# api/webhook.py
from ninja import Router
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json
import logging

from ..models import ScheduledJob
from ..services.task_executor import TaskExecutor

logger = logging.getLogger(__name__)

router = Router(tags=["Webhook"])

@router.post("/execute")
@csrf_exempt
def execute_job(request: HttpRequest):
    """QStash 웹훅으로 호출되는 작업 실행 엔드포인트"""
    
    try:
        # QStash에서 전송된 데이터 파싱
        payload = json.loads(request.body.decode('utf-8'))
        job_id = payload.get('job_id')
        task_type = payload.get('task_type')
        task_payload = payload.get('payload', {})
        
        # 작업 조회
        job = get_object_or_404(ScheduledJob, id=job_id)
        
        # 이미 완료된 작업인지 확인
        if job.status == 'completed':
            return JsonResponse({
                "status": "success",
                "message": "Job already completed"
            })
        
        # 작업 실행
        executor = TaskExecutor()
        result = executor.execute(task_type, task_payload)
        
        # 결과 저장
        job.status = 'completed'
        job.result = result
        job.save()
        
        logger.info(f"Job {job_id} executed successfully")
        
        return JsonResponse({
            "status": "success",
            "job_id": job_id,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")
        
        # 실패 상태 저장
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
        
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
```

## 작업 실행기 구현

다양한 작업 유형을 처리하는 TaskExecutor 클래스를 구현합니다:

```python
# services/task_executor.py
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TaskExecutor:
    """스케줄된 작업을 실행하는 클래스"""
    
    def execute(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """작업 유형에 따라 적절한 핸들러 호출"""
        
        handlers = {
            'email': self._handle_email,
            'report': self._handle_report,
            'backup': self._handle_backup,
            'cleanup': self._handle_cleanup,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return handler(payload)
    
    def _handle_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """이메일 발송 처리"""
        try:
            recipient = payload.get('recipient')
            subject = payload.get('subject')
            message = payload.get('message')
            
            if not all([recipient, subject, message]):
                raise ValueError("Missing required email fields")
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False
            )
            
            return {
                "status": "success",
                "message": f"Email sent to {recipient}",
                "timestamp": str(datetime.now())
            }
            
        except Exception as e:
            logger.error(f"Email task failed: {str(e)}")
            raise
    
    def _handle_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """리포트 생성 처리"""
        try:
            report_type = payload.get('report_type')
            
            # 리포트 생성 로직 구현
            # 예: 사용자 통계, 매출 리포트 등
            
            if report_type == 'user_stats':
                user_count = User.objects.count()
                return {
                    "status": "success",
                    "report_type": report_type,
                    "data": {"total_users": user_count},
                    "timestamp": str(datetime.now())
                }
            
            return {
                "status": "success",
                "message": f"Report {report_type} generated"
            }
            
        except Exception as e:
            logger.error(f"Report task failed: {str(e)}")
            raise
    
    def _handle_backup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 백업 처리"""
        try:
            backup_type = payload.get('backup_type', 'database')
            
            # 백업 로직 구현
            # 예: 데이터베이스 백업, 파일 백업 등
            
            return {
                "status": "success",
                "backup_type": backup_type,
                "message": "Backup completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Backup task failed: {str(e)}")
            raise
    
    def _handle_cleanup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 정리 처리"""
        try:
            cleanup_type = payload.get('cleanup_type')
            
            # 정리 로직 구현
            # 예: 임시 파일 삭제, 오래된 로그 삭제 등
            
            return {
                "status": "success",
                "cleanup_type": cleanup_type,
                "message": "Cleanup completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {str(e)}")
            raise
```

## 사용 예제

### 1. 이메일 스케줄링

```python
# 1시간 후 이메일 발송
POST /api/schedule
{
    "task_type": "email",
    "payload": {
        "recipient": "user@example.com",
        "subject": "Scheduled Email",
        "message": "This is a scheduled email."
    },
    "delay_minutes": 60
}

# 매주 월요일 오전 9시 리포트 이메일 발송
POST /api/schedule
{
    "task_type": "email",
    "payload": {
        "recipient": "admin@example.com",
        "subject": "Weekly Report",
        "message": "Weekly report is ready."
    },
    "schedule_expression": "0 9 * * 1"
}
```

### 2. 정기 백업

```python
# 매일 새벽 2시 데이터베이스 백업
POST /api/schedule
{
    "task_type": "backup",
    "payload": {
        "backup_type": "database"
    },
    "schedule_expression": "0 2 * * *"
}
```

### 3. 주기적 정리 작업

```python
# 매월 첫째 날 오전 3시 로그 정리
POST /api/schedule
{
    "task_type": "cleanup",
    "payload": {
        "cleanup_type": "logs"
    },
    "schedule_expression": "0 3 1 * *"
}
```

## 환경 변수 설정

`.env` 파일에 필요한 설정을 추가합니다:

```bash
# QStash 설정
QSTASH_TOKEN=your_qstash_token_here
QSTASH_CURRENT_SIGNING_KEY=your_signing_key
QSTASH_NEXT_SIGNING_KEY=your_next_signing_key

# 이메일 설정 (선택사항)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

## 보안 고려사항

### 1. 웹훅 서명 검증

QStash는 웹훅 요청에 서명을 포함합니다. 이를 검증하여 보안을 강화할 수 있습니다:

```python
import hmac
import hashlib
import base64

def verify_qstash_signature(request: HttpRequest) -> bool:
    """QStash 서명 검증"""
    signature = request.headers.get('Upstash-Signature')
    if not signature:
        return False
    
    current_signing_key = os.getenv('QSTASH_CURRENT_SIGNING_KEY')
    next_signing_key = os.getenv('QSTASH_NEXT_SIGNING_KEY')
    
    body = request.body.decode('utf-8')
    
    # 현재 키로 검증
    expected_signature = base64.b64encode(
        hmac.new(
            current_signing_key.encode(),
            body.encode(),
            hashlib.sha256
        ).digest()
    ).decode()
    
    if hmac.compare_digest(signature, expected_signature):
        return True
    
    # 다음 키로 검증 (키 로테이션 대비)
    if next_signing_key:
        expected_signature = base64.b64encode(
            hmac.new(
                next_signing_key.encode(),
                body.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        return hmac.compare_digest(signature, expected_signature)
    
    return False
```

### 2. 인증 및 권한 확인

```python
from django.contrib.auth.decorators import login_required
from ninja.security import django_auth

@router.post("/schedule", auth=django_auth)
def schedule_job(request: HttpRequest, job_request: ScheduleJobRequest):
    # 인증된 사용자만 스케줄링 가능
    pass
```

## 모니터링 및 로깅

### 1. 작업 모니터링 대시보드

```python
@router.get("/dashboard")
def get_dashboard_stats(request: HttpRequest):
    """스케줄링 대시보드 통계"""
    
    stats = {
        "total_jobs": ScheduledJob.objects.count(),
        "pending_jobs": ScheduledJob.objects.filter(status='pending').count(),
        "completed_jobs": ScheduledJob.objects.filter(status='completed').count(),
        "failed_jobs": ScheduledJob.objects.filter(status='failed').count(),
        "recent_jobs": list(
            ScheduledJob.objects.order_by('-created_at')[:10]
            .values('id', 'task_type', 'status', 'created_at')
        )
    }
    
    return stats
```

### 2. 로깅 설정

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/scheduling.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'scheduling': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 장점과 한계

### 장점

1. **간편한 설정**: 복잡한 인프라 설정 불필요
2. **서버리스**: 관리 오버헤드 최소화
3. **확장성**: 자동으로 확장되는 인프라
4. **신뢰성**: 내장된 재시도 및 DLQ 기능
5. **비용 효율**: 사용한 만큼만 비용 지불

### 한계

1. **네트워크 의존성**: 인터넷 연결 필수
2. **지연시간**: 로컬 큐보다 약간의 지연 가능
3. **비용**: 대용량 처리 시 비용 고려 필요
4. **제한사항**: QStash 서비스 제약사항 준수 필요

## 결론

Django-Ninja와 QStash를 활용하면 복잡한 스케줄링 시스템을 매우 간단하게 구현할 수 있습니다. 특히 중소규모 프로젝트에서는 Celery + Redis보다 훨씬 간편하고 효율적인 솔루션이 될 수 있습니다.

서버리스 아키텍처의 장점을 활용하여 인프라 관리 부담을 줄이고, 비즈니스 로직 구현에 더 집중할 수 있습니다. QStash의 강력한 스케줄링 기능과 Django-Ninja의 편리한 API 개발 경험을 통해 더 나은 개발자 경험을 얻을 수 있을 것입니다.

---

*이 포스트가 도움이 되셨다면 GitHub에서 ⭐️를 눌러주세요!*
