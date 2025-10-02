---
layout: post
title: "Django Soft Delete 완벽 구현 가이드 - unique_together와 M2M 관계 처리"
date: 2025-10-02 10:00:00 +0900
categories: [Web Development, Backend, Django]
tags: [django, soft-delete, database, orm, unique-together, many-to-many, constraints]
description: "Django에서 Soft Delete를 구현하는 방법과 unique_together 제약조건, Many-to-Many 관계에서의 주의사항을 상세히 알아봅니다. 실무에서 마주치는 문제점과 해결 방법을 함께 다룹니다."
author: "updaun"
image: "/assets/img/posts/2025-10-02-django-soft-delete-implementation-guide.webp"
---

## 개요

Soft Delete는 데이터를 실제로 삭제하지 않고 '삭제됨' 플래그만 표시하는 방식입니다. 데이터 복구, 감사 추적, 규정 준수 등의 이유로 실무에서 자주 사용됩니다. 하지만 Django에서 Soft Delete를 구현할 때는 unique_together 제약조건과 Many-to-Many 관계에서 특별한 주의가 필요합니다.

## Soft Delete의 필요성

### 1. 데이터 복구 가능
- **실수 방지**: 사용자의 실수로 삭제한 데이터 복구
- **비즈니스 요구사항**: 30일 이내 삭제 취소 기능
- **법적 요구사항**: 개인정보 삭제 후 일정 기간 보관

### 2. 감사 추적 (Audit Trail)
- **변경 이력**: 누가, 언제 삭제했는지 기록
- **규정 준수**: GDPR, 금융 규제 등 준수
- **비즈니스 분석**: 삭제된 데이터 패턴 분석

### 3. 참조 무결성 유지
- **외래키 관계**: 삭제된 데이터를 참조하는 다른 레코드 보호
- **데이터 일관성**: 관련 데이터 간 관계 유지
- **성능**: CASCADE 삭제로 인한 대량 삭제 방지

## 기본 Soft Delete 구현

### 1. Base Model 생성

```python
# core/models.py
from django.db import models
from django.utils import timezone
from django.db.models import Q, QuerySet
from typing import Optional

class SoftDeleteQuerySet(QuerySet):
    """Soft Delete를 지원하는 커스텀 QuerySet"""
    
    def delete(self):
        """벌크 삭제 시에도 Soft Delete 적용"""
        return self.update(
            deleted_at=timezone.now(),
            is_deleted=True
        )
    
    def hard_delete(self):
        """실제 데이터베이스에서 삭제"""
        return super().delete()
    
    def alive(self):
        """삭제되지 않은 레코드만 조회"""
        return self.filter(is_deleted=False)
    
    def dead(self):
        """삭제된 레코드만 조회"""
        return self.filter(is_deleted=True)
    
    def with_deleted(self):
        """삭제된 레코드 포함 전체 조회"""
        return self


class SoftDeleteManager(models.Manager):
    """Soft Delete를 지원하는 커스텀 Manager"""
    
    def get_queryset(self):
        """기본적으로 삭제되지 않은 레코드만 반환"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            is_deleted=False
        )
    
    def all_with_deleted(self):
        """삭제된 레코드 포함 전체 조회"""
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """삭제된 레코드만 조회"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            is_deleted=True
        )


class SoftDeleteModel(models.Model):
    """Soft Delete를 지원하는 Base Model"""
    
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='삭제 여부'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='삭제 시각'
    )
    
    # 기본 매니저 (삭제되지 않은 레코드만)
    objects = SoftDeleteManager()
    
    # 전체 레코드 접근용 매니저
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """Soft Delete 수행"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)
    
    def hard_delete(self, using=None, keep_parents=False):
        """실제 삭제"""
        return super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """삭제 취소"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class TimeStampedModel(models.Model):
    """생성/수정 시각 추적 모델"""
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시각')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시각')
    
    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """타임스탬프와 Soft Delete를 모두 지원하는 Base Model"""
    
    class Meta:
        abstract = True
```

### 2. 기본 사용 예제

```python
# blog/models.py
from django.db import models
from django.contrib.auth.models import User
from core.models import BaseModel

class Category(BaseModel):
    """카테고리 모델"""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Post(BaseModel):
    """게시글 모델 (기본 사용)"""
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    published = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = '게시글'
        verbose_name_plural = '게시글'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


# 사용 예제
def basic_usage_example():
    # 1. 생성
    post = Post.objects.create(
        title='테스트 게시글',
        slug='test-post',
        author=user,
        content='내용'
    )
    
    # 2. 조회 (삭제되지 않은 것만)
    posts = Post.objects.all()  # is_deleted=False인 것만
    
    # 3. Soft Delete
    post.delete()  # DB에서 삭제되지 않고 is_deleted=True로 표시
    
    # 4. 삭제된 것 포함 조회
    all_posts = Post.objects.all_with_deleted()
    
    # 5. 삭제된 것만 조회
    deleted_posts = Post.objects.deleted_only()
    
    # 6. 복구
    post.restore()
    
    # 7. 실제 삭제
    post.hard_delete()  # 실제로 DB에서 삭제
```

## unique_together와 Soft Delete

### 1. 문제점

Soft Delete를 사용할 때 `unique_together`나 `unique` 제약조건과 충돌이 발생합니다.

```python
# ❌ 문제가 있는 코드
class Article(BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    
    class Meta:
        unique_together = [('slug',)]  # 또는 ['slug']

# 문제 시나리오:
# 1. slug='hello-world'인 Article 생성
# 2. 해당 Article을 soft delete
# 3. 다시 slug='hello-world'인 Article 생성 시도
# ❌ IntegrityError 발생! (slug가 이미 존재함)
```

**왜 문제가 될까?**
- Soft Delete는 데이터를 삭제하지 않고 `is_deleted=True`로 표시만 함
- 데이터베이스에는 여전히 `slug='hello-world'`인 레코드가 존재
- 새로운 레코드 생성 시 unique 제약조건 위반

### 2. 해결 방법 1: UniqueConstraint 사용 (Django 2.2+)

```python
# ✅ 올바른 구현
from django.db import models
from django.db.models import Q, UniqueConstraint
from core.models import BaseModel

class Article(BaseModel):
    """unique_together를 올바르게 구현한 모델"""
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = '기사'
        verbose_name_plural = '기사'
        
        # ✅ 삭제되지 않은 레코드에 대해서만 unique 제약조건 적용
        constraints = [
            UniqueConstraint(
                fields=['slug'],
                condition=Q(is_deleted=False),
                name='unique_article_slug_when_not_deleted'
            )
        ]

# 이제 정상 작동:
# 1. slug='hello-world'인 Article 생성 ✅
# 2. 해당 Article을 soft delete ✅
# 3. 다시 slug='hello-world'인 Article 생성 ✅ (이전 것은 is_deleted=True)
```

### 3. 해결 방법 2: 복합 제약조건

```python
class Product(BaseModel):
    """여러 필드의 조합에 대한 unique 제약조건"""
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50)  # Stock Keeping Unit
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            # SKU는 카테고리 내에서 유일해야 함 (삭제되지 않은 것만)
            UniqueConstraint(
                fields=['sku', 'category'],
                condition=Q(is_deleted=False),
                name='unique_sku_per_category'
            ),
            
            # 판매자는 같은 카테고리에서 같은 이름의 상품을 가질 수 없음
            UniqueConstraint(
                fields=['name', 'category', 'seller'],
                condition=Q(is_deleted=False),
                name='unique_product_name_per_seller_category'
            )
        ]
```

### 4. 해결 방법 3: 삭제 시 고유값 변경

```python
class UserProfile(BaseModel):
    """삭제 시 고유값을 변경하는 방식"""
    
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    def delete(self, using=None, keep_parents=False):
        """삭제 시 고유 필드에 타임스탬프 추가"""
        import uuid
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_suffix = str(uuid.uuid4())[:8]
        
        # 고유 필드 변경
        self.username = f"{self.username}_deleted_{timestamp}_{unique_suffix}"
        self.email = f"{self.email}_deleted_{timestamp}_{unique_suffix}"
        if self.phone:
            self.phone = f"{self.phone}_deleted_{timestamp}"
        
        # Soft Delete 수행
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

# 장점: 구 버전 Django에서도 작동
# 단점: 삭제된 데이터의 원본 값을 알기 어려움
```

### 5. 실무 패턴: 이메일 중복 방지

```python
class User(BaseModel):
    """실무에서 자주 사용하는 패턴"""
    
    email = models.EmailField()
    username = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            # 활성 사용자 중에서 이메일은 유일해야 함
            UniqueConstraint(
                fields=['email'],
                condition=Q(is_deleted=False),
                name='unique_email_when_active'
            ),
            
            # 활성 사용자 중에서 사용자명은 유일해야 함
            UniqueConstraint(
                fields=['username'],
                condition=Q(is_deleted=False),
                name='unique_username_when_active'
            )
        ]
    
    def __str__(self):
        return f"{self.email} ({'Active' if self.is_active else 'Inactive'})"


# 사용 예제
def user_lifecycle_example():
    # 1. 사용자 생성
    user = User.objects.create(
        email='user@example.com',
        username='johndoe',
        full_name='John Doe'
    )
    
    # 2. 사용자 탈퇴 (Soft Delete)
    user.delete()
    
    # 3. 같은 이메일로 다시 가입 가능
    new_user = User.objects.create(
        email='user@example.com',  # ✅ 이전 사용자는 is_deleted=True
        username='johndoe2',
        full_name='John Doe'
    )
    
    # 4. 이전 사용자 복구 시도
    # user.restore()  # ❌ 이메일 중복으로 실패
    
    # 5. 새 사용자를 삭제해야 복구 가능
    new_user.delete()
    user.restore()  # ✅ 성공
```

## Many-to-Many 관계와 Soft Delete

### 1. M2M에서 Soft Delete를 피해야 하는 이유

```python
# ❌ 권장하지 않는 패턴
class Tag(BaseModel):  # Soft Delete 적용
    """태그 모델"""
    name = models.CharField(max_length=50)

class Post(BaseModel):  # Soft Delete 적용
    """게시글 모델"""
    title = models.CharField(max_length=200)
    tags = models.ManyToManyField(Tag)  # M2M 관계

# 문제점:
# 1. 성능 문제: 매번 중간 테이블을 조인해야 함
# 2. 복잡성: Tag가 삭제되면 Post와의 관계를 어떻게 처리할까?
# 3. 데이터 무결성: 삭제된 Tag를 참조하는 Post는?
# 4. 쿼리 복잡도: 삭제되지 않은 Tag만 필터링해야 함
```

**주요 문제점:**

1. **성능 저하**
   ```python
   # 삭제되지 않은 태그만 가져오기 위해 복잡한 쿼리 필요
   post.tags.filter(is_deleted=False)  # 매번 필터링 필요
   ```

2. **관계 복잡성**
   ```python
   # Tag가 soft delete되면 Post와의 관계는?
   tag.delete()  # 중간 테이블 레코드는 그대로 유지됨
   # Post에서 tag를 조회하면 삭제된 tag가 나옴
   ```

3. **데이터 정합성**
   ```python
   # 새로운 Tag를 같은 이름으로 생성하면?
   old_tag = Tag.objects.create(name='Python')
   old_tag.delete()  # soft delete
   new_tag = Tag.objects.create(name='Python')  # unique 제약조건 위반!
   ```

### 2. 올바른 구현 방법

#### 방법 1: M2M 중간 테이블만 Soft Delete

```python
class Tag(models.Model):
    """태그는 Hard Delete (Soft Delete 적용 안 함)"""
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Post(BaseModel):
    """게시글은 Soft Delete 적용"""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    # M2M 관계를 명시적으로 정의하지 않음
    
    def __str__(self):
        return self.title


class PostTag(BaseModel):
    """중간 테이블에만 Soft Delete 적용"""
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    
    # 추가 메타데이터
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order = models.PositiveIntegerField(default=0)  # 태그 순서
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['post', 'tag'],
                condition=Q(is_deleted=False),
                name='unique_post_tag_when_active'
            )
        ]
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.post.title} - {self.tag.name}"


# 사용 예제
def m2m_usage_example():
    post = Post.objects.create(title='Django 튜토리얼', content='...')
    python_tag = Tag.objects.get_or_create(name='Python', slug='python')[0]
    django_tag = Tag.objects.get_or_create(name='Django', slug='django')[0]
    
    # 태그 추가
    PostTag.objects.create(post=post, tag=python_tag, order=1)
    PostTag.objects.create(post=post, tag=django_tag, order=2)
    
    # 게시글의 활성 태그 조회
    active_tags = Tag.objects.filter(
        posttag__post=post,
        posttag__is_deleted=False
    ).distinct()
    
    # 태그 제거 (Soft Delete)
    post_tag = PostTag.objects.get(post=post, tag=python_tag)
    post_tag.delete()  # soft delete
    
    # 태그 복구
    post_tag.restore()
```

#### 방법 2: 커스텀 Manager로 추상화

```python
class PostTagManager(models.Manager):
    """PostTag 관계를 쉽게 다루는 Manager"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def for_post(self, post):
        """특정 게시글의 활성 태그들"""
        return self.filter(post=post).select_related('tag')
    
    def add_tag(self, post, tag, **kwargs):
        """태그 추가 (이미 있으면 복구)"""
        post_tag, created = PostTag.all_objects.get_or_create(
            post=post,
            tag=tag,
            defaults=kwargs
        )
        
        if not created and post_tag.is_deleted:
            # 삭제된 관계를 복구
            post_tag.restore()
        
        return post_tag
    
    def remove_tag(self, post, tag):
        """태그 제거 (Soft Delete)"""
        try:
            post_tag = self.get(post=post, tag=tag)
            post_tag.delete()
            return True
        except PostTag.DoesNotExist:
            return False


class PostTag(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    
    objects = PostTagManager()
    all_objects = models.Manager()
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['post', 'tag'],
                condition=Q(is_deleted=False),
                name='unique_post_tag_active'
            )
        ]


# 편리한 사용
def convenient_m2m_usage():
    post = Post.objects.get(id=1)
    python_tag = Tag.objects.get(name='Python')
    
    # 태그 추가
    PostTag.objects.add_tag(post, python_tag)
    
    # 게시글의 태그 조회
    tags = Tag.objects.filter(
        posttag__in=PostTag.objects.for_post(post)
    )
    
    # 태그 제거
    PostTag.objects.remove_tag(post, python_tag)
```

#### 방법 3: Post 모델에 헬퍼 메서드 추가

```python
class Post(BaseModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    def get_tags(self):
        """활성 태그 목록"""
        return Tag.objects.filter(
            posttag__post=self,
            posttag__is_deleted=False
        ).distinct()
    
    def add_tag(self, tag, **kwargs):
        """태그 추가"""
        return PostTag.objects.add_tag(self, tag, **kwargs)
    
    def remove_tag(self, tag):
        """태그 제거"""
        return PostTag.objects.remove_tag(self, tag)
    
    def has_tag(self, tag):
        """태그 보유 여부"""
        return PostTag.objects.filter(
            post=self,
            tag=tag,
            is_deleted=False
        ).exists()
    
    def set_tags(self, tags):
        """태그 일괄 설정"""
        # 기존 태그 모두 제거
        PostTag.objects.filter(post=self).delete()
        
        # 새 태그 추가
        for order, tag in enumerate(tags, start=1):
            self.add_tag(tag, order=order)


# 직관적인 사용
def intuitive_usage():
    post = Post.objects.get(id=1)
    
    # 태그 추가
    post.add_tag(Tag.objects.get(name='Python'))
    
    # 태그 확인
    if post.has_tag(django_tag):
        print("Django 태그가 있습니다")
    
    # 태그 목록
    for tag in post.get_tags():
        print(tag.name)
    
    # 태그 일괄 설정
    post.set_tags([python_tag, django_tag, web_tag])
```

### 3. M2M에서 완전히 피해야 할 패턴

```python
# ❌ 절대 하지 말 것!
class BadExample1(BaseModel):
    name = models.CharField(max_length=100)
    # M2M 관계에서 through 모델에 Soft Delete
    related = models.ManyToManyField('self', through='BadThrough')

class BadThrough(BaseModel):  # ❌ 문제 발생
    from_obj = models.ForeignKey(BadExample1, on_delete=models.CASCADE, related_name='+')
    to_obj = models.ForeignKey(BadExample1, on_delete=models.CASCADE, related_name='+')
    
# 문제: Django의 M2M 관리자가 is_deleted 필드를 인식하지 못함


# ❌ Soft Delete된 객체를 M2M으로 연결
class BadExample2(BaseModel):  # Soft Delete 적용
    name = models.CharField(max_length=100)

class BadExample3(models.Model):
    name = models.CharField(max_length=100)
    bad_relations = models.ManyToManyField(BadExample2)  # ❌ 위험!

# 문제: BadExample2가 삭제되어도 관계는 남아있음
# BadExample3.bad_relations.all()을 하면 삭제된 객체도 포함됨
```

## 고급 패턴 및 베스트 프랙티스

### 1. 삭제된 데이터 자동 정리

```python
# core/management/commands/cleanup_soft_deleted.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from datetime import timedelta

class Command(BaseCommand):
    help = 'Soft Delete된 데이터를 영구 삭제합니다'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='N일 이전에 삭제된 데이터 정리 (기본: 90일)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제하지 않고 시뮬레이션만 수행'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"🗑️  {days}일 이전 삭제 데이터 정리 시작...")
        self.stdout.write(f"   기준 날짜: {cutoff_date}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN 모드 (실제 삭제 안 함)"))
        
        total_deleted = 0
        
        # Soft Delete를 사용하는 모든 모델 찾기
        for model in apps.get_models():
            if hasattr(model, 'is_deleted') and hasattr(model, 'deleted_at'):
                # 오래된 삭제 데이터 조회
                old_deleted = model.all_objects.filter(
                    is_deleted=True,
                    deleted_at__lt=cutoff_date
                )
                
                count = old_deleted.count()
                if count > 0:
                    self.stdout.write(
                        f"   📦 {model._meta.label}: {count}개 발견"
                    )
                    
                    if not dry_run:
                        # 실제 삭제
                        deleted = old_deleted._raw_delete(old_deleted.db)
                        total_deleted += deleted
                        self.stdout.write(
                            self.style.SUCCESS(f"   ✅ {deleted}개 영구 삭제됨")
                        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n💡 DRY RUN 완료: {total_deleted}개가 삭제될 예정")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✨ 완료: 총 {total_deleted}개 영구 삭제됨")
            )

# 사용 예제:
# python manage.py cleanup_soft_deleted --days=90
# python manage.py cleanup_soft_deleted --days=30 --dry-run
```

### 2. Admin에서 삭제된 객체 관리

```python
# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

class SoftDeleteAdmin(admin.ModelAdmin):
    """Soft Delete를 지원하는 Admin 클래스"""
    
    list_display = ['__str__', 'is_deleted_display', 'deleted_at']
    list_filter = ['is_deleted', 'deleted_at']
    actions = ['soft_delete_selected', 'restore_selected', 'hard_delete_selected']
    
    def get_queryset(self, request):
        """삭제된 것 포함 전체 표시"""
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs
    
    def is_deleted_display(self, obj):
        """삭제 상태 표시"""
        if obj.is_deleted:
            return format_html(
                '<span style="color: red;">🗑️ 삭제됨</span>'
            )
        return format_html(
            '<span style="color: green;">✅ 활성</span>'
        )
    is_deleted_display.short_description = '상태'
    
    def soft_delete_selected(self, request, queryset):
        """선택한 항목 Soft Delete"""
        count = 0
        for obj in queryset:
            if not obj.is_deleted:
                obj.delete()
                count += 1
        
        self.message_user(
            request,
            f'{count}개 항목이 삭제되었습니다 (복구 가능).'
        )
    soft_delete_selected.short_description = '선택한 항목 삭제 (복구 가능)'
    
    def restore_selected(self, request, queryset):
        """선택한 항목 복구"""
        count = 0
        for obj in queryset.filter(is_deleted=True):
            obj.restore()
            count += 1
        
        self.message_user(
            request,
            f'{count}개 항목이 복구되었습니다.'
        )
    restore_selected.short_description = '선택한 항목 복구'
    
    def hard_delete_selected(self, request, queryset):
        """선택한 항목 영구 삭제"""
        count = queryset.count()
        queryset._raw_delete(queryset.db)
        
        self.message_user(
            request,
            f'{count}개 항목이 영구 삭제되었습니다 (복구 불가능).',
            level='WARNING'
        )
    hard_delete_selected.short_description = '선택한 항목 영구 삭제 (주의!)'


# blog/admin.py
from core.admin import SoftDeleteAdmin
from .models import Post, Category

@admin.register(Post)
class PostAdmin(SoftDeleteAdmin):
    list_display = ['title', 'author', 'category', 'published', 'is_deleted_display', 'created_at']
    list_filter = ['is_deleted', 'published', 'category', 'created_at']
    search_fields = ['title', 'content']

@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ['name', 'slug', 'is_deleted_display', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
```

### 3. 성능 최적화

```python
# core/models.py 추가
class OptimizedSoftDeleteQuerySet(SoftDeleteQuerySet):
    """성능 최적화된 QuerySet"""
    
    def alive(self):
        """인덱스를 효율적으로 사용"""
        # is_deleted 필드에 인덱스가 있으므로 빠름
        return self.filter(is_deleted=False)
    
    def recent_deleted(self, days=30):
        """최근 N일 이내 삭제된 것만"""
        cutoff = timezone.now() - timedelta(days=days)
        return self.filter(
            is_deleted=True,
            deleted_at__gte=cutoff
        )
    
    def bulk_restore(self):
        """대량 복구 (성능 최적화)"""
        return self.update(
            is_deleted=False,
            deleted_at=None
        )


class OptimizedSoftDeleteModel(models.Model):
    """성능 최적화된 Soft Delete 모델"""
    
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,  # ⚠️ 인덱스 필수!
        verbose_name='삭제 여부'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,  # ⚠️ 인덱스 필수!
        verbose_name='삭제 시각'
    )
    
    objects = SoftDeleteManager.from_queryset(OptimizedSoftDeleteQuerySet)()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
        # 복합 인덱스로 쿼리 성능 향상
        indexes = [
            models.Index(fields=['is_deleted', '-deleted_at']),
        ]
```

### 4. 외래키 관계에서의 주의사항

```python
class Author(BaseModel):
    """작가 모델"""
    name = models.CharField(max_length=100)
    email = models.EmailField()


class Book(BaseModel):
    """책 모델"""
    title = models.CharField(max_length=200)
    
    # ⚠️ 주의: on_delete 옵션
    # CASCADE: 작가 삭제 시 책도 삭제 (Soft Delete면 책도 Soft Delete)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,  # 기본값
        related_name='books'
    )
    
    # 또는 SET_NULL: 작가 삭제 시 null로 설정
    # author = models.ForeignKey(
    #     Author,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     related_name='books'
    # )


# 문제 시나리오
def foreign_key_issue_example():
    author = Author.objects.create(name='John Doe', email='john@example.com')
    book = Book.objects.create(title='Django Guide', author=author)
    
    # 작가를 Soft Delete
    author.delete()
    
    # ❌ 문제: 책도 자동으로 Soft Delete됨!
    # book.refresh_from_db()
    # assert book.is_deleted == True  # CASCADE 동작
    
    # 책 조회 시 작가가 삭제되었는지 확인 필요
    books = Book.objects.select_related('author').filter(
        author__is_deleted=False  # 활성 작가의 책만
    )


# ✅ 해결책: 커스텀 Manager
class BookManager(SoftDeleteManager):
    def with_active_author(self):
        """활성 작가의 책만 조회"""
        return self.get_queryset().filter(
            author__is_deleted=False
        )

class Book(BaseModel):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    
    objects = BookManager()
    
    @property
    def author_is_active(self):
        """작가가 활성 상태인지"""
        return self.author and not self.author.is_deleted
```

## 테스트 작성

### 1. 기본 Soft Delete 테스트

```python
# tests/test_soft_delete.py
from django.test import TestCase
from django.contrib.auth.models import User
from blog.models import Post, Category

class SoftDeleteTest(TestCase):
    """Soft Delete 기능 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.category = Category.objects.create(
            name='Tech',
            slug='tech'
        )
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            category=self.category,
            content='Test content'
        )
    
    def test_soft_delete(self):
        """Soft Delete가 정상 작동하는지 테스트"""
        # 삭제 전
        self.assertFalse(self.post.is_deleted)
        self.assertIsNone(self.post.deleted_at)
        
        # Soft Delete 수행
        self.post.delete()
        
        # 삭제 후
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)
        self.assertIsNotNone(self.post.deleted_at)
        
        # 기본 쿼리에서 제외됨
        self.assertEqual(Post.objects.count(), 0)
        
        # all_objects로는 조회 가능
        self.assertEqual(Post.all_objects.count(), 1)
    
    def test_restore(self):
        """복구 기능 테스트"""
        # 삭제
        self.post.delete()
        self.assertEqual(Post.objects.count(), 0)
        
        # 복구
        self.post.restore()
        self.assertEqual(Post.objects.count(), 1)
        self.assertFalse(self.post.is_deleted)
        self.assertIsNone(self.post.deleted_at)
    
    def test_hard_delete(self):
        """영구 삭제 테스트"""
        post_id = self.post.id
        
        # 영구 삭제
        self.post.hard_delete()
        
        # 완전히 삭제됨
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(Post.all_objects.count(), 0)
        
        # 조회 시 DoesNotExist 발생
        with self.assertRaises(Post.DoesNotExist):
            Post.all_objects.get(id=post_id)
    
    def test_bulk_delete(self):
        """벌크 삭제 테스트"""
        # 추가 게시글 생성
        Post.objects.create(
            title='Post 2',
            slug='post-2',
            author=self.user,
            category=self.category,
            content='Content 2'
        )
        Post.objects.create(
            title='Post 3',
            slug='post-3',
            author=self.user,
            category=self.category,
            content='Content 3'
        )
        
        # 벌크 Soft Delete
        Post.objects.all().delete()
        
        # 모두 삭제됨
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(Post.all_objects.count(), 3)
        
        # 모두 is_deleted=True
        for post in Post.all_objects.all():
            self.assertTrue(post.is_deleted)


class UniqueConstraintTest(TestCase):
    """unique_together와 Soft Delete 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_unique_slug_with_soft_delete(self):
        """같은 slug를 가진 Article을 삭제 후 다시 생성할 수 있는지 테스트"""
        from blog.models import Article
        
        # 첫 번째 Article 생성
        article1 = Article.objects.create(
            title='First Article',
            slug='test-slug',
            author=self.user
        )
        
        # 같은 slug로 생성 시도 (실패해야 함)
        with self.assertRaises(Exception):  # IntegrityError
            Article.objects.create(
                title='Second Article',
                slug='test-slug',
                author=self.user
            )
        
        # 첫 번째 Article Soft Delete
        article1.delete()
        
        # 이제 같은 slug로 생성 가능
        article2 = Article.objects.create(
            title='Second Article',
            slug='test-slug',
            author=self.user
        )
        
        self.assertEqual(article2.slug, 'test-slug')
        self.assertFalse(article2.is_deleted)


class ManyToManyTest(TestCase):
    """M2M 관계에서 Soft Delete 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Content'
        )
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django', slug='django')
    
    def test_post_tag_relationship(self):
        """PostTag 관계 테스트"""
        # 태그 추가
        pt1 = PostTag.objects.create(post=self.post, tag=self.tag1, order=1)
        pt2 = PostTag.objects.create(post=self.post, tag=self.tag2, order=2)
        
        # 활성 태그 2개
        self.assertEqual(self.post.get_tags().count(), 2)
        
        # 태그 하나 제거 (Soft Delete)
        pt1.delete()
        
        # 활성 태그 1개
        self.assertEqual(self.post.get_tags().count(), 1)
        
        # 전체 관계는 2개 (삭제된 것 포함)
        self.assertEqual(
            PostTag.all_objects.filter(post=self.post).count(),
            2
        )
        
        # 복구
        pt1.restore()
        self.assertEqual(self.post.get_tags().count(), 2)
```

## 마이그레이션 주의사항

### 1. 기존 모델에 Soft Delete 추가

```python
# migrations/0002_add_soft_delete.py
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    
    dependencies = [
        ('blog', '0001_initial'),
    ]
    
    operations = [
        # 1. is_deleted 필드 추가
        migrations.AddField(
            model_name='post',
            name='is_deleted',
            field=models.BooleanField(default=False, db_index=True),
        ),
        
        # 2. deleted_at 필드 추가
        migrations.AddField(
            model_name='post',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        
        # 3. 복합 인덱스 추가
        migrations.AddIndex(
            model_name='post',
            index=models.Index(
                fields=['is_deleted', '-deleted_at'],
                name='post_soft_delete_idx'
            ),
        ),
    ]
```

### 2. unique_together 마이그레이션

```python
# migrations/0003_update_unique_constraints.py
from django.db import migrations, models
from django.db.models import Q

class Migration(migrations.Migration):
    
    dependencies = [
        ('blog', '0002_add_soft_delete'),
    ]
    
    operations = [
        # 1. 기존 unique_together 제거
        migrations.AlterUniqueTogether(
            name='article',
            unique_together=set(),  # 제거
        ),
        
        # 2. UniqueConstraint 추가
        migrations.AddConstraint(
            model_name='article',
            constraint=models.UniqueConstraint(
                fields=['slug'],
                condition=Q(is_deleted=False),
                name='unique_article_slug_when_not_deleted'
            ),
        ),
    ]
```

## 실무 체크리스트

### ✅ Soft Delete 구현 시 확인사항

1. **모델 설계**
   - [ ] BaseModel에 is_deleted, deleted_at 필드 추가
   - [ ] 적절한 인덱스 설정 (성능)
   - [ ] 커스텀 Manager 및 QuerySet 구현

2. **unique 제약조건**
   - [ ] unique=True 대신 UniqueConstraint 사용
   - [ ] condition=Q(is_deleted=False) 추가
   - [ ] 기존 unique_together 마이그레이션

3. **M2M 관계**
   - [ ] M2M을 직접 사용하지 않고 중간 모델 사용
   - [ ] 중간 모델에만 Soft Delete 적용
   - [ ] Tag 등 참조 모델은 Hard Delete

4. **외래키 관계**
   - [ ] on_delete 동작 확인
   - [ ] 연쇄 삭제 동작 테스트
   - [ ] 삭제된 객체 참조 처리

5. **관리 및 정리**
   - [ ] Admin에서 삭제/복구 기능 구현
   - [ ] 오래된 데이터 자동 정리 스크립트
   - [ ] 모니터링 및 로깅

6. **테스트**
   - [ ] Soft Delete 동작 테스트
   - [ ] 복구 기능 테스트
   - [ ] unique 제약조건 테스트
   - [ ] M2M 관계 테스트
   - [ ] 성능 테스트

## 결론

### 📌 핵심 정리

1. **Soft Delete의 장점**
   - 데이터 복구 가능
   - 감사 추적 및 규정 준수
   - 참조 무결성 유지

2. **unique_together 주의사항**
   - `UniqueConstraint`와 `Q(is_deleted=False)` 조합 사용
   - Django 2.2 이상 필수
   - 마이그레이션 시 기존 제약조건 제거 후 재생성

3. **M2M 관계 주의사항**
   - M2M 엔티티 자체는 Soft Delete 피하기
   - 중간 테이블에만 Soft Delete 적용
   - 명시적인 through 모델 사용

4. **성능 고려사항**
   - is_deleted, deleted_at 필드에 인덱스 필수
   - 복합 인덱스로 쿼리 최적화
   - 정기적인 데이터 정리

5. **실무 권장사항**
   - 모든 모델에 무분별하게 적용하지 말 것
   - 비즈니스 요구사항에 따라 선택적 적용
   - 테스트 코드 필수 작성
   - 문서화 및 팀 공유

Soft Delete는 강력한 기능이지만 올바르게 구현하지 않으면 데이터 정합성 문제를 일으킬 수 있습니다. 이 가이드의 패턴과 주의사항을 따라 안전하고 효율적인 Soft Delete 시스템을 구축하시기 바랍니다.
