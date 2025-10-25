---
layout: post
title: "Django Ninja로 실시간 배송추적 시스템 구축하기 - 스마트택배 API 완벽 활용"
subtitle: "외부 택배사 API 연동으로 고도화된 배송 추적 서비스 개발"
date: 2025-10-25 10:00:00 +0900
background: '/img/posts/django-ninja-delivery-bg.jpg'
categories: [Django, API, Logistics]
tags: [django-ninja, delivery-tracking, smartparcel-api, fastapi, logistics, shipping]
---

# 🚚 Django Ninja로 실시간 배송추적 시스템 구축하기

현대 e-커머스에서 **배송 추적**은 필수 기능입니다. 고객들은 주문한 상품이 어디에 있는지 실시간으로 확인하고 싶어하죠. 

이번 포스트에서는 **Django Ninja**와 **스마트택배 API**를 활용하여 **실무급 배송추적 시스템**을 구축해보겠습니다.

## 🎯 구현할 기능 개요

- **다중 택배사 지원** (CJ대한통운, 로젠, 한진택배 등)
- **실시간 배송 상태 추적**
- **자동 배송 상태 업데이트**
- **고객 알림 시스템** (SMS, 푸시, 이메일)
- **배송 예상 시간 계산**
- **배송 지연 감지 및 알림**

---

## 📦 1. 프로젝트 설정 및 기본 구조

먼저 프로젝트의 기본 구조를 설정하고 필요한 의존성을 설치하겠습니다.

### 1.1 의존성 설치

```bash
# requirements.txt
django==4.2.7
django-ninja==1.0.1
redis==5.0.1
celery==5.3.4
requests==2.31.0
python-decouple==3.8
django-model-utils==4.3.1
django-extensions==3.2.3

# 알림 서비스용
twilio==8.10.0
django-push-notifications==3.0.2

# 데이터베이스
psycopg2-binary==2.9.9
```

### 1.2 Django 설정

```python
# settings/base.py
from decouple import config

# 스마트택배 API 설정
SMARTPARCEL_API_KEY = config('SMARTPARCEL_API_KEY')
SMARTPARCEL_BASE_URL = 'https://info.sweettracker.co.kr/api'

# Celery 설정 (비동기 작업용)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')

# 알림 서비스 설정
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'ninja',
    'django_extensions',
    
    # Local apps
    'apps.accounts',
    'apps.orders',
    'apps.delivery',  # 새로 생성할 앱
    'apps.notifications',
]
```

### 1.3 프로젝트 구조

```
delivery_tracking/
├── apps/
│   ├── delivery/
│   │   ├── models.py          # 배송 관련 모델
│   │   ├── services.py        # 택배사 API 서비스
│   │   ├── api.py            # Django Ninja API
│   │   ├── tasks.py          # Celery 비동기 작업
│   │   └── schemas.py        # Pydantic 스키마
│   ├── orders/
│   │   └── models.py         # 주문 모델
│   └── notifications/
│       └── services.py       # 알림 서비스
├── config/
│   ├── settings/
│   ├── urls.py
│   └── celery.py
└── requirements.txt
```

---

## 🏗️ 2. 데이터 모델 설계

배송 추적을 위한 핵심 모델들을 설계해보겠습니다.
