---
layout: post
title: "Django Ninja로 AWS SES 첨부파일 메일 발송 API 구현하기"
date: 2025-11-07 09:00:00 +0900
categories: [Django, AWS, Backend]
tags: [django-ninja, aws-ses, email, attachment, api, boto3, mime]
description: "Django Ninja와 AWS SES를 활용하여 첨부파일을 포함한 이메일 발송 API를 구현하는 완벽 가이드. 실무에서 바로 사용할 수 있는 코드와 함께 보안, 성능 최적화까지 다룹니다."
image: "/assets/img/posts/2025-11-07-django-ninja-aws-ses-email-attachment.webp"
---

## 1. 서론

### 1.1 왜 AWS SES를 사용하는가?

이메일 발송은 현대 웹 애플리케이션에서 필수적인 기능입니다. 회원가입 인증, 비밀번호 재설정, 알림, 마케팅 메일 등 다양한 용도로 사용되죠. 특히 첨부파일을 포함한 이메일 발송은 청구서, 리포트, 계약서 등을 전송할 때 자주 필요합니다.

AWS SES(Simple Email Service)는 다음과 같은 장점을 제공합니다:

- **비용 효율성**: 월 62,000건까지 무료, 이후 $0.10/1,000건
- **높은 전송률**: 초당 수백 건의 이메일 발송 가능
- **뛰어난 전달률**: AWS의 평판 관리 시스템으로 스팸 처리 최소화
- **확장성**: 트래픽 증가에 따라 자동으로 확장
- **모니터링**: CloudWatch를 통한 실시간 모니터링
- **유연성**: SMTP, API 두 가지 방식 모두 지원

### 1.2 Django Ninja의 장점

Django Ninja는 FastAPI에서 영감을 받아 만들어진 Django용 API 프레임워크로, 다음과 같은 특징을 가집니다:

- **빠른 성능**: Pydantic 기반의 빠른 데이터 검증
- **자동 문서화**: OpenAPI(Swagger) 자동 생성
- **타입 힌팅**: Python 3.6+ 타입 힌팅 완벽 지원
- **Django 통합**: Django ORM, 인증 시스템 등과 완벽한 통합
- **간결한 코드**: FastAPI 스타일의 직관적인 문법

### 1.3 이 글에서 다룰 내용

이 포스트에서는 다음 내용을 실습과 함께 다룹니다:

1. AWS SES 설정 및 인증
2. Django 프로젝트 구조 설계
3. 첨부파일 포함 이메일 발송 서비스 구현
4. Django Ninja API 엔드포인트 작성
5. 비동기 처리 및 성능 최적화
6. 에러 핸들링 및 재시도 로직
7. 테스트 코드 작성
8. 프로덕션 배포 가이드

완성된 API는 다음 기능을 제공합니다:

- 단일/다중 수신자에게 이메일 발송
- 다양한 형식의 첨부파일 지원 (PDF, 이미지, 문서 등)
- HTML/텍스트 이메일 모두 지원
- 템플릿 기반 이메일 작성
- 발송 상태 추적 및 로깅
- 재시도 로직 및 에러 핸들링

## 2. AWS SES 설정

### 2.1 AWS SES 개요

AWS SES는 두 가지 발송 방식을 제공합니다:

1. **SMTP 인터페이스**: 기존 이메일 클라이언트와 호환
2. **API 호출**: boto3를 통한 프로그래밍 방식 (이 글에서 사용)

SES는 두 가지 환경으로 구분됩니다:

- **Sandbox 환경**: 
  - 일일 200통 제한
  - 인증된 이메일 주소로만 발송 가능
  - 테스트 및 개발용
  
- **Production 환경**:
  - AWS 승인 후 사용 가능
  - 일일 50,000통 이상 발송 가능
  - 모든 이메일 주소로 발송 가능

### 2.2 AWS 계정 및 IAM 설정

먼저 AWS 계정이 필요합니다. 계정이 있다면 IAM 사용자를 생성하여 최소 권한 원칙을 적용합니다.

**1) IAM 사용자 생성**

AWS Console → IAM → Users → Add user

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail",
        "ses:SendTemplatedEmail",
        "ses:GetSendQuota",
        "ses:GetSendStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

이 정책은 SES 이메일 발송에 필요한 최소한의 권한만 부여합니다.

**2) Access Key 발급**

IAM 사용자 생성 후 Security credentials 탭에서 Access Key를 발급받습니다:

```
Access Key ID: AKIAIOSFODNN7EXAMPLE
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

⚠️ **보안 주의사항**: Access Key는 절대 코드에 하드코딩하지 마세요. 환경 변수나 AWS Secrets Manager를 사용하세요.

### 2.3 SES 이메일/도메인 인증

SES에서 이메일을 발송하려면 발신자 주소를 인증해야 합니다.

**방법 1: 개별 이메일 주소 인증**

AWS Console → Amazon SES → Verified identities → Create identity

1. Identity type: Email address 선택
2. 이메일 주소 입력 (예: noreply@example.com)
3. Create identity 클릭
4. 받은 인증 메일에서 링크 클릭

**방법 2: 도메인 인증 (권장)**

도메인 전체를 인증하면 해당 도메인의 모든 이메일 주소를 사용할 수 있습니다.

1. Identity type: Domain 선택
2. 도메인 입력 (예: example.com)
3. DNS 레코드 추가:

```dns
# Route53 또는 DNS 제공자에 추가할 레코드
Type: TXT
Name: _amazonses.example.com
Value: [AWS에서 제공하는 토큰]

# DKIM 레코드 (3개)
Type: CNAME
Name: [token1]._domainkey.example.com
Value: [token1].dkim.amazonses.com

Type: CNAME
Name: [token2]._domainkey.example.com
Value: [token2].dkim.amazonses.com

Type: CNAME
Name: [token3]._domainkey.example.com
Value: [token3].dkim.amazonses.com

# SPF 레코드 (선택사항, 권장)
Type: TXT
Name: example.com
Value: "v=spf1 include:amazonses.com ~all"

# DMARC 레코드 (선택사항, 권장)
Type: TXT
Name: _dmarc.example.com
Value: "v=DMARC1; p=quarantine; rua=mailto:admin@example.com"
```

DNS 전파는 최대 72시간이 걸릴 수 있지만 보통 몇 분 내에 완료됩니다.

### 2.4 Sandbox 해제 (프로덕션 사용 시)

프로덕션에서 사용하려면 AWS에 Sandbox 해제를 요청해야 합니다.

AWS Console → Amazon SES → Account dashboard → Request production access

요청 시 포함할 내용:
- 이메일 발송 목적
- 수신자가 구독을 해제하는 방법
- 바운스 및 컴플레인 처리 방법
- 예상 발송량

승인은 보통 24시간 내에 완료됩니다.

### 2.5 리전 선택

SES는 일부 리전에서만 사용 가능합니다:

- **미국**: us-east-1 (버지니아), us-west-2 (오레곤)
- **유럽**: eu-west-1 (아일랜드), eu-central-1 (프랑크푸르트)
- **아시아**: ap-south-1 (뭄바이), ap-southeast-1 (싱가포르), ap-southeast-2 (시드니), ap-northeast-1 (도쿄)

한국에서 사용 시 **ap-northeast-1 (도쿄)** 리전을 권장합니다.

## 3. Django 프로젝트 설정

### 3.1 프로젝트 구조

완성될 프로젝트 구조는 다음과 같습니다:

```
email_service/
├── manage.py
├── requirements.txt
├── .env
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── apps/
│   └── emails/
│       ├── __init__.py
│       ├── models.py
│       ├── schemas.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── ses_client.py
│       │   └── email_service.py
│       ├── api.py
│       ├── tasks.py
│       └── tests/
│           ├── __init__.py
│           ├── test_services.py
│           └── test_api.py
└── templates/
    └── emails/
        ├── base.html
        └── notification.html
```

### 3.2 환경 설정

**1) 가상환경 생성 및 패키지 설치**

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Django 프로젝트 생성
pip install django
django-admin startproject config .
python manage.py startapp apps/emails

# 필요한 패키지 설치
pip install django-ninja boto3 python-dotenv celery redis pydantic pillow
```

**2) requirements.txt**

```txt
Django==5.0.0
django-ninja==1.1.0
boto3==1.34.0
python-dotenv==1.0.0
celery==5.3.4
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
Pillow==10.1.0
python-magic==0.4.27

# Development
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
moto==4.2.9  # AWS 서비스 mocking
faker==21.0.0
```

**3) .env 파일**

```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# AWS SES
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-northeast-1
AWS_SES_FROM_EMAIL=noreply@example.com

# Email 설정
EMAIL_MAX_ATTACHMENT_SIZE=10485760  # 10MB
EMAIL_ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,gif,doc,docx,xls,xlsx,txt

# Celery (비동기 작업용)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 로깅
LOG_LEVEL=INFO
```

⚠️ `.env` 파일은 `.gitignore`에 추가하세요!

**4) settings.py 수정**

```python
# config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'ninja',
    
    # Local apps
    'apps.emails',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# AWS SES 설정
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-1')
AWS_SES_FROM_EMAIL = os.getenv('AWS_SES_FROM_EMAIL')

# Email 설정
EMAIL_MAX_ATTACHMENT_SIZE = int(os.getenv('EMAIL_MAX_ATTACHMENT_SIZE', 10485760))
EMAIL_ALLOWED_EXTENSIONS = os.getenv('EMAIL_ALLOWED_EXTENSIONS', '').split(',')

# Celery 설정
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'email_service.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.emails': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# 보안 설정 (프로덕션)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
```

**5) Celery 설정**

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('email_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 3.3 Django Ninja 라우터 설정

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from apps.emails.api import router as email_router

api = NinjaAPI(
    title="Email Service API",
    version="1.0.0",
    description="AWS SES 기반 이메일 발송 서비스",
    docs_url="/docs",
)

api.add_router("/emails/", email_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

이제 기본 설정이 완료되었습니다. 다음 섹션에서는 핵심 이메일 서비스를 구현하겠습니다.

## 4. 이메일 서비스 구현

### 4.1 데이터 모델 정의

먼저 이메일 발송 이력을 저장할 모델을 정의합니다.

```python
# apps/emails/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid

class EmailLog(models.Model):
    """이메일 발송 로그"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        SENDING = 'sending', '발송중'
        SENT = 'sent', '발송완료'
        FAILED = 'failed', '실패'
        BOUNCED = 'bounced', '반송됨'
        COMPLAINED = 'complained', '스팸신고'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 발신자/수신자 정보
    from_email = models.EmailField(verbose_name="발신자")
    to_emails = models.JSONField(verbose_name="수신자 목록")
    cc_emails = models.JSONField(default=list, blank=True, verbose_name="참조")
    bcc_emails = models.JSONField(default=list, blank=True, verbose_name="숨은참조")
    
    # 이메일 내용
    subject = models.CharField(max_length=255, verbose_name="제목")
    body_text = models.TextField(blank=True, verbose_name="텍스트 본문")
    body_html = models.TextField(blank=True, verbose_name="HTML 본문")
    
    # 첨부파일
    attachments = models.JSONField(default=list, blank=True, verbose_name="첨부파일")
    
    # 발송 상태
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="상태"
    )
    message_id = models.CharField(max_length=255, blank=True, verbose_name="SES 메시지 ID")
    
    # 에러 정보
    error_message = models.TextField(blank=True, verbose_name="에러 메시지")
    retry_count = models.IntegerField(default=0, verbose_name="재시도 횟수")
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="발송일시")
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.status}"


class EmailTemplate(models.Model):
    """이메일 템플릿"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="템플릿명")
    subject = models.CharField(max_length=255, verbose_name="제목")
    body_html = models.TextField(verbose_name="HTML 본문")
    body_text = models.TextField(blank=True, verbose_name="텍스트 본문")
    
    # 템플릿 변수 설명 (JSON)
    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="템플릿에서 사용 가능한 변수들",
        verbose_name="변수"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    
    class Meta:
        db_table = 'email_templates'
        ordering = ['name']
    
    def __str__(self):
        return self.name
```

마이그레이션을 생성하고 적용합니다:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4.2 SES 클라이언트 래퍼

boto3를 사용하여 SES와 통신하는 클라이언트 클래스를 만듭니다.

```python
# apps/emails/services/ses_client.py
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from django.conf import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SESClientError(Exception):
    """SES 클라이언트 에러"""
    pass


class SESClient:
    """AWS SES 클라이언트 래퍼"""
    
    def __init__(self):
        """SES 클라이언트 초기화"""
        try:
            self.client = boto3.client(
                'ses',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            logger.info(f"SES 클라이언트 초기화 완료: {settings.AWS_REGION}")
        except Exception as e:
            logger.error(f"SES 클라이언트 초기화 실패: {str(e)}")
            raise SESClientError(f"SES 클라이언트 초기화 실패: {str(e)}")
    
    def send_raw_email(self, raw_message: bytes, source: str, destinations: list) -> Dict[str, Any]:
        """
        Raw 이메일 발송 (첨부파일 포함 가능)
        
        Args:
            raw_message: MIME 형식의 원본 메시지
            source: 발신자 이메일
            destinations: 수신자 이메일 리스트
            
        Returns:
            SES 응답 (MessageId 포함)
            
        Raises:
            SESClientError: 발송 실패 시
        """
        try:
            response = self.client.send_raw_email(
                Source=source,
                Destinations=destinations,
                RawMessage={'Data': raw_message}
            )
            
            logger.info(
                f"이메일 발송 성공: MessageId={response['MessageId']}, "
                f"Source={source}, Destinations={destinations}"
            )
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                f"SES ClientError: {error_code} - {error_message}, "
                f"Source={source}, Destinations={destinations}"
            )
            
            # 에러 코드별 처리
            if error_code == 'MessageRejected':
                raise SESClientError(f"메시지 거부됨: {error_message}")
            elif error_code == 'MailFromDomainNotVerified':
                raise SESClientError(f"발신자 도메인 미인증: {error_message}")
            elif error_code == 'ConfigurationSetDoesNotExist':
                raise SESClientError(f"설정 세트 없음: {error_message}")
            elif error_code == 'AccountSendingPausedException':
                raise SESClientError(f"계정 발송 일시중지: {error_message}")
            else:
                raise SESClientError(f"SES 에러 ({error_code}): {error_message}")
                
        except BotoCoreError as e:
            logger.error(f"BotoCore 에러: {str(e)}")
            raise SESClientError(f"AWS 연결 에러: {str(e)}")
            
        except Exception as e:
            logger.error(f"예상치 못한 에러: {str(e)}")
            raise SESClientError(f"이메일 발송 실패: {str(e)}")
    
    def get_send_quota(self) -> Dict[str, Any]:
        """
        SES 발송 쿼터 조회
        
        Returns:
            Max24HourSend: 24시간 최대 발송량
            MaxSendRate: 초당 최대 발송량
            SentLast24Hours: 최근 24시간 발송량
        """
        try:
            response = self.client.get_send_quota()
            logger.info(f"발송 쿼터 조회: {response}")
            return response
        except Exception as e:
            logger.error(f"쿼터 조회 실패: {str(e)}")
            raise SESClientError(f"쿼터 조회 실패: {str(e)}")
    
    def get_send_statistics(self) -> Dict[str, Any]:
        """
        SES 발송 통계 조회
        
        Returns:
            최근 2주간의 발송 통계
        """
        try:
            response = self.client.get_send_statistics()
            logger.info(f"발송 통계 조회 완료")
            return response
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            raise SESClientError(f"통계 조회 실패: {str(e)}")
    
    def verify_email_identity(self, email: str) -> Dict[str, Any]:
        """
        이메일 주소 인증 요청
        
        Args:
            email: 인증할 이메일 주소
            
        Returns:
            SES 응답
        """
        try:
            response = self.client.verify_email_identity(EmailAddress=email)
            logger.info(f"이메일 인증 요청: {email}")
            return response
        except Exception as e:
            logger.error(f"이메일 인증 요청 실패: {str(e)}")
            raise SESClientError(f"이메일 인증 요청 실패: {str(e)}")
```

### 4.3 MIME 메시지 생성 및 첨부파일 처리

이메일 본문과 첨부파일을 MIME 형식으로 구성하는 서비스를 만듭니다.

```python
# apps/emails/services/email_service.py
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.template.loader import render_to_string
import logging
import mimetypes
import os

from .ses_client import SESClient, SESClientError
from apps.emails.models import EmailLog

logger = logging.getLogger(__name__)


class EmailAttachment:
    """이메일 첨부파일 클래스"""
    
    def __init__(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ):
        self.filename = filename
        self.content = content
        self.content_type = content_type or self._guess_content_type()
    
    def _guess_content_type(self) -> str:
        """파일명으로부터 content type 추측"""
        content_type, _ = mimetypes.guess_type(self.filename)
        return content_type or 'application/octet-stream'
    
    def validate(self) -> Tuple[bool, str]:
        """첨부파일 유효성 검증"""
        # 파일 크기 검증
        if len(self.content) > settings.EMAIL_MAX_ATTACHMENT_SIZE:
            max_mb = settings.EMAIL_MAX_ATTACHMENT_SIZE / (1024 * 1024)
            return False, f"파일 크기가 {max_mb}MB를 초과합니다"
        
        # 확장자 검증
        ext = os.path.splitext(self.filename)[1].lower().lstrip('.')
        if ext not in settings.EMAIL_ALLOWED_EXTENSIONS:
            return False, f"허용되지 않는 파일 형식입니다: {ext}"
        
        return True, "OK"


class EmailService:
    """이메일 발송 서비스"""
    
    def __init__(self):
        self.ses_client = SESClient()
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        reply_to: Optional[List[str]] = None,
    ) -> EmailLog:
        """
        이메일 발송
        
        Args:
            to_emails: 수신자 리스트
            subject: 제목
            body_html: HTML 본문
            body_text: 텍스트 본문
            from_email: 발신자 (기본값: settings.AWS_SES_FROM_EMAIL)
            cc_emails: 참조
            bcc_emails: 숨은 참조
            attachments: 첨부파일 리스트
            reply_to: 회신 주소
            
        Returns:
            EmailLog 인스턴스
        """
        from_email = from_email or settings.AWS_SES_FROM_EMAIL
        cc_emails = cc_emails or []
        bcc_emails = bcc_emails or []
        attachments = attachments or []
        
        # EmailLog 생성
        email_log = EmailLog.objects.create(
            from_email=from_email,
            to_emails=to_emails,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            subject=subject,
            body_html=body_html or '',
            body_text=body_text or '',
            attachments=[
                {
                    'filename': att.filename,
                    'content_type': att.content_type,
                    'size': len(att.content)
                }
                for att in attachments
            ],
            status=EmailLog.Status.PENDING
        )
        
        try:
            # 첨부파일 유효성 검증
            for attachment in attachments:
                is_valid, error_msg = attachment.validate()
                if not is_valid:
                    raise ValueError(f"{attachment.filename}: {error_msg}")
            
            # MIME 메시지 생성
            mime_message = self._create_mime_message(
                from_email=from_email,
                to_emails=to_emails,
                cc_emails=cc_emails,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                attachments=attachments,
                reply_to=reply_to
            )
            
            # 모든 수신자 리스트
            all_destinations = to_emails + cc_emails + bcc_emails
            
            # 발송 상태 업데이트
            email_log.status = EmailLog.Status.SENDING
            email_log.save(update_fields=['status'])
            
            # SES로 발송
            response = self.ses_client.send_raw_email(
                raw_message=mime_message.as_bytes(),
                source=from_email,
                destinations=all_destinations
            )
            
            # 성공 처리
            email_log.status = EmailLog.Status.SENT
            email_log.message_id = response['MessageId']
            email_log.sent_at = timezone.now()
            email_log.save(update_fields=['status', 'message_id', 'sent_at'])
            
            logger.info(f"이메일 발송 성공: {email_log.id}")
            return email_log
            
        except (SESClientError, ValueError) as e:
            # 에러 처리
            email_log.status = EmailLog.Status.FAILED
            email_log.error_message = str(e)
            email_log.save(update_fields=['status', 'error_message'])
            
            logger.error(f"이메일 발송 실패: {email_log.id} - {str(e)}")
            raise
        
        except Exception as e:
            # 예상치 못한 에러
            email_log.status = EmailLog.Status.FAILED
            email_log.error_message = f"예상치 못한 에러: {str(e)}"
            email_log.save(update_fields=['status', 'error_message'])
            
            logger.exception(f"이메일 발송 중 예외 발생: {email_log.id}")
            raise
    
    def _create_mime_message(
        self,
        from_email: str,
        to_emails: List[str],
        cc_emails: List[str],
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str],
        attachments: List[EmailAttachment],
        reply_to: Optional[List[str]]
    ) -> MIMEMultipart:
        """MIME 메시지 생성"""
        
        # Mixed 타입 메시지 (첨부파일 포함 가능)
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        if reply_to:
            msg['Reply-To'] = ', '.join(reply_to)
        
        # Alternative 파트 생성 (HTML과 텍스트)
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # 텍스트 본문
        if body_text:
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg_alternative.attach(part_text)
        
        # HTML 본문
        if body_html:
            part_html = MIMEText(body_html, 'html', 'utf-8')
            msg_alternative.attach(part_html)
        
        # 첨부파일 추가
        for attachment in attachments:
            msg.attach(self._create_attachment_part(attachment))
        
        return msg
    
    def _create_attachment_part(self, attachment: EmailAttachment) -> MIMEBase:
        """첨부파일 MIME 파트 생성"""
        
        maintype, subtype = attachment.content_type.split('/', 1)
        
        if maintype == 'text':
            part = MIMEText(
                attachment.content.decode('utf-8'),
                _subtype=subtype
            )
        elif maintype == 'image':
            part = MIMEImage(attachment.content, _subtype=subtype)
        elif maintype == 'audio':
            part = MIMEAudio(attachment.content, _subtype=subtype)
        elif maintype == 'application':
            part = MIMEApplication(attachment.content, _subtype=subtype)
        else:
            part = MIMEBase(maintype, subtype)
            part.set_payload(attachment.content)
            encoders.encode_base64(part)
        
        part.add_header(
            'Content-Disposition',
            'attachment',
            filename=attachment.filename
        )
        
        return part
    
    def send_templated_email(
        self,
        to_emails: List[str],
        template_name: str,
        context: Dict,
        from_email: Optional[str] = None,
        attachments: Optional[List[EmailAttachment]] = None
    ) -> EmailLog:
        """
        템플릿 기반 이메일 발송
        
        Args:
            to_emails: 수신자 리스트
            template_name: 템플릿 이름
            context: 템플릿 컨텍스트
            from_email: 발신자
            attachments: 첨부파일
            
        Returns:
            EmailLog 인스턴스
        """
        # Django 템플릿 렌더링
        html_template = f'emails/{template_name}.html'
        text_template = f'emails/{template_name}.txt'
        
        try:
            body_html = render_to_string(html_template, context)
        except Exception:
            body_html = None
        
        try:
            body_text = render_to_string(text_template, context)
        except Exception:
            body_text = None
        
        # 제목은 컨텍스트에서 가져오기
        subject = context.get('subject', 'No Subject')
        
        return self.send_email(
            to_emails=to_emails,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=from_email,
            attachments=attachments
        )


# Django timezone import 추가
from django.utils import timezone
```

이제 핵심 서비스 로직이 완성되었습니다. 다음 섹션에서는 Django Ninja API를 구현하겠습니다.

## 5. Django Ninja API 구현

### 5.1 Pydantic 스키마 정의

API 요청/응답에 사용할 스키마를 정의합니다.

```python
# apps/emails/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class EmailStatus(str, Enum):
    """이메일 상태"""
    PENDING = 'pending'
    SENDING = 'sending'
    SENT = 'sent'
    FAILED = 'failed'
    BOUNCED = 'bounced'
    COMPLAINED = 'complained'


class AttachmentInfo(BaseModel):
    """첨부파일 정보"""
    filename: str
    content_type: str
    size: int


class SendEmailRequest(BaseModel):
    """이메일 발송 요청"""
    to_emails: List[EmailStr] = Field(..., min_items=1, max_items=50)
    subject: str = Field(..., min_length=1, max_length=255)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    cc_emails: Optional[List[EmailStr]] = Field(default=None, max_items=50)
    bcc_emails: Optional[List[EmailStr]] = Field(default=None, max_items=50)
    reply_to: Optional[List[EmailStr]] = Field(default=None, max_items=5)
    
    @validator('body_html', 'body_text')
    def validate_body(cls, v, values):
        """HTML 또는 텍스트 본문 중 하나는 필수"""
        if 'body_html' in values and not values['body_html'] and not v:
            raise ValueError('body_html 또는 body_text 중 하나는 필수입니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "to_emails": ["user@example.com"],
                "subject": "테스트 이메일",
                "body_html": "<h1>안녕하세요</h1><p>테스트 메일입니다.</p>",
                "body_text": "안녕하세요\n테스트 메일입니다.",
                "cc_emails": ["cc@example.com"],
                "reply_to": ["reply@example.com"]
            }
        }


class SendTemplatedEmailRequest(BaseModel):
    """템플릿 이메일 발송 요청"""
    to_emails: List[EmailStr] = Field(..., min_items=1, max_items=50)
    template_name: str = Field(..., min_length=1, max_length=100)
    context: dict = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "to_emails": ["user@example.com"],
                "template_name": "notification",
                "context": {
                    "subject": "알림",
                    "username": "홍길동",
                    "message": "새로운 알림이 있습니다."
                }
            }
        }


class EmailResponse(BaseModel):
    """이메일 발송 응답"""
    id: str
    status: EmailStatus
    message_id: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailLogResponse(BaseModel):
    """이메일 로그 상세 응답"""
    id: str
    from_email: str
    to_emails: List[str]
    cc_emails: List[str]
    bcc_emails: List[str]
    subject: str
    status: EmailStatus
    message_id: Optional[str] = None
    attachments: List[AttachmentInfo]
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SendQuotaResponse(BaseModel):
    """발송 쿼터 응답"""
    max_24_hour_send: float
    max_send_rate: float
    sent_last_24_hours: float


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
```

### 5.2 API 라우터 구현

```python
# apps/emails/api.py
from ninja import Router, File, UploadedFile
from ninja.errors import HttpError
from typing import List, Optional
from django.shortcuts import get_object_or_404
import logging

from .schemas import (
    SendEmailRequest,
    SendTemplatedEmailRequest,
    EmailResponse,
    EmailLogResponse,
    SendQuotaResponse,
    ErrorResponse
)
from .services.email_service import EmailService, EmailAttachment
from .services.ses_client import SESClientError
from .models import EmailLog

router = Router(tags=["emails"])
logger = logging.getLogger(__name__)


@router.post(
    "/send",
    response={200: EmailResponse, 400: ErrorResponse, 500: ErrorResponse},
    summary="이메일 발송",
    description="첨부파일 없이 이메일을 발송합니다."
)
def send_email(request, payload: SendEmailRequest):
    """
    이메일 발송 API
    
    - **to_emails**: 수신자 이메일 목록 (최대 50개)
    - **subject**: 이메일 제목
    - **body_html**: HTML 본문 (선택)
    - **body_text**: 텍스트 본문 (선택)
    - **cc_emails**: 참조 이메일 목록 (선택)
    - **bcc_emails**: 숨은 참조 이메일 목록 (선택)
    - **reply_to**: 회신 주소 (선택)
    
    HTML 또는 텍스트 본문 중 하나는 필수입니다.
    """
    try:
        email_service = EmailService()
        
        email_log = email_service.send_email(
            to_emails=payload.to_emails,
            subject=payload.subject,
            body_html=payload.body_html,
            body_text=payload.body_text,
            cc_emails=payload.cc_emails,
            bcc_emails=payload.bcc_emails,
            reply_to=payload.reply_to
        )
        
        return EmailResponse(
            id=str(email_log.id),
            status=email_log.status,
            message_id=email_log.message_id,
            created_at=email_log.created_at,
            sent_at=email_log.sent_at
        )
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except SESClientError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        logger.exception("이메일 발송 중 예외 발생")
        raise HttpError(500, "이메일 발송에 실패했습니다")


@router.post(
    "/send-with-attachments",
    response={200: EmailResponse, 400: ErrorResponse, 500: ErrorResponse},
    summary="첨부파일 포함 이메일 발송",
    description="첨부파일을 포함한 이메일을 발송합니다."
)
def send_email_with_attachments(
    request,
    to_emails: str,
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    cc_emails: Optional[str] = None,
    bcc_emails: Optional[str] = None,
    reply_to: Optional[str] = None,
    attachments: List[UploadedFile] = File(None)
):
    """
    첨부파일 포함 이메일 발송 API
    
    Form-data 형식으로 요청해야 합니다.
    
    - **to_emails**: 쉼표로 구분된 수신자 이메일
    - **subject**: 이메일 제목
    - **body_html**: HTML 본문 (선택)
    - **body_text**: 텍스트 본문 (선택)
    - **cc_emails**: 쉼표로 구분된 참조 이메일 (선택)
    - **bcc_emails**: 쉼표로 구분된 숨은 참조 이메일 (선택)
    - **reply_to**: 쉼표로 구분된 회신 주소 (선택)
    - **attachments**: 첨부파일 (복수 가능)
    """
    try:
        # 쉼표로 구분된 이메일 파싱
        to_list = [email.strip() for email in to_emails.split(',')]
        cc_list = [email.strip() for email in cc_emails.split(',')] if cc_emails else []
        bcc_list = [email.strip() for email in bcc_emails.split(',')] if bcc_emails else []
        reply_to_list = [email.strip() for email in reply_to.split(',')] if reply_to else []
        
        # 첨부파일 처리
        attachment_objects = []
        if attachments:
            for uploaded_file in attachments:
                content = uploaded_file.read()
                attachment = EmailAttachment(
                    filename=uploaded_file.name,
                    content=content,
                    content_type=uploaded_file.content_type
                )
                attachment_objects.append(attachment)
        
        # 이메일 발송
        email_service = EmailService()
        email_log = email_service.send_email(
            to_emails=to_list,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            cc_emails=cc_list if cc_list else None,
            bcc_emails=bcc_list if bcc_list else None,
            reply_to=reply_to_list if reply_to_list else None,
            attachments=attachment_objects
        )
        
        return EmailResponse(
            id=str(email_log.id),
            status=email_log.status,
            message_id=email_log.message_id,
            created_at=email_log.created_at,
            sent_at=email_log.sent_at
        )
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except SESClientError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        logger.exception("첨부파일 이메일 발송 중 예외 발생")
        raise HttpError(500, "이메일 발송에 실패했습니다")


@router.post(
    "/send-templated",
    response={200: EmailResponse, 400: ErrorResponse, 500: ErrorResponse},
    summary="템플릿 이메일 발송",
    description="미리 정의된 템플릿으로 이메일을 발송합니다."
)
def send_templated_email(request, payload: SendTemplatedEmailRequest):
    """
    템플릿 기반 이메일 발송 API
    
    - **to_emails**: 수신자 이메일 목록
    - **template_name**: 템플릿 이름
    - **context**: 템플릿 변수
    """
    try:
        email_service = EmailService()
        
        email_log = email_service.send_templated_email(
            to_emails=payload.to_emails,
            template_name=payload.template_name,
            context=payload.context
        )
        
        return EmailResponse(
            id=str(email_log.id),
            status=email_log.status,
            message_id=email_log.message_id,
            created_at=email_log.created_at,
            sent_at=email_log.sent_at
        )
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except SESClientError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        logger.exception("템플릿 이메일 발송 중 예외 발생")
        raise HttpError(500, "이메일 발송에 실패했습니다")


@router.get(
    "/logs/{email_id}",
    response={200: EmailLogResponse, 404: ErrorResponse},
    summary="이메일 로그 조회",
    description="특정 이메일의 상세 정보를 조회합니다."
)
def get_email_log(request, email_id: str):
    """
    이메일 로그 조회 API
    
    - **email_id**: 이메일 ID (UUID)
    """
    email_log = get_object_or_404(EmailLog, id=email_id)
    
    return EmailLogResponse(
        id=str(email_log.id),
        from_email=email_log.from_email,
        to_emails=email_log.to_emails,
        cc_emails=email_log.cc_emails,
        bcc_emails=email_log.bcc_emails,
        subject=email_log.subject,
        status=email_log.status,
        message_id=email_log.message_id,
        attachments=[AttachmentInfo(**att) for att in email_log.attachments],
        error_message=email_log.error_message,
        retry_count=email_log.retry_count,
        created_at=email_log.created_at,
        sent_at=email_log.sent_at
    )


@router.get(
    "/logs",
    response=List[EmailLogResponse],
    summary="이메일 로그 목록",
    description="이메일 발송 로그 목록을 조회합니다."
)
def list_email_logs(
    request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    이메일 로그 목록 조회 API
    
    - **status**: 상태 필터 (pending, sending, sent, failed 등)
    - **limit**: 조회할 개수 (기본 50, 최대 100)
    - **offset**: 시작 위치
    """
    queryset = EmailLog.objects.all()
    
    if status:
        queryset = queryset.filter(status=status)
    
    limit = min(limit, 100)
    email_logs = queryset[offset:offset + limit]
    
    return [
        EmailLogResponse(
            id=str(log.id),
            from_email=log.from_email,
            to_emails=log.to_emails,
            cc_emails=log.cc_emails,
            bcc_emails=log.bcc_emails,
            subject=log.subject,
            status=log.status,
            message_id=log.message_id,
            attachments=[AttachmentInfo(**att) for att in log.attachments],
            error_message=log.error_message,
            retry_count=log.retry_count,
            created_at=log.created_at,
            sent_at=log.sent_at
        )
        for log in email_logs
    ]


@router.get(
    "/quota",
    response={200: SendQuotaResponse, 500: ErrorResponse},
    summary="SES 발송 쿼터 조회",
    description="AWS SES 발송 쿼터 정보를 조회합니다."
)
def get_send_quota(request):
    """
    SES 발송 쿼터 조회 API
    
    24시간 최대 발송량, 초당 발송량, 최근 24시간 발송량을 반환합니다.
    """
    try:
        email_service = EmailService()
        quota = email_service.ses_client.get_send_quota()
        
        return SendQuotaResponse(
            max_24_hour_send=quota['Max24HourSend'],
            max_send_rate=quota['MaxSendRate'],
            sent_last_24_hours=quota['SentLast24Hours']
        )
    except SESClientError as e:
        raise HttpError(500, str(e))
```

### 5.3 API 테스트

**1) Swagger UI를 통한 테스트**

서버를 실행하고 `http://localhost:8000/api/docs`에 접속하면 자동 생성된 API 문서를 확인할 수 있습니다.

```bash
python manage.py runserver
```

**2) cURL을 통한 테스트**

```bash
# 간단한 이메일 발송
curl -X POST "http://localhost:8000/api/emails/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to_emails": ["test@example.com"],
    "subject": "테스트 이메일",
    "body_html": "<h1>안녕하세요</h1><p>테스트입니다.</p>",
    "body_text": "안녕하세요\n테스트입니다."
  }'

# 첨부파일 포함 이메일 발송
curl -X POST "http://localhost:8000/api/emails/send-with-attachments" \
  -F "to_emails=test@example.com" \
  -F "subject=첨부파일 테스트" \
  -F "body_html=<h1>첨부파일이 있습니다</h1>" \
  -F "attachments=@/path/to/file.pdf" \
  -F "attachments=@/path/to/image.jpg"

# 이메일 로그 조회
curl "http://localhost:8000/api/emails/logs/{email_id}"

# 발송 쿼터 조회
curl "http://localhost:8000/api/emails/quota"
```

**3) Python requests를 통한 테스트**

```python
import requests

# 간단한 이메일 발송
response = requests.post(
    'http://localhost:8000/api/emails/send',
    json={
        'to_emails': ['test@example.com'],
        'subject': '테스트 이메일',
        'body_html': '<h1>안녕하세요</h1>',
        'body_text': '안녕하세요'
    }
)
print(response.json())

# 첨부파일 포함 이메일
files = [
    ('attachments', ('report.pdf', open('report.pdf', 'rb'), 'application/pdf')),
    ('attachments', ('chart.png', open('chart.png', 'rb'), 'image/png'))
]
data = {
    'to_emails': 'test@example.com',
    'subject': '리포트 발송',
    'body_html': '<h1>월간 리포트</h1>'
}
response = requests.post(
    'http://localhost:8000/api/emails/send-with-attachments',
    files=files,
    data=data
)
print(response.json())
```

이제 기본 API가 완성되었습니다. 다음 섹션에서는 비동기 처리와 고급 기능을 구현하겠습니다.

## 6. 고급 기능 및 최적화

### 6.1 Celery를 활용한 비동기 이메일 발송

대량의 이메일을 발송하거나 응답 시간이 중요한 API에서는 비동기 처리가 필수입니다.

```python
# apps/emails/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from typing import List, Optional, Dict
import time

from .services.email_service import EmailService, EmailAttachment
from .models import EmailLog

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60초 후 재시도
    autoretry_for=(Exception,),
    retry_backoff=True,  # 지수 백오프
    retry_jitter=True  # 재시도 시간에 랜덤성 추가
)
def send_email_task(
    self,
    to_emails: List[str],
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    from_email: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    attachment_data: Optional[List[Dict]] = None
) -> str:
    """
    비동기 이메일 발송 태스크
    
    Returns:
        EmailLog ID
    """
    try:
        logger.info(f"이메일 발송 태스크 시작: to={to_emails}, subject={subject}")
        
        # 첨부파일 복원
        attachments = []
        if attachment_data:
            for att_data in attachment_data:
                attachment = EmailAttachment(
                    filename=att_data['filename'],
                    content=att_data['content'].encode() if isinstance(att_data['content'], str) else att_data['content'],
                    content_type=att_data['content_type']
                )
                attachments.append(attachment)
        
        # 이메일 발송
        email_service = EmailService()
        email_log = email_service.send_email(
            to_emails=to_emails,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=from_email,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            attachments=attachments if attachments else None
        )
        
        logger.info(f"이메일 발송 완료: {email_log.id}")
        return str(email_log.id)
        
    except Exception as e:
        logger.error(f"이메일 발송 실패 (재시도 {self.request.retries}/{self.max_retries}): {str(e)}")
        
        # 최대 재시도 횟수 도달 시
        if self.request.retries >= self.max_retries:
            logger.error(f"최대 재시도 횟수 도달. 이메일 발송 포기")
        
        raise


@shared_task
def send_bulk_emails_task(email_data_list: List[Dict]) -> Dict:
    """
    대량 이메일 발송 태스크
    
    Args:
        email_data_list: 이메일 데이터 리스트
        
    Returns:
        발송 결과 통계
    """
    logger.info(f"대량 이메일 발송 시작: {len(email_data_list)}건")
    
    results = {
        'total': len(email_data_list),
        'success': 0,
        'failed': 0,
        'email_ids': []
    }
    
    email_service = EmailService()
    
    for email_data in email_data_list:
        try:
            email_log = email_service.send_email(
                to_emails=email_data['to_emails'],
                subject=email_data['subject'],
                body_html=email_data.get('body_html'),
                body_text=email_data.get('body_text'),
                from_email=email_data.get('from_email')
            )
            
            results['success'] += 1
            results['email_ids'].append(str(email_log.id))
            
            # SES rate limit 고려 (초당 발송량 제한)
            time.sleep(0.1)  # 초당 10건으로 제한
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {str(e)}")
            results['failed'] += 1
    
    logger.info(f"대량 이메일 발송 완료: 성공 {results['success']}, 실패 {results['failed']}")
    return results


@shared_task
def retry_failed_emails_task(hours: int = 24) -> Dict:
    """
    실패한 이메일 재발송 태스크
    
    Args:
        hours: 최근 몇 시간 이내의 실패 이메일을 재발송할지
        
    Returns:
        재발송 결과
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(hours=hours)
    
    # 실패한 이메일 조회 (재시도 횟수 3회 미만)
    failed_emails = EmailLog.objects.filter(
        status=EmailLog.Status.FAILED,
        created_at__gte=cutoff_time,
        retry_count__lt=3
    )
    
    logger.info(f"재발송 대상 이메일: {failed_emails.count()}건")
    
    results = {
        'total': failed_emails.count(),
        'success': 0,
        'failed': 0
    }
    
    email_service = EmailService()
    
    for email_log in failed_emails:
        try:
            # 재발송
            new_log = email_service.send_email(
                to_emails=email_log.to_emails,
                subject=email_log.subject,
                body_html=email_log.body_html,
                body_text=email_log.body_text,
                from_email=email_log.from_email,
                cc_emails=email_log.cc_emails if email_log.cc_emails else None,
                bcc_emails=email_log.bcc_emails if email_log.bcc_emails else None
            )
            
            # 원본 로그 업데이트
            email_log.retry_count += 1
            email_log.save(update_fields=['retry_count'])
            
            results['success'] += 1
            logger.info(f"이메일 재발송 성공: {email_log.id} -> {new_log.id}")
            
            time.sleep(0.1)
            
        except Exception as e:
            email_log.retry_count += 1
            email_log.save(update_fields=['retry_count'])
            results['failed'] += 1
            logger.error(f"이메일 재발송 실패: {email_log.id} - {str(e)}")
    
    return results
```

**비동기 API 엔드포인트 추가**

```python
# apps/emails/api.py에 추가

@router.post(
    "/send-async",
    response={202: dict, 400: ErrorResponse},
    summary="비동기 이메일 발송",
    description="이메일을 비동기로 발송합니다. 즉시 태스크 ID를 반환합니다."
)
def send_email_async(request, payload: SendEmailRequest):
    """
    비동기 이메일 발송 API
    
    Celery 태스크로 이메일을 발송하고 즉시 태스크 ID를 반환합니다.
    """
    from apps.emails.tasks import send_email_task
    
    try:
        task = send_email_task.delay(
            to_emails=payload.to_emails,
            subject=payload.subject,
            body_html=payload.body_html,
            body_text=payload.body_text,
            cc_emails=payload.cc_emails,
            bcc_emails=payload.bcc_emails
        )
        
        return {
            'task_id': task.id,
            'status': 'queued',
            'message': '이메일이 발송 대기열에 추가되었습니다'
        }
        
    except Exception as e:
        logger.exception("비동기 이메일 발송 실패")
        raise HttpError(400, str(e))


@router.get(
    "/task/{task_id}",
    response=dict,
    summary="태스크 상태 조회",
    description="비동기 이메일 발송 태스크의 상태를 조회합니다."
)
def get_task_status(request, task_id: str):
    """
    Celery 태스크 상태 조회 API
    
    - **task_id**: Celery 태스크 ID
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id)
    
    response = {
        'task_id': task_id,
        'status': task_result.status,
        'result': None
    }
    
    if task_result.ready():
        if task_result.successful():
            response['result'] = task_result.result
        else:
            response['error'] = str(task_result.info)
    
    return response
```

### 6.2 이메일 템플릿 시스템

Django 템플릿을 활용한 이메일 템플릿을 만들겠습니다.

{% raw %}
```html
<!-- templates/emails/base.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Noto Sans KR', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #4A90E2;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
        }
        .footer {
            background-color: #333;
            color: #fff;
            padding: 15px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 5px 5px;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background-color: #4A90E2;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }
        .button:hover {
            background-color: #357ABD;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{% block header_title %}알림{% endblock %}</h1>
    </div>
    <div class="content">
        {% block content %}{% endblock %}
    </div>
    <div class="footer">
        <p>&copy; 2025 Your Company. All rights reserved.</p>
        <p>
            <a href="#" style="color: #4A90E2;">수신거부</a> |
            <a href="#" style="color: #4A90E2;">개인정보처리방침</a>
        </p>
    </div>
</body>
</html>
```

```html
<!-- templates/emails/notification.html -->
{% extends "emails/base.html" %}

{% block header_title %}{{ subject }}{% endblock %}

{% block content %}
<h2>안녕하세요, {{ username }}님!</h2>

<p>{{ message }}</p>

{% if action_url %}
<a href="{{ action_url }}" class="button">{{ action_text|default:"자세히 보기" }}</a>
{% endif %}

{% if items %}
<h3>항목 목록:</h3>
<ul>
    {% for item in items %}
    <li>{{ item }}</li>
    {% endfor %}
</ul>
{% endif %}

<p>
    문의사항이 있으시면 언제든지 연락주세요.<br>
    감사합니다.
</p>
{% endblock %}
```

```
<!-- templates/emails/notification.txt -->
{{ subject }}

안녕하세요, {{ username }}님!

{{ message }}

{% if action_url %}
자세히 보기: {{ action_url }}
{% endif %}

{% if items %}
항목 목록:
{% for item in items %}
- {{ item }}
{% endfor %}
{% endif %}

문의사항이 있으시면 언제든지 연락주세요.
감사합니다.

---
© 2025 Your Company. All rights reserved.
```
{% endraw %}

### 6.3 레이트 리미팅 및 쿼터 관리

```python
# apps/emails/services/rate_limiter.py
from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """이메일 발송 속도 제한"""
    
    def __init__(self):
        self.cache_key_prefix = 'email_rate_limit'
    
    def check_rate_limit(self, identifier: str, limit: int = 100, period: int = 3600) -> bool:
        """
        레이트 리미트 체크
        
        Args:
            identifier: 식별자 (예: user_id, ip_address)
            limit: 제한 횟수
            period: 제한 기간 (초)
            
        Returns:
            True: 허용, False: 제한 초과
        """
        cache_key = f"{self.cache_key_prefix}:{identifier}"
        
        # 현재 카운트 조회
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            logger.warning(f"레이트 리미트 초과: {identifier} ({current_count}/{limit})")
            return False
        
        # 카운트 증가
        if current_count == 0:
            # 첫 요청이면 TTL 설정
            cache.set(cache_key, 1, period)
        else:
            # 기존 TTL 유지하면서 증가
            cache.incr(cache_key)
        
        return True
    
    def get_remaining_quota(self, identifier: str, limit: int = 100) -> int:
        """
        남은 쿼터 조회
        
        Args:
            identifier: 식별자
            limit: 제한 횟수
            
        Returns:
            남은 발송 가능 횟수
        """
        cache_key = f"{self.cache_key_prefix}:{identifier}"
        current_count = cache.get(cache_key, 0)
        return max(0, limit - current_count)
    
    def reset_quota(self, identifier: str):
        """쿼터 초기화"""
        cache_key = f"{self.cache_key_prefix}:{identifier}"
        cache.delete(cache_key)
        logger.info(f"쿼터 초기화: {identifier}")


# API에 레이트 리미팅 적용
# apps/emails/api.py에 추가

from .services.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

@router.post("/send")
def send_email(request, payload: SendEmailRequest):
    # 레이트 리미트 체크 (IP 기반)
    client_ip = request.META.get('REMOTE_ADDR')
    
    if not rate_limiter.check_rate_limit(
        identifier=f"ip:{client_ip}",
        limit=100,  # 1시간당 100건
        period=3600
    ):
        remaining = rate_limiter.get_remaining_quota(f"ip:{client_ip}", limit=100)
        raise HttpError(429, f"발송 제한을 초과했습니다. 남은 쿼터: {remaining}")
    
    # 기존 로직...
```

### 6.4 이메일 검증 및 블랙리스트

```python
# apps/emails/services/email_validator.py
import re
from typing import Tuple
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class EmailValidator:
    """이메일 주소 검증"""
    
    # 일회용 이메일 도메인 (예시)
    DISPOSABLE_DOMAINS = {
        'tempmail.com', 'throwaway.email', '10minutemail.com',
        'guerrillamail.com', 'mailinator.com'
    }
    
    # 블랙리스트 캐시 키
    BLACKLIST_CACHE_KEY = 'email_blacklist'
    
    @staticmethod
    def is_valid_format(email: str) -> bool:
        """이메일 형식 검증"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def is_disposable(cls, email: str) -> bool:
        """일회용 이메일 주소 체크"""
        domain = email.split('@')[1].lower()
        return domain in cls.DISPOSABLE_DOMAINS
    
    @classmethod
    def is_blacklisted(cls, email: str) -> bool:
        """블랙리스트 체크"""
        blacklist = cache.get(cls.BLACKLIST_CACHE_KEY, set())
        return email.lower() in blacklist
    
    @classmethod
    def add_to_blacklist(cls, email: str):
        """블랙리스트에 추가"""
        blacklist = cache.get(cls.BLACKLIST_CACHE_KEY, set())
        blacklist.add(email.lower())
        cache.set(cls.BLACKLIST_CACHE_KEY, blacklist, timeout=None)
        logger.info(f"블랙리스트 추가: {email}")
    
    @classmethod
    def remove_from_blacklist(cls, email: str):
        """블랙리스트에서 제거"""
        blacklist = cache.get(cls.BLACKLIST_CACHE_KEY, set())
        blacklist.discard(email.lower())
        cache.set(cls.BLACKLIST_CACHE_KEY, blacklist, timeout=None)
        logger.info(f"블랙리스트 제거: {email}")
    
    @classmethod
    def validate(cls, email: str) -> Tuple[bool, str]:
        """
        종합 검증
        
        Returns:
            (유효성, 에러 메시지)
        """
        if not cls.is_valid_format(email):
            return False, "올바르지 않은 이메일 형식입니다"
        
        if cls.is_disposable(email):
            return False, "일회용 이메일 주소는 사용할 수 없습니다"
        
        if cls.is_blacklisted(email):
            return False, "차단된 이메일 주소입니다"
        
        return True, "OK"
```

이제 고급 기능들이 구현되었습니다. 다음 섹션에서는 테스트 코드를 작성하겠습니다.

## 7. 테스트 코드 작성

### 7.1 pytest 설정

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = --reuse-db --nomigrations -v
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Tests that take a long time to run
```

```python
# conftest.py
import pytest
from moto import mock_ses
import boto3
from django.conf import settings


@pytest.fixture
def mock_ses_client():
    """Mock SES 클라이언트"""
    with mock_ses():
        # SES 클라이언트 생성
        client = boto3.client(
            'ses',
            region_name=settings.AWS_REGION,
            aws_access_key_id='testing',
            aws_secret_access_key='testing'
        )
        
        # 테스트용 이메일 주소 인증
        client.verify_email_identity(EmailAddress=settings.AWS_SES_FROM_EMAIL)
        client.verify_email_identity(EmailAddress='test@example.com')
        
        yield client


@pytest.fixture
def sample_attachment():
    """샘플 첨부파일"""
    from apps.emails.services.email_service import EmailAttachment
    
    return EmailAttachment(
        filename='test.pdf',
        content=b'PDF content here',
        content_type='application/pdf'
    )


@pytest.fixture
def sample_email_data():
    """샘플 이메일 데이터"""
    return {
        'to_emails': ['test@example.com'],
        'subject': 'Test Email',
        'body_html': '<h1>Test</h1>',
        'body_text': 'Test'
    }
```

### 7.2 서비스 레이어 테스트

```python
# apps/emails/tests/test_services.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from apps.emails.services.ses_client import SESClient, SESClientError
from apps.emails.services.email_service import EmailService, EmailAttachment
from apps.emails.models import EmailLog


@pytest.mark.django_db
class TestSESClient:
    """SES 클라이언트 테스트"""
    
    def test_send_raw_email_success(self, mock_ses_client):
        """정상 발송 테스트"""
        client = SESClient()
        
        message = b"From: test@example.com\nTo: test@example.com\nSubject: Test\n\nBody"
        
        response = client.send_raw_email(
            raw_message=message,
            source='test@example.com',
            destinations=['test@example.com']
        )
        
        assert 'MessageId' in response
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_send_raw_email_invalid_sender(self, mock_ses_client):
        """미인증 발신자 테스트"""
        client = SESClient()
        
        message = b"From: invalid@example.com\nTo: test@example.com\nSubject: Test\n\nBody"
        
        with pytest.raises(SESClientError) as exc_info:
            client.send_raw_email(
                raw_message=message,
                source='invalid@example.com',
                destinations=['test@example.com']
            )
        
        assert "인증" in str(exc_info.value).lower() or "verified" in str(exc_info.value).lower()
    
    def test_get_send_quota(self, mock_ses_client):
        """발송 쿼터 조회 테스트"""
        client = SESClient()
        quota = client.get_send_quota()
        
        assert 'Max24HourSend' in quota
        assert 'MaxSendRate' in quota
        assert 'SentLast24Hours' in quota


@pytest.mark.django_db
class TestEmailAttachment:
    """첨부파일 테스트"""
    
    def test_attachment_creation(self):
        """첨부파일 생성 테스트"""
        attachment = EmailAttachment(
            filename='test.pdf',
            content=b'PDF content',
            content_type='application/pdf'
        )
        
        assert attachment.filename == 'test.pdf'
        assert attachment.content == b'PDF content'
        assert attachment.content_type == 'application/pdf'
    
    def test_attachment_content_type_guessing(self):
        """Content-Type 자동 추측 테스트"""
        attachment = EmailAttachment(
            filename='image.png',
            content=b'PNG data'
        )
        
        assert attachment.content_type == 'image/png'
    
    def test_attachment_size_validation(self, settings):
        """파일 크기 검증 테스트"""
        settings.EMAIL_MAX_ATTACHMENT_SIZE = 100
        
        # 작은 파일 - 성공
        small_attachment = EmailAttachment(
            filename='small.txt',
            content=b'small'
        )
        is_valid, msg = small_attachment.validate()
        assert is_valid
        
        # 큰 파일 - 실패
        large_attachment = EmailAttachment(
            filename='large.txt',
            content=b'x' * 200
        )
        is_valid, msg = large_attachment.validate()
        assert not is_valid
        assert '초과' in msg
    
    def test_attachment_extension_validation(self, settings):
        """파일 확장자 검증 테스트"""
        settings.EMAIL_ALLOWED_EXTENSIONS = ['pdf', 'jpg']
        
        # 허용된 확장자
        valid_attachment = EmailAttachment(
            filename='doc.pdf',
            content=b'data'
        )
        is_valid, msg = valid_attachment.validate()
        assert is_valid
        
        # 허용되지 않은 확장자
        invalid_attachment = EmailAttachment(
            filename='script.exe',
            content=b'data'
        )
        is_valid, msg = invalid_attachment.validate()
        assert not is_valid
        assert '허용되지 않는' in msg


@pytest.mark.django_db
class TestEmailService:
    """이메일 서비스 테스트"""
    
    def test_send_email_success(self, mock_ses_client, sample_email_data):
        """이메일 발송 성공 테스트"""
        service = EmailService()
        
        email_log = service.send_email(**sample_email_data)
        
        assert email_log.status == EmailLog.Status.SENT
        assert email_log.message_id is not None
        assert email_log.to_emails == sample_email_data['to_emails']
        assert email_log.subject == sample_email_data['subject']
    
    def test_send_email_with_attachment(self, mock_ses_client, sample_email_data, sample_attachment):
        """첨부파일 포함 이메일 발송 테스트"""
        service = EmailService()
        
        email_log = service.send_email(
            **sample_email_data,
            attachments=[sample_attachment]
        )
        
        assert email_log.status == EmailLog.Status.SENT
        assert len(email_log.attachments) == 1
        assert email_log.attachments[0]['filename'] == 'test.pdf'
    
    def test_send_email_invalid_attachment(self, mock_ses_client, sample_email_data, settings):
        """잘못된 첨부파일 테스트"""
        settings.EMAIL_ALLOWED_EXTENSIONS = ['pdf']
        
        service = EmailService()
        
        invalid_attachment = EmailAttachment(
            filename='virus.exe',
            content=b'malicious'
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.send_email(
                **sample_email_data,
                attachments=[invalid_attachment]
            )
        
        assert '허용되지 않는' in str(exc_info.value)
    
    def test_send_email_failure_logging(self, sample_email_data):
        """발송 실패 로깅 테스트"""
        service = EmailService()
        
        # SES 클라이언트를 Mock으로 대체하여 에러 발생시키기
        with patch.object(service.ses_client, 'send_raw_email') as mock_send:
            mock_send.side_effect = SESClientError("Test error")
            
            with pytest.raises(SESClientError):
                service.send_email(**sample_email_data)
            
            # 실패 로그 확인
            failed_log = EmailLog.objects.filter(status=EmailLog.Status.FAILED).first()
            assert failed_log is not None
            assert failed_log.error_message == "Test error"
    
    def test_send_templated_email(self, mock_ses_client):
        """템플릿 이메일 발송 테스트"""
        service = EmailService()
        
        email_log = service.send_templated_email(
            to_emails=['test@example.com'],
            template_name='notification',
            context={
                'subject': 'Test Notification',
                'username': 'John Doe',
                'message': 'This is a test message'
            }
        )
        
        assert email_log.status == EmailLog.Status.SENT
        assert 'John Doe' in email_log.body_html


@pytest.mark.django_db
class TestEmailValidator:
    """이메일 검증 테스트"""
    
    def test_valid_email_format(self):
        """올바른 이메일 형식 테스트"""
        from apps.emails.services.email_validator import EmailValidator
        
        assert EmailValidator.is_valid_format('test@example.com')
        assert EmailValidator.is_valid_format('user.name+tag@example.co.kr')
        assert not EmailValidator.is_valid_format('invalid.email')
        assert not EmailValidator.is_valid_format('@example.com')
    
    def test_disposable_email_detection(self):
        """일회용 이메일 감지 테스트"""
        from apps.emails.services.email_validator import EmailValidator
        
        assert EmailValidator.is_disposable('test@tempmail.com')
        assert not EmailValidator.is_disposable('test@gmail.com')
    
    def test_blacklist_management(self):
        """블랙리스트 관리 테스트"""
        from apps.emails.services.email_validator import EmailValidator
        
        email = 'spam@example.com'
        
        # 블랙리스트 추가
        EmailValidator.add_to_blacklist(email)
        assert EmailValidator.is_blacklisted(email)
        
        # 블랙리스트 제거
        EmailValidator.remove_from_blacklist(email)
        assert not EmailValidator.is_blacklisted(email)


@pytest.mark.django_db
class TestRateLimiter:
    """레이트 리미터 테스트"""
    
    def test_rate_limit_basic(self):
        """기본 레이트 리미팅 테스트"""
        from apps.emails.services.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        identifier = 'test_user'
        
        # 처음 몇 번은 허용
        for i in range(5):
            assert limiter.check_rate_limit(identifier, limit=5, period=60)
        
        # 제한 초과
        assert not limiter.check_rate_limit(identifier, limit=5, period=60)
    
    def test_rate_limit_quota_check(self):
        """남은 쿼터 확인 테스트"""
        from apps.emails.services.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        identifier = 'test_user_2'
        
        # 3번 사용
        for i in range(3):
            limiter.check_rate_limit(identifier, limit=10, period=60)
        
        # 남은 쿼터는 7
        remaining = limiter.get_remaining_quota(identifier, limit=10)
        assert remaining == 7
```

### 7.3 API 엔드포인트 테스트

```python
# apps/emails/tests/test_api.py
import pytest
import json
from django.test import Client
from unittest.mock import patch, Mock
import io

from apps.emails.models import EmailLog


@pytest.mark.django_db
class TestEmailAPI:
    """이메일 API 테스트"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    def test_send_email_endpoint(self, client, mock_ses_client):
        """이메일 발송 엔드포인트 테스트"""
        response = client.post(
            '/api/emails/send',
            data=json.dumps({
                'to_emails': ['test@example.com'],
                'subject': 'Test Email',
                'body_html': '<h1>Test</h1>',
                'body_text': 'Test'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['status'] == 'sent'
    
    def test_send_email_validation_error(self, client):
        """잘못된 요청 검증 테스트"""
        response = client.post(
            '/api/emails/send',
            data=json.dumps({
                'to_emails': [],  # 빈 리스트
                'subject': 'Test'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_send_email_with_attachments_endpoint(self, client, mock_ses_client):
        """첨부파일 포함 발송 엔드포인트 테스트"""
        # 테스트 파일 생성
        test_file = io.BytesIO(b'test file content')
        test_file.name = 'test.txt'
        
        response = client.post(
            '/api/emails/send-with-attachments',
            data={
                'to_emails': 'test@example.com',
                'subject': 'Test with Attachment',
                'body_html': '<h1>Test</h1>',
                'attachments': test_file
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'sent'
    
    def test_get_email_log_endpoint(self, client, mock_ses_client):
        """이메일 로그 조회 엔드포인트 테스트"""
        # 먼저 이메일 발송
        from apps.emails.services.email_service import EmailService
        service = EmailService()
        email_log = service.send_email(
            to_emails=['test@example.com'],
            subject='Test',
            body_text='Test'
        )
        
        # 로그 조회
        response = client.get(f'/api/emails/logs/{email_log.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(email_log.id)
        assert data['subject'] == 'Test'
    
    def test_list_email_logs_endpoint(self, client, mock_ses_client):
        """이메일 로그 목록 엔드포인트 테스트"""
        # 여러 이메일 발송
        from apps.emails.services.email_service import EmailService
        service = EmailService()
        
        for i in range(5):
            service.send_email(
                to_emails=['test@example.com'],
                subject=f'Test {i}',
                body_text='Test'
            )
        
        # 목록 조회
        response = client.get('/api/emails/logs?limit=10')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_get_quota_endpoint(self, client, mock_ses_client):
        """쿼터 조회 엔드포인트 테스트"""
        response = client.get('/api/emails/quota')
        
        assert response.status_code == 200
        data = response.json()
        assert 'max_24_hour_send' in data
        assert 'max_send_rate' in data
        assert 'sent_last_24_hours' in data
    
    def test_rate_limiting(self, client, mock_ses_client):
        """레이트 리미팅 테스트"""
        # 짧은 시간에 많은 요청
        for i in range(101):  # 제한: 100
            response = client.post(
                '/api/emails/send',
                data=json.dumps({
                    'to_emails': ['test@example.com'],
                    'subject': f'Test {i}',
                    'body_text': 'Test'
                }),
                content_type='application/json',
                REMOTE_ADDR='127.0.0.1'
            )
            
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429  # Too Many Requests


@pytest.mark.django_db
class TestAsyncEmailAPI:
    """비동기 이메일 API 테스트"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    @patch('apps.emails.tasks.send_email_task.delay')
    def test_send_email_async_endpoint(self, mock_task, client):
        """비동기 발송 엔드포인트 테스트"""
        mock_task.return_value = Mock(id='test-task-id')
        
        response = client.post(
            '/api/emails/send-async',
            data=json.dumps({
                'to_emails': ['test@example.com'],
                'subject': 'Async Test',
                'body_text': 'Test'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'queued'
        
        # Celery 태스크가 호출되었는지 확인
        mock_task.assert_called_once()


# 테스트 실행
# pytest apps/emails/tests/ -v
# pytest apps/emails/tests/test_services.py::TestEmailService -v
# pytest apps/emails/tests/ --cov=apps.emails --cov-report=html
```

### 7.4 커버리지 확인

```bash
# 테스트 실행 및 커버리지 확인
pytest apps/emails/tests/ --cov=apps.emails --cov-report=html --cov-report=term

# 결과 예시:
# Name                                    Stmts   Miss  Cover
# -----------------------------------------------------------
# apps/emails/__init__.py                     0      0   100%
# apps/emails/models.py                      45      2    96%
# apps/emails/schemas.py                     38      1    97%
# apps/emails/services/ses_client.py         72      5    93%
# apps/emails/services/email_service.py     128      8    94%
# apps/emails/api.py                         95      6    94%
# -----------------------------------------------------------
# TOTAL                                     378     22    94%
```

이제 테스트 코드가 완성되었습니다. 다음 섹션에서는 프로덕션 배포 가이드를 작성하겠습니다.

## 8. 프로덕션 배포 가이드

### 8.1 보안 설정

**1) AWS IAM 역할 기반 인증 (EC2/ECS)**

하드코딩된 Access Key 대신 IAM 역할을 사용하는 것이 더 안전합니다.

```python
# config/settings.py - 프로덕션 설정
import boto3
from botocore.exceptions import NoCredentialsError

# IAM 역할 사용 시 (EC2/ECS)
try:
    # 자격 증명을 명시하지 않으면 IAM 역할 사용
    session = boto3.Session()
    AWS_ACCESS_KEY_ID = None
    AWS_SECRET_ACCESS_KEY = None
except NoCredentialsError:
    # Fallback to environment variables
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
```

**2) AWS Secrets Manager 사용**

```python
# apps/emails/utils/secrets.py
import boto3
import json
from django.conf import settings


def get_secret(secret_name: str) -> dict:
    """AWS Secrets Manager에서 시크릿 가져오기"""
    client = boto3.client(
        'secretsmanager',
        region_name=settings.AWS_REGION
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise Exception(f"시크릿 가져오기 실패: {str(e)}")


# 사용 예시
# secrets = get_secret('prod/email-service')
# AWS_ACCESS_KEY_ID = secrets['aws_access_key_id']
```

**3) 환경별 설정 분리**

```python
# config/settings/base.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ... 공통 설정 ...
```

```python
# config/settings/production.py
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# 보안 설정
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS 설정
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')

# 데이터베이스 - RDS 사용
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'sslmode': 'require',
        }
    }
}

# Redis - ElastiCache 사용
CELERY_BROKER_URL = os.getenv('REDIS_URL')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL')

# 로깅 - CloudWatch로 전송
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'watchtower': {
            'class': 'watchtower.CloudWatchLogHandler',
            'log_group': '/aws/email-service',
            'stream_name': 'production',
        }
    },
    'loggers': {
        'apps.emails': {
            'handlers': ['console', 'watchtower'],
            'level': 'INFO',
        },
    },
}
```

### 8.2 모니터링 및 알림

**1) CloudWatch 메트릭 전송**

```python
# apps/emails/services/metrics.py
import boto3
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricsClient:
    """CloudWatch 메트릭 클라이언트"""
    
    def __init__(self):
        self.client = boto3.client(
            'cloudwatch',
            region_name=settings.AWS_REGION
        )
        self.namespace = 'EmailService'
    
    def put_metric(self, metric_name: str, value: float, unit: str = 'Count', **dimensions):
        """메트릭 전송"""
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': [
                            {'Name': k, 'Value': v}
                            for k, v in dimensions.items()
                        ]
                    }
                ]
            )
        except Exception as e:
            logger.error(f"메트릭 전송 실패: {str(e)}")
    
    def record_email_sent(self, status: str):
        """이메일 발송 메트릭"""
        self.put_metric('EmailSent', 1, Status=status)
    
    def record_send_duration(self, duration_ms: float):
        """발송 소요 시간 메트릭"""
        self.put_metric('SendDuration', duration_ms, unit='Milliseconds')
    
    def record_attachment_size(self, size_bytes: int):
        """첨부파일 크기 메트릭"""
        self.put_metric('AttachmentSize', size_bytes, unit='Bytes')


# 이메일 서비스에 메트릭 추가
# apps/emails/services/email_service.py에 추가

from .metrics import MetricsClient
import time

class EmailService:
    def __init__(self):
        self.ses_client = SESClient()
        self.metrics = MetricsClient()
    
    def send_email(self, ...):
        start_time = time.time()
        
        try:
            # ... 기존 로직 ...
            
            # 성공 메트릭
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_email_sent('success')
            self.metrics.record_send_duration(duration_ms)
            
            return email_log
            
        except Exception as e:
            # 실패 메트릭
            self.metrics.record_email_sent('failed')
            raise
```

**2) SNS 알림 설정**

```python
# apps/emails/services/notifications.py
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SNSNotifier:
    """SNS 알림 클라이언트"""
    
    def __init__(self):
        self.client = boto3.client(
            'sns',
            region_name=settings.AWS_REGION
        )
        self.topic_arn = settings.SNS_ALERT_TOPIC_ARN
    
    def send_alert(self, subject: str, message: str):
        """알림 전송"""
        try:
            self.client.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message
            )
            logger.info(f"알림 전송: {subject}")
        except Exception as e:
            logger.error(f"알림 전송 실패: {str(e)}")
    
    def send_error_alert(self, error: Exception, context: dict):
        """에러 알림"""
        message = f"""
이메일 발송 에러 발생

에러: {str(error)}
컨텍스트: {context}

즉시 확인이 필요합니다.
        """
        self.send_alert("이메일 서비스 에러", message)


# Celery 태스크에서 사용
from .notifications import SNSNotifier

@shared_task
def send_email_task(...):
    notifier = SNSNotifier()
    
    try:
        # ... 발송 로직 ...
        pass
    except Exception as e:
        notifier.send_error_alert(e, {'to_emails': to_emails})
        raise
```

**3) SES 이벤트 추적 (SNS 웹훅)**

```python
# apps/emails/views.py - SES 이벤트 수신
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def ses_webhook(request):
    """
    SES 이벤트 웹훅 핸들러
    
    Bounce, Complaint 등의 이벤트를 수신하여 처리
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # SNS 메시지 파싱
        message = json.loads(request.body)
        
        # 구독 확인
        if message.get('Type') == 'SubscriptionConfirmation':
            # SubscribeURL 방문하여 구독 확인
            import requests
            requests.get(message['SubscribeURL'])
            logger.info("SNS 구독 확인 완료")
            return JsonResponse({'status': 'confirmed'})
        
        # 알림 메시지 처리
        if message.get('Type') == 'Notification':
            ses_message = json.loads(message['Message'])
            event_type = ses_message.get('eventType')
            
            if event_type == 'Bounce':
                handle_bounce(ses_message)
            elif event_type == 'Complaint':
                handle_complaint(ses_message)
            elif event_type == 'Delivery':
                handle_delivery(ses_message)
            
            return JsonResponse({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"SES 웹훅 처리 실패: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def handle_bounce(message):
    """바운스 처리"""
    bounce = message['bounce']
    bounced_recipients = bounce['bouncedRecipients']
    
    for recipient in bounced_recipients:
        email = recipient['emailAddress']
        
        # 이메일 로그 업데이트
        EmailLog.objects.filter(
            to_emails__contains=[email],
            message_id=message['mail']['messageId']
        ).update(status=EmailLog.Status.BOUNCED)
        
        # 블랙리스트 추가 (Hard bounce의 경우)
        if bounce['bounceType'] == 'Permanent':
            from apps.emails.services.email_validator import EmailValidator
            EmailValidator.add_to_blacklist(email)
            logger.warning(f"영구 바운스로 블랙리스트 추가: {email}")


def handle_complaint(message):
    """스팸 신고 처리"""
    complaint = message['complaint']
    complained_recipients = complaint['complainedRecipients']
    
    for recipient in complained_recipients:
        email = recipient['emailAddress']
        
        # 이메일 로그 업데이트
        EmailLog.objects.filter(
            to_emails__contains=[email],
            message_id=message['mail']['messageId']
        ).update(status=EmailLog.Status.COMPLAINED)
        
        # 블랙리스트 추가
        from apps.emails.services.email_validator import EmailValidator
        EmailValidator.add_to_blacklist(email)
        logger.warning(f"스팸 신고로 블랙리스트 추가: {email}")


def handle_delivery(message):
    """전송 성공 처리"""
    logger.info(f"이메일 전송 성공: {message['mail']['messageId']}")
```

### 8.3 Docker 배포

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Gunicorn으로 실행
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: email_service
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  celery:
    build: .
    command: celery -A config worker -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis
  
  celery-beat:
    build: .
    command: celery -A config beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

### 8.4 성능 최적화

**1) 커넥션 풀링**

```python
# config/settings/production.py

# PostgreSQL 커넥션 풀링
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # 10분
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30초
        }
    }
}

# Redis 커넥션 풀
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True
            }
        }
    }
}
```

**2) 이메일 배치 처리**

```python
# apps/emails/services/batch_processor.py
from typing import List
import time
from django.db import transaction


class EmailBatchProcessor:
    """이메일 배치 처리"""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.email_service = EmailService()
    
    def process_batch(self, emails: List[dict]) -> dict:
        """
        이메일 배치 발송
        
        Args:
            emails: 이메일 데이터 리스트
            
        Returns:
            발송 결과 통계
        """
        results = {
            'total': len(emails),
            'success': 0,
            'failed': 0
        }
        
        # 배치 단위로 처리
        for i in range(0, len(emails), self.batch_size):
            batch = emails[i:i + self.batch_size]
            
            with transaction.atomic():
                for email_data in batch:
                    try:
                        self.email_service.send_email(**email_data)
                        results['success'] += 1
                    except Exception as e:
                        results['failed'] += 1
                        logger.error(f"배치 발송 실패: {str(e)}")
            
            # Rate limit 고려
            time.sleep(1)  # 배치 간 1초 대기
        
        return results
```

**3) 캐싱 전략**

```python
# apps/emails/services/cache_service.py
from django.core.cache import cache
from functools import wraps


def cache_email_template(timeout=3600):
    """이메일 템플릿 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(template_name, *args, **kwargs):
            cache_key = f'email_template:{template_name}'
            result = cache.get(cache_key)
            
            if result is None:
                result = func(template_name, *args, **kwargs)
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


@cache_email_template(timeout=3600)
def get_rendered_template(template_name, context):
    """템플릿 렌더링 (캐시 적용)"""
    from django.template.loader import render_to_string
    return render_to_string(f'emails/{template_name}.html', context)
```

이제 프로덕션 배포 가이드가 완성되었습니다. 마지막으로 결론을 작성하겠습니다.

## 9. 결론

### 9.1 주요 구현 내용 요약

이 가이드에서는 Django Ninja와 AWS SES를 활용하여 프로덕션 수준의 이메일 발송 API를 구축했습니다:

**핵심 기능:**
- ✅ AWS SES 통합 및 첨부파일 지원
- ✅ RESTful API (Django Ninja)
- ✅ 비동기 처리 (Celery)
- ✅ 이메일 템플릿 시스템
- ✅ 레이트 리미팅 및 쿼터 관리
- ✅ 이메일 검증 및 블랙리스트
- ✅ 에러 핸들링 및 재시도 로직
- ✅ 포괄적인 테스트 코드
- ✅ 모니터링 및 알림 시스템
- ✅ Docker 기반 배포

### 9.2 베스트 프랙티스

**1) 보안**
- IAM 역할 기반 인증 사용
- 민감 정보는 Secrets Manager 활용
- HTTPS 및 CORS 설정
- 입력 데이터 검증 철저히 수행

**2) 성능**
- 비동기 처리로 응답 시간 단축
- 커넥션 풀링으로 리소스 효율화
- 템플릿 캐싱으로 렌더링 속도 향상
- 배치 처리로 대량 발송 최적화

**3) 안정성**
- 재시도 로직 및 지수 백오프
- 에러 로깅 및 알림
- SES 이벤트 추적 (Bounce, Complaint)
- 레이트 리미팅으로 서비스 보호

**4) 모니터링**
- CloudWatch 메트릭 수집
- 발송 상태 로깅
- 에러 알림 (SNS)
- 성능 추적

### 9.3 확장 가능성

이 시스템은 다음과 같이 확장할 수 있습니다:

**기능 확장:**
- 이메일 스케줄링 (특정 시간에 발송)
- A/B 테스트 (여러 버전 테스트)
- 이메일 트래킹 (열람, 클릭 추적)
- 자동 응답 및 시퀀스
- 다국어 템플릿 지원

**인프라 확장:**
- Kubernetes 배포
- 멀티 리전 구성
- 로드 밸런싱
- Auto Scaling
- CDN을 통한 정적 파일 제공

**통합 확장:**
- Slack/Discord 알림
- CRM 시스템 연동
- 분석 도구 통합 (Google Analytics)
- 마케팅 자동화 플랫폼 연결

### 9.4 비용 최적화 팁

**AWS SES 비용:**
- 무료 티어: 월 62,000건
- 유료: $0.10/1,000건
- 첨부파일: 추가 비용 없음
- 전송 대역폭: EC2 내부에서 SES 호출 시 무료

**예상 비용 (월 100만 건 기준):**
```
SES: (1,000,000 - 62,000) × $0.10 / 1,000 = $93.80
EC2 (t3.medium): ~$30
RDS (db.t3.micro): ~$15
ElastiCache (cache.t3.micro): ~$12
------------------------
총 예상 비용: ~$150/월
```

**비용 절감 전략:**
- 템플릿 캐싱으로 CPU 사용량 감소
- 배치 처리로 API 호출 최소화
- Reserved Instance 활용
- 불필요한 로그 줄이기

### 9.5 트러블슈팅 가이드

**문제 1: "MessageRejected" 에러**
```
원인: 발신자 이메일/도메인 미인증
해결: AWS SES 콘솔에서 이메일 주소 또는 도메인 인증
```

**문제 2: "MailFromDomainNotVerified" 에러**
```
원인: MAIL FROM 도메인 미설정
해결: SES에서 Custom MAIL FROM 도메인 설정
```

**문제 3: 첨부파일이 손상됨**
```
원인: 인코딩 문제
해결: MIME 파트 생성 시 올바른 Content-Type 설정
```

**문제 4: Celery 태스크가 실행되지 않음**
```
원인: Celery worker 미실행 또는 Redis 연결 문제
해결: 
1. Celery worker 상태 확인: celery -A config inspect active
2. Redis 연결 확인: redis-cli ping
```

**문제 5: 높은 바운스율**
```
원인: 잘못된 이메일 주소 또는 스팸으로 분류
해결:
1. 이메일 검증 강화
2. SPF, DKIM, DMARC 레코드 확인
3. 발송 빈도 조절
4. 수신자 참여 유도 (옵트인)
```

### 9.6 참고 자료

**공식 문서:**
- [AWS SES 개발자 가이드](https://docs.aws.amazon.com/ses/)
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Celery 공식 문서](https://docs.celeryproject.org/)
- [boto3 SES 레퍼런스](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html)

**관련 RFC:**
- [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)
- [RFC 2045-2049 - MIME](https://tools.ietf.org/html/rfc2045)
- [RFC 7208 - SPF](https://tools.ietf.org/html/rfc7208)
- [RFC 6376 - DKIM](https://tools.ietf.org/html/rfc6376)

**유용한 도구:**
- [Mail Tester](https://www.mail-tester.com/) - 이메일 스팸 점수 확인
- [MXToolbox](https://mxtoolbox.com/) - DNS, SPF, DKIM 검증
- [Litmus](https://www.litmus.com/) - 이메일 클라이언트 호환성 테스트
- [Postmark SPAM Check](https://spamcheck.postmarkapp.com/) - 스팸 필터 테스트

**커뮤니티:**
- [Django Forum](https://forum.djangoproject.com/)
- [AWS re:Post](https://repost.aws/)
- [Stack Overflow - Django Tag](https://stackoverflow.com/questions/tagged/django)

### 9.7 마치며

이메일은 여전히 가장 신뢰할 수 있는 커뮤니케이션 채널입니다. 이 가이드에서 구축한 시스템은 다음과 같은 장점을 제공합니다:

**비즈니스 가치:**
- 📊 확장 가능한 아키텍처
- 💰 비용 효율적인 솔루션
- 🔒 엔터프라이즈급 보안
- 📈 데이터 기반 의사결정 (로깅, 메트릭)

**개발자 경험:**
- 🚀 빠른 개발 속도 (Django Ninja)
- 🧪 테스트 가능한 코드
- 📚 자동 API 문서화
- 🔧 유지보수 용이

**운영 관점:**
- 🎯 높은 전달률 (AWS SES)
- 📊 실시간 모니터링
- 🔄 자동 재시도 및 복구
- 🛡️ 에러 추적 및 알림

이제 여러분의 프로젝트에 이 시스템을 적용하고, 필요에 따라 커스터마이징하여 사용하시기 바랍니다. 

질문이나 피드백이 있으시면 댓글로 남겨주세요! 🚀

---

**전체 코드는 GitHub에서 확인할 수 있습니다:**
- Repository: `https://github.com/yourusername/django-ses-email-service`
- Branch: `main`
- License: MIT

**다음 포스트 예고:**
- Django Ninja로 실시간 채팅 API 구현하기
- AWS Lambda + Django로 서버리스 백엔드 만들기
- Django에서 WebSocket과 Channels 활용하기
