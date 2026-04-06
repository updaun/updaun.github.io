---
layout: post
title: "Django Ninja + PostgreSQL 풀텍스트 검색 완전 가이드 - 한글 최적화와 오탈자 허용 전략까지"
date: 2026-04-05
categories: backend
tags: [django-ninja, postgresql, fulltext-search, pg_trgm, pgroonga, korean-search, python]
author: updaun
render_with_liquid: false
image: "/assets/img/posts/2026-04-05-django-ninja-postgres-fulltext-search-guide.webp"
---

# Django Ninja + PostgreSQL 풀텍스트 검색 완전 가이드 - 한글 최적화와 오탈자 허용 전략까지

검색 기능은 서비스 품질을 결정짓는 핵심 요소 중 하나입니다. 사용자가 "파이썬 장고"를 검색할 때, "파이썬"과 "장고"가 따로 존재하는 문서를 찾아줄 수 있어야 합니다. 더 나아가 "잠고"나 "쟝고"처럼 오탈자가 있어도 올바른 결과를 보여줘야 합니다. 한국어는 특히 조사와 어미 변화, 복합어 분해 등의 문제로 영어보다 훨씬 복잡한 처리가 필요합니다.

이 포스트에서는 **Django Ninja** + **PostgreSQL**을 사용해서 검색 시스템을 처음부터 끝까지 구축합니다. PostgreSQL 내장 Full-Text Search로 기본 틀을 잡고, `pg_trgm`으로 오탈자 허용 검색을 추가하며, `pgroonga`로 한국어 검색을 제대로 처리하는 방법까지 순서대로 다룹니다.

---

## 1. PostgreSQL Full-Text Search 핵심 개념

구현에 들어가기 전에 PostgreSQL이 텍스트 검색을 어떻게 처리하는지 원리를 이해해야 합니다. 이 부분을 모르면 나중에 예상치 못한 동작이 왜 발생하는지 파악하기 어렵습니다.

### tsvector: 검색용 문서 표현

PostgreSQL Full-Text Search의 핵심은 `tsvector`입니다. 원문 텍스트를 검색에 최적화된 **어휘 목록(lexeme)**으로 변환한 자료형입니다.

```sql
-- tsvector 변환 예시
SELECT to_tsvector('english', 'Django is a high-level Python web framework');
-- 'django':1 'framework':7 'high-level':4 'python':5 'web':6
```

스톱워드(is, a, the 등)는 제거되고, 각 단어는 정규화됩니다. 숫자는 단어 내 위치(위치 번호)를 함께 저장해서 근접도 랭킹에 활용합니다.

### tsquery: 검색 조건 표현

사용자 입력을 `tsquery`로 변환해 `tsvector`와 매칭합니다.

```sql
-- & (AND), | (OR), ! (NOT), <-> (근접)
SELECT to_tsquery('english', 'django & python');
SELECT plainto_tsquery('english', 'django python web');   -- 자연어 파싱
SELECT websearch_to_tsquery('english', '"django rest" OR fastapi');  -- 웹 검색 스타일
```

### 한국어의 문제

`english` 설정으로 한국어를 처리하면 어간 추출(stemming)과 스톱워드 처리가 전혀 동작하지 않습니다.

```sql
SELECT to_tsvector('english', '파이썬 장고 웹 프레임워크');
-- '파이썬' 장고' '웹' '프레임워크'  ← 그냥 단어 그대로 저장됨
-- '파이썬으로' 검색 시 '파이썬'은 찾지 못함
```

한국어에서는 "파이썬으로", "파이썬의", "파이썬이" 모두 동일한 어근 "파이썬"에서 파생됐지만, 기본 FTS는 이를 전부 다른 단어로 취급합니다. 이 문제를 해결하는 전략을 뒤에서 상세히 다룹니다.

---

## 2. 프로젝트 초기 설정

### 환경 구성

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate

# 핵심 패키지 설치
pip install django django-ninja psycopg2-binary python-dotenv

# requirements.txt 생성
pip freeze > requirements.txt
```

### Django 프로젝트 생성

```bash
django-admin startproject config .
python manage.py startapp search
```

### `settings.py` 설정

```python
# config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",   # PostgreSQL 전용 기능 활성화
    "search",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "searchdb"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}
```

```env
# .env
DJANGO_SECRET_KEY=your-very-secret-key-here
DEBUG=True
DB_NAME=searchdb
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```

---

## 3. 검색 모델 설계

검색 성능의 90%는 모델 설계 단계에서 결정됩니다. `SearchVectorField`를 별도 컬럼으로 저장해 검색 시점에 매번 변환 연산을 수행하지 않도록 합니다.

### 모델 정의

```python
# search/models.py
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Article(models.Model):
    """기사/콘텐츠 모델 - 검색 대상"""

    title = models.CharField(max_length=300, verbose_name="제목")
    subtitle = models.CharField(max_length=500, blank=True, verbose_name="부제목")
    body = models.TextField(verbose_name="본문")
    author = models.CharField(max_length=100, verbose_name="작성자")
    category = models.CharField(max_length=50, db_index=True, verbose_name="카테고리")
    tags = models.JSONField(default=list, verbose_name="태그 목록")
    published_at = models.DateTimeField(auto_now_add=True, verbose_name="게시일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    view_count = models.PositiveIntegerField(default=0, verbose_name="조회수")

    # 검색 색인 컬럼: 실시간 연산 대신 사전 계산된 tsvector 저장
    search_vector = SearchVectorField(null=True, blank=True, verbose_name="검색 벡터")

    class Meta:
        verbose_name = "기사"
        verbose_name_plural = "기사 목록"
        indexes = [
            # GIN 인덱스: tsvector 검색에 최적화된 자료구조
            GinIndex(fields=["search_vector"], name="article_search_gin_idx"),
        ]

    def __str__(self):
        return self.title


class SearchLog(models.Model):
    """검색 로그 - 검색어 분석 및 품질 개선에 활용"""

    query = models.CharField(max_length=500, verbose_name="검색어")
    result_count = models.PositiveIntegerField(default=0, verbose_name="결과 수")
    response_time_ms = models.FloatField(verbose_name="응답 시간(ms)")
    searched_at = models.DateTimeField(auto_now_add=True, verbose_name="검색 시각")
    user_agent = models.CharField(max_length=300, blank=True, verbose_name="유저 에이전트")

    class Meta:
        verbose_name = "검색 로그"
        indexes = [
            models.Index(fields=["query"], name="searchlog_query_idx"),
            models.Index(fields=["searched_at"], name="searchlog_time_idx"),
        ]

    def __str__(self):
        return f"{self.query} ({self.result_count}건)"
```

### GIN vs GiST 인덱스 선택 기준

| 구분 | GIN | GiST |
|---|---|---|
| 읽기 속도 | 빠름 | 느림 |
| 쓰기 속도 | 느림 | 빠름 |
| 저장 공간 | 큼 | 작음 |
| 적합한 상황 | 읽기 위주 검색 서비스 | 쓰기가 잦은 실시간 데이터 |

검색 서비스는 대부분 읽기가 압도적으로 많으므로 **GIN 인덱스**를 선택합니다. 단, 대용량 배치 삽입이 자주 일어난다면 GiST를 검토합니다.

---

## 4. 검색 벡터 자동 갱신 설정

모델에 레코드가 저장될 때마다 `search_vector` 컬럼을 자동으로 갱신하는 두 가지 방법이 있습니다. PostgreSQL 트리거 방식이 가장 안정적입니다.

### 방법 1: Django Signal 활용

```python
# search/signals.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Article


@receiver(post_save, sender=Article)
def update_search_vector(sender, instance, **kwargs):
    """Article 저장 시 search_vector 자동 갱신"""
    if kwargs.get("update_fields") and "search_vector" in kwargs["update_fields"]:
        # 무한 루프 방지: search_vector 업데이트로 인한 재귀 호출 차단
        return

    Article.objects.filter(pk=instance.pk).update(
        search_vector=(
            # 제목: 가중치 A (가장 높음), 부제목: B, 본문: C
            SearchVector("title", weight="A", config="simple")
            + SearchVector("subtitle", weight="B", config="simple")
            + SearchVector("body", weight="C", config="simple")
            + SearchVector("author", weight="D", config="simple")
        )
    )
```

```python
# search/apps.py
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "search"

    def ready(self):
        import search.signals  # noqa: F401
```

Signal 방식은 Django 레이어에서 처리되므로 이해하기 쉽지만, 대량 `bulk_create` 시 시그널이 발화하지 않는다는 한계가 있습니다.

### 방법 2: PostgreSQL 트리거 (권장)

PostgreSQL 트리거는 DB 레벨에서 동작하므로 Django를 통하지 않는 삽입/수정에도 색인이 자동 갱신됩니다.

```python
# search/migrations/0002_add_search_trigger.py
from django.db import migrations


TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION update_article_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A')
        || setweight(to_tsvector('simple', coalesce(NEW.subtitle, '')), 'B')
        || setweight(to_tsvector('simple', coalesce(NEW.body, '')), 'C')
        || setweight(to_tsvector('simple', coalesce(NEW.author, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER article_search_vector_update
    BEFORE INSERT OR UPDATE OF title, subtitle, body, author
    ON search_article
    FOR EACH ROW
    EXECUTE FUNCTION update_article_search_vector();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS article_search_vector_update ON search_article;
DROP FUNCTION IF EXISTS update_article_search_vector();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=TRIGGER_SQL, reverse_sql=DROP_TRIGGER_SQL),
    ]
```

`simple` 설정을 사용하면 스톱워드를 제거하지 않고 모든 단어를 보존합니다. 한국어처럼 언어별 사전이 없는 경우 `simple`이 가장 안전한 선택입니다.

---

## 5. Django Ninja 검색 API 구현

모델과 색인이 준비됐으니 이제 API를 만듭니다. 스키마 정의부터 시작합니다.

### 스키마 정의

```python
# search/schemas.py
from ninja import Schema
from pydantic import Field, field_validator
from typing import Optional
from datetime import datetime


class ArticleCreateSchema(Schema):
    title: str = Field(..., min_length=1, max_length=300)
    subtitle: str = Field(default="", max_length=500)
    body: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list)


class ArticleResponseSchema(Schema):
    id: int
    title: str
    subtitle: str
    author: str
    category: str
    tags: list[str]
    published_at: datetime
    view_count: int
    # 검색 결과에서 관련도 점수 포함
    rank: Optional[float] = None
    headline: Optional[str] = None  # 검색어 하이라이팅


class SearchQuerySchema(Schema):
    q: str = Field(..., min_length=1, max_length=200, description="검색어")
    category: Optional[str] = Field(default=None, description="카테고리 필터")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # 특수문자 제거 (SQL Injection 방지는 ORM이 담당하지만, 검색 품질 향상을 위해 정제)
        import re
        # tsquery에서 의미없는 특수기호 제거
        cleaned = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]", " ", v)
        return " ".join(cleaned.split())


class SearchResponseSchema(Schema):
    total: int
    page: int
    page_size: int
    results: list[ArticleResponseSchema]
    query_time_ms: float
```

### 검색 API 라우터

```python
# search/api.py
import time
from typing import Optional

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    SearchHeadline,
)
from django.db import connection
from ninja import Router

from .models import Article, SearchLog
from .schemas import (
    ArticleCreateSchema,
    ArticleResponseSchema,
    SearchQuerySchema,
    SearchResponseSchema,
)

router = Router(tags=["검색"])


@router.post("/articles", response=ArticleResponseSchema, summary="기사 등록")
def create_article(request, payload: ArticleCreateSchema):
    article = Article.objects.create(**payload.dict())
    return ArticleResponseSchema(
        id=article.id,
        title=article.title,
        subtitle=article.subtitle,
        author=article.author,
        category=article.category,
        tags=article.tags,
        published_at=article.published_at,
        view_count=article.view_count,
    )


@router.get("/search", response=SearchResponseSchema, summary="풀텍스트 검색")
def search_articles(request, query: SearchQuerySchema = None, q: str = "", category: Optional[str] = None, page: int = 1, page_size: int = 20):
    """
    PostgreSQL Full-Text Search를 사용한 기사 검색 API.
    - 검색어는 AND 조건으로 처리 (모든 단어 포함)
    - 결과는 관련도 점수(rank) 기준 정렬
    - 검색어 하이라이팅 제공
    """
    start_time = time.perf_counter()

    # 검색어 정제 (스키마 validator를 통과한 값)
    import re
    cleaned_q = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]", " ", q)
    cleaned_q = " ".join(cleaned_q.split())

    if not cleaned_q:
        return SearchResponseSchema(total=0, page=page, page_size=page_size, results=[], query_time_ms=0)

    # SearchQuery: 여러 단어를 AND 조건으로 연결
    search_query = SearchQuery(cleaned_q, config="simple", search_type="websearch")

    # 기본 쿼리셋
    qs = Article.objects.filter(search_vector=search_query)

    if category:
        qs = qs.filter(category=category)

    # 관련도 점수 계산 (제목 가중치를 본문보다 높게)
    rank_annotation = SearchRank(
        "search_vector",
        search_query,
        weights=[0.1, 0.2, 0.4, 1.0],  # D, C, B, A 가중치
        normalization=2,  # 문서 길이로 정규화
    )

    # 검색어 하이라이팅
    headline_annotation = SearchHeadline(
        "body",
        search_query,
        config="simple",
        start_sel="<mark>",
        stop_sel="</mark>",
        max_words=35,
        min_words=15,
        max_fragments=3,
    )

    qs = qs.annotate(rank=rank_annotation, headline=headline_annotation)
    qs = qs.order_by("-rank", "-published_at")

    # 페이지네이션
    total = qs.count()
    offset = (page - 1) * page_size
    articles = qs[offset : offset + page_size]

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # 검색 로그 기록
    SearchLog.objects.create(
        query=cleaned_q,
        result_count=total,
        response_time_ms=round(elapsed_ms, 2),
    )

    results = [
        ArticleResponseSchema(
            id=a.id,
            title=a.title,
            subtitle=a.subtitle,
            author=a.author,
            category=a.category,
            tags=a.tags,
            published_at=a.published_at,
            view_count=a.view_count,
            rank=round(a.rank, 4),
            headline=a.headline,
        )
        for a in articles
    ]

    return SearchResponseSchema(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
        query_time_ms=round(elapsed_ms, 2),
    )
```

### API 등록

```python
# config/api.py
from ninja import NinjaAPI
from search.api import router as search_router

api = NinjaAPI(
    title="Search API",
    version="1.0.0",
    description="Django Ninja + PostgreSQL Full-Text Search",
)

api.add_router("/search", search_router)
```

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

---

## 6. 기존 데이터 일괄 색인 갱신

새 시스템을 도입하거나 컬럼을 추가했다면 기존 레코드에 대해 색인을 모두 갱신해야 합니다. 한 번에 모든 행을 업데이트하면 테이블 락이 발생할 수 있으므로 배치 단위로 처리합니다.

```python
# search/management/commands/rebuild_search_index.py
from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from search.models import Article


class Command(BaseCommand):
    help = "search_vector 컬럼 전체 재구성 (배치 단위 처리)"

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500, help="배치 크기 (기본: 500)")

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        total = Article.objects.count()
        self.stdout.write(f"총 {total:,}건 처리 시작 (배치 크기: {batch_size})")

        updated = 0
        ids = list(Article.objects.values_list("id", flat=True).order_by("id"))

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            Article.objects.filter(id__in=batch_ids).update(
                search_vector=(
                    SearchVector("title", weight="A", config="simple")
                    + SearchVector("subtitle", weight="B", config="simple")
                    + SearchVector("body", weight="C", config="simple")
                    + SearchVector("author", weight="D", config="simple")
                )
            )
            updated += len(batch_ids)
            progress = updated / total * 100
            self.stdout.write(f"진행: {updated:,}/{total:,} ({progress:.1f}%)", ending="\r")

        self.stdout.write(f"\n완료: {updated:,}건 색인 갱신")
```

```bash
python manage.py rebuild_search_index
python manage.py rebuild_search_index --batch-size=1000  # 대용량 테이블
```

---

## 7. 한글 검색 최적화 전략

PostgreSQL의 기본 FTS는 한국어를 제대로 처리하지 못합니다. 어간 추출도 없고 언어별 사전도 없기 때문입니다. 한국어 검색 품질을 높이는 방법을 세 단계로 나눠서 설명합니다.

### 전략 1: `simple` 설정 + N-gram 분해 (가장 간단)

정확한 어간 추출 없이 텍스트를 일정 길이 단위로 쪼개서 색인하는 방식입니다. 구현이 간단하고 추가 플러그인이 필요 없습니다.

```python
# search/utils.py
import re


def normalize_korean(text: str) -> str:
    """한국어 텍스트 정규화 및 N-gram 토큰 생성"""
    # 특수문자, 공백 정규화
    text = re.sub(r"[^\w가-힣]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = text.split()
    ngrams = []

    for token in tokens:
        ngrams.append(token)
        # 2-gram 추가: '파이썬' → '파이', '이썬'
        if len(token) >= 2:
            for i in range(len(token) - 1):
                ngrams.append(token[i : i + 2])
        # 3-gram 추가: '프레임워크' → '프레임', '레임워', '임워크'
        if len(token) >= 3:
            for i in range(len(token) - 2):
                ngrams.append(token[i : i + 3])

    return " ".join(dict.fromkeys(ngrams))  # 중복 제거, 순서 유지


def build_korean_search_query(query: str) -> str:
    """검색어를 N-gram 기반 tsquery 문자열로 변환"""
    query = re.sub(r"[^\w가-힣\s]", " ", query)
    words = query.split()
    if not words:
        return ""
    # 각 단어를 AND 조건으로 연결
    return " & ".join(words)
```

이 방식은 완벽하지 않지만 추가 설치 없이 즉시 적용할 수 있는 현실적인 해법입니다.

### 전략 2: `pg_bigm` 확장 - 2-gram 기반 전문 검색

`pg_bigm`은 PostgreSQL 확장 모듈로, 텍스트를 2-gram(바이그램)으로 분해해서 색인합니다. 한국어, 중국어, 일본어 등 **공백 기반 단어 분리가 어려운 언어**에 적합합니다.

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-16-pg-bigm

# macOS (Homebrew)
brew install pg_bigm
```

```sql
-- PostgreSQL 클라이언트에서 확장 설치
CREATE EXTENSION pg_bigm;

-- 2-gram 인덱스 생성
CREATE INDEX article_body_bigm_idx ON search_article
    USING gin (body gin_bigm_ops);
CREATE INDEX article_title_bigm_idx ON search_article
    USING gin (title gin_bigm_ops);
```

```python
# Django 마이그레이션으로 pg_bigm 확장 설치
# search/migrations/0003_add_pg_bigm.py
from django.db import migrations
from django.contrib.postgres.operations import CreateExtension


BIGM_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS article_body_bigm_idx
    ON search_article USING gin (body gin_bigm_ops);
CREATE INDEX IF NOT EXISTS article_title_bigm_idx
    ON search_article USING gin (title gin_bigm_ops);
"""

DROP_BIGM_INDEXES_SQL = """
DROP INDEX IF EXISTS article_body_bigm_idx;
DROP INDEX IF EXISTS article_title_bigm_idx;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0002_add_search_trigger"),
    ]

    operations = [
        CreateExtension("pg_bigm"),
        migrations.RunSQL(sql=BIGM_INDEXES_SQL, reverse_sql=DROP_BIGM_INDEXES_SQL),
    ]
```

`pg_bigm`을 사용하면 `LIKE '%검색어%'` 패턴의 쿼리가 전체 테이블 스캔 없이 인덱스를 활용합니다. FTS 색인 없이도 한글 부분 문자열 검색이 빠르게 동작하는 것이 핵심 장점입니다.

```python
# pg_bigm을 Django에서 활용하는 검색 함수
from django.db.models import Q


def bigm_search(query: str):
    """pg_bigm 기반 한국어 부분 일치 검색"""
    # LIKE 쿼리 - pg_bigm 인덱스가 자동 적용됨
    return Article.objects.filter(
        Q(title__contains=query) | Q(body__contains=query)
    ).order_by("-published_at")
```

### 전략 3: `pgroonga` 확장 - 형태소 분석 기반 (가장 강력)

`pgroonga`는 Groonga 검색 엔진을 PostgreSQL에 통합한 확장으로, 한국어 형태소 분석기(`mecab`, `nori`)를 지원합니다. 세 가지 방식 중 가장 검색 품질이 높습니다.

```bash
# Ubuntu/Debian (pgroonga 공식 저장소 추가 필요)
sudo apt-get install postgresql-16-pgroonga

# Docker 사용 시 Dockerfile 예시
# FROM groonga/pgroonga:latest-debian-16
```

```sql
-- pgroonga 확장 설치
CREATE EXTENSION pgroonga;

-- pgroonga 인덱스 생성 (한국어 형태소 분석기 적용)
CREATE INDEX article_pgroonga_idx ON search_article
    USING pgroonga (title, subtitle, body)
    WITH (
        plugins='token_filters/stem',
        token_filters='TokenFilterStem'
    );
```

```python
# search/migrations/0004_add_pgroonga.py
from django.db import migrations
from django.contrib.postgres.operations import CreateExtension


PGROONGA_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS article_pgroonga_idx
    ON search_article USING pgroonga (title, subtitle, body);
"""

DROP_PGROONGA_INDEX_SQL = """
DROP INDEX IF EXISTS article_pgroonga_idx;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0003_add_pg_bigm"),
    ]

    operations = [
        CreateExtension("pgroonga"),
        migrations.RunSQL(sql=PGROONGA_INDEX_SQL, reverse_sql=DROP_PGROONGA_INDEX_SQL),
    ]
```

```python
# pgroonga를 사용한 한국어 검색 뷰
from django.db import connection


def pgroonga_search(query: str, page: int = 1, page_size: int = 20):
    """pgroonga 기반 고품질 한국어 검색"""
    offset = (page - 1) * page_size

    with connection.cursor() as cursor:
        # pgroonga의 &@~ 연산자: 형태소 분석 기반 검색
        cursor.execute(
            """
            SELECT
                id, title, subtitle, author, category, published_at,
                pgroonga_score(tableoid, ctid) AS score,
                pgroonga_highlight_html(body, pgroonga_query_expand('pgroonga_condition', 'term', 'readings', %s)) AS headline
            FROM search_article
            WHERE title &@~ %s OR subtitle &@~ %s OR body &@~ %s
            ORDER BY score DESC, published_at DESC
            LIMIT %s OFFSET %s
            """,
            [query, query, query, query, page_size, offset],
        )
        rows = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM search_article
            WHERE title &@~ %s OR subtitle &@~ %s OR body &@~ %s
            """,
            [query, query, query],
        )
        total = cursor.fetchone()[0]

    return {"total": total, "results": rows}
```

### 현실적인 한국어 검색 조합 전략

세 가지 전략을 모두 도입하는 것이 이상적이지만, 운영 환경의 제약을 감안해 다음 우선순위로 적용합니다.

```
┌──────────────────────────────────────────────────────────┐
│              한국어 검색 전략 선택 가이드                │
├──────────────────┬───────────────────────────────────────┤
│  상황            │  권장 전략                            │
├──────────────────┼───────────────────────────────────────┤
│ 빠른 MVP 출시    │ simple FTS + N-gram 전처리            │
│ 관리형 DB (RDS)  │ pg_bigm (확장 허용 여부 확인 필요)    │
│ 자체 서버 운영   │ pgroonga (최고 품질)                  │
│ 대규모 서비스    │ Elasticsearch / OpenSearch 별도 구축  │
└──────────────────┴───────────────────────────────────────┘
```

---

## 8. 오탈자 허용 검색: pg_trgm 활용

사용자는 항상 정확하게 입력하지 않습니다. "쟝고"를 검색해도 "장고"가 포함된 문서를 찾아야 합니다. PostgreSQL의 `pg_trgm` 확장이 이 문제를 해결합니다.

### pg_trgm 원리

`pg_trgm`은 텍스트를 **3-gram(trignram)** 으로 분해하고, 두 문자열 간 공통 3-gram 비율로 유사도를 계산합니다.

```
"django" → {dja, jan, ang, ngo}
"djago"  → {dja, jag, ago}
공통: {dja} = 1개 / 전체 6개 → 유사도 ≈ 0.18
```

한국어는 한 글자가 초성+중성+종성으로 구성된 음절 단위이므로 3-gram이 잘 동작합니다.

```
"장고" → {장고} → 2-gram만 존재
"쟝고" → {쟝고} → 유사도 계산 가능
"파이썬" → {파이썬} → 3글자면 하나의 3-gram
```

### pg_trgm 인덱스 설정

```python
# search/migrations/0005_add_pg_trgm.py
from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


TRGM_INDEXES_SQL = """
-- GIN 트리그램 인덱스 (LIKE, 유사도 검색에 사용)
CREATE INDEX IF NOT EXISTS article_title_trgm_idx
    ON search_article USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS article_body_trgm_idx
    ON search_article USING gin (body gin_trgm_ops);

-- 유사도 임계값 설정 (0.0 ~ 1.0, 낮을수록 더 많은 결과)
SET pg_trgm.similarity_threshold = 0.2;
"""

DROP_TRGM_INDEXES_SQL = """
DROP INDEX IF EXISTS article_title_trgm_idx;
DROP INDEX IF EXISTS article_body_trgm_idx;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0004_add_pgroonga"),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(sql=TRGM_INDEXES_SQL, reverse_sql=DROP_TRGM_INDEXES_SQL),
    ]
```

### Django에서 pg_trgm 활용

`django.contrib.postgres`는 `TrigramSimilarity`, `TrigramDistance`, `TrigramWordSimilarity`를 내장 제공합니다.

```python
# search/fuzzy_search.py
from django.contrib.postgres.search import (
    TrigramSimilarity,
    TrigramDistance,
    TrigramWordSimilarity,
)
from django.db.models import Q, FloatField
from django.db.models.functions import Greatest
from .models import Article


def fuzzy_search(query: str, threshold: float = 0.2, page: int = 1, page_size: int = 20):
    """
    pg_trgm 기반 오탈자 허용 검색.
    - TrigramSimilarity: 전체 문자열 유사도 (0.0 ~ 1.0)
    - TrigramWordSimilarity: 단어 단위 최대 유사도 (부분 매칭에 유리)
    - threshold: 최소 유사도 점수 (낮출수록 더 많은 오탈자 허용)
    """
    # 제목과 본문에서 각각 유사도를 계산하고 최대값 사용
    qs = Article.objects.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        body_similarity=TrigramWordSimilarity(query, "body"),
        similarity=Greatest(
            TrigramWordSimilarity(query, "title"),
            TrigramWordSimilarity(query, "body"),
            output_field=FloatField(),
        ),
    ).filter(
        similarity__gte=threshold
    ).order_by("-similarity", "-published_at")

    total = qs.count()
    offset = (page - 1) * page_size
    results = qs[offset : offset + page_size]

    return {"total": total, "results": list(results)}


def autocomplete_suggest(partial_query: str, limit: int = 10):
    """
    자동완성 제안: 부분 입력에서 유사한 제목 목록 반환.
    검색창의 자동완성 드롭다운에 활용.
    """
    return (
        Article.objects.annotate(
            similarity=TrigramWordSimilarity(partial_query, "title"),
        )
        .filter(similarity__gte=0.15)
        .order_by("-similarity")
        .values("id", "title", "similarity")[:limit]
    )
```

### pg_trgm 유사도 임계값 튜닝 가이드

임계값은 서비스 특성에 맞게 조정해야 합니다.

```python
# search/api.py 에 추가
@router.get("/search/fuzzy", response=SearchResponseSchema, summary="오탈자 허용 검색")
def fuzzy_search_articles(
    request,
    q: str,
    threshold: float = 0.2,
    page: int = 1,
    page_size: int = 20,
):
    """
    oq 임계값 가이드:
    - 0.3 이상: 유사도 높음 (오탈자 한두 글자만 허용)
    - 0.2 ~ 0.3: 적당한 허용 범위 (권장)
    - 0.1 ~ 0.2: 관대한 허용 (노이즈 증가)
    - 0.1 미만: 너무 광범위한 허용 (비권장)
    """
    import time

    start_time = time.perf_counter()

    # 임계값 범위 제한 (보안: 너무 낮은 값으로 전체 테이블 순회 방지)
    threshold = max(0.1, min(0.5, threshold))

    from .fuzzy_search import fuzzy_search

    result = fuzzy_search(query=q, threshold=threshold, page=page, page_size=page_size)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    results = [
        ArticleResponseSchema(
            id=a.id,
            title=a.title,
            subtitle=a.subtitle,
            author=a.author,
            category=a.category,
            tags=a.tags,
            published_at=a.published_at,
            view_count=a.view_count,
            rank=round(a.similarity, 4),
        )
        for a in result["results"]
    ]

    return SearchResponseSchema(
        total=result["total"],
        page=page,
        page_size=page_size,
        results=results,
        query_time_ms=round(elapsed_ms, 2),
    )


@router.get("/autocomplete", summary="자동완성 제안")
def autocomplete(request, q: str):
    """검색창 자동완성: 부분 입력에서 유사한 제목 최대 10개 반환"""
    if len(q) < 2:
        return {"suggestions": []}

    from .fuzzy_search import autocomplete_suggest

    suggestions = list(autocomplete_suggest(partial_query=q))
    return {"suggestions": suggestions}
```

---

## 9. 통합 검색 전략: FTS + Fuzzy 결합

실무에서는 FTS와 Fuzzy 검색을 함께 사용하는 **하이브리드 전략**이 가장 효과적입니다. 정확한 매칭이 있으면 우선 반환하고, 없을 경우 자동으로 오탈자 허용 검색으로 폴백(fallback)합니다.

```python
# search/hybrid_search.py
import time
from typing import Optional
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchHeadline,
    TrigramWordSimilarity,
)
from django.db.models import FloatField, Value
from django.db.models.functions import Greatest, Coalesce

from .models import Article


def hybrid_search(
    query: str,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    fuzzy_threshold: float = 0.2,
    fuzzy_fallback_min_results: int = 3,
):
    """
    하이브리드 검색:
    1. FTS 정확도 검색 우선 시도
    2. 결과가 부족하면 pg_trgm 오탈자 허용 검색으로 자동 전환

    Returns:
        dict: {total, results, search_type: "fts" | "fuzzy"}
    """
    search_query = SearchQuery(query, config="simple", search_type="websearch")

    # --- 1단계: FTS 검색 ---
    fts_qs = Article.objects.filter(search_vector=search_query)
    if category:
        fts_qs = fts_qs.filter(category=category)

    fts_qs = fts_qs.annotate(
        rank=SearchRank("search_vector", search_query, normalization=2),
        headline=SearchHeadline(
            "body",
            search_query,
            config="simple",
            start_sel="<mark>",
            stop_sel="</mark>",
            max_words=30,
            min_words=10,
        ),
    ).order_by("-rank", "-published_at")

    fts_total = fts_qs.count()

    # FTS 결과가 충분하면 그대로 반환
    if fts_total >= fuzzy_fallback_min_results:
        offset = (page - 1) * page_size
        return {
            "total": fts_total,
            "results": list(fts_qs[offset : offset + page_size]),
            "search_type": "fts",
        }

    # --- 2단계: Fuzzy 폴백 ---
    fuzzy_qs = Article.objects.annotate(
        rank=Greatest(
            TrigramWordSimilarity(query, "title"),
            TrigramWordSimilarity(query, "body"),
            output_field=FloatField(),
        ),
        headline=Value("", output_field=FloatField()),  # Fuzzy에서는 하이라이트 없음
    ).filter(rank__gte=fuzzy_threshold)

    if category:
        fuzzy_qs = fuzzy_qs.filter(category=category)

    fuzzy_qs = fuzzy_qs.order_by("-rank", "-published_at")

    fuzzy_total = fuzzy_qs.count()
    offset = (page - 1) * page_size

    return {
        "total": fuzzy_total,
        "results": list(fuzzy_qs[offset : offset + page_size]),
        "search_type": "fuzzy",
    }
```

```python
# search/api.py 에 하이브리드 검색 엔드포인트 추가
@router.get("/search/smart", response=SearchResponseSchema, summary="스마트 통합 검색")
def smart_search(
    request,
    q: str,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    FTS 결과가 부족하면 자동으로 오탈자 허용 검색으로 전환.
    응답 헤더에 X-Search-Type: fts | fuzzy 를 포함합니다.
    """
    import time
    from ninja import request as ninja_request
    from .hybrid_search import hybrid_search

    start_time = time.perf_counter()

    # 검색어 정제
    import re
    cleaned_q = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]", " ", q).strip()
    if not cleaned_q:
        return SearchResponseSchema(total=0, page=page, page_size=page_size, results=[], query_time_ms=0)

    result = hybrid_search(
        query=cleaned_q,
        category=category,
        page=page,
        page_size=page_size,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    results = [
        ArticleResponseSchema(
            id=a.id,
            title=a.title,
            subtitle=a.subtitle,
            author=a.author,
            category=a.category,
            tags=a.tags,
            published_at=a.published_at,
            view_count=a.view_count,
            rank=round(getattr(a, "rank", 0.0) or 0.0, 4),
            headline=getattr(a, "headline", None),
        )
        for a in result["results"]
    ]

    return SearchResponseSchema(
        total=result["total"],
        page=page,
        page_size=page_size,
        results=results,
        query_time_ms=round(elapsed_ms, 2),
    )
```

---

## 10. 검색 성능 측정 및 쿼리 분석

구현이 끝났다면 실제로 얼마나 빠른지 측정해야 합니다. PostgreSQL의 `EXPLAIN ANALYZE`를 Django에서 활용하는 방법을 소개합니다.

### 쿼리 실행 계획 분석

```python
# search/management/commands/analyze_query.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.postgres.search import SearchQuery, SearchRank
from search.models import Article


class Command(BaseCommand):
    help = "검색 쿼리 실행 계획 분석"

    def add_arguments(self, parser):
        parser.add_argument("query", type=str, help="분석할 검색어")

    def handle(self, *args, **options):
        query_str = options["query"]
        search_query = SearchQuery(query_str, config="simple", search_type="websearch")

        qs = (
            Article.objects.filter(search_vector=search_query)
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank")
        )

        # 쿼리 SQL 확인
        self.stdout.write("=== 생성된 SQL ===")
        self.stdout.write(str(qs.query))

        # EXPLAIN ANALYZE 실행
        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {qs.query}")
            plan = cursor.fetchall()

        self.stdout.write("\n=== 실행 계획 ===")
        for row in plan:
            self.stdout.write(row[0])
```

```bash
python manage.py analyze_query "파이썬 웹 개발"
```

### 성능 벤치마크 스크립트

```python
# search/benchmarks.py
import time
import statistics
from django.contrib.postgres.search import SearchQuery, SearchRank
from .models import Article


def benchmark_fts(query: str, runs: int = 100):
    """FTS 검색 성능 측정"""
    times = []
    search_query = SearchQuery(query, config="simple", search_type="websearch")

    for _ in range(runs):
        start = time.perf_counter()
        results = list(
            Article.objects.filter(search_vector=search_query)
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank")[:20]
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return {
        "query": query,
        "runs": runs,
        "result_count": len(results),
        "avg_ms": round(statistics.mean(times), 2),
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(runs * 0.95)], 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
    }
```

### 인덱스 상태 확인 쿼리

```sql
-- 인덱스 크기와 사용 빈도 확인
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read
FROM pg_stat_user_indexes
WHERE tablename = 'search_article'
ORDER BY idx_scan DESC;
```

### 성능 최적화 체크리스트

| 항목 | 확인 방법 | 기준값 |
|---|---|---|
| GIN 인덱스 적용 여부 | EXPLAIN ANALYZE에서 "Bitmap Index Scan" 확인 | 없으면 Seq Scan 발생 |
| search_vector NULL 비율 | `SELECT COUNT(*) FROM article WHERE search_vector IS NULL` | 0건이어야 함 |
| 평균 검색 응답 시간 | SearchLog 테이블 집계 | 100ms 이하 목표 |
| 인덱스 크기 | `pg_size_pretty(pg_relation_size(...))` | 테이블 크기의 20~50% 정상 |
| dead tuple 비율 | `pg_stat_user_tables.n_dead_tup` | VACUUM 필요 여부 판단 |

---

## 11. 검색 품질 향상: 동의어 사전과 불용어 처리

기술적인 성능 외에도 **검색 품질(relevance)**을 높이는 작업이 필요합니다.

### 커스텀 사전 설정 (PostgreSQL)

```sql
-- 동의어 파일 생성: /usr/share/postgresql/16/tsearch_data/korean_syn.syn
-- 형식: 동의어1 동의어2 동의어3 (공백 구분)
-- 예:
-- 장고 Django django
-- 파이썬 Python python
-- 리액트 React react 리엑트

-- 동의어 사전 등록
CREATE TEXT SEARCH DICTIONARY korean_syn (
    TEMPLATE = synonym,
    SYNONYMS = korean_syn
);

-- 커스텀 텍스트 검색 설정 생성
CREATE TEXT SEARCH CONFIGURATION korean_simple (COPY = simple);

ALTER TEXT SEARCH CONFIGURATION korean_simple
    ALTER MAPPING FOR word WITH korean_syn, simple;
```

```python
# Django에서 커스텀 FTS 설정 활용
from django.contrib.postgres.search import SearchQuery, SearchVector

# 커스텀 설정을 사용한 검색
search_query = SearchQuery("장고", config="korean_simple")
Article.objects.filter(search_vector=search_query)
# "django"가 포함된 문서도 함께 검색됨
```

### 불용어(Stopword) 처리

검색 효율을 높이기 위해 의미 없는 단어를 색인에서 제외합니다.

```python
# search/stopwords.py
KOREAN_STOPWORDS = {
    "이", "그", "저", "것", "수", "들", "및", "를", "을", "이다",
    "있다", "하다", "되다", "않다", "없다", "같다", "보다", "또한",
    "그리고", "하지만", "그러나", "따라서", "즉", "또", "더",
    "에서", "으로", "에게", "한테", "부터", "까지", "만", "도",
}


def remove_stopwords(text: str) -> str:
    """한국어 불용어 제거"""
    tokens = text.split()
    filtered = [t for t in tokens if t not in KOREAN_STOPWORDS]
    return " ".join(filtered) if filtered else text
```

---

## 12. 완성된 프로젝트 구조와 실행 방법

지금까지 구현한 내용을 정리합니다.

```
config/
├── __init__.py
├── settings.py
├── urls.py
└── api.py

search/
├── __init__.py
├── apps.py
├── models.py
├── schemas.py
├── api.py
├── fuzzy_search.py
├── hybrid_search.py
├── signals.py
├── stopwords.py
├── utils.py
├── benchmarks.py
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_add_search_trigger.py
│   ├── 0003_add_pg_bigm.py
│   ├── 0004_add_pgroonga.py
│   └── 0005_add_pg_trgm.py
└── management/
    └── commands/
        ├── rebuild_search_index.py
        └── analyze_query.py
```

### Docker Compose로 개발 환경 구성

```yaml
# docker-compose.yml
version: "3.9"

services:
  db:
    image: groonga/pgroonga:latest-debian-16  # pgroonga 포함 이미지
    environment:
      POSTGRES_DB: searchdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: >
      postgres
        -c shared_preload_libraries=pg_bigm
        -c pg_bigm.enable_recheck=off

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DB_HOST: db
      DB_PASSWORD: password

volumes:
  postgres_data:
```

### 마이그레이션 및 초기 실행

```bash
# 컨테이너 실행
docker compose up -d

# 마이그레이션
python manage.py migrate

# 샘플 데이터 생성 (옵션)
python manage.py shell -c "
from search.models import Article
samples = [
    Article(title='파이썬 장고 웹 개발 기초', body='장고는 파이썬 기반의 고수준 웹 프레임워크입니다.', author='홍길동', category='python'),
    Article(title='Django REST API 설계', body='DRF와 Django Ninja를 비교하고 RESTful API를 구축합니다.', author='김철수', category='django'),
    Article(title='PostgreSQL 성능 최적화', body='인덱스 설계와 쿼리 튜닝으로 DB 성능을 개선합니다.', author='이영희', category='database'),
]
Article.objects.bulk_create(samples)
"

# 검색 색인 재구성
python manage.py rebuild_search_index

# 서버 실행
python manage.py runserver
```

### API 테스트

```bash
# 기본 FTS 검색
curl "http://localhost:8000/api/search/search?q=파이썬+웹+개발"

# 오탈자 허용 검색
curl "http://localhost:8000/api/search/search/fuzzy?q=쟝고&threshold=0.2"

# 스마트 통합 검색 (FTS → Fuzzy 자동 폴백)
curl "http://localhost:8000/api/search/search/smart?q=쟝고+웹+개발"

# 자동완성
curl "http://localhost:8000/api/search/autocomplete?q=파이"

# Swagger UI
open http://localhost:8000/api/docs
```

---

## 마무리: 검색 시스템 진화 로드맵

이 포스트에서 구축한 시스템은 중소 규모 서비스에 충분한 성능을 제공합니다. 서비스가 성장하면서 요구사항이 높아질 경우 다음 단계로 진화할 수 있습니다.

```
현재 구현 (PostgreSQL FTS + pg_trgm)
        │
        ▼ 일 검색 10만 건 이상
pgroonga 형태소 분석 적용
        │
        ▼ 복합 검색 조건, 집계 기능 필요
Elasticsearch / OpenSearch 도입
  (PostgreSQL과 이중 색인 운영)
        │
        ▼ 자연어 의도 파악 필요
LLM 기반 벡터 검색 (pgvector)
  + Hybrid Retrieval (키워드 + 시맨틱)
```

핵심 원칙은 단순한 것부터 시작해서 측정하고 개선하는 것입니다. PostgreSQL FTS는 별도 인프라 없이 기존 DB에서 바로 활용할 수 있는 강력한 도구입니다. 여기에 `pg_trgm`으로 오탈자 허용을 더하고, 한국어 처리가 중요하다면 `pg_bigm`이나 `pgroonga`를 추가하면 대부분의 검색 요구사항을 충족할 수 있습니다.
