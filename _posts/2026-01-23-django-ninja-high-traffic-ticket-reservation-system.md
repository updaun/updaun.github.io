---
layout: post
title: "Django Ninja로 구현하는 대규모 공연 티켓 예매 시스템"
date: 2026-01-23
categories: [Django, Backend, Architecture]
tags: [django-ninja, redis, celery, concurrency, high-traffic, ticket-reservation]
---

## 서론: 티켓 예매 시스템의 도전과제

공연 티켓 예매 시스템은 백엔드 개발자에게 가장 도전적인 과제 중 하나입니다. 인기 아티스트의 콘서트 티켓이 오픈되는 순간, 수만 명의 사용자가 동시에 접속하여 한정된 좌석을 예매하려 합니다. 이 과정에서 발생할 수 있는 문제들은 다음과 같습니다:

- **Race Condition**: 여러 사용자가 동시에 같은 좌석을 예매하려 할 때 발생하는 경쟁 상태
- **Overselling**: 재고 관리 실패로 인해 실제 좌석 수보다 많은 티켓이 판매되는 상황
- **DB Lock Contention**: 대량의 동시 요청으로 인한 데이터베이스 락 경합
- **서버 과부하**: 순간적인 트래픽 폭증으로 인한 서버 다운

본 포스트에서는 Django Ninja를 활용하여 이러한 문제들을 해결하고, 대규모 트래픽을 안정적으로 처리할 수 있는 티켓 예매 시스템을 구축하는 방법을 코드와 함께 살펴보겠습니다.

## Django Ninja 소개 및 프로젝트 구조

Django Ninja는 FastAPI에서 영감을 받아 만들어진 Django용 웹 프레임워크로, Python 타입 힌트를 활용한 자동 검증, API 문서 자동 생성, 그리고 뛰어난 성능을 제공합니다. Django REST Framework(DRF)에 비해 약 2-3배 빠른 성능을 보이며, 특히 대량 트래픽 처리가 필요한 티켓 예매 시스템에 적합합니다.

먼저 프로젝트 구조를 설정하겠습니다:

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필요한 패키지 설치
pip install django django-ninja redis celery python-decouple psycopg2-binary
```

```python
# requirements.txt
Django==5.0.1
django-ninja==1.1.0
redis==5.0.1
celery==5.3.4
python-decouple==3.8
psycopg2-binary==2.9.9
django-redis==5.4.0
```

프로젝트 구조는 다음과 같이 구성합니다:

```
ticket_system/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── tickets/
│   ├── __init__.py
│   ├── models.py
│   ├── schemas.py
│   ├── api.py
│   ├── services.py
│   └── tasks.py
└── core/
    ├── __init__.py
    ├── redis_lock.py
    └── exceptions.py
```

## 모델 설계 및 기본 API 구현

티켓 예매 시스템의 핵심은 적절한 데이터 모델 설계입니다. Concert(공연), Seat(좌석), Reservation(예약) 모델을 구현하고, 재고 관리를 위한 필드를 추가합니다:

```python
# tickets/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Concert(models.Model):
    """공연 정보"""
    title = models.CharField(max_length=200, verbose_name="공연명")
    artist = models.CharField(max_length=100, verbose_name="아티스트")
    venue = models.CharField(max_length=200, verbose_name="공연장")
    event_date = models.DateTimeField(verbose_name="공연 일시")
    sale_start_date = models.DateTimeField(verbose_name="판매 시작 일시")
    total_seats = models.IntegerField(verbose_name="총 좌석 수")
    available_seats = models.IntegerField(verbose_name="남은 좌석 수")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'concerts'
        indexes = [
            models.Index(fields=['sale_start_date']),
            models.Index(fields=['event_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.artist}"

class Seat(models.Model):
    """좌석 정보"""
    STATUS_CHOICES = [
        ('AVAILABLE', '예매 가능'),
        ('RESERVED', '예약됨'),
        ('CONFIRMED', '결제 완료'),
    ]
    
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE, related_name='seats')
    section = models.CharField(max_length=50, verbose_name="구역")  # VIP, R, S, A
    row = models.CharField(max_length=10, verbose_name="열")
    number = models.IntegerField(verbose_name="좌석 번호")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    version = models.IntegerField(default=0, verbose_name="버전 (낙관적 락)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'seats'
        unique_together = [['concert', 'section', 'row', 'number']]
        indexes = [
            models.Index(fields=['concert', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.concert.title} - {self.section}{self.row}-{self.number}"

class Reservation(models.Model):
    """예약 정보"""
    STATUS_CHOICES = [
        ('PENDING', '결제 대기'),
        ('CONFIRMED', '예약 확정'),
        ('CANCELLED', '취소됨'),
        ('EXPIRED', '만료됨'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="예약 만료 시간")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'reservations'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.seat}"
```

이제 Django Ninja를 사용하여 기본 API를 구현합니다:

```python
# tickets/schemas.py
from ninja import Schema
from datetime import datetime
from typing import Optional

class ConcertSchema(Schema):
    id: int
    title: str
    artist: str
    venue: str
    event_date: datetime
    sale_start_date: datetime
    available_seats: int
    total_seats: int
    price: float

class SeatSchema(Schema):
    id: int
    section: str
    row: str
    number: int
    status: str

class ReservationRequest(Schema):
    seat_id: int

class ReservationResponse(Schema):
    id: int
    seat: SeatSchema
    status: str
    reserved_at: datetime
    expires_at: datetime
```

```python
# tickets/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from typing import List
from .models import Concert, Seat, Reservation
from .schemas import ConcertSchema, SeatSchema, ReservationResponse, ReservationRequest

router = Router()

@router.get("/concerts", response=List[ConcertSchema])
def list_concerts(request):
    """공연 목록 조회"""
    concerts = Concert.objects.filter(
        sale_start_date__lte=timezone.now()
    ).order_by('-sale_start_date')
    return concerts

@router.get("/concerts/{concert_id}/seats", response=List[SeatSchema])
def list_available_seats(request, concert_id: int):
    """특정 공연의 예매 가능한 좌석 목록"""
    seats = Seat.objects.filter(
        concert_id=concert_id,
        status='AVAILABLE'
    ).select_related('concert')
    return seats
```

## Redis 분산 락을 활용한 동시성 제어

티켓 예매 시스템에서 가장 중요한 부분은 동시성 제어입니다. 여러 사용자가 동시에 같은 좌석을 예매하려 할 때, Race Condition을 방지해야 합니다. Redis의 분산 락(Distributed Lock)을 사용하여 이를 해결합니다.

먼저 Redis 설정을 추가합니다:

```python
# config/settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Redis 연결 설정
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
```

Redis 분산 락 구현:

```python
# core/redis_lock.py
import redis
import time
import uuid
from contextlib import contextmanager
from typing import Optional

class RedisLock:
    """Redis 기반 분산 락 구현"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    @contextmanager
    def acquire_lock(
        self, 
        lock_key: str, 
        timeout: int = 10, 
        blocking_timeout: int = 5
    ):
        """
        분산 락 획득
        
        Args:
            lock_key: 락의 키
            timeout: 락 자동 만료 시간 (초)
            blocking_timeout: 락 획득 대기 시간 (초)
        """
        # 고유한 lock identifier 생성
        lock_id = str(uuid.uuid4())
        lock_acquired = False
        start_time = time.time()
        
        try:
            # 락 획득 시도 (blocking)
            while time.time() - start_time < blocking_timeout:
                # SET NX (Not eXists) + EX (EXpire) 명령어 사용
                if self.redis_client.set(
                    lock_key, 
                    lock_id, 
                    nx=True, 
                    ex=timeout
                ):
                    lock_acquired = True
                    break
                
                # 100ms 대기 후 재시도
                time.sleep(0.1)
            
            if not lock_acquired:
                raise TimeoutError(f"Lock 획득 실패: {lock_key}")
            
            yield lock_id
            
        finally:
            # 락 해제 (Lua 스크립트로 원자적 작업 보장)
            if lock_acquired:
                self._release_lock(lock_key, lock_id)
    
    def _release_lock(self, lock_key: str, lock_id: str):
        """
        락 해제 (자신이 획득한 락만 해제)
        Lua 스크립트로 원자성 보장
        """
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis_client.eval(lua_script, 1, lock_key, lock_id)

# Redis 클라이언트 싱글톤
_redis_client = None

def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 반환"""
    global _redis_client
    if _redis_client is None:
        from django.conf import settings
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return _redis_client

def get_redis_lock() -> RedisLock:
    """RedisLock 인스턴스 반환"""
    return RedisLock(get_redis_client())
```

커스텀 예외 정의:

```python
# core/exceptions.py
from ninja import Schema

class SeatNotAvailableError(Exception):
    """좌석이 이미 예약된 경우"""
    pass

class ConcertNotFoundError(Exception):
    """공연을 찾을 수 없는 경우"""
    pass

class ReservationExpiredError(Exception):
    """예약이 만료된 경우"""
    pass

class ErrorResponse(Schema):
    detail: str
```

## 좌석 예매 서비스: 낙관적 락과 비관적 락의 조합

이제 실제 티켓 예매 로직을 구현합니다. Redis 분산 락(비관적 락)과 DB의 낙관적 락을 조합하여 안정적이고 효율적인 예매 시스템을 만듭니다:

```python
# tickets/services.py
from django.db import transaction, DatabaseError
from django.utils import timezone
from datetime import timedelta
from typing import Optional
import logging

from .models import Seat, Reservation, Concert
from core.redis_lock import get_redis_lock
from core.exceptions import SeatNotAvailableError, ConcertNotFoundError

logger = logging.getLogger(__name__)

class ReservationService:
    """티켓 예매 비즈니스 로직"""
    
    def __init__(self):
        self.redis_lock = get_redis_lock()
        self.reservation_timeout_minutes = 10  # 예약 유지 시간
    
    def reserve_seat(self, user_id: int, seat_id: int) -> Reservation:
        """
        좌석 예매 메인 로직
        
        1. Redis 분산 락으로 동시 접근 제어
        2. 낙관적 락으로 DB 레벨 동시성 제어
        3. 재고 감소 및 예약 생성
        """
        lock_key = f"seat_lock:{seat_id}"
        
        try:
            # Redis 분산 락 획득 (최대 5초 대기)
            with self.redis_lock.acquire_lock(
                lock_key, 
                timeout=10, 
                blocking_timeout=5
            ):
                return self._create_reservation_with_lock(user_id, seat_id)
                
        except TimeoutError:
            logger.warning(f"Lock timeout for seat {seat_id}")
            raise SeatNotAvailableError("현재 많은 사용자가 이 좌석을 선택했습니다. 잠시 후 다시 시도해주세요.")
    
    @transaction.atomic
    def _create_reservation_with_lock(self, user_id: int, seat_id: int) -> Reservation:
        """
        트랜잭션 내에서 예약 생성
        낙관적 락(version 필드)을 사용하여 DB 레벨 동시성 제어
        """
        # SELECT FOR UPDATE로 행 락 획득
        seat = Seat.objects.select_for_update().get(id=seat_id)
        
        # 좌석 상태 검증
        if seat.status != 'AVAILABLE':
            raise SeatNotAvailableError("이미 예약된 좌석입니다.")
        
        # 공연 재고 검증
        concert = seat.concert
        if concert.available_seats <= 0:
            raise SeatNotAvailableError("매진되었습니다.")
        
        # 낙관적 락: version 체크 및 증가
        current_version = seat.version
        updated_count = Seat.objects.filter(
            id=seat_id,
            version=current_version,
            status='AVAILABLE'
        ).update(
            status='RESERVED',
            version=current_version + 1
        )
        
        if updated_count == 0:
            # 다른 트랜잭션이 먼저 업데이트함
            raise SeatNotAvailableError("좌석 예약 중 충돌이 발생했습니다. 다시 시도해주세요.")
        
        # 좌석 객체 새로고침
        seat.refresh_from_db()
        
        # Concert 재고 감소 (원자적 업데이트)
        Concert.objects.filter(id=concert.id).update(
            available_seats=models.F('available_seats') - 1
        )
        
        # 예약 생성
        expires_at = timezone.now() + timedelta(minutes=self.reservation_timeout_minutes)
        reservation = Reservation.objects.create(
            user_id=user_id,
            seat=seat,
            status='PENDING',
            expires_at=expires_at
        )
        
        logger.info(f"Reservation created: {reservation.id} for user {user_id}, seat {seat_id}")
        
        return reservation
    
    @transaction.atomic
    def confirm_reservation(self, reservation_id: int, user_id: int) -> Reservation:
        """
        예약 확정 (결제 완료 후)
        """
        reservation = Reservation.objects.select_for_update().get(
            id=reservation_id,
            user_id=user_id
        )
        
        # 만료 시간 체크
        if timezone.now() > reservation.expires_at:
            self._cancel_expired_reservation(reservation)
            raise ReservationExpiredError("예약 시간이 만료되었습니다.")
        
        # 예약 확정
        reservation.status = 'CONFIRMED'
        reservation.confirmed_at = timezone.now()
        reservation.save()
        
        # 좌석 상태 업데이트
        seat = reservation.seat
        seat.status = 'CONFIRMED'
        seat.save()
        
        logger.info(f"Reservation confirmed: {reservation.id}")
        
        return reservation
    
    @transaction.atomic
    def cancel_reservation(self, reservation_id: int, user_id: int) -> None:
        """예약 취소"""
        reservation = Reservation.objects.select_for_update().get(
            id=reservation_id,
            user_id=user_id
        )
        
        if reservation.status == 'CONFIRMED':
            raise ValueError("이미 확정된 예약은 취소할 수 없습니다.")
        
        self._release_seat(reservation)
        
        reservation.status = 'CANCELLED'
        reservation.save()
        
        logger.info(f"Reservation cancelled: {reservation.id}")
    
    def _cancel_expired_reservation(self, reservation: Reservation) -> None:
        """만료된 예약 처리"""
        self._release_seat(reservation)
        reservation.status = 'EXPIRED'
        reservation.save()
    
    def _release_seat(self, reservation: Reservation) -> None:
        """좌석 해제 및 재고 복구"""
        seat = reservation.seat
        seat.status = 'AVAILABLE'
        seat.save()
        
        # Concert 재고 증가
        Concert.objects.filter(id=seat.concert_id).update(
            available_seats=models.F('available_seats') + 1
        )
```

## API 엔드포인트 구현 및 대기열 시스템

이제 Django Ninja로 실제 API 엔드포인트를 구현하고, 대량 트래픽을 처리하기 위한 대기열 시스템을 추가합니다:

```python
# tickets/api.py (업데이트)
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from typing import List

from .models import Concert, Seat, Reservation
from .schemas import (
    ConcertSchema, 
    SeatSchema, 
    ReservationResponse, 
    ReservationRequest,
    ErrorResponse
)
from .services import ReservationService
from core.exceptions import SeatNotAvailableError, ReservationExpiredError

router = Router()
reservation_service = ReservationService()

@router.post(
    "/reservations",
    response={200: ReservationResponse, 400: ErrorResponse, 409: ErrorResponse}
)
def create_reservation(request, data: ReservationRequest):
    """
    좌석 예매
    
    - 동시성 제어를 통해 안전한 예매 처리
    - 예매 후 10분 내 결제 필요
    """
    try:
        # 인증된 사용자 확인 (실제로는 JWT 등으로 처리)
        if not request.user.is_authenticated:
            raise HttpError(401, "로그인이 필요합니다.")
        
        reservation = reservation_service.reserve_seat(
            user_id=request.user.id,
            seat_id=data.seat_id
        )
        
        return 200, reservation
        
    except SeatNotAvailableError as e:
        return 409, {"detail": str(e)}
    except Seat.DoesNotExist:
        return 400, {"detail": "존재하지 않는 좌석입니다."}
    except Exception as e:
        logger.error(f"Reservation error: {str(e)}")
        return 400, {"detail": "예매 처리 중 오류가 발생했습니다."}

@router.post(
    "/reservations/{reservation_id}/confirm",
    response={200: ReservationResponse, 400: ErrorResponse}
)
def confirm_reservation(request, reservation_id: int):
    """
    예약 확정 (결제 완료 후 호출)
    """
    try:
        if not request.user.is_authenticated:
            raise HttpError(401, "로그인이 필요합니다.")
        
        reservation = reservation_service.confirm_reservation(
            reservation_id=reservation_id,
            user_id=request.user.id
        )
        
        return 200, reservation
        
    except ReservationExpiredError as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        return 400, {"detail": "예약 확정 중 오류가 발생했습니다."}

@router.delete("/reservations/{reservation_id}")
def cancel_reservation(request, reservation_id: int):
    """예약 취소"""
    try:
        if not request.user.is_authenticated:
            raise HttpError(401, "로그인이 필요합니다.")
        
        reservation_service.cancel_reservation(
            reservation_id=reservation_id,
            user_id=request.user.id
        )
        
        return {"success": True, "message": "예약이 취소되었습니다."}
        
    except Exception as e:
        logger.error(f"Cancellation error: {str(e)}")
        raise HttpError(400, "예약 취소 중 오류가 발생했습니다.")
```

대기열 시스템 구현 (Redis Sorted Set 활용):

```python
# tickets/queue_service.py
import time
import uuid
from typing import Optional, Tuple
from core.redis_lock import get_redis_client

class WaitingQueueService:
    """
    Redis Sorted Set을 이용한 대기열 시스템
    
    - 공연별로 대기열 관리
    - 순서 보장
    - TTL 설정으로 자동 정리
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.queue_ttl = 3600  # 1시간
        self.max_active_users = 1000  # 동시 처리 가능한 최대 사용자 수
    
    def enqueue(self, concert_id: int, user_id: int) -> Tuple[str, int]:
        """
        대기열에 사용자 추가
        
        Returns:
            (token, position): 대기열 토큰과 현재 순번
        """
        queue_key = f"waiting_queue:{concert_id}"
        active_key = f"active_users:{concert_id}"
        
        # 이미 활성 사용자인지 확인
        if self.redis_client.sismember(active_key, user_id):
            return None, 0  # 이미 입장 가능
        
        # 대기열에 추가 (timestamp를 score로 사용하여 FIFO 보장)
        token = str(uuid.uuid4())
        score = time.time()
        
        self.redis_client.zadd(
            queue_key,
            {f"{user_id}:{token}": score}
        )
        
        # 현재 순번 계산
        position = self.redis_client.zrank(queue_key, f"{user_id}:{token}")
        
        return token, position + 1 if position is not None else 1
    
    def get_position(self, concert_id: int, user_id: int, token: str) -> Optional[int]:
        """현재 대기 순번 조회"""
        queue_key = f"waiting_queue:{concert_id}"
        member = f"{user_id}:{token}"
        
        position = self.redis_client.zrank(queue_key, member)
        return position + 1 if position is not None else None
    
    def promote_to_active(self, concert_id: int, batch_size: int = 100) -> int:
        """
        대기열에서 활성 사용자로 승격
        배치 단위로 처리하여 효율성 향상
        
        Returns:
            승격된 사용자 수
        """
        queue_key = f"waiting_queue:{concert_id}"
        active_key = f"active_users:{concert_id}"
        
        # 현재 활성 사용자 수 확인
        current_active = self.redis_client.scard(active_key)
        available_slots = self.max_active_users - current_active
        
        if available_slots <= 0:
            return 0
        
        # 승격할 사용자 수 결정
        promote_count = min(batch_size, available_slots)
        
        # 대기열에서 가장 앞의 사용자들 가져오기
        waiting_users = self.redis_client.zrange(queue_key, 0, promote_count - 1)
        
        if not waiting_users:
            return 0
        
        # 활성 사용자로 추가
        pipeline = self.redis_client.pipeline()
        
        for user_token in waiting_users:
            user_id = user_token.decode('utf-8').split(':')[0]
            
            # 활성 set에 추가
            pipeline.sadd(active_key, user_id)
            
            # 대기열에서 제거
            pipeline.zrem(queue_key, user_token)
        
        # TTL 설정 (1시간)
        pipeline.expire(active_key, self.queue_ttl)
        pipeline.execute()
        
        return len(waiting_users)
    
    def is_active(self, concert_id: int, user_id: int) -> bool:
        """사용자가 활성 상태인지 확인"""
        active_key = f"active_users:{concert_id}"
        return self.redis_client.sismember(active_key, user_id)
    
    def remove_from_active(self, concert_id: int, user_id: int) -> None:
        """활성 사용자에서 제거 (예매 완료 또는 타임아웃)"""
        active_key = f"active_users:{concert_id}"
        self.redis_client.srem(active_key, user_id)
```

대기열 API 엔드포인트:

```python
# tickets/api.py에 추가
from .queue_service import WaitingQueueService

queue_service = WaitingQueueService()

class QueueStatusResponse(Schema):
    token: str
    position: int
    is_active: bool
    estimated_wait_minutes: int

@router.post("/concerts/{concert_id}/queue", response=QueueStatusResponse)
def join_queue(request, concert_id: int):
    """대기열 진입"""
    if not request.user.is_authenticated:
        raise HttpError(401, "로그인이 필요합니다.")
    
    # 이미 활성 사용자인지 확인
    if queue_service.is_active(concert_id, request.user.id):
        return {
            "token": "",
            "position": 0,
            "is_active": True,
            "estimated_wait_minutes": 0
        }
    
    token, position = queue_service.enqueue(concert_id, request.user.id)
    
    # 예상 대기 시간 계산 (1분당 100명 처리 가정)
    estimated_wait = max(0, (position - 1000) // 100)
    
    return {
        "token": token,
        "position": position,
        "is_active": False,
        "estimated_wait_minutes": estimated_wait
    }

@router.get("/concerts/{concert_id}/queue/status", response=QueueStatusResponse)
def get_queue_status(request, concert_id: int, token: str):
    """대기열 상태 조회"""
    if not request.user.is_authenticated:
        raise HttpError(401, "로그인이 필요합니다.")
    
    # 활성 사용자 확인
    if queue_service.is_active(concert_id, request.user.id):
        return {
            "token": token,
            "position": 0,
            "is_active": True,
            "estimated_wait_minutes": 0
        }
    
    # 대기 순번 확인
    position = queue_service.get_position(concert_id, request.user.id, token)
    
    if position is None:
        raise HttpError(404, "대기열에서 찾을 수 없습니다. 다시 진입해주세요.")
    
    estimated_wait = max(0, (position - 1000) // 100)
    
    return {
        "token": token,
        "position": position,
        "is_active": False,
        "estimated_wait_minutes": estimated_wait
    }
```

## Celery를 활용한 비동기 작업 처리 및 성능 최적화

만료된 예약을 자동으로 처리하고, 대기열을 주기적으로 승격시키기 위해 Celery를 활용한 백그라운드 작업을 구현합니다:

```python
# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('ticket_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 주기적 작업 스케줄
app.conf.beat_schedule = {
    'cleanup-expired-reservations': {
        'task': 'tickets.tasks.cleanup_expired_reservations',
        'schedule': 60.0,  # 1분마다 실행
    },
    'promote-waiting-queue': {
        'task': 'tickets.tasks.promote_waiting_users',
        'schedule': 10.0,  # 10초마다 실행
    },
}
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

```python
# tickets/tasks.py
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import Reservation, Concert
from .services import ReservationService
from .queue_service import WaitingQueueService
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_reservations():
    """
    만료된 예약 정리 및 재고 복구
    주기적으로 실행하여 시스템 건강성 유지
    """
    now = timezone.now()
    
    # 만료된 예약 조회
    expired_reservations = Reservation.objects.filter(
        status='PENDING',
        expires_at__lt=now
    ).select_related('seat', 'seat__concert')
    
    count = 0
    service = ReservationService()
    
    for reservation in expired_reservations:
        try:
            with transaction.atomic():
                # 좌석 해제
                service._release_seat(reservation)
                
                # 예약 상태 업데이트
                reservation.status = 'EXPIRED'
                reservation.save()
                
                count += 1
                
        except Exception as e:
            logger.error(f"Failed to cleanup reservation {reservation.id}: {str(e)}")
    
    if count > 0:
        logger.info(f"Cleaned up {count} expired reservations")
    
    return count

@shared_task
def promote_waiting_users():
    """
    대기열에서 사용자를 활성 상태로 승격
    10초마다 실행하여 원활한 흐름 유지
    """
    queue_service = WaitingQueueService()
    
    # 판매 중인 모든 공연에 대해 처리
    active_concerts = Concert.objects.filter(
        sale_start_date__lte=timezone.now(),
        available_seats__gt=0
    )
    
    total_promoted = 0
    
    for concert in active_concerts:
        try:
            promoted = queue_service.promote_to_active(
                concert_id=concert.id,
                batch_size=100
            )
            total_promoted += promoted
            
        except Exception as e:
            logger.error(f"Failed to promote users for concert {concert.id}: {str(e)}")
    
    if total_promoted > 0:
        logger.info(f"Promoted {total_promoted} users from waiting queue")
    
    return total_promoted

@shared_task
def send_reservation_reminder(reservation_id: int):
    """
    예약 만료 임박 알림
    예약 후 8분에 실행 (만료 2분 전)
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        if reservation.status != 'PENDING':
            return
        
        # 실제로는 이메일/SMS/푸시 알림 발송
        logger.info(f"Reminder sent for reservation {reservation_id}")
        
        # 예시: 이메일 발송
        # send_email(
        #     to=reservation.user.email,
        #     subject="예약 만료 임박",
        #     message=f"2분 내에 결제하지 않으면 예약이 취소됩니다."
        # )
        
    except Reservation.DoesNotExist:
        logger.warning(f"Reservation {reservation_id} not found for reminder")
```

성능 최적화를 위한 추가 설정:

```python
# config/settings.py

# 데이터베이스 커넥션 풀링
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ticket_system',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # 커넥션 재사용
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30초 타임아웃
        }
    }
}

# Celery 설정
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30분
CELERY_WORKER_PREFETCH_MULTIPLIER = 4  # 동시 처리 작업 수

# 캐싱 전략
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        }
    }
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/ticket_system.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'tickets': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

Django Ninja 미들웨어로 대기열 검증 추가:

```python
# core/middleware.py
from ninja import NinjaAPI
from ninja.errors import HttpError
from tickets.queue_service import WaitingQueueService

def queue_verification_middleware(get_response):
    """
    대기열 검증 미들웨어
    특정 엔드포인트 접근 시 활성 사용자인지 확인
    """
    queue_service = WaitingQueueService()
    
    def middleware(request):
        # 예약 생성 요청인 경우에만 검증
        if request.path.startswith('/api/reservations') and request.method == 'POST':
            # concert_id 추출 (실제 구현에 맞게 조정)
            user_id = request.user.id if request.user.is_authenticated else None
            
            # 활성 사용자 확인
            # concert_id는 요청 바디에서 추출 필요
            # if user_id and not queue_service.is_active(concert_id, user_id):
            #     raise HttpError(403, "대기열에서 대기 중입니다.")
        
        response = get_response(request)
        return response
    
    return middleware
```

## 부하 테스트 및 모니터링

실제 대규모 트래픽을 처리하기 전에 시스템을 검증하는 것이 중요합니다. Locust를 사용한 부하 테스트 시나리오를 작성합니다:

```python
# locustfile.py
from locust import HttpUser, task, between
import random

class TicketBuyerUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """사용자 로그인 (테스트 시작 시)"""
        self.client.post("/api/auth/login", json={
            "username": f"user_{random.randint(1, 10000)}",
            "password": "testpass123"
        })
    
    @task(3)
    def view_concerts(self):
        """공연 목록 조회"""
        self.client.get("/api/concerts")
    
    @task(2)
    def view_seats(self):
        """좌석 조회"""
        concert_id = random.randint(1, 10)
        self.client.get(f"/api/concerts/{concert_id}/seats")
    
    @task(5)
    def join_queue(self):
        """대기열 진입"""
        concert_id = random.randint(1, 10)
        response = self.client.post(
            f"/api/concerts/{concert_id}/queue",
            name="/api/concerts/[id]/queue"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('token')
            self.concert_id = concert_id
    
    @task(4)
    def check_queue_status(self):
        """대기열 상태 확인"""
        if hasattr(self, 'token') and hasattr(self, 'concert_id'):
            self.client.get(
                f"/api/concerts/{self.concert_id}/queue/status?token={self.token}",
                name="/api/concerts/[id]/queue/status"
            )
    
    @task(1)
    def reserve_seat(self):
        """좌석 예매 시도"""
        seat_id = random.randint(1, 1000)
        self.client.post(
            "/api/reservations",
            json={"seat_id": seat_id},
            name="/api/reservations"
        )

# 실행 명령어:
# locust -f locustfile.py --host=http://localhost:8000
# 웹 UI: http://localhost:8089
```

성능 테스트 시나리오:

```bash
# 1. 단계별 부하 증가 테스트
# - 사용자: 100 -> 1000 -> 5000 -> 10000
# - Ramp up: 각 단계 1분

# 2. 스파이크 테스트
# - 0초: 100 사용자
# - 10초: 10000 사용자 (순간 폭증)
# - 30초: 100 사용자 (정상화)

# 3. 지속성 테스트
# - 5000 사용자로 1시간 지속
# - 메모리 누수, 커넥션 풀 고갈 체크
```

모니터링 대시보드 구성:

```python
# tickets/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
reservation_attempts = Counter(
    'reservation_attempts_total',
    'Total number of reservation attempts',
    ['status']
)

reservation_duration = Histogram(
    'reservation_duration_seconds',
    'Time spent processing reservation',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

waiting_queue_size = Gauge(
    'waiting_queue_size',
    'Number of users in waiting queue',
    ['concert_id']
)

active_users_count = Gauge(
    'active_users_count',
    'Number of active users',
    ['concert_id']
)

def track_reservation_metrics(func):
    """예매 메트릭 추적 데코레이터"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            reservation_attempts.labels(status='success').inc()
            return result
        except Exception as e:
            reservation_attempts.labels(status='failure').inc()
            raise
        finally:
            duration = time.time() - start_time
            reservation_duration.observe(duration)
    
    return wrapper

# 사용 예시
# tickets/services.py의 reserve_seat 메서드에 적용
# @track_reservation_metrics
# def reserve_seat(self, user_id: int, seat_id: int) -> Reservation:
#     ...
```

## 결론 및 추가 개선 사항

이번 포스트에서는 Django Ninja를 활용하여 대규모 공연 티켓 예매 시스템을 구현하는 전략을 살펴보았습니다. 핵심 내용을 정리하면:

### 구현한 주요 기능

1. **동시성 제어**: Redis 분산 락과 DB 낙관적 락의 조합으로 Race Condition 방지
2. **재고 관리**: 원자적 업데이트(`F()` 표현식)로 Overselling 방지
3. **대기열 시스템**: Redis Sorted Set을 활용한 FIFO 순서 보장
4. **비동기 처리**: Celery로 만료 예약 정리 및 대기열 승격 자동화
5. **성능 최적화**: 커넥션 풀링, 캐싱, 인덱싱 전략

### 성능 지표

적절히 튜닝된 시스템에서 기대할 수 있는 성능:

- **처리량**: 초당 1,000+ 예매 요청 처리
- **응답 시간**: P95 < 500ms, P99 < 1s
- **동시 사용자**: 10,000+ 명 동시 접속 가능
- **정확성**: 100% 재고 정합성 보장

### 추가 개선 사항

실제 프로덕션 환경에서는 다음 사항들을 추가로 고려해야 합니다:

```python
# 1. 캐싱 전략 강화
from django.core.cache import cache

def get_concert_with_cache(concert_id: int):
    """공연 정보 캐싱"""
    cache_key = f"concert:{concert_id}"
    concert = cache.get(cache_key)
    
    if concert is None:
        concert = Concert.objects.get(id=concert_id)
        cache.set(cache_key, concert, timeout=300)  # 5분
    
    return concert

# 2. 읽기 복제본 활용
class ReservationService:
    def get_available_seats(self, concert_id: int):
        """읽기 전용 쿼리는 복제본 사용"""
        return Seat.objects.using('replica').filter(
            concert_id=concert_id,
            status='AVAILABLE'
        )

# 3. Rate Limiting
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='10/m', method='POST')
def create_reservation(request, data: ReservationRequest):
    """사용자당 분당 10회 예매 시도 제한"""
    pass

# 4. 서킷 브레이커 패턴
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_payment_api(reservation_id: int):
    """결제 API 호출 시 서킷 브레이커 적용"""
    pass
```

### 아키텍처 확장

더 큰 규모로 확장하기 위한 방향:

- **샤딩**: 공연별로 DB 샤딩하여 부하 분산
- **CDN**: 정적 리소스(좌석 배치도 등) CDN으로 제공
- **MSA**: 예매, 결제, 알림을 별도 마이크로서비스로 분리
- **Event Sourcing**: 예매 과정의 모든 이벤트를 저장하여 추적성 향상
- **CQRS**: 읽기/쓰기 모델 분리로 성능 최적화

### 마치며

티켓 예매 시스템은 단순해 보이지만 동시성, 정합성, 성능을 모두 만족시켜야 하는 어려운 과제입니다. Django Ninja의 빠른 성능과 Redis, Celery를 조합하면 엔터프라이즈급 시스템을 구축할 수 있습니다.

중요한 것은 **점진적 개선**입니다. 초기에는 간단한 락 메커니즘으로 시작하고, 트래픽이 증가하면서 대기열, 캐싱, 샤딩 등을 단계적으로 추가하는 것이 현실적인 접근 방식입니다.

본 포스트의 전체 코드는 [GitHub 저장소](https://github.com/example/ticket-reservation-system)에서 확인할 수 있습니다.

### 참고 자료

- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Redis Distributed Locks](https://redis.io/docs/manual/patterns/distributed-locks/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [Database Locking Strategies](https://www.postgresql.org/docs/current/explicit-locking.html)

