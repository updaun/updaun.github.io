---
layout: post
title: "Django 데이터베이스 마이그레이션 전략 - 프로덕션 환경의 주의사항 완벽 가이드"
date: 2026-02-08
categories: django python database
author: updaun
image: "/assets/img/posts/2026-02-08-django-database-migration-strategy.webp"
---

# Django 데이터베이스 마이그레이션 전략

프로덕션 환경에서 데이터베이스는 서비스의 심장입니다. Django 개발자들이 가장 두려워하는 순간은 마이그레이션을 실행할 때입니다. 잘못된 마이그레이션은 서비스 중단, 데이터 손실, 롤백 불가능 상황까지 초래할 수 있습니다. 이 글에서는 2년간 100GB+ 규모의 데이터베이스를 관리하면서 익힌 마이그레이션 전략, 실제 사례, 그리고 프로덕션에서 안전하게 적용할 수 있는 방법들을 공유합니다.

## 1. 왜 마이그레이션 전략이 필요한가?

### 프로덕션 환경에서의 리스크

Django는 `python manage.py migrate`라는 간단한 명령어로 마이그레이션을 수행합니다. 하지만 이 명령어가 실행되는 순간:

```
- 테이블이 잠금(LOCK)됩니다
- 해당 테이블의 모든 쓰기 작업이 대기합니다
- DNS 조회, API 요청 등이 타임아웃될 수 있습니다
- 사용자는 "서비스가 응답하지 않음" 화면을 봅니다
```

예를 들어 100만 개의 행을 가진 테이블에 새로운 TEXT 컬럼을 추가한다면:

```sql
-- 이 쿼리는 최소 10~30초 이상 걸릴 수 있습니다
ALTER TABLE users ADD COLUMN bio TEXT;
```

이 30초 동안 users 테이블 전체가 WRITE LOCK이 걸려서 모든 로그인, 프로필 조회가 멈춥니다.

### 실제 사례: 대참사를 피한 경험담

저는 과거에 신경 쓰지 않고 피크 타임(오후 3시)에 마이그레이션을 실행했습니다. 업체 주문 수가 가장 많은 시간이었는데, 마이그레이션 때문에 30초간 모든 주문이 처리되지 않았습니다. 결과:

- 사용자 500명이 동시에 "주문 실패" 오류 경험
- 고객 센터에 항의 전화 폭주
- 결국 금전적 보상 발생

이 경험 이후로 리스크 기반의 마이그레이션 전략을 수립했고, 이후 2년간 마이그레이션으로 인한 장애는 한 번도 없었습니다.

## 2. 마이그레이션 난이도 분류 - 어떤 것이 위험한가?

모든 마이그레이션이 같은 위험도를 가지지 않습니다. 먼저 위험도부터 분류합시다.

### 그린존(Green Zone) - 완전히 안전한 마이그레이션

```python
# 1. 새 컬럼 추가 (DEFAULT 값 지정 + NOT NULL 미적용)
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='user',
            name='notification_enabled',
            field=models.BooleanField(default=True),
            preserve_default=True,  # 중요: 마이그레이션 후 DEFAULT 제거
        ),
    ]

# 2. 이미 사용되지 않는 컬럼/테이블 삭제
# (사전에 완전히 제거되었는지 확인 필요)

# 3. 데이터 검증 추가 (CHECK 제약조건)
migrations.RunSQL(
    sql="ALTER TABLE products ADD CONSTRAINT price_positive CHECK (price >= 0)",
)

# 4. Index 추가 (스캔 시간이 걸리지만 LOCK 거는 시간은 짧음)
migrations.AddIndex(
    model_name='order',
    index=models.Index(fields=['user', 'created_at']),
)
```

**특징:**
- 대부분 경우 밀리초 단위로 완료
- 실행 중 대기 시간 무시할 수 있음
- 안심하고 피크 타임에도 실행 가능

### 옐로우존(Yellow Zone) - 주의가 필요한 마이그레이션

```python
# 1. NOT NULL 제약조건 추가
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=20),
            # default 없이 NOT NULL로 변경 = 위험!
        ),
    ]

# 2. 큰 테이블에 컬럼 추가하면서 DEFAULT 없음
migrations.AddField(
    model_name='largetable',
    name='new_field',
    field=models.CharField(max_length=100),
    # 1000만 행이 있다면? 마이그레이션이 10분 이상 걸릴 수 있음
)

# 3. 데이터 마이그레이션 (RunPython)
def populate_calculated_field(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    for user in User.objects.all():  # 매우 위험 - 메모리 터질 수 있음
        user.calculated_field = user.first_name + user.last_name
        user.save()

migrations.RunPython(populate_calculated_field),
```

**특징:**
- 테이블 크기에 따라 LOCK 시간이 길어짐
- 데이터양이 많으면 메모리 부담
- 사전에 성능 테스트 필수
- 새벽 시간대 실행 권장

### 레드존(Red Zone) - 극도의 주의가 필요한 마이그레이션

```python
# 1. 대형 테이블에서 컬럼 삭제
migrations.RemoveField(
    model_name='user',
    name='old_payment_info',  # 1000만 행 테이블에서 삭제
)

# 2. 컬럼 타입 변경
migrations.AlterField(
    model_name='product',
    name='price',
    field=models.DecimalField(max_digits=10, decimal_places=2),
    # 기존: IntegerField → 변경: DecimalField (타입 전환 필요)
)

# 3. 유니크 제약조건 추가 (유효성 검증 없이)
migrations.AlterUniqueTogether(
    name='userprofile',
    unique_together={('user', 'profile_type')},
    # 중복 데이터가 있으면 실패
)

# 4. 완전한 데이터 마이그레이션
def complex_data_migration(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Category = apps.get_model('shop', 'Category')
    
    # 외부 API 호출
    for product in Product.objects.all():
        category = external_api.fetch_category(product.name)
        product.category = Category.objects.get(name=category)
        product.save()

migrations.RunPython(complex_data_migration, migrations.RunPython.noop),
```

**특징:**
- LOCK 시간이 매우 김 (수 분 ~ 수십 분)
- 롤백 불가능할 가능성 높음
- 프로덕션 배포 전 철저한 테스트 필수
- 다운타임 스케줄링 필요
- 또는 여유 시간에 천천히 진행 필요

## 3. 안전한 마이그레이션 전략 - 5가지 실전 방법

### 방법 1: Blue-Green 배포 + 마이그레이션

가장 안전한 방법은 별도의 데이터베이스에서 마이그레이션을 먼저 완료한 후, 트래픽을 전환하는 것입니다.

```python
# 시나리오: 기존 Django 앱 + 마이그레이션이 필요한 상황

# 1단계: 프로덕션 DB를 복제하여 새로운 환경 준비
# AWS RDS Console에서 스냅샷으로부터 새 DB 인스턴스 생성
# 또는 PostgreSQL: pg_dump로 복제
bash_command = """
pg_dump -h prod-db.rds.amazonaws.com -U admin production_db > backup.sql
psql -h new-db.rds.amazonaws.com -U admin production_db < backup.sql
"""

# 2단계: 새 환경에서 먼저 마이그레이션 실행
# 이 과정에서 오류가 발생해도 프로덕션에는 영향 없음

# 3단계: 새 환경에서 완전한 회귀 테스트 수행
# - 모든 API 엔드포인트 테스트
# - 데이터 무결성 검증
# - 성능 테스트 (쿼리 응답 시간 확인)

# 4단계: 데이터베이스 연결 정보 변경
# Django settings.py에서 DB 연결을 새 데이터베이스로 전환
# 또는 로드 밸런서에서 DNS를 변경

# 5단계: 모니터링
# 새 환경에서 모든 작동이 정상인지 5~10분간 모니터링
# 이상하면 이전 데이터베이스로 빠르게 롤백

# BlueGreen 구현 코드 예시
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'prod_db'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),  # 환경변수로 동적 변경 가능
        'PORT': '5432',
    }
}
"""
```

**장점:**
- 프로덕션 환경의 완벽한 안전성
- 빠른 롤백 가능 (수초)
- 실제 환경과 동일한 테스트

**단점:**
- 인프라 비용 (임시 DB 비용)
- 복제 시간 (대용량 DB는 30분 이상)
- 데이터 동기화 문제 (마이그레이션 중 발생한 변경사항 반영 필요)

### 방법 2: 점진적 마이그레이션 + Feature Flag

위험한 마이그레이션은 여러 단계로 나누어 진행합니다.

```python
# 예시: users 테이블에 user_type 컬럼 추가 (선택적 필드)

# PHASE 1: 프로덕션 환경에서 먼저 컬럼만 추가 (Default 값 포함)
# migrations/0002_add_user_type.py
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='user',
            name='user_type',
            field=models.CharField(
                max_length=20,
                default='regular',  # 중요: 기존 행들은 'regular'로 자동 설정
                choices=[('regular', 'Regular'), ('premium', 'Premium')]
            ),
            preserve_default=False,  # 마이그레이션 후 DEFAULT 제약 제거
        ),
    ]

# PHASE 2: 코드 배포 (하지만 아직 user_type을 사용하지 않음)
# models.py에 필드는 존재하지만, 비즈니스 로직에서 무시

# PHASE 3: Feature flag로 점진적 사용 활성화
# settings.py에 Feature flag 추가
FEATURES = {
    'use_user_type': os.getenv('FEATURE_USE_USER_TYPE', 'false').lower() == 'true'
}

# views.py에서 사용
def create_user(request):
    user = User.objects.create(
        email=request.data['email'],
        name=request.data['name'],
    )
    
    if settings.FEATURES['use_user_type']:
        user.user_type = request.data.get('user_type', 'regular')
        user.save()
    
    return Response({'id': user.id})

# PHASE 4: Feature flag를 5%, 10%, 25%, 50%, 100% 순서로 증가
# 각 단계에서 모니터링하며 문제 발생 시 즉시 off

# PHASE 5: 100% 적용 후 1주일 안정화 확인 후 컬럼 락 추가
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.CharField(
                max_length=20,
                null=False,  # 이제 NOT NULL 제약 추가 가능
            ),
        ),
    ]
```

**장점:**
- 위험을 최소화하며 점진적 배포
- 문제 발생 시 빠른 롤백
- 사용자 영향 최소화

**단점:**
- 배포 프로세스 복잡
- Feature flag 관리 필요

### 방법 3: Zero-Downtime 마이그레이션 패턴

대형 테이블에 컬럼을 추가할 때 가장 효과적인 방법:

```python
# 문제 상황: 1000만 행을 가진 orders 테이블에
# shipping_address 컬럼을 추가해야 함

# 기존(위험한) 방법:
class BadMigration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(null=True),
        ),
    ]
# 이 마이그레이션은 테이블 전체 복제로 5~10분 LOCK

# ✅ 안전한 방법: 3단계 마이그레이션
# STEP 1: 컬럼 추가 (NOT NULL 제약 없이)
class Step1AddColumn(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(null=True),  # NULL 허용
        ),
    ]

# STEP 2: 기존 데이터 채우기 (최적화된 배치 처리)
class Step2PopulateData(migrations.Migration):
    operations = [
        migrations.RunPython(populate_shipping_address_batch),
    ]

def populate_shipping_address_batch(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    batch_size = 10000
    
    # 쿼리 최적화: 배치 처리로 메모리 절약
    orders_qs = Order.objects.filter(shipping_address__isnull=True)
    total = orders_qs.count()
    
    for start in range(0, total, batch_size):
        end = start + batch_size
        batch = orders_qs[start:end]
        
        for order in batch:
            # 기존 청구 주소 사용
            order.shipping_address = order.billing_address
        
        Order.objects.bulk_update(batch, ['shipping_address'], batch_size=1000)
        print(f"Processed {end}/{total}")

# STEP 3: 데이터 검증 및 NOT NULL 제약 추가
class Step3AddConstraint(migrations.Migration):
    operations = [
        migrations.RunPython(validate_no_nulls),
        migrations.AlterField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(null=False),  # 이제 NOT NULL 가능
        ),
    ]

def validate_no_nulls(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    null_count = Order.objects.filter(shipping_address__isnull=True).count()
    if null_count > 0:
        raise ValueError(f"Still {null_count} orders with NULL shipping_address")
```

**배포 순서:**
```bash
# 월요일 낮: Step 1 (컬럼 추가, 빠름)
python manage.py migrate orders 0001

# 월요일 밤 10시: Step 2 (배치 처리, 서서히 진행)
python manage.py migrate orders 0002

# 화요일 아침: Step 3 (제약 추가, 빠름)
python manage.py migrate orders 0003

# 검증
python manage.py shell
>>> from orders.models import Order
>>> Order.objects.filter(shipping_address__isnull=True).count()
0  # 모두 채워졌음
```

**장점:**
- 각 단계가 대부분 빠르게 완료
- LOCK 시간 최소화
- 롤백 가능

### 방법 4: 캐시 계층을 활용한 무중단 마이그레이션

데이터 조회 성능이 중요한 경우:

```python
# 시나리오: products 테이블의 쿼리 응답이 느려짐
# 해결책: 캐시된 category_id 추가

# STEP 1: 마이그레이션으로 새 컬럼 추가
class AddCategoryIdCache(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='product',
            name='category_id_cached',
            field=models.IntegerField(null=True, db_index=True),
        ),
    ]

# STEP 2: 백그라운드 워커에서 점진적으로 채우기
# celery task 또는 management command
from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    def handle(self, *args, **options):
        # 배치 처리로 메모리 절약
        batch_size = 5000
        
        qs = Product.objects.filter(category_id_cached__isnull=True)
        total = qs.count()
        
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = qs[start:end]
            
            for product in batch:
                product.category_id_cached = product.category.id
            
            Product.objects.bulk_update(
                batch,
                ['category_id_cached'],
                batch_size=1000
            )
            
            self.stdout.write(f"Progress: {end}/{total}")

# STEP 3: 코드에서 캐시 필드 사용 시작
# managers.py
class ProductQuerySet(models.QuerySet):
    def with_category(self):
        # 캐시 필드가 null이면 JOIN, 아니면 캐시 필드 사용
        return self.annotate(
            cat_id=Case(
                When(category_id_cached__isnull=False),
                then=F('category_id_cached'),
                default=F('category_id'),
            )
        )

# STEP 4: 데이터 검증
def validate_cache_filled(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    null_count = Product.objects.filter(category_id_cached__isnull=True).count()
    if null_count > 0:
        raise ValueError(f"{null_count} products still have NULL cache")
```

**장점:**
- 기존 쿼리 영향 없음
- 백그라운드에서 천천히 처리
- 언제든 취소 더능

### 방법 5: 외부 마이그레이션 스크립트 (대용량 데이터용)

매우 큰 테이블(수천만 행)의 경우, Django 마이그레이션 대신 직접 SQL 스크립트 사용:

```python
# migrations/0005_large_table_migration.py
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="""
            -- PostgreSQL 최적화 쿼리 (CONCURRENTLY 사용으로 LOCK 최소화)
            CREATE INDEX CONCURRENTLY idx_orders_user_date 
            ON orders (user_id, created_at DESC);
            """,
            reverse_sql="DROP INDEX idx_orders_user_date;",
        ),
    ]

# 또는 별도 스크립트로 실행
# scripts/migrate_large_table.sql
"""
-- PostgreSQL에서 LOCK 최소화 마이그레이션
BEGIN;

-- 1. 새 테이블 생성 (변환 로직 포함)
CREATE TABLE orders_new AS
SELECT 
    id,
    user_id,
    created_at,
    CASE 
        WHEN status = 'pending' THEN 'waiting'
        WHEN status = 'completed' THEN 'done'
        ELSE status
    END AS status_normalized
FROM orders;

-- 2. 인덱스 생성
CREATE INDEX idx_orders_new_user ON orders_new(user_id);

-- 3. 테이블 스왑 (원자적)
ALTER TABLE orders RENAME TO orders_old;
ALTER TABLE orders_new RENAME TO orders;

-- 4. 제약조건 재생성
ALTER TABLE orders ADD CONSTRAINT pk_orders PRIMARY KEY (id);

COMMIT;
"""

# 실행 방법
# psql -h prod-db.amazonaws.com -U admin -d production_db -f migrate_large_table.sql
```

**장점:**
- 최대 성능 최적화
- PostgreSQL, MySQL 고급 기능 활용

## 4. 마이그레이션 전 필수 체크리스트

```python
# 1. 백업 확인
# ✅ 가장 최근 백업이 있는가?
import datetime
from django.db import connection

def check_backup():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT backup_date FROM backups ORDER BY backup_date DESC LIMIT 1"
        )
        latest_backup = cursor.fetchone()
        days_since = (datetime.now() - latest_backup[0]).days
        assert days_since <= 1, "Backup is older than 1 day!"

# 2. 마이그레이션 드라이 런
# ✅ 테스트 환경에서 먼저 실행
bash_command = """
# 테스트 DB 준비
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py migrate

# 또는 도커를 사용한 테스트
docker run -e DATABASE_URL=... myapp:latest python manage.py migrate
"""

# 3. 마이그레이션 시간 예측
# ✅ 프로덕션 데이터로 미리 테스트
def estimate_migration_time():
    from django.db import connection
    import time
    
    # 테스트 마이그레이션 로직 측정
    start = time.time()
    
    # 큰 배치 처리 테스트
    Order = apps.get_model('orders', 'Order')
    for _ in range(10000):  # 샘플
        Order.objects.latest('created_at')
    
    elapsed = (time.time() - start) / 10000
    estimated_total = elapsed * Order.objects.count()
    print(f"Estimated time: {estimated_total/60:.1f} minutes")

# 4. 모니터링 준비
# ✅ 마이그레이션 중 확인할 메트릭
monitoring_checklist = [
    "✅ CPU 사용률 (>90% 경고)",
    "✅ 디스크 I/O (초당 쓰기량)",
    "✅ 데이터베이스 연결 수",
    "✅ 쿼리 응답 시간",
    "✅ 애플리케이션 에러율",
    "✅ 사용자 리포트 모니터링",
]

# 5. 롤백 계획
# ✅ 마이그레이션 실패 시 복구 방법
rollback_plan = """
마이그레이션 실패 시:
1. 즉시 Django 애플리케이션 중단 (요청 처리 X)
2. 데이터베이스 백업 스냅샷으로부터 복구 시작
3. 애플리케이션 재시작
4. 데이터 무결성 검증
5. 사용자 공지
"""
```

## 5. 실전 마이그레이션 체크리스트

실제 마이그레이션 실행 전에 이 체크리스트를 반드시 확인하세요:

```
배포 전 (1일 전):
☐ 모든 팀원과 마이그레이션 계획 공유
☐ 마이그레이션 테스트 환경에서 완료
☐ 예상 소요 시간 문서화
☐ 롤백 절차 테스트
☐ 모니터링 대시보드 준비
☐ 고객 지원팀에 공지

배포 직전:
☐ 백업 확인 (최근 백업이 5분 이내인지 확인)
☐ 데이터베이스 연결 확인
☐ 프로덕션 환경에서 마이그레이션 순서 최종 확인
☐ 팀원과 실시간 커뮤니케이션 채널 열기

배포 중:
☐ 슬랙/디스코드 실시간 모니터링
☐ DB 연결 풀 상태 확인
☐ CPU, 메모리, I/O 모니터링
☐ 에러 로그 실시간 확인
☐ 사용자 리포트 대기

배포 후:
☐ 마이그레이션 정상 완료 확인
☐ 데이터 무결성 검증 쿼리 실행
☐ 애플리케이션 로그에서 마이그레이션 관련 에러 확인
☐ 성능 지표 확인
☐ 30분간 추가 모니터링
```

## 6. 마이그레이션 자동화 - CI/CD 통합

실수를 가장 잘 줄이는 방법은 자동화입니다:

```python
# .github/workflows/migration-check.yml
name: Migration Check

on: [pull_request]

jobs:
  check-migrations:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_PASSWORD: simple
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Check migrations
        env:
          DATABASE_URL: postgresql://postgres:simple@localhost:5432/test_db
        run: |
          # 1. 마이그레이션이 실제로 적용 가능한지 확인
          python manage.py migrate --check
          
          # 2. 마이그레이션 파일 이름 규칙 확인
          python scripts/validate_migration_names.py
          
          # 3. 만들어졌지만 적용되지 않은 마이그레이션 확인
          python manage.py makemigrations --check --dry-run
```

```python
# scripts/validate_migration_names.py
"""마이그레이션 파일 이름 규칙 검증"""
import os
import re
from pathlib import Path

MIGRATION_DIR = Path('myapp/migrations')
VALID_PATTERN = r'^\d{4}_[a-z_]+\.py$'

for file in MIGRATION_DIR.glob('*.py'):
    if file.name == '__init__.py':
        continue
    
    if not re.match(VALID_PATTERN, file.name):
        print(f"❌ Invalid migration name: {file.name}")
        print(f"   Expected format: 0001_description.py")
        exit(1)

print("✅ All migration names are valid")
```

## 7. 흔한 실수와 해결책

### 실수 1: 마이그레이션 순서 뒤바뀜

```python
# ❌ 실수: 자동으로 생성된 마이그레이션 순서가 잘못됨
# migrations/0002_auto_2024_02_15_0530.py:
#   - AddField(model='user', name='age')
#   - AlterField(model='user', name='email')  # age를 참조해야 하는데 아직 없음!

# ✅ 해결책: 수동으로 순서 정렬
# Django는 마이그레이션 번호 순서로 실행하므로,
# 올바른 의존성 순서로 수동 작성
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='user',
            name='age',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(unique=True),
        ),
    ]
```

### 실수 2: 마이그레이션 파일 직접 수정

```python
# ❌ 절대 금지: 이미 프로덕션에 적용된 마이그레이션 수정
# migrations/0001_initial.py를 실수로 수정 → 다른 환경과 불일치

# ✅ 해결책: 새로운 마이그레이션으로 수정사항 적용
# migrations/0003_fix_previous_mistake.py
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0002_add_field'),
    ]
    
    operations = [
        # 이전 실수를 수정하는 새로운 마이그레이션
        migrations.AlterField(
            model_name='user',
            name='age',
            field=models.IntegerField(default=18),  # 기본값 수정
        ),
    ]
```

### 실수 3: 마이그레이션 없이 모델 변경

```python
# ❌ 위험: 모델만 바꾸고 마이그레이션 미생성
class User(models.Model):
    email = models.EmailField()
    # 새 필드 추가했는데 makemigrations 안 함!
    phone = models.CharField(max_length=20)

# 결과: 
# - 로컬에서는 phone 사용 가능
# - 프로덕션에서는 phone 컬럼이 없어서 오류 발생
# - 데이터베이스 구조와 모델 정의 불일치

# ✅ 해결책: 항상 마이그레이션 생성
python manage.py makemigrations
python manage.py migrate
```

## 8. 프로덕션에서 마이그레이션 성능 모니터링

실제 마이그레이션 중 성능을 모니터링하는 코드:

```python
# management/commands/migrate_with_monitoring.py
from django.core.management.base import BaseCommand
from django.db import connection
import time
import psutil
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        start_time = time.time()
        
        # 마이그레이션 전 상태
        self.log_system_metrics()
        
        # 마이그레이션 실행
        call_command('migrate')
        
        # 마이그레이션 후 상태
        self.log_system_metrics()
        
        elapsed = time.time() - start_time
        self.stdout.write(
            f"✅ Migration completed in {elapsed:.2f} seconds"
        )
    
    def log_system_metrics(self):
        """시스템 메트릭 로깅"""
        process = psutil.Process()
        
        metrics = {
            'cpu_percent': process.cpu_percent(interval=1),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'db_connections': self.get_db_connection_count(),
        }
        
        logger.info(f"System metrics: {metrics}")
    
    def get_db_connection_count(self):
        """현재 DB 연결 수"""
        with connection.cursor() as cursor:
            if 'postgresql' in connection.settings_dict['ENGINE']:
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database()"
                )
                return cursor.fetchone()[0]
        return 0
```

## 결론: 안전한 마이그레이션 문화 만들기

2년간 100GB 이상의 대용량 데이터베이스를 관리하면서 배운 가장 중요한 교훈은:

**빠른 마이그레이션보다 안전한 마이그레이션이 중요하다**

마이그레이션으로 인한 장애는 복구 시간, 고객 신뢰도, 심리적 스트레스 측면에서 매우 큰 비용입니다. 따라서:

1. **마이그레이션을 계획하고 준비하는 데 시간을 투자하세요**
2. **작은 단계로 나누어 진행하세요**
3. **항상 롤백 계획을 준비하세요**
4. **자동화와 모니터링으로 인적 오류를 줄이세요**
5. **팀 전체가 마이그레이션 지식을 공유하세요**

이 가이드의 전략들을 따르면, 대규모 데이터베이스도 안전하게 발전시킬 수 있습니다.

---

**다음 글 예고:** Django ORM 성능 최적화 - 쿼리 분석과 인덱싱 전략
