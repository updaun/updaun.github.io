---
layout: post
title: "Shopify 결제와 Django 웹훅으로 모바일 청첩장 SaaS 구축하기"
date: 2025-11-11 09:00:00 +0900
categories: [Django, E-commerce, Backend]
tags: [shopify, django, webhook, saas, mobile-wedding-invitation, payment-integration]
description: "Shopify에서 상품 판매 후 Django 서버로 웹훅을 전송하여 모바일 청첩장 배포 권한을 자동으로 제공하는 SaaS 서비스 구축 완벽 가이드. 실시간 결제 검증부터 라이선스 관리까지."
---

## 1. 서론

### 1.1 프로젝트 개요

온라인으로 모바일 청첩장 템플릿을 판매하고, 구매 즉시 고객에게 청첩장 제작 권한을 자동으로 부여하는 SaaS 서비스를 구축합니다.

**비즈니스 플로우:**
```
1. 고객이 Shopify 스토어에서 청첩장 템플릿 구매
2. Shopify가 주문 완료 웹훅을 Django 서버로 전송
3. Django가 주문 검증 및 라이선스 생성
4. 고객 이메일로 접속 정보 발송
5. 모바일 앱/웹에서 청첩장 제작 및 배포
```

**왜 이 구조인가?**

🛒 **Shopify 선택 이유:**
- 글로벌 결제 인프라 (135개 통화)
- PCI DSS 인증 완료 (보안 처리 불필요)
- 재고 관리, 쿠폰, 배송 자동화
- 강력한 관리자 대시보드
- 개발 리소스를 비즈니스 로직에 집중

⚡ **Django 백엔드 선택 이유:**
- 청첩장 데이터 관리 (ORM)
- 복잡한 비즈니스 로직 처리
- RESTful API 제공
- 사용자 인증 및 권한 관리
- 확장 가능한 아키텍처

### 1.2 시스템 아키텍처

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   고객      │ 구매 →  │   Shopify    │ 웹훅 →  │   Django    │
│             │         │   스토어     │         │   서버      │
└─────────────┘         └──────────────┘         └─────────────┘
                               ↓                        ↓
                        Order Created              License 생성
                        Payment Success            DB 저장
                                                   Email 발송
                                                        ↓
                                                   ┌─────────────┐
                                                   │  Mobile App │
                                                   │  청첩장 생성 │
                                                   └─────────────┘
```

**핵심 컴포넌트:**

1. **Shopify Store**
   - 상품 등록 (청첩장 템플릿)
   - 결제 처리
   - 웹훅 발송

2. **Django Backend**
   - 웹훅 수신 및 검증
   - 주문 데이터 처리
   - 라이선스 발급
   - REST API 제공

3. **PostgreSQL Database**
   - 주문 내역
   - 라이선스 정보
   - 청첩장 데이터
   - 사용자 정보

4. **Mobile Client** (React Native/Flutter)
   - 라이선스 인증
   - 청첩장 제작 UI
   - 실시간 미리보기
   - 공유 기능

### 1.3 주요 기능

**자동화 프로세스:**
- ✅ Shopify 결제 완료 시 실시간 웹훅
- ✅ HMAC 서명 검증으로 보안 보장
- ✅ 라이선스 자동 생성 및 활성화
- ✅ 이메일 자동 발송 (접속 정보)
- ✅ 만료일 관리 (구독형/영구 라이선스)

**라이선스 관리:**
- 📝 1회 구매 / 구독형 라이선스
- 🔐 고유 라이선스 키 발급
- ⏰ 만료일 자동 체크
- 🔄 갱신 및 업그레이드
- 📊 사용 통계 추적

**청첩장 서비스:**
- 🎨 템플릿 기반 청첩장 생성
- 📱 모바일 최적화 뷰
- 🔗 고유 URL 발급 (예: yourdomain.com/wedding/abc123)
- 💾 클라우드 이미지 호스팅
- 📅 D-day 카운트다운
- 📍 지도 연동 (카카오맵/구글맵)
- 💌 게스트 방명록

### 1.4 기술 스택

**Backend:**
```
- Python 3.11+
- Django 5.0
- Django REST Framework 3.14
- PostgreSQL 15
- Celery + Redis (비동기 작업)
- Gunicorn + Nginx (프로덕션)
```

**Shopify Integration:**
```
- Shopify Admin API
- Webhooks (Order Creation, Payment)
- HMAC Signature Verification
```

**Infrastructure:**
```
- AWS EC2 / DigitalOcean
- AWS S3 (이미지 저장)
- CloudFront (CDN)
- Route53 (DNS)
- Let's Encrypt (SSL)
```

**Mobile (예정):**
```
- React Native / Flutter
- REST API 통신
- JWT 인증
```

### 1.5 예상 비용 구조

**Shopify:**
```
Basic Plan: $39/month
- 무제한 상품
- 2% 거래 수수료 (Shopify Payments 사용 시 면제)
- 신용카드 수수료: 2.9% + $0.30
```

**AWS (초기 규모):**
```
EC2 t3.small: $17/month
RDS PostgreSQL: $25/month
S3 Storage: $0.023/GB
CloudFront: $0.085/GB (첫 10TB)
```

**개발 도구:**
```
무료: Django, DRF, PostgreSQL, Redis
```

총 초기 비용: 약 $100-150/month

### 1.6 이 글에서 다룰 내용

각 단계별로 실제 구현 코드와 함께 진행합니다:

1. ✅ **Shopify 스토어 설정** - 개발자 앱 생성, 웹훅 설정
2. ✅ **Django 프로젝트 구성** - 모델 설계, 프로젝트 구조
3. ✅ **웹훅 수신 구현** - HMAC 검증, 주문 데이터 파싱
4. ✅ **라이선스 시스템** - 자동 발급, 만료 관리
5. ✅ **청첩장 API** - CRUD, 권한 검증
6. ✅ **모바일 연동** - API 인증, 데이터 동기화
7. ✅ **테스트 & 배포** - 프로덕션 배포, 모니터링
8. ✅ **보안 & 최적화** - Rate limiting, 캐싱, 에러 핸들링

**실습 결과물:**
- 완전히 작동하는 SaaS 서비스
- Shopify와 실시간 연동
- 모바일 앱 지원 준비 완료
- 프로덕션 배포 가능한 코드

시작하겠습니다! 🚀

## 2. Shopify 스토어 설정

### 2.1 Shopify 개발자 계정 생성

**1) Partner 계정 등록**

Shopify Partner 프로그램에 가입하여 개발 스토어를 무료로 생성할 수 있습니다.

```
1. https://partners.shopify.com 접속
2. "Join Now" 클릭
3. 이메일 가입 또는 Google 로그인
4. 개발자 정보 입력:
   - Account Type: Development stores
   - Primary Focus: Building apps
```

**2) 개발 스토어 생성**

Partner Dashboard → Stores → Add store

```
Store details:
- Store name: wedding-invitation-shop
- Store URL: wedding-invitation-shop.myshopify.com
- Login information: 자동 생성됨
- Purpose: Development store
```

⚠️ **주의**: 개발 스토어는 실제 결제가 불가능합니다. 테스트용 Bogus Gateway를 사용합니다.

**3) 프로덕션 스토어 (실제 판매용)**

실제 비즈니스를 위해서는 정식 Shopify 플랜이 필요합니다:

```
1. https://www.shopify.com 접속
2. "Start free trial" 클릭 (3일 무료 체험)
3. 스토어 정보 입력
4. Basic Plan ($39/month) 선택
5. Shopify Payments 활성화 (한국 지원)
```

### 2.2 상품 등록 (청첩장 템플릿)

**1) 상품 카테고리 구조**

```
청첩장 템플릿
├── 모던 스타일 ($29)
├── 클래식 스타일 ($29)
├── 미니멀 스타일 ($29)
└── 프리미엄 패키지 ($99)
    - 모든 템플릿 이용 가능
    - 우선 고객 지원
```

**2) 상품 등록 방법**

Shopify Admin → Products → Add product

```yaml
# 예시: 모던 스타일 청첩장
Title: "모던 스타일 모바일 청첩장"

Description: |
  심플하고 세련된 디자인의 모바일 청첩장입니다.
  
  포함 기능:
  - 커스터마이징 가능한 템플릿
  - 사진 갤러리 (최대 30장)
  - 지도 및 교통 안내
  - 방명록 기능
  - D-day 카운터
  - 모바일 최적화
  
  구매 후 즉시 이메일로 접속 정보가 전송됩니다.

Price: $29.00
Compare at price: $49.00 (할인 표시용)

SKU: MOD-WEDDING-001
Barcode: (비워둠)

Inventory:
  Track quantity: No (디지털 상품)
  Continue selling when out of stock: Yes

Shipping:
  This is a physical product: No (디지털 상품)

Product type: Digital Products
Vendor: Your Brand
Collections: 청첩장, 인기상품

Tags: wedding, invitation, mobile, digital, korean
```

**3) 상품 메타데이터 추가 (중요!)**

Metafields를 사용하여 라이선스 정보를 저장합니다:

```
Settings → Custom data → Products → Add definition

Metafield name: license_type
Namespace: custom
Type: Single line text
Values: 
  - "single_use" (1회 사용)
  - "subscription" (구독형)
  - "unlimited" (무제한)

Metafield name: validity_days
Namespace: custom  
Type: Integer
Description: 라이선스 유효 기간 (일)
```

각 상품 편집 시 메타필드 설정:

```
모던 스타일: license_type = "single_use", validity_days = 365
프리미엄 패키지: license_type = "unlimited", validity_days = 0
```

### 2.3 Shopify App 생성

Django와 통신하기 위한 Private App을 생성합니다.

**1) App 생성**

Shopify Admin → Settings → Apps and sales channels → Develop apps → Create an app

```
App name: Wedding Invitation Service
App developer: your-email@example.com
```

**2) API 권한 설정**

Configure Admin API scopes:

```
필수 권한:
✓ read_orders (주문 읽기)
✓ write_orders (주문 수정)
✓ read_products (상품 읽기)
✓ read_customers (고객 읽기)

선택 권한:
✓ read_inventory (재고)
✓ read_fulfillments (배송)
```

Save → Install app

**3) API 자격 증명 확인**

```bash
# Admin API access token
shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# API key
xxxxxxxxxxxxxxxxxxxxxxxxxxx

# API secret key
shpss_xxxxxxxxxxxxxxxxxxxxxxxxxxx

# Storefront API access token (선택)
xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **중요**: Admin API access token을 안전하게 보관하세요!

### 2.4 웹훅 설정

**1) 웹훅 엔드포인트 결정**

Django 서버의 웹훅 수신 URL:

```
개발 환경: http://localhost:8000/api/webhooks/shopify/
프로덕션: https://yourdomain.com/api/webhooks/shopify/
```

개발 시에는 ngrok를 사용하여 로컬 서버를 외부에 노출:

```bash
# ngrok 설치
brew install ngrok  # macOS
# 또는 https://ngrok.com/download

# ngrok 실행
ngrok http 8000

# 출력된 HTTPS URL 사용
# https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app
```

**2) 웹훅 등록 (Admin 대시보드)**

Settings → Notifications → Webhooks → Create webhook

**주문 생성 웹훅:**
```
Event: Order creation
Format: JSON
URL: https://yourdomain.com/api/webhooks/shopify/order-create
Webhook API version: 2024-10 (최신 버전)
```

**결제 완료 웹훅:**
```
Event: Order payment
Format: JSON  
URL: https://yourdomain.com/api/webhooks/shopify/order-paid
```

**3) 웹훅 등록 (API 사용 - 권장)**

나중에 Django 코드에서 자동으로 등록하는 방법도 다룹니다.

```python
# 미리보기 - 나중에 구현
import requests

def register_webhook():
    url = f"https://{shop_domain}/admin/api/2024-10/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    webhook_data = {
        "webhook": {
            "topic": "orders/create",
            "address": "https://yourdomain.com/api/webhooks/shopify/order-create",
            "format": "json"
        }
    }
    
    response = requests.post(url, headers=headers, json=webhook_data)
    return response.json()
```

### 2.5 Shopify Payments 설정 (프로덕션)

**1) 결제 게이트웨이 활성화**

Settings → Payments → Shopify Payments → Complete account setup

```
비즈니스 정보:
- Legal business name
- Business address
- Tax ID (사업자등록번호)
- Bank account details

신원 확인:
- 대표자 이름
- 생년월일
- 주소
- 신분증 업로드
```

**2) 지원 결제 수단**

한국에서 사용 가능한 결제 수단:

```
신용카드:
✓ Visa
✓ Mastercard
✓ American Express

디지털 지갑:
✓ Apple Pay
✓ Google Pay
✓ Shop Pay

대체 결제:
✓ PayPal (별도 연동 필요)
```

**3) 수수료 구조 (한국 기준)**

```
Shopify Payments 수수료:
- Domestic card: 2.9% + ₩300
- International card: 3.4% + ₩300

Plan 거래 수수료:
- Basic Plan: 2.0% (Shopify Payments 미사용 시)
- Using Shopify Payments: 0% ✅
```

### 2.6 테스트 결제 설정

**1) Bogus Gateway 활성화 (개발 스토어)**

개발 스토어에서 자동으로 활성화됨:

```
Settings → Payments → Bogus Gateway
Status: Enabled
```

**2) 테스트 카드 번호**

```
성공 케이스:
  카드 번호: 1
  이름: Bogus Gateway
  만료일: 미래 날짜
  CVV: 아무 숫자

실패 케이스:
  카드 번호: 2 (카드 거부)
  카드 번호: 3 (처리 에러)
```

**3) 테스트 주문 생성**

```
1. 스토어 프론트엔드 접속
   https://wedding-invitation-shop.myshopify.com

2. 상품을 장바구니에 추가

3. Checkout 진행
   - 고객 정보 입력
   - 배송 주소 (디지털 상품이므로 스킵 가능)
   - 결제 정보 입력 (카드 번호: 1)

4. 주문 완료

5. Shopify Admin에서 주문 확인
   Orders → 최근 주문 확인

6. 웹훅 전송 확인 (나중에 Django에서 수신)
```

### 2.7 Shopify Admin API 테스트

API가 정상 작동하는지 확인합니다:

```bash
# 주문 목록 조회
curl -X GET \
  "https://your-shop.myshopify.com/admin/api/2024-10/orders.json?status=any" \
  -H "X-Shopify-Access-Token: shpat_your_token_here"

# 응답 예시
{
  "orders": [
    {
      "id": 5678901234567,
      "email": "customer@example.com",
      "created_at": "2025-11-11T12:00:00Z",
      "total_price": "29.00",
      "currency": "USD",
      "line_items": [
        {
          "id": 12345678901234567,
          "title": "모던 스타일 모바일 청첩장",
          "quantity": 1,
          "price": "29.00",
          "sku": "MOD-WEDDING-001"
        }
      ],
      "customer": {
        "id": 6789012345678,
        "email": "customer@example.com",
        "first_name": "길동",
        "last_name": "홍"
      }
    }
  ]
}
```

### 2.8 환경 변수 정리

Shopify 관련 설정을 정리합니다:

```bash
# .env 파일
SHOPIFY_SHOP_DOMAIN=your-shop.myshopify.com
SHOPIFY_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxx
SHOPIFY_API_SECRET=shpss_xxxxxxxxxxxxxxxxxxxxxxxxxxx
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SHOPIFY_WEBHOOK_SECRET=  # 나중에 자동 생성됨
SHOPIFY_API_VERSION=2024-10
```

⚠️ **보안 주의사항:**

```bash
# .gitignore에 추가
.env
*.env.local
*.env.production
```

절대 Git에 커밋하지 마세요!

### 2.9 Shopify GraphQL Admin API (선택)

REST API 대신 GraphQL을 사용할 수도 있습니다:

```graphql
# 주문 조회 쿼리 예시
query {
  orders(first: 10, query: "financial_status:paid") {
    edges {
      node {
        id
        name
        email
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 10) {
          edges {
            node {
              title
              quantity
              variant {
                sku
              }
            }
          }
        }
      }
    }
  }
}
```

이 튜토리얼에서는 REST API를 사용하지만, GraphQL이 더 효율적인 경우가 많습니다.

Shopify 설정이 완료되었습니다! 다음 섹션에서는 Django 프로젝트를 설정하겠습니다.

## 3. Django 프로젝트 기본 설정

### 3.1 프로젝트 구조

완성될 프로젝트 구조입니다:

```
wedding_invitation_service/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── utils.py
│   ├── shopify_integration/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── webhooks.py
│   │   ├── api.py
│   │   └── tasks.py
│   ├── licenses/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── api.py
│   │   └── permissions.py
│   └── invitations/
│       ├── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── api.py
│       ├── permissions.py
│       └── views.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── media/
│   └── invitations/
│       └── photos/
└── templates/
    └── invitations/
        └── preview.html
```

### 3.2 환경 설정

**1) 가상환경 생성**

```bash
# 프로젝트 디렉토리 생성
mkdir wedding_invitation_service
cd wedding_invitation_service

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# pip 업그레이드
pip install --upgrade pip
```

**2) Django 프로젝트 생성**

```bash
# Django 설치
pip install django

# 프로젝트 생성
django-admin startproject config .

# 앱 생성
python manage.py startapp apps/core
python manage.py startapp apps/shopify_integration
python manage.py startapp apps/licenses
python manage.py startapp apps/invitations
```

**3) 필수 패키지 설치**

```bash
pip install django djangorestframework django-cors-headers \
    python-dotenv psycopg2-binary pillow celery redis \
    requests pyjwt cryptography
```

### 3.3 requirements.txt

```txt
# Core Django
Django==5.0.0
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-environ==0.11.2

# Database
psycopg2-binary==2.9.9

# Task Queue
celery==5.3.4
redis==5.0.1

# Image Processing
Pillow==10.1.0

# HTTP & API
requests==2.31.0
httpx==0.25.2

# Security & Auth
PyJWT==2.8.0
cryptography==41.0.7
python-dotenv==1.0.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Development
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
faker==21.0.0
black==23.12.1
flake8==6.1.0

# Production
gunicorn==21.2.0
whitenoise==6.6.0
sentry-sdk==1.39.1
```

설치:

```bash
pip install -r requirements.txt
```

### 3.4 환경 변수 설정

**.env 파일 생성:**

```bash
# Django
DEBUG=True
SECRET_KEY=your-super-secret-key-change-this-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings

# Database
DATABASE_URL=postgresql://wedding_user:wedding_password@localhost:5432/wedding_db
# 또는 개발 시 SQLite:
# DATABASE_URL=sqlite:///db.sqlite3

# Shopify
SHOPIFY_SHOP_DOMAIN=your-shop.myshopify.com
SHOPIFY_API_KEY=your_api_key_here
SHOPIFY_API_SECRET=your_api_secret_here
SHOPIFY_ACCESS_TOKEN=your_access_token_here
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret_here
SHOPIFY_API_VERSION=2024-10

# Celery & Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (SendGrid / AWS SES)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# AWS S3 (이미지 저장)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=wedding-invitations
AWS_S3_REGION_NAME=ap-northeast-2

# Frontend URL
FRONTEND_URL=https://yourdomain.com
INVITATION_BASE_URL=https://yourdomain.com/wedding/

# Logging
LOG_LEVEL=INFO

# Sentry (에러 모니터링)
SENTRY_DSN=your_sentry_dsn_here
```

**.gitignore:**

```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# Django
*.log
db.sqlite3
db.sqlite3-journal
media/
staticfiles/

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Secrets
secrets.json
*.pem
*.key
```

### 3.5 settings.py 설정

```python
# config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'apps.core',
    'apps.shopify_integration',
    'apps.licenses',
    'apps.invitations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'wedding_db'),
        'USER': os.getenv('DB_USER', 'wedding_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# 개발 시 SQLite 사용
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.licenses.authentication.LicenseKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True

# Shopify Settings
SHOPIFY_SHOP_DOMAIN = os.getenv('SHOPIFY_SHOP_DOMAIN')
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOPIFY_WEBHOOK_SECRET = os.getenv('SHOPIFY_WEBHOOK_SECRET')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2024-10')

# Celery Settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Email Settings
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# AWS S3 Settings (프로덕션)
USE_S3 = os.getenv('USE_S3', 'False') == 'True'

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL = 'public-read'
    
    # Static & Media files
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Invitation Settings
INVITATION_BASE_URL = os.getenv('INVITATION_BASE_URL', 'http://localhost:8000/wedding/')
MAX_INVITATION_PHOTOS = 30
MAX_PHOTO_SIZE_MB = 5

# License Settings
DEFAULT_LICENSE_VALIDITY_DAYS = 365
LICENSE_KEY_LENGTH = 32

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    }
}

# Sentry (프로덕션 에러 모니터링)
if not DEBUG and os.getenv('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment='production' if not DEBUG else 'development',
    )

# Security Settings (프로덕션)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

### 3.6 Celery 설정

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('wedding_invitation_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 3.7 URL 설정

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/webhooks/', include('apps.shopify_integration.urls')),
    path('api/licenses/', include('apps.licenses.urls')),
    path('api/invitations/', include('apps.invitations.urls')),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### 3.8 데이터베이스 설정

**PostgreSQL 설치 (프로덕션용):**

```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# 데이터베이스 생성
psql postgres
CREATE DATABASE wedding_db;
CREATE USER wedding_user WITH PASSWORD 'wedding_password';
GRANT ALL PRIVILEGES ON DATABASE wedding_db TO wedding_user;
\q
```

**개발 시에는 SQLite로 시작:**

```bash
# settings.py에 이미 설정됨
# DEBUG=True일 때 자동으로 SQLite 사용
```

### 3.9 초기 마이그레이션

```bash
# logs 디렉토리 생성
mkdir logs

# 마이그레이션 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 3.10 개발 서버 실행

```bash
# Django 서버 실행
python manage.py runserver

# 다른 터미널에서 Celery 실행
celery -A config worker -l info

# 다른 터미널에서 Redis 실행 (macOS)
redis-server
```

접속:
- Django Admin: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/

기본 설정이 완료되었습니다! 다음 섹션에서는 데이터 모델을 설계하겠습니다.

## 4. Shopify 웹훅 수신 구현

이제 Shopify로부터 주문 완료 알림을 받는 핵심 기능을 구현합니다.

### 4.1 데이터 모델 설계

먼저 필요한 모델들을 정의합니다.

```python
# apps/shopify_integration/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid


class ShopifyCustomer(models.Model):
    """Shopify 고객 정보"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopify_customer'
    )
    
    # Shopify 정보
    shopify_customer_id = models.BigIntegerField(unique=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    
    # 메타데이터
    orders_count = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopify_customers'
        verbose_name = 'Shopify 고객'
        verbose_name_plural = 'Shopify 고객'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['shopify_customer_id']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.shopify_customer_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class ShopifyOrder(models.Model):
    """Shopify 주문 정보"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        AUTHORIZED = 'authorized', '승인됨'
        PAID = 'paid', '결제완료'
        PARTIALLY_PAID = 'partially_paid', '부분결제'
        REFUNDED = 'refunded', '환불'
        VOIDED = 'voided', '취소'
        PARTIALLY_REFUNDED = 'partially_refunded', '부분환불'
    
    class FulfillmentStatus(models.TextChoices):
        FULFILLED = 'fulfilled', '배송완료'
        NULL = 'null', '미배송'
        PARTIAL = 'partial', '부분배송'
        RESTOCKED = 'restocked', '재입고'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 고객 정보
    customer = models.ForeignKey(
        ShopifyCustomer,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Shopify 정보
    shopify_order_id = models.BigIntegerField(unique=True)
    shopify_order_number = models.IntegerField()
    order_name = models.CharField(max_length=50)  # #1001
    
    # 주문 상세
    email = models.EmailField()
    financial_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.NULL
    )
    
    # 금액
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_discounts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # 원본 데이터
    raw_data = models.JSONField(default=dict)
    
    # 처리 상태
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # 타임스탬프
    shopify_created_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopify_orders'
        ordering = ['-shopify_created_at']
        indexes = [
            models.Index(fields=['shopify_order_id']),
            models.Index(fields=['email']),
            models.Index(fields=['financial_status']),
            models.Index(fields=['is_processed']),
        ]
    
    def __str__(self):
        return f"{self.order_name} - {self.email} - ${self.total_price}"


class ShopifyOrderLineItem(models.Model):
    """주문 상품 항목"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(
        ShopifyOrder,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    
    # Shopify 정보
    shopify_line_item_id = models.BigIntegerField(unique=True)
    shopify_product_id = models.BigIntegerField()
    shopify_variant_id = models.BigIntegerField()
    
    # 상품 정보
    title = models.CharField(max_length=255)
    variant_title = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=100, blank=True)
    
    # 수량 및 가격
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # 메타데이터 (라이선스 타입 등)
    properties = models.JSONField(default=dict)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shopify_order_line_items'
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['shopify_product_id']),
        ]
    
    def __str__(self):
        return f"{self.title} x {self.quantity}"


class ShopifyWebhook(models.Model):
    """웹훅 이벤트 로그"""
    
    class Status(models.TextChoices):
        RECEIVED = 'received', '수신'
        PROCESSING = 'processing', '처리중'
        PROCESSED = 'processed', '처리완료'
        FAILED = 'failed', '실패'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 웹훅 정보
    topic = models.CharField(max_length=100)  # orders/create, orders/paid
    shopify_domain = models.CharField(max_length=255)
    
    # 이벤트 데이터
    payload = models.JSONField()
    headers = models.JSONField(default=dict)
    
    # 처리 상태
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # 타임스탬프
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'shopify_webhooks'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['topic']),
            models.Index(fields=['status']),
            models.Index(fields=['-received_at']),
        ]
    
    def __str__(self):
        return f"{self.topic} - {self.status} - {self.received_at}"
```

마이그레이션:

```bash
python manage.py makemigrations shopify_integration
python manage.py migrate
```

### 4.2 HMAC 서명 검증

Shopify 웹훅의 진위를 확인하는 HMAC 검증 함수:

```python
# apps/shopify_integration/services.py
import hmac
import hashlib
import base64
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def verify_shopify_webhook(data, hmac_header):
    """
    Shopify 웹훅 HMAC 서명 검증
    
    Args:
        data: 요청 본문 (bytes)
        hmac_header: X-Shopify-Hmac-SHA256 헤더 값
        
    Returns:
        bool: 검증 성공 여부
    """
    secret = settings.SHOPIFY_WEBHOOK_SECRET.encode('utf-8')
    
    # HMAC 계산
    computed_hmac = base64.b64encode(
        hmac.new(secret, data, hashlib.sha256).digest()
    ).decode('utf-8')
    
    # 비교
    is_valid = hmac.compare_digest(computed_hmac, hmac_header)
    
    if not is_valid:
        logger.warning(f"Invalid HMAC signature. Expected: {computed_hmac}, Got: {hmac_header}")
    
    return is_valid


def extract_webhook_headers(request):
    """
    웹훅 요청에서 중요한 헤더 추출
    
    Returns:
        dict: 헤더 정보
    """
    return {
        'hmac': request.headers.get('X-Shopify-Hmac-SHA256'),
        'topic': request.headers.get('X-Shopify-Topic'),
        'domain': request.headers.get('X-Shopify-Shop-Domain'),
        'api_version': request.headers.get('X-Shopify-API-Version'),
        'webhook_id': request.headers.get('X-Shopify-Webhook-Id'),
    }
```

### 4.3 웹훅 핸들러 구현

```python
# apps/shopify_integration/webhooks.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
import json
import logging

from .models import (
    ShopifyWebhook,
    ShopifyCustomer,
    ShopifyOrder,
    ShopifyOrderLineItem
)
from .services import verify_shopify_webhook, extract_webhook_headers
from .tasks import process_order_paid

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def shopify_webhook_handler(request):
    """
    Shopify 웹훅 통합 핸들러
    """
    # 요청 본문 읽기
    try:
        body = request.body
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return HttpResponse("Invalid JSON", status=400)
    
    # 헤더 추출
    headers = extract_webhook_headers(request)
    hmac_header = headers.get('hmac')
    topic = headers.get('topic')
    
    # HMAC 검증
    if not verify_shopify_webhook(body, hmac_header):
        logger.error("HMAC verification failed")
        return HttpResponse("Unauthorized", status=401)
    
    # 웹훅 로그 저장
    webhook_log = ShopifyWebhook.objects.create(
        topic=topic,
        shopify_domain=headers.get('domain'),
        payload=data,
        headers=headers,
        status=ShopifyWebhook.Status.RECEIVED
    )
    
    logger.info(f"Received webhook: {topic} - ID: {webhook_log.id}")
    
    # 토픽별 처리
    try:
        if topic == 'orders/create':
            handle_order_create(data, webhook_log)
        elif topic == 'orders/paid':
            handle_order_paid(data, webhook_log)
        elif topic == 'orders/cancelled':
            handle_order_cancelled(data, webhook_log)
        elif topic == 'refunds/create':
            handle_refund_create(data, webhook_log)
        else:
            logger.info(f"Unhandled webhook topic: {topic}")
    
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_log.id}: {str(e)}")
        webhook_log.status = ShopifyWebhook.Status.FAILED
        webhook_log.error_message = str(e)
        webhook_log.save()
        return HttpResponse("Processing failed", status=500)
    
    # 성공 응답 (Shopify는 200 OK를 기대)
    return HttpResponse("OK", status=200)


def handle_order_create(data, webhook_log):
    """
    주문 생성 이벤트 처리
    """
    logger.info(f"Processing order/create: {data.get('id')}")
    
    with transaction.atomic():
        # 고객 정보 생성/업데이트
        customer_data = data.get('customer', {})
        customer, created = get_or_create_customer(customer_data)
        
        # 주문 정보 저장
        order = create_or_update_order(data, customer)
        
        # 주문 항목 저장
        for item_data in data.get('line_items', []):
            create_order_line_item(item_data, order)
        
        webhook_log.status = ShopifyWebhook.Status.PROCESSED
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        
        logger.info(f"Order created: {order.order_name}")


def handle_order_paid(data, webhook_log):
    """
    결제 완료 이벤트 처리 (가장 중요!)
    
    이 시점에 라이선스를 발급합니다.
    """
    logger.info(f"Processing order/paid: {data.get('id')}")
    
    with transaction.atomic():
        # 고객 정보
        customer_data = data.get('customer', {})
        customer, _ = get_or_create_customer(customer_data)
        
        # 주문 정보 업데이트
        order = create_or_update_order(data, customer)
        order.financial_status = ShopifyOrder.Status.PAID
        order.save()
        
        # 주문 항목 저장
        for item_data in data.get('line_items', []):
            create_order_line_item(item_data, order)
        
        webhook_log.status = ShopifyWebhook.Status.PROCESSING
        webhook_log.save()
    
    # 비동기로 라이선스 발급 (Celery)
    process_order_paid.delay(order.id)
    
    webhook_log.status = ShopifyWebhook.Status.PROCESSED
    webhook_log.processed_at = timezone.now()
    webhook_log.save()
    
    logger.info(f"Order paid: {order.order_name}")


def handle_order_cancelled(data, webhook_log):
    """
    주문 취소 이벤트 처리
    """
    shopify_order_id = data.get('id')
    
    try:
        order = ShopifyOrder.objects.get(shopify_order_id=shopify_order_id)
        order.financial_status = ShopifyOrder.Status.VOIDED
        order.save()
        
        # TODO: 라이선스 비활성화
        
        webhook_log.status = ShopifyWebhook.Status.PROCESSED
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        
        logger.info(f"Order cancelled: {order.order_name}")
        
    except ShopifyOrder.DoesNotExist:
        logger.warning(f"Order not found: {shopify_order_id}")


def handle_refund_create(data, webhook_log):
    """
    환불 이벤트 처리
    """
    order_id = data.get('order_id')
    
    try:
        order = ShopifyOrder.objects.get(shopify_order_id=order_id)
        order.financial_status = ShopifyOrder.Status.REFUNDED
        order.save()
        
        # TODO: 라이선스 비활성화
        
        webhook_log.status = ShopifyWebhook.Status.PROCESSED
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        
        logger.info(f"Refund processed for order: {order.order_name}")
        
    except ShopifyOrder.DoesNotExist:
        logger.warning(f"Order not found: {order_id}")


# Helper Functions

def get_or_create_customer(customer_data):
    """
    Shopify 고객 정보 생성/업데이트
    """
    if not customer_data or not customer_data.get('id'):
        return None, False
    
    shopify_customer_id = customer_data['id']
    email = customer_data.get('email', '')
    
    customer, created = ShopifyCustomer.objects.update_or_create(
        shopify_customer_id=shopify_customer_id,
        defaults={
            'email': email,
            'first_name': customer_data.get('first_name', ''),
            'last_name': customer_data.get('last_name', ''),
            'phone': customer_data.get('phone', ''),
            'orders_count': customer_data.get('orders_count', 0),
            'total_spent': customer_data.get('total_spent', 0),
        }
    )
    
    return customer, created


def create_or_update_order(order_data, customer):
    """
    Shopify 주문 정보 생성/업데이트
    """
    shopify_order_id = order_data['id']
    
    order, created = ShopifyOrder.objects.update_or_create(
        shopify_order_id=shopify_order_id,
        defaults={
            'customer': customer,
            'shopify_order_number': order_data.get('order_number'),
            'order_name': order_data.get('name'),
            'email': order_data.get('email'),
            'financial_status': order_data.get('financial_status', 'pending'),
            'fulfillment_status': order_data.get('fulfillment_status') or 'null',
            'total_price': order_data.get('total_price', 0),
            'subtotal_price': order_data.get('subtotal_price', 0),
            'total_tax': order_data.get('total_tax', 0),
            'total_discounts': order_data.get('total_discounts', 0),
            'currency': order_data.get('currency', 'USD'),
            'raw_data': order_data,
            'shopify_created_at': order_data.get('created_at'),
        }
    )
    
    return order


def create_order_line_item(item_data, order):
    """
    주문 항목 생성/업데이트
    """
    shopify_line_item_id = item_data['id']
    
    line_item, created = ShopifyOrderLineItem.objects.update_or_create(
        shopify_line_item_id=shopify_line_item_id,
        defaults={
            'order': order,
            'shopify_product_id': item_data.get('product_id', 0),
            'shopify_variant_id': item_data.get('variant_id', 0),
            'title': item_data.get('title', ''),
            'variant_title': item_data.get('variant_title', ''),
            'sku': item_data.get('sku', ''),
            'quantity': item_data.get('quantity', 1),
            'price': item_data.get('price', 0),
            'total_discount': item_data.get('total_discount', 0),
            'properties': item_data.get('properties', {}),
        }
    )
    
    return line_item
```

### 4.4 Celery 비동기 작업

```python
# apps/shopify_integration/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_order_paid(order_id):
    """
    결제 완료 주문 처리 (비동기)
    
    1. 라이선스 생성
    2. 이메일 발송
    3. 주문 처리 완료 표시
    """
    from .models import ShopifyOrder
    from apps.licenses.services import LicenseService
    
    try:
        order = ShopifyOrder.objects.get(id=order_id)
        
        # 이미 처리된 주문은 스킵
        if order.is_processed:
            logger.info(f"Order {order.order_name} already processed")
            return
        
        logger.info(f"Processing paid order: {order.order_name}")
        
        # 각 주문 항목에 대해 라이선스 생성
        license_service = LicenseService()
        licenses = []
        
        for line_item in order.line_items.all():
            # SKU로 라이선스 타입 결정
            license_type = determine_license_type(line_item.sku)
            validity_days = determine_validity_days(line_item.sku)
            
            # 라이선스 생성
            license = license_service.create_license_from_order(
                order=order,
                line_item=line_item,
                license_type=license_type,
                validity_days=validity_days
            )
            
            licenses.append(license)
            logger.info(f"Created license: {license.license_key}")
        
        # 이메일 발송
        send_license_email(order, licenses)
        
        # 주문 처리 완료
        order.is_processed = True
        order.processed_at = timezone.now()
        order.save()
        
        logger.info(f"Order {order.order_name} processed successfully")
        
    except ShopifyOrder.DoesNotExist:
        logger.error(f"Order not found: {order_id}")
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {str(e)}")
        raise


def determine_license_type(sku):
    """
    SKU로부터 라이선스 타입 결정
    """
    if 'PREMIUM' in sku.upper():
        return 'unlimited'
    elif 'SUBSCRIPTION' in sku.upper():
        return 'subscription'
    else:
        return 'single_use'


def determine_validity_days(sku):
    """
    SKU로부터 유효 기간 결정
    """
    if 'PREMIUM' in sku.upper() or 'UNLIMITED' in sku.upper():
        return 0  # 무제한
    else:
        return settings.DEFAULT_LICENSE_VALIDITY_DAYS


def send_license_email(order, licenses):
    """
    라이선스 정보 이메일 발송
    """
    subject = "🎉 모바일 청첩장 구매 완료 - 라이선스 정보"
    
    message = f"""
안녕하세요 {order.customer.get_full_name()}님,

모바일 청첩장을 구매해 주셔서 감사합니다!

주문 정보:
- 주문 번호: {order.order_name}
- 결제 금액: ${order.total_price}

라이선스 정보:
"""
    
    for i, license in enumerate(licenses, 1):
        message += f"""
{i}. {license.product_name}
   라이선스 키: {license.license_key}
   유효 기간: {license.expires_at.strftime('%Y-%m-%d') if license.expires_at else '무제한'}
"""
    
    message += f"""

시작하기:
1. 모바일 앱을 다운로드하세요 (App Store / Google Play)
2. 라이선스 키를 입력하세요
3. 청첩장을 제작하고 공유하세요!

앱 다운로드: {settings.FRONTEND_URL}

문의사항이 있으시면 언제든지 연락 주세요.

감사합니다!
"""
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=False,
    )
    
    logger.info(f"License email sent to {order.email}")
```

### 4.5 URL 설정

```python
# apps/shopify_integration/urls.py
from django.urls import path
from . import webhooks

app_name = 'shopify_integration'

urlpatterns = [
    path('shopify/', webhooks.shopify_webhook_handler, name='shopify-webhook'),
]
```

### 4.6 테스트

**1) 로컬 테스트 (ngrok 사용)**

```bash
# ngrok 시작
ngrok http 8000

# 출력된 HTTPS URL 복사
# https://xxxx.ngrok-free.app

# Shopify Admin에서 웹훅 URL 업데이트
# https://xxxx.ngrok-free.app/api/webhooks/shopify/
```

**2) curl로 테스트**

```bash
# HMAC 계산 (Python)
python -c "
import hmac
import hashlib
import base64
import json

secret = 'your_webhook_secret'
data = json.dumps({'id': 123, 'email': 'test@example.com'})

hmac_value = base64.b64encode(
    hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()
).decode('utf-8')

print(hmac_value)
"

# curl 요청
curl -X POST http://localhost:8000/api/webhooks/shopify/ \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Hmac-SHA256: <계산된_HMAC>" \
  -H "X-Shopify-Topic: orders/create" \
  -H "X-Shopify-Shop-Domain: your-shop.myshopify.com" \
  -d '{"id": 123, "email": "test@example.com"}'
```

**3) Shopify에서 실제 주문 테스트**

```
1. Shopify 스토어에서 테스트 주문 생성
2. Bogus Gateway로 결제 (카드 번호: 1)
3. Django 로그 확인:
   - 웹훅 수신 확인
   - 주문 저장 확인
   - 라이선스 생성 확인
4. 이메일 수신 확인
```

다음 섹션에서는 라이선스 시스템을 구현하겠습니다!

## 5. 청첩장 배포 권한 시스템 (라이선스)

### 5.1 라이선스 모델

```python
# apps/licenses/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets
import string
import uuid


class License(models.Model):
    """청첩장 배포 라이선스"""
    
    class Type(models.TextChoices):
        SINGLE_USE = 'single_use', '1회 사용'
        SUBSCRIPTION = 'subscription', '구독형'
        UNLIMITED = 'unlimited', '무제한'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        EXPIRED = 'expired', '만료'
        REVOKED = 'revoked', '취소'
        SUSPENDED = 'suspended', '정지'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 라이선스 정보
    license_key = models.CharField(max_length=64, unique=True, db_index=True)
    license_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SINGLE_USE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # 연관 주문
    order = models.ForeignKey(
        'shopify_integration.ShopifyOrder',
        on_delete=models.CASCADE,
        related_name='licenses'
    )
    customer = models.ForeignKey(
        'shopify_integration.ShopifyCustomer',
        on_delete=models.CASCADE,
        related_name='licenses'
    )
    
    # 상품 정보
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    
    # 유효 기간
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # 사용 제한
    max_invitations = models.IntegerField(default=1)  # 생성 가능한 청첩장 수
    used_invitations = models.IntegerField(default=0)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'licenses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license_key']),
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]
    
    def __str__(self):
        return f"{self.license_key} - {self.customer.email}"
    
    @property
    def is_active(self):
        """라이선스 활성 상태 확인"""
        if self.status != self.Status.ACTIVE:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        if self.license_type == self.Type.SINGLE_USE:
            return self.used_invitations < self.max_invitations
        
        return True
    
    @property
    def remaining_invitations(self):
        """남은 청첩장 생성 횟수"""
        if self.license_type == self.Type.UNLIMITED:
            return float('inf')
        return max(0, self.max_invitations - self.used_invitations)
    
    @property
    def days_until_expiry(self):
        """만료까지 남은 일수"""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    def activate(self):
        """라이선스 활성화"""
        if not self.activated_at:
            self.activated_at = timezone.now()
            self.save()
    
    def revoke(self, reason=''):
        """라이선스 취소"""
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.notes = f"Revoked: {reason}"
        self.save()
    
    def increment_usage(self):
        """사용 횟수 증가"""
        self.used_invitations += 1
        self.save()
    
    @staticmethod
    def generate_license_key(length=32):
        """라이선스 키 생성"""
        chars = string.ascii_uppercase + string.digits
        key = ''.join(secrets.choice(chars) for _ in range(length))
        
        # 4자리씩 하이픈으로 구분
        return '-'.join([key[i:i+4] for i in range(0, len(key), 4)])


class LicenseActivation(models.Model):
    """라이선스 활성화 로그"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name='activations'
    )
    
    # 디바이스 정보
    device_id = models.CharField(max_length=255, blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=50, blank=True)  # iOS, Android, Web
    
    # IP 주소
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # 위치 (선택)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # 타임스탬프
    activated_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'license_activations'
        ordering = ['-activated_at']
    
    def __str__(self):
        return f"{self.license.license_key} - {self.device_name}"
```

마이그레이션:

```bash
python manage.py makemigrations licenses
python manage.py migrate
```

### 5.2 라이선스 서비스

```python
# apps/licenses/services.py
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import License, LicenseActivation

logger = logging.getLogger(__name__)


class LicenseService:
    """라이선스 관리 서비스"""
    
    def create_license_from_order(
        self,
        order,
        line_item,
        license_type='single_use',
        validity_days=365
    ):
        """
        주문으로부터 라이선스 생성
        
        Args:
            order: ShopifyOrder 객체
            line_item: ShopifyOrderLineItem 객체
            license_type: 라이선스 타입
            validity_days: 유효 기간 (일), 0이면 무제한
            
        Returns:
            License 객체
        """
        # 라이선스 키 생성 (중복 확인)
        while True:
            license_key = License.generate_license_key(
                length=settings.LICENSE_KEY_LENGTH
            )
            if not License.objects.filter(license_key=license_key).exists():
                break
        
        # 만료일 계산
        expires_at = None
        if validity_days > 0:
            expires_at = timezone.now() + timedelta(days=validity_days)
        
        # 최대 청첩장 생성 수
        max_invitations = self._calculate_max_invitations(
            license_type,
            line_item.quantity
        )
        
        # 라이선스 생성
        license = License.objects.create(
            license_key=license_key,
            license_type=license_type,
            order=order,
            customer=order.customer,
            product_name=line_item.title,
            product_sku=line_item.sku,
            expires_at=expires_at,
            max_invitations=max_invitations,
            metadata={
                'order_id': str(order.id),
                'order_name': order.order_name,
                'line_item_id': str(line_item.id),
                'price_paid': str(line_item.price),
            }
        )
        
        logger.info(f"License created: {license.license_key} for order {order.order_name}")
        
        return license
    
    def _calculate_max_invitations(self, license_type, quantity):
        """라이선스 타입별 최대 청첩장 수 계산"""
        if license_type == License.Type.UNLIMITED:
            return 999999  # 사실상 무제한
        elif license_type == License.Type.SUBSCRIPTION:
            return 10 * quantity  # 구독형은 10개까지
        else:
            return quantity  # 1회용은 구매 수량만큼
    
    def validate_license(self, license_key):
        """
        라이선스 키 검증
        
        Returns:
            tuple: (is_valid, license_or_error_message)
        """
        try:
            license = License.objects.get(license_key=license_key)
        except License.DoesNotExist:
            return False, "Invalid license key"
        
        # 상태 확인
        if license.status != License.Status.ACTIVE:
            return False, f"License is {license.get_status_display()}"
        
        # 만료 확인
        if license.expires_at and timezone.now() > license.expires_at:
            license.status = License.Status.EXPIRED
            license.save()
            return False, "License has expired"
        
        # 사용 횟수 확인
        if license.license_type == License.Type.SINGLE_USE:
            if license.used_invitations >= license.max_invitations:
                return False, "License usage limit reached"
        
        return True, license
    
    def activate_license(self, license, device_info=None):
        """
        라이선스 활성화 및 디바이스 등록
        
        Args:
            license: License 객체
            device_info: dict with device_id, device_name, platform, ip_address
        """
        # 첫 활성화 시간 기록
        license.activate()
        
        # 디바이스 정보 저장
        if device_info:
            activation, created = LicenseActivation.objects.get_or_create(
                license=license,
                device_id=device_info.get('device_id', ''),
                defaults={
                    'device_name': device_info.get('device_name', ''),
                    'platform': device_info.get('platform', ''),
                    'ip_address': device_info.get('ip_address'),
                }
            )
            
            if not created:
                activation.last_used_at = timezone.now()
                activation.save()
            
            logger.info(f"License activated on device: {device_info.get('device_name')}")
        
        return license
    
    def get_customer_licenses(self, customer):
        """고객의 모든 라이선스 조회"""
        return License.objects.filter(customer=customer).order_by('-created_at')
    
    def get_active_licenses(self, customer):
        """고객의 활성 라이선스만 조회"""
        licenses = License.objects.filter(
            customer=customer,
            status=License.Status.ACTIVE
        )
        
        # 만료된 라이선스 필터링
        active_licenses = []
        for license in licenses:
            if license.is_active:
                active_licenses.append(license)
            elif license.expires_at and timezone.now() > license.expires_at:
                # 만료 상태로 업데이트
                license.status = License.Status.EXPIRED
                license.save()
        
        return active_licenses
    
    def extend_license(self, license, additional_days):
        """라이선스 유효기간 연장"""
        if license.expires_at:
            license.expires_at += timedelta(days=additional_days)
        else:
            license.expires_at = timezone.now() + timedelta(days=additional_days)
        
        license.save()
        logger.info(f"License {license.license_key} extended by {additional_days} days")
        
        return license
    
    def revoke_license(self, license, reason=''):
        """라이선스 취소"""
        license.revoke(reason)
        logger.info(f"License {license.license_key} revoked: {reason}")
        
        return license
```

### 5.3 라이선스 인증 미들웨어

```python
# apps/licenses/authentication.py
from rest_framework import authentication
from rest_framework import exceptions
from .models import License


class LicenseKeyAuthentication(authentication.BaseAuthentication):
    """
    라이선스 키 기반 인증
    
    Header: Authorization: License YOUR-LICENSE-KEY-HERE
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('License '):
            return None
        
        license_key = auth_header.replace('License ', '').strip()
        
        if not license_key:
            return None
        
        try:
            license = License.objects.get(license_key=license_key)
        except License.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid license key')
        
        # 라이선스 검증
        if not license.is_active:
            raise exceptions.AuthenticationFailed('License is not active')
        
        # 인증 성공: (user, auth) 반환
        # user는 고객의 User 객체 (없으면 None)
        return (license.customer.user if license.customer.user else None, license)


# apps/licenses/permissions.py
from rest_framework import permissions


class HasActiveLicense(permissions.BasePermission):
    """
    활성 라이선스 보유 권한
    """
    
    def has_permission(self, request, view):
        # 인증되지 않은 경우
        if not hasattr(request, 'auth'):
            return False
        
        # auth는 License 객체
        license = request.auth
        
        if not isinstance(license, License):
            return False
        
        return license.is_active


class CanCreateInvitation(permissions.BasePermission):
    """
    청첩장 생성 권한 (사용 횟수 체크)
    """
    
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        
        if not hasattr(request, 'auth'):
            return False
        
        license = request.auth
        
        if not isinstance(license, License):
            return False
        
        # 무제한 라이선스
        if license.license_type == License.Type.UNLIMITED:
            return True
        
        # 사용 횟수 체크
        return license.remaining_invitations > 0
```

### 5.4 라이선스 API

```python
# apps/licenses/api.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .services import LicenseService
from .models import License
from .serializers import LicenseSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_license(request):
    """
    라이선스 키 검증
    
    POST /api/licenses/validate/
    {
        "license_key": "XXXX-XXXX-XXXX-XXXX",
        "device_info": {
            "device_id": "uuid",
            "device_name": "iPhone 14 Pro",
            "platform": "iOS"
        }
    }
    """
    license_key = request.data.get('license_key')
    device_info = request.data.get('device_info')
    
    if not license_key:
        return Response(
            {'error': 'License key is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    service = LicenseService()
    is_valid, result = service.validate_license(license_key)
    
    if not is_valid:
        return Response(
            {'valid': False, 'error': result},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 라이선스 객체
    license = result
    
    # 디바이스 활성화
    if device_info:
        device_info['ip_address'] = get_client_ip(request)
        service.activate_license(license, device_info)
    
    return Response({
        'valid': True,
        'license': LicenseSerializer(license).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def check_license_status(request, license_key):
    """
    라이선스 상태 조회
    
    GET /api/licenses/status/{license_key}/
    """
    try:
        license = License.objects.get(license_key=license_key)
    except License.DoesNotExist:
        return Response(
            {'error': 'License not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response({
        'license_key': license.license_key,
        'status': license.status,
        'type': license.license_type,
        'is_active': license.is_active,
        'product_name': license.product_name,
        'expires_at': license.expires_at,
        'days_until_expiry': license.days_until_expiry,
        'max_invitations': license.max_invitations,
        'used_invitations': license.used_invitations,
        'remaining_invitations': license.remaining_invitations,
    })


@api_view(['GET'])
def my_licenses(request):
    """
    내 라이선스 목록 조회
    
    GET /api/licenses/my/
    Header: Authorization: License YOUR-KEY
    """
    license = request.auth
    
    if not isinstance(license, License):
        return Response(
            {'error': 'Invalid authentication'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    service = LicenseService()
    licenses = service.get_customer_licenses(license.customer)
    
    return Response({
        'licenses': LicenseSerializer(licenses, many=True).data
    })


def get_client_ip(request):
    """클라이언트 IP 주소 가져오기"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 5.5 Serializers

```python
# apps/licenses/serializers.py
from rest_framework import serializers
from .models import License, LicenseActivation


class LicenseActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicenseActivation
        fields = [
            'device_name',
            'platform',
            'activated_at',
            'last_used_at',
        ]


class LicenseSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    remaining_invitations = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    activations = LicenseActivationSerializer(many=True, read_only=True)
    
    class Meta:
        model = License
        fields = [
            'id',
            'license_key',
            'license_type',
            'status',
            'product_name',
            'product_sku',
            'activated_at',
            'expires_at',
            'max_invitations',
            'used_invitations',
            'remaining_invitations',
            'is_active',
            'days_until_expiry',
            'activations',
            'created_at',
        ]
```

### 5.6 URL 설정

```python
# apps/licenses/urls.py
from django.urls import path
from . import api

app_name = 'licenses'

urlpatterns = [
    path('validate/', api.validate_license, name='validate'),
    path('status/<str:license_key>/', api.check_license_status, name='status'),
    path('my/', api.my_licenses, name='my-licenses'),
]
```

### 5.7 Admin 인터페이스

```python
# apps/licenses/admin.py
from django.contrib import admin
from .models import License, LicenseActivation


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = [
        'license_key',
        'customer_email',
        'product_name',
        'license_type',
        'status',
        'is_active',
        'expires_at',
        'used_invitations',
        'max_invitations',
        'created_at',
    ]
    
    list_filter = [
        'license_type',
        'status',
        'created_at',
    ]
    
    search_fields = [
        'license_key',
        'customer__email',
        'product_name',
        'product_sku',
    ]
    
    readonly_fields = [
        'id',
        'license_key',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('라이선스 정보', {
            'fields': ('id', 'license_key', 'license_type', 'status')
        }),
        ('주문 정보', {
            'fields': ('order', 'customer', 'product_name', 'product_sku')
        }),
        ('유효 기간', {
            'fields': ('activated_at', 'expires_at', 'revoked_at')
        }),
        ('사용 제한', {
            'fields': ('max_invitations', 'used_invitations')
        }),
        ('메타데이터', {
            'fields': ('metadata', 'notes'),
            'classes': ('collapse',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_email(self, obj):
        return obj.customer.email
    customer_email.short_description = '고객 이메일'


@admin.register(LicenseActivation)
class LicenseActivationAdmin(admin.ModelAdmin):
    list_display = [
        'license_key',
        'device_name',
        'platform',
        'ip_address',
        'activated_at',
        'last_used_at',
    ]
    
    list_filter = [
        'platform',
        'activated_at',
    ]
    
    search_fields = [
        'license__license_key',
        'device_name',
        'ip_address',
    ]
    
    def license_key(self, obj):
        return obj.license.license_key
    license_key.short_description = '라이선스 키'
```

라이선스 시스템 구현이 완료되었습니다! 다음 섹션에서는 청첩장 API를 구현하겠습니다.

## 6. 청첩장 배포 API 구현

이제 라이선스로 인증된 사용자가 청첩장을 생성하고 관리하는 API를 구현합니다.

### 6.1 청첩장 모델

```python
# apps/invitations/models.py
from django.db import models
import uuid
import secrets
import string


class WeddingInvitation(models.Model):
    """모바일 청첩장"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', '작성중'
        PUBLISHED = 'published', '공개'
        ARCHIVED = 'archived', '보관'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 라이선스 연결
    license = models.ForeignKey(
        'licenses.License',
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    
    # 고유 URL
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    
    # 상태
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # 신랑 신부 정보
    groom_name = models.CharField(max_length=100)
    groom_father = models.CharField(max_length=100, blank=True)
    groom_mother = models.CharField(max_length=100, blank=True)
    groom_phone = models.CharField(max_length=20, blank=True)
    
    bride_name = models.CharField(max_length=100)
    bride_father = models.CharField(max_length=100, blank=True)
    bride_mother = models.CharField(max_length=100, blank=True)
    bride_phone = models.CharField(max_length=20, blank=True)
    
    # 예식 정보
    wedding_date = models.DateTimeField()
    venue_name = models.CharField(max_length=200)
    venue_address = models.CharField(max_length=300)
    venue_floor = models.CharField(max_length=50, blank=True)
    venue_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    venue_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # 메시지
    greeting_message = models.TextField(blank=True)
    invitation_message = models.TextField(blank=True)
    
    # 계좌 정보
    account_info = models.JSONField(default=list, blank=True)
    
    # 디자인
    template_type = models.CharField(max_length=50, default='modern')
    color_scheme = models.CharField(max_length=50, default='pink')
    background_music_url = models.URLField(blank=True)
    
    # 통계
    view_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'wedding_invitations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.groom_name} ❤️ {self.bride_name}"
    
    @property
    def url(self):
        from django.conf import settings
        return f"{settings.INVITATION_BASE_URL}{self.slug}"
    
    @staticmethod
    def generate_slug():
        """고유한 슬러그 생성"""
        chars = string.ascii_lowercase + string.digits
        while True:
            slug = ''.join(secrets.choice(chars) for _ in range(8))
            if not WeddingInvitation.objects.filter(slug=slug).exists():
                return slug


class InvitationPhoto(models.Model):
    """청첩장 사진 갤러리"""
    
    invitation = models.ForeignKey(
        WeddingInvitation,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    image = models.ImageField(upload_to='invitations/photos/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'invitation_photos'
        ordering = ['order', 'created_at']


class GuestMessage(models.Model):
    """방명록"""
    
    invitation = models.ForeignKey(
        WeddingInvitation,
        on_delete=models.CASCADE,
        related_name='guest_messages'
    )
    
    name = models.CharField(max_length=100)
    message = models.TextField()
    password = models.CharField(max_length=128)  # 수정/삭제용
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'guest_messages'
        ordering = ['-created_at']
```

### 6.2 청첩장 API

```python
# apps/invitations/api.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone

from apps.licenses.authentication import LicenseKeyAuthentication
from apps.licenses.permissions import HasActiveLicense, CanCreateInvitation
from .models import WeddingInvitation, InvitationPhoto, GuestMessage
from .serializers import (
    WeddingInvitationSerializer,
    InvitationPhotoSerializer,
    GuestMessageSerializer
)


class WeddingInvitationViewSet(viewsets.ModelViewSet):
    """청첩장 CRUD API"""
    
    queryset = WeddingInvitation.objects.all()
    serializer_class = WeddingInvitationSerializer
    lookup_field = 'slug'
    
    def get_permissions(self):
        """액션별 권한 설정"""
        if self.action in ['retrieve', 'list_public']:
            return [AllowAny()]
        elif self.action == 'create':
            return [HasActiveLicense(), CanCreateInvitation()]
        return [HasActiveLicense()]
    
    def get_authenticators(self):
        """인증 방식"""
        if self.action in ['retrieve', 'list_public']:
            return []
        return [LicenseKeyAuthentication()]
    
    def get_queryset(self):
        """라이선스 소유자의 청첩장만 조회"""
        if self.action in ['retrieve', 'list_public']:
            return WeddingInvitation.objects.filter(status='published')
        
        license = self.request.auth
        return WeddingInvitation.objects.filter(license=license)
    
    def create(self, request, *args, **kwargs):
        """청첩장 생성"""
        license = request.auth
        
        # 슬러그 생성
        slug = WeddingInvitation.generate_slug()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 청첩장 생성
        invitation = serializer.save(
            license=license,
            slug=slug
        )
        
        # 라이선스 사용 횟수 증가
        license.increment_usage()
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def publish(self, request, slug=None):
        """청첩장 공개"""
        invitation = self.get_object()
        invitation.status = WeddingInvitation.Status.PUBLISHED
        invitation.published_at = timezone.now()
        invitation.save()
        
        return Response({
            'message': '청첩장이 공개되었습니다.',
            'url': invitation.url
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """통계 조회"""
        invitation = self.get_object()
        return Response({
            'view_count': invitation.view_count,
            'share_count': invitation.share_count,
            'guest_messages_count': invitation.guest_messages.count(),
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def view_invitation(request, slug):
    """
    공개 청첩장 조회
    
    GET /api/invitations/view/{slug}/
    """
    try:
        invitation = WeddingInvitation.objects.get(
            slug=slug,
            status='published'
        )
    except WeddingInvitation.DoesNotExist:
        return Response(
            {'error': '청첩장을 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 조회수 증가
    invitation.view_count += 1
    invitation.save(update_fields=['view_count'])
    
    serializer = WeddingInvitationSerializer(invitation)
    return Response(serializer.data)
```

### 6.3 요약 및 남은 섹션

이제 핵심 기능이 모두 구현되었습니다!

**완성된 기능:**
- ✅ Shopify 결제 연동
- ✅ 웹훅 수신 및 검증
- ✅ 자동 라이선스 발급
- ✅ 라이선스 인증 시스템
- ✅ 청첩장 CRUD API

**남은 작업 (간단히):**
- 모바일 클라이언트 통합 예제
- 테스트 및 배포
- 보안 최적화
- 모니터링

## 7. 모바일 클라이언트 통합

### React Native 예제

```javascript
// API Client
const API_BASE_URL = 'https://yourdomain.com/api';

class WeddingAPI {
  constructor(licenseKey) {
    this.licenseKey = licenseKey;
  }

  async validateLicense() {
    const response = await fetch(`${API_BASE_URL}/licenses/validate/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        license_key: this.licenseKey,
        device_info: {
          device_id: await DeviceInfo.getUniqueId(),
          device_name: await DeviceInfo.getDeviceName(),
          platform: Platform.OS,
        }
      })
    });
    return response.json();
  }

  async createInvitation(data) {
    const response = await fetch(`${API_BASE_URL}/invitations/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `License ${this.licenseKey}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  }

  async getMyInvitations() {
    const response = await fetch(`${API_BASE_URL}/invitations/`, {
      headers: { 'Authorization': `License ${this.licenseKey}` }
    });
    return response.json();
  }
}
```

## 8. 테스트

```python
# tests/test_webhooks.py
import json
import hmac
import hashlib
import base64
from django.test import TestCase, Client
from django.conf import settings

class WebhookTestCase(TestCase):
    def test_order_paid_webhook(self):
        payload = {
            "id": 123456,
            "email": "customer@example.com",
            "total_price": "29.00",
            "line_items": [...]
        }
        
        # HMAC 생성
        data = json.dumps(payload).encode('utf-8')
        secret = settings.SHOPIFY_WEBHOOK_SECRET.encode('utf-8')
        hmac_value = base64.b64encode(
            hmac.new(secret, data, hashlib.sha256).digest()
        ).decode('utf-8')
        
        # 웹훅 요청
        response = self.client.post(
            '/api/webhooks/shopify/',
            data=payload,
            content_type='application/json',
            HTTP_X_SHOPIFY_HMAC_SHA256=hmac_value,
            HTTP_X_SHOPIFY_TOPIC='orders/paid',
        )
        
        self.assertEqual(response.status_code, 200)
```

## 9. 프로덕션 배포

### AWS EC2 배포

```bash
# 서버 설정
sudo apt update
sudo apt install python3-pip python3-venv postgresql nginx

# 프로젝트 배포
git clone your-repo
cd wedding_invitation_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Gunicorn 실행
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Nginx 설정
# /etc/nginx/sites-available/wedding
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}

# SSL 인증서 (Let's Encrypt)
sudo certbot --nginx -d yourdomain.com
```

## 10. 결론

이 튜토리얼에서 구현한 시스템:

**핵심 성과:**
- 🛒 Shopify 결제 시스템 완전 통합
- 🔐 안전한 웹훅 검증 (HMAC)
- 🎫 자동화된 라이선스 발급
- 📱 모바일 API 제공
- 💌 모바일 청첩장 SaaS 완성

**확장 가능성:**
- 다양한 템플릿 추가
- AI 기반 이미지 편집
- 실시간 게스트 참석 관리
- 결혼식 스트리밍 연동
- 다국어 지원

**참고 자료:**
- [Shopify Webhook Documentation](https://shopify.dev/docs/api/webhooks)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryq.dev/)

축하합니다! 완전한 SaaS 서비스를 구축했습니다! 🎉

