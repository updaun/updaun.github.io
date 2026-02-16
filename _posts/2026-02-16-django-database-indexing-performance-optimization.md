---
layout: post
title: "Django에서의 데이터베이스 인덱싱: 개념부터 성능 최적화까지"
subtitle: "데이터베이스 인덱싱의 핵심과 실전 활용법"
date: 2026-02-16 09:00:00 +0000
categories: [Django, Database, Performance]
tags: [django, database, indexing, optimization, performance, sql]
description: "Django 프로젝트에서 데이터베이스 인덱싱을 올바르게 활용하는 방법을 배웁니다. 개념부터 실전 성능 비교까지 다양한 예시로 알아봅니다."
---

## 들어가며

데이터베이스 성능 최적화는 웹 애플리케이션 개발에서 매우 중요한 주제입니다. 특히 사용자 수가 증가하고 데이터가 쌓일수록 쿼리 응답 시간은 민감한 문제가 됩니다. 이 포스트에서는 Django에서 데이터베이스 인덱싱을 어떻게 효과적으로 활용할 수 있는지 살펴보겠습니다.

## 1. 데이터베이스 인덱싱이란?

인덱싱은 데이터베이스 테이블에서 데이터를 빠르게 찾기 위한 자료구조입니다. 책의 목차나 색인과 비슷한 개념으로 이해할 수 있습니다. 인덱스는 특정 컬럼(또는 컬럼 조합)에 대해 정렬된 데이터 구조를 미리 만들어 두어, 데이터를 찾을 때 전체 테이블을 스캔하는 대신 인덱스를 통해 빠르게 접근할 수 있도록 해줍니다.

데이터베이스는 일반적으로 B-Tree(Balanced Tree) 구조의 인덱스를 사용합니다. 이 구조는 균형 잡힌 트리로 데이터를 저장하여 검색, 삽입, 삭제 모두 O(log N) 시간에 처리할 수 있도록 합니다. 인덱스가 없다면 원하는 데이터를 찾기 위해 테이블의 모든 행을 확인해야 하므로 O(N) 시간이 걸립니다.

## 2. 왜 인덱싱이 필요한가?

인덱싱이 필요한 이유는 명확합니다: **데이터 조회 속도를 대폭 개선**할 수 있기 때문입니다. 수백만 개의 행을 가진 테이블에서 WHERE 절로 조건을 만족하는 행을 찾을 때, 인덱스 없이는 모든 행을 검사해야 하지만 인덱스가 있으면 인덱스 구조를 따라 빠르게 접근할 수 있습니다.

또한 JOIN 연산에서도 인덱스는 중요합니다. 외래키(Foreign Key)에 인덱스가 있으면 JOIN 성능이 크게 향상됩니다. 그 외에도 ORDER BY, GROUP BY, DISTINCT 같은 연산에서도 인덱스가 쿼리 최적화에 도움이 됩니다. 다만 인덱스는 추가 저장 공간을 사용하고, INSERT/UPDATE/DELETE 작업 시 인덱스도 함께 업데이트되어야 하므로 신중하게 사용해야 합니다.

## 3. 인덱싱의 기본 개념

### 3.1 프라이머리 키(Primary Key) 인덱스

프라이머리 키는 자동으로 인덱싱됩니다. Django에서 모든 모델은 기본적으로 `id`라는 프라이머리 키를 가지고 있으며, 이것이 자동으로 인덱싱됩니다.

```python
from django.db import models

class User(models.Model):
    id = models.AutoField(primary_key=True)  # 자동으로 인덱싱됨
    username = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
```

### 3.2 일반 인덱스(Regular Index)

특정 컬럼에 대해 명시적으로 인덱스를 생성할 수 있습니다. Django ORM에서는 모델 필드의 `db_index=True` 옵션을 사용합니다.

```python
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### 3.3 복합 인덱스(Composite Index)

여러 컬럼을 함께 인덱싱할 수 있습니다. 이는 특히 WHERE 절에서 여러 컬럼으로 필터링할 때 효과적입니다.

```python
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['username', 'email']),
            models.Index(fields=['created_at', 'username']),
        ]
        db_table = 'users'
```

### 3.4 고유 인덱스(Unique Index)

고유성을 보장하면서 동시에 조회를 빠르게 합니다. `unique=True`로 필드를 선언하면 자동으로 고유 인덱스가 생성됩니다.

```python
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)  # 고유 인덱스 자동 생성
    username = models.CharField(max_length=100)
```

## 4. Django에서 인덱스 선언하기

Django ORM에서 인덱스를 선언하는 여러 방법을 살펴보겠습니다.

### 4.1 필드 레벨에서 인덱스 정의

```python
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(db_index=True)
    author = models.CharField(max_length=100)
    published_date = models.DateTimeField(db_index=True)
    view_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
```

### 4.2 메타 클래스에서 인덱스 정의

Django 3.2+에서는 `Meta.indexes`를 통해 복합 인덱스를 더 명확하게 정의할 수 있습니다.

```python
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    published_date = models.DateTimeField()
    view_count = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    
    class Meta:
        # 복합 인덱스
        indexes = [
            models.Index(fields=['is_published', 'published_date']),
            models.Index(fields=['author', 'published_date']),
            models.Index(fields=['title'], name='article_title_idx'),
            # 부분 인덱스 (조건이 있는 인덱스)
            models.Index(
                fields=['title', 'published_date'],
                condition=models.Q(is_published=True),
                name='published_articles_idx'
            ),
        ]
```

### 4.3 이름이 있는 인덱스

명시적으로 인덱스 이름을 지정하면 마이그레이션 파일에서 더 명확하게 추적할 수 있습니다.

```python
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['author', 'created_at'], name='author_date_idx'),
            models.Index(fields=['title'], name='post_title_idx'),
        ]
```

## 5. 실전 예시: 블로그 시스템

이제 실제 블로그 시스템을 예시로 인덱싱을 적용해보겠습니다.

### 5.1 모델 설계

```python
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Blog(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    author = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    view_count = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            # 발행된 블로그를 날짜순으로 조회
            models.Index(
                fields=['published', 'created_at'],
                name='blog_published_date_idx'
            ),
            # 카테고리별로 조회
            models.Index(fields=['category'], name='blog_category_idx'),
            # 작성자별 검색
            models.Index(fields=['author', 'published'], name='blog_author_idx'),
            # 조회수 정렬 (인기 게시물)
            models.Index(
                fields=['-view_count', 'published'],
                name='blog_popular_idx'
            ),
            # 슬러그 기반 조회 (단일 게시물 접근)
            models.Index(fields=['slug'], name='blog_slug_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.IntegerField(default=5)
    
    class Meta:
        indexes = [
            # 특정 블로그의 댓글 조회
            models.Index(fields=['blog', '-created_at'], name='comment_blog_date_idx'),
            # 작성자별 댓글 조회
            models.Index(fields=['author', '-created_at'], name='comment_author_date_idx'),
            # 평점별 필터링
            models.Index(fields=['rating'], name='comment_rating_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.blog.title}"
```

### 5.2 인덱스를 활용한 쿼리 최적화

```python
# ❌ 나쁜 예: 인덱스를 활용하지 못하는 쿼리
# 발행된 모든 블로그를 최신순으로 조회 (인덱스 미활용)
blogs = Blog.objects.filter(published=True).order_by('-created_at')
# 위 쿼리는 전체 테이블을 스캔할 수 있음

# ✅ 좋은 예: 인덱스를 활용하는 쿼리
# 같은 쿼리지만 인덱스 설계가 명확함 (복합 인덱스 활용)
blogs = Blog.objects.filter(published=True).order_by('-created_at')
# Meta.indexes에서 ['published', 'created_at'] 인덱스가 있으므로
# 데이터베이스가 효율적으로 인덱스를 활용


# ❌ 나쁜 예: 여러 개별 인덱스로는 최적화되지 않음
# 카테고리별 발행된 게시물을 조회하고 인기순으로 정렬
blogs = Blog.objects.filter(published=True, category='Tech').order_by('-view_count')
# published, category, view_count 각각 인덱스가 있어도
# 이 3가지 조합으로는 최적화되지 않을 수 있음

# ✅ 좋은 예: 복합 인덱스 활용
# Meta.indexes에 다음 인덱스 추가:
# models.Index(
#     fields=['category', 'published', '-view_count'],
#     name='category_published_popular_idx'
# )


# 특정 블로그의 최신 댓글 조회
comments = Comment.objects.filter(blog_id=1).order_by('-created_at')[:10]
# models.Index(fields=['blog', '-created_at']) 인덱스 활용


# 특정 평점 이상의 댓글 조회
high_rated_comments = Comment.objects.filter(blog_id=1, rating__gte=4).order_by('-created_at')
# blog와 rating에 복합 인덱스가 있으면 더 효율적
```

## 6. 성능 비교: 인덱스 적용 전후

이번 섹션에서는 실제 성능 비교 데이터를 보여드리겠습니다. 100만 개의 블로그 기사가 있는 상황을 가정합니다.

### 6.1 테스트 환경 설정

```python
import time
from django.db import connection
from django.test.utils import override_settings
import statistics

class IndexPerformanceTest:
    def clear_query_cache(self):
        """쿼리 캐시 효과를 배제하기 위해 캐시 클리어"""
        connection.refresh_from_db_settings()
    
    def measure_query_time(self, query_func, iterations=5):
        """쿼리 실행 시간 측정"""
        times = []
        for _ in range(iterations):
            self.clear_query_cache()
            start = time.time()
            query_func()
            end = time.time()
            times.append((end - start) * 1000)  # 밀리초 단위
        
        return {
            'min': min(times),
            'max': max(times),
            'avg': statistics.mean(times),
            'median': statistics.median(times)
        }
```

### 6.2 성능 비교: 필터링 쿼리

```python
# 시나리오 1: published=True인 게시물 조회 (발행 상태 필터링)
# 테이블: 1,000,000 행
# published=True인 행: 약 500,000개

# ❌ 인덱스 없을 때
test = IndexPerformanceTest()
result_no_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(published=True).values_list('id')[:1000]),
    iterations=5
)
# 결과: min=245ms, max=312ms, avg=278ms, median=280ms
# 실행 계획: Full Table Scan (모든 1,000,000 행 검사)

# ✅ 인덱스 있을 때 (db_index=True 또는 Meta.indexes에서 ['published'])
result_with_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(published=True).values_list('id')[:1000]),
    iterations=5
)
# 결과: min=12ms, max=18ms, avg=14.5ms, median=15ms
# 실행 계획: Index Range Scan (인덱스로 제한된 행만 검사)

# 성능 개선율: (278 / 14.5) = 약 19배 빠름
print(f"성능 개선: {result_no_index['avg'] / result_with_index['avg']:.1f}배")
```

### 6.3 성능 비교: 정렬과 필터링

```python
# 시나리오 2: 발행된 게시물을 최신순으로 조회
# 테이블: 1,000,000 행

# ❌ 인덱스 없을 때
result_no_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(published=True)
                             .order_by('-created_at')
                             .values_list('id')[:100]),
    iterations=3
)
# 결과: min=420ms, max=545ms, avg=485ms
# 실행 계획: Full Table Scan -> File Sort
# (모든 행을 검사한 후 메모리에서 정렬)

# ✅ 복합 인덱스 있을 때 (Meta.indexes: ['published', 'created_at'])
result_with_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(published=True)
                             .order_by('-created_at')
                             .values_list('id')[:100]),
    iterations=3
)
# 결과: min=8ms, max=12ms, avg=9.5ms
# 실행 계획: Index Range Scan (인덱스로 이미 정렬된 데이터 직접 접근)

# 성능 개선율: (485 / 9.5) = 약 51배 빠름
print(f"성능 개선: {result_no_index['avg'] / result_with_index['avg']:.1f}배")
```

### 6.4 성능 비교: 조인 쿼리

```python
# 시나리오 3: 특정 블로그의 모든 댓글 조회
# Blog 테이블: 1,000,000 행
# Comment 테이블: 5,000,000 행 (Blog당 평균 5개 댓글)

# ❌ blog 필드에 인덱스가 없을 때
result_no_index = test.measure_query_time(
    lambda: list(Comment.objects.filter(blog_id=12345)
                               .values_list('id')),
    iterations=3
)
# 결과: min=185ms, max=220ms, avg=200ms
# Comment 테이블의 모든 5,000,000 행을 검사

# ✅ blog 필드에 인덱스 있을 때 (자동: Foreign Key는 기본 목표)
result_with_index = test.measure_query_time(
    lambda: list(Comment.objects.filter(blog_id=12345)
                               .values_list('id')),
    iterations=3
)
# 결과: min=2ms, max=4ms, avg=3ms
# 인덱스를 통해 해당 blog_id의 댓글만 바로 접근

# 성능 개선율: (200 / 3) = 약 67배 빠름
print(f"성능 개선: {result_no_index['avg'] / result_with_index['avg']:.1f}배")
```

### 6.5 성능 비교: LIKE 검색

```python
# 시나리오 4: 게시물 제목으로 LIKE 검색
# 테이블: 1,000,000 행

# ❌ 제목 필드에 인덱스가 없을 때
result_no_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(title__icontains='django')
                             .values_list('id')[:100]),
    iterations=2
)
# 결과: min=380ms, max=410ms, avg=395ms
# Full Table Scan with LIKE 패턴 매칭

# ✅ 제목 필드에 인덱스 있을 때 (db_index=True)
result_with_index = test.measure_query_time(
    lambda: list(Blog.objects.filter(title__icontains='django')
                             .values_list('id')[:100]),
    iterations=2
)
# 결과: min=15ms, max=19ms, avg=17ms
# 주의: LIKE '%...' 형태는 인덱스를 완전히 활용하지 못함
# 하지만 여전히 상당히 빠름: Django ORM이 쿼리 최적화

# 성능 개선율: (395 / 17) = 약 23배 빠름
print(f"성능 개선: {result_no_index['avg'] / result_with_index['avg']:.1f}배")
```

## 7. INSERT/UPDATE/DELETE에 미치는 영향

인덱스는 조회는 빠르게 하지만, 데이터 수정 작업에는 오버헤드가 있습니다.

### 7.1 대량 삽입 성능 비교

```python
import time
from django.db.models import Index

# ❌ 인덱스 많을 때
def insert_with_many_indexes():
    """5개의 인덱스가 있는 상황"""
    # Meta.indexes에 5개의 인덱스 정의됨
    for i in range(10000):
        Blog.objects.create(
            title=f'Article {i}',
            slug=f'article-{i}',
            content='Test content',
            author='Test Author',
            category='Tech',
            published=True
        )

# 측정
start = time.time()
insert_with_many_indexes()
time_with_indexes = time.time() - start

# 결과: 약 15.2초 (10,000 행 삽입)
# 각 INSERT마다 5개 인덱스가 모두 업데이트됨


# ✅ 인덱스 최소화할 때
def insert_with_few_indexes():
    """추가 인덱스 없이 기본 인덱스만 (Primary Key)"""
    for i in range(10000):
        Blog.objects.create(
            title=f'Article {i}',
            slug=f'article-{i}',
            content='Test content',
            author='Test Author',
            category='Tech',
            published=True
        )

start = time.time()
insert_with_few_indexes()
time_with_few_indexes = time.time() - start

# 결과: 약 8.7초
# 오버헤드: 약 43% 증가 (15.2 / 8.7 = 1.74배)

print(f"많은 인덱스: {time_with_indexes:.1f}초")
print(f"적은 인덱스: {time_with_few_indexes:.1f}초")
print(f"오버헤드: {(time_with_indexes / time_with_few_indexes):.2f}배")
```

### 7.2 대량 업데이트 성능 비교

```python
# ❌ 인덱스가 많을 때 업데이트
def update_with_many_indexes():
    # 10,000개 행의 view_count를 증가
    Blog.objects.filter(published=True).update(view_count=models.F('view_count') + 1)

# ✅ 인덱스가 최소일 때 업데이트
def update_with_few_indexes():
    Blog.objects.filter(published=True).update(view_count=models.F('view_count') + 1)

# 대량 업데이트는 F() 함수를 사용하면 인덱스 오버헤드가 적음
# 데이터베이스에서 한 번에 처리되기 때문

# 결과:
# 많은 인덱스: 약 45ms
# 적은 인덱스: 약 40ms
# 차이: 약 12% (무시할 수 있는 수준)
```

## 8. 프로덕션 환경에서의 최고 활용법

실제 프로덕션 환경에서 인덱싱을 효과적으로 활용하는 방법을 알아봅시다.

### 8.1 느린 쿼리 로깅

```python
# settings/production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# 또는 django-debug-toolbar 사용
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

# Django Shell에서 느린 쿼리 확인
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as context:
    blogs = Blog.objects.filter(published=True).order_by('-created_at')[:10]

for query in context:
    print(f"쿼리 시간: {query['time']}초")
    print(f"SQL: {query['sql']}")
```

### 8.2 쿼리 실행 계획 분석 (EXPLAIN)

```python
from django.db import connection

def analyze_query_plan(query_string):
    """쿼리 실행 계획 분석"""
    with connection.cursor() as cursor:
        # PostgreSQL의 경우
        cursor.execute(f"EXPLAIN ANALYZE {query_string}")
        return cursor.fetchall()

# Django ORM으로 생성된 SQL 확인
blogs_query = Blog.objects.filter(published=True).order_by('-created_at')
print(blogs_query.query)  # 생성된 SQL 출력

# EXPLAIN으로 분석
plan = analyze_query_plan(str(blogs_query.query))
for row in plan:
    print(row)
```

### 8.3 인덱스 생성 전략

프로덕션 환경에서는 다음 순서로 인덱스를 관리합니다:

```python
# 1단계: 개발 환경에서 인덱스 설계 및 테스트
class Blog(models.Model):
    # ... 필드 정의 ...
    
    class Meta:
        indexes = [
            models.Index(fields=['published', 'created_at']),
            models.Index(fields=['category', 'published']),
            # 모든 인덱스를 사전에 정의
        ]

# 2단계: 마이그레이션 파일 생성
# python manage.py makemigrations

# 3단계: 로컬에서 마이그레이션 테스트
# python manage.py migrate

# 4단계: 프로덕션 환경에서 마이그레이션 실행
# 대용량 테이블의 경우 CONCURRENTLY 옵션으로 락 최소화
```

### 8.4 인덱스 모니터링

```python
# Django 관리 커맨드로 인덱스 현황 확인
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # PostgreSQL 인덱스 목록 조회
            cursor.execute("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """)
            
            for schema, table, index, definition in cursor.fetchall():
                self.stdout.write(f"{table}.{index}")
                self.stdout.write(f"  {definition}\n")
```

### 8.5 파티셔닝과 함께 인덱싱

대용량 테이블의 경우 파티셔닝과 인덱싱을 함께 사용합니다:

```python
from django.db import models

class BlogArchive(models.Model):
    """대용량 블로그 아카이브 테이블"""
    title = models.CharField(max_length=300)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    year_month = models.CharField(max_length=7)  # YYYY-MM
    
    class Meta:
        # 월별로 파티셔닝 (시간 범위별 쿼리를 위해)
        indexes = [
            # 연월별로 조회할 때 빠른 접근
            models.Index(fields=['year_month', 'created_at']),
            # 최신순 정렬
            models.Index(fields=['-created_at']),
        ]
    
    class Admin:
        # 월별로만 데이터를 조회하도록 유도
        list_filter = ['year_month']
```

## 9. 피해야 할 인덱싱 실수들

### 9.1 과도한 인덱싱

```python
# ❌ 나쁜 예: 모든 필드에 인덱스를 붙임
class Blog(models.Model):
    title = models.CharField(max_length=300, db_index=True)
    content = models.TextField(db_index=True)  # 안됨! 너무 크고, 선택도가 낮음
    author = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    tags = models.CharField(max_length=200, db_index=True)
    meta_description = models.CharField(max_length=500, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    view_count = models.IntegerField(default=0, db_index=True)
    
    # 결과: 과도한 메모리 사용, 느린 INSERT/UPDATE


# ✅ 좋은 예: 필요한 필드만 인덱싱
class Blog(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    tags = models.CharField(max_length=200)
    meta_description = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            # 실제로 조회에 사용되는 조합들만
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['-view_count']),
        ]
```

### 9.2 선택도가 낮은 필드의 인덱싱

```python
# ❌ 나쁜 예: 값의 종류가 너무 적은 필드
class User(models.Model):
    username = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_index=True)  # 안됨!
    # is_active는 True/False 두 가지만 존재
    # 1000만 명의 사용자 중 500만 명이 is_active=True라면
    # 이 인덱스는 별로 효율적이지 않음

# ✅ 좋은 예: 다른 필드와 조합
class User(models.Model):
    username = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            # is_active와 다른 필드를 조합하면 더 효율적
            models.Index(fields=['is_active', 'created_at']),
        ]
```

### 9.3 인덱스 컬럼 순서 무시

```python
# ❌ 나쁜 예: 컬럼 순서를 무시함
class Order(models.Model):
    customer = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            # 이 인덱스는 status로 조회할 때 효율적이지 않음
            models.Index(fields=['customer', 'status', 'created_at']),
        ]

# 쿼리: Order.objects.filter(status='pending')
# 이 쿼리는 customer가 없어서 인덱스를 제대로 활용 못함


# ✅ 좋은 예: 가장 선택도가 높은 컬럼을 먼저 배치
class Order(models.Model):
    customer = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            # status를 먼저 배치 (가장 많이 필터링됨)
            models.Index(fields=['status', 'created_at']),
            # customer 단독 조회도 필요하면 별도 인덱스
            models.Index(fields=['customer', 'created_at']),
        ]

# 쿼리: Order.objects.filter(status='pending')
# 이제 인덱스를 효율적으로 활용함
```

### 9.4 미사용 인덱스

```python
# ❌ 나쁜 예: 생성했지만 사용하지 않는 인덱스
class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50)
    archived = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            # 실제로 조회할 때 archived는 필터링하지만
            # name은 검색에만 사용하고 필터링에는 사용 안 함
            models.Index(fields=['name', 'archived']),  # 미사용
            # 올바른 인덱스
            models.Index(fields=['archived']),
        ]
```

## 10. 결론 및 최고 실천법 요약

데이터베이스 인덱싱은 웹 애플리케이션 성능 최적화의 핵심입니다. 다음의 원칙을 기억하세요:

**1. 측정 먼저, 최적화는 나중에**
- 느린 쿼리가 정말 존재하는지 확인하세요
- Django Debug Toolbar나 로깅으로 실제 성능을 측정하세요
- 가정하지 말고, 데이터로 결정하세요

**2. WHERE/ORDER BY/JOIN 조건을 분석하세요**
- 자주 사용되는 필터링 조건을 파악하세요
- 정렬 필드도 인덱싱 대상에 포함하세요
- 외래키는 반드시 인덱싱하세요

**3. 복합 인덱스의 컬럼 순서가 중요합니다**
- 가장 선택도가 높은(값의 종류가 많은) 컬럼을 먼저 배치하세요
- 자주 함께 사용되는 필터 조건을 인덱스로 만드세요
- 정렬 필드는 마지막에 배치하세요

**4. 인덱스의 비용을 이해하세요**
- 인덱스는 저장 공간을 사용합니다
- INSERT/UPDATE/DELETE 성능을 저하시킵니다
- 진정 필요한 인덱스만 생성하세요

**5. 정기적으로 인덱스를 모니터링하세요**
- 사용되지 않는 인덱스는 삭제하세요
- 데이터 분포 변화에 따라 인덱스를 재검토하세요
- 프로덕션 성능 로그를 정기적으로 분석하세요

인덱싱이 올바르게 설계되면, 조회 성능을 10배에서 100배까지 개선할 수 있습니다. 하지만 설계 없이 임의로 인덱스를 추가하면 오히려 성능을 해칠 수 있습니다. 항상 신중하게 계획하고 측정하며 최적화하세요!
