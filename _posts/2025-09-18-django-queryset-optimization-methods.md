---
layout: post
title: "Django QuerySet 최적화: values(), values_list(), only(), defer() 완벽 가이드"
date: 2025-09-18 10:00:00 +0900
categories: [Django, Python, Database, Performance]
tags: [Django, QuerySet, ORM, Database, Performance, Optimization, Python, SQL]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-09-18-django-queryset-optimization-methods.webp"
---

Django ORM을 사용하다 보면 데이터베이스 성능 최적화가 중요한 이슈가 됩니다. 특히 대용량 데이터를 다룰 때는 필요한 필드만 선택적으로 가져오는 것이 성능에 큰 영향을 미칩니다. 이 글에서는 Django에서 제공하는 4가지 주요 QuerySet 최적화 메서드인 `values()`, `values_list()`, `only()`, `defer()`의 차이점과 성능 영향을 상세히 알아보겠습니다.

## 📚 테스트 환경 설정

먼저 예제에서 사용할 모델을 정의해보겠습니다.

```python
# models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    bio = models.TextField()
    birth_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.CharField(max_length=500)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    published_date = models.DateTimeField()
    view_count = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
```

## 🔍 1. values() 메서드

### 기본 개념

`values()`는 QuerySet의 결과를 딕셔너리 형태로 반환합니다. 지정된 필드만 데이터베이스에서 가져오므로 메모리 사용량과 네트워크 트래픽을 줄일 수 있습니다.

### 사용법과 예제

```python
# 기본 사용법
articles = Article.objects.values('title', 'author__name', 'published_date')
print(articles.query)  # 생성된 SQL 확인

# 출력 결과
for article in articles:
    print(article)
    # {'title': 'Django 튜토리얼', 'author__name': '김개발', 'published_date': datetime.datetime(...)}
```

### 실제 SQL 분석

```sql
-- values()로 생성되는 SQL
SELECT "article"."title", "author"."name", "article"."published_date"
FROM "article" 
INNER JOIN "author" ON ("article"."author_id" = "author"."id")

-- 전체 필드를 가져오는 일반 QuerySet
SELECT "article"."id", "article"."title", "article"."content", 
       "article"."summary", "article"."author_id", "article"."published_date",
       "article"."view_count", "article"."is_published"
FROM "article"
```

### 활용 시나리오

```python
# 1. API 응답용 데이터 준비
def get_article_list_api(request):
    articles = Article.objects.filter(is_published=True).values(
        'id', 'title', 'summary', 'author__name', 'published_date'
    )
    return JsonResponse({'articles': list(articles)})

# 2. 대시보드용 통계 데이터
def get_dashboard_stats():
    stats = Article.objects.values('author__name').annotate(
        article_count=Count('id'),
        total_views=Sum('view_count'),
        avg_views=Avg('view_count')
    )
    return list(stats)

# 3. 검색 결과 최적화
def search_articles(query):
    return Article.objects.filter(
        title__icontains=query
    ).values(
        'id', 'title', 'summary', 'author__name'
    )[:20]  # 상위 20개만
```

## 📋 2. values_list() 메서드

### 기본 개념

`values_list()`는 결과를 튜플 형태로 반환합니다. 딕셔너리보다 메모리 효율이 좋고, 단순한 데이터 처리에 적합합니다.

### 사용법과 옵션

```python
# 기본 사용법 - 튜플 반환
articles = Article.objects.values_list('title', 'author__name', 'view_count')
for article in articles:
    print(article)
    # ('Django 튜토리얼', '김개발', 1250)

# flat=True - 단일 필드의 경우 평면 리스트 반환
titles = Article.objects.values_list('title', flat=True)
print(list(titles))
# ['Django 튜토리얼', 'Python 기초', 'REST API 설계']

# named=True - 명명된 튜플 반환 (Django 4.2+)
from collections import namedtuple
articles = Article.objects.values_list('title', 'view_count', named=True)
for article in articles:
    print(f"제목: {article.title}, 조회수: {article.view_count}")
```

### 성능 비교 예제

```python
import time
from django.db import connection

# 성능 테스트 함수
def measure_query_performance(queryset, description):
    start_time = time.time()
    list(queryset)  # 강제 평가
    end_time = time.time()
    
    print(f"{description}")
    print(f"실행 시간: {end_time - start_time:.4f}초")
    print(f"SQL 쿼리 수: {len(connection.queries)}")
    print("=" * 50)

# 테스트 실행
def performance_comparison():
    # 전체 객체 조회
    full_objects = Article.objects.all()
    measure_query_performance(full_objects, "전체 객체 조회")
    
    # values() 사용
    values_query = Article.objects.values('title', 'view_count')
    measure_query_performance(values_query, "values() 사용")
    
    # values_list() 사용
    values_list_query = Article.objects.values_list('title', 'view_count')
    measure_query_performance(values_list_query, "values_list() 사용")
```

### 실용적 활용 예제

```python
# 1. 선택 옵션 생성
def get_author_choices():
    return Article.objects.values_list('author_id', 'author__name').distinct()

# 2. 데이터 내보내기
def export_article_data():
    articles = Article.objects.values_list(
        'title', 'author__name', 'published_date', 'view_count'
    )
    
    import csv
    with open('articles.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['제목', '작성자', '발행일', '조회수'])
        writer.writerows(articles)

# 3. 간단한 통계 계산
def get_view_stats():
    view_counts = Article.objects.values_list('view_count', flat=True)
    return {
        'total': sum(view_counts),
        'average': sum(view_counts) / len(view_counts),
        'max': max(view_counts),
        'min': min(view_counts)
    }
```

## 🎯 3. only() 메서드

### 기본 개념

`only()`는 지정된 필드만 데이터베이스에서 가져오지만, 모델 인스턴스를 반환합니다. 다른 필드에 접근하면 추가 쿼리가 발생합니다.

### 기본 사용법

```python
# only() 사용 - 지정된 필드만 로드
articles = Article.objects.only('title', 'published_date')

for article in articles:
    print(article.title)          # OK - 이미 로드된 필드
    print(article.published_date) # OK - 이미 로드된 필드
    print(article.content)        # 추가 DB 쿼리 발생!
```

### 지연 로딩 동작 분석

```python
# 지연 로딩 테스트
def test_deferred_loading():
    # only()로 제한된 필드만 로드
    article = Article.objects.only('title').first()
    
    print("=== 초기 로드된 필드 ===")
    print(f"제목: {article.title}")  # 쿼리 없음
    
    print("=== 추가 필드 접근 ===")
    print(f"내용: {article.content}")  # 새로운 쿼리 발생
    
    # 필드별 로드 상태 확인
    print(f"지연 필드들: {article.get_deferred_fields()}")
```

### ForeignKey와 only() 활용

```python
# 관계 필드 최적화
def optimized_article_view():
    # 작성자 정보도 함께 최적화
    articles = Article.objects.select_related('author').only(
        'title', 'summary', 'published_date',
        'author__name', 'author__email'
    )
    
    for article in articles:
        print(f"제목: {article.title}")
        print(f"작성자: {article.author.name}")  # 추가 쿼리 없음
        print(f"이메일: {article.author.email}")  # 추가 쿼리 없음
        # print(f"바이오: {article.author.bio}")  # 추가 쿼리 발생!

# prefetch_related와 only() 조합
def complex_optimization():
    authors = Author.objects.prefetch_related(
        Prefetch(
            'article_set',
            queryset=Article.objects.only('title', 'view_count')
        )
    ).only('name', 'email')
    
    for author in authors:
        print(f"작성자: {author.name}")
        for article in author.article_set.all():
            print(f"  - {article.title}: {article.view_count}회")
```

## ⏱️ 4. defer() 메서드

### 기본 개념

`defer()`는 `only()`의 반대 개념으로, 지정된 필드를 제외한 모든 필드를 로드합니다. 큰 텍스트 필드나 바이너리 필드를 제외할 때 유용합니다.

### 기본 사용법

```python
# defer() 사용 - 지정된 필드 제외하고 로드
articles = Article.objects.defer('content', 'summary')

for article in articles:
    print(article.title)     # OK - 로드된 필드
    print(article.view_count) # OK - 로드된 필드
    print(article.content)   # 추가 DB 쿼리 발생!
```

### 대용량 필드 처리

```python
# 대용량 텍스트 필드 최적화
def article_list_view():
    # content 필드는 크기가 크므로 목록에서 제외
    articles = Article.objects.defer('content').filter(is_published=True)
    
    context = {
        'articles': articles,
        'total_count': articles.count()
    }
    return render(request, 'articles/list.html', context)

def article_detail_view(request, article_id):
    # 상세 페이지에서는 모든 필드 필요
    article = Article.objects.get(id=article_id)
    return render(request, 'articles/detail.html', {'article': article})

# 파일 업로드가 있는 모델의 경우
class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    file_content = models.BinaryField()  # 큰 바이너리 데이터
    uploaded_at = models.DateTimeField(auto_now_add=True)

# 파일 내용 제외하고 목록 조회
def document_list():
    return Document.objects.defer('file_content').all()
```

### 복합 최적화 전략

```python
# defer()와 select_related() 조합
def optimized_article_with_author():
    return Article.objects.select_related('author').defer(
        'content',           # 큰 텍스트 필드 제외
        'author__bio'        # 작성자 바이오도 제외
    )

# 조건부 defer() 사용
def conditional_defer(include_content=False):
    queryset = Article.objects.select_related('author')
    
    if not include_content:
        queryset = queryset.defer('content')
    
    return queryset
```

## ⚡ 5. 성능 비교 및 분석

### 메모리 사용량 비교

```python
import sys
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def memory_usage_comparison():
    # 테스트 데이터 생성
    test_count = 1000
    
    # 1. 전체 객체 로드
    full_objects = list(Article.objects.all()[:test_count])
    full_memory = sys.getsizeof(full_objects) + sum(
        sys.getsizeof(obj) for obj in full_objects
    )
    
    # 2. values() 사용
    values_data = list(Article.objects.values(
        'title', 'view_count'
    )[:test_count])
    values_memory = sys.getsizeof(values_data) + sum(
        sys.getsizeof(item) for item in values_data
    )
    
    # 3. values_list() 사용
    values_list_data = list(Article.objects.values_list(
        'title', 'view_count'
    )[:test_count])
    values_list_memory = sys.getsizeof(values_list_data) + sum(
        sys.getsizeof(item) for item in values_list_data
    )
    
    # 4. only() 사용
    only_objects = list(Article.objects.only(
        'title', 'view_count'
    )[:test_count])
    only_memory = sys.getsizeof(only_objects) + sum(
        sys.getsizeof(obj) for obj in only_objects
    )
    
    print("=== 메모리 사용량 비교 ===")
    print(f"전체 객체: {full_memory:,} bytes")
    print(f"values(): {values_memory:,} bytes ({values_memory/full_memory*100:.1f}%)")
    print(f"values_list(): {values_list_memory:,} bytes ({values_list_memory/full_memory*100:.1f}%)")
    print(f"only(): {only_memory:,} bytes ({only_memory/full_memory*100:.1f}%)")
```

### 실행 시간 벤치마크

```python
import time
from django.db import connection, reset_queries

def benchmark_methods():
    test_queries = [
        ("Full objects", lambda: list(Article.objects.all()[:1000])),
        ("values()", lambda: list(Article.objects.values('title', 'view_count')[:1000])),
        ("values_list()", lambda: list(Article.objects.values_list('title', 'view_count')[:1000])),
        ("only()", lambda: list(Article.objects.only('title', 'view_count')[:1000])),
        ("defer()", lambda: list(Article.objects.defer('content', 'summary')[:1000])),
    ]
    
    results = []
    
    for name, query_func in test_queries:
        reset_queries()
        start_time = time.time()
        
        # 3번 실행해서 평균 계산
        times = []
        for _ in range(3):
            start = time.time()
            query_func()
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        query_count = len(connection.queries)
        
        results.append({
            'method': name,
            'avg_time': avg_time,
            'query_count': query_count
        })
    
    print("=== 성능 벤치마크 결과 ===")
    for result in results:
        print(f"{result['method']:15}: {result['avg_time']:.4f}초, {result['query_count']}개 쿼리")
```

## 🎯 6. 실무 적용 가이드

### 방법별 선택 기준

```python
# 1. API 응답 최적화
class ArticleViewSet(viewsets.ModelViewSet):
    def list(self, request):
        # values() 사용 - JSON 직렬화에 최적
        articles = Article.objects.filter(
            is_published=True
        ).values(
            'id', 'title', 'summary', 'author__name', 'published_date'
        )
        return Response({'articles': list(articles)})
    
    def retrieve(self, request, pk=None):
        # only() 사용 - 모델 메서드 활용 가능
        article = Article.objects.select_related('author').only(
            'title', 'content', 'author__name', 'published_date'
        ).get(pk=pk)
        
        # 모델 메서드 사용 가능
        return Response({
            'article': {
                'title': article.title,
                'content': article.content,
                'author': article.author.name,
                'word_count': article.get_word_count(),  # 모델 메서드
            }
        })

# 2. 대시보드 데이터 준비
def dashboard_analytics():
    # values() + aggregation
    author_stats = Article.objects.values('author__name').annotate(
        total_articles=Count('id'),
        total_views=Sum('view_count'),
        avg_views=Avg('view_count'),
        latest_article=Max('published_date')
    ).order_by('-total_views')
    
    return list(author_stats)

# 3. 데이터 내보내기
def export_to_csv():
    # values_list() 사용 - CSV 작성에 최적
    data = Article.objects.filter(
        is_published=True
    ).values_list(
        'title', 'author__name', 'published_date', 'view_count'
    )
    
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['제목', '작성자', '발행일', '조회수'])
    writer.writerows(data)
    
    return response
```

### 성능 모니터링

```python
# Django Debug Toolbar와 함께 사용
def monitor_query_performance(view_func):
    def wrapper(*args, **kwargs):
        from django.db import connection
        from django.conf import settings
        
        if settings.DEBUG:
            initial_queries = len(connection.queries)
            start_time = time.time()
            
            result = view_func(*args, **kwargs)
            
            end_time = time.time()
            final_queries = len(connection.queries)
            
            print(f"함수: {view_func.__name__}")
            print(f"실행 시간: {end_time - start_time:.4f}초")
            print(f"DB 쿼리: {final_queries - initial_queries}개")
            
            return result
        
        return view_func(*args, **kwargs)
    
    return wrapper

# 사용 예제
@monitor_query_performance
def optimized_article_list():
    return Article.objects.select_related('author').only(
        'title', 'summary', 'published_date', 'author__name'
    )[:50]
```

## 📊 7. 고급 최적화 패턴

### Prefetch와 조합

```python
from django.db.models import Prefetch

# 복잡한 관계 최적화
def advanced_optimization():
    authors = Author.objects.prefetch_related(
        Prefetch(
            'article_set',
            queryset=Article.objects.filter(is_published=True).only(
                'title', 'view_count', 'published_date'
            ).order_by('-published_date')
        )
    ).only('name', 'email')
    
    for author in authors:
        print(f"작성자: {author.name}")
        for article in author.article_set.all():
            print(f"  - {article.title} ({article.view_count}회)")

# 조건부 최적화
def conditional_optimization(user_role):
    queryset = Article.objects.select_related('author')
    
    if user_role == 'admin':
        # 관리자는 모든 필드 접근 가능
        return queryset
    elif user_role == 'editor':
        # 에디터는 content 제외
        return queryset.defer('content')
    else:
        # 일반 사용자는 제목과 요약만
        return queryset.only('title', 'summary', 'author__name')
```

### 캐싱과 연계

```python
from django.core.cache import cache

def cached_article_list():
    cache_key = 'article_list_optimized'
    articles = cache.get(cache_key)
    
    if articles is None:
        # values()로 캐시하기 좋은 형태로 변환
        articles = list(Article.objects.filter(
            is_published=True
        ).values(
            'id', 'title', 'summary', 'author__name', 'published_date'
        ).order_by('-published_date')[:20])
        
        cache.set(cache_key, articles, 300)  # 5분 캐시
    
    return articles
```

## 🎯 결론 및 권장사항

### 언제 어떤 방법을 사용할까?

| 상황 | 권장 방법 | 이유 |
|------|----------|------|
| API JSON 응답 | `values()` | 딕셔너리 → JSON 변환 용이 |
| CSV/Excel 내보내기 | `values_list()` | 튜플 → 행 데이터 최적 |
| 템플릿 렌더링 | `only()` | 모델 메서드 사용 가능 |
| 대용량 텍스트 제외 | `defer()` | 선택적 필드 로딩 |
| 단순 통계 계산 | `values_list(flat=True)` | 메모리 효율 최고 |

### 성능 최적화 체크리스트

1. **필요한 필드만 선택**: 불필요한 필드 로딩 방지
2. **관계 최적화**: `select_related()`, `prefetch_related()` 활용
3. **인덱스 활용**: 필터링 필드에 적절한 인덱스 설정
4. **지연 로딩 주의**: `only()`, `defer()` 사용 시 추가 쿼리 발생 가능성 고려
5. **캐싱 전략**: 자주 사용되는 데이터는 캐시 활용

### 실무 권장사항

```python
# 좋은 예시
def good_optimization():
    # 목적에 맞는 최적화
    return Article.objects.select_related('author').values(
        'id', 'title', 'summary', 'author__name', 'published_date'
    ).filter(is_published=True).order_by('-published_date')

# 피해야 할 예시
def bad_optimization():
    # N+1 문제 발생 위험
    articles = Article.objects.only('title')  # author 정보 없음
    for article in articles:
        print(article.author.name)  # 매번 추가 쿼리!
```

Django의 QuerySet 최적화 메서드들을 적절히 활용하면 애플리케이션의 성능을 크게 개선할 수 있습니다. 각 방법의 특성을 이해하고 상황에 맞게 선택하여 사용하세요.

---

*더 자세한 내용은 [Django 공식 문서](https://docs.djangoproject.com/en/stable/ref/models/querysets/)를 참조하시기 바랍니다.*