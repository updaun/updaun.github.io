---
layout: post
title: "Django DB 커넥션 관리 완전 가이드: 기초부터 최적화까지"
date: 2025-07-17 10:00:00 +0900
categories: [Django, Python, Database, Performance]
tags: [Django, Database, Connection, PostgreSQL, MySQL, SQLite, Performance, Optimization, CONN_MAX_AGE, Connection Pooling]
---

Django로 개발하면서 데이터베이스 성능 이슈에 부딪힌 적이 있나요? 많은 개발자들이 Django의 데이터베이스 커넥션 관리를 제대로 이해하지 못해 성능 문제를 겪고 있습니다. 이 글에서는 Django의 데이터베이스 커넥션 관리에 대해 기초부터 고급 최적화 기법까지 단계별로 알아보겠습니다.

## 📚 Django DB 커넥션의 기본 이해

### Django는 어떻게 데이터베이스에 연결하는가?

Django는 기본적으로 **autocommit 모드**로 동작합니다. 이는 각 SQL 쿼리가 실행될 때마다 자동으로 트랜잭션이 시작되고 완료된다는 의미입니다.

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**커넥션 생성 과정:**
1. Django가 첫 번째 데이터베이스 쿼리를 실행할 때 커넥션을 생성
2. 요청이 끝날 때까지 해당 커넥션을 재사용
3. 기본적으로 요청이 끝나면 커넥션을 닫음

### 전통적인 커넥션 관리의 문제점

```python
# 문제가 되는 시나리오
def my_view(request):
    # 첫 번째 쿼리에서 커넥션 생성
    users = User.objects.all()
    
    # 동일한 커넥션 재사용
    posts = Post.objects.filter(author__in=users)
    
    # 뷰가 끝나면 커넥션 닫힘
    return render(request, 'template.html', {'posts': posts})
    
# 다음 요청에서는 새로운 커넥션 생성 (비효율적!)
```

**문제점:**
- 매 요청마다 새로운 커넥션 생성/해제
- 커넥션 생성 오버헤드
- 데이터베이스 서버 리소스 낭비

## 🔧 CONN_MAX_AGE: 지속적 커넥션의 핵심

### CONN_MAX_AGE 설정 이해하기

`CONN_MAX_AGE`는 Django에서 가장 중요한 커넥션 설정입니다:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # 10분 (초 단위)
    }
}
```

**설정값별 의미:**
- `0` (기본값): 매 요청 후 커넥션 닫기
- `양수`: 지정된 시간(초) 동안 커넥션 유지
- `None`: 무제한 지속 커넥션 (권장하지 않음)

### 실전 CONN_MAX_AGE 최적화

```python
# 환경별 설정 예시
import os

# 개발 환경
if DEBUG:
    CONN_MAX_AGE = 0  # 개발시에는 비활성화
    
# 운영 환경
else:
    CONN_MAX_AGE = 300  # 5분 추천
    
# 고트래픽 환경
if os.environ.get('HIGH_TRAFFIC'):
    CONN_MAX_AGE = 600  # 10분
```

**주의사항:**
⚠️ **개발 서버에서는 사용하지 마세요!** 개발 서버는 매 요청마다 새로운 스레드를 생성하므로 지속적 커넥션의 효과가 없습니다.

## 🏥 CONN_HEALTH_CHECKS: 커넥션 건강 관리

### 커넥션 건강 체크의 필요성

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,  # 커넥션 건강 체크 활성화
    }
}
```

**건강 체크가 필요한 상황:**
- 데이터베이스 서버 재시작 후
- 네트워크 연결 불안정
- 로드 밸런서에 의한 커넥션 타임아웃

### 커넥션 건강 체크 동작 원리

```python
# Django 내부 동작 (의사 코드)
def get_connection():
    if hasattr(local, 'connection'):
        if CONN_HEALTH_CHECKS:
            if not connection.is_usable():
                connection.close()
                connection = create_new_connection()
        return connection
    else:
        return create_new_connection()
```

## 🎯 데이터베이스별 커넥션 최적화

### PostgreSQL 최적화

PostgreSQL은 Django에서 가장 권장되는 데이터베이스입니다:

```python
# PostgreSQL 최적화 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            # 커넥션 풀링 (Django 5.1+)
            'pool': {
                'min_size': 1,
                'max_size': 10,
            },
            # 서버사이드 커서 비활성화 (PgBouncer 사용시)
            'server_side_binding': False,
        },
    }
}
```

**PostgreSQL 커넥션 풀링 (Django 5.1+):**
```python
# psycopg3 with connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'pool': True,  # 기본 설정 사용
            # 또는 세부 설정
            'pool': {
                'min_size': 2,
                'max_size': 10,
                'timeout': 30,
            }
        },
    }
}
```

### MySQL/MariaDB 최적화

```python
# MySQL 최적화 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '3306',
        'CONN_MAX_AGE': 300,  # MySQL은 짧게 설정 추천
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'autocommit': True,
        },
    }
}
```

### SQLite 특별 고려사항

```python
# SQLite 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 0,  # SQLite는 지속 커넥션 비권장
        'OPTIONS': {
            'timeout': 20,  # 락 타임아웃 설정
            'init_command': 'PRAGMA synchronous=NORMAL;',  # 성능 최적화
        },
    }
}
```

**SQLite 제한사항:**
- 동시 쓰기 작업 제한
- 멀티스레드 환경에서 잠금 문제
- 지속적 커넥션 효과 제한적

## 🔄 트랜잭션과 커넥션 관리

### 기본 트랜잭션 동작

```python
# Django의 기본 autocommit 모드
from django.db import transaction

def basic_operation():
    # 각 쿼리가 별도 트랜잭션으로 실행
    user = User.objects.create(username='john')  # 즉시 커밋
    profile = Profile.objects.create(user=user)  # 즉시 커밋
```

### ATOMIC_REQUESTS 설정

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'ATOMIC_REQUESTS': True,  # 모든 뷰를 트랜잭션으로 래핑
    }
}
```

**ATOMIC_REQUESTS 주의사항:**
```python
@transaction.non_atomic_requests
def long_running_view(request):
    # 트랜잭션 없이 실행하고 싶은 뷰
    # 대용량 데이터 처리나 외부 API 호출시 유용
    process_large_dataset()
    return JsonResponse({'status': 'success'})
```

### 수동 트랜잭션 관리

```python
from django.db import transaction

# 데코레이터 방식
@transaction.atomic
def create_user_with_profile(username, email):
    user = User.objects.create(username=username, email=email)
    Profile.objects.create(user=user)
    return user

# 컨텍스트 매니저 방식
def complex_operation():
    # 이 부분은 autocommit 모드
    initial_data = SomeModel.objects.all()
    
    with transaction.atomic():
        # 이 블록은 하나의 트랜잭션
        user = User.objects.create(username='john')
        try:
            with transaction.atomic():  # 중첩 트랜잭션 (savepoint)
                Profile.objects.create(user=user, bio='Test')
        except IntegrityError:
            # 내부 트랜잭션만 롤백, user는 유지
            pass
    
    # 다시 autocommit 모드
    log_operation('completed')
```

## ⚡ 커넥션 풀링과 성능 최적화

### 외부 커넥션 풀링 솔루션

#### 1. PgBouncer (PostgreSQL)

```bash
# PgBouncer 설정 예시
[databases]
myproject = host=localhost port=5432 dbname=myproject

[pgbouncer]
listen_port = 6432
listen_addr = localhost
auth_type = trust
pool_mode = transaction
max_client_conn = 100
default_pool_size = 25
```

```python
# Django 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '6432',  # PgBouncer 포트
        'CONN_MAX_AGE': 0,  # PgBouncer 사용시 비활성화
        'OPTIONS': {
            'DISABLE_SERVER_SIDE_CURSORS': True,  # 필수!
        },
    }
}
```

#### 2. Django-connection-pool

```bash
pip install django-connection-pool
```

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',  # 풀링 백엔드
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 10,
            'RECYCLE': 24 * 60 * 60,  # 24시간
        }
    }
}
```

### 성능 모니터링 및 측정

```python
# 커넥션 상태 모니터링
import time
from django.db import connection
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # 커넥션 정보 확인
        print(f"Connection vendor: {connection.vendor}")
        print(f"Connection settings: {connection.settings_dict}")
        
        # 쿼리 수행 시간 측정
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_user")
            result = cursor.fetchone()
        
        execution_time = time.time() - start_time
        print(f"Query time: {execution_time:.4f} seconds")
        print(f"Query count: {len(connection.queries)}")
```

## 🐛 일반적인 문제와 해결방법

### 1. "Database connection isn't set to UTC" 경고

```python
# 해결방법
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'TIME_ZONE': 'UTC',  # 명시적 설정
    }
}

# 또는 USE_TZ 설정 확인
USE_TZ = True
TIME_ZONE = 'UTC'
```

### 2. "Connection already closed" 오류

```python
# 문제가 되는 코드
def problematic_view(request):
    users = User.objects.all()
    connection.close()  # 수동으로 커넥션 닫기
    # 이후 쿼리에서 오류 발생
    posts = Post.objects.all()

# 해결방법: 수동으로 커넥션을 닫지 않기
def fixed_view(request):
    users = User.objects.all()
    posts = Post.objects.all()
    # Django가 자동으로 커넥션 관리
```

### 3. 메모리 누수 방지

```python
from django.db import connections

def cleanup_connections():
    """장시간 실행되는 프로세스에서 사용"""
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()

# 또는 명시적으로 오래된 커넥션 정리
from django.db import close_old_connections

def long_running_task():
    for i in range(1000):
        # 작업 수행
        process_item(i)
        
        # 주기적으로 오래된 커넥션 정리
        if i % 100 == 0:
            close_old_connections()
```

## 🏭 운영 환경 최적화 전략

### 환경별 설정 관리

```python
# settings/base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# settings/development.py
DATABASES['default'].update({
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
})

# settings/production.py
DATABASES['default'].update({
    'CONN_MAX_AGE': 600,
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {
        'MAX_CONNS': 20,
        'MIN_CONNS': 5,
    }
})
```

### 로드 밸런싱 환경에서의 고려사항

```python
# 읽기/쓰기 분리
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'write_user',
        'PASSWORD': 'password',
        'HOST': 'primary-db.example.com',
        'PORT': '5432',
        'CONN_MAX_AGE': 300,
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'read_user',
        'PASSWORD': 'password',
        'HOST': 'replica-db.example.com',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # 읽기 전용이므로 더 길게
    }
}

# 데이터베이스 라우터
class DatabaseRouter:
    def db_for_read(self, model, **hints):
        return 'replica'
    
    def db_for_write(self, model, **hints):
        return 'default'
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'

DATABASE_ROUTERS = ['myapp.routers.DatabaseRouter']
```

### 모니터링 및 알림 설정

```python
# 커스텀 미들웨어로 커넥션 모니터링
import logging
from django.db import connections

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 요청 전 커넥션 수 체크
        initial_queries = len(connections['default'].queries)
        
        response = self.get_response(request)
        
        # 요청 후 쿼리 수 체크
        final_queries = len(connections['default'].queries)
        query_count = final_queries - initial_queries
        
        # 임계값 초과시 로깅
        if query_count > 50:
            logger.warning(
                f"High query count detected: {query_count} queries "
                f"for {request.path}"
            )
        
        return response
```

## 📊 성능 벤치마킹

### 커넥션 설정별 성능 비교

```python
import time
from django.test import TestCase
from django.db import connection
from django.contrib.auth.models import User

class ConnectionPerformanceTest(TestCase):
    def test_connection_reuse_performance(self):
        """커넥션 재사용 성능 테스트"""
        
        # CONN_MAX_AGE = 0 (매번 새 커넥션)
        start_time = time.time()
        for i in range(100):
            User.objects.count()
            connection.close()  # 강제로 커넥션 닫기
        no_reuse_time = time.time() - start_time
        
        # CONN_MAX_AGE > 0 (커넥션 재사용)
        start_time = time.time()
        for i in range(100):
            User.objects.count()
            # 커넥션 재사용
        with_reuse_time = time.time() - start_time
        
        print(f"No reuse: {no_reuse_time:.4f}s")
        print(f"With reuse: {with_reuse_time:.4f}s")
        print(f"Improvement: {(no_reuse_time / with_reuse_time):.2f}x faster")
```

## 🎯 마무리: 커넥션 관리 체크리스트

### ✅ 기본 설정 체크리스트

- [ ] `CONN_MAX_AGE` 적절히 설정 (운영: 300-600초)
- [ ] `CONN_HEALTH_CHECKS` 활성화
- [ ] 개발 환경에서는 지속 커넥션 비활성화
- [ ] 데이터베이스별 최적 설정 적용

### ⚡ 성능 최적화 체크리스트

- [ ] 커넥션 풀링 고려 (PgBouncer, django-connection-pool)
- [ ] 읽기/쓰기 분리 구현
- [ ] 장시간 실행 프로세스에서 커넥션 정리
- [ ] 쿼리 수 모니터링 구현

### 🔒 보안 및 안정성 체크리스트

- [ ] 데이터베이스 커넥션 암호화 설정
- [ ] 커넥션 타임아웃 적절히 설정
- [ ] 에러 핸들링 및 로깅 구현
- [ ] 부하 테스트 및 모니터링 구축

Django의 데이터베이스 커넥션 관리는 애플리케이션 성능에 직접적인 영향을 미치는 중요한 요소입니다. 이 가이드를 통해 여러분의 Django 애플리케이션이 더욱 효율적이고 안정적으로 동작하기를 바랍니다.

## 📚 추가 학습 자료

- [Django 공식 문서 - Database](https://docs.djangoproject.com/en/stable/ref/databases/)
- [Django 트랜잭션 관리](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [PostgreSQL 커넥션 풀링](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PgBouncer 공식 문서](https://www.pgbouncer.org/)

---

💡 **팁**: 이 설정들을 프로덕션에 적용하기 전에 반드시 개발/스테이징 환경에서 충분히 테스트해보세요!
