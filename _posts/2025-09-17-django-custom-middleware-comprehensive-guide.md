---
layout: post
title: "Django 커스텀 미들웨어 완전 가이드: 실전 구현 사례와 고려사항"
date: 2025-09-17 14:00:00 +0900
categories: [Django, Middleware, Performance, Security]
tags: [Django, Middleware, Custom Middleware, Performance, Security, Authentication, Logging, Rate Limiting]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-09-17-django-custom-middleware-comprehensive-guide.webp"
---

Django 미들웨어는 요청과 응답 처리 과정에서 **횡단 관심사(Cross-cutting Concerns)**를 처리하는 강력한 도구입니다. 인증, 로깅, 성능 모니터링, 보안 검사 등 애플리케이션 전반에 걸쳐 적용되어야 하는 기능들을 중앙화하여 관리할 수 있습니다. 이 글에서는 Django 커스텀 미들웨어의 **실전 구현 사례**와 **고려사항**을 상세히 다루겠습니다.

## 🎯 Django 미들웨어 기본 원리

### 미들웨어 실행 흐름

Django 미들웨어는 **양파껍질(Onion) 패턴**으로 동작합니다. 요청은 위에서 아래로, 응답은 아래에서 위로 처리됩니다.

```python
# Django 미들웨어 실행 순서
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',          # 1
    'django.contrib.sessions.middleware.SessionMiddleware',   # 2
    'django.middleware.common.CommonMiddleware',              # 3
    'django.middleware.csrf.CsrfViewMiddleware',              # 4
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 5
    'myproject.middleware.CustomMiddleware',                  # 6 (우리가 만들 미들웨어)
    'django.contrib.messages.middleware.MessageMiddleware',   # 7
]

# 실행 흐름:
# 요청 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → View → 7 → 6 → 5 → 4 → 3 → 2 → 1 → 응답
```

### 미들웨어 기본 구조

```python
# middleware/base.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class BaseCustomMiddleware(MiddlewareMixin):
    """기본 커스텀 미들웨어 템플릿"""
    
    def __init__(self, get_response):
        """미들웨어 초기화 (Django 2.0+ 스타일)"""
        self.get_response = get_response
        # 일회성 초기화 코드
        super().__init__(get_response)
    
    def __call__(self, request):
        """각 요청마다 호출되는 메인 메서드"""
        # 요청 전 처리
        response = self.get_response(request)
        # 응답 후 처리
        return response
    
    # === 옵셔널 메서드들 ===
    
    def process_request(self, request):
        """뷰 실행 전 요청 처리"""
        # HttpResponse를 반환하면 뷰를 건너뛰고 응답 처리로 이동
        # None을 반환하면 다음 미들웨어로 진행
        pass
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """뷰 함수 실행 직전 처리"""
        # view_func: 실행될 뷰 함수
        # view_args, view_kwargs: 뷰 함수의 인자들
        pass
    
    def process_exception(self, request, exception):
        """뷰에서 예외 발생 시 처리"""
        # HttpResponse를 반환하면 해당 응답 사용
        # None을 반환하면 기본 예외 처리
        pass
    
    def process_response(self, request, response):
        """응답 반환 전 처리"""
        # 반드시 HttpResponse 객체를 반환해야 함
        return response
```

## 🔧 실전 미들웨어 구현 사례

### 1. 성능 모니터링 미들웨어

```python
# middleware/performance.py
import time
import logging
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
import json

logger = logging.getLogger('performance')

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """요청별 성능 모니터링 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0)  # 1초
        self.db_query_threshold = getattr(settings, 'DB_QUERY_THRESHOLD', 10)  # 10개 쿼리
        super().__init__(get_response)
    
    def process_request(self, request):
        """요청 시작 시 성능 측정 시작"""
        request._start_time = time.time()
        request._db_queries_start = len(connection.queries)
        
        # 메모리 사용량 측정 (옵션)
        if hasattr(settings, 'MONITOR_MEMORY') and settings.MONITOR_MEMORY:
            import psutil
            process = psutil.Process()
            request._memory_start = process.memory_info().rss
    
    def process_response(self, request, response):
        """응답 시 성능 데이터 수집"""
        if not hasattr(request, '_start_time'):
            return response
        
        # 응답 시간 계산
        duration = time.time() - request._start_time
        
        # DB 쿼리 수 계산
        db_queries = len(connection.queries) - getattr(request, '_db_queries_start', 0)
        
        # 응답 크기 계산
        content_length = len(response.content) if hasattr(response, 'content') else 0
        
        # 성능 데이터 구성
        perf_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'db_queries': db_queries,
            'content_length': content_length,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'timestamp': time.time()
        }
        
        # 메모리 사용량 (옵션)
        if hasattr(request, '_memory_start'):
            import psutil
            process = psutil.Process()
            memory_diff = process.memory_info().rss - request._memory_start
            perf_data['memory_usage_mb'] = round(memory_diff / 1024 / 1024, 2)
        
        # 성능 임계값 검사
        self.check_performance_thresholds(perf_data)
        
        # 메트릭 저장
        self.save_metrics(perf_data)
        
        # HTTP 헤더에 성능 정보 추가 (개발환경)
        if settings.DEBUG:
            response['X-Response-Time'] = f"{perf_data['duration_ms']}ms"
            response['X-DB-Queries'] = str(db_queries)
        
        return response
    
    def get_client_ip(self, request):
        """클라이언트 실제 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_performance_thresholds(self, perf_data):
        """성능 임계값 검사 및 알림"""
        
        # 느린 요청 감지
        if perf_data['duration_ms'] > self.slow_request_threshold * 1000:
            logger.warning(
                f"Slow request detected: {perf_data['method']} {perf_data['path']} "
                f"took {perf_data['duration_ms']}ms"
            )
            
            # 심각한 지연 시 즉시 알림
            if perf_data['duration_ms'] > 5000:  # 5초 이상
                self.send_critical_alert(perf_data)
        
        # N+1 쿼리 문제 감지
        if perf_data['db_queries'] > self.db_query_threshold:
            logger.warning(
                f"High DB query count: {perf_data['path']} "
                f"executed {perf_data['db_queries']} queries"
            )
        
        # 4xx, 5xx 에러 처리
        if perf_data['status_code'] >= 400:
            log_level = logger.error if perf_data['status_code'] >= 500 else logger.warning
            log_level(
                f"HTTP {perf_data['status_code']}: {perf_data['method']} {perf_data['path']}"
            )
    
    def save_metrics(self, perf_data):
        """성능 메트릭을 캐시/DB에 저장"""
        try:
            # Redis에 실시간 메트릭 저장 (분 단위)
            minute_key = f"metrics:{int(time.time() // 60)}"
            current_metrics = cache.get(minute_key, {
                'total_requests': 0,
                'total_duration': 0,
                'slow_requests': 0,
                'error_count': 0,
                'avg_db_queries': 0
            })
            
            current_metrics['total_requests'] += 1
            current_metrics['total_duration'] += perf_data['duration_ms']
            current_metrics['avg_db_queries'] = (
                (current_metrics['avg_db_queries'] * (current_metrics['total_requests'] - 1) + 
                 perf_data['db_queries']) / current_metrics['total_requests']
            )
            
            if perf_data['duration_ms'] > self.slow_request_threshold * 1000:
                current_metrics['slow_requests'] += 1
            
            if perf_data['status_code'] >= 400:
                current_metrics['error_count'] += 1
            
            cache.set(minute_key, current_metrics, timeout=300)  # 5분 캐시
            
            # 상세 로그를 별도 저장 (옵션)
            if getattr(settings, 'SAVE_DETAILED_METRICS', False):
                self.save_detailed_metrics(perf_data)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def save_detailed_metrics(self, perf_data):
        """상세 성능 데이터를 DB에 저장"""
        from myapp.models import PerformanceLog
        
        try:
            PerformanceLog.objects.create(
                method=perf_data['method'],
                path=perf_data['path'],
                status_code=perf_data['status_code'],
                duration_ms=perf_data['duration_ms'],
                db_queries=perf_data['db_queries'],
                content_length=perf_data['content_length'],
                user_id=perf_data['user_id'],
                ip_address=perf_data['ip'],
                user_agent=perf_data['user_agent']
            )
        except Exception as e:
            logger.error(f"Failed to save detailed metrics: {e}")
    
    def send_critical_alert(self, perf_data):
        """심각한 성능 문제 시 알림 발송"""
        # Slack, 이메일, SMS 등으로 알림
        alert_message = (
            f"🚨 Critical Performance Alert\n"
            f"Path: {perf_data['method']} {perf_data['path']}\n"
            f"Duration: {perf_data['duration_ms']}ms\n"
            f"DB Queries: {perf_data['db_queries']}\n"
            f"User: {perf_data['user_id']}\n"
            f"IP: {perf_data['ip']}"
        )
        
        # 여기에 실제 알림 로직 구현
        logger.critical(alert_message)
```

### 2. API 레이트 리미팅 미들웨어

```python
# middleware/rate_limiting.py
import time
import json
import hashlib
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('rate_limiting')

class RateLimitingMiddleware(MiddlewareMixin):
    """API 요청 속도 제한 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 기본 레이트 리밋 설정
        self.default_limits = getattr(settings, 'RATE_LIMITS', {
            'default': {'requests': 1000, 'window': 3600},  # 1시간에 1000요청
            'api': {'requests': 100, 'window': 60},          # 1분에 100요청
            'auth': {'requests': 5, 'window': 300},          # 5분에 5요청 (로그인 등)
        })
        
        # 경로별 레이트 리밋 설정
        self.path_limits = getattr(settings, 'PATH_RATE_LIMITS', {
            '/api/auth/login/': 'auth',
            '/api/auth/register/': 'auth',
            '/api/': 'api',
        })
        
        super().__init__(get_response)
    
    def process_request(self, request):
        """요청 전 레이트 리밋 검사"""
        
        # 레이트 리밋 적용 대상 확인
        if not self.should_rate_limit(request):
            return None
        
        # 클라이언트 식별
        client_id = self.get_client_identifier(request)
        
        # 레이트 리밋 규칙 결정
        limit_key = self.get_limit_key(request)
        limit_config = self.default_limits.get(limit_key, self.default_limits['default'])
        
        # 레이트 리밋 검사
        is_allowed, remaining, reset_time = self.check_rate_limit(
            client_id, limit_key, limit_config
        )
        
        if not is_allowed:
            return self.rate_limit_exceeded_response(remaining, reset_time)
        
        # 요청 허용 - 응답 헤더에 정보 추가
        request._rate_limit_info = {
            'remaining': remaining,
            'reset_time': reset_time,
            'limit': limit_config['requests']
        }
        
        return None
    
    def process_response(self, request, response):
        """응답에 레이트 리밋 헤더 추가"""
        
        if hasattr(request, '_rate_limit_info'):
            info = request._rate_limit_info
            response['X-RateLimit-Limit'] = str(info['limit'])
            response['X-RateLimit-Remaining'] = str(info['remaining'])
            response['X-RateLimit-Reset'] = str(int(info['reset_time']))
        
        return response
    
    def should_rate_limit(self, request):
        """레이트 리밋 적용 여부 판단"""
        
        # 내부 헬스체크 등은 제외
        if request.path in ['/health/', '/ping/']:
            return False
        
        # 특정 IP는 제외 (화이트리스트)
        whitelist_ips = getattr(settings, 'RATE_LIMIT_WHITELIST', [])
        client_ip = self.get_client_ip(request)
        if client_ip in whitelist_ips:
            return False
        
        # 관리자는 제외 (옵션)
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.is_superuser:
                return False
        
        return True
    
    def get_client_identifier(self, request):
        """클라이언트 식별자 생성"""
        
        # 인증된 사용자는 user_id 사용
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # API 키가 있는 경우
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            # API 키 해시화
            return f"api:{hashlib.md5(api_key.encode()).hexdigest()[:16]}"
        
        # IP 주소 기반
        ip = self.get_client_ip(request)
        return f"ip:{ip}"
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_limit_key(self, request):
        """요청 경로에 따른 레이트 리밋 키 결정"""
        
        path = request.path
        
        # 가장 구체적인 패턴부터 매칭
        for pattern, limit_key in self.path_limits.items():
            if path.startswith(pattern):
                return limit_key
        
        return 'default'
    
    def check_rate_limit(self, client_id, limit_key, limit_config):
        """레이트 리밋 검사 (Sliding Window 알고리즘)"""
        
        cache_key = f"rate_limit:{limit_key}:{client_id}"
        window_size = limit_config['window']
        max_requests = limit_config['requests']
        
        current_time = time.time()
        window_start = current_time - window_size
        
        # 현재 윈도우의 요청 기록 조회
        request_times = cache.get(cache_key, [])
        
        # 윈도우 밖의 요청들 제거
        request_times = [t for t in request_times if t > window_start]
        
        # 요청 허용 여부 확인
        if len(request_times) >= max_requests:
            # 제한 초과
            oldest_request = min(request_times) if request_times else current_time
            reset_time = oldest_request + window_size
            return False, 0, reset_time
        
        # 요청 허용 - 현재 요청 기록
        request_times.append(current_time)
        cache.set(cache_key, request_times, timeout=window_size + 60)
        
        remaining = max_requests - len(request_times)
        reset_time = current_time + window_size
        
        return True, remaining, reset_time
    
    def rate_limit_exceeded_response(self, remaining, reset_time):
        """레이트 리밋 초과 시 응답"""
        
        retry_after = int(reset_time - time.time())
        
        response_data = {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': retry_after
        }
        
        response = JsonResponse(response_data, status=429)
        response['Retry-After'] = str(retry_after)
        response['X-RateLimit-Remaining'] = '0'
        response['X-RateLimit-Reset'] = str(int(reset_time))
        
        # 로깅
        logger.warning(f"Rate limit exceeded: retry_after={retry_after}s")
        
        return response

# 사용법 예시
# settings.py
RATE_LIMITS = {
    'default': {'requests': 1000, 'window': 3600},
    'api': {'requests': 100, 'window': 60},
    'auth': {'requests': 5, 'window': 300},
    'heavy': {'requests': 10, 'window': 60},  # 무거운 작업용
}

PATH_RATE_LIMITS = {
    '/api/auth/': 'auth',
    '/api/reports/': 'heavy',
    '/api/': 'api',
}

RATE_LIMIT_WHITELIST = [
    '127.0.0.1',  # 로컬호스트
    '10.0.0.0/8',  # 내부 네트워크
]
```

### 3. 보안 및 접근 제어 미들웨어

```python
# middleware/security.py
import re
import logging
import hashlib
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.contrib.gis.geoip2 import GeoIP2
from django.core.exceptions import SuspiciousOperation

logger = logging.getLogger('security')

class SecurityMiddleware(MiddlewareMixin):
    """종합 보안 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 의심스러운 패턴들
        self.suspicious_patterns = [
            r'(?i)(union.*select|select.*from|insert.*into|update.*set|delete.*from)',  # SQL Injection
            r'(?i)(<script|javascript:|onload=|onerror=)',  # XSS
            r'(?i)(\.\.\/|\.\.\\|%2e%2e%2f)',  # Path Traversal
            r'(?i)(eval\(|base64_decode|exec\()',  # Code Injection
        ]
        
        # 차단할 User-Agent 패턴
        self.blocked_user_agents = [
            r'(?i)(bot|crawler|spider|scraper)',  # 봇
            r'(?i)(sqlmap|nmap|nikto|burp)',  # 해킹 도구
        ]
        
        # 지역 차단 설정
        self.blocked_countries = getattr(settings, 'BLOCKED_COUNTRIES', [])
        self.allowed_countries = getattr(settings, 'ALLOWED_COUNTRIES', [])
        
        super().__init__(get_response)
    
    def process_request(self, request):
        """요청 보안 검사"""
        
        # 1. IP 기반 차단 검사
        if self.is_ip_blocked(request):
            return self.security_block_response("IP blocked")
        
        # 2. 지역 기반 차단 검사
        if self.is_geo_blocked(request):
            return self.security_block_response("Geographic restriction")
        
        # 3. User-Agent 검사
        if self.is_user_agent_blocked(request):
            return self.security_block_response("User agent blocked")
        
        # 4. 의심스러운 페이로드 검사
        if self.has_suspicious_payload(request):
            return self.security_block_response("Suspicious payload detected")
        
        # 5. 요청 빈도 기반 어뷰즈 검사
        if self.is_abuse_detected(request):
            return self.security_block_response("Abuse detected")
        
        return None
    
    def is_ip_blocked(self, request):
        """IP 차단 목록 검사"""
        client_ip = self.get_client_ip(request)
        
        # Redis에서 차단된 IP 확인
        blocked_key = f"blocked_ip:{client_ip}"
        if cache.get(blocked_key):
            logger.warning(f"Blocked IP access attempt: {client_ip}")
            return True
        
        # 설정에서 차단 IP 확인
        blocked_ips = getattr(settings, 'BLOCKED_IPS', [])
        if client_ip in blocked_ips:
            return True
        
        return False
    
    def is_geo_blocked(self, request):
        """지역 기반 차단 검사"""
        if not (self.blocked_countries or self.allowed_countries):
            return False
        
        try:
            client_ip = self.get_client_ip(request)
            if client_ip in ['127.0.0.1', 'localhost']:
                return False
            
            g = GeoIP2()
            country_code = g.country_code(client_ip)
            
            # 허용 국가 목록이 있는 경우
            if self.allowed_countries:
                if country_code not in self.allowed_countries:
                    logger.warning(f"Geographic access denied: {country_code} from {client_ip}")
                    return True
            
            # 차단 국가 목록 검사
            if country_code in self.blocked_countries:
                logger.warning(f"Blocked country access: {country_code} from {client_ip}")
                return True
                
        except Exception as e:
            logger.error(f"GeoIP lookup failed: {e}")
        
        return False
    
    def is_user_agent_blocked(self, request):
        """User-Agent 차단 검사"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        for pattern in self.blocked_user_agents:
            if re.search(pattern, user_agent):
                logger.warning(f"Blocked user agent: {user_agent}")
                return True
        
        return False
    
    def has_suspicious_payload(self, request):
        """의심스러운 페이로드 검사"""
        
        # GET 파라미터 검사
        for key, value in request.GET.items():
            if self.is_suspicious_string(value):
                logger.warning(f"Suspicious GET parameter: {key}={value}")
                return True
        
        # POST 데이터 검사
        if hasattr(request, 'body') and request.body:
            try:
                body_str = request.body.decode('utf-8', errors='ignore')
                if self.is_suspicious_string(body_str):
                    logger.warning(f"Suspicious POST data detected")
                    return True
            except Exception:
                pass
        
        # URL 경로 검사
        if self.is_suspicious_string(request.path):
            logger.warning(f"Suspicious URL path: {request.path}")
            return True
        
        return False
    
    def is_suspicious_string(self, text):
        """문자열에서 의심스러운 패턴 검사"""
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def is_abuse_detected(self, request):
        """어뷰즈 패턴 검사"""
        client_ip = self.get_client_ip(request)
        
        # 분당 요청 수 체크
        minute_key = f"requests_per_minute:{client_ip}:{int(time.time() // 60)}"
        requests_count = cache.get(minute_key, 0)
        
        if requests_count > 120:  # 분당 120요청 초과
            logger.warning(f"High request rate detected: {client_ip} - {requests_count} req/min")
            
            # IP 일시 차단
            cache.set(f"blocked_ip:{client_ip}", True, timeout=300)  # 5분 차단
            return True
        
        # 요청 카운트 증가
        cache.set(minute_key, requests_count + 1, timeout=120)
        
        return False
    
    def get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def security_block_response(self, reason):
        """보안 차단 응답"""
        logger.error(f"Security block: {reason}")
        
        # API 요청인지 확인
        if self.is_api_request():
            return JsonResponse({
                'error': 'Access denied',
                'code': 'SECURITY_BLOCK'
            }, status=403)
        
        return HttpResponseForbidden("Access denied")
    
    def is_api_request(self, request=None):
        """API 요청 여부 확인"""
        if request and request.path.startswith('/api/'):
            return True
        return False
    
    def process_response(self, request, response):
        """보안 헤더 추가"""
        
        # 기본 보안 헤더들
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
        
        # 개발환경이 아닌 경우 HSTS 헤더 추가
        if not settings.DEBUG:
            security_headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        for header, value in security_headers.items():
            if header not in response:
                response[header] = value
        
        return response

# 보안 로깅을 위한 추가 미들웨어
class SecurityLoggingMiddleware(MiddlewareMixin):
    """보안 이벤트 로깅 미들웨어"""
    
    def process_exception(self, request, exception):
        """예외 발생 시 보안 로깅"""
        
        if isinstance(exception, SuspiciousOperation):
            logger.error(
                f"Suspicious operation: {exception} from {self.get_client_ip(request)}"
            )
        
        return None
    
    def get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### 4. 캐싱 및 압축 미들웨어

```python
# middleware/caching.py
import gzip
import hashlib
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.cache import get_cache_key
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger('caching')

class SmartCachingMiddleware(MiddlewareMixin):
    """지능형 캐싱 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = getattr(settings, 'CACHE_MIDDLEWARE_SECONDS', 600)
        self.cache_anonymous_only = getattr(settings, 'CACHE_ANONYMOUS_ONLY', True)
        super().__init__(get_response)
    
    def process_request(self, request):
        """캐시된 응답 확인"""
        
        # 캐시 대상인지 확인
        if not self.should_cache_request(request):
            return None
        
        # 캐시 키 생성
        cache_key = self.generate_cache_key(request)
        
        # 캐시에서 응답 조회
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug(f"Cache hit: {cache_key}")
            
            # 캐시된 응답을 HttpResponse로 변환
            response = HttpResponse(
                cached_response['content'],
                status=cached_response['status_code'],
                content_type=cached_response['content_type']
            )
            
            # 캐시 헤더 추가
            response['X-Cache'] = 'HIT'
            response['X-Cache-Key'] = cache_key[:32]  # 보안상 일부만
            
            return response
        
        return None
    
    def process_response(self, request, response):
        """응답 캐싱"""
        
        # 캐시 대상인지 확인
        if not self.should_cache_response(request, response):
            response['X-Cache'] = 'SKIP'
            return response
        
        # 캐시 키 생성
        cache_key = self.generate_cache_key(request)
        
        # 응답 데이터 준비
        cached_data = {
            'content': response.content,
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', 'text/html'),
        }
        
        # 캐시에 저장
        cache.set(cache_key, cached_data, self.cache_timeout)
        
        # 캐시 헤더 추가
        response['X-Cache'] = 'MISS'
        response['X-Cache-Timeout'] = str(self.cache_timeout)
        
        logger.debug(f"Cached response: {cache_key}")
        
        return response
    
    def should_cache_request(self, request):
        """요청 캐싱 여부 결정"""
        
        # GET 요청만 캐시
        if request.method != 'GET':
            return False
        
        # 인증된 사용자는 캐시하지 않음 (옵션)
        if self.cache_anonymous_only and hasattr(request, 'user') and request.user.is_authenticated:
            return False
        
        # 특정 경로는 캐시하지 않음
        no_cache_paths = getattr(settings, 'NO_CACHE_PATHS', ['/admin/', '/api/'])
        for path in no_cache_paths:
            if request.path.startswith(path):
                return False
        
        return True
    
    def should_cache_response(self, request, response):
        """응답 캐싱 여부 결정"""
        
        # 요청이 캐시 대상이 아니면 응답도 캐시하지 않음
        if not self.should_cache_request(request):
            return False
        
        # 성공적인 응답만 캐시
        if response.status_code != 200:
            return False
        
        # Cache-Control 헤더 확인
        cache_control = response.get('Cache-Control', '')
        if 'no-cache' in cache_control or 'no-store' in cache_control:
            return False
        
        # 응답 크기가 너무 크면 캐시하지 않음
        max_cache_size = getattr(settings, 'MAX_CACHE_SIZE', 1024 * 1024)  # 1MB
        if len(response.content) > max_cache_size:
            return False
        
        return True
    
    def generate_cache_key(self, request):
        """캐시 키 생성"""
        
        # 기본 키 구성 요소
        key_parts = [
            request.path,
            request.META.get('QUERY_STRING', ''),
        ]
        
        # 사용자별 캐시가 필요한 경우
        if hasattr(request, 'user') and request.user.is_authenticated:
            key_parts.append(f"user:{request.user.id}")
        
        # 언어별 캐시
        if hasattr(request, 'LANGUAGE_CODE'):
            key_parts.append(f"lang:{request.LANGUAGE_CODE}")
        
        # Accept-Encoding 헤더 (압축 여부)
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' in accept_encoding:
            key_parts.append('gzip')
        
        # 키 생성
        key_string = '|'.join(key_parts)
        cache_key = f"smart_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
        
        return cache_key

class CompressionMiddleware(MiddlewareMixin):
    """응답 압축 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.min_length = getattr(settings, 'COMPRESSION_MIN_LENGTH', 1024)  # 1KB
        super().__init__(get_response)
    
    def process_response(self, request, response):
        """응답 압축 처리"""
        
        # 압축 대상인지 확인
        if not self.should_compress(request, response):
            return response
        
        # Gzip 압축
        if 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', ''):
            compressed_content = gzip.compress(response.content)
            
            # 압축 효과가 있는 경우만 적용
            if len(compressed_content) < len(response.content):
                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))
                
                # 압축률 로깅
                compression_ratio = len(compressed_content) / len(response.content) * 100
                logger.debug(f"Compressed response: {compression_ratio:.1f}% of original size")
        
        return response
    
    def should_compress(self, request, response):
        """압축 여부 결정"""
        
        # 이미 압축된 응답은 제외
        if response.get('Content-Encoding'):
            return False
        
        # 응답 크기가 최소 크기보다 작으면 제외
        if len(response.content) < self.min_length:
            return False
        
        # 압축 가능한 Content-Type인지 확인
        content_type = response.get('Content-Type', '').lower()
        compressible_types = [
            'text/', 'application/json', 'application/javascript',
            'application/xml', 'application/rss+xml'
        ]
        
        if not any(content_type.startswith(ct) for ct in compressible_types):
            return False
        
        return True
```

## 🎛️ 미들웨어 최적화 및 고려사항

### 1. 성능 최적화

```python
# middleware/optimized.py
import cProfile
import pstats
from io import StringIO
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class OptimizedMiddleware(MiddlewareMixin):
    """성능 최적화된 미들웨어 베이스"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 프로파일링 설정
        self.enable_profiling = getattr(settings, 'ENABLE_PROFILING', False)
        
        # 캐시 설정
        self._cache = {}
        self._cache_max_size = 1000
        
        super().__init__(get_response)
    
    def __call__(self, request):
        """최적화된 호출 메서드"""
        
        if self.enable_profiling:
            # 프로파일링과 함께 실행
            profiler = cProfile.Profile()
            profiler.enable()
            
            response = self.get_response(request)
            
            profiler.disable()
            self.log_profiling_results(profiler, request)
            
        else:
            # 일반 실행
            response = self.get_response(request)
        
        return response
    
    def cached_property(self, key, factory_func):
        """간단한 메모리 캐시"""
        if key not in self._cache:
            if len(self._cache) >= self._cache_max_size:
                # LRU 정책으로 가장 오래된 항목 제거
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[key] = factory_func()
        
        return self._cache[key]
    
    def log_profiling_results(self, profiler, request):
        """프로파일링 결과 로깅"""
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)  # 상위 10개만
        
        logger.debug(f"Profiling for {request.path}:\n{s.getvalue()}")

# 미들웨어 순서 최적화 가이드
OPTIMIZED_MIDDLEWARE = [
    # 1. 보안 관련 (가장 먼저)
    'django.middleware.security.SecurityMiddleware',
    'myproject.middleware.SecurityMiddleware',
    
    # 2. 세션 (인증보다 먼저)
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # 3. 공통 처리
    'django.middleware.common.CommonMiddleware',
    
    # 4. CSRF (폼 처리 전)
    'django.middleware.csrf.CsrfViewMiddleware',
    
    # 5. 인증
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # 6. 레이트 리미팅 (인증 후)
    'myproject.middleware.RateLimitingMiddleware',
    
    # 7. 성능 모니터링
    'myproject.middleware.PerformanceMonitoringMiddleware',
    
    # 8. 캐싱 (가장 나중에)
    'myproject.middleware.SmartCachingMiddleware',
    
    # 9. 압축 (응답 처리 마지막)
    'myproject.middleware.CompressionMiddleware',
]
```

### 2. 에러 처리 및 로깅

```python
# middleware/error_handling.py
import traceback
import sys
from django.http import JsonResponse, HttpResponseServerError
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('error_handling')

class ErrorHandlingMiddleware(MiddlewareMixin):
    """통합 에러 처리 미들웨어"""
    
    def process_exception(self, request, exception):
        """예외 처리"""
        
        # 에러 정보 수집
        error_info = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'path': request.path,
            'method': request.method,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'traceback': traceback.format_exc()
        }
        
        # 에러 로깅
        logger.error(f"Unhandled exception: {error_info}")
        
        # 개발환경이 아닌 경우 상세 에러 정보 숨김
        if settings.DEBUG:
            return None  # Django 기본 에러 페이지 사용
        
        # API 요청 여부 확인
        if self.is_api_request(request):
            return JsonResponse({
                'error': 'Internal server error',
                'code': 'INTERNAL_ERROR',
                'request_id': self.generate_request_id(request)
            }, status=500)
        
        # 일반 웹 요청
        return HttpResponseServerError("Internal server error occurred.")
    
    def get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_api_request(self, request):
        """API 요청 여부 확인"""
        return request.path.startswith('/api/')
    
    def generate_request_id(self, request):
        """요청 ID 생성"""
        import uuid
        return str(uuid.uuid4())[:8]
```

### 3. 테스트 및 디버깅

```python
# tests/test_middleware.py
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from myproject.middleware import (
    PerformanceMonitoringMiddleware,
    RateLimitingMiddleware,
    SecurityMiddleware
)

class MiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_performance_middleware(self):
        """성능 모니터링 미들웨어 테스트"""
        middleware = PerformanceMonitoringMiddleware(lambda req: HttpResponse("OK"))
        
        request = self.factory.get('/test/')
        request.user = self.user
        
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Response-Time', response)
    
    @patch('myproject.middleware.cache')
    def test_rate_limiting_middleware(self, mock_cache):
        """레이트 리미팅 미들웨어 테스트"""
        # 캐시 모킹
        mock_cache.get.return_value = []
        mock_cache.set.return_value = True
        
        middleware = RateLimitingMiddleware(lambda req: HttpResponse("OK"))
        
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-RateLimit-Remaining', response)
    
    def test_security_middleware_blocks_sql_injection(self):
        """보안 미들웨어 SQL 인젝션 차단 테스트"""
        middleware = SecurityMiddleware(lambda req: HttpResponse("OK"))
        
        # SQL 인젝션 시도
        request = self.factory.get('/test/?id=1 UNION SELECT * FROM users')
        
        response = middleware(request)
        
        self.assertEqual(response.status_code, 403)

# 디버깅용 미들웨어
class DebugMiddleware(MiddlewareMixin):
    """디버깅용 미들웨어"""
    
    def process_request(self, request):
        if settings.DEBUG:
            print(f"Request: {request.method} {request.path}")
            print(f"Headers: {dict(request.META)}")
    
    def process_response(self, request, response):
        if settings.DEBUG:
            print(f"Response: {response.status_code}")
            print(f"Headers: {dict(response.items())}")
        return response
```

## 📋 미들웨어 베스트 프랙티스

### 1. 개발 가이드라인

```python
# 미들웨어 개발 체크리스트
MIDDLEWARE_CHECKLIST = {
    '성능': [
        '무거운 연산은 process_request에서 피하기',
        '데이터베이스 쿼리 최소화',
        '캐싱 적극 활용',
        '조건부 실행으로 불필요한 처리 방지'
    ],
    '보안': [
        '사용자 입력 검증',
        '민감한 정보 로깅 금지',
        'SQL 인젝션, XSS 방어',
        '에러 메시지에서 정보 유출 방지'
    ],
    '안정성': [
        '예외 처리 철저히',
        '기본값 설정',
        '롤백 메커니즘 구현',
        '의존성 최소화'
    ],
    '확장성': [
        '설정 가능한 매개변수',
        '플러그인 아키텍처',
        '이벤트 기반 설계',
        '모니터링 지원'
    ]
}
```

### 2. 운영 고려사항

```python
# settings/production.py
# 운영환경 미들웨어 설정

# 미들웨어 활성화/비활성화
PERFORMANCE_MONITORING_ENABLED = True
RATE_LIMITING_ENABLED = True
SECURITY_MIDDLEWARE_ENABLED = True
CACHING_MIDDLEWARE_ENABLED = True

# 성능 임계값
SLOW_REQUEST_THRESHOLD = 2.0  # 2초
DB_QUERY_THRESHOLD = 20       # 20개 쿼리

# 레이트 리미팅
RATE_LIMITS = {
    'api': {'requests': 1000, 'window': 3600},
    'auth': {'requests': 10, 'window': 300},
}

# 보안 설정
BLOCKED_COUNTRIES = ['CN', 'RU']  # 예시
SECURITY_ALERTS_ENABLED = True

# 로깅 설정
LOGGING = {
    'version': 1,
    'handlers': {
        'middleware': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/middleware.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'performance': {'handlers': ['middleware'], 'level': 'INFO'},
        'security': {'handlers': ['middleware'], 'level': 'WARNING'},
        'rate_limiting': {'handlers': ['middleware'], 'level': 'INFO'},
    },
}
```

## 🎯 결론

Django 커스텀 미들웨어는 애플리케이션의 **횡단 관심사**를 효율적으로 처리할 수 있는 강력한 도구입니다. 

### 핵심 포인트

1. **성능 최적화**: 요청/응답 처리 시간 모니터링과 최적화
2. **보안 강화**: 다층 보안 검사와 위협 탐지
3. **운영 효율성**: 자동화된 모니터링과 알림 시스템
4. **확장성**: 설정 기반의 유연한 기능 조정

### 실무 적용 팁

- **미들웨어 순서**가 중요합니다. 의존성을 고려하여 배치하세요.
- **성능 영향**을 최소화하기 위해 조건부 실행을 활용하세요.
- **에러 처리**를 철저히 하여 미들웨어 장애가 전체 시스템에 영향을 주지 않도록 하세요.
- **모니터링과 로깅**을 통해 미들웨어의 효과를 지속적으로 측정하세요.

잘 설계된 커스텀 미들웨어는 Django 애플리케이션의 **안정성, 보안성, 성능**을 크게 향상시킬 수 있습니다. 각 프로젝트의 요구사항에 맞게 적절히 조합하여 사용하시기 바랍니다! 🚀