---
layout: post
title: "Django-Ninja로 구축하는 모바일 청첩장 서비스 - 데이터 구조 설계"
categories: [Django, Backend]
tags: [django-ninja, wedding-invitation, data-structure, multi-tenancy, template-system, postgresql, jsonfield]
date: 2025-11-27 09:00:00 +0900
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

