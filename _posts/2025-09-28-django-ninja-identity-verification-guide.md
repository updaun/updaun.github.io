---
layout: post
title: "Django Ninja로 본인인증 시스템 구축하기 - 휴대폰 SMS 인증부터 신분증 검증까지"
date: 2025-09-28 10:00:00 +0900
categories: [Web Development, Backend, Authentication]
tags: [django, django-ninja, identity verification, sms authentication, phone verification, id card verification, security]
description: "Django Ninja를 활용하여 휴대폰 SMS 인증, 이메일 인증, 신분증 OCR 검증을 포함한 완전한 본인인증 시스템을 구축하는 방법을 단계별로 알아봅니다. 실제 서비스에서 사용할 수 있는 보안성과 사용성을 모두 갖춘 인증 시스템 구현 가이드입니다."
author: "updaun"
image: "/assets/img/posts/2025-09-28-django-ninja-identity-verification-guide.webp"
---

## 개요

현대 웹 서비스에서 본인인증은 필수적인 보안 기능입니다. 특히 금융, 의료, 전자상거래 등 민감한 데이터를 다루는 서비스에서는 강력한 본인인증 시스템이 요구됩니다. Django Ninja를 활용하여 다단계 본인인증 시스템을 구축하는 방법을 알아보겠습니다.

## 본인인증 시스템의 구성 요소

### 1. 다단계 인증 방식
- **1단계**: 휴대폰 SMS 인증
- **2단계**: 이메일 인증
- **3단계**: 신분증 OCR 검증
- **4단계**: 얼굴 인식 검증 (선택사항)

### 2. 보안 고려사항
- **시간 제한**: 각 인증 단계별 제한 시간
- **재시도 제한**: 무차별 대입 공격 방지
- **암호화**: 민감 정보 암호화 저장
- **로깅**: 인증 시도 기록 및 모니터링

### 3. 사용자 경험
- **진행 상태 표시**: 현재 인증 단계 시각화
- **에러 처리**: 명확한 오류 메시지
- **모바일 최적화**: 반응형 UI 설계

## 프로젝트 설정

### 1. 의존성 설치

```bash
# 가상환경 생성 및 활성화
python -m venv identity_verification_env
source identity_verification_env/bin/activate

# 필수 패키지 설치
pip install django django-ninja celery redis
pip install twilio python-decouple pillow opencv-python
pip install easyocr pytesseract face-recognition requests
pip install cryptography pyjwt django-cors-headers

# requirements.txt 생성
pip freeze > requirements.txt
```

### 2. Django 설정

```python
# settings.py
import os
from decouple import config
from datetime import timedelta

# 기본 Django 설정
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# 인증 관련 설정
VERIFICATION_SETTINGS = {
    # SMS 인증 설정
    'SMS_PROVIDER': config('SMS_PROVIDER', default='twilio'),
    'TWILIO_ACCOUNT_SID': config('TWILIO_ACCOUNT_SID'),
    'TWILIO_AUTH_TOKEN': config('TWILIO_AUTH_TOKEN'),
    'TWILIO_PHONE_NUMBER': config('TWILIO_PHONE_NUMBER'),
    
    # 이메일 인증 설정
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'EMAIL_HOST': config('EMAIL_HOST'),
    'EMAIL_PORT': config('EMAIL_PORT', cast=int),
    'EMAIL_USE_TLS': config('EMAIL_USE_TLS', cast=bool),
    'EMAIL_HOST_USER': config('EMAIL_HOST_USER'),
    'EMAIL_HOST_PASSWORD': config('EMAIL_HOST_PASSWORD'),
    
    # OCR 서비스 설정
    'OCR_PROVIDER': config('OCR_PROVIDER', default='easyocr'),
    'NAVER_CLOVA_API_URL': config('NAVER_CLOVA_API_URL', default=''),
    'NAVER_CLOVA_SECRET_KEY': config('NAVER_CLOVA_SECRET_KEY', default=''),
    
    # 인증 제한 설정
    'SMS_COOLDOWN_SECONDS': 60,  # SMS 재발송 대기시간
    'EMAIL_COOLDOWN_SECONDS': 60,  # 이메일 재발송 대기시간
    'MAX_VERIFICATION_ATTEMPTS': 5,  # 최대 인증 시도 횟수
    'VERIFICATION_CODE_LENGTH': 6,  # 인증코드 길이
    'VERIFICATION_EXPIRES_MINUTES': 10,  # 인증코드 유효시간
    
    # 신분증 검증 설정
    'ID_CARD_MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_ID_CARD_FORMATS': ['jpg', 'jpeg', 'png'],
    'ID_CARD_MIN_CONFIDENCE': 0.8,  # OCR 신뢰도 임계값
}

# Celery 설정 (비동기 작업용)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# 캐시 설정 (인증 상태 관리용)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 미디어 파일 설정 (신분증 이미지 저장용)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 개발 서버
    "https://yourdomain.com",
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'verification',  # 본인인증 앱
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 3. 환경변수 설정

```bash
# .env
DEBUG=False
SECRET_KEY=your-secret-key-here
DB_NAME=identity_verification
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# SMS 서비스 (Twilio)
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# 이메일 서비스
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# OCR 서비스 (네이버 클로바 OCR)
OCR_PROVIDER=naver_clova
NAVER_CLOVA_API_URL=https://naveropenapi.apigw.ntruss.com/vision/v1/id-card
NAVER_CLOVA_SECRET_KEY=your-naver-clova-secret-key

# Redis
REDIS_URL=redis://localhost:6379/0
```

## 데이터 모델 설계

### 1. 본인인증 관련 모델

```python
# verification/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from cryptography.fernet import Fernet
from django.conf import settings
import uuid
import json
import base64
from datetime import datetime, timedelta

class VerificationSession(models.Model):
    """본인인증 세션 관리"""
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', '진행중'
        PHONE_VERIFIED = 'phone_verified', '휴대폰 인증 완료'
        EMAIL_VERIFIED = 'email_verified', '이메일 인증 완료'
        ID_CARD_VERIFIED = 'id_card_verified', '신분증 인증 완료'
        FACE_VERIFIED = 'face_verified', '얼굴 인증 완료'
        COMPLETED = 'completed', '인증 완료'
        FAILED = 'failed', '인증 실패'
        EXPIRED = 'expired', '인증 만료'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, unique=True)
    
    # 인증 상태
    status = models.CharField(
        max_length=20, 
        choices=VerificationStatus.choices, 
        default=VerificationStatus.PENDING
    )
    current_step = models.PositiveSmallIntegerField(default=1)  # 현재 인증 단계
    max_step = models.PositiveSmallIntegerField(default=4)  # 총 인증 단계
    
    # 개인정보 (암호화 저장)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    encrypted_personal_data = models.TextField(blank=True)  # 암호화된 개인정보
    
    # 인증 시도 관리
    phone_attempts = models.PositiveSmallIntegerField(default=0)
    email_attempts = models.PositiveSmallIntegerField(default=0)
    id_card_attempts = models.PositiveSmallIntegerField(default=0)
    face_attempts = models.PositiveSmallIntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    # 완료 정보
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_score = models.FloatField(default=0.0)  # 인증 신뢰도 점수
    
    class Meta:
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def encrypt_personal_data(self, data):
        """개인정보 암호화"""
        if not data:
            return
        
        key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
        f = Fernet(base64.urlsafe_b64encode(key))
        encrypted_data = f.encrypt(json.dumps(data).encode())
        self.encrypted_personal_data = base64.b64encode(encrypted_data).decode()
    
    def decrypt_personal_data(self):
        """개인정보 복호화"""
        if not self.encrypted_personal_data:
            return {}
        
        try:
            key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
            f = Fernet(base64.urlsafe_b64encode(key))
            encrypted_data = base64.b64decode(self.encrypted_personal_data.encode())
            decrypted_data = f.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except:
            return {}

class PhoneVerification(models.Model):
    """휴대폰 인증 관리"""
    
    session = models.ForeignKey(VerificationSession, on_delete=models.CASCADE, related_name='phone_verifications')
    phone_number = models.CharField(max_length=20)
    verification_code = models.CharField(max_length=10)
    
    # 상태 관리
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # SMS 발송 정보
    sms_sid = models.CharField(max_length=100, blank=True)  # Twilio SID
    sms_status = models.CharField(max_length=20, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(
                minutes=settings.VERIFICATION_SETTINGS['VERIFICATION_EXPIRES_MINUTES']
            )
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def can_resend(self):
        cooldown = settings.VERIFICATION_SETTINGS['SMS_COOLDOWN_SECONDS']
        return (datetime.now() - self.created_at).seconds >= cooldown

class EmailVerification(models.Model):
    """이메일 인증 관리"""
    
    session = models.ForeignKey(VerificationSession, on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField()
    verification_code = models.CharField(max_length=10)
    verification_token = models.UUIDField(default=uuid.uuid4)
    
    # 상태 관리
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(
                minutes=settings.VERIFICATION_SETTINGS['VERIFICATION_EXPIRES_MINUTES']
            )
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def can_resend(self):
        cooldown = settings.VERIFICATION_SETTINGS['EMAIL_COOLDOWN_SECONDS']
        return (datetime.now() - self.created_at).seconds >= cooldown

class IDCardVerification(models.Model):
    """신분증 인증 관리"""
    
    class IDCardType(models.TextChoices):
        RESIDENT_CARD = 'resident_card', '주민등록증'
        DRIVER_LICENSE = 'driver_license', '운전면허증'
        PASSPORT = 'passport', '여권'
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', '대기중'
        PROCESSING = 'processing', '처리중'
        SUCCESS = 'success', '성공'
        FAILED = 'failed', '실패'
        REJECTED = 'rejected', '거부됨'
    
    session = models.ForeignKey(VerificationSession, on_delete=models.CASCADE, related_name='id_card_verifications')
    
    # 신분증 정보
    id_card_type = models.CharField(max_length=20, choices=IDCardType.choices)
    front_image = models.ImageField(upload_to='id_cards/front/')
    back_image = models.ImageField(upload_to='id_cards/back/', null=True, blank=True)
    
    # OCR 결과
    extracted_data = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=0.0)
    
    # 검증 결과
    status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    verification_details = models.JSONField(default=dict, blank=True)
    
    # 개인정보 매칭
    name_match = models.BooleanField(null=True, blank=True)
    birth_date_match = models.BooleanField(null=True, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # 처리 정보
    processing_duration = models.FloatField(null=True, blank=True)  # 처리 시간(초)
    error_message = models.TextField(blank=True)

class FaceVerification(models.Model):
    """얼굴 인증 관리"""
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', '대기중'
        PROCESSING = 'processing', '처리중'
        SUCCESS = 'success', '성공'
        FAILED = 'failed', '실패'
    
    session = models.ForeignKey(VerificationSession, on_delete=models.CASCADE, related_name='face_verifications')
    
    # 얼굴 이미지
    selfie_image = models.ImageField(upload_to='face_verification/')
    reference_image = models.ImageField(upload_to='face_verification/', null=True, blank=True)
    
    # 인식 결과
    face_encoding = models.TextField(blank=True)  # 얼굴 인코딩 데이터
    similarity_score = models.FloatField(default=0.0)  # 유사도 점수
    liveness_score = models.FloatField(default=0.0)  # 생체 감지 점수
    
    # 검증 상태
    status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    is_live_person = models.BooleanField(null=True, blank=True)  # 실제 사람 여부
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # 처리 정보
    processing_duration = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)

class VerificationLog(models.Model):
    """인증 이벤트 로그"""
    
    class EventType(models.TextChoices):
        SESSION_CREATED = 'session_created', '세션 생성'
        PHONE_SENT = 'phone_sent', 'SMS 발송'
        PHONE_VERIFIED = 'phone_verified', '휴대폰 인증 완료'
        EMAIL_SENT = 'email_sent', '이메일 발송'
        EMAIL_VERIFIED = 'email_verified', '이메일 인증 완료'
        ID_CARD_UPLOADED = 'id_card_uploaded', '신분증 업로드'
        ID_CARD_VERIFIED = 'id_card_verified', '신분증 인증 완료'
        FACE_UPLOADED = 'face_uploaded', '얼굴 사진 업로드'
        FACE_VERIFIED = 'face_verified', '얼굴 인증 완료'
        VERIFICATION_COMPLETED = 'verification_completed', '인증 완료'
        VERIFICATION_FAILED = 'verification_failed', '인증 실패'
    
    session = models.ForeignKey(VerificationSession, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    
    # 이벤트 상세 정보
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # 요청 정보
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'event_type']),
            models.Index(fields=['created_at']),
        ]
```

## 서비스 클래스 구현

### 1. SMS 인증 서비스

```python
# verification/services/sms_service.py
from twilio.rest import Client
from django.conf import settings
from django.core.cache import cache
import random
import string
from typing import Dict, Any

class SMSService:
    """SMS 인증 서비스"""
    
    def __init__(self):
        self.client = Client(
            settings.VERIFICATION_SETTINGS['TWILIO_ACCOUNT_SID'],
            settings.VERIFICATION_SETTINGS['TWILIO_AUTH_TOKEN']
        )
        self.from_number = settings.VERIFICATION_SETTINGS['TWILIO_PHONE_NUMBER']
    
    def generate_verification_code(self, length: int = 6) -> str:
        """인증코드 생성"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_sms(self, phone_number: str, verification_code: str) -> Dict[str, Any]:
        """SMS 인증코드 발송"""
        try:
            message_body = f"[본인인증] 인증번호는 {verification_code}입니다. 10분 내에 입력해주세요."
            
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=phone_number
            )
            
            return {
                'success': True,
                'sms_sid': message.sid,
                'status': message.status,
                'message': 'SMS sent successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to send SMS'
            }
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """휴대폰 번호 유효성 검사"""
        import re
        # 한국 휴대폰 번호 패턴
        pattern = r'^(\+82|0)1[0-9]{1}[0-9]{3,4}[0-9]{4}$'
        return bool(re.match(pattern, phone_number.replace('-', '').replace(' ', '')))
    
    def normalize_phone_number(self, phone_number: str) -> str:
        """휴대폰 번호 정규화"""
        # 공백, 하이픈 제거
        normalized = phone_number.replace('-', '').replace(' ', '')
        
        # +82로 시작하는 경우 그대로 반환
        if normalized.startswith('+82'):
            return normalized
        
        # 0으로 시작하는 경우 +82로 변환
        if normalized.startswith('0'):
            return '+82' + normalized[1:]
        
        # 그 외의 경우 +82를 앞에 붙임
        return '+82' + normalized
    
    def check_rate_limit(self, phone_number: str) -> bool:
        """SMS 발송 횟수 제한 확인"""
        cache_key = f"sms_rate_limit:{phone_number}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= 5:  # 시간당 5회 제한
            return False
        
        cache.set(cache_key, current_count + 1, 3600)  # 1시간 유지
        return True

class EmailService:
    """이메일 인증 서비스"""
    
    def __init__(self):
        self.from_email = settings.VERIFICATION_SETTINGS['EMAIL_HOST_USER']
    
    def generate_verification_code(self, length: int = 6) -> str:
        """인증코드 생성"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_email(self, email: str, verification_code: str, verification_token: str) -> Dict[str, Any]:
        """이메일 인증코드 발송"""
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            
            subject = '[본인인증] 이메일 인증번호'
            
            # HTML 이메일 템플릿 렌더링
            html_message = render_to_string('verification/email_verification.html', {
                'verification_code': verification_code,
                'verification_token': verification_token,
                'expires_minutes': settings.VERIFICATION_SETTINGS['VERIFICATION_EXPIRES_MINUTES']
            })
            
            plain_message = f"""
            본인인증 이메일 인증번호: {verification_code}
            
            위 인증번호를 입력하여 이메일 인증을 완료해주세요.
            인증번호는 {settings.VERIFICATION_SETTINGS['VERIFICATION_EXPIRES_MINUTES']}분 후에 만료됩니다.
            
            본인이 요청하지 않은 인증이라면 이 이메일을 무시해주세요.
            """
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False
            )
            
            return {
                'success': True,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to send email'
            }
    
    def validate_email(self, email: str) -> bool:
        """이메일 주소 유효성 검사"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def check_rate_limit(self, email: str) -> bool:
        """이메일 발송 횟수 제한 확인"""
        cache_key = f"email_rate_limit:{email}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= 3:  # 시간당 3회 제한
            return False
        
        cache.set(cache_key, current_count + 1, 3600)  # 1시간 유지
        return True

class OCRService:
    """신분증 OCR 서비스"""
    
    def __init__(self):
        self.provider = settings.VERIFICATION_SETTINGS['OCR_PROVIDER']
    
    def extract_id_card_data(self, image_path: str, id_card_type: str) -> Dict[str, Any]:
        """신분증에서 텍스트 추출"""
        
        if self.provider == 'easyocr':
            return self._extract_with_easyocr(image_path, id_card_type)
        elif self.provider == 'naver_clova':
            return self._extract_with_naver_clova(image_path, id_card_type)
        else:
            return self._extract_with_tesseract(image_path, id_card_type)
    
    def _extract_with_easyocr(self, image_path: str, id_card_type: str) -> Dict[str, Any]:
        """EasyOCR을 사용한 텍스트 추출"""
        try:
            import easyocr
            
            reader = easyocr.Reader(['ko', 'en'])
            results = reader.readtext(image_path)
            
            extracted_text = []
            confidence_scores = []
            
            for (bbox, text, confidence) in results:
                extracted_text.append(text)
                confidence_scores.append(confidence)
            
            # 신분증 타입별 데이터 파싱
            parsed_data = self._parse_id_card_data(extracted_text, id_card_type)
            
            return {
                'success': True,
                'extracted_text': extracted_text,
                'parsed_data': parsed_data,
                'confidence_score': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                'raw_results': results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'OCR processing failed'
            }
    
    def _extract_with_naver_clova(self, image_path: str, id_card_type: str) -> Dict[str, Any]:
        """네이버 클로바 OCR을 사용한 텍스트 추출"""
        try:
            import requests
            import json
            
            api_url = settings.VERIFICATION_SETTINGS['NAVER_CLOVA_API_URL']
            secret_key = settings.VERIFICATION_SETTINGS['NAVER_CLOVA_SECRET_KEY']
            
            with open(image_path, 'rb') as f:
                files = {'file': f}
                headers = {'X-OCR-SECRET': secret_key}
                
                # 요청 메시지 구성
                request_json = {
                    'version': 'V1',
                    'requestId': str(uuid.uuid4()),
                    'timestamp': int(time.time() * 1000),
                    'lang': 'ko',
                    'images': [{
                        'format': 'jpg',
                        'name': 'id_card'
                    }]
                }
                
                data = {'message': json.dumps(request_json)}
                
                response = requests.post(api_url, files=files, data=data, headers=headers)
                result = response.json()
                
                if response.status_code == 200:
                    # 클로바 OCR 결과 파싱
                    extracted_text = []
                    confidence_scores = []
                    
                    for field in result['images'][0]['fields']:
                        extracted_text.append(field['inferText'])
                        confidence_scores.append(field['inferConfidence'])
                    
                    parsed_data = self._parse_id_card_data(extracted_text, id_card_type)
                    
                    return {
                        'success': True,
                        'extracted_text': extracted_text,
                        'parsed_data': parsed_data,
                        'confidence_score': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                        'raw_results': result
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Clova OCR API error',
                        'message': result.get('message', 'Unknown error')
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Naver Clova OCR processing failed'
            }
    
    def _parse_id_card_data(self, extracted_text: list, id_card_type: str) -> Dict[str, Any]:
        """추출된 텍스트에서 개인정보 파싱"""
        import re
        
        parsed_data = {
            'name': None,
            'birth_date': None,
            'id_number': None,
            'address': None,
            'issue_date': None
        }
        
        text_string = ' '.join(extracted_text)
        
        # 이름 추출 (한글 2-4글자)
        name_pattern = r'[가-힣]{2,4}'
        name_matches = re.findall(name_pattern, text_string)
        if name_matches:
            # 주소, 발급일 등이 아닌 이름으로 추정되는 항목 선택
            for name in name_matches:
                if name not in ['주민등록증', '운전면허증', '대한민국']:
                    parsed_data['name'] = name
                    break
        
        # 생년월일 추출 (YYMMDD 또는 YYYY-MM-DD 형식)
        birth_patterns = [
            r'(\d{2})(\d{2})(\d{2})',  # YYMMDD
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{4})\.(\d{2})\.(\d{2})'  # YYYY.MM.DD
        ]
        
        for pattern in birth_patterns:
            birth_match = re.search(pattern, text_string)
            if birth_match:
                parsed_data['birth_date'] = birth_match.group()
                break
        
        # 주민등록번호 또는 외국인등록번호 추출
        id_number_pattern = r'\d{6}-\d{7}'
        id_number_match = re.search(id_number_pattern, text_string)
        if id_number_match:
            parsed_data['id_number'] = id_number_match.group()
        
        return parsed_data
    
    def validate_id_card_image(self, image_path: str) -> Dict[str, Any]:
        """신분증 이미지 유효성 검사"""
        try:
            from PIL import Image
            import cv2
            import numpy as np
            
            # 이미지 로드
            img = cv2.imread(image_path)
            if img is None:
                return {'valid': False, 'error': 'Invalid image file'}
            
            # 이미지 크기 확인
            height, width = img.shape[:2]
            if width < 300 or height < 200:
                return {'valid': False, 'error': 'Image too small'}
            
            # 이미지 품질 확인 (블러 검사)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if blur_score < 100:  # 임계값 조정 가능
                return {'valid': False, 'error': 'Image too blurry'}
            
            # 밝기 확인
            brightness = np.mean(gray)
            if brightness < 50 or brightness > 200:
                return {'valid': False, 'error': 'Poor lighting conditions'}
            
            return {
                'valid': True,
                'width': width,
                'height': height,
                'blur_score': blur_score,
                'brightness': brightness
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

class FaceRecognitionService:
    """얼굴 인식 서비스"""
    
    def __init__(self):
        self.similarity_threshold = 0.6  # 유사도 임계값
        self.liveness_threshold = 0.7  # 생체 감지 임계값
    
    def compare_faces(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """두 얼굴 이미지 비교"""
        try:
            import face_recognition
            
            # 이미지 로드 및 얼굴 인코딩
            image1 = face_recognition.load_image_file(image1_path)
            image2 = face_recognition.load_image_file(image2_path)
            
            encodings1 = face_recognition.face_encodings(image1)
            encodings2 = face_recognition.face_encodings(image2)
            
            if len(encodings1) == 0:
                return {'success': False, 'error': 'No face found in first image'}
            
            if len(encodings2) == 0:
                return {'success': False, 'error': 'No face found in second image'}
            
            # 얼굴 비교
            face_distances = face_recognition.face_distance(encodings1, encodings2[0])
            similarity_score = 1 - face_distances[0]  # 거리를 유사도로 변환
            
            is_match = similarity_score >= self.similarity_threshold
            
            return {
                'success': True,
                'similarity_score': float(similarity_score),
                'is_match': is_match,
                'face_encoding1': encodings1[0].tolist(),
                'face_encoding2': encodings2[0].tolist()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Face comparison failed'
            }
    
    def detect_liveness(self, image_path: str) -> Dict[str, Any]:
        """생체 감지 (실제 사람인지 확인)"""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(image_path)
            if img is None:
                return {'success': False, 'error': 'Invalid image file'}
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 눈 깜빡임 검사를 위한 눈 검출
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, 1.1, 5)
            
            # 기본적인 생체 감지 점수 계산
            liveness_score = 0.0
            
            # 눈이 검출되면 점수 증가
            if len(eyes) >= 2:
                liveness_score += 0.4
            
            # 이미지 품질 기반 점수
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            if blur_score > 100:
                liveness_score += 0.3
            
            # 색상 정보 기반 점수 (흑백이 아닌 컬러 이미지)
            if len(img.shape) == 3:
                color_variance = np.var(img)
                if color_variance > 1000:
                    liveness_score += 0.3
            
            is_live = liveness_score >= self.liveness_threshold
            
            return {
                'success': True,
                'liveness_score': float(liveness_score),
                'is_live': is_live,
                'eyes_detected': len(eyes),
                'blur_score': float(blur_score)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Liveness detection failed'
            }
```

## Pydantic 스키마 정의

### 1. 요청/응답 스키마

```python
# verification/schemas.py
from ninja import Schema, File, UploadedFile
from pydantic import validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import re

# 기본 응답 스키마
class BaseResponse(Schema):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

# 인증 세션 관련 스키마
class CreateVerificationSessionSchema(Schema):
    """인증 세션 생성 요청"""
    phone_number: Optional[str] = None
    email: Optional[str] = None
    full_verification: bool = Field(default=True, description="전체 인증 단계 포함 여부")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v:
            # 한국 휴대폰 번호 패턴 검증
            pattern = r'^(\+82|0)1[0-9]{1}[0-9]{3,4}[0-9]{4}$'
            if not re.match(pattern, v.replace('-', '').replace(' ', '')):
                raise ValueError('Invalid phone number format')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError('Invalid email format')
        return v

class VerificationSessionResponse(Schema):
    """인증 세션 응답"""
    session_id: str
    session_key: str
    status: str
    current_step: int
    max_step: int
    created_at: datetime
    expires_at: datetime

# 휴대폰 인증 관련 스키마
class SendSMSRequest(Schema):
    """SMS 발송 요청"""
    session_key: str
    phone_number: str
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        pattern = r'^(\+82|0)1[0-9]{1}[0-9]{3,4}[0-9]{4}$'
        normalized = v.replace('-', '').replace(' ', '')
        if not re.match(pattern, normalized):
            raise ValueError('Invalid phone number format')
        return normalized

class VerifyPhoneRequest(Schema):
    """휴대폰 인증 확인 요청"""
    session_key: str
    phone_number: str
    verification_code: str
    
    @validator('verification_code')
    def validate_code(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('Verification code must be 6 digits')
        return v

class PhoneVerificationResponse(Schema):
    """휴대폰 인증 응답"""
    verified: bool
    attempts_remaining: int
    expires_at: datetime
    can_resend: bool
    next_resend_at: Optional[datetime] = None

# 이메일 인증 관련 스키마
class SendEmailRequest(Schema):
    """이메일 발송 요청"""
    session_key: str
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v

class VerifyEmailRequest(Schema):
    """이메일 인증 확인 요청"""
    session_key: str
    email: str
    verification_code: str
    
    @validator('verification_code')
    def validate_code(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('Verification code must be 6 digits')
        return v

class EmailVerificationResponse(Schema):
    """이메일 인증 응답"""
    verified: bool
    attempts_remaining: int
    expires_at: datetime
    can_resend: bool

# 신분증 인증 관련 스키마
class IDCardUploadRequest(Schema):
    """신분증 업로드 요청"""
    session_key: str
    id_card_type: str = Field(description="resident_card, driver_license, passport")
    
    @validator('id_card_type')
    def validate_id_card_type(cls, v):
        allowed_types = ['resident_card', 'driver_license', 'passport']
        if v not in allowed_types:
            raise ValueError(f'ID card type must be one of: {", ".join(allowed_types)}')
        return v

class IDCardVerificationResponse(Schema):
    """신분증 인증 응답"""
    verification_id: str
    status: str
    confidence_score: float
    extracted_data: Dict[str, Any]
    verification_details: Dict[str, Any]
    processing_duration: Optional[float] = None

class IDCardStatusResponse(Schema):
    """신분증 처리 상태 응답"""
    status: str
    confidence_score: float
    name_match: Optional[bool] = None
    birth_date_match: Optional[bool] = None
    error_message: Optional[str] = None

# 얼굴 인증 관련 스키마
class FaceUploadRequest(Schema):
    """얼굴 이미지 업로드 요청"""
    session_key: str

class FaceVerificationResponse(Schema):
    """얼굴 인증 응답"""
    verification_id: str
    status: str
    similarity_score: float
    liveness_score: float
    is_live_person: Optional[bool] = None
    processing_duration: Optional[float] = None

# 인증 진행 상황 스키마
class VerificationProgressResponse(Schema):
    """인증 진행 상황 응답"""
    session_id: str
    status: str
    current_step: int
    max_step: int
    completed_steps: List[str]
    verification_score: float
    
    # 각 단계별 상태
    phone_verified: bool
    email_verified: bool
    id_card_verified: bool
    face_verified: bool
    
    # 만료 정보
    expires_at: datetime
    is_expired: bool

# 인증 완료 스키마
class VerificationCompletionResponse(Schema):
    """인증 완료 응답"""
    session_id: str
    verification_token: str
    verified_at: datetime
    verification_score: float
    personal_data: Dict[str, Any]
    
    # 검증된 정보
    verified_phone: Optional[str] = None
    verified_email: Optional[str] = None
    verified_name: Optional[str] = None
    verified_birth_date: Optional[str] = None

# 통계 및 로그 스키마
class VerificationStatsResponse(Schema):
    """인증 통계 응답"""
    total_sessions: int
    completed_sessions: int
    success_rate: float
    average_completion_time: float
    
    # 단계별 통계
    phone_success_rate: float
    email_success_rate: float
    id_card_success_rate: float
    face_success_rate: float
    
    # 최근 활동
    recent_completions: int
    recent_failures: int

class VerificationLogResponse(Schema):
    """인증 로그 응답"""
    event_type: str
    description: str
    created_at: datetime
    ip_address: Optional[str] = None
    metadata: Dict[str, Any]

# 에러 응답 스키마
class ValidationErrorResponse(Schema):
    """유효성 검사 에러 응답"""
    success: bool = False
    message: str = "Validation failed"
    errors: List[Dict[str, str]]
    field_errors: Dict[str, List[str]]

class RateLimitErrorResponse(Schema):
    """요청 제한 에러 응답"""
    success: bool = False
    message: str = "Rate limit exceeded"
    retry_after: int  # 재시도 가능한 시간(초)
    limit_type: str  # sms, email 등

class SessionExpiredErrorResponse(Schema):
    """세션 만료 에러 응답"""
    success: bool = False
    message: str = "Verification session expired"
    expired_at: datetime
    new_session_required: bool = True

# 필터 및 페이지네이션 스키마
class VerificationFilterSchema(Schema):
    """인증 기록 필터"""
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

class PaginationSchema(Schema):
    """페이지네이션 파라미터"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(Schema):
    """페이지네이션 응답"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
```

## API 엔드포인트 구현

### 1. 메인 API 라우터

```python
# verification/api.py
from ninja import Router, File, UploadedFile
from ninja.pagination import paginate, PageNumberPagination
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from typing import List
import uuid
import os
import time

from .models import (
    VerificationSession, PhoneVerification, EmailVerification,
    IDCardVerification, FaceVerification, VerificationLog
)
from .services.sms_service import SMSService
from .services.email_service import EmailService
from .services.ocr_service import OCRService
from .services.face_service import FaceRecognitionService
from .schemas import *
from .tasks import process_id_card_verification, process_face_verification

router = Router()

# 서비스 인스턴스
sms_service = SMSService()
email_service = EmailService()
ocr_service = OCRService()
face_service = FaceRecognitionService()

@router.post("/session/create", response=BaseResponse)
def create_verification_session(request, payload: CreateVerificationSessionSchema):
    """인증 세션 생성"""
    
    try:
        # 세션 키 생성
        session_key = str(uuid.uuid4())
        
        # 인증 세션 생성
        session = VerificationSession.objects.create(
            session_key=session_key,
            phone_number=payload.phone_number or '',
            email=payload.email or '',
            max_step=4 if payload.full_verification else 2,
            current_step=1
        )
        
        # 로그 기록
        VerificationLog.objects.create(
            session=session,
            event_type=VerificationLog.EventType.SESSION_CREATED,
            description="새로운 인증 세션이 생성되었습니다",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'has_phone': bool(payload.phone_number),
                'has_email': bool(payload.email),
                'full_verification': payload.full_verification
            }
        )
        
        return BaseResponse(
            success=True,
            message="Verification session created successfully",
            data={
                'session_id': str(session.id),
                'session_key': session.session_key,
                'status': session.status,
                'current_step': session.current_step,
                'max_step': session.max_step,
                'expires_at': session.expires_at.isoformat()
            }
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            message="Failed to create verification session",
            errors=[str(e)]
        )

@router.get("/session/{session_key}/status", response=VerificationProgressResponse)
def get_verification_status(request, session_key: str):
    """인증 진행 상황 조회"""
    
    session = get_object_or_404(VerificationSession, session_key=session_key)
    
    # 완료된 단계 확인
    completed_steps = []
    phone_verified = session.phone_verifications.filter(is_verified=True).exists()
    email_verified = session.email_verifications.filter(is_verified=True).exists()
    id_card_verified = session.id_card_verifications.filter(status='success').exists()
    face_verified = session.face_verifications.filter(status='success').exists()
    
    if phone_verified:
        completed_steps.append('phone')
    if email_verified:
        completed_steps.append('email')
    if id_card_verified:
        completed_steps.append('id_card')
    if face_verified:
        completed_steps.append('face')
    
    return VerificationProgressResponse(
        session_id=str(session.id),
        status=session.status,
        current_step=session.current_step,
        max_step=session.max_step,
        completed_steps=completed_steps,
        verification_score=session.verification_score,
        phone_verified=phone_verified,
        email_verified=email_verified,
        id_card_verified=id_card_verified,
        face_verified=face_verified,
        expires_at=session.expires_at,
        is_expired=session.is_expired()
    )

# 휴대폰 인증 엔드포인트
@router.post("/phone/send", response=BaseResponse)
def send_phone_verification(request, payload: SendSMSRequest):
    """휴대폰 인증번호 발송"""
    
    session = get_object_or_404(VerificationSession, session_key=payload.session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 전화번호 정규화
    normalized_phone = sms_service.normalize_phone_number(payload.phone_number)
    
    # 전화번호 유효성 검사
    if not sms_service.validate_phone_number(normalized_phone):
        return BaseResponse(
            success=False,
            message="Invalid phone number format",
            errors=["INVALID_PHONE_NUMBER"]
        )
    
    # 요청 제한 확인
    if not sms_service.check_rate_limit(normalized_phone):
        return BaseResponse(
            success=False,
            message="SMS rate limit exceeded",
            errors=["RATE_LIMIT_EXCEEDED"]
        )
    
    # 최근 발송 내역 확인
    recent_verification = session.phone_verifications.filter(
        phone_number=normalized_phone
    ).order_by('-created_at').first()
    
    if recent_verification and not recent_verification.can_resend():
        return BaseResponse(
            success=False,
            message="Please wait before requesting another SMS",
            errors=["SMS_COOLDOWN_ACTIVE"]
        )
    
    try:
        # 인증번호 생성
        verification_code = sms_service.generate_verification_code()
        
        # SMS 발송
        sms_result = sms_service.send_verification_sms(normalized_phone, verification_code)
        
        if sms_result['success']:
            # 인증 레코드 생성
            phone_verification = PhoneVerification.objects.create(
                session=session,
                phone_number=normalized_phone,
                verification_code=verification_code,
                sms_sid=sms_result.get('sms_sid', ''),
                sms_status=sms_result.get('status', '')
            )
            
            # 세션 정보 업데이트
            session.phone_number = normalized_phone
            session.save()
            
            # 로그 기록
            VerificationLog.objects.create(
                session=session,
                event_type=VerificationLog.EventType.PHONE_SENT,
                description=f"SMS 인증번호를 {normalized_phone}로 발송했습니다",
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'phone_number': normalized_phone, 'sms_sid': sms_result.get('sms_sid')}
            )
            
            return BaseResponse(
                success=True,
                message="SMS verification code sent successfully",
                data={
                    'phone_number': normalized_phone,
                    'expires_at': phone_verification.expires_at.isoformat(),
                    'attempts_remaining': phone_verification.max_attempts
                }
            )
        else:
            return BaseResponse(
                success=False,
                message="Failed to send SMS",
                errors=[sms_result.get('error', 'Unknown error')]
            )
            
    except Exception as e:
        return BaseResponse(
            success=False,
            message="SMS sending failed",
            errors=[str(e)]
        )

@router.post("/phone/verify", response=BaseResponse)
def verify_phone_code(request, payload: VerifyPhoneRequest):
    """휴대폰 인증번호 확인"""
    
    session = get_object_or_404(VerificationSession, session_key=payload.session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 최근 인증 요청 조회
    phone_verification = session.phone_verifications.filter(
        phone_number=payload.phone_number,
        is_verified=False
    ).order_by('-created_at').first()
    
    if not phone_verification:
        return BaseResponse(
            success=False,
            message="No pending phone verification found",
            errors=["NO_PENDING_VERIFICATION"]
        )
    
    if phone_verification.is_expired():
        return BaseResponse(
            success=False,
            message="Verification code expired",
            errors=["CODE_EXPIRED"]
        )
    
    if phone_verification.attempts >= phone_verification.max_attempts:
        return BaseResponse(
            success=False,
            message="Maximum attempts exceeded",
            errors=["MAX_ATTEMPTS_EXCEEDED"]
        )
    
    # 인증번호 확인
    phone_verification.attempts += 1
    
    if phone_verification.verification_code == payload.verification_code:
        # 인증 성공
        phone_verification.is_verified = True
        phone_verification.verified_at = timezone.now()
        phone_verification.save()
        
        # 세션 상태 업데이트
        session.status = VerificationSession.VerificationStatus.PHONE_VERIFIED
        session.current_step = min(session.current_step + 1, session.max_step)
        session.verification_score += 25.0  # 각 단계당 25점
        session.save()
        
        # 로그 기록
        VerificationLog.objects.create(
            session=session,
            event_type=VerificationLog.EventType.PHONE_VERIFIED,
            description="휴대폰 인증이 완료되었습니다",
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'phone_number': payload.phone_number}
        )
        
        return BaseResponse(
            success=True,
            message="Phone verification completed successfully",
            data={
                'verified': True,
                'current_step': session.current_step,
                'next_step': 'email' if session.current_step <= session.max_step else 'completed'
            }
        )
    else:
        # 인증 실패
        phone_verification.save()
        
        return BaseResponse(
            success=False,
            message="Invalid verification code",
            errors=["INVALID_CODE"],
            data={
                'attempts_remaining': phone_verification.max_attempts - phone_verification.attempts
            }
        )

# 이메일 인증 엔드포인트
@router.post("/email/send", response=BaseResponse)
def send_email_verification(request, payload: SendEmailRequest):
    """이메일 인증번호 발송"""
    
    session = get_object_or_404(VerificationSession, session_key=payload.session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 이메일 유효성 검사
    if not email_service.validate_email(payload.email):
        return BaseResponse(
            success=False,
            message="Invalid email format",
            errors=["INVALID_EMAIL"]
        )
    
    # 요청 제한 확인
    if not email_service.check_rate_limit(payload.email):
        return BaseResponse(
            success=False,
            message="Email rate limit exceeded",
            errors=["RATE_LIMIT_EXCEEDED"]
        )
    
    try:
        # 인증번호 및 토큰 생성
        verification_code = email_service.generate_verification_code()
        verification_token = uuid.uuid4()
        
        # 이메일 발송
        email_result = email_service.send_verification_email(
            payload.email, verification_code, str(verification_token)
        )
        
        if email_result['success']:
            # 인증 레코드 생성
            email_verification = EmailVerification.objects.create(
                session=session,
                email=payload.email,
                verification_code=verification_code,
                verification_token=verification_token
            )
            
            # 세션 정보 업데이트
            session.email = payload.email
            session.save()
            
            # 로그 기록
            VerificationLog.objects.create(
                session=session,
                event_type=VerificationLog.EventType.EMAIL_SENT,
                description=f"이메일 인증번호를 {payload.email}로 발송했습니다",
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'email': payload.email}
            )
            
            return BaseResponse(
                success=True,
                message="Email verification code sent successfully",
                data={
                    'email': payload.email,
                    'expires_at': email_verification.expires_at.isoformat(),
                    'attempts_remaining': email_verification.max_attempts
                }
            )
        else:
            return BaseResponse(
                success=False,
                message="Failed to send email",
                errors=[email_result.get('error', 'Unknown error')]
            )
            
    except Exception as e:
        return BaseResponse(
            success=False,
            message="Email sending failed",
            errors=[str(e)]
        )

@router.post("/email/verify", response=BaseResponse)
def verify_email_code(request, payload: VerifyEmailRequest):
    """이메일 인증번호 확인"""
    
    session = get_object_or_404(VerificationSession, session_key=payload.session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 최근 인증 요청 조회
    email_verification = session.email_verifications.filter(
        email=payload.email,
        is_verified=False
    ).order_by('-created_at').first()
    
    if not email_verification:
        return BaseResponse(
            success=False,
            message="No pending email verification found",
            errors=["NO_PENDING_VERIFICATION"]
        )
    
    if email_verification.is_expired():
        return BaseResponse(
            success=False,
            message="Verification code expired",
            errors=["CODE_EXPIRED"]
        )
    
    if email_verification.attempts >= email_verification.max_attempts:
        return BaseResponse(
            success=False,
            message="Maximum attempts exceeded",
            errors=["MAX_ATTEMPTS_EXCEEDED"]
        )
    
    # 인증번호 확인
    email_verification.attempts += 1
    
    if email_verification.verification_code == payload.verification_code:
        # 인증 성공
        email_verification.is_verified = True
        email_verification.verified_at = timezone.now()
        email_verification.save()
        
        # 세션 상태 업데이트
        session.status = VerificationSession.VerificationStatus.EMAIL_VERIFIED
        session.current_step = min(session.current_step + 1, session.max_step)
        session.verification_score += 25.0
        session.save()
        
        # 로그 기록
        VerificationLog.objects.create(
            session=session,
            event_type=VerificationLog.EventType.EMAIL_VERIFIED,
            description="이메일 인증이 완료되었습니다",
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'email': payload.email}
        )
        
        return BaseResponse(
            success=True,
            message="Email verification completed successfully",
            data={
                'verified': True,
                'current_step': session.current_step,
                'next_step': 'id_card' if session.current_step <= session.max_step else 'completed'
            }
        )
    else:
        # 인증 실패
        email_verification.save()
        
        return BaseResponse(
            success=False,
            message="Invalid verification code",
            errors=["INVALID_CODE"],
            data={
                'attempts_remaining': email_verification.max_attempts - email_verification.attempts
            }
        )

# 신분증 인증 엔드포인트
@router.post("/id-card/upload", response=BaseResponse)
def upload_id_card(
    request,
    session_key: str,
    id_card_type: str,
    front_image: UploadedFile = File(...),
    back_image: UploadedFile = File(None)
):
    """신분증 이미지 업로드"""
    
    session = get_object_or_404(VerificationSession, session_key=session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 신분증 타입 유효성 검사
    allowed_types = ['resident_card', 'driver_license', 'passport']
    if id_card_type not in allowed_types:
        return BaseResponse(
            success=False,
            message="Invalid ID card type",
            errors=["INVALID_ID_CARD_TYPE"]
        )
    
    try:
        # 파일 저장
        front_path = f"id_cards/front/{session.id}_{int(time.time())}_front.jpg"
        back_path = None
        
        with open(f"media/{front_path}", 'wb+') as destination:
            for chunk in front_image.chunks():
                destination.write(chunk)
        
        if back_image:
            back_path = f"id_cards/back/{session.id}_{int(time.time())}_back.jpg"
            with open(f"media/{back_path}", 'wb+') as destination:
                for chunk in back_image.chunks():
                    destination.write(chunk)
        
        # 신분증 인증 레코드 생성
        id_card_verification = IDCardVerification.objects.create(
            session=session,
            id_card_type=id_card_type,
            front_image=front_path,
            back_image=back_path,
            status=IDCardVerification.VerificationStatus.PENDING
        )
        
        # 비동기 처리를 위해 Celery 태스크 실행
        process_id_card_verification.delay(str(id_card_verification.id))
        
        # 로그 기록
        VerificationLog.objects.create(
            session=session,
            event_type=VerificationLog.EventType.ID_CARD_UPLOADED,
            description="신분증 이미지가 업로드되었습니다",
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                'id_card_type': id_card_type,
                'has_back_image': bool(back_image)
            }
        )
        
        return BaseResponse(
            success=True,
            message="ID card uploaded successfully",
            data={
                'verification_id': str(id_card_verification.id),
                'status': id_card_verification.status,
                'estimated_processing_time': '30-60 seconds'
            }
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            message="ID card upload failed",
            errors=[str(e)]
        )

@router.get("/id-card/{verification_id}/status", response=IDCardStatusResponse)
def get_id_card_status(request, verification_id: str):
    """신분증 처리 상태 조회"""
    
    id_card_verification = get_object_or_404(IDCardVerification, id=verification_id)
    
    return IDCardStatusResponse(
        status=id_card_verification.status,
        confidence_score=id_card_verification.confidence_score,
        name_match=id_card_verification.name_match,
        birth_date_match=id_card_verification.birth_date_match,
        error_message=id_card_verification.error_message
    )

# 얼굴 인증 엔드포인트
@router.post("/face/upload", response=BaseResponse)
def upload_face_image(
    request,
    session_key: str,
    selfie_image: UploadedFile = File(...)
):
    """얼굴 이미지 업로드"""
    
    session = get_object_or_404(VerificationSession, session_key=session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    try:
        # 파일 저장
        selfie_path = f"face_verification/{session.id}_{int(time.time())}_selfie.jpg"
        
        with open(f"media/{selfie_path}", 'wb+') as destination:
            for chunk in selfie_image.chunks():
                destination.write(chunk)
        
        # 얼굴 인증 레코드 생성
        face_verification = FaceVerification.objects.create(
            session=session,
            selfie_image=selfie_path,
            status=FaceVerification.VerificationStatus.PENDING
        )
        
        # 비동기 처리를 위해 Celery 태스크 실행
        process_face_verification.delay(str(face_verification.id))
        
        # 로그 기록
        VerificationLog.objects.create(
            session=session,
            event_type=VerificationLog.EventType.FACE_UPLOADED,
            description="얼굴 이미지가 업로드되었습니다",
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'selfie_uploaded': True}
        )
        
        return BaseResponse(
            success=True,
            message="Face image uploaded successfully",
            data={
                'verification_id': str(face_verification.id),
                'status': face_verification.status,
                'estimated_processing_time': '10-30 seconds'
            }
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            message="Face image upload failed",
            errors=[str(e)]
        )

# 인증 완료 확인
@router.post("/complete/{session_key}", response=BaseResponse)
@transaction.atomic
def complete_verification(request, session_key: str):
    """본인인증 완료 처리"""
    
    session = get_object_or_404(VerificationSession, session_key=session_key)
    
    if session.is_expired():
        return BaseResponse(
            success=False,
            message="Verification session expired",
            errors=["SESSION_EXPIRED"]
        )
    
    # 모든 단계 완료 확인
    phone_verified = session.phone_verifications.filter(is_verified=True).exists()
    email_verified = session.email_verifications.filter(is_verified=True).exists()
    id_card_verified = session.id_card_verifications.filter(status='success').exists()
    face_verified = session.face_verifications.filter(status='success').exists()
    
    required_verifications = [phone_verified, email_verified]
    if session.max_step >= 3:
        required_verifications.append(id_card_verified)
    if session.max_step >= 4:
        required_verifications.append(face_verified)
    
    if not all(required_verifications):
        return BaseResponse(
            success=False,
            message="Not all verification steps completed",
            errors=["INCOMPLETE_VERIFICATION"]
        )
    
    # 인증 완료 처리
    session.status = VerificationSession.VerificationStatus.COMPLETED
    session.verified_at = timezone.now()
    session.verification_score = 100.0
    session.save()
    
    # 완료 토큰 생성
    verification_token = str(uuid.uuid4())
    cache.set(f"verification_token:{verification_token}", str(session.id), 3600 * 24)  # 24시간 유효
    
    # 검증된 개인정보 수집
    personal_data = {}
    
    # 신분증에서 추출된 정보
    id_card = session.id_card_verifications.filter(status='success').first()
    if id_card:
        personal_data.update(id_card.extracted_data)
    
    # 암호화하여 저장
    session.encrypt_personal_data(personal_data)
    session.save()
    
    # 로그 기록
    VerificationLog.objects.create(
        session=session,
        event_type=VerificationLog.EventType.VERIFICATION_COMPLETED,
        description="본인인증이 완료되었습니다",
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'verification_score': session.verification_score,
            'steps_completed': session.current_step
        }
    )
    
    return BaseResponse(
        success=True,
        message="Identity verification completed successfully",
        data={
            'session_id': str(session.id),
            'verification_token': verification_token,
            'verified_at': session.verified_at.isoformat(),
            'verification_score': session.verification_score,
            'verified_phone': session.phone_number,
            'verified_email': session.email,
            'verified_name': personal_data.get('name'),
            'verified_birth_date': personal_data.get('birth_date')
        }
    )
```

## 비동기 태스크 처리

### 1. Celery 태스크 구현

```python
# verification/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import datetime
import time

@shared_task
def process_id_card_verification(verification_id: str):
    """신분증 인증 비동기 처리"""
    
    from .models import IDCardVerification, VerificationSession, VerificationLog
    from .services.ocr_service import OCRService
    
    try:
        verification = IDCardVerification.objects.get(id=verification_id)
        verification.status = IDCardVerification.VerificationStatus.PROCESSING
        verification.save()
        
        start_time = time.time()
        ocr_service = OCRService()
        
        # 이미지 유효성 검사
        validation_result = ocr_service.validate_id_card_image(verification.front_image.path)
        
        if not validation_result['valid']:
            verification.status = IDCardVerification.VerificationStatus.FAILED
            verification.error_message = validation_result['error']
            verification.processed_at = timezone.now()
            verification.processing_duration = time.time() - start_time
            verification.save()
            return
        
        # OCR 처리
        ocr_result = ocr_service.extract_id_card_data(
            verification.front_image.path,
            verification.id_card_type
        )
        
        if ocr_result['success']:
            verification.extracted_data = ocr_result['parsed_data']
            verification.confidence_score = ocr_result['confidence_score']
            verification.verification_details = ocr_result
            
            # 신뢰도 확인
            if verification.confidence_score >= 0.8:
                verification.status = IDCardVerification.VerificationStatus.SUCCESS
                
                # 세션 상태 업데이트
                session = verification.session
                session.status = VerificationSession.VerificationStatus.ID_CARD_VERIFIED
                session.current_step = min(session.current_step + 1, session.max_step)
                session.verification_score += 25.0
                session.save()
                
                # 로그 기록
                VerificationLog.objects.create(
                    session=session,
                    event_type=VerificationLog.EventType.ID_CARD_VERIFIED,
                    description="신분증 인증이 완료되었습니다",
                    metadata={
                        'confidence_score': verification.confidence_score,
                        'extracted_name': ocr_result['parsed_data'].get('name')
                    }
                )
            else:
                verification.status = IDCardVerification.VerificationStatus.REJECTED
                verification.error_message = "OCR confidence score too low"
        else:
            verification.status = IDCardVerification.VerificationStatus.FAILED
            verification.error_message = ocr_result.get('error', 'OCR processing failed')
        
        verification.processed_at = timezone.now()
        verification.processing_duration = time.time() - start_time
        verification.save()
        
    except Exception as e:
        verification.status = IDCardVerification.VerificationStatus.FAILED
        verification.error_message = str(e)
        verification.processed_at = timezone.now()
        verification.save()

@shared_task
def process_face_verification(verification_id: str):
    """얼굴 인증 비동기 처리"""
    
    from .models import FaceVerification, VerificationSession, VerificationLog
    from .services.face_service import FaceRecognitionService
    
    try:
        verification = FaceVerification.objects.get(id=verification_id)
        verification.status = FaceVerification.VerificationStatus.PROCESSING
        verification.save()
        
        start_time = time.time()
        face_service = FaceRecognitionService()
        
        # 생체 감지
        liveness_result = face_service.detect_liveness(verification.selfie_image.path)
        
        if liveness_result['success']:
            verification.liveness_score = liveness_result['liveness_score']
            verification.is_live_person = liveness_result['is_live']
            
            if verification.is_live_person:
                verification.status = FaceVerification.VerificationStatus.SUCCESS
                
                # 세션 상태 업데이트
                session = verification.session
                session.status = VerificationSession.VerificationStatus.FACE_VERIFIED
                session.current_step = min(session.current_step + 1, session.max_step)
                session.verification_score += 25.0
                session.save()
                
                # 로그 기록
                VerificationLog.objects.create(
                    session=session,
                    event_type=VerificationLog.EventType.FACE_VERIFIED,
                    description="얼굴 인증이 완료되었습니다",
                    metadata={
                        'liveness_score': verification.liveness_score,
                        'is_live_person': verification.is_live_person
                    }
                )
            else:
                verification.status = FaceVerification.VerificationStatus.FAILED
                verification.error_message = "Liveness detection failed"
        else:
            verification.status = FaceVerification.VerificationStatus.FAILED
            verification.error_message = liveness_result.get('error', 'Face processing failed')
        
        verification.processed_at = timezone.now()
        verification.processing_duration = time.time() - start_time
        verification.save()
        
    except Exception as e:
        verification.status = FaceVerification.VerificationStatus.FAILED
        verification.error_message = str(e)
        verification.processed_at = timezone.now()
        verification.save()

@shared_task
def cleanup_expired_sessions():
    """만료된 인증 세션 정리"""
    
    from .models import VerificationSession
    
    expired_sessions = VerificationSession.objects.filter(
        expires_at__lt=timezone.now(),
        status__in=[
            VerificationSession.VerificationStatus.PENDING,
            VerificationSession.VerificationStatus.PHONE_VERIFIED,
            VerificationSession.VerificationStatus.EMAIL_VERIFIED,
        ]
    )
    
    count = 0
    for session in expired_sessions:
        session.status = VerificationSession.VerificationStatus.EXPIRED
        session.save()
        count += 1
    
    return f"Cleaned up {count} expired sessions"
```

## 프론트엔드 연동 예시

### 1. React 컴포넌트

{% raw %}
```jsx
// components/IdentityVerification.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const IdentityVerification = ({ onComplete }) => {
    const [session, setSession] = useState(null);
    const [currentStep, setCurrentStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // 단계별 상태
    const [phoneNumber, setPhoneNumber] = useState('');
    const [email, setEmail] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [selectedFiles, setSelectedFiles] = useState({});
    
    // API 클라이언트 설정
    const api = axios.create({
        baseURL: '/api/verification',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    // 인증 세션 생성
    const createSession = async () => {
        try {
            setLoading(true);
            const response = await api.post('/session/create', {
                phone_number: phoneNumber,
                email: email,
                full_verification: true
            });
            
            if (response.data.success) {
                setSession(response.data.data);
                setCurrentStep(1);
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('인증 세션 생성에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // SMS 발송
    const sendSMS = async () => {
        try {
            setLoading(true);
            const response = await api.post('/phone/send', {
                session_key: session.session_key,
                phone_number: phoneNumber
            });
            
            if (response.data.success) {
                alert('인증번호가 발송되었습니다.');
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('SMS 발송에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 휴대폰 인증 확인
    const verifyPhone = async () => {
        try {
            setLoading(true);
            const response = await api.post('/phone/verify', {
                session_key: session.session_key,
                phone_number: phoneNumber,
                verification_code: verificationCode
            });
            
            if (response.data.success) {
                setCurrentStep(2);
                setVerificationCode('');
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('휴대폰 인증에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 이메일 발송
    const sendEmail = async () => {
        try {
            setLoading(true);
            const response = await api.post('/email/send', {
                session_key: session.session_key,
                email: email
            });
            
            if (response.data.success) {
                alert('인증번호가 발송되었습니다.');
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('이메일 발송에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 이메일 인증 확인
    const verifyEmail = async () => {
        try {
            setLoading(true);
            const response = await api.post('/email/verify', {
                session_key: session.session_key,
                email: email,
                verification_code: verificationCode
            });
            
            if (response.data.success) {
                setCurrentStep(3);
                setVerificationCode('');
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('이메일 인증에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 신분증 업로드
    const uploadIDCard = async (idCardType) => {
        try {
            setLoading(true);
            const formData = new FormData();
            formData.append('session_key', session.session_key);
            formData.append('id_card_type', idCardType);
            formData.append('front_image', selectedFiles.front);
            if (selectedFiles.back) {
                formData.append('back_image', selectedFiles.back);
            }
            
            const response = await api.post('/id-card/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            
            if (response.data.success) {
                // 처리 상태 확인 시작
                checkIDCardStatus(response.data.data.verification_id);
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('신분증 업로드에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 신분증 처리 상태 확인
    const checkIDCardStatus = async (verificationId) => {
        const checkStatus = async () => {
            try {
                const response = await api.get(`/id-card/${verificationId}/status`);
                const status = response.data.status;
                
                if (status === 'success') {
                    setCurrentStep(4);
                    return;
                } else if (status === 'failed' || status === 'rejected') {
                    setError('신분증 인증에 실패했습니다.');
                    return;
                }
                
                // 처리 중이면 3초 후 다시 확인
                setTimeout(checkStatus, 3000);
            } catch (err) {
                setError('상태 확인 중 오류가 발생했습니다.');
            }
        };
        
        checkStatus();
    };
    
    // 얼굴 인증 업로드
    const uploadFaceImage = async () => {
        try {
            setLoading(true);
            const formData = new FormData();
            formData.append('session_key', session.session_key);
            formData.append('selfie_image', selectedFiles.selfie);
            
            const response = await api.post('/face/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            
            if (response.data.success) {
                // 처리 완료 후 최종 단계로
                setTimeout(() => {
                    completeVerification();
                }, 10000); // 10초 후 완료 처리
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('얼굴 인증 업로드에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 인증 완료
    const completeVerification = async () => {
        try {
            setLoading(true);
            const response = await api.post(`/complete/${session.session_key}`);
            
            if (response.data.success) {
                onComplete(response.data.data);
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError('인증 완료 처리에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };
    
    // 진행 단계 렌더링
    const renderStep = () => {
        switch (currentStep) {
            case 0:
                return (
                    <div className="step-container">
                        <h3>본인인증 시작</h3>
                        <div className="form-group">
                            <label>휴대폰 번호</label>
                            <input
                                type="tel"
                                value={phoneNumber}
                                onChange={(e) => setPhoneNumber(e.target.value)}
                                placeholder="010-0000-0000"
                            />
                        </div>
                        <div className="form-group">
                            <label>이메일 주소</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="example@email.com"
                            />
                        </div>
                        <button onClick={createSession} disabled={loading}>
                            인증 시작하기
                        </button>
                    </div>
                );
                
            case 1:
                return (
                    <div className="step-container">
                        <h3>1단계: 휴대폰 인증</h3>
                        <p>등록하신 휴대폰번호: {phoneNumber}</p>
                        <button onClick={sendSMS} disabled={loading}>
                            인증번호 발송
                        </button>
                        <div className="form-group">
                            <label>인증번호</label>
                            <input
                                type="text"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                                placeholder="6자리 숫자"
                                maxLength="6"
                            />
                        </div>
                        <button onClick={verifyPhone} disabled={loading || !verificationCode}>
                            인증 확인
                        </button>
                    </div>
                );
                
            case 2:
                return (
                    <div className="step-container">
                        <h3>2단계: 이메일 인증</h3>
                        <p>등록하신 이메일: {email}</p>
                        <button onClick={sendEmail} disabled={loading}>
                            인증번호 발송
                        </button>
                        <div className="form-group">
                            <label>인증번호</label>
                            <input
                                type="text"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                                placeholder="6자리 숫자"
                                maxLength="6"
                            />
                        </div>
                        <button onClick={verifyEmail} disabled={loading || !verificationCode}>
                            인증 확인
                        </button>
                    </div>
                );
                
            case 3:
                return (
                    <div className="step-container">
                        <h3>3단계: 신분증 인증</h3>
                        <div className="file-upload">
                            <label>신분증 앞면</label>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={(e) => setSelectedFiles({
                                    ...selectedFiles,
                                    front: e.target.files[0]
                                })}
                            />
                        </div>
                        <div className="file-upload">
                            <label>신분증 뒷면 (선택사항)</label>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={(e) => setSelectedFiles({
                                    ...selectedFiles,
                                    back: e.target.files[0]
                                })}
                            />
                        </div>
                        <button 
                            onClick={() => uploadIDCard('resident_card')} 
                            disabled={loading || !selectedFiles.front}
                        >
                            주민등록증 인증
                        </button>
                        <button 
                            onClick={() => uploadIDCard('driver_license')} 
                            disabled={loading || !selectedFiles.front}
                        >
                            운전면허증 인증
                        </button>
                    </div>
                );
                
            case 4:
                return (
                    <div className="step-container">
                        <h3>4단계: 얼굴 인증</h3>
                        <p>본인 얼굴이 선명하게 나온 셀피를 업로드해주세요.</p>
                        <div className="file-upload">
                            <label>셀피 이미지</label>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={(e) => setSelectedFiles({
                                    ...selectedFiles,
                                    selfie: e.target.files[0]
                                })}
                            />
                        </div>
                        <button 
                            onClick={uploadFaceImage} 
                            disabled={loading || !selectedFiles.selfie}
                        >
                            얼굴 인증하기
                        </button>
                    </div>
                );
                
            default:
                return (
                    <div className="step-container">
                        <h3>인증 완료</h3>
                        <p>본인인증이 성공적으로 완료되었습니다.</p>
                    </div>
                );
        }
    };
    
    return (
        <div className="identity-verification">
            <div className="progress-bar">
                <div className="progress" style={{ width: `${(currentStep / 4) * 100}%` }}></div>
            </div>
            
            {error && (
                <div className="error-message">
                    {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}
            
            {loading && (
                <div className="loading-overlay">
                    <div className="spinner"></div>
                    <p>처리 중입니다...</p>
                </div>
            )}
            
            {renderStep()}
        </div>
    );
};

export default IdentityVerification;
```
{% endraw %}

### 2. CSS 스타일링

```css
/* styles/IdentityVerification.css */
.identity-verification {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    font-family: 'Noto Sans KR', sans-serif;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background-color: #e0e0e0;
    border-radius: 4px;
    margin-bottom: 30px;
    overflow: hidden;
}

.progress {
    height: 100%;
    background: linear-gradient(90deg, #4CAF50, #45a049);
    transition: width 0.3s ease;
}

.step-container {
    background: white;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.step-container h3 {
    color: #333;
    margin-bottom: 20px;
    font-size: 24px;
    font-weight: 600;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #555;
}

.form-group input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s ease;
}

.form-group input:focus {
    outline: none;
    border-color: #4CAF50;
}

.file-upload {
    margin-bottom: 20px;
    padding: 20px;
    border: 2px dashed #e0e0e0;
    border-radius: 8px;
    text-align: center;
    transition: border-color 0.3s ease;
}

.file-upload:hover {
    border-color: #4CAF50;
}

.file-upload label {
    display: block;
    margin-bottom: 10px;
    font-weight: 500;
    color: #555;
}

.file-upload input[type="file"] {
    border: none;
    background: none;
}

button {
    background: #4CAF50;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.3s ease;
    margin-right: 10px;
    margin-bottom: 10px;
}

button:hover:not(:disabled) {
    background: #45a049;
}

button:disabled {
    background: #cccccc;
    cursor: not-allowed;
}

.error-message {
    background: #ffebee;
    color: #c62828;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.error-message button {
    background: none;
    color: #c62828;
    padding: 0;
    font-size: 20px;
    font-weight: bold;
    margin: 0;
}

.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #4CAF50;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading-overlay p {
    color: white;
    font-size: 18px;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .identity-verification {
        padding: 10px;
    }
    
    .step-container {
        padding: 20px;
    }
    
    .step-container h3 {
        font-size: 20px;
    }
    
    button {
        width: 100%;
        margin-right: 0;
    }
}
```

## 보안 고려사항

### 1. 데이터 보호

```python
# verification/security.py
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib
import hmac
import base64

class SecurityManager:
    """보안 관리 클래스"""
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """민감 데이터 해싱"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def encrypt_personal_data(data: str) -> str:
        """개인정보 암호화"""
        key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
        f = Fernet(base64.urlsafe_b64encode(key))
        return base64.b64encode(f.encrypt(data.encode())).decode()
    
    @staticmethod
    def decrypt_personal_data(encrypted_data: str) -> str:
        """개인정보 복호화"""
        key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
        f = Fernet(base64.urlsafe_b64encode(key))
        return f.decrypt(base64.b64decode(encrypted_data.encode())).decode()
    
    @staticmethod
    def generate_csrf_token(session_key: str) -> str:
        """CSRF 토큰 생성"""
        return hmac.new(
            settings.SECRET_KEY.encode(),
            session_key.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_csrf_token(session_key: str, token: str) -> bool:
        """CSRF 토큰 검증"""
        expected_token = SecurityManager.generate_csrf_token(session_key)
        return hmac.compare_digest(expected_token, token)
```

### 2. API 보안 설정

```python
# verification/middleware.py
from django.http import JsonResponse
from django.core.cache import cache
import time

class RateLimitMiddleware:
    """API 요청 제한 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path.startswith('/api/verification/'):
            client_ip = self.get_client_ip(request)
            
            # IP별 요청 제한 확인
            if not self.check_rate_limit(client_ip):
                return JsonResponse({
                    'success': False,
                    'message': 'Rate limit exceeded',
                    'retry_after': 60
                }, status=429)
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_rate_limit(self, client_ip):
        cache_key = f"rate_limit:{client_ip}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= 100:  # 시간당 100회 제한
            return False
        
        cache.set(cache_key, current_requests + 1, 3600)  # 1시간
        return True
```

## 결론

Django Ninja를 활용한 본인인증 시스템을 통해 다음과 같은 이점을 얻을 수 있습니다:

### 🎯 주요 장점

1. **강력한 보안**: 다단계 인증으로 높은 보안 수준 제공
2. **사용자 경험**: 직관적이고 단계별 안내로 쉬운 인증 과정
3. **확장성**: 모듈러 구조로 새로운 인증 방식 추가 용이
4. **신뢰성**: 비동기 처리와 에러 핸들링으로 안정적인 서비스
5. **규정 준수**: 개인정보보호법 등 관련 법규 준수

### 💡 실무 적용 포인트

- **금융 서비스**: 은행, 증권, 보험 등 금융 앱의 본인인증
- **의료 서비스**: 병원 예약, 처방전 조회 등 의료 정보 접근
- **전자상거래**: 고액 결제, 회원가입 시 신원 확인
- **공공 서비스**: 정부 민원, 증명서 발급 등 공공 서비스

### 🔧 확장 가능한 기능

- **생체 인증**: 지문, 홍채 인식 등 추가 생체 인증
- **블록체인**: 인증 결과의 무결성 보장
- **AI 기반 검증**: 딥러닝을 활용한 더 정확한 신분증/얼굴 인식
- **국제 표준**: OAuth 2.0, OpenID Connect 등 표준 프로토콜 연동

이 시스템은 실제 운영 환경에서 바로 활용할 수 있도록 설계되었으며, 각 조직의 요구사항에 맞춰 커스터마이징할 수 있습니다. 특히 Django Ninja의 자동 문서화 기능을 통해 API 문서도 자동으로 생성되어 개발 생산성을 크게 향상시킬 수 있습니다.