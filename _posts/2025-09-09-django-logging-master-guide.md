---
layout: post
title: "Django 로그 마스터하기: 기초부터 전문가 수준까지"
date: 2025-09-09 10:00:00 +0900
categories: [Django, Python, DevOps, Monitoring]
tags: [Django, Python, Logging, Monitoring, Debugging, Production, Performance]
---

Django 애플리케이션을 운영하면서 로그만큼 중요한 것은 없습니다. 하지만 많은 개발자들이 로그의 진정한 가치를 모르거나, 단순한 print 문으로 디버깅을 끝내는 경우가 많습니다. 이 글에서는 Django 로그의 중요성부터 전문가 수준의 로그 시스템 구축까지 단계별로 알아보겠습니다.

## 🎯 로그가 중요한 이유

### 1. 장애 대응의 핵심

```python
# 로그 없이 장애 상황
def transfer_money(from_account, to_account, amount):
    try:
        # 복잡한 금융 로직...
        result = process_transfer(from_account, to_account, amount)
        return result
    except Exception as e:
        # 무엇이 잘못되었는지 알 수 없음
        return {"error": "Transfer failed"}

# 적절한 로그가 있는 경우
import logging

logger = logging.getLogger(__name__)

def transfer_money(from_account, to_account, amount):
    logger.info(f"Transfer initiated: {from_account} -> {to_account}, amount: {amount}")
    
    try:
        # 각 단계별 로그
        logger.debug(f"Validating accounts: {from_account}, {to_account}")
        validate_accounts(from_account, to_account)
        
        logger.debug(f"Checking balance for account: {from_account}")
        if not check_sufficient_balance(from_account, amount):
            logger.warning(f"Insufficient balance: {from_account}, required: {amount}")
            return {"error": "Insufficient balance"}
        
        logger.info(f"Processing transfer: {amount}")
        result = process_transfer(from_account, to_account, amount)
        
        logger.info(f"Transfer completed successfully: {result['transaction_id']}")
        return result
        
    except ValidationError as e:
        logger.error(f"Validation failed: {e}, accounts: {from_account}, {to_account}")
        return {"error": "Invalid account"}
    except DatabaseError as e:
        logger.critical(f"Database error during transfer: {e}, rolling back")
        return {"error": "System error"}
    except Exception as e:
        logger.critical(f"Unexpected error: {e}, context: {locals()}")
        return {"error": "Transfer failed"}
```

### 2. 비즈니스 인사이트 도출

```python
# 사용자 행동 분석을 위한 로그
import structlog

# 구조화된 로거 설정
logger = structlog.get_logger()

def product_view(request, product_id):
    """상품 조회 로그 - 비즈니스 분석용"""
    
    logger.info(
        "product_viewed",
        user_id=request.user.id if request.user.is_authenticated else None,
        product_id=product_id,
        session_id=request.session.session_key,
        user_agent=request.META.get('HTTP_USER_AGENT'),
        referrer=request.META.get('HTTP_REFERER'),
        ip_address=get_client_ip(request),
        timestamp=timezone.now().isoformat(),
        # 비즈니스 메트릭
        product_category=product.category,
        product_price=float(product.price),
        is_mobile=is_mobile_request(request),
    )
    
    # 상품 조회 로직...
    return render(request, 'product.html', {'product': product})

def purchase_completed(request, order):
    """구매 완료 로그 - 매출 분석용"""
    
    logger.info(
        "purchase_completed",
        user_id=request.user.id,
        order_id=order.id,
        order_value=float(order.total_amount),
        payment_method=order.payment_method,
        products=[{
            'id': item.product.id,
            'name': item.product.name,
            'quantity': item.quantity,
            'price': float(item.price)
        } for item in order.items.all()],
        discount_applied=float(order.discount_amount) if order.discount_amount else 0,
        timestamp=timezone.now().isoformat(),
    )
```

### 3. 성능 모니터링

```python
import time
import functools

def performance_log(func):
    """성능 측정 데코레이터"""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        logger.info(f"Function {func.__name__} started", extra={
            'function': func.__name__,
            'args_count': len(args),
            'kwargs_count': len(kwargs),
        })
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"Function {func.__name__} completed", extra={
                'function': func.__name__,
                'execution_time': execution_time,
                'success': True,
            })
            
            # 성능 임계값 체크
            if execution_time > 1.0:  # 1초 이상
                logger.warning(f"Slow function detected: {func.__name__}", extra={
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'threshold_exceeded': True,
                })
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed", extra={
                'function': func.__name__,
                'execution_time': execution_time,
                'error': str(e),
                'success': False,
            })
            raise
    
    return wrapper

# 사용 예
@performance_log
def complex_data_processing(data):
    # 복잡한 데이터 처리...
    return processed_data
```

## 🔧 기초적인 Django 로그 설정

### 1. 기본 로그 설정

```python
# settings.py - 기본 로그 설정

import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    # 로그 포맷 정의
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    
    # 로그 핸들러 정의
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'level': 'ERROR',
            'formatter': 'verbose',
        },
    },
    
    # 루트 로거 설정
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
    
    # Django 관련 로거
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # 커스텀 앱 로거
        'myapp': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# 로그 디렉토리 생성
import os
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
```

### 2. 뷰에서 로그 사용하기

```python
# views.py - 기본적인 로그 사용

import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# 로거 생성
logger = logging.getLogger('myapp')

def user_profile(request, user_id):
    """사용자 프로필 조회"""
    
    logger.info(f"User profile requested for user_id: {user_id}")
    
    try:
        user = get_object_or_404(User, id=user_id)
        logger.debug(f"User found: {user.username}")
        
        return render(request, 'profile.html', {'user': user})
        
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        return JsonResponse({'error': 'User not found'}, status=404)

@require_http_methods(["POST"])
def create_post(request):
    """게시물 생성"""
    
    logger.info("Post creation requested", extra={
        'user_id': request.user.id,
        'user_ip': get_client_ip(request),
    })
    
    try:
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        if not title or not content:
            logger.warning("Post creation failed: missing required fields")
            return JsonResponse({'error': 'Title and content required'}, status=400)
        
        post = Post.objects.create(
            title=title,
            content=content,
            author=request.user
        )
        
        logger.info(f"Post created successfully: {post.id}")
        return JsonResponse({'post_id': post.id, 'status': 'created'})
        
    except Exception as e:
        logger.error(f"Error creating post: {e}", extra={
            'user_id': request.user.id,
            'error_type': type(e).__name__,
        })
        return JsonResponse({'error': 'Post creation failed'}, status=500)
```

### 3. 모델에서 로그 사용하기

```python
# models.py - 모델 레벨 로깅

import logging
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger('myapp.models')

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """저장 시 로그 기록"""
        
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"Creating new post: {self.title[:50]}...")
        else:
            logger.info(f"Updating post: {self.pk}")
        
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"Post created successfully: {self.pk}")
            else:
                logger.info(f"Post updated successfully: {self.pk}")
                
        except Exception as e:
            logger.error(f"Error saving post: {e}", extra={
                'post_title': self.title,
                'author_id': self.author.id if self.author else None,
            })
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로그 기록"""
        
        logger.warning(f"Deleting post: {self.pk} - {self.title}")
        
        try:
            super().delete(*args, **kwargs)
            logger.info(f"Post deleted successfully: {self.pk}")
            
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            raise
```

## 🚀 전문가 수준의 로그 시스템

### 1. 구조화된 로깅 (Structured Logging)

```python
# structured_logging.py - 구조화된 로깅 설정

import structlog
import logging.config
from django.conf import settings

def configure_structlog():
    """structlog 설정"""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# settings.py에서 호출
configure_structlog()

# 사용 예
import structlog

logger = structlog.get_logger()

def process_payment(user_id, amount, payment_method):
    """결제 처리 - 구조화된 로깅"""
    
    # 컨텍스트 로거 생성
    payment_logger = logger.bind(
        user_id=user_id,
        amount=amount,
        payment_method=payment_method,
        transaction_id=generate_transaction_id(),
    )
    
    payment_logger.info("Payment processing started")
    
    try:
        # 결제 검증
        payment_logger.debug("Validating payment information")
        validate_payment_info(user_id, amount, payment_method)
        
        # 결제 처리
        payment_logger.info("Processing payment with gateway")
        result = process_with_gateway(amount, payment_method)
        
        payment_logger.info("Payment completed successfully", 
                          gateway_response=result)
        
        return result
        
    except PaymentValidationError as e:
        payment_logger.error("Payment validation failed", 
                           error=str(e), error_type="validation")
        raise
    except GatewayError as e:
        payment_logger.error("Gateway error occurred", 
                           error=str(e), error_type="gateway")
        raise
    except Exception as e:
        payment_logger.critical("Unexpected payment error", 
                               error=str(e), error_type="unknown")
        raise
```

### 2. 로그 수집 및 중앙화

```python
# log_collectors.py - 로그 수집 시스템

import json
import requests
import threading
from queue import Queue
from datetime import datetime

class LogCollector:
    """로그를 외부 시스템으로 전송하는 수집기"""
    
    def __init__(self, endpoint, api_key, batch_size=100):
        self.endpoint = endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self.log_queue = Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def send_log(self, level, message, extra=None):
        """로그를 큐에 추가"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'extra': extra or {},
            'service': 'django-app',
            'environment': settings.ENVIRONMENT,
        }
        self.log_queue.put(log_entry)
    
    def _worker(self):
        """백그라운드에서 로그 전송"""
        logs_batch = []
        
        while True:
            try:
                # 큐에서 로그 수집
                log_entry = self.log_queue.get(timeout=5)
                logs_batch.append(log_entry)
                
                # 배치 크기에 도달하면 전송
                if len(logs_batch) >= self.batch_size:
                    self._send_batch(logs_batch)
                    logs_batch = []
                    
            except:
                # 타임아웃 또는 에러 시 현재 배치 전송
                if logs_batch:
                    self._send_batch(logs_batch)
                    logs_batch = []
    
    def _send_batch(self, logs_batch):
        """로그 배치를 외부 시스템으로 전송"""
        try:
            response = requests.post(
                self.endpoint,
                json={'logs': logs_batch},
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=10
            )
            response.raise_for_status()
            
        except Exception as e:
            # 로그 전송 실패는 조용히 처리 (무한 루프 방지)
            print(f"Failed to send logs: {e}")

# 전역 로그 수집기 인스턴스
log_collector = LogCollector(
    endpoint=settings.LOG_ENDPOINT,
    api_key=settings.LOG_API_KEY
)

class ExternalLogHandler(logging.Handler):
    """외부 로그 시스템 연동 핸들러"""
    
    def emit(self, record):
        """로그 레코드를 외부 시스템으로 전송"""
        try:
            # 로그 메시지 포맷팅
            message = self.format(record)
            
            # 추가 정보 수집
            extra = {
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'thread': record.thread,
                'process': record.process,
            }
            
            # 커스텀 필드 추가
            if hasattr(record, 'user_id'):
                extra['user_id'] = record.user_id
            if hasattr(record, 'request_id'):
                extra['request_id'] = record.request_id
            
            # 외부 시스템으로 전송
            log_collector.send_log(record.levelname, message, extra)
            
        except Exception:
            # 로그 처리 실패해도 애플리케이션은 계속 실행
            pass
```

### 3. 고급 로그 미들웨어

```python
# middleware.py - 고급 로그 미들웨어

import time
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve

logger = logging.getLogger('django.request')

class AdvancedLoggingMiddleware(MiddlewareMixin):
    """고급 로깅 미들웨어"""
    
    def process_request(self, request):
        """요청 시작 시 처리"""
        
        # 고유 요청 ID 생성
        request.id = str(uuid.uuid4())
        request.start_time = time.time()
        
        # URL 패턴 정보
        try:
            url_match = resolve(request.path_info)
            view_name = url_match.view_name
            view_args = url_match.args
            view_kwargs = url_match.kwargs
        except:
            view_name = 'unknown'
            view_args = ()
            view_kwargs = {}
        
        # 요청 정보 로깅
        logger.info("Request started", extra={
            'request_id': request.id,
            'method': request.method,
            'path': request.path,
            'view_name': view_name,
            'view_args': view_args,
            'view_kwargs': view_kwargs,
            'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'content_type': request.content_type,
            'content_length': request.META.get('CONTENT_LENGTH', 0),
        })
    
    def process_response(self, request, response):
        """응답 완료 시 처리"""
        
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # 응답 정보 로깅
            logger.info("Request completed", extra={
                'request_id': getattr(request, 'id', 'unknown'),
                'status_code': response.status_code,
                'duration': duration,
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
                'cache_hit': response.get('X-Cache-Status', 'unknown'),
            })
            
            # 성능 경고
            if duration > 1.0:  # 1초 이상
                logger.warning("Slow request detected", extra={
                    'request_id': getattr(request, 'id', 'unknown'),
                    'duration': duration,
                    'path': request.path,
                    'method': request.method,
                })
        
        return response
    
    def process_exception(self, request, exception):
        """예외 발생 시 처리"""
        
        duration = time.time() - request.start_time if hasattr(request, 'start_time') else 0
        
        logger.error("Request failed with exception", extra={
            'request_id': getattr(request, 'id', 'unknown'),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'duration': duration,
            'path': request.path,
            'method': request.method,
            'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
        }, exc_info=True)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### 4. 로그 분석 및 알림 시스템

```python
# log_analysis.py - 로그 분석 시스템

import re
import time
import smtplib
from collections import defaultdict, deque
from email.mime.text import MimeText
from datetime import datetime, timedelta
from threading import Lock

class LogAnalyzer:
    """실시간 로그 분석 및 알림 시스템"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=1000)
        self.alert_thresholds = {
            'error_rate': 10,  # 분당 에러 수
            'critical_errors': 1,  # 크리티컬 에러는 즉시 알림
            'slow_requests': 50,  # 분당 느린 요청 수
        }
        self.lock = Lock()
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5분 쿨다운
    
    def analyze_log(self, record):
        """로그 레코드 분석"""
        
        with self.lock:
            current_time = time.time()
            
            # 에러 레벨 분석
            if record.levelno >= logging.ERROR:
                self.error_counts[record.levelname] += 1
                self.recent_errors.append({
                    'timestamp': current_time,
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                })
                
                # 크리티컬 에러는 즉시 알림
                if record.levelno >= logging.CRITICAL:
                    self.send_immediate_alert(record)
            
            # 성능 분석
            if hasattr(record, 'duration') and record.duration > 1.0:
                self.analyze_performance(record)
            
            # 주기적 분석
            self.periodic_analysis()
    
    def analyze_performance(self, record):
        """성능 분석"""
        
        slow_request_count = sum(1 for error in self.recent_errors 
                               if time.time() - error['timestamp'] < 60 
                               and 'slow' in error.get('message', '').lower())
        
        if slow_request_count > self.alert_thresholds['slow_requests']:
            self.send_performance_alert(slow_request_count)
    
    def periodic_analysis(self):
        """주기적 분석 (1분마다)"""
        
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # 최근 1분간 에러 수 계산
        recent_error_count = sum(1 for error in self.recent_errors 
                               if error['timestamp'] > one_minute_ago)
        
        if recent_error_count > self.alert_thresholds['error_rate']:
            self.send_error_rate_alert(recent_error_count)
    
    def send_immediate_alert(self, record):
        """즉시 알림 전송"""
        
        alert_key = f"critical_{record.module}"
        current_time = time.time()
        
        if (alert_key not in self.last_alert_time or 
            current_time - self.last_alert_time[alert_key] > self.alert_cooldown):
            
            subject = f"🚨 CRITICAL ERROR in {record.module}"
            body = f"""
            Critical error detected:
            
            Time: {datetime.now()}
            Module: {record.module}
            Function: {record.funcName}
            Line: {record.lineno}
            Message: {record.getMessage()}
            
            Please investigate immediately.
            """
            
            self.send_email_alert(subject, body)
            self.last_alert_time[alert_key] = current_time
    
    def send_error_rate_alert(self, error_count):
        """에러 발생률 알림"""
        
        alert_key = "error_rate"
        current_time = time.time()
        
        if (alert_key not in self.last_alert_time or 
            current_time - self.last_alert_time[alert_key] > self.alert_cooldown):
            
            subject = f"⚠️ High Error Rate: {error_count} errors/minute"
            body = f"""
            High error rate detected:
            
            Error count (last minute): {error_count}
            Threshold: {self.alert_thresholds['error_rate']}
            
            Recent errors:
            {self.format_recent_errors()}
            """
            
            self.send_email_alert(subject, body)
            self.last_alert_time[alert_key] = current_time
    
    def format_recent_errors(self):
        """최근 에러 포맷팅"""
        
        recent = list(self.recent_errors)[-10:]  # 최근 10개
        formatted = []
        
        for error in recent:
            timestamp = datetime.fromtimestamp(error['timestamp'])
            formatted.append(f"[{timestamp}] {error['level']}: {error['message']}")
        
        return '\n'.join(formatted)
    
    def send_email_alert(self, subject, body):
        """이메일 알림 전송"""
        
        try:
            msg = MimeText(body)
            msg['Subject'] = subject
            msg['From'] = settings.ALERT_EMAIL_FROM
            msg['To'] = settings.ALERT_EMAIL_TO
            
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            # 알림 전송 실패는 별도 로그에 기록
            print(f"Failed to send alert email: {e}")

# 전역 로그 분석기
log_analyzer = LogAnalyzer()

class AnalysisLogHandler(logging.Handler):
    """로그 분석 핸들러"""
    
    def emit(self, record):
        """로그 레코드를 분석기로 전달"""
        try:
            log_analyzer.analyze_log(record)
        except Exception:
            # 분석 실패해도 애플리케이션은 계속 실행
            pass
```

### 5. 프로덕션 로그 설정

```python
# settings/production.py - 프로덕션 로그 설정

import os
from .base import *

# 로그 디렉토리 설정
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    # 포맷터
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        },
        'syslog': {
            'format': 'django[%(process)d]: %(levelname)s %(name)s: %(message)s'
        },
    },
    
    # 핸들러
    'handlers': {
        # 콘솔 출력 (Docker/Kubernetes 환경)
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'INFO',
        },
        
        # 애플리케이션 로그 파일
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'application.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'INFO',
        },
        
        # 에러 로그 파일
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'ERROR',
        },
        
        # 보안 로그 파일
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'security.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'json',
            'level': 'WARNING',
        },
        
        # 외부 로그 시스템 연동
        'external': {
            '()': 'myapp.logging.ExternalLogHandler',
            'level': 'WARNING',
        },
        
        # 로그 분석 시스템
        'analyzer': {
            '()': 'myapp.logging.AnalysisLogHandler',
            'level': 'ERROR',
        },
        
        # Syslog (시스템 로그)
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'facility': 'local0',
            'formatter': 'syslog',
            'level': 'ERROR',
        },
    },
    
    # 로거 설정
    'loggers': {
        # Django 프레임워크 로그
        'django': {
            'handlers': ['console', 'app_file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Django 요청 로그
        'django.request': {
            'handlers': ['console', 'error_file', 'external'],
            'level': 'ERROR',
            'propagate': False,
        },
        
        # Django 보안 로그
        'django.security': {
            'handlers': ['console', 'security_file', 'external'],
            'level': 'WARNING',
            'propagate': False,
        },
        
        # 데이터베이스 쿼리 로그 (성능 모니터링용)
        'django.db.backends': {
            'handlers': ['app_file'],
            'level': 'WARNING',  # 프로덕션에서는 WARNING 이상만
            'propagate': False,
        },
        
        # 애플리케이션 로그
        'myapp': {
            'handlers': ['console', 'app_file', 'analyzer'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # 비즈니스 로그 (분석용)
        'myapp.business': {
            'handlers': ['console', 'app_file', 'external'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # 보안 관련 로그
        'myapp.security': {
            'handlers': ['security_file', 'external', 'syslog'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    
    # 루트 로거
    'root': {
        'level': 'WARNING',
        'handlers': ['console', 'error_file'],
    },
}

# 로그 관련 설정
LOG_ENDPOINT = os.environ.get('LOG_ENDPOINT')
LOG_API_KEY = os.environ.get('LOG_API_KEY')
ALERT_EMAIL_FROM = os.environ.get('ALERT_EMAIL_FROM')
ALERT_EMAIL_TO = os.environ.get('ALERT_EMAIL_TO')
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
```

## 📊 로그 모니터링 및 분석 도구

### 1. 로그 대시보드

```python
# dashboard.py - 로그 대시보드

import json
import sqlite3
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render

class LogDashboard:
    """로그 대시보드 데이터 제공"""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
    
    def get_error_statistics(self, hours=24):
        """에러 통계 조회"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        error_counts = {
            'ERROR': 0,
            'CRITICAL': 0,
            'WARNING': 0,
        }
        
        error_timeline = []
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        log_time = datetime.fromisoformat(log_entry['asctime'])
                        
                        if start_time <= log_time <= end_time:
                            level = log_entry.get('levelname')
                            if level in error_counts:
                                error_counts[level] += 1
                                
                                error_timeline.append({
                                    'time': log_time.isoformat(),
                                    'level': level,
                                    'message': log_entry.get('message', '')[:100],
                                })
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        return {
            'error_counts': error_counts,
            'error_timeline': error_timeline[-100:],  # 최근 100개
            'total_errors': sum(error_counts.values()),
        }
    
    def get_performance_metrics(self, hours=24):
        """성능 메트릭 조회"""
        
        response_times = []
        slow_requests = []
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        
                        if 'duration' in log_entry:
                            duration = float(log_entry['duration'])
                            response_times.append(duration)
                            
                            if duration > 1.0:  # 1초 이상
                                slow_requests.append({
                                    'time': log_entry.get('asctime'),
                                    'duration': duration,
                                    'path': log_entry.get('path', ''),
                                    'method': log_entry.get('method', ''),
                                })
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        # 통계 계산
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = max_response_time = p95_response_time = 0
        
        return {
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'p95_response_time': p95_response_time,
            'slow_requests_count': len(slow_requests),
            'slow_requests': slow_requests[-20:],  # 최근 20개
        }

def dashboard_view(request):
    """대시보드 뷰"""
    
    dashboard = LogDashboard('/app/logs/application.log')
    
    error_stats = dashboard.get_error_statistics()
    performance_stats = dashboard.get_performance_metrics()
    
    context = {
        'error_stats': error_stats,
        'performance_stats': performance_stats,
        'last_updated': datetime.now().isoformat(),
    }
    
    return render(request, 'dashboard.html', context)

def dashboard_api(request):
    """대시보드 API (Ajax용)"""
    
    dashboard = LogDashboard('/app/logs/application.log')
    
    data = {
        'errors': dashboard.get_error_statistics(),
        'performance': dashboard.get_performance_metrics(),
        'timestamp': datetime.now().isoformat(),
    }
    
    return JsonResponse(data)
```

### 2. 로그 검색 및 필터링

```python
# log_search.py - 로그 검색 시스템

import re
import json
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.http import JsonResponse

class LogSearch:
    """고급 로그 검색 시스템"""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
    
    def search(self, query=None, level=None, start_time=None, end_time=None, 
               module=None, user_id=None, limit=100):
        """로그 검색"""
        
        results = []
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        
                        # 필터 조건 확인
                        if not self._matches_filters(log_entry, query, level, 
                                                   start_time, end_time, module, user_id):
                            continue
                        
                        results.append(log_entry)
                        
                        if len(results) >= limit:
                            break
                    
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        except FileNotFoundError:
            pass
        
        return results
    
    def _matches_filters(self, log_entry, query, level, start_time, end_time, module, user_id):
        """필터 조건 확인"""
        
        # 텍스트 검색
        if query:
            message = log_entry.get('message', '').lower()
            if query.lower() not in message:
                return False
        
        # 로그 레벨 필터
        if level and log_entry.get('levelname') != level:
            return False
        
        # 시간 범위 필터
        if start_time or end_time:
            try:
                log_time = datetime.fromisoformat(log_entry.get('asctime', ''))
                if start_time and log_time < start_time:
                    return False
                if end_time and log_time > end_time:
                    return False
            except ValueError:
                return False
        
        # 모듈 필터
        if module and log_entry.get('name') != module:
            return False
        
        # 사용자 ID 필터
        if user_id and log_entry.get('user_id') != user_id:
            return False
        
        return True
    
    def get_log_statistics(self, hours=24):
        """로그 통계"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        stats = {
            'total_logs': 0,
            'by_level': {},
            'by_module': {},
            'by_hour': {},
        }
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        log_time = datetime.fromisoformat(log_entry.get('asctime', ''))
                        
                        if start_time <= log_time <= end_time:
                            stats['total_logs'] += 1
                            
                            # 레벨별 통계
                            level = log_entry.get('levelname', 'UNKNOWN')
                            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
                            
                            # 모듈별 통계
                            module = log_entry.get('name', 'unknown')
                            stats['by_module'][module] = stats['by_module'].get(module, 0) + 1
                            
                            # 시간별 통계
                            hour_key = log_time.strftime('%Y-%m-%d %H:00')
                            stats['by_hour'][hour_key] = stats['by_hour'].get(hour_key, 0) + 1
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        return stats

def search_logs(request):
    """로그 검색 API"""
    
    # 검색 파라미터
    query = request.GET.get('q')
    level = request.GET.get('level')
    module = request.GET.get('module')
    user_id = request.GET.get('user_id')
    hours = int(request.GET.get('hours', 24))
    page = int(request.GET.get('page', 1))
    
    # 시간 범위 설정
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 로그 검색
    searcher = LogSearch('/app/logs/application.log')
    results = searcher.search(
        query=query,
        level=level,
        start_time=start_time,
        end_time=end_time,
        module=module,
        user_id=user_id,
        limit=1000
    )
    
    # 페이지네이션
    paginator = Paginator(results, 50)
    page_obj = paginator.get_page(page)
    
    return JsonResponse({
        'logs': list(page_obj),
        'total_count': len(results),
        'page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })
```

## 🎯 로그 베스트 프랙티스

### 1. 로그 레벨 가이드라인

```python
# log_guidelines.py - 로그 레벨 사용 가이드

import logging

logger = logging.getLogger(__name__)

# DEBUG: 개발 중 상세한 정보
def process_data(data):
    logger.debug(f"Processing data with {len(data)} items")
    logger.debug(f"Data structure: {type(data).__name__}")
    
    for item in data:
        logger.debug(f"Processing item: {item['id']}")
        # 처리 로직...

# INFO: 일반적인 정보, 비즈니스 플로우
def user_login(user):
    logger.info(f"User login successful", extra={
        'user_id': user.id,
        'username': user.username,
        'login_method': 'password',
    })

# WARNING: 문제가 될 수 있는 상황
def check_disk_space():
    free_space = get_free_disk_space()
    if free_space < 1024 * 1024 * 1024:  # 1GB 미만
        logger.warning(f"Low disk space: {free_space / 1024 / 1024:.1f}MB remaining")

# ERROR: 오류가 발생했지만 애플리케이션은 계속 실행
def process_payment(amount):
    try:
        result = payment_gateway.charge(amount)
        return result
    except PaymentException as e:
        logger.error(f"Payment failed: {e}", extra={
            'amount': amount,
            'error_code': e.code,
        })
        return None

# CRITICAL: 심각한 오류, 즉시 대응 필요
def database_connection():
    try:
        connection = get_db_connection()
        return connection
    except DatabaseConnectionError as e:
        logger.critical(f"Database connection failed: {e}", extra={
            'database_host': settings.DATABASE_HOST,
            'error_details': str(e),
        })
        raise
```

### 2. 성능을 고려한 로깅

```python
# performance_logging.py - 성능 최적화된 로깅

import logging
from functools import wraps

logger = logging.getLogger(__name__)

# 조건부 로깅 (성능 향상)
def conditional_debug_log(condition_func):
    """조건이 참일 때만 DEBUG 로그 출력"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if logger.isEnabledFor(logging.DEBUG) and condition_func():
                logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            result = func(*args, **kwargs)
            
            if logger.isEnabledFor(logging.DEBUG) and condition_func():
                logger.debug(f"{func.__name__} returned: {type(result).__name__}")
            
            return result
        return wrapper
    return decorator

# 지연 로그 평가 (Lazy Evaluation)
class LazyLogMessage:
    """무거운 로그 메시지의 지연 평가"""
    
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def __str__(self):
        return self.func(*self.args, **self.kwargs)

def expensive_debug_info():
    """무거운 디버그 정보 생성"""
    # 복잡한 계산이나 데이터 직렬화...
    return "Very expensive debug information..."

# 사용 예
logger.debug(LazyLogMessage(expensive_debug_info))

# 배치 로깅 (성능 향상)
class BatchLogger:
    """로그를 모아서 배치로 처리"""
    
    def __init__(self, logger, batch_size=100, flush_interval=30):
        self.logger = logger
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_buffer = []
        self.last_flush = time.time()
    
    def log(self, level, message, extra=None):
        """로그를 버퍼에 추가"""
        self.log_buffer.append({
            'level': level,
            'message': message,
            'extra': extra,
            'timestamp': time.time(),
        })
        
        # 조건에 따라 플러시
        if (len(self.log_buffer) >= self.batch_size or 
            time.time() - self.last_flush > self.flush_interval):
            self.flush()
    
    def flush(self):
        """버퍼의 로그들을 실제로 출력"""
        for log_entry in self.log_buffer:
            getattr(self.logger, log_entry['level'].lower())(
                log_entry['message'], 
                extra=log_entry['extra']
            )
        
        self.log_buffer.clear()
        self.last_flush = time.time()
```

## 🚀 결론

Django 로그 시스템을 제대로 구축하는 것은 애플리케이션의 안정성과 운영 효율성에 직결됩니다.

**핵심 포인트:**

1. **로그는 비용이 아닌 투자**: 초기 설정에 시간을 투자하면 장기적으로 엄청난 시간을 절약할 수 있습니다.

2. **단계적 접근**: 기초적인 로그부터 시작해서 점차 고도화해 나가세요.

3. **구조화된 로깅**: JSON 형태의 구조화된 로그는 분석과 알림 시스템 구축에 필수입니다.

4. **성능 고려**: 로그 자체가 성능 병목이 되지 않도록 최적화가 중요합니다.

5. **모니터링과 알림**: 로그를 수집하는 것뿐만 아니라 실시간 분석과 알림 시스템까지 구축해야 완전합니다.

**추천 로드맵:**
- **1단계**: 기본 로그 설정 및 적절한 로그 레벨 적용
- **2단계**: 구조화된 로깅 도입 및 로그 수집 시스템 구축
- **3단계**: 실시간 분석 및 알림 시스템 개발
- **4단계**: 로그 기반 비즈니스 인사이트 도출

효과적인 로그 시스템은 단순한 디버깅 도구를 넘어서 비즈니스 성장의 핵심 인프라가 될 수 있습니다.

---

**참고 자료:**
- [Django 로깅 공식 문서](https://docs.djangoproject.com/en/stable/topics/logging/)
- [Python logging 모듈](https://docs.python.org/3/library/logging.html)
- [Structlog 라이브러리](https://www.structlog.org/)
- [ELK Stack (Elasticsearch, Logstash, Kibana)](https://www.elastic.co/elk-stack)
