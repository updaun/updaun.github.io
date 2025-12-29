---
layout: post
title: "Django-Ninja로 구축하는 모바일 청첩장 서비스 - 데이터 구조 설계"
categories: [Django, Backend]
tags: [django-ninja, wedding-invitation, data-structure, multi-tenancy, template-system, postgresql, jsonfield]
date: 2025-11-27 09:00:00 +0900
image: "/assets/img/posts/2025-11-27-django-ninja-mobile-wedding-invitation-data-structure.webp"
---

## 1. 서비스 개요 및 요구사항

### 1.1 모바일 청첩장 서비스란?

모바일 청첩장 서비스는 사용자가 종이 청첩장 없이 웹 기반으로 결혼식 초대장을 제작하고 공유할 수 있는 플랫폼입니다. 최근 COVID-19 이후 비대면 문화가 확산되면서 폭발적으로 성장한 시장으로, 카카오톡, 문자 등으로 손쉽게 공유할 수 있어 MZ세대에게 인기가 높습니다.

**주요 서비스 예시:**
- 청첩장: 카카오 메이크, 웨딩북, 웨드빌
- 비슷한 서비스: 링크드인(프로필 생성), Linktree(링크 모음)
- 핵심: **템플릿 기반 + 개인화 커스터마이징**

### 1.2 핵심 기능 요구사항

```python
# 기능적 요구사항
FUNCTIONAL_REQUIREMENTS = {
    # 1. 사용자 관리
    "user_management": [
        "회원가입/로그인 (소셜 로그인 포함)",
        "사용자별 여러 청첩장 생성 가능",
        "프리미엄/무료 요금제 구분"
    ],
    
    # 2. 템플릿 시스템
    "template_system": [
        "다양한 디자인 템플릿 제공",
        "템플릿 카테고리별 분류 (모던, 클래식, 미니멀 등)",
        "무료/유료 템플릿 구분",
        "미리보기 기능"
    ],
    
    # 3. 커스터마이징
    "customization": [
        "신랑/신부 정보 입력",
        "날짜, 시간, 장소 정보",
        "사진 업로드 (메인, 갤러리)",
        "색상, 폰트 변경",
        "배경 음악 설정",
        "지도 및 교통 정보",
        "방명록 기능",
        "축의금 계좌번호"
    ],
    
    # 4. 배포 및 공유
    "deployment": [
        "고유 URL 생성 (예: domain.com/wedding/abc123)",
        "QR 코드 생성",
        "카카오톡, 문자 공유",
        "통계 (조회수, 방문자 수)"
    ],
    
    # 5. 관리
    "management": [
        "청첩장 수정/삭제",
        "참석 여부 관리",
        "방명록 관리",
        "비공개 설정"
    ]
}

# 비기능적 요구사항
NON_FUNCTIONAL_REQUIREMENTS = {
    "performance": "1초 이내 페이지 로딩",
    "scalability": "월 10만 청첩장 처리 가능",
    "availability": "99.9% 가동률 (결혼식 당일 중요!)",
    "security": "개인정보 보호, HTTPS 필수",
    "mobile_first": "모바일 최적화 UI/UX",
    "seo": "검색엔진 노출 (오픈그래프 태그)"
}
```

### 1.3 데이터 구조 설계의 핵심 과제

모바일 청첩장 서비스의 데이터 구조를 설계할 때 가장 중요한 고려사항:

**1. 템플릿과 인스턴스 분리**
- **템플릿**: 재사용 가능한 디자인/레이아웃 (1개 템플릿 → 수천 명이 사용)
- **인스턴스**: 사용자가 만든 실제 청첩장 (개인화된 데이터)
- 문제: 템플릿이 업데이트되면 기존 청첩장은?

**2. 유연한 커스터마이징**
- 템플릿마다 다른 설정 항목 (어떤 템플릿은 동영상 지원, 어떤 템플릿은 불가)
- 사용자별 다양한 요구사항 (일부는 신랑/신부 정보만, 일부는 갤러리 50장)
- 해결책: JSON Field vs 정규화된 테이블?

**3. 멀티테넌시 URL 구조**
- 각 청첩장은 고유 URL (예: `/wedding/john-mary-2025`)
- Slug 충돌 방지 (같은 이름 여러 명)
- SEO 친화적 URL

**4. 미디어 파일 관리**
- 사진 수십 장 업로드 (용량 제한, CDN 필요)
- 썸네일 자동 생성
- 임베디드 동영상 (YouTube, Vimeo)

**5. 실시간 데이터**
- 방명록 실시간 업데이트
- 참석 여부 집계
- 조회수 카운팅

이러한 요구사항을 만족하는 최적의 데이터베이스 스키마를 설계해보겠습니다.

---

## 2. 핵심 엔티티 설계

### 2.1 ERD (Entity Relationship Diagram)

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│    User     │1      * │  Invitation      │*      1 │    Template     │
│─────────────│─────────│──────────────────│─────────│─────────────────│
│ id          │         │ id               │         │ id              │
│ email       │         │ user_id (FK)     │         │ name            │
│ username    │         │ template_id (FK) │         │ category        │
│ is_premium  │         │ slug (unique)    │         │ preview_url     │
│ created_at  │         │ status           │         │ is_premium      │
└─────────────┘         │ settings (JSON)  │         │ schema (JSON)   │
                        │ published_at     │         │ version         │
                        └──────────────────┘         └─────────────────┘
                                │                             
                                │1                            
                                │                             
                        ┌───────┴────────┬──────────────────┬────────────────┐
                        │*               │*                 │*               │*
                ┌───────┴──────┐ ┌──────┴─────┐ ┌──────────┴─────┐ ┌───────┴────────┐
                │ GuestBook    │ │   Photo    │ │   Attendance   │ │   Analytics    │
                │──────────────│ │────────────│ │────────────────│ │────────────────│
                │ id           │ │ id         │ │ id             │ │ id             │
                │ invitation_id│ │ invitation │ │ invitation_id  │ │ invitation_id  │
                │ author_name  │ │ image_url  │ │ guest_name     │ │ visit_date     │
                │ message      │ │ order      │ │ will_attend    │ │ user_agent     │
                │ created_at   │ │ is_main    │ │ guest_count    │ │ referrer       │
                └──────────────┘ └────────────┘ └────────────────┘ └────────────────┘
```

### 2.2 User 모델

```python
# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    사용자 모델
    
    Django 기본 AbstractUser 확장
    """
    
    # 추가 필드
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="전화번호 (알림용)"
    )
    
    # 소셜 로그인
    social_provider = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('kakao', '카카오'),
            ('naver', '네이버'),
            ('google', '구글'),
        ]
    )
    social_id = models.CharField(max_length=100, blank=True, unique=True)
    
    # 구독 정보
    is_premium = models.BooleanField(
        default=False,
        help_text="프리미엄 회원 여부"
    )
    premium_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="프리미엄 만료일"
    )
    
    # 통계
    invitation_count = models.IntegerField(
        default=0,
        help_text="생성한 청첩장 수"
    )
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['social_provider', 'social_id']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def is_premium_active(self):
        """현재 프리미엄 활성 상태"""
        from django.utils import timezone
        return self.is_premium and (
            self.premium_until is None or 
            self.premium_until > timezone.now()
        )
```

### 2.3 Template 모델

```python
# invitations/models.py
from django.db import models
from django.core.validators import MinValueValidator

class Template(models.Model):
    """
    청첩장 템플릿
    
    재사용 가능한 디자인/레이아웃 정의
    """
    
    # 기본 정보
    name = models.CharField(
        max_length=100,
        help_text="템플릿 이름 (예: 모던 화이트)"
    )
    
    description = models.TextField(
        help_text="템플릿 설명"
    )
    
    category = models.CharField(
        max_length=50,
        choices=[
            ('modern', '모던'),
            ('classic', '클래식'),
            ('minimal', '미니멀'),
            ('vintage', '빈티지'),
            ('floral', '플로럴'),
            ('elegant', '우아함'),
        ],
        default='modern'
    )
    
    # 미리보기
    thumbnail_url = models.URLField(
        help_text="썸네일 이미지 URL"
    )
    
    preview_url = models.URLField(
        help_text="미리보기 페이지 URL"
    )
    
    # 템플릿 파일
    # 옵션 1: HTML 템플릿 경로
    template_path = models.CharField(
        max_length=255,
        help_text="Django 템플릿 파일 경로 (예: templates/invitations/modern_white.html)"
    )
    
    # 옵션 2: React 컴포넌트 이름
    component_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="React 컴포넌트 이름 (SPA인 경우)"
    )
    
    # 가격
    is_free = models.BooleanField(
        default=True,
        help_text="무료 템플릿 여부"
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="유료 템플릿 가격"
    )
    
    # 스키마 (템플릿이 지원하는 설정 항목)
    schema = models.JSONField(
        default=dict,
        help_text="""
        템플릿 설정 스키마 (JSON Schema 형식)
        예: {
            "fields": {
                "bride_name": {"type": "string", "required": true},
                "groom_name": {"type": "string", "required": true},
                "wedding_date": {"type": "datetime", "required": true},
                "venue": {"type": "object", "required": true},
                "photos": {"type": "array", "max_items": 10},
                "background_music": {"type": "string", "required": false},
                "theme_color": {
                    "type": "string", 
                    "default": "#FFB6C1",
                    "options": ["#FFB6C1", "#E6E6FA", "#FFF8DC"]
                }
            },
            "features": {
                "gallery": true,
                "guestbook": true,
                "attendance": true,
                "video": false,
                "map": true
            }
        }
        """
    )
    
    # 버전 관리
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        help_text="템플릿 버전 (시맨틱 버저닝)"
    )
    
    # 통계
    usage_count = models.IntegerField(
        default=0,
        help_text="사용 횟수"
    )
    
    # 상태
    is_active = models.BooleanField(
        default=True,
        help_text="활성화 여부 (false면 목록에서 숨김)"
    )
    
    # 정렬
    display_order = models.IntegerField(
        default=0,
        help_text="표시 순서 (낮을수록 먼저)"
    )
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'templates'
        ordering = ['display_order', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_free', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    def increment_usage(self):
        """사용 횟수 증가 (원자적)"""
        self.__class__.objects.filter(id=self.id).update(
            usage_count=models.F('usage_count') + 1
        )
```

**템플릿 스키마 예시:**

```json
{
  "fields": {
    "bride": {
      "type": "object",
      "required": true,
      "properties": {
        "name": {"type": "string", "max_length": 50},
        "father_name": {"type": "string", "required": false},
        "mother_name": {"type": "string", "required": false},
        "phone": {"type": "string", "required": false}
      }
    },
    "groom": {
      "type": "object",
      "required": true,
      "properties": {
        "name": {"type": "string", "max_length": 50},
        "father_name": {"type": "string", "required": false},
        "mother_name": {"type": "string", "required": false},
        "phone": {"type": "string", "required": false}
      }
    },
    "wedding_date": {
      "type": "datetime",
      "required": true
    },
    "venue": {
      "type": "object",
      "required": true,
      "properties": {
        "name": {"type": "string"},
        "address": {"type": "string"},
        "floor": {"type": "string"},
        "hall_name": {"type": "string"},
        "latitude": {"type": "number"},
        "longitude": {"type": "number"}
      }
    },
    "theme_color": {
      "type": "string",
      "default": "#FFB6C1",
      "enum": ["#FFB6C1", "#E6E6FA", "#FFF8DC", "#F0E68C"]
    },
    "font_family": {
      "type": "string",
      "default": "Noto Sans KR",
      "enum": ["Noto Sans KR", "Nanum Gothic", "Nanum Myeongjo"]
    },
    "background_music": {
      "type": "string",
      "required": false,
      "description": "YouTube URL 또는 파일 URL"
    }
  },
  "features": {
    "gallery": {
      "enabled": true,
      "max_photos": 20
    },
    "guestbook": {
      "enabled": true,
      "requires_password": false
    },
    "attendance": {
      "enabled": true
    },
    "video": {
      "enabled": false
    },
    "map": {
      "enabled": true,
      "provider": "kakao"
    },
    "account_transfer": {
      "enabled": true,
      "supports_kakaopay": true
    }
  },
  "layout": {
    "sections": [
      "header",
      "intro",
      "couple_info",
      "gallery",
      "map",
      "guestbook",
      "account"
    ]
  }
}
```

이 스키마를 통해:
- 템플릿마다 다른 설정 항목 지원
- 프론트엔드에서 동적 폼 생성
- 유효성 검사 (Pydantic으로 변환 가능)

---

## 3. Invitation 모델 - 핵심 엔티티

### 3.1 Invitation 모델 설계

```python
# invitations/models.py
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import RegexValidator
import uuid

class Invitation(models.Model):
    """
    청첩장 인스턴스
    
    사용자가 템플릿을 기반으로 생성한 실제 청첩장
    """
    
    # 관계
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text="청첩장 소유자"
    )
    
    template = models.ForeignKey(
        'Template',
        on_delete=models.PROTECT,  # 템플릿 삭제 방지
        related_name='invitations',
        help_text="사용된 템플릿"
    )
    
    # 고유 식별자
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID (보안상 순차 ID 대신 사용)"
    )
    
    # URL Slug
    slug = models.SlugField(
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9-]+$',
                message='소문자, 숫자, 하이픈만 사용 가능'
            )
        ],
        help_text="URL 경로 (예: john-mary-2025)"
    )
    
    # 기본 정보
    title = models.CharField(
        max_length=200,
        help_text="청첩장 제목 (예: John & Mary의 결혼식에 초대합니다)"
    )
    
    # 상태
    class Status(models.TextChoices):
        DRAFT = 'draft', '임시저장'
        PUBLISHED = 'published', '공개'
        PRIVATE = 'private', '비공개'
        ARCHIVED = 'archived', '보관됨'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="공개 상태"
    )
    
    # 설정 데이터 (JSON)
    settings = models.JSONField(
        default=dict,
        help_text="""
        템플릿 스키마에 따른 사용자 설정값
        예: {
            "bride": {"name": "김지영", "father_name": "김철수"},
            "groom": {"name": "이민수", "mother_name": "박영희"},
            "wedding_date": "2025-12-25T14:00:00+09:00",
            "venue": {
                "name": "서울 웨딩홀",
                "address": "서울시 강남구...",
                "latitude": 37.123456,
                "longitude": 127.123456
            },
            "theme_color": "#FFB6C1",
            "font_family": "Noto Sans KR"
        }
        """
    )
    
    # 보안
    password = models.CharField(
        max_length=128,
        blank=True,
        help_text="비공개 청첩장 비밀번호 (해싱된 값)"
    )
    
    is_password_protected = models.BooleanField(
        default=False,
        help_text="비밀번호 보호 여부"
    )
    
    # 통계
    view_count = models.IntegerField(
        default=0,
        help_text="조회수"
    )
    
    unique_visitor_count = models.IntegerField(
        default=0,
        help_text="순 방문자 수"
    )
    
    share_count = models.IntegerField(
        default=0,
        help_text="공유 횟수"
    )
    
    # 날짜
    wedding_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="결혼식 날짜 (빠른 조회용)"
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="공개 일시"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['wedding_date']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.slug})"
    
    def save(self, *args, **kwargs):
        # Slug 자동 생성
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        # wedding_date 자동 추출
        if self.settings.get('wedding_date'):
            from dateutil import parser
            self.wedding_date = parser.parse(self.settings['wedding_date'])
        
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        """고유한 Slug 생성"""
        base_slug = slugify(self.title[:50])
        
        # 영문이 없으면 UUID 일부 사용
        if not base_slug:
            base_slug = str(uuid.uuid4())[:8]
        
        slug = base_slug
        counter = 1
        
        # 중복 확인
        while Invitation.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    @property
    def url(self):
        """공개 URL"""
        from django.urls import reverse
        return reverse('invitation_detail', kwargs={'slug': self.slug})
    
    @property
    def full_url(self):
        """전체 URL (도메인 포함)"""
        from django.conf import settings
        return f"{settings.SITE_URL}{self.url}"
    
    def increment_view(self, is_unique=False):
        """조회수 증가"""
        update_fields = {'view_count': models.F('view_count') + 1}
        if is_unique:
            update_fields['unique_visitor_count'] = models.F('unique_visitor_count') + 1
        
        self.__class__.objects.filter(id=self.id).update(**update_fields)
    
    def get_bride_name(self):
        """신부 이름 추출"""
        return self.settings.get('bride', {}).get('name', '')
    
    def get_groom_name(self):
        """신랑 이름 추출"""
        return self.settings.get('groom', {}).get('name', '')
```

### 3.2 JSON Settings vs 정규화 테이블 비교

**왜 settings를 JSONField로?**

```python
# ❌ 안티패턴: 모든 필드를 테이블 컬럼으로
class BadInvitation(models.Model):
    bride_name = models.CharField(max_length=50)
    bride_father = models.CharField(max_length=50, blank=True)
    bride_mother = models.CharField(max_length=50, blank=True)
    groom_name = models.CharField(max_length=50)
    groom_father = models.CharField(max_length=50, blank=True)
    venue_name = models.CharField(max_length=100)
    venue_address = models.TextField()
    theme_color = models.CharField(max_length=7)
    font_family = models.CharField(max_length=50)
    # 템플릿마다 필드가 다르면? → 테이블 변경 필요!
    # 새로운 설정 추가 시 마이그레이션 필수!

# ✅ 올바른 패턴: JSON으로 유연하게
class Invitation(models.Model):
    settings = models.JSONField(default=dict)
    # 템플릿 스키마에 따라 자유롭게 확장 가능
    # 마이그레이션 없이 새 필드 추가 가능
```

**JSONField 장점:**
1. **유연성**: 템플릿마다 다른 필드 구조 지원
2. **확장성**: 새 설정 추가 시 DB 변경 불필요
3. **간결성**: 수십 개 컬럼 대신 하나의 JSON

**JSONField 단점 및 해결책:**
1. **쿼리 복잡도**: JSON 내부 검색 어려움
   - 해결: 자주 검색하는 필드는 별도 컬럼 (`wedding_date`, `title`)
   
2. **타입 안정성**: 런타임 에러 가능
   - 해결: Pydantic으로 검증 (아래 예시)

3. **인덱싱 제한**: JSON 내부 필드 인덱싱 어려움
   - 해결: PostgreSQL의 GIN 인덱스 활용

```python
# PostgreSQL JSON 인덱싱 (마이그레이션)
from django.contrib.postgres.operations import AddIndexConcurrently
from django.contrib.postgres.indexes import GinIndex

class Migration(migrations.Migration):
    operations = [
        # JSON 필드 전체 인덱싱
        AddIndexConcurrently(
            model_name='invitation',
            index=GinIndex(fields=['settings'], name='idx_settings_gin'),
        ),
    ]

# JSON 쿼리 예시 (PostgreSQL)
from django.contrib.postgres.fields.jsonb import KeyTextTransform

# 신부 이름으로 검색
invitations = Invitation.objects.annotate(
    bride_name=KeyTextTransform('name', KeyTextTransform('bride', 'settings'))
).filter(bride_name='김지영')
```

### 3.3 Pydantic으로 Settings 검증

```python
# invitations/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class PersonInfo(BaseModel):
    """인물 정보"""
    name: str = Field(..., max_length=50)
    father_name: Optional[str] = Field(None, max_length=50)
    mother_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, regex=r'^\d{3}-\d{4}-\d{4}$')
    relation: Optional[str] = None  # "장남", "차녀" 등

class VenueInfo(BaseModel):
    """장소 정보"""
    name: str = Field(..., max_length=100)
    address: str
    floor: Optional[str] = None
    hall_name: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    phone: Optional[str] = None
    
    @validator('latitude', 'longitude')
    def validate_coords(cls, v):
        if v == 0:
            raise ValueError('Invalid coordinates')
        return v

class AccountInfo(BaseModel):
    """계좌 정보"""
    bank_name: str
    account_number: str
    account_holder: str
    relation: str  # "신랑", "신부", "신랑 아버지" 등

class InvitationSettings(BaseModel):
    """청첩장 설정 (템플릿 스키마 기반)"""
    
    # 필수 정보
    bride: PersonInfo
    groom: PersonInfo
    wedding_date: datetime
    venue: VenueInfo
    
    # 선택 정보
    message: Optional[str] = Field(None, max_length=1000)
    theme_color: str = Field(default='#FFB6C1', regex=r'^#[0-9A-Fa-f]{6}$')
    font_family: str = Field(default='Noto Sans KR')
    background_music: Optional[str] = None
    
    # 계좌 정보 (여러 개 가능)
    accounts: List[AccountInfo] = Field(default_factory=list, max_items=10)
    
    # 기능 활성화
    enable_guestbook: bool = True
    enable_attendance: bool = True
    enable_gallery: bool = True
    
    # 커스텀 섹션
    custom_sections: Optional[dict] = None
    
    @validator('wedding_date')
    def validate_wedding_date(cls, v):
        if v < datetime.now():
            raise ValueError('Wedding date must be in the future')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "bride": {
                    "name": "김지영",
                    "father_name": "김철수",
                    "mother_name": "이영희"
                },
                "groom": {
                    "name": "박민수",
                    "father_name": "박동진",
                    "mother_name": "최수진"
                },
                "wedding_date": "2025-12-25T14:00:00+09:00",
                "venue": {
                    "name": "서울 웨딩홀",
                    "address": "서울시 강남구 테헤란로 123",
                    "floor": "3층",
                    "hall_name": "그랜드홀",
                    "latitude": 37.5012345,
                    "longitude": 127.0398765,
                    "phone": "02-1234-5678"
                },
                "theme_color": "#FFB6C1",
                "accounts": [
                    {
                        "bank_name": "국민은행",
                        "account_number": "123-456-789012",
                        "account_holder": "박민수",
                        "relation": "신랑"
                    }
                ]
            }
        }

# Django-Ninja API에서 사용
from ninja import Router, Schema
from typing import Optional

router = Router(tags=["Invitations"])

class CreateInvitationIn(Schema):
    template_id: int
    title: str
    slug: Optional[str] = None
    settings: dict  # InvitationSettings로 검증됨

@router.post("/")
def create_invitation(request, data: CreateInvitationIn):
    # Pydantic으로 검증
    try:
        validated_settings = InvitationSettings(**data.settings)
    except Exception as e:
        return 400, {"error": str(e)}
    
    # Invitation 생성
    invitation = Invitation.objects.create(
        user=request.user,
        template_id=data.template_id,
        title=data.title,
        slug=data.slug,
        settings=validated_settings.dict()  # dict로 변환하여 저장
    )
    
    return {"id": str(invitation.id), "slug": invitation.slug}
```

---

## 4. 관련 엔티티 설계

### 4.1 Photo 모델 (갤러리)

```python
# invitations/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
import os

def invitation_photo_path(instance, filename):
    """사진 업로드 경로"""
    ext = os.path.splitext(filename)[1]
    return f'invitations/{instance.invitation.id}/photos/{instance.id}{ext}'

class Photo(models.Model):
    """
    청첩장 사진
    
    메인 사진, 갤러리 사진 관리
    """
    
    invitation = models.ForeignKey(
        'Invitation',
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    # 이미지
    image = models.ImageField(
        upload_to=invitation_photo_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])
        ],
        help_text="원본 이미지"
    )
    
    # 썸네일 (자동 생성)
    thumbnail = models.ImageField(
        upload_to=invitation_photo_path,
        blank=True,
        null=True,
        help_text="썸네일 (자동 생성)"
    )
    
    # 메타데이터
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    file_size = models.IntegerField(default=0, help_text="바이트 단위")
    
    # 순서 및 타입
    display_order = models.IntegerField(
        default=0,
        help_text="표시 순서 (낮을수록 먼저)"
    )
    
    is_main = models.BooleanField(
        default=False,
        help_text="메인 사진 여부 (OG 이미지로 사용)"
    )
    
    # 캡션
    caption = models.CharField(
        max_length=200,
        blank=True,
        help_text="사진 설명"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'photos'
        ordering = ['display_order', 'created_at']
        indexes = [
            models.Index(fields=['invitation', 'display_order']),
        ]
    
    def __str__(self):
        return f"Photo for {self.invitation.slug}"
    
    def save(self, *args, **kwargs):
        # 이미지 메타데이터 추출
        if self.image:
            from PIL import Image
            img = Image.open(self.image)
            self.width, self.height = img.size
            self.file_size = self.image.size
            
            # 썸네일 생성
            if not self.thumbnail:
                self.create_thumbnail(img)
        
        super().save(*args, **kwargs)
    
    def create_thumbnail(self, img):
        """썸네일 생성"""
        from PIL import Image
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        # 비율 유지하며 리사이즈
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # 메모리에 저장
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        
        # 파일로 저장
        thumb_file = ContentFile(thumb_io.getvalue())
        self.thumbnail.save(
            f'thumb_{self.id}.jpg',
            thumb_file,
            save=False
        )
```

### 4.2 GuestBook 모델 (방명록)

```python
class GuestBook(models.Model):
    """
    방명록
    
    축하 메시지 및 덕담
    """
    
    invitation = models.ForeignKey(
        'Invitation',
        on_delete=models.CASCADE,
        related_name='guestbook_entries'
    )
    
    # 작성자 정보
    author_name = models.CharField(
        max_length=50,
        help_text="작성자 이름"
    )
    
    password = models.CharField(
        max_length=128,
        help_text="수정/삭제 비밀번호 (해싱)"
    )
    
    # 메시지
    message = models.TextField(
        max_length=500,
        help_text="축하 메시지"
    )
    
    # 관계
    relation = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('friend', '친구'),
            ('colleague', '직장동료'),
            ('family', '가족'),
            ('relative', '친척'),
            ('etc', '기타'),
        ],
        help_text="신랑/신부와의 관계"
    )
    
    # 공개 여부
    is_public = models.BooleanField(
        default=True,
        help_text="공개 여부 (비공개 시 주인만 볼 수 있음)"
    )
    
    # IP 및 User Agent (스팸 방지)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    user_agent = models.TextField(
        blank=True
    )
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'guestbook'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invitation', '-created_at']),
            models.Index(fields=['invitation', 'is_public', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.author_name}: {self.message[:50]}"

### 4.3 Attendance 모델 (참석 여부)

```python
class Attendance(models.Model):
    """
    참석 여부 관리
    
    식사 준비, 좌석 배치 등에 활용
    """
    
    invitation = models.ForeignKey(
        'Invitation',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    
    # 참석자 정보
    guest_name = models.CharField(
        max_length=50,
        help_text="참석자 이름"
    )
    
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="연락처 (선택)"
    )
    
    # 참석 여부
    will_attend = models.BooleanField(
        help_text="참석 여부"
    )
    
    guest_count = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="동반 인원 (본인 포함)"
    )
    
    # 식사 정보
    meal_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('normal', '일반식'),
            ('vegetarian', '채식'),
            ('halal', '할랄'),
            ('kids', '어린이식'),
        ],
        help_text="식사 종류"
    )
    
    # 메시지
    message = models.TextField(
        max_length=200,
        blank=True,
        help_text="전할 말"
    )
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendances'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invitation', 'will_attend']),
        ]
        # 동일인 중복 제출 방지
        unique_together = [['invitation', 'guest_name', 'phone_number']]
    
    def __str__(self):
        status = "참석" if self.will_attend else "불참"
        return f"{self.guest_name} - {status}"
```

### 4.4 Analytics 모델 (방문 통계)

```python
class Analytics(models.Model):
    """
    방문 통계
    
    조회수, 유입 경로 등 추적
    """
    
    invitation = models.ForeignKey(
        'Invitation',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # 방문 정보
    visitor_id = models.CharField(
        max_length=100,
        help_text="방문자 식별자 (쿠키 또는 fingerprint)"
    )
    
    ip_address = models.GenericIPAddressField()
    
    user_agent = models.TextField(
        help_text="User-Agent 문자열"
    )
    
    # 디바이스 정보 (파싱)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile', '모바일'),
            ('tablet', '태블릿'),
            ('desktop', '데스크톱'),
        ],
        blank=True
    )
    
    os = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    
    # 유입 정보
    referrer = models.URLField(
        blank=True,
        help_text="유입 URL"
    )
    
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    
    # 페이지 정보
    page_url = models.CharField(max_length=500)
    
    # 세션 정보
    session_duration = models.IntegerField(
        default=0,
        help_text="세션 시간 (초)"
    )
    
    # 날짜
    visit_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics'
        ordering = ['-visit_date']
        indexes = [
            models.Index(fields=['invitation', '-visit_date']),
            models.Index(fields=['visitor_id']),
        ]
    
    def __str__(self):
        return f"{self.invitation.slug} - {self.visit_date}"
```

---

## 5. Django-Ninja API 구현

### 5.1 스키마 정의

```python
# invitations/schemas.py
from ninja import Schema, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ===== 템플릿 스키마 =====

class TemplateOut(Schema):
    """템플릿 응답"""
    id: int
    name: str
    description: str
    category: str
    thumbnail_url: str
    preview_url: str
    is_free: bool
    price: Decimal
    usage_count: int
    
    @staticmethod
    def resolve_price(obj):
        return str(obj.price)  # Decimal을 문자열로

class TemplateListOut(Schema):
    """템플릿 목록"""
    templates: List[TemplateOut]
    total: int
    category: Optional[str] = None

# ===== 청첩장 스키마 =====

class InvitationCreateIn(Schema):
    """청첩장 생성 요청"""
    template_id: int = Field(..., description="템플릿 ID")
    title: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = Field(None, regex=r'^[a-z0-9-]+$')
    settings: dict = Field(default_factory=dict)

class InvitationUpdateIn(Schema):
    """청첩장 수정 요청"""
    title: Optional[str] = None
    settings: Optional[dict] = None
    status: Optional[str] = None

class InvitationOut(Schema):
    """청첩장 응답 (간략)"""
    id: str
    slug: str
    title: str
    status: str
    template: TemplateOut
    view_count: int
    created_at: datetime
    updated_at: datetime
    url: str
    
    @staticmethod
    def resolve_id(obj):
        return str(obj.id)
    
    @staticmethod
    def resolve_url(obj):
        return obj.url

class InvitationDetailOut(InvitationOut):
    """청첩장 상세 응답"""
    settings: dict
    wedding_date: Optional[datetime]
    unique_visitor_count: int
    share_count: int

# ===== 사진 스키마 =====

class PhotoOut(Schema):
    """사진 응답"""
    id: int
    image_url: str
    thumbnail_url: Optional[str]
    caption: str
    display_order: int
    is_main: bool
    
    @staticmethod
    def resolve_image_url(obj):
        return obj.image.url if obj.image else None
    
    @staticmethod
    def resolve_thumbnail_url(obj):
        return obj.thumbnail.url if obj.thumbnail else None

# ===== 방명록 스키마 =====

class GuestBookCreateIn(Schema):
    """방명록 작성"""
    author_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=4, max_length=20)
    message: str = Field(..., min_length=1, max_length=500)
    relation: Optional[str] = None
    is_public: bool = True

class GuestBookOut(Schema):
    """방명록 응답"""
    id: int
    author_name: str
    message: str
    relation: str
    is_public: bool
    created_at: datetime
    
    # 비밀번호는 절대 노출하지 않음!

# ===== 참석 스키마 =====

class AttendanceCreateIn(Schema):
    """참석 여부 제출"""
    guest_name: str = Field(..., min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, regex=r'^\d{3}-\d{4}-\d{4}$')
    will_attend: bool
    guest_count: int = Field(default=1, ge=0, le=10)
    meal_type: Optional[str] = None
    message: Optional[str] = Field(None, max_length=200)

class AttendanceOut(Schema):
    """참석 응답"""
    id: int
    guest_name: str
    will_attend: bool
    guest_count: int
    created_at: datetime

class AttendanceSummaryOut(Schema):
    """참석 통계"""
    total_responses: int
    attending_count: int
    not_attending_count: int
    total_guests: int  # 동반 인원 포함
```

### 5.2 API 엔드포인트

```python
# invitations/api.py
from ninja import Router
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from django.db import transaction
from typing import List
from .models import Template, Invitation, Photo, GuestBook, Attendance
from .schemas import *

router = Router(tags=["Invitations"])

# ===== 템플릿 API =====

@router.get("/templates", response=TemplateListOut)
def list_templates(
    request,
    category: Optional[str] = None,
    is_free: Optional[bool] = None
):
    """
    템플릿 목록 조회
    
    Query Parameters:
    - category: 카테고리 필터 (modern, classic, minimal 등)
    - is_free: 무료/유료 필터
    """
    templates = Template.objects.filter(is_active=True)
    
    if category:
        templates = templates.filter(category=category)
    
    if is_free is not None:
        templates = templates.filter(is_free=is_free)
    
    return {
        "templates": list(templates),
        "total": templates.count(),
        "category": category
    }

@router.get("/templates/{template_id}", response=TemplateOut)
def get_template(request, template_id: int):
    """템플릿 상세 조회"""
    template = get_object_or_404(Template, id=template_id, is_active=True)
    return template

# ===== 청첩장 CRUD =====

@router.post("/", response=InvitationOut)
@transaction.atomic
def create_invitation(request, data: InvitationCreateIn):
    """
    청첩장 생성
    
    1. 템플릿 선택
    2. 기본 정보 입력
    3. 임시저장 상태로 생성
    """
    # 템플릿 확인
    template = get_object_or_404(Template, id=data.template_id, is_active=True)
    
    # 유료 템플릿인 경우 권한 확인
    if not template.is_free and not request.user.is_premium_active:
        return 403, {"error": "Premium template requires premium subscription"}
    
    # Pydantic으로 settings 검증 (선택적)
    if data.settings:
        try:
            from .schemas import InvitationSettings
            InvitationSettings(**data.settings)
        except Exception as e:
            return 400, {"error": f"Invalid settings: {str(e)}"}
    
    # 청첩장 생성
    invitation = Invitation.objects.create(
        user=request.user,
        template=template,
        title=data.title,
        slug=data.slug,
        settings=data.settings,
        status=Invitation.Status.DRAFT
    )
    
    # 템플릿 사용 횟수 증가
    template.increment_usage()
    
    # 사용자 청첩장 수 증가
    request.user.invitation_count += 1
    request.user.save(update_fields=['invitation_count'])
    
    return invitation

@router.get("/", response=List[InvitationOut])
def list_my_invitations(request):
    """내 청첩장 목록"""
    invitations = Invitation.objects.filter(
        user=request.user
    ).select_related('template')
    
    return list(invitations)

@router.get("/{slug}", response=InvitationDetailOut)
def get_invitation(request, slug: str):
    """
    청첩장 상세 조회
    
    공개된 청첩장은 누구나 볼 수 있음
    """
    invitation = get_object_or_404(Invitation, slug=slug)
    
    # 비공개 청첩장 권한 확인
    if invitation.status == Invitation.Status.PRIVATE:
        if not request.user.is_authenticated or invitation.user != request.user:
            return 403, {"error": "Private invitation"}
    
    # 조회수 증가 (비동기 권장)
    invitation.increment_view()
    
    return invitation

@router.patch("/{slug}", response=InvitationOut)
@transaction.atomic
def update_invitation(request, slug: str, data: InvitationUpdateIn):
    """청첩장 수정"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    # 업데이트
    update_data = data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(invitation, field, value)
    
    invitation.save()
    
    return invitation

@router.post("/{slug}/publish", response=InvitationOut)
def publish_invitation(request, slug: str):
    """청첩장 공개"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    # 필수 정보 검증
    required_fields = ['bride', 'groom', 'wedding_date', 'venue']
    missing = [f for f in required_fields if f not in invitation.settings]
    
    if missing:
        return 400, {"error": f"Missing required fields: {', '.join(missing)}"}
    
    # 공개 처리
    from django.utils import timezone
    invitation.status = Invitation.Status.PUBLISHED
    invitation.published_at = timezone.now()
    invitation.save(update_fields=['status', 'published_at'])
    
    return invitation

@router.delete("/{slug}")
def delete_invitation(request, slug: str):
    """청첩장 삭제"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    # 소프트 삭제 (보관)
    invitation.status = Invitation.Status.ARCHIVED
    invitation.save(update_fields=['status'])
    
    return {"success": True}

# ===== 사진 API =====

@router.get("/{slug}/photos", response=List[PhotoOut])
def list_photos(request, slug: str):
    """사진 목록"""
    invitation = get_object_or_404(Invitation, slug=slug)
    photos = invitation.photos.all()
    return list(photos)

@router.post("/{slug}/photos")
@transaction.atomic
def upload_photo(request, slug: str):
    """
    사진 업로드
    
    multipart/form-data로 이미지 전송
    """
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    # 템플릿의 최대 사진 수 확인
    template_schema = invitation.template.schema
    max_photos = template_schema.get('features', {}).get('gallery', {}).get('max_photos', 20)
    
    current_count = invitation.photos.count()
    if current_count >= max_photos:
        return 400, {"error": f"Maximum {max_photos} photos allowed"}
    
    # 파일 업로드
    uploaded_file = request.FILES.get('image')
    if not uploaded_file:
        return 400, {"error": "No image file"}
    
    # 파일 크기 확인 (5MB 제한)
    if uploaded_file.size > 5 * 1024 * 1024:
        return 400, {"error": "File size must be less than 5MB"}
    
    # Photo 생성
    photo = Photo.objects.create(
        invitation=invitation,
        image=uploaded_file,
        display_order=current_count,
        caption=request.POST.get('caption', '')
    )
    
    return {"id": photo.id, "image_url": photo.image.url}

@router.delete("/{slug}/photos/{photo_id}")
def delete_photo(request, slug: str, photo_id: int):
    """사진 삭제"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    photo = get_object_or_404(Photo, id=photo_id, invitation=invitation)
    
    photo.delete()
    
    return {"success": True}

# ===== 방명록 API =====

@router.get("/{slug}/guestbook", response=List[GuestBookOut])
@paginate
def list_guestbook(request, slug: str):
    """방명록 목록"""
    invitation = get_object_or_404(Invitation, slug=slug)
    
    # 공개된 항목만 (소유자는 모두 볼 수 있음)
    entries = invitation.guestbook_entries.all()
    
    if not request.user.is_authenticated or invitation.user != request.user:
        entries = entries.filter(is_public=True)
    
    return list(entries)

@router.post("/{slug}/guestbook", response=GuestBookOut)
def create_guestbook(request, slug: str, data: GuestBookCreateIn):
    """방명록 작성"""
    invitation = get_object_or_404(Invitation, slug=slug)
    
    # 공개 상태 확인
    if invitation.status != Invitation.Status.PUBLISHED:
        return 403, {"error": "Invitation is not published"}
    
    # 비밀번호 해싱
    from django.contrib.auth.hashers import make_password
    
    entry = GuestBook.objects.create(
        invitation=invitation,
        author_name=data.author_name,
        password=make_password(data.password),
        message=data.message,
        relation=data.relation or 'etc',
        is_public=data.is_public,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return entry

@router.delete("/{slug}/guestbook/{entry_id}")
def delete_guestbook(request, slug: str, entry_id: int, password: str):
    """방명록 삭제"""
    invitation = get_object_or_404(Invitation, slug=slug)
    entry = get_object_or_404(GuestBook, id=entry_id, invitation=invitation)
    
    # 비밀번호 확인
    from django.contrib.auth.hashers import check_password
    
    if not check_password(password, entry.password):
        return 403, {"error": "Invalid password"}
    
    entry.delete()
    
    return {"success": True}

# ===== 참석 API =====

@router.post("/{slug}/attendance", response=AttendanceOut)
def submit_attendance(request, slug: str, data: AttendanceCreateIn):
    """참석 여부 제출"""
    invitation = get_object_or_404(Invitation, slug=slug)
    
    # 중복 체크
    existing = Attendance.objects.filter(
        invitation=invitation,
        guest_name=data.guest_name,
        phone_number=data.phone_number or ''
    ).first()
    
    if existing:
        # 업데이트
        for field, value in data.dict().items():
            setattr(existing, field, value)
        existing.save()
        return existing
    
    # 새로 생성
    attendance = Attendance.objects.create(
        invitation=invitation,
        **data.dict()
    )
    
    return attendance

@router.get("/{slug}/attendance/summary", response=AttendanceSummaryOut)
def get_attendance_summary(request, slug: str):
    """참석 통계 (소유자만)"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    from django.db.models import Sum, Count
    
    stats = invitation.attendances.aggregate(
        total_responses=Count('id'),
        attending_count=Count('id', filter=models.Q(will_attend=True)),
        not_attending_count=Count('id', filter=models.Q(will_attend=False)),
        total_guests=Sum('guest_count', filter=models.Q(will_attend=True))
    )
    
    return stats
```

### 5.3 인증 및 권한

```python
# invitations/auth.py
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthBearer(HttpBearer):
    """JWT 인증"""
    
    def authenticate(self, request, token):
        try:
            # JWT 디코딩
            import jwt
            from django.conf import settings
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            return user
        
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None

# API에 인증 적용
from ninja import NinjaAPI

api = NinjaAPI(auth=AuthBearer())

# 인증 필요한 엔드포인트
@api.post("/invitations/")
def create_invitation(request, data: InvitationCreateIn):
    # request.auth에 User 객체
    user = request.auth
    # ...

# 인증 선택적 엔드포인트
from ninja.security import HttpBearer
from typing import Optional

class OptionalAuth(HttpBearer):
    def authenticate(self, request, token):
        # 토큰이 없어도 None 반환 (에러 X)
        if not token:
            return None
        # ... JWT 검증
        return user

@api.get("/invitations/{slug}", auth=OptionalAuth())
def get_invitation(request, slug: str):
    user = request.auth  # None 또는 User
    # ...
```

---

## 6. 고급 기능 구현

### 6.1 실시간 조회수 추적

```python
# invitations/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import hashlib

class VisitorTrackingMiddleware(MiddlewareMixin):
    """방문자 추적 미들웨어"""
    
    def process_request(self, request):
        if request.path.startswith('/wedding/'):
            slug = request.path.split('/')[-1]
            
            # 방문자 ID 생성 (IP + User-Agent)
            visitor_data = f"{request.META.get('REMOTE_ADDR')}{request.META.get('HTTP_USER_AGENT', '')}"
            visitor_id = hashlib.md5(visitor_data.encode()).hexdigest()
            
            # 중복 방문 체크 (24시간)
            cache_key = f"visitor:{slug}:{visitor_id}"
            
            if not cache.get(cache_key):
                # 첫 방문
                from .models import Invitation, Analytics
                
                try:
                    invitation = Invitation.objects.get(slug=slug)
                    
                    # Analytics 기록
                    Analytics.objects.create(
                        invitation=invitation,
                        visitor_id=visitor_id,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        referrer=request.META.get('HTTP_REFERER', ''),
                        page_url=request.build_absolute_uri(),
                        utm_source=request.GET.get('utm_source', ''),
                        utm_medium=request.GET.get('utm_medium', ''),
                        utm_campaign=request.GET.get('utm_campaign', '')
                    )
                    
                    # 조회수 증가
                    invitation.increment_view(is_unique=True)
                    
                    # 캐시 설정 (24시간)
                    cache.set(cache_key, True, 86400)
                
                except Invitation.DoesNotExist:
                    pass

# settings.py
MIDDLEWARE = [
    # ...
    'invitations.middleware.VisitorTrackingMiddleware',
]
```

### 6.2 QR 코드 생성

```python
# invitations/utils.py
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generate_qr_code(invitation):
    """
    청첩장 QR 코드 생성
    
    Returns:
        BytesIO: QR 코드 이미지
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(invitation.full_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer

# API에서 사용
@router.get("/{slug}/qr-code")
def get_qr_code(request, slug: str):
    """QR 코드 다운로드"""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    
    qr_buffer = generate_qr_code(invitation)
    
    from django.http import HttpResponse
    response = HttpResponse(qr_buffer, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{slug}_qr.png"'
    
    return response
```

### 6.3 카카오톡 공유 (Open Graph)

```python
# templates/invitation_detail.html
<!DOCTYPE html>
<html>
<head>
{% raw %}
    <!-- Open Graph 메타 태그 -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{{ invitation.title }}">
    <meta property="og:description" content="{{ invitation.settings.bride.name }}💕{{ invitation.settings.groom.name }}의 결혼식에 초대합니다">
    <meta property="og:url" content="{{ invitation.full_url }}">
    
    {% if invitation.photos.filter(is_main=True).first %}
    <meta property="og:image" content="{{ invitation.photos.filter(is_main=True).first.image.url }}">
    {% endif %}
{% endraw %}
    
    <!-- 카카오톡 -->
    <meta property="og:image:width" content="800">
    <meta property="og:image:height" content="400">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
</head>
<body>
    <!-- 청첩장 내용 -->
</body>
</html>
```

### 6.4 캐싱 전략

```python
# invitations/views.py
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

# 공개된 청첩장은 5분 캐싱
@cache_page(60 * 5)
def invitation_detail_view(request, slug):
    invitation = get_object_or_404(Invitation, slug=slug)
    # ...

# Redis 캐싱
from django.core.cache import cache

def get_invitation_cached(slug):
    """청첩장 조회 (캐시 활용)"""
    cache_key = f"invitation:{slug}"
    
    invitation = cache.get(cache_key)
    
    if not invitation:
        invitation = Invitation.objects.select_related('template').get(slug=slug)
        cache.set(cache_key, invitation, 300)  # 5분
    
    return invitation

# 수정 시 캐시 무효화
@transaction.atomic
def update_invitation(invitation_id, **data):
    invitation = Invitation.objects.get(id=invitation_id)
    
    for key, value in data.items():
        setattr(invitation, key, value)
    
    invitation.save()
    
    # 캐시 삭제
    cache.delete(f"invitation:{invitation.slug}")
    
    return invitation
```

---

## 7. 성능 최적화 및 확장성

### 7.1 데이터베이스 인덱싱 전략

```python
# 복합 인덱스 마이그레이션
from django.db import migrations, models

class Migration(migrations.Migration):
    operations = [
        # 1. 자주 조회되는 필드 조합
        migrations.AddIndex(
            model_name='invitation',
            index=models.Index(
                fields=['user', 'status', '-created_at'],
                name='idx_user_status_date'
            ),
        ),
        
        # 2. 공개된 청첩장 조회
        migrations.AddIndex(
            model_name='invitation',
            index=models.Index(
                fields=['status', '-wedding_date'],
                name='idx_status_wedding'
            ),
        ),
        
        # 3. Slug 조회 (이미 unique=True지만 명시적 인덱스)
        migrations.AddIndex(
            model_name='invitation',
            index=models.Index(
                fields=['slug'],
                name='idx_slug'
            ),
        ),
        
        # 4. 방명록 pagination
        migrations.AddIndex(
            model_name='guestbook',
            index=models.Index(
                fields=['invitation', 'is_public', '-created_at'],
                name='idx_guestbook_list'
            ),
        ),
        
        # 5. PostgreSQL 부분 인덱스 (공개된 청첩장만)
        migrations.RunSQL(
            sql="""
                CREATE INDEX idx_published_invitations 
                ON invitations (wedding_date DESC)
                WHERE status = 'published';
            """,
            reverse_sql="DROP INDEX idx_published_invitations;"
        ),
        
        # 6. JSON 필드 GIN 인덱스
        migrations.RunSQL(
            sql="""
                CREATE INDEX idx_invitation_settings_gin 
                ON invitations USING GIN (settings);
            """,
            reverse_sql="DROP INDEX idx_invitation_settings_gin;"
        ),
    ]
```

### 7.2 쿼리 최적화

```python
# ❌ 나쁜 예: N+1 쿼리
def bad_list_invitations(user_id):
    invitations = Invitation.objects.filter(user_id=user_id)
    
    for inv in invitations:
        print(inv.template.name)  # 매번 DB 조회!
        print(inv.photos.count())  # 매번 DB 조회!

# ✅ 좋은 예: select_related, prefetch_related
def good_list_invitations(user_id):
    invitations = Invitation.objects.filter(
        user_id=user_id
    ).select_related(
        'template'  # ForeignKey JOIN
    ).prefetch_related(
        'photos',  # Reverse ForeignKey
        'guestbook_entries',
        'attendances'
    )
    
    return invitations

# ✅ 더 나은 예: annotate로 집계
from django.db.models import Count, Prefetch

def optimized_list_invitations(user_id):
    invitations = Invitation.objects.filter(
        user_id=user_id
    ).select_related(
        'template'
    ).annotate(
        photo_count=Count('photos'),
        guestbook_count=Count('guestbook_entries'),
        attendance_count=Count('attendances', filter=models.Q(attendances__will_attend=True))
    ).prefetch_related(
        Prefetch(
            'photos',
            queryset=Photo.objects.filter(is_main=True)[:1]  # 메인 사진만
        )
    )
    
    return invitations
```

### 7.3 CDN 및 미디어 최적화

```python
# settings.py

# AWS S3 + CloudFront 설정
if not DEBUG:
    # S3 스토리지
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = 'wedding-invitations'
    AWS_S3_REGION_NAME = 'ap-northeast-2'
    
    # CloudFront CDN
    AWS_S3_CUSTOM_DOMAIN = 'd1234567890.cloudfront.net'
    
    # 미디어 URL
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    # 캐시 설정
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # 1일
    }

# 이미지 최적화
from PIL import Image

def optimize_image(image_file):
    """
    이미지 최적화
    
    1. WebP 변환
    2. 리사이즈 (최대 1920px)
    3. 압축
    """
    img = Image.open(image_file)
    
    # EXIF 회전 처리
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except:
        pass
    
    # 리사이즈 (비율 유지)
    max_size = 1920
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    # WebP 변환
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='WebP', quality=85, optimize=True)
    buffer.seek(0)
    
    return buffer

# Signal로 자동 최적화
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Photo)
def optimize_photo_before_save(sender, instance, **kwargs):
    """사진 저장 전 최적화"""
    if instance.image:
        optimized = optimize_image(instance.image)
        instance.image.save(
            instance.image.name.replace('.jpg', '.webp'),
            optimized,
            save=False
        )
```

### 7.4 멀티테넌시 URL 라우팅

```python
# urls.py
from django.urls import path
from invitations import views

urlpatterns = [
    # 관리 API
    path('api/invitations/', include('invitations.api')),
    
    # 공개 청첩장 (서브도메인 또는 경로)
    # 옵션 1: 경로 기반
    path('wedding/<slug:slug>/', views.invitation_detail, name='invitation_detail'),
    
    # 옵션 2: 서브도메인 (커스텀 미들웨어 필요)
    # john-mary.weddingcard.com
]

# 커스텀 도메인 지원
class CustomDomainMiddleware:
    """
    사용자 커스텀 도메인 지원
    
    예: johnanmary.com → invitation의 slug
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        host = request.get_host().split(':')[0]
        
        # 메인 도메인이 아닌 경우
        if host not in ['weddingcard.com', 'localhost', '127.0.0.1']:
            # 커스텀 도메인 조회
            try:
                from invitations.models import CustomDomain
                custom_domain = CustomDomain.objects.get(domain=host)
                
                # 해당 청첩장으로 리다이렉트
                request.custom_invitation = custom_domain.invitation
            
            except CustomDomain.DoesNotExist:
                pass
        
        response = self.get_response(request)
        return response

# CustomDomain 모델
class CustomDomain(models.Model):
    """사용자 커스텀 도메인"""
    
    invitation = models.OneToOneField(
        'Invitation',
        on_delete=models.CASCADE,
        related_name='custom_domain'
    )
    
    domain = models.CharField(
        max_length=255,
        unique=True,
        help_text="커스텀 도메인 (예: johnanmary.com)"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="DNS 인증 완료 여부"
    )
    
    ssl_enabled = models.BooleanField(
        default=False,
        help_text="SSL 인증서 발급 여부"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'custom_domains'
```

### 7.5 백그라운드 작업 (Celery)

```python
# invitations/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_wedding_reminder(invitation_id):
    """
    결혼식 D-7 리마인더 발송
    
    결혼식 7일 전에 참석 확정자에게 알림
    """
    from .models import Invitation, Attendance
    from .notifications import send_sms
    
    invitation = Invitation.objects.get(id=invitation_id)
    
    # 참석 확정자 목록
    attendees = Attendance.objects.filter(
        invitation=invitation,
        will_attend=True,
        phone_number__isnull=False
    )
    
    for attendee in attendees:
        message = f"""
        [{invitation.get_bride_name()} ❤️ {invitation.get_groom_name()}]
        결혼식이 7일 남았습니다!
        
        📅 {invitation.wedding_date.strftime('%Y년 %m월 %d일 %H시')}
        📍 {invitation.settings['venue']['name']}
        
        청첩장: {invitation.full_url}
        """
        
        send_sms(attendee.phone_number, message)

@shared_task
def generate_thumbnails(photo_id):
    """
    사진 썸네일 생성 (비동기)
    
    여러 사이즈 생성: small(200px), medium(400px), large(800px)
    """
    from .models import Photo
    from PIL import Image
    from io import BytesIO
    from django.core.files.base import ContentFile
    
    photo = Photo.objects.get(id=photo_id)
    
    sizes = {
        'small': 200,
        'medium': 400,
        'large': 800
    }
    
    for name, size in sizes.items():
        img = Image.open(photo.image)
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        # 별도 필드에 저장 또는 파일명으로 구분
        # photo.thumbnail_small, photo.thumbnail_medium 등

@shared_task
def cleanup_old_drafts():
    """
    오래된 임시저장 청첩장 삭제
    
    30일 이상 DRAFT 상태인 청첩장 자동 삭제
    """
    from .models import Invitation
    
    threshold = timezone.now() - timedelta(days=30)
    
    old_drafts = Invitation.objects.filter(
        status=Invitation.Status.DRAFT,
        created_at__lt=threshold
    )
    
    count = old_drafts.count()
    old_drafts.delete()
    
    return f"Deleted {count} old drafts"

@shared_task
def generate_analytics_report(invitation_id):
    """
    통계 리포트 생성
    
    일일/주간/월간 통계 집계
    """
    from .models import Invitation, Analytics
    from django.db.models import Count
    import pandas as pd
    
    invitation = Invitation.objects.get(id=invitation_id)
    
    # 일별 방문자 수
    daily_stats = Analytics.objects.filter(
        invitation=invitation
    ).extra(
        select={'day': 'DATE(visit_date)'}
    ).values('day').annotate(
        visitors=Count('visitor_id', distinct=True),
        views=Count('id')
    ).order_by('day')
    
    # 디바이스별 통계
    device_stats = Analytics.objects.filter(
        invitation=invitation
    ).values('device_type').annotate(
        count=Count('id')
    )
    
    # 유입 경로
    referrer_stats = Analytics.objects.filter(
        invitation=invitation,
        utm_source__isnull=False
    ).values('utm_source', 'utm_medium').annotate(
        count=Count('id')
    )
    
    return {
        'daily': list(daily_stats),
        'devices': list(device_stats),
        'referrers': list(referrer_stats)
    }

# Celery Beat 스케줄링
from celery.schedules import crontab

app.conf.beat_schedule = {
    # 매일 자정 청소
    'cleanup-old-drafts': {
        'task': 'invitations.tasks.cleanup_old_drafts',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # 결혼식 D-7 리마인더 (매일 오전 10시)
    'send-reminders': {
        'task': 'invitations.tasks.check_and_send_reminders',
        'schedule': crontab(hour=10, minute=0),
    },
}
```

---

## 8. 보안 고려사항

### 8.1 개인정보 보호

```python
# 1. 민감 정보 암호화
from django.conf import settings
from cryptography.fernet import Fernet

class EncryptedTextField(models.TextField):
    """암호화된 텍스트 필드"""
    
    def get_prep_value(self, value):
        if value is None:
            return value
        
        # 암호화
        f = Fernet(settings.ENCRYPTION_KEY)
        encrypted = f.encrypt(value.encode())
        return encrypted.decode()
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        
        # 복호화
        f = Fernet(settings.ENCRYPTION_KEY)
        decrypted = f.decrypt(value.encode())
        return decrypted.decode()

# 계좌번호 암호화
class AccountInfo(models.Model):
    account_number = EncryptedTextField()  # 암호화

# 2. 민감 정보 로깅 제외
import logging

class SensitiveDataFilter(logging.Filter):
    """민감 정보 필터링"""
    
    SENSITIVE_KEYS = ['password', 'account_number', 'phone_number']
    
    def filter(self, record):
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            
            # 전화번호 마스킹
            import re
            msg = re.sub(r'\d{3}-\d{4}-\d{4}', '***-****-****', msg)
            
            # 계좌번호 마스킹
            msg = re.sub(r'\d{3}-\d{2}-\d{5}', '***-**-*****', msg)
            
            record.msg = msg
        
        return True

# 3. GDPR 준수 - 개인정보 삭제
def delete_user_data(user_id):
    """
    사용자 탈퇴 시 개인정보 삭제
    
    GDPR의 'Right to be Forgotten' 구현
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.get(id=user_id)
    
    # 청첩장은 익명화 (삭제 X)
    Invitation.objects.filter(user=user).update(
        user=None,  # 익명 사용자로
        status=Invitation.Status.ARCHIVED
    )
    
    # 방명록/참석 정보는 유지 (청첩장 소유자가 아니므로)
    
    # 사용자 계정 삭제
    user.delete()
```

### 8.2 Rate Limiting

```python
# Rate Limiting (django-ratelimit 사용)
from django_ratelimit.decorators import ratelimit

@router.post("/{slug}/guestbook")
@ratelimit(key='ip', rate='5/h', method='POST')  # IP당 시간당 5회
def create_guestbook(request, slug: str, data: GuestBookCreateIn):
    # 제한 초과 시 자동으로 429 반환
    # ...

# 커스텀 Rate Limit
from django.core.cache import cache

def rate_limit_check(key, limit=10, period=3600):
    """
    Rate limit 확인
    
    Args:
        key: 식별자 (IP, user_id 등)
        limit: 제한 횟수
        period: 기간 (초)
    
    Returns:
        bool: 허용 여부
    """
    cache_key = f"rate_limit:{key}"
    current = cache.get(cache_key, 0)
    
    if current >= limit:
        return False
    
    cache.set(cache_key, current + 1, period)
    return True

# API에서 사용
@router.post("/{slug}/attendance")
def submit_attendance(request, slug: str, data: AttendanceCreateIn):
    ip = request.META.get('REMOTE_ADDR')
    
    if not rate_limit_check(f"attendance:{slug}:{ip}", limit=3, period=3600):
        return 429, {"error": "Too many requests. Please try again later."}
    
    # ...
```

### 8.3 XSS 및 CSRF 방지

```python
# 1. XSS 방지 - 사용자 입력 이스케이프
from django.utils.html import escape

class GuestBookCreateIn(Schema):
    message: str
    
    @validator('message')
    def sanitize_message(cls, v):
        # HTML 태그 제거
        import bleach
        allowed_tags = []  # 태그 허용 안함
        cleaned = bleach.clean(v, tags=allowed_tags, strip=True)
        return cleaned

# 2. CSRF 토큰 (Django 기본 제공)
# Django-Ninja는 자동으로 CSRF 체크

# 3. SQL Injection 방지 (ORM 사용으로 자동 방지)
# ❌ 절대 금지
def bad_query(slug):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM invitations WHERE slug = '{slug}'")  # SQL Injection!

# ✅ ORM 사용
def good_query(slug):
    return Invitation.objects.get(slug=slug)  # 파라미터화된 쿼리
```

---

## 9. 테스트 전략

### 9.1 단위 테스트

```python
# invitations/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from invitations.models import Invitation, Template

User = get_user_model()

class InvitationModelTest(TestCase):
    """Invitation 모델 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        self.template = Template.objects.create(
            name='Test Template',
            category='modern',
            is_free=True
        )
    
    def test_slug_auto_generation(self):
        """Slug 자동 생성"""
        invitation = Invitation.objects.create(
            user=self.user,
            template=self.template,
            title='John & Mary Wedding'
        )
        
        self.assertIsNotNone(invitation.slug)
        self.assertIn('john', invitation.slug.lower())
    
    def test_slug_uniqueness(self):
        """Slug 중복 방지"""
        Invitation.objects.create(
            user=self.user,
            template=self.template,
            title='Same Title'
        )
        
        # 같은 제목으로 다시 생성
        invitation2 = Invitation.objects.create(
            user=self.user,
            template=self.template,
            title='Same Title'
        )
        
        # Slug가 달라야 함 (예: same-title, same-title-1)
        self.assertNotEqual(
            Invitation.objects.first().slug,
            invitation2.slug
        )
    
    def test_increment_view(self):
        """조회수 증가"""
        invitation = Invitation.objects.create(
            user=self.user,
            template=self.template,
            title='Test'
        )
        
        initial_count = invitation.view_count
        
        invitation.increment_view()
        invitation.refresh_from_db()
        
        self.assertEqual(invitation.view_count, initial_count + 1)
```

### 9.2 API 테스트

```python
# invitations/tests/test_api.py
from ninja.testing import TestClient
from django.test import TestCase

class InvitationAPITest(TestCase):
    """Invitation API 테스트"""
    
    def setUp(self):
        from invitations.api import router
        self.client = TestClient(router)
        
        # 사용자 및 템플릿 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.template = Template.objects.create(
            name='Test Template',
            is_free=True
        )
    
    def test_create_invitation(self):
        """청첩장 생성 API"""
        response = self.client.post(
            '/',
            json={
                'template_id': self.template.id,
                'title': 'Test Wedding',
                'settings': {
                    'bride': {'name': 'Jane'},
                    'groom': {'name': 'John'}
                }
            },
            # 인증 헤더 (실제로는 JWT)
            headers={'Authorization': f'Bearer {self.get_token()}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('slug', data)
    
    def test_get_invitation_detail(self):
        """청첩장 상세 조회"""
        invitation = Invitation.objects.create(
            user=self.user,
            template=self.template,
            title='Test',
            status=Invitation.Status.PUBLISHED
        )
        
        response = self.client.get(f'/{invitation.slug}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['slug'], invitation.slug)
```

---

## 10. 배포 및 운영

### 10.1 환경 설정

```python
# config/settings/production.py
import os

DEBUG = False

ALLOWED_HOSTS = [
    'weddingcard.com',
    'www.weddingcard.com',
    '*.weddingcard.com',  # 서브도메인
]

# 데이터베이스 (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # 커넥션 풀링
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Redis 캐시
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')

# 보안
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

### 10.2 모니터링

```python
# Sentry 에러 트래킹
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # 10% 트랜잭션 추적
    send_default_pii=False  # 개인정보 전송 안함
)

# 커스텀 메트릭
from prometheus_client import Counter, Histogram

invitation_created = Counter(
    'invitation_created_total',
    'Total invitations created'
)

invitation_view_duration = Histogram(
    'invitation_view_duration_seconds',
    'Time to render invitation'
)

# 사용
@invitation_view_duration.time()
def invitation_detail_view(request, slug):
    invitation_created.inc()
    # ...
```

---

## 결론

### 핵심 설계 원칙 정리

**1. 템플릿과 인스턴스 분리**
- `Template` 모델: 재사용 가능한 디자인
- `Invitation` 모델: 사용자 개인화 데이터
- JSON Schema로 템플릿별 다른 설정 지원

**2. JSON vs 정규화**
- 유연한 커스터마이징: JSONField 사용
- 자주 검색하는 필드: 별도 컬럼 (`wedding_date`, `title`)
- PostgreSQL GIN 인덱스로 JSON 검색 최적화

**3. 멀티테넌시 구조**
- 고유 Slug로 청첩장별 URL (`/wedding/john-mary-2025`)
- UUID Primary Key로 보안 강화
- 커스텀 도메인 지원 가능

**4. 성능 최적화**
- select_related/prefetch_related로 N+1 방지
- Redis 캐싱 (청첩장 조회 5분)
- CDN + WebP로 이미지 최적화
- Celery로 무거운 작업 비동기 처리

**5. 보안**
- 민감 정보 암호화 (계좌번호)
- Rate Limiting (스팸 방지)
- XSS/CSRF/SQL Injection 방어
- GDPR 준수 (개인정보 삭제)

### 확장 가능성

이 구조는 다음으로 확장 가능:
- **돌잔치**, **생일파티**, **이벤트** 청첩장
- **다국어 지원** (i18n)
- **결제 시스템** (프리미엄 템플릿)
- **AI 추천** (사용자 취향 기반 템플릿 추천)
- **실시간 방명록** (WebSocket)

### 추가 학습 자료

- [Django-Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)
- [Multi-Tenancy Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/multi-tenancy)
- [Django Performance Optimization](https://docs.djangoproject.com/en/stable/topics/performance/)

**모바일 청첩장 서비스 구축 화이팅!** 💒💐

