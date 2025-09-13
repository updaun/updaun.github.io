---
layout: post
title: "Django ORM 최적화: select_related()와 prefetch_related() 완전 정복"
date: 2025-09-13 14:00:00 +0900
categories: [Django, ORM, Database, Performance]
tags: [Django, ORM, Database Optimization, N+1 Problem, select_related, prefetch_related, Prefetch, Performance Tuning]
---

Django 개발에서 가장 흔히 마주치는 성능 문제 중 하나가 바로 **N+1 쿼리 문제**입니다. 이를 해결하기 위해 Django ORM은 `select_related()`와 `prefetch_related()` 두 가지 강력한 도구를 제공합니다. 이 글에서는 두 메서드의 차이점과 고급 최적화 기법을 심도 있게 살펴보겠습니다.

## 🔍 N+1 쿼리 문제란?

먼저 N+1 쿼리 문제가 무엇인지 이해해보겠습니다.

```python
# 모델 정의
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    bio = models.TextField()

class Publisher(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13)

class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)
    rating = models.IntegerField()
    comment = models.TextField()
```

### N+1 쿼리 문제 발생 예제

```python
# 문제가 되는 코드
def get_books_with_authors():
    books = Book.objects.all()  # 1번의 쿼리
    
    for book in books:
        print(f"{book.title} - {book.author.name}")  # 각 책마다 추가 쿼리 발생
        # N번의 추가 쿼리 (N = 책의 개수)

# 총 1 + N번의 쿼리가 실행됨
# 책이 1000권이면 1001번의 쿼리!
```

```sql
-- 실제 실행되는 SQL
SELECT * FROM book;  -- 1번째 쿼리

SELECT * FROM author WHERE id = 1;  -- 2번째 쿼리
SELECT * FROM author WHERE id = 2;  -- 3번째 쿼리
SELECT * FROM author WHERE id = 3;  -- 4번째 쿼리
-- ... 각 책마다 반복
```

## 🔗 select_related(): OneToOne과 ForeignKey 최적화

### 기본 개념과 동작 원리

`select_related()`는 **SQL JOIN**을 사용하여 관련 객체를 한 번의 쿼리로 가져옵니다.

```python
# select_related() 사용
def get_books_with_authors_optimized():
    books = Book.objects.select_related('author')  # 1번의 JOIN 쿼리
    
    for book in books:
        print(f"{book.title} - {book.author.name}")  # 추가 쿼리 없음

# 총 1번의 쿼리만 실행됨!
```

```sql
-- 실제 실행되는 SQL (INNER JOIN 사용)
SELECT 
    book.id, book.title, book.publication_date, book.isbn,
    author.id, author.name, author.email, author.bio
FROM book 
INNER JOIN author ON book.author_id = author.id;
```

### 다양한 select_related() 사용법

#### 1. 단일 관계 최적화
```python
# 기본 사용법
books = Book.objects.select_related('author')
books = Book.objects.select_related('publisher')

# 여러 관계 동시 최적화
books = Book.objects.select_related('author', 'publisher')
```

#### 2. 중첩 관계 최적화
```python
# 모델 확장 예제
class AuthorProfile(models.Model):
    author = models.OneToOneField(Author, on_delete=models.CASCADE)
    birth_date = models.DateField()
    nationality = models.CharField(max_length=50)

# 중첩 관계 최적화
books = Book.objects.select_related(
    'author',
    'author__authorprofile',  # 이중 관계 최적화
    'publisher'
)

for book in books:
    print(f"{book.title} by {book.author.name}")
    print(f"Nationality: {book.author.authorprofile.nationality}")
    # 모든 데이터가 이미 로드되어 있어 추가 쿼리 없음
```

#### 3. 조건부 select_related
```python
# 동적으로 select_related 적용
def get_books(include_author=False, include_publisher=False):
    queryset = Book.objects.all()
    
    select_fields = []
    if include_author:
        select_fields.append('author')
    if include_publisher:
        select_fields.append('publisher')
    
    if select_fields:
        queryset = queryset.select_related(*select_fields)
    
    return queryset
```

### select_related() 성능 분석

```python
import time
from django.db import connection

def measure_query_performance():
    # 비최적화 버전
    start_time = time.time()
    books = Book.objects.all()
    for book in books:
        _ = book.author.name  # N+1 쿼리 발생
    
    unoptimized_time = time.time() - start_time
    unoptimized_queries = len(connection.queries)
    
    # 초기화
    connection.queries.clear()
    
    # 최적화 버전
    start_time = time.time()
    books = Book.objects.select_related('author')
    for book in books:
        _ = book.author.name  # 추가 쿼리 없음
    
    optimized_time = time.time() - start_time
    optimized_queries = len(connection.queries)
    
    print(f"비최적화: {unoptimized_time:.3f}초, {unoptimized_queries}개 쿼리")
    print(f"최적화: {optimized_time:.3f}초, {optimized_queries}개 쿼리")
    print(f"성능 향상: {unoptimized_time/optimized_time:.1f}배")

# 결과 예시:
# 비최적화: 2.345초, 1001개 쿼리
# 최적화: 0.089초, 1개 쿼리  
# 성능 향상: 26.3배
```

## 🔄 prefetch_related(): ManyToMany와 역참조 최적화

### 기본 개념과 동작 원리

`prefetch_related()`는 **별도의 쿼리**로 관련 객체들을 가져온 후 Python에서 관계를 연결합니다.

```python
# ManyToMany 관계 모델 추가
class Tag(models.Model):
    name = models.CharField(max_length=50)

class Book(models.Model):
    # 기존 필드들...
    tags = models.ManyToManyField(Tag, related_name='books')

# prefetch_related() 사용
def get_books_with_tags():
    books = Book.objects.prefetch_related('tags')  # 2번의 쿼리
    
    for book in books:
        tag_names = [tag.name for tag in book.tags.all()]  # 추가 쿼리 없음
        print(f"{book.title}: {', '.join(tag_names)}")
```

```sql
-- 실제 실행되는 SQL (2개의 분리된 쿼리)
-- 첫 번째 쿼리: 책 정보
SELECT * FROM book;

-- 두 번째 쿼리: 태그 정보 (IN 절 사용)
SELECT 
    book_tags.book_id, tag.id, tag.name
FROM tag
INNER JOIN book_tags ON tag.id = book_tags.tag_id
WHERE book_tags.book_id IN (1, 2, 3, 4, 5, ...);
```

### 다양한 prefetch_related() 사용법

#### 1. 역참조 관계 최적화
```python
# 저자별 책 목록 조회
authors = Author.objects.prefetch_related('book_set')

for author in authors:
    books = author.book_set.all()  # 추가 쿼리 없음
    print(f"{author.name}: {books.count()}권의 책")

# related_name 사용 시
class Book(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

authors = Author.objects.prefetch_related('books')
```

#### 2. 중첩 관계 최적화
```python
# 책 → 리뷰 → 리뷰어 정보까지 최적화
books = Book.objects.prefetch_related(
    'reviews',  # 책의 리뷰들
    'reviews__reviewer'  # 각 리뷰의 리뷰어 (추가 모델 필요)
)

for book in books:
    reviews = book.reviews.all()
    for review in reviews:
        print(f"{review.reviewer.name}: {review.rating}점")
```

#### 3. 필터링과 함께 사용
```python
# 특정 조건의 관련 객체만 prefetch
from django.db import models

books = Book.objects.prefetch_related(
    models.Prefetch(
        'reviews',
        queryset=Review.objects.filter(rating__gte=4)  # 4점 이상 리뷰만
    )
)

for book in books:
    high_reviews = book.reviews.all()  # 이미 필터링된 결과
    print(f"{book.title}: {high_reviews.count()}개의 고평점 리뷰")
```

## 🚀 Prefetch 객체를 사용한 고급 최적화

### Prefetch 객체의 강력한 기능

`Prefetch` 객체를 사용하면 prefetch 동작을 세밀하게 제어할 수 있습니다.

```python
from django.db.models import Prefetch, Count, Avg

# 기본 Prefetch 객체 사용
books = Book.objects.prefetch_related(
    Prefetch('reviews')  # 기본 prefetch_related('reviews')와 동일
)
```

### 1. 커스텀 QuerySet으로 최적화

```python
# 특정 조건으로 필터링된 관련 객체만 가져오기
def get_books_with_recent_reviews():
    from datetime import date, timedelta
    
    recent_date = date.today() - timedelta(days=30)
    
    books = Book.objects.prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.filter(
                created_at__gte=recent_date
            ).select_related('reviewer'),  # 리뷰어 정보도 함께
            to_attr='recent_reviews'  # 커스텀 속성명
        )
    )
    
    for book in books:
        # book.reviews.all() 대신 book.recent_reviews 사용
        reviews = book.recent_reviews
        print(f"{book.title}: {len(reviews)}개의 최근 리뷰")
```

### 2. 정렬된 관련 객체 가져오기

```python
# 평점 순으로 정렬된 리뷰 prefetch
def get_books_with_sorted_reviews():
    books = Book.objects.prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.order_by('-rating', '-created_at'),
            to_attr='sorted_reviews'
        )
    )
    
    for book in books:
        top_reviews = book.sorted_reviews[:5]  # 상위 5개 리뷰
        for review in top_reviews:
            print(f"  {review.rating}점: {review.comment[:50]}...")
```

### 3. 집계 함수와 함께 사용

```python
# 리뷰 통계를 포함한 책 정보 조회
def get_books_with_review_stats():
    books = Book.objects.annotate(
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating')
    ).prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.select_related('reviewer').order_by('-rating')
        )
    )
    
    for book in books:
        print(f"{book.title}")
        print(f"  평균 평점: {book.avg_rating:.1f}")
        print(f"  리뷰 수: {book.review_count}")
        
        # 실제 리뷰 데이터도 이미 로드됨
        best_review = book.reviews.all()[0] if book.reviews.all() else None
        if best_review:
            print(f"  최고 평점 리뷰: {best_review.rating}점")
```

### 4. 중첩된 Prefetch 최적화

```python
# 복잡한 중첩 관계 최적화
def get_authors_with_detailed_books():
    authors = Author.objects.prefetch_related(
        Prefetch(
            'books',
            queryset=Book.objects.select_related('publisher').prefetch_related(
                Prefetch(
                    'reviews',
                    queryset=Review.objects.filter(rating__gte=4).order_by('-rating'),
                    to_attr='good_reviews'
                ),
                'tags'
            ),
            to_attr='published_books'
        )
    )
    
    for author in authors:
        print(f"\n저자: {author.name}")
        for book in author.published_books:
            print(f"  책: {book.title} (출판사: {book.publisher.name})")
            print(f"    태그: {', '.join(tag.name for tag in book.tags.all())}")
            print(f"    좋은 리뷰: {len(book.good_reviews)}개")
```

### 5. 조건부 Prefetch

```python
# 동적으로 Prefetch 조건 변경
def get_books_dynamic_prefetch(min_rating=None, tag_filter=None):
    prefetch_list = []
    
    # 조건부 리뷰 prefetch
    if min_rating:
        review_queryset = Review.objects.filter(rating__gte=min_rating)
        prefetch_list.append(
            Prefetch('reviews', queryset=review_queryset, to_attr='filtered_reviews')
        )
    else:
        prefetch_list.append('reviews')
    
    # 조건부 태그 prefetch
    if tag_filter:
        tag_queryset = Tag.objects.filter(name__icontains=tag_filter)
        prefetch_list.append(
            Prefetch('tags', queryset=tag_queryset, to_attr='filtered_tags')
        )
    else:
        prefetch_list.append('tags')
    
    books = Book.objects.prefetch_related(*prefetch_list)
    return books
```

## ⚡ 성능 비교와 최적화 전략

### 1. 쿼리 수 비교

```python
from django.test.utils import override_settings
from django.db import connection

@override_settings(DEBUG=True)
def compare_query_strategies():
    """다양한 최적화 전략의 쿼리 수 비교"""
    
    strategies = {
        '최적화 없음': lambda: Book.objects.all(),
        'select_related만': lambda: Book.objects.select_related('author', 'publisher'),
        'prefetch_related만': lambda: Book.objects.prefetch_related('reviews', 'tags'),
        '둘 다 사용': lambda: Book.objects.select_related('author', 'publisher').prefetch_related('reviews', 'tags'),
        'Prefetch 객체': lambda: Book.objects.select_related('author').prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('reviewer'))
        )
    }
    
    for name, strategy in strategies.items():
        connection.queries.clear()
        
        books = strategy()
        
        # 실제 데이터 접근
        for book in books[:10]:  # 처음 10권만 테스트
            _ = book.title
            _ = book.author.name
            _ = book.publisher.name
            _ = list(book.reviews.all())
            _ = list(book.tags.all())
        
        query_count = len(connection.queries)
        print(f"{name}: {query_count}개 쿼리")

# 결과 예시:
# 최적화 없음: 41개 쿼리
# select_related만: 21개 쿼리  
# prefetch_related만: 23개 쿼리
# 둘 다 사용: 3개 쿼리
# Prefetch 객체: 3개 쿼리
```

### 2. 메모리 사용량 최적화

```python
# 대량 데이터 처리 시 메모리 최적화
def process_large_dataset():
    # 잘못된 방법: 모든 데이터를 메모리에 로드
    books = Book.objects.select_related('author').prefetch_related('reviews')
    all_books = list(books)  # 메모리 부족 위험
    
    # 올바른 방법: iterator() 사용
    books = Book.objects.select_related('author').prefetch_related('reviews')
    
    for book in books.iterator(chunk_size=1000):
        # 1000개씩 청크 단위로 처리
        process_book(book)

def process_book_batch():
    # 배치 처리 최적화
    from django.core.paginator import Paginator
    
    books = Book.objects.select_related('author').prefetch_related('reviews')
    paginator = Paginator(books, 100)  # 100개씩 페이지네이션
    
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for book in page.object_list:
            process_book(book)
```

### 3. 캐싱과 결합한 최적화

```python
from django.core.cache import cache
from django.db.models import Prefetch

def get_cached_books_with_reviews():
    cache_key = 'books_with_reviews_v1'
    
    # 캐시에서 먼저 확인
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 캐시 미스 시 최적화된 쿼리 실행
    books = Book.objects.select_related('author', 'publisher').prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.filter(rating__gte=3).order_by('-rating')[:5],
            to_attr='top_reviews'
        ),
        'tags'
    )
    
    # 직렬화 가능한 형태로 변환
    book_data = []
    for book in books:
        book_info = {
            'title': book.title,
            'author': book.author.name,
            'publisher': book.publisher.name,
            'tags': [tag.name for tag in book.tags.all()],
            'top_reviews': [
                {'rating': review.rating, 'comment': review.comment}
                for review in book.top_reviews
            ]
        }
        book_data.append(book_info)
    
    # 30분 캐싱
    cache.set(cache_key, book_data, 1800)
    return book_data
```

## 🎯 실전 최적화 패턴

### 1. API 엔드포인트 최적화

```python
# Django REST Framework 뷰 최적화
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

class BookViewSet(ModelViewSet):
    def get_queryset(self):
        queryset = Book.objects.select_related('author', 'publisher')
        
        # 액션별로 다른 최적화 적용
        if self.action == 'list':
            # 목록 조회 시 기본 정보만
            queryset = queryset.prefetch_related('tags')
        elif self.action == 'retrieve':
            # 상세 조회 시 모든 관련 정보
            queryset = queryset.prefetch_related(
                Prefetch(
                    'reviews',
                    queryset=Review.objects.select_related('reviewer').order_by('-created_at')
                ),
                'tags'
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def with_stats(self, request):
        """통계 정보가 포함된 책 목록"""
        books = Book.objects.select_related('author').annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating')
        ).prefetch_related(
            Prefetch(
                'reviews',
                queryset=Review.objects.order_by('-rating')[:3],
                to_attr='top_3_reviews'
            )
        )
        
        # 직렬화 및 응답
        return Response(self.get_serializer(books, many=True).data)
```

### 2. 관리자 인터페이스 최적화

```python
# Django Admin 최적화
from django.contrib import admin

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_name', 'publisher_name', 'review_count']
    list_select_related = ['author', 'publisher']  # list_display 최적화
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('author', 'publisher').annotate(
            review_count=Count('reviews')
        )
    
    def author_name(self, obj):
        return obj.author.name
    author_name.short_description = '저자'
    author_name.admin_order_field = 'author__name'
    
    def publisher_name(self, obj):
        return obj.publisher.name
    publisher_name.short_description = '출판사'
    
    def review_count(self, obj):
        return obj.review_count
    review_count.short_description = '리뷰 수'
    review_count.admin_order_field = 'review_count'

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'book_count']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            book_count=Count('books')
        )
    
    def book_count(self, obj):
        return obj.book_count
    book_count.short_description = '저서 수'
```

### 3. 복잡한 검색 최적화

```python
def advanced_book_search(query_params):
    """복잡한 조건의 책 검색 최적화"""
    
    # 기본 쿼리셋
    books = Book.objects.select_related('author', 'publisher')
    
    # 동적 필터링
    if query_params.get('author_name'):
        books = books.filter(author__name__icontains=query_params['author_name'])
    
    if query_params.get('min_rating'):
        books = books.filter(reviews__rating__gte=query_params['min_rating'])
    
    if query_params.get('tags'):
        tag_names = query_params['tags'].split(',')
        books = books.filter(tags__name__in=tag_names).distinct()
    
    # 최종 최적화
    books = books.prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.select_related('reviewer').order_by('-rating')[:5],
            to_attr='top_reviews'
        ),
        'tags'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating', '-review_count')
    
    return books
```

## ⚠️ 주의사항과 함정

### 1. select_related() 사용 시 주의점

```python
# 잘못된 사용: 불필요한 JOIN
# 모든 필드를 항상 select_related 하지 말 것
books = Book.objects.select_related()  # 모든 ForeignKey 관계를 JOIN (위험!)

# 올바른 사용: 필요한 관계만 명시
books = Book.objects.select_related('author')  # 실제로 사용하는 관계만

# 주의: 깊은 중첩은 성능 저하 가능
books = Book.objects.select_related(
    'author__profile__address__country'  # 너무 깊은 중첩
)
```

### 2. prefetch_related() 사용 시 주의점

```python
# 잘못된 사용: prefetch 후 추가 필터링
books = Book.objects.prefetch_related('reviews')
for book in books:
    # 이렇게 하면 prefetch 효과가 사라짐!
    recent_reviews = book.reviews.filter(created_at__gte=recent_date)

# 올바른 사용: Prefetch 객체로 미리 필터링
books = Book.objects.prefetch_related(
    Prefetch(
        'reviews',
        queryset=Review.objects.filter(created_at__gte=recent_date),
        to_attr='recent_reviews'
    )
)
for book in books:
    recent_reviews = book.recent_reviews  # 추가 쿼리 없음
```

### 3. 메모리 사용량 고려

```python
# 위험: 대량 데이터 prefetch
# 10,000권의 책에 각각 100개씩 리뷰가 있다면?
books = Book.objects.prefetch_related('reviews')  # 1,000,000개 리뷰 로드!

# 안전: 필요한 만큼만 prefetch
books = Book.objects.prefetch_related(
    Prefetch(
        'reviews',
        queryset=Review.objects.order_by('-rating')[:10],  # 상위 10개만
        to_attr='top_reviews'
    )
)
```

## 📊 성능 모니터링과 디버깅

### 1. 쿼리 분석 도구

```python
# Django Debug Toolbar 설정
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

# 커스텀 쿼리 분석기
class QueryAnalyzer:
    def __init__(self):
        self.queries = []
    
    def __enter__(self):
        from django.db import connection
        self.initial_count = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from django.db import connection
        self.queries = connection.queries[self.initial_count:]
        self.analyze()
    
    def analyze(self):
        print(f"\n총 {len(self.queries)}개의 쿼리 실행")
        
        for i, query in enumerate(self.queries, 1):
            print(f"\n쿼리 {i}: {query['time']}초")
            print(f"SQL: {query['sql'][:100]}...")
            
            # 느린 쿼리 감지
            if float(query['time']) > 0.1:
                print("⚠️  느린 쿼리 감지!")

# 사용 예제
with QueryAnalyzer():
    books = Book.objects.select_related('author').prefetch_related('reviews')
    for book in books[:10]:
        print(f"{book.title} by {book.author.name}")
        print(f"Reviews: {book.reviews.count()}")
```

### 2. 성능 테스트 자동화

```python
import time
from django.test import TestCase
from django.test.utils import override_settings

class PerformanceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 테스트 데이터 생성
        cls.create_test_data()
    
    def test_book_query_performance(self):
        """책 조회 성능 테스트"""
        
        test_cases = [
            ('기본 쿼리', lambda: Book.objects.all()),
            ('select_related', lambda: Book.objects.select_related('author')),
            ('prefetch_related', lambda: Book.objects.prefetch_related('reviews')),
            ('최적화 조합', lambda: Book.objects.select_related('author').prefetch_related('reviews'))
        ]
        
        for name, query_func in test_cases:
            with self.subTest(name=name):
                start_time = time.time()
                
                books = query_func()
                # 실제 데이터 접근
                for book in books:
                    _ = book.title
                    _ = book.author.name
                    _ = list(book.reviews.all())
                
                execution_time = time.time() - start_time
                
                print(f"{name}: {execution_time:.3f}초")
                
                # 성능 기준 검증
                if name == '최적화 조합':
                    self.assertLess(execution_time, 0.1, "최적화된 쿼리가 너무 느림")
```

## 🎯 결론 및 모범 사례

### 선택 가이드라인

| 관계 유형 | 권장 방법 | 이유 |
|-----------|-----------|------|
| **ForeignKey** | `select_related()` | JOIN으로 단일 쿼리 |
| **OneToOneField** | `select_related()` | JOIN으로 단일 쿼리 |
| **ManyToManyField** | `prefetch_related()` | 별도 쿼리가 더 효율적 |
| **역참조 (ForeignKey)** | `prefetch_related()` | 1:N 관계 처리 |
| **중첩 관계** | 조합 사용 | 관계 유형에 따라 선택 |

### 최적화 체크리스트

```python
# ✅ 모범 사례 체크리스트

def optimized_book_view():
    # 1. 필요한 관계만 최적화
    books = Book.objects.select_related(
        'author',  # 항상 필요한 ForeignKey
        'publisher'  # 항상 필요한 ForeignKey
    ).prefetch_related(
        # 2. Prefetch 객체로 세밀한 제어
        Prefetch(
            'reviews',
            queryset=Review.objects.select_related('reviewer').order_by('-rating')[:5],
            to_attr='top_reviews'
        ),
        # 3. 단순한 ManyToMany는 기본 prefetch
        'tags'
    ).annotate(
        # 4. 집계는 DB에서 처리
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating')
    
    return books

# ❌ 피해야 할 안티패턴
def bad_book_view():
    books = Book.objects.all()  # 최적화 없음
    
    for book in books:
        book.author.name  # N+1 쿼리
        book.reviews.count()  # 매번 COUNT 쿼리
        book.reviews.filter(rating__gte=4)  # 매번 필터 쿼리
```

### 실무 권장사항

1. **개발 단계에서 Django Debug Toolbar 필수 사용**
2. **복잡한 쿼리는 Raw SQL 프로파일링으로 검증**
3. **대량 데이터는 Pagination과 함께 최적화**
4. **캐싱 레이어와 조합하여 성능 극대화**
5. **정기적인 성능 모니터링과 최적화**

Django ORM의 `select_related()`와 `prefetch_related()`를 제대로 활용하면 **N+1 쿼리 문제를 해결**하고 **데이터베이스 성능을 극적으로 향상**시킬 수 있습니다. 특히 `Prefetch` 객체를 사용한 고급 최적화 기법은 복잡한 쿼리 최적화의 핵심입니다.

**다음 글에서는 Django의 쿼리 최적화를 더욱 심화시킨 Raw SQL과 Database Index 활용법을 다루겠습니다. 🚀**
