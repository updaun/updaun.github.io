---
layout: post
title: "Railway로 Django Ninja + Redis + Celery + Celery Beat 프로덕션 배포하기: 실전 운영 가이드"
date: 2026-03-26 10:00:00 +0900
categories: [Django, Django-Ninja, Celery, Railway, DevOps]
tags: [Django, Django-Ninja, Railway, Redis, Celery, Celery-Beat, Deployment, Background Jobs, Python, PostgreSQL]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-03-26-django-ninja-railway-celery-redis-deployment-guide.webp"
---

Django Ninja API를 실제 서비스로 운영하려면 HTTP 요청 처리와 백그라운드 작업 처리를 분리하고, 스케줄러를 안정적으로 실행하는 구조가 필요합니다. 이 글은 Railway를 기준으로 Django Ninja(Web), Redis(Broker), Celery Worker, Celery Beat를 각각 독립 서비스로 배포하고 운영 이슈까지 해결하는 과정을 처음부터 끝까지 다룹니다.

Railway에서 이 조합이 좋은 이유는 단순합니다. Git 기반 배포가 빠르고, 서비스 단위로 환경변수와 리소스를 분리할 수 있으며, Redis와 PostgreSQL을 붙여도 설정 복잡도가 낮습니다. 다만 프로덕션에서는 “돌아간다”보다 “예측 가능하게 운영된다”가 더 중요하므로, 이 글에서는 로컬 성공이 아니라 운영 안정성을 기준으로 설명합니다.

## 1. 배포 아키텍처 먼저 확정하기

가장 먼저 해야 할 일은 서비스 경계를 명확히 나누는 것입니다. Railway 프로젝트 안에 Web 서비스(Django Ninja), Worker 서비스(Celery), Beat 서비스(Celery Beat), Redis 서비스, PostgreSQL 서비스를 각각 두고, Web만 외부 트래픽을 받게 설계합니다. Worker와 Beat는 내부 네트워크에서만 브로커/DB를 사용하므로 퍼블릭 노출이 필요 없습니다.

핵심 원칙은 “한 프로세스 한 책임”입니다. Web에서 API만 처리하고, Worker에서 비동기 작업만 처리하고, Beat에서 스케줄 발행만 담당하면 장애 전파 범위가 줄어듭니다. 특히 Beat를 Worker와 한 컨테이너에서 같이 돌리면 중복 스케줄 발행이나 재시작 타이밍 문제를 만나기 쉬워 반드시 분리하는 편이 안전합니다.

## 2. Django 프로젝트 기본 의존성 정리

먼저 필수 패키지를 고정 버전으로 정리합니다. `django-celery-beat`는 주기 스케줄을 DB에 저장해 운영 중에도 안전하게 수정할 수 있고, `django-celery-results`는 작업 결과 추적이 필요할 때 유용합니다.

```txt
Django==5.1.6
django-ninja==1.3.0
celery==5.4.0
redis==5.0.7
django-celery-beat==2.7.0
django-celery-results==2.5.1
gunicorn==22.0.0
psycopg[binary]==3.2.3
```

Railway는 빌드 환경이 자주 갱신되므로 “최신이면 되겠지” 접근보다 검증된 버전 고정이 훨씬 안전합니다. 프로덕션 배포 이후 예기치 못한 마이너 변경으로 Worker만 죽는 상황을 막으려면, 최소한 주요 런타임 패키지는 pinning 해두는 것이 좋습니다.

## 3. settings.py를 Railway 친화적으로 구성

Railway 환경변수를 기준으로 DB, Redis, Celery 설정을 모두 통일합니다. 포인트는 Web/Worker/Beat가 같은 환경변수 체계를 공유하되, 역할별로 필요한 값만 참조하는 구조입니다.

```python
# settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "django_celery_results",
]

DATABASE_URL = os.getenv("DATABASE_URL")

# 예시: dj-database-url 사용 시
# import dj_database_url
# DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}

REDIS_URL = os.getenv("REDIS_URL")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("TIME_ZONE", "Asia/Seoul")
CELERY_ENABLE_UTC = False
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 20
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 18
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
```

여기서 `CELERY_WORKER_PREFETCH_MULTIPLIER=1`과 `ACKS_LATE=True`는 작업 쏠림과 워커 비정상 종료 시 유실 위험을 줄이는 데 실무적으로 매우 중요합니다. 특히 Railway처럼 스케일 업/다운이 잦은 환경에서는 공정한 작업 분배와 안전한 재처리가 체감 안정성을 크게 좌우합니다.

## 4. Celery 앱 초기화와 태스크 분리

Celery 초기화 파일은 Django 설정 로딩과 자동 태스크 탐지를 명확히 해두면 됩니다. 복잡한 커스텀보다 예측 가능한 기본 구성이 운영에 유리합니다.

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ("celery_app",)
```

태스크는 API 레이어와 분리된 앱(예: `jobs/tasks.py`)에 두고, 재시도 정책을 태스크 단위로 선언하는 패턴이 좋습니다. 외부 API 호출 태스크에는 `autoretry_for`, `retry_backoff`, `max_retries`를 적용해 일시 장애를 흡수해야 실제 운영에서 큐 폭증을 막을 수 있습니다.

```python
# jobs/tasks.py
from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_notification(self, user_id: int, message: str):
    # 외부 API 호출, 이메일 발송, 푸시 전송 등
    return {"user_id": user_id, "status": "sent"}
```

## 5. Django Ninja에서 비동기 작업 트리거

Django Ninja 엔드포인트에서는 긴 작업을 절대 직접 처리하지 말고 큐에 위임합니다. API는 “요청 수신 및 작업 등록”까지 책임지고 즉시 응답해야 SLA를 지킬 수 있습니다.

```python
# api.py
from ninja import NinjaAPI, Schema
from jobs.tasks import send_notification

api = NinjaAPI(title="My Service API", version="1.0.0")

class NotificationIn(Schema):
    user_id: int
    message: str

@api.post("/notifications")
def enqueue_notification(request, payload: NotificationIn):
    async_result = send_notification.delay(payload.user_id, payload.message)
    return {
        "task_id": async_result.id,
        "status": "queued",
    }
```

이 방식의 장점은 명확합니다. API p95 응답시간은 짧아지고, 작업 처리량은 Worker 스케일로 대응할 수 있으며, 실패는 재시도 정책으로 분리 처리됩니다. 즉, 사용자 경험과 백엔드 처리량을 동시에 확보할 수 있습니다.

## 6. Railway 배포를 위한 실행 명령 설계

Railway는 동일 리포지토리에서 여러 서비스를 만들 수 있으므로, 서비스별 Start Command를 분리해 운영하는 방식이 가장 단순합니다. Dockerfile 하나로 공통 이미지를 빌드하고, Web/Worker/Beat에서 서로 다른 실행 커맨드를 사용하면 됩니다.

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:${PORT}", "--workers", "2", "--threads", "4", "--timeout", "120"]
```

Web 서비스 Start Command는 다음과 같이 구성합니다.

```bash
python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

Worker 서비스 Start Command는 큐 처리 안정성을 기준으로 설정합니다.

```bash
celery -A config worker --loglevel=INFO --concurrency=2 --max-tasks-per-child=1000
```

Beat 서비스 Start Command는 반드시 단일 인스턴스로 운영합니다.

```bash
celery -A config beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

`--max-tasks-per-child`는 메모리 누수를 완화하는 데 실무적으로 효과가 좋고, Beat 단일 인스턴스 원칙은 중복 스케줄 발행 사고를 방지하는 핵심 제어점입니다.

## 7. Railway 서비스 생성 순서와 연결

실전에서는 생성 순서가 중요합니다. 먼저 PostgreSQL, Redis를 만들고 연결 정보가 안정적으로 나온 뒤 Web/Worker/Beat를 붙여야 시행착오가 줄어듭니다. 이후 각 서비스에 동일한 환경변수 키를 주입합니다.

필수 환경변수 예시는 아래와 같습니다.

```bash
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=...
DEBUG=false
ALLOWED_HOSTS=your-web-domain.up.railway.app
DATABASE_URL=postgresql://...
REDIS_URL=redis://default:password@host:port
CELERY_BROKER_URL=redis://default:password@host:port/0
CELERY_RESULT_BACKEND=django-db
TIME_ZONE=Asia/Seoul
```

Railway에서 내부 URL을 사용할 수 있다면 외부 노출 대신 내부 네트워크 주소를 우선 사용하세요. 네트워크 홉을 줄이면 지연과 장애면에서 유리하고, 보안 표면도 줄어듭니다.

## 8. Celery Beat 스케줄을 DB로 운영

`django-celery-beat`를 쓰면 코드 배포 없이 스케줄 변경이 가능합니다. 운영자가 Admin에서 주기를 조정할 수 있고, 긴급 대응 시 배포 파이프라인을 기다릴 필요가 없습니다.

```bash
python manage.py migrate
python manage.py createsuperuser
```

예를 들어 매 5분마다 통계 집계 태스크를 실행하려면 Interval Schedule을 만들고, Periodic Task에서 `jobs.tasks.aggregate_metrics`를 연결하면 됩니다. 이 방식은 스케줄 변경 이력과 가시성이 좋아 팀 운영에서 특히 유리합니다.

## 9. 프로덕션 안정화 체크리스트

첫째, Worker autoscaling을 사용할 때는 큐 길이 기반으로 관찰 지표를 먼저 정하고 스케일 정책을 나중에 얹어야 합니다. 기준 없이 스케일만 열면 Redis 커넥션과 DB 부하가 동시에 튀는 경우가 많습니다.

둘째, idempotency를 반드시 설계해야 합니다. Celery는 최소 1회 전달 특성이 있으므로 중복 실행 가능성을 전제로 태스크를 작성해야 하며, 결제/포인트/재고 같은 도메인에서는 고유 키 또는 상태 전이 검증이 필수입니다.

셋째, 타임존을 Django와 Celery에서 동일하게 맞추고 Beat 기준 시간을 명확히 해야 합니다. 이 설정이 틀리면 “자정 배치”가 실제로는 다른 시각에 실행되는 문제가 반복됩니다.

넷째, 로그는 Web/Worker/Beat를 분리해서 봐야 원인 파악 속도가 빨라집니다. API 200 응답인데 작업이 실패하는 유형은 대부분 Worker 로그에서만 단서가 나옵니다.

다섯째, Railway의 파일시스템은 영속 스토리지로 가정하면 안 됩니다. 업로드 파일, 리포트 결과물, 모델 파일 캐시는 S3 같은 외부 스토리지로 분리해야 재배포 시 데이터 유실을 막을 수 있습니다.

## 10. 장애 시나리오별 대응 전략

Redis 일시 장애가 발생하면 Worker는 브로커 재연결을 반복하게 됩니다. 이때 `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True`와 적절한 재시도 정책이 없으면 서비스 재기동 루프에 빠질 수 있으니 반드시 활성화해두세요.

DB 마이그레이션과 애플리케이션 배포 타이밍이 어긋나면 Worker가 구버전 스키마를 참조해 실패할 수 있습니다. 배포 순서를 “migrate 완료 -> Web/Worker/Beat 재시작”으로 고정하고, 파괴적 마이그레이션은 2단계(확장 후 축소)로 처리하면 안전합니다.

Beat 중복 기동은 같은 작업이 여러 번 큐에 들어가는 대표 원인입니다. Railway에서 Beat 서비스의 replica를 1로 강제하고, 장애 복구 시 수동으로 중복 인스턴스가 생기지 않았는지 확인하는 운영 습관이 필요합니다.

## 11. 마무리: Railway에서 이 스택을 오래 운영하려면

Django Ninja + Redis + Celery + Celery Beat 조합은 Railway에서 충분히 프로덕션급으로 운영할 수 있습니다. 다만 성공 포인트는 배포 자체보다 역할 분리, 재시도 전략, 단일 Beat 보장, 환경변수 표준화, 그리고 관측 가능한 로그 체계에 있습니다.

이 글의 순서대로 구성하면 “일단 배포됨” 수준을 넘어 “장애가 나도 복구 가능한 시스템”으로 빠르게 올라설 수 있습니다. 처음에는 Web/Worker/Beat 각각 1개 인스턴스로 시작하고, 실제 트래픽과 큐 패턴을 본 뒤 수평 확장하는 접근이 비용과 안정성 모두에서 가장 현실적입니다.

## 부록 A. 최소 점검 명령어

배포 직후에는 아래 항목을 순서대로 점검하면 대부분의 초기 장애를 빠르게 잡을 수 있습니다.

```bash
# Django 설정 확인
python manage.py check --deploy

# Celery에 태스크가 로드됐는지 확인
celery -A config inspect registered

# 워커 상태 확인
celery -A config inspect ping

# Beat 스케줄 확인(관리자 화면 + DB)
python manage.py shell
# >>> from django_celery_beat.models import PeriodicTask
# >>> PeriodicTask.objects.filter(enabled=True).count()
```

Web 헬스체크 엔드포인트, Redis 연결 테스트 엔드포인트, 큐 적재/소비 테스트 태스크까지 준비해두면 Railway 재배포 시 회귀 점검 시간이 크게 줄어듭니다.