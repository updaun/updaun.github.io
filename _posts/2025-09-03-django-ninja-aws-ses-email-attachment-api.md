---
layout: post
title: "Django Ninja + AWS SES로 첨부파일 포함 이메일 API 구축하기"
date: 2025-09-03 10:00:00 +0900
categories: [Django, AWS, API, Email]
tags: [Django, Django-Ninja, AWS, SES, Email, API, FastAPI-style, Attachment, Backend]
---

Django Ninja와 AWS SES를 조합하면 강력하고 확장 가능한 이메일 발송 시스템을 구축할 수 있습니다. 특히 첨부파일 처리까지 포함한 완전한 이메일 API를 만들어보겠습니다.

## 🎯 프로젝트 개요

### 구현할 기능
- **파일 업로드** 및 첨부파일 처리
- **HTML/텍스트** 이메일 발송
- **다중 수신자** 지원
- **AWS SES** 통합
- **Django Ninja** 기반 FastAPI 스타일 API

### 기술 스택
- Django 4.2+
- Django Ninja 1.0+
- AWS SES (Simple Email Service)
- Boto3 (AWS SDK)

## 🛠️ 환경 설정

### 1. 패키지 설치

```bash
pip install django django-ninja boto3 python-multipart
```

### 2. AWS 설정

**settings.py**
```python
import os
from django.core.exceptions import ImproperlyConfigured

# AWS SES 설정
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION = os.getenv('AWS_SES_REGION', 'us-east-1')
AWS_SES_FROM_EMAIL = os.getenv('AWS_SES_FROM_EMAIL')

# 환경변수 확인
if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SES_FROM_EMAIL]):
    raise ImproperlyConfigured("AWS SES 환경변수가 설정되지 않았습니다.")

# 파일 업로드 설정
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
```

### 3. 프로젝트 구조

```
email_service/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── api.py
└── exceptions.py
```

## 📝 모델 정의

**models.py**
```python
from django.db import models
from django.contrib.auth.models import User
import uuid

class EmailLog(models.Model):
    """이메일 발송 로그"""
    
    STATUS_CHOICES = [
        ('pending', '발송 대기'),
        ('sent', '발송 완료'),
        ('failed', '발송 실패'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    recipients = models.JSONField()  # 수신자 리스트
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message_id = models.CharField(max_length=200, blank=True)  # AWS SES 메시지 ID
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

class EmailAttachment(models.Model):
    """이메일 첨부파일"""
    
    email_log = models.ForeignKey(EmailLog, related_name='attachments', on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()  # bytes
    created_at = models.DateTimeField(auto_now_add=True)
```

## 🏗️ 스키마 정의

**schemas.py**
```python
from ninja import Schema, File
from ninja.files import UploadedFile
from typing import List, Optional
from pydantic import EmailStr, validator

class EmailRecipient(Schema):
    """이메일 수신자"""
    email: EmailStr
    name: Optional[str] = None

class EmailRequest(Schema):
    """이메일 발송 요청"""
    recipients: List[EmailRecipient]
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    
    @validator('recipients')
    def recipients_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('최소 1명의 수신자가 필요합니다.')
        if len(v) > 50:
            raise ValueError('수신자는 최대 50명까지 가능합니다.')
        return v
    
    @validator('html_content', 'text_content')
    def content_required(cls, v, values):
        if not v and not values.get('html_content') and not values.get('text_content'):
            raise ValueError('HTML 또는 텍스트 내용 중 하나는 필수입니다.')
        return v

class EmailResponse(Schema):
    """이메일 발송 응답"""
    email_id: str
    status: str
    message: str
    message_id: Optional[str] = None

class EmailStatusResponse(Schema):
    """이메일 상태 응답"""
    email_id: str
    status: str
    recipients: List[str]
    subject: str
    created_at: str
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    attachments: List[dict] = []
```

## 🔧 서비스 로직

**services.py**
```python
import boto3
import logging
from typing import List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.exceptions import ClientError, BotoCoreError
from ninja.files import UploadedFile

from .models import EmailLog, EmailAttachment
from .schemas import EmailRecipient, EmailRequest
from .exceptions import EmailServiceError

logger = logging.getLogger(__name__)

class AWSEmailService:
    """AWS SES를 사용한 이메일 서비스"""
    
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            region_name=settings.AWS_SES_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
    
    def validate_attachments(self, files: List[UploadedFile]) -> None:
        """첨부파일 유효성 검사"""
        if not files:
            return
            
        total_size = sum(file.size for file in files)
        max_total_size = 25 * 1024 * 1024  # 25MB (SES 제한)
        
        if total_size > max_total_size:
            raise EmailServiceError(f"첨부파일 총 크기가 25MB를 초과합니다. ({total_size / 1024 / 1024:.1f}MB)")
        
        allowed_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.csv', '.zip', '.rar', '.jpg', '.jpeg', '.png', '.gif'
        }
        
        for file in files:
            if file.size > 10 * 1024 * 1024:  # 10MB per file
                raise EmailServiceError(f"파일 '{file.name}'이 10MB를 초과합니다.")
            
            ext = '.' + file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise EmailServiceError(f"지원하지 않는 파일 형식입니다: {ext}")
    
    def create_message(
        self, 
        recipients: List[EmailRecipient], 
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        attachments: Optional[List[UploadedFile]] = None
    ) -> MIMEMultipart:
        """MIME 메시지 생성"""
        
        msg = MIMEMultipart('mixed')
        msg['From'] = settings.AWS_SES_FROM_EMAIL
        msg['To'] = ', '.join([r.email for r in recipients])
        msg['Subject'] = subject
        
        # 메시지 본문
        msg_body = MIMEMultipart('alternative')
        
        if text_content:
            msg_body.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        if html_content:
            msg_body.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        msg.attach(msg_body)
        
        # 첨부파일 추가
        if attachments:
            for file in attachments:
                file_content = file.read()
                attachment = MIMEApplication(file_content)
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=file.name
                )
                msg.attach(attachment)
                
                # 파일 포인터 리셋 (로깅용)
                file.seek(0)
        
        return msg
    
    def send_email(
        self,
        email_request: EmailRequest,
        attachments: Optional[List[UploadedFile]] = None,
        sender_id: Optional[int] = None
    ) -> Tuple[EmailLog, Optional[str]]:
        """이메일 발송"""
        
        # 첨부파일 검증
        if attachments:
            self.validate_attachments(attachments)
        
        # 이메일 로그 생성
        email_log = EmailLog.objects.create(
            sender_id=sender_id,
            recipients=[r.dict() for r in email_request.recipients],
            subject=email_request.subject,
            status='pending'
        )
        
        try:
            # MIME 메시지 생성
            message = self.create_message(
                email_request.recipients,
                email_request.subject,
                email_request.html_content,
                email_request.text_content,
                attachments
            )
            
            # AWS SES로 발송
            response = self.ses_client.send_raw_email(
                Source=settings.AWS_SES_FROM_EMAIL,
                Destinations=[r.email for r in email_request.recipients],
                RawMessage={'Data': message.as_string()}
            )
            
            # 발송 성공 처리
            message_id = response['MessageId']
            email_log.status = 'sent'
            email_log.message_id = message_id
            email_log.sent_at = timezone.now()
            email_log.save()
            
            # 첨부파일 로그 저장
            if attachments:
                for file in attachments:
                    EmailAttachment.objects.create(
                        email_log=email_log,
                        filename=file.name,
                        content_type=file.content_type or 'application/octet-stream',
                        size=file.size
                    )
            
            logger.info(f"이메일 발송 성공: {email_log.id} (MessageId: {message_id})")
            return email_log, message_id
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"AWS SES 오류: {str(e)}"
            email_log.status = 'failed'
            email_log.error_message = error_msg
            email_log.save()
            
            logger.error(f"이메일 발송 실패: {email_log.id} - {error_msg}")
            raise EmailServiceError(error_msg)
        
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            email_log.status = 'failed'
            email_log.error_message = error_msg
            email_log.save()
            
            logger.error(f"이메일 발송 실패: {email_log.id} - {error_msg}")
            raise EmailServiceError(error_msg)
```

## 🔒 예외 처리

**exceptions.py**
```python
class EmailServiceError(Exception):
    """이메일 서비스 관련 예외"""
    pass

class AttachmentError(EmailServiceError):
    """첨부파일 관련 예외"""
    pass

class RecipientError(EmailServiceError):
    """수신자 관련 예외"""
    pass
```

## 🚀 API 엔드포인트

**api.py**
```python
from ninja import NinjaAPI, File
from ninja.files import UploadedFile
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from .schemas import EmailRequest, EmailResponse, EmailStatusResponse
from .services import AWSEmailService
from .models import EmailLog
from .exceptions import EmailServiceError

api = NinjaAPI(title="Email Service API", version="1.0.0")

email_service = AWSEmailService()

@api.post("/send", response=EmailResponse, tags=["Email"])
def send_email(
    request,
    email_data: EmailRequest,
    attachments: Optional[List[UploadedFile]] = File(None, description="첨부파일 (최대 25MB)")
):
    """
    첨부파일 포함 이메일 발송
    
    **주요 기능:**
    - HTML/텍스트 이메일 발송
    - 다중 수신자 지원
    - 첨부파일 지원 (최대 25MB)
    - AWS SES 통합
    
    **제한사항:**
    - 수신자 최대 50명
    - 첨부파일 총 크기 25MB
    - 개별 파일 최대 10MB
    """
    try:
        sender_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        
        email_log, message_id = email_service.send_email(
            email_data,
            attachments,
            sender_id
        )
        
        return EmailResponse(
            email_id=str(email_log.id),
            status="sent",
            message="이메일이 성공적으로 발송되었습니다.",
            message_id=message_id
        )
        
    except EmailServiceError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {"error": "서버 내부 오류가 발생했습니다."},
            status=500
        )

@api.get("/status/{email_id}", response=EmailStatusResponse, tags=["Email"])
def get_email_status(request, email_id: str):
    """
    이메일 발송 상태 조회
    """
    try:
        email_log = get_object_or_404(EmailLog, id=email_id)
        
        return EmailStatusResponse(
            email_id=str(email_log.id),
            status=email_log.status,
            recipients=[r['email'] for r in email_log.recipients],
            subject=email_log.subject,
            created_at=email_log.created_at.isoformat(),
            sent_at=email_log.sent_at.isoformat() if email_log.sent_at else None,
            error_message=email_log.error_message,
            attachments=[
                {
                    'filename': att.filename,
                    'content_type': att.content_type,
                    'size': att.size
                }
                for att in email_log.attachments.all()
            ]
        )
        
    except Exception as e:
        return JsonResponse(
            {"error": "이메일 정보를 찾을 수 없습니다."},
            status=404
        )

@api.get("/history", tags=["Email"])
def get_email_history(request, page: int = 1, size: int = 20):
    """
    이메일 발송 이력 조회
    """
    try:
        start = (page - 1) * size
        end = start + size
        
        queryset = EmailLog.objects.all()
        
        # 사용자별 필터링 (인증된 사용자의 경우)
        if hasattr(request, 'user') and request.user.is_authenticated:
            if not request.user.is_staff:
                queryset = queryset.filter(sender=request.user)
        
        total = queryset.count()
        emails = queryset[start:end]
        
        return {
            "total": total,
            "page": page,
            "size": size,
            "data": [
                {
                    "email_id": str(email.id),
                    "subject": email.subject,
                    "status": email.status,
                    "recipients_count": len(email.recipients),
                    "created_at": email.created_at.isoformat(),
                    "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                }
                for email in emails
            ]
        }
        
    except Exception as e:
        return JsonResponse(
            {"error": "이력 조회 중 오류가 발생했습니다."},
            status=500
        )

# 헬스체크 엔드포인트
@api.get("/health", tags=["System"])
def health_check(request):
    """API 상태 확인"""
    return {"status": "ok", "service": "Email API"}
```

## 🔗 URL 연결

**urls.py**
```python
from django.contrib import admin
from django.urls import path
from email_service.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/email/', api.urls),
]
```

## 📋 사용 예시

### 1. 기본 이메일 발송

```javascript
// Frontend에서 사용 예시
const sendBasicEmail = async () => {
    const formData = new FormData();
    
    // 이메일 데이터
    const emailData = {
        recipients: [
            { email: "user@example.com", name: "홍길동" },
            { email: "admin@example.com", name: "관리자" }
        ],
        subject: "중요한 공지사항",
        html_content: "<h1>안녕하세요!</h1><p>중요한 내용입니다.</p>",
        text_content: "안녕하세요! 중요한 내용입니다."
    };
    
    formData.append('email_data', JSON.stringify(emailData));
    
    const response = await fetch('/api/email/send', {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    console.log('발송 결과:', result);
};
```

### 2. 첨부파일 포함 이메일

```javascript
const sendEmailWithAttachments = async () => {
    const formData = new FormData();
    
    // 이메일 데이터
    const emailData = {
        recipients: [{ email: "client@example.com", name: "고객" }],
        subject: "계약서 및 제안서",
        html_content: `
            <h2>안녕하세요, 고객님</h2>
            <p>요청하신 계약서와 제안서를 첨부파일로 보내드립니다.</p>
            <ul>
                <li>계약서.pdf</li>
                <li>제안서.docx</li>
            </ul>
            <p>검토 후 연락 부탁드립니다.</p>
        `
    };
    
    formData.append('email_data', JSON.stringify(emailData));
    
    // 첨부파일 추가
    const contractFile = document.getElementById('contract').files[0];
    const proposalFile = document.getElementById('proposal').files[0];
    
    if (contractFile) formData.append('attachments', contractFile);
    if (proposalFile) formData.append('attachments', proposalFile);
    
    const response = await fetch('/api/email/send', {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    console.log('발송 결과:', result);
};
```

### 3. Python 클라이언트 예시

```python
import requests
import json

def send_email_with_python():
    url = "http://localhost:8000/api/email/send"
    
    # 이메일 데이터
    email_data = {
        "recipients": [
            {"email": "test@example.com", "name": "테스터"}
        ],
        "subject": "Python에서 보낸 이메일",
        "html_content": "<h1>Hello from Python!</h1>",
        "text_content": "Hello from Python!"
    }
    
    files = []
    data = {"email_data": json.dumps(email_data)}
    
    # 첨부파일이 있다면
    # files = [("attachments", open("report.pdf", "rb"))]
    
    response = requests.post(url, data=data, files=files)
    
    if response.status_code == 200:
        result = response.json()
        print(f"발송 성공: {result['email_id']}")
    else:
        print(f"발송 실패: {response.text}")

# 상태 확인
def check_email_status(email_id):
    url = f"http://localhost:8000/api/email/status/{email_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        status = response.json()
        print(f"상태: {status['status']}")
        print(f"발송 시간: {status['sent_at']}")
    else:
        print("상태 조회 실패")
```

## 🔍 모니터링 및 관리

### Django Admin 설정

**admin.py**
```python
from django.contrib import admin
from .models import EmailLog, EmailAttachment

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'status', 'recipients_count', 'created_at', 'sent_at']
    list_filter = ['status', 'created_at']
    search_fields = ['subject', 'recipients']
    readonly_fields = ['id', 'created_at', 'sent_at']
    
    def recipients_count(self, obj):
        return len(obj.recipients) if obj.recipients else 0
    recipients_count.short_description = '수신자 수'

@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'content_type', 'size_mb', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['filename']
    
    def size_mb(self, obj):
        return f"{obj.size / 1024 / 1024:.2f} MB"
    size_mb.short_description = '파일 크기'
```

## 🚨 보안 고려사항

### 1. 파일 검증 강화

```python
# services.py에 추가
import magic

def validate_file_content(self, file: UploadedFile) -> None:
    """파일 내용 기반 검증"""
    file_content = file.read()
    file.seek(0)  # 포인터 리셋
    
    # MIME 타입 검증
    detected_type = magic.from_buffer(file_content, mime=True)
    allowed_types = {
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg', 'image/png', 'text/plain'
    }
    
    if detected_type not in allowed_types:
        raise AttachmentError(f"허용되지 않은 파일 타입: {detected_type}")
    
    # 악성 코드 패턴 검사 (기본적인 예시)
    malicious_patterns = [b'<script', b'javascript:', b'vbscript:']
    for pattern in malicious_patterns:
        if pattern in file_content.lower():
            raise AttachmentError("잠재적으로 위험한 파일입니다.")
```

### 2. 요청 제한

```python
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests

def rate_limit_check(request, key: str, limit: int = 10, window: int = 3600):
    """요청 제한 검사"""
    cache_key = f"rate_limit:{key}:{request.META.get('REMOTE_ADDR')}"
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= limit:
        return HttpResponseTooManyRequests("요청 한도를 초과했습니다.")
    
    cache.set(cache_key, requests_count + 1, window)
    return None
```

## 📊 성능 최적화

### 1. 비동기 처리 (Celery 활용)

```python
# tasks.py
from celery import shared_task
from .services import AWSEmailService

@shared_task
def send_email_async(email_data_dict, attachment_paths=None):
    """비동기 이메일 발송"""
    service = AWSEmailService()
    # ... 구현
```

### 2. 첨부파일 캐싱

```python
from django.core.files.storage import default_storage
from django.core.cache import cache

def cache_attachment(file: UploadedFile, cache_time: int = 3600) -> str:
    """첨부파일 임시 캐싱"""
    cache_key = f"attachment:{hash(file.name + str(file.size))}"
    
    if not cache.get(cache_key):
        # 파일을 임시 저장소에 저장
        temp_path = default_storage.save(f"temp/{file.name}", file)
        cache.set(cache_key, temp_path, cache_time)
        return temp_path
    
    return cache.get(cache_key)
```

## 🧪 테스트 코드

**tests.py**
```python
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
import json

class EmailAPITest(TestCase):
    
    def setUp(self):
        self.client = Client()
    
    def test_send_basic_email(self):
        """기본 이메일 발송 테스트"""
        email_data = {
            "recipients": [{"email": "test@example.com"}],
            "subject": "테스트 이메일",
            "text_content": "테스트 내용"
        }
        
        response = self.client.post(
            '/api/email/send',
            {'email_data': json.dumps(email_data)},
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'sent')
    
    def test_send_email_with_attachment(self):
        """첨부파일 포함 이메일 테스트"""
        # 테스트 파일 생성
        test_file = SimpleUploadedFile(
            "test.txt", 
            b"test content",
            content_type="text/plain"
        )
        
        email_data = {
            "recipients": [{"email": "test@example.com"}],
            "subject": "첨부파일 테스트",
            "text_content": "첨부파일이 있는 이메일"
        }
        
        response = self.client.post(
            '/api/email/send',
            {
                'email_data': json.dumps(email_data),
                'attachments': test_file
            },
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_attachment_size(self):
        """잘못된 첨부파일 크기 테스트"""
        # 11MB 파일 (제한 초과)
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (11 * 1024 * 1024),  # 11MB
            content_type="text/plain"
        )
        
        email_data = {
            "recipients": [{"email": "test@example.com"}],
            "subject": "큰 파일 테스트",
            "text_content": "큰 파일 테스트"
        }
        
        response = self.client.post(
            '/api/email/send',
            {
                'email_data': json.dumps(email_data),
                'attachments': large_file
            },
        )
        
        self.assertEqual(response.status_code, 400)
```

## 🎯 결론

Django Ninja와 AWS SES를 조합한 이메일 API는 다음과 같은 장점을 제공합니다:

### ✅ 주요 장점
- **FastAPI 스타일** API 개발 경험
- **강력한 첨부파일** 처리 기능
- **확장 가능한** 아키텍처
- **AWS SES** 통합으로 높은 전송률
- **자동 검증** 및 오류 처리

### 🔄 확장 가능성
- 이메일 템플릿 시스템
- 대량 메일 발송 기능
- 실시간 전송 상태 추적
- 메일 분석 및 통계

이 구현을 통해 안정적이고 확장 가능한 이메일 서비스를 구축할 수 있으며, 실제 프로덕션 환경에서도 충분히 활용 가능합니다.
