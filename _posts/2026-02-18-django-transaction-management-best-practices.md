---
layout: post
title: "Django 트랜잭션 관리 완벽 가이드: 데이터 일관성을 지키는 실전 기법"
date: 2026-02-18 10:00:00 +0900
categories: [Django, Python, Database]
tags: [Django, Python, Transaction, Database, ACID, PostgreSQL, MySQL, ORM, Concurrency]
image: "/assets/img/posts/2026-02-18-django-transaction-management-best-practices.webp"
---

데이터베이스를 다루는 모든 애플리케이션에서 트랜잭션 관리는 필수적입니다. 특히 금융 거래, 전자상거래, 재고 관리 같은 중요한 비즈니스 로직에서는 데이터의 일관성이 보장되지 않으면 심각한 문제가 발생할 수 있습니다. 이 글에서는 Django에서 트랜잭션을 효과적으로 관리하는 방법과 다양한 실전 사례를 살펴보겠습니다.

## 🔒 트랜잭션이란? 왜 중요한가?

### 트랜잭션의 정의

트랜잭션(Transaction)은 데이터베이스에서 하나의 논리적 작업 단위를 의미합니다. 여러 개의 데이터베이스 작업을 하나로 묶어서 "모두 성공하거나, 모두 실패하거나" 둘 중 하나만 발생하도록 보장합니다.

### ACID 속성

트랜잭션은 다음 네 가지 핵심 속성을 보장해야 합니다:

**1. Atomicity (원자성)**
- 트랜잭션 내의 모든 작업이 완전히 수행되거나, 전혀 수행되지 않아야 합니다
- "All or Nothing" 원칙

**2. Consistency (일관성)**
- 트랜잭션이 완료되면 데이터베이스는 항상 일관된 상태를 유지해야 합니다
- 모든 제약 조건과 규칙이 위반되지 않아야 합니다

**3. Isolation (격리성)**
- 동시에 실행되는 트랜잭션들이 서로 간섭하지 않아야 합니다
- 각 트랜잭션은 독립적으로 실행되는 것처럼 보여야 합니다

**4. Durability (지속성)**
- 트랜잭션이 성공적으로 완료되면 그 결과는 영구적으로 저장되어야 합니다
- 시스템 장애가 발생해도 데이터는 보존됩니다

### 트랜잭션이 필요한 상황

트랜잭션 없이 데이터베이스 작업을 수행하면 어떤 문제가 발생할까요? 다음 예시를 살펴보겠습니다:

```python
# ❌ 트랜잭션 없는 위험한 코드
def transfer_money(from_account, to_account, amount):
    # 출금 계좌에서 차감
    from_account.balance -= amount
    from_account.save()
    
    # 만약 여기서 에러가 발생하면?
    # 네트워크 장애, 서버 크래시, 코드 에러 등
    
    # 입금 계좌에 추가
    to_account.balance += amount
    to_account.save()
```

**문제점:**
- 출금은 성공했는데 입금이 실패하면 돈이 사라집니다
- 중간에 에러가 발생하면 데이터 불일치가 발생합니다
- 동시에 여러 요청이 들어오면 잔액 계산이 틀어질 수 있습니다

```python
# ✅ 트랜잭션을 사용한 안전한 코드
from django.db import transaction

@transaction.atomic
def transfer_money(from_account, to_account, amount):
    # 출금 계좌에서 차감
    from_account.balance -= amount
    from_account.save()
    
    # 어떤 에러가 발생해도 위의 작업이 롤백됩니다
    
    # 입금 계좌에 추가
    to_account.balance += amount
    to_account.save()
    
    # 모든 작업이 성공해야만 커밋됩니다
```

**해결:**
- 모든 작업이 성공하거나 모두 취소됩니다
- 데이터 일관성이 보장됩니다
- 동시성 문제를 제어할 수 있습니다

## 🛠️ Django에서 트랜잭션 사용하기

Django는 트랜잭션 관리를 위한 강력하고 직관적인 API를 제공합니다. 가장 일반적으로 사용되는 방법들을 알아보겠습니다.

### 1. 데코레이터 방식: `@transaction.atomic`

함수나 메서드 전체를 하나의 트랜잭션으로 묶는 가장 간편한 방법입니다.

```python
from django.db import transaction

@transaction.atomic
def create_blog_post(title, content, author):
    """블로그 포스트 생성과 관련 작업을 트랜잭션으로 처리"""
    # 포스트 생성
    post = Post.objects.create(
        title=title,
        content=content,
        author=author
    )
    
    # 작성자 포스트 카운트 증가
    author.post_count += 1
    author.save()
    
    # 알림 생성
    Notification.objects.create(
        user=author,
        message=f"새 포스트 '{title}'가 게시되었습니다"
    )
    
    return post
```

**장점:**
- 코드가 간결하고 읽기 쉽습니다
- 함수가 끝나면 자동으로 커밋됩니다
- 예외 발생 시 자동으로 롤백됩니다

### 2. 컨텍스트 매니저 방식: `with transaction.atomic()`

코드의 특정 블록만 트랜잭션으로 묶고 싶을 때 사용합니다.

```python
from django.db import transaction

def process_order(order_id):
    order = Order.objects.get(id=order_id)
    
    # 주문 정보 조회는 트랜잭션 밖에서
    print(f"Processing order: {order.order_number}")
    
    # 중요한 데이터 변경만 트랜잭션으로 보호
    with transaction.atomic():
        # 재고 차감
        for item in order.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()
        
        # 주문 상태 변경
        order.status = 'CONFIRMED'
        order.save()
        
        # 결제 처리
        Payment.objects.create(
            order=order,
            amount=order.total_amount,
            status='COMPLETED'
        )
    
    # 트랜잭션 밖에서 실행 (이메일 전송은 롤백 대상 아님)
    send_order_confirmation_email(order)
```

**장점:**
- 트랜잭션 범위를 정확하게 제어할 수 있습니다
- 트랜잭션 밖의 작업(메일 발송, 로깅 등)을 분리할 수 있습니다
- 여러 트랜잭션 블록을 독립적으로 관리할 수 있습니다

### 3. 수동 트랜잭션 제어

더 세밀한 제어가 필요한 경우 수동으로 트랜잭션을 관리할 수 있습니다.

```python
from django.db import transaction

def complex_operation():
    # 수동으로 트랜잭션 시작
    with transaction.atomic():
        # 첫 번째 작업
        user = User.objects.create(username='newuser')
        
        try:
            # 외부 API 호출
            api_result = external_api_call(user.id)
            
            # API 결과에 따라 처리
            if api_result['success']:
                Profile.objects.create(user=user, data=api_result['data'])
            else:
                # 명시적으로 롤백
                raise Exception("API call failed")
                
        except Exception as e:
            # 트랜잭션 블록을 벗어나면 자동 롤백
            print(f"Transaction rolled back: {e}")
            raise
```

### 4. 데이터베이스별 트랜잭션 지정

여러 데이터베이스를 사용하는 경우 특정 DB에 대한 트랜잭션을 지정할 수 있습니다.

```python
from django.db import transaction

# 기본 데이터베이스에 대한 트랜잭션
@transaction.atomic
def save_to_default_db():
    User.objects.create(username='user1')

# 특정 데이터베이스에 대한 트랜잭션
@transaction.atomic(using='analytics_db')
def save_analytics_data():
    AnalyticsEvent.objects.using('analytics_db').create(
        event_type='page_view',
        user_id=123
    )

# 여러 데이터베이스에 대한 트랜잭션
def multi_db_operation():
    with transaction.atomic():  # 기본 DB
        User.objects.create(username='user2')
    
    with transaction.atomic(using='analytics_db'):  # 분석 DB
        AnalyticsEvent.objects.using('analytics_db').create(
            event_type='signup'
        )
```

## 💼 실전 응용 사례

이제 실무에서 자주 접하는 다양한 상황에서 트랜잭션을 어떻게 활용하는지 살펴보겠습니다.

### 사례 1: 전자상거래 주문 처리

전자상거래에서 주문 처리는 여러 단계를 거칩니다. 각 단계가 모두 성공해야만 주문이 완료됩니다.

```python
from django.db import transaction
from django.core.exceptions import ValidationError

@transaction.atomic
def process_purchase(user, cart_items, payment_method):
    """
    주문 처리 프로세스:
    1. 재고 확인 및 차감
    2. 주문 생성
    3. 결제 처리
    4. 포인트 적립
    """
    
    # 1단계: 재고 확인 및 차감
    order_items = []
    total_amount = 0
    
    for cart_item in cart_items:
        product = cart_item.product
        quantity = cart_item.quantity
        
        # 재고 체크
        if product.stock < quantity:
            raise ValidationError(
                f"{product.name}의 재고가 부족합니다. "
                f"(요청: {quantity}, 재고: {product.stock})"
            )
        
        # 재고 차감 (동시성 문제 방지를 위해 select_for_update 사용)
        product = Product.objects.select_for_update().get(id=product.id)
        product.stock -= quantity
        product.save()
        
        order_items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price
        })
        total_amount += product.price * quantity
    
    # 2단계: 주문 생성
    order = Order.objects.create(
        user=user,
        total_amount=total_amount,
        status='PENDING'
    )
    
    for item in order_items:
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            quantity=item['quantity'],
            price=item['price']
        )
    
    # 3단계: 결제 처리
    payment = Payment.objects.create(
        order=order,
        amount=total_amount,
        method=payment_method,
        status='PROCESSING'
    )
    
    # 외부 결제 게이트웨이 호출
    try:
        payment_result = payment_gateway.charge(
            amount=total_amount,
            method=payment_method
        )
        
        if not payment_result['success']:
            raise ValidationError("결제 처리에 실패했습니다")
        
        payment.transaction_id = payment_result['transaction_id']
        payment.status = 'COMPLETED'
        payment.save()
        
    except Exception as e:
        payment.status = 'FAILED'
        payment.save()
        raise ValidationError(f"결제 오류: {str(e)}")
    
    # 4단계: 주문 완료 및 포인트 적립
    order.status = 'CONFIRMED'
    order.save()
    
    points_earned = int(total_amount * 0.01)  # 1% 적립
    user.points += points_earned
    user.save()
    
    PointHistory.objects.create(
        user=user,
        points=points_earned,
        reason=f"주문 #{order.id} 적립"
    )
    
    return order
```

**핵심 포인트:**
- 재고 차감, 주문 생성, 결제, 포인트 적립이 모두 성공해야 커밋됩니다
- 중간에 실패하면 모든 작업이 롤백되어 데이터 일관성이 유지됩니다
- `select_for_update()`로 동시성 문제를 방지합니다

### 사례 2: 회원 가입과 프로필 생성

회원 가입 시 User, Profile, 초기 설정 등 여러 테이블에 데이터를 생성해야 합니다.

```python
from django.db import transaction
from django.contrib.auth.models import User

@transaction.atomic
def register_user(username, email, password, profile_data):
    """
    회원 가입 프로세스:
    1. User 생성
    2. Profile 생성
    3. 기본 설정 생성
    4. 환영 알림 생성
    5. 추천인 포인트 지급
    """
    
    # 1. User 생성
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # 2. Profile 생성
    profile = Profile.objects.create(
        user=user,
        full_name=profile_data.get('full_name', ''),
        phone=profile_data.get('phone', ''),
        birth_date=profile_data.get('birth_date'),
        bio=profile_data.get('bio', '')
    )
    
    # 3. 기본 설정 생성
    UserSettings.objects.create(
        user=user,
        email_notifications=True,
        newsletter=True,
        language='ko'
    )
    
    # 4. 환영 알림 생성
    Notification.objects.create(
        user=user,
        title="가입을 환영합니다!",
        message=f"{username}님, 가입을 환영합니다. 지금 바로 서비스를 이용해보세요.",
        type='WELCOME'
    )
    
    # 5. 추천인 포인트 지급
    referral_code = profile_data.get('referral_code')
    if referral_code:
        try:
            referrer = User.objects.get(profile__referral_code=referral_code)
            
            # 추천인에게 포인트 지급
            referrer.points += 1000
            referrer.save()
            
            PointHistory.objects.create(
                user=referrer,
                points=1000,
                reason=f"{username}님 추천으로 적립"
            )
            
            # 신규 가입자에게도 포인트 지급
            user.points = 500
            user.save()
            
            PointHistory.objects.create(
                user=user,
                points=500,
                reason="추천 코드 사용 보너스"
            )
            
        except User.DoesNotExist:
            pass  # 추천 코드가 유효하지 않으면 무시
    
    return user
```

**핵심 포인트:**
- User, Profile, Settings, Notification 등 여러 모델이 동시에 생성됩니다
- 추천인 시스템처럼 다른 사용자의 데이터도 함께 수정됩니다
- 모든 작업이 원자적으로 처리되어 부분 가입을 방지합니다

### 사례 3: 금융 거래 - 송금

금융 거래는 트랜잭션이 가장 중요한 영역 중 하나입니다.

```python
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

@transaction.atomic
def transfer_money(from_user, to_user, amount):
    """
    송금 프로세스:
    1. 잔액 확인
    2. 출금 계좌에서 차감
    3. 입금 계좌에 추가
    4. 거래 내역 기록
    """
    
    # 금액 검증
    if amount <= 0:
        raise ValidationError("송금 금액은 0보다 커야 합니다")
    
    # 동시성 문제 방지를 위해 row-level lock 획득
    from_account = Account.objects.select_for_update().get(user=from_user)
    to_account = Account.objects.select_for_update().get(user=to_user)
    
    # 1. 잔액 확인
    if from_account.balance < amount:
        raise ValidationError(
            f"잔액이 부족합니다. "
            f"(잔액: {from_account.balance}, 요청: {amount})"
        )
    
    # 2. 출금
    from_account.balance -= amount
    from_account.save()
    
    # 3. 입금
    to_account.balance += amount
    to_account.save()
    
    # 4. 거래 내역 기록
    transaction_record = Transaction.objects.create(
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        type='TRANSFER',
        status='COMPLETED'
    )
    
    # 송금자 거래 내역
    TransactionHistory.objects.create(
        account=from_account,
        transaction=transaction_record,
        amount=-amount,
        balance_after=from_account.balance,
        description=f"{to_user.username}님에게 송금"
    )
    
    # 수취인 거래 내역
    TransactionHistory.objects.create(
        account=to_account,
        transaction=transaction_record,
        amount=amount,
        balance_after=to_account.balance,
        description=f"{from_user.username}님으로부터 입금"
    )
    
    return transaction_record
```

**핵심 포인트:**
- `select_for_update()`로 동시 송금 요청 시 데이터 무결성을 보장합니다
- 잔액 확인부터 거래 완료까지 전체가 원자적으로 처리됩니다
- 출금과 입금이 모두 성공해야만 커밋됩니다

### 사례 4: 재고 관리와 벌크 업데이트

대량의 재고를 한 번에 업데이트해야 하는 경우입니다.

```python
from django.db import transaction

@transaction.atomic
def process_inventory_adjustment(adjustments):
    """
    재고 조정 프로세스:
    adjustments = [
        {'product_id': 1, 'quantity_change': -10, 'reason': 'DAMAGED'},
        {'product_id': 2, 'quantity_change': 50, 'reason': 'RESTOCK'},
        ...
    ]
    """
    
    adjustment_records = []
    
    for adjustment in adjustments:
        product_id = adjustment['product_id']
        quantity_change = adjustment['quantity_change']
        reason = adjustment['reason']
        
        # Lock을 걸고 제품 가져오기
        product = Product.objects.select_for_update().get(id=product_id)
        
        # 현재 재고 기록
        old_stock = product.stock
        
        # 재고 변경
        new_stock = old_stock + quantity_change
        
        # 음수 재고 방지
        if new_stock < 0:
            raise ValidationError(
                f"제품 '{product.name}'의 재고가 음수가 될 수 없습니다. "
                f"(현재: {old_stock}, 변경: {quantity_change})"
            )
        
        product.stock = new_stock
        product.save()
        
        # 재고 변경 이력 기록
        record = InventoryAdjustment.objects.create(
            product=product,
            old_stock=old_stock,
            new_stock=new_stock,
            quantity_change=quantity_change,
            reason=reason
        )
        adjustment_records.append(record)
        
        # 재고 부족 알림 체크
        if new_stock < product.minimum_stock:
            Notification.objects.create(
                title=f"재고 부족 알림: {product.name}",
                message=f"현재 재고: {new_stock}, 최소 재고: {product.minimum_stock}",
                type='LOW_STOCK',
                severity='WARNING'
            )
    
    return adjustment_records
```

**핵심 포인트:**
- 여러 제품의 재고를 한 번에 조정합니다
- 하나라도 실패하면 모든 조정이 롤백됩니다
- 각 조정마다 이력이 기록됩니다

### 사례 5: 파일 업로드와 데이터베이스 연동

파일 업로드와 데이터베이스 작업을 함께 처리하는 경우입니다.

```python
from django.db import transaction
from django.core.files.storage import default_storage

def upload_document_with_transaction(file, user, metadata):
    """
    문서 업로드 프로세스:
    1. 파일 저장
    2. DB 레코드 생성
    3. 사용자 통계 업데이트
    """
    
    file_path = None
    
    try:
        with transaction.atomic():
            # 1. 파일 저장 (트랜잭션 안에서)
            file_path = default_storage.save(
                f"documents/{user.id}/{file.name}",
                file
            )
            file_url = default_storage.url(file_path)
            
            # 2. DB 레코드 생성
            document = Document.objects.create(
                user=user,
                title=metadata.get('title', file.name),
                file_path=file_path,
                file_url=file_url,
                file_size=file.size,
                file_type=file.content_type,
                description=metadata.get('description', '')
            )
            
            # 3. 사용자 통계 업데이트
            user.document_count += 1
            user.total_storage_used += file.size
            
            # 저장공간 제한 체크
            if user.total_storage_used > user.storage_limit:
                raise ValidationError(
                    f"저장공간이 부족합니다. "
                    f"(사용: {user.total_storage_used}, 제한: {user.storage_limit})"
                )
            
            user.save()
            
            # 4. 활동 로그 생성
            ActivityLog.objects.create(
                user=user,
                action='DOCUMENT_UPLOADED',
                details=f"문서 '{document.title}' 업로드 완료"
            )
            
            return document
            
    except Exception as e:
        # 트랜잭션 롤백 시 업로드된 파일도 삭제
        if file_path and default_storage.exists(file_path):
            default_storage.delete(file_path)
        raise
```

**핵심 포인트:**
- 파일 저장과 DB 작업을 하나의 트랜잭션으로 처리합니다
- 실패 시 업로드된 파일도 함께 삭제합니다
- 저장공간 제한을 체크하여 초과를 방지합니다

### 사례 6: 배치 작업 - 대량 데이터 처리

대량의 데이터를 처리하되, 일부 실패가 전체에 영향을 주지 않도록 합니다.

```python
from django.db import transaction

def process_bulk_user_updates(user_updates):
    """
    대량 사용자 정보 업데이트
    각 사용자는 독립적인 트랜잭션으로 처리
    """
    
    success_count = 0
    failed_items = []
    
    for update_data in user_updates:
        try:
            # 각 업데이트를 독립적인 트랜잭션으로 처리
            with transaction.atomic():
                user_id = update_data['user_id']
                user = User.objects.select_for_update().get(id=user_id)
                
                # 사용자 정보 업데이트
                if 'email' in update_data:
                    user.email = update_data['email']
                if 'phone' in update_data:
                    user.profile.phone = update_data['phone']
                    user.profile.save()
                
                user.save()
                
                # 업데이트 이력 기록
                UpdateHistory.objects.create(
                    user=user,
                    updated_fields=list(update_data.keys()),
                    timestamp=timezone.now()
                )
                
                success_count += 1
                
        except Exception as e:
            # 개별 실패는 기록하고 계속 진행
            failed_items.append({
                'user_id': update_data.get('user_id'),
                'error': str(e)
            })
    
    return {
        'success_count': success_count,
        'failed_count': len(failed_items),
        'failed_items': failed_items
    }


@transaction.atomic
def process_monthly_subscriptions():
    """
    월간 구독 갱신 처리
    모든 갱신이 성공해야 커밋
    """
    
    today = timezone.now().date()
    
    # 오늘 갱신할 구독 조회
    subscriptions = Subscription.objects.filter(
        next_billing_date=today,
        status='ACTIVE'
    ).select_for_update()
    
    processed = []
    
    for subscription in subscriptions:
        user = subscription.user
        plan = subscription.plan
        
        # 결제 시도
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            amount=plan.price,
            status='PROCESSING'
        )
        
        try:
            # 결제 처리
            result = payment_gateway.charge(
                user=user,
                amount=plan.price
            )
            
            if result['success']:
                payment.status = 'COMPLETED'
                payment.transaction_id = result['transaction_id']
                payment.save()
                
                # 구독 기간 연장
                subscription.next_billing_date = today + timedelta(days=30)
                subscription.save()
                
                processed.append(subscription.id)
            else:
                payment.status = 'FAILED'
                payment.save()
                
                # 결제 실패 알림
                Notification.objects.create(
                    user=user,
                    title="구독 결제 실패",
                    message=f"구독 '{plan.name}' 결제에 실패했습니다.",
                    type='PAYMENT_FAILED'
                )
                
        except Exception as e:
            payment.status = 'FAILED'
            payment.error_message = str(e)
            payment.save()
            raise  # 트랜잭션 롤백
    
    return processed
```

**핵심 포인트:**
- 첫 번째 예제는 각 항목을 독립적으로 처리하여 부분 실패를 허용합니다
- 두 번째 예제는 모든 구독 갱신이 성공해야 커밋됩니다
- 사용 사례에 따라 적절한 트랜잭션 범위를 선택합니다

## 🚀 고급 트랜잭션 패턴

더 복잡한 시나리오를 위한 고급 트랜잭션 패턴들을 살펴보겠습니다.

### 1. 중첩 트랜잭션과 세이브포인트

Django는 중첩된 트랜잭션을 세이브포인트를 통해 지원합니다.

```python
from django.db import transaction

@transaction.atomic
def create_blog_post_with_images(post_data, images):
    """
    블로그 포스트와 이미지를 생성
    이미지 업로드 실패는 허용하되, 포스트는 반드시 생성
    """
    
    # 외부 트랜잭션: 포스트 생성
    post = Post.objects.create(
        title=post_data['title'],
        content=post_data['content'],
        author=post_data['author']
    )
    
    uploaded_images = []
    failed_images = []
    
    # 각 이미지는 독립적인 세이브포인트로 처리
    for image in images:
        try:
            # 내부 트랜잭션 (세이브포인트 생성)
            with transaction.atomic():
                image_obj = PostImage.objects.create(
                    post=post,
                    image=image,
                    caption=image.name
                )
                uploaded_images.append(image_obj)
                
        except Exception as e:
            # 개별 이미지 실패는 무시하고 계속 진행
            failed_images.append({'name': image.name, 'error': str(e)})
    
    # 포스트는 반드시 생성되고, 성공한 이미지들만 연결됨
    return {
        'post': post,
        'uploaded_images': uploaded_images,
        'failed_images': failed_images
    }
```

### 2. 동시성 제어: select_for_update()

여러 사용자가 동시에 같은 데이터를 수정할 때 발생하는 문제를 방지합니다.

```python
from django.db import transaction

@transaction.atomic
def reserve_seat(user, concert_id, seat_number):
    """
    콘서트 좌석 예약 (동시성 제어)
    """
    
    # Row-level lock 획득
    # nowait=True: 이미 락이 걸려있으면 즉시 에러
    # skip_locked=True: 락이 걸린 행은 건너뛰기
    
    try:
        seat = Seat.objects.select_for_update(nowait=True).get(
            concert_id=concert_id,
            seat_number=seat_number
        )
    except DatabaseError:
        raise ValidationError("다른 사용자가 이 좌석을 예약 중입니다.")
    
    # 좌석 상태 확인
    if seat.status != 'AVAILABLE':
        raise ValidationError("이미 예약된 좌석입니다.")
    
    # 예약 생성
    reservation = Reservation.objects.create(
        user=user,
        seat=seat,
        status='CONFIRMED'
    )
    
    # 좌석 상태 변경
    seat.status = 'RESERVED'
    seat.reserved_by = user
    seat.reserved_at = timezone.now()
    seat.save()
    
    return reservation


def get_available_seats_and_reserve(concert_id, user, seat_count=1):
    """
    사용 가능한 좌석을 찾아서 예약
    skip_locked를 사용하여 경쟁 없는 좌석 선택
    """
    
    with transaction.atomic():
        # 락이 걸리지 않은 좌석만 조회
        available_seats = Seat.objects.select_for_update(
            skip_locked=True
        ).filter(
            concert_id=concert_id,
            status='AVAILABLE'
        )[:seat_count]
        
        if len(available_seats) < seat_count:
            raise ValidationError(f"사용 가능한 좌석이 {seat_count}개 미만입니다.")
        
        reservations = []
        for seat in available_seats:
            reservation = Reservation.objects.create(
                user=user,
                seat=seat,
                status='CONFIRMED'
            )
            
            seat.status = 'RESERVED'
            seat.reserved_by = user
            seat.reserved_at = timezone.now()
            seat.save()
            
            reservations.append(reservation)
        
        return reservations
```

### 3. 낙관적 잠금 (Optimistic Locking)

충돌이 적을 것으로 예상되는 경우 버전 필드를 사용한 낙관적 잠금을 사용할 수 있습니다.

```python
from django.db import models, transaction
from django.core.exceptions import ValidationError

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    version = models.IntegerField(default=0)  # 버전 필드
    updated_at = models.DateTimeField(auto_now=True)

@transaction.atomic
def update_article_with_optimistic_lock(article_id, new_content, expected_version):
    """
    낙관적 잠금을 사용한 아티클 업데이트
    """
    
    article = Article.objects.get(id=article_id)
    
    # 버전 체크
    if article.version != expected_version:
        raise ValidationError(
            "다른 사용자가 이 문서를 수정했습니다. "
            "페이지를 새로고침하고 다시 시도해주세요."
        )
    
    # 업데이트 수행
    article.content = new_content
    article.version += 1  # 버전 증가
    article.save()
    
    return article


# Django ORM의 F 표현식을 사용한 자동 버전 증가
@transaction.atomic
def update_article_atomic(article_id, new_content):
    """
    F 표현식으로 race condition 방지
    """
    from django.db.models import F
    
    # 업데이트와 버전 증가를 하나의 쿼리로
    updated_count = Article.objects.filter(
        id=article_id
    ).update(
        content=new_content,
        version=F('version') + 1
    )
    
    if updated_count == 0:
        raise ValidationError("아티클을 찾을 수 없습니다.")
    
    return Article.objects.get(id=article_id)
```

### 4. 트랜잭션 후 작업 수행: on_commit()

트랜잭션이 성공적으로 커밋된 후에만 실행해야 하는 작업이 있습니다.

```python
from django.db import transaction

@transaction.atomic
def create_order_and_send_notification(order_data):
    """
    주문 생성 후 알림 전송
    트랜잭션이 커밋된 후에만 알림 전송
    """
    
    # 주문 생성
    order = Order.objects.create(
        user=order_data['user'],
        total_amount=order_data['total_amount']
    )
    
    # 트랜잭션이 성공적으로 커밋된 후 실행
    transaction.on_commit(lambda: send_order_email(order.id))
    transaction.on_commit(lambda: send_push_notification(order.user.id, order.id))
    transaction.on_commit(lambda: update_external_system(order.id))
    
    return order


def send_order_email(order_id):
    """이메일 발송은 트랜잭션 커밋 후 실행"""
    order = Order.objects.get(id=order_id)
    # 이메일 발송 로직
    print(f"Sending email for order {order_id}")


@transaction.atomic
def process_payment_with_webhook(payment_data):
    """
    결제 처리 및 외부 웹훅 호출
    """
    
    payment = Payment.objects.create(
        amount=payment_data['amount'],
        status='COMPLETED'
    )
    
    # 성공 후 외부 API 호출
    def notify_external_system():
        try:
            external_api.notify_payment(payment.id)
        except Exception as e:
            # 외부 API 실패는 로깅만 하고 트랜잭션에 영향 없음
            logger.error(f"External API failed: {e}")
    
    transaction.on_commit(notify_external_system)
    
    return payment
```

### 5. 격리 수준 설정

특정 상황에서는 트랜잭션 격리 수준을 조정해야 할 수 있습니다.

```python
from django.db import transaction

# PostgreSQL 격리 수준 설정
def high_consistency_operation():
    """
    높은 일관성이 필요한 작업
    PostgreSQL의 SERIALIZABLE 격리 수준 사용
    """
    from django.db import connection
    
    with transaction.atomic():
        # 격리 수준 설정
        cursor = connection.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        
        # 중요한 비즈니스 로직
        # ...
        pass


# settings.py에서 전역 설정
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
        },
        ...
    }
}
"""
```

## ⚠️ 주의사항과 베스트 프랙티스

### 1. 트랜잭션 범위는 최소화하기

```python
# ❌ 나쁜 예: 트랜잭션이 너무 큼
@transaction.atomic
def bad_example():
    user = User.objects.create(username='newuser')
    
    # 외부 API 호출 (느림)
    api_result = external_api.call()  # 5초 소요
    
    # 복잡한 계산 (느림)
    result = complex_calculation()  # 10초 소요
    
    # 파일 업로드 (느림)
    upload_to_s3(file)  # 3초 소요
    
    user.save()
    # 트랜잭션이 18초 동안 유지됨 - 데이터베이스 부하!


# ✅ 좋은 예: 필요한 부분만 트랜잭션으로
def good_example():
    # 외부 작업은 트랜잭션 밖에서
    api_result = external_api.call()
    result = complex_calculation()
    s3_url = upload_to_s3(file)
    
    # DB 작업만 트랜잭션으로
    with transaction.atomic():
        user = User.objects.create(username='newuser')
        user.api_data = api_result
        user.calculation_result = result
        user.file_url = s3_url
        user.save()
```

### 2. 트랜잭션 내에서 예외 처리하기

```python
# ❌ 나쁜 예: 예외를 삼켜버림
@transaction.atomic
def bad_exception_handling():
    try:
        User.objects.create(username='user1')
        raise Exception("Error!")
    except:
        pass  # 트랜잭션이 커밋되어 부분 데이터 생성!


# ✅ 좋은 예: 예외를 다시 발생시킴
@transaction.atomic
def good_exception_handling():
    try:
        User.objects.create(username='user1')
        risky_operation()
    except SpecificError as e:
        logger.error(f"Error: {e}")
        raise  # 트랜잭션 롤백
```

### 3. select_for_update() 사용 시 주의사항

```python
# ❌ 나쁜 예: 데드락 위험
@transaction.atomic
def deadlock_risk():
    # 사용자 A: 계좌1 -> 계좌2 순서로 락
    account1 = Account.objects.select_for_update().get(id=1)
    account2 = Account.objects.select_for_update().get(id=2)
    
    # 사용자 B: 계좌2 -> 계좌1 순서로 락
    # 데드락 발생!


# ✅ 좋은 예: 일관된 순서로 락 획득
@transaction.atomic
def avoid_deadlock(from_id, to_id):
    # 항상 작은 ID부터 락 획득
    first_id, second_id = sorted([from_id, to_id])
    
    account1 = Account.objects.select_for_update().get(id=first_id)
    account2 = Account.objects.select_for_update().get(id=second_id)
    
    # 안전하게 작업 수행
```

### 4. 긴 트랜잭션 피하기

```python
# ❌ 나쁜 예: 대량 데이터를 하나의 트랜잭션으로
@transaction.atomic
def process_all_users():
    users = User.objects.all()  # 100만 명
    for user in users:
        user.send_email()  # 트랜잭션이 몇 시간 동안 유지!
        user.save()


# ✅ 좋은 예: 청크 단위로 처리
def process_users_in_chunks(chunk_size=1000):
    user_ids = User.objects.values_list('id', flat=True)
    
    for i in range(0, len(user_ids), chunk_size):
        chunk_ids = user_ids[i:i+chunk_size]
        
        with transaction.atomic():
            users = User.objects.filter(id__in=chunk_ids)
            for user in users:
                user.processed = True
                user.save()
```

### 5. autocommit 모드 이해하기

```python
from django.db import transaction

# Django의 기본 모드는 autocommit
# 각 쿼리가 즉시 커밋됨

User.objects.create(username='user1')  # 즉시 커밋
User.objects.create(username='user2')  # 즉시 커밋

# autocommit 비활성화 (일반적으로 권장하지 않음)
transaction.set_autocommit(False)
try:
    User.objects.create(username='user3')
    User.objects.create(username='user4')
    transaction.commit()  # 수동으로 커밋
except:
    transaction.rollback()  # 수동으로 롤백
finally:
    transaction.set_autocommit(True)
```

### 6. 테스트 작성하기

```python
from django.test import TransactionTestCase
from django.db import transaction

class TransactionTests(TransactionTestCase):
    """트랜잭션 테스트"""
    
    def test_transaction_rollback(self):
        """트랜잭션 롤백 테스트"""
        initial_count = User.objects.count()
        
        with self.assertRaises(Exception):
            with transaction.atomic():
                User.objects.create(username='user1')
                User.objects.create(username='user2')
                raise Exception("Force rollback")
        
        # 롤백되어 카운트가 증가하지 않음
        self.assertEqual(User.objects.count(), initial_count)
    
    def test_concurrent_updates(self):
        """동시성 테스트"""
        from django.db import connection
        from threading import Thread
        
        account = Account.objects.create(balance=1000)
        
        def withdraw(amount):
            with transaction.atomic():
                acc = Account.objects.select_for_update().get(id=account.id)
                acc.balance -= amount
                acc.save()
        
        # 두 스레드가 동시에 출금 시도
        t1 = Thread(target=withdraw, args=(100,))
        t2 = Thread(target=withdraw, args=(200,))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # 잔액이 정확하게 계산됨
        account.refresh_from_db()
        self.assertEqual(account.balance, 700)
```

## 📊 성능 고려사항

트랜잭션 사용 시 성능에 미치는 영향을 이해하는 것이 중요합니다.

### 트랜잭션 격리 수준별 성능

| 격리 수준 | 동시성 | 일관성 | 사용 사례 |
|---------|--------|--------|---------|
| READ UNCOMMITTED | 가장 높음 | 가장 낮음 | 로그 수집, 통계 |
| READ COMMITTED | 높음 | 보통 | 대부분의 일반 작업 |
| REPEATABLE READ | 보통 | 높음 | 금융 거래, 재고 관리 |
| SERIALIZABLE | 가장 낮음 | 가장 높음 | 극도로 중요한 작업 |

### 성능 최적화 팁

```python
# 1. 불필요한 쿼리 줄이기
@transaction.atomic
def optimized_bulk_create():
    """bulk_create로 한 번에 삽입"""
    users = [
        User(username=f'user{i}', email=f'user{i}@example.com')
        for i in range(1000)
    ]
    User.objects.bulk_create(users, batch_size=100)


# 2. select_related와 prefetch_related 사용
@transaction.atomic
def optimized_query():
    """N+1 쿼리 문제 방지"""
    orders = Order.objects.select_related('user').prefetch_related('items')
    
    for order in orders:
        # 추가 쿼리 없이 접근 가능
        print(order.user.username)
        for item in order.items.all():
            print(item.product.name)


# 3. 조건부 업데이트
@transaction.atomic
def conditional_update():
    """조건에 맞는 레코드만 업데이트"""
    from django.db.models import F
    
    # 재고가 10개 미만인 제품만 재입고
    Product.objects.filter(
        stock__lt=10
    ).update(
        stock=F('stock') + 100
    )


# 4. 인덱스 활용
class Product(models.Model):
    sku = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    stock = models.IntegerField(db_index=True)  # 자주 검색되는 필드
    
    class Meta:
        indexes = [
            models.Index(fields=['sku', 'stock']),  # 복합 인덱스
        ]
```

## 🎯 실전 체크리스트

트랜잭션을 사용할 때 다음 체크리스트를 확인하세요:

### 설계 단계
- [ ] 트랜잭션이 정말 필요한가?
- [ ] ACID 속성 중 어떤 것이 중요한가?
- [ ] 트랜잭션 범위가 적절한가?
- [ ] 동시성 문제가 발생할 수 있는가?
- [ ] 예상되는 트랜잭션 시간은?

### 구현 단계
- [ ] `@transaction.atomic` 또는 `with transaction.atomic()` 사용
- [ ] 필요한 경우 `select_for_update()` 적용
- [ ] 예외 처리가 올바른가?
- [ ] 외부 시스템 호출은 트랜잭션 밖에 있는가?
- [ ] `transaction.on_commit()` 필요한가?

### 테스트 단계
- [ ] 정상 케이스 테스트
- [ ] 롤백 케이스 테스트
- [ ] 동시성 테스트
- [ ] 성능 테스트
- [ ] 데드락 시나리오 테스트

### 모니터링 단계
- [ ] 긴 트랜잭션 모니터링
- [ ] 데드락 발생 모니터링
- [ ] 락 대기 시간 모니터링
- [ ] 트랜잭션 롤백 비율 모니터링

## 🔍 트러블슈팅

자주 발생하는 문제와 해결 방법입니다.

### 1. "database is locked" 에러 (SQLite)

```python
# SQLite는 동시 쓰기를 지원하지 않음
# 해결책: PostgreSQL이나 MySQL 사용 권장

# 또는 timeout 늘리기
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 기본값 5초에서 증가
        }
    }
}
```

### 2. 데드락 발생

```python
# 데드락 발생 시 재시도 로직
def retry_on_deadlock(func, max_retries=3):
    """데드락 발생 시 자동 재시도"""
    from django.db import OperationalError
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if 'deadlock' in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))  # 지수 백오프
                continue
            raise


@transaction.atomic
def transfer_with_retry(from_id, to_id, amount):
    """데드락 방지 및 재시도"""
    return retry_on_deadlock(
        lambda: transfer_money(from_id, to_id, amount)
    )
```

### 3. TransactionManagementError

```python
# 에러: "Transaction managed block ended with pending COMMIT/ROLLBACK"

# ❌ 원인: 중첩된 트랜잭션에서 수동 커밋
@transaction.atomic
def wrong_way():
    User.objects.create(username='user1')
    transaction.commit()  # 에러 발생!


# ✅ 해결: atomic 블록 안에서는 자동으로 처리
@transaction.atomic
def right_way():
    User.objects.create(username='user1')
    # 블록이 끝나면 자동으로 커밋됨
```

## 📚 참고 자료

Django 공식 문서와 추가 학습 자료입니다.

### Django 공식 문서
- [Database transactions](https://docs.djangoproject.com/en/5.0/topics/db/transactions/)
- [Query Expressions](https://docs.djangoproject.com/en/5.0/ref/models/expressions/)
- [Database Functions](https://docs.djangoproject.com/en/5.0/ref/models/database-functions/)

### 데이터베이스별 특성
- **PostgreSQL**: 가장 강력한 트랜잭션 지원, MVCC 사용
- **MySQL/MariaDB**: InnoDB 엔진 필수, REPEATABLE READ가 기본
- **SQLite**: 파일 기반, 동시 쓰기 제한적

### 추천 라이브러리
- `django-db-locking`: 추가적인 락 기능
- `django-transaction-hooks`: 다양한 트랜잭션 훅
- `django-extensions`: 디버깅 도구

## 🎓 결론

Django의 트랜잭션 관리는 데이터 일관성과 무결성을 보장하는 핵심 기능입니다. 이 글에서 다룬 내용을 정리하면:

### 핵심 요약

1. **트랜잭션의 중요성**
   - ACID 속성으로 데이터 일관성 보장
   - 금융, 전자상거래 등 중요한 비즈니스 로직에 필수

2. **Django 트랜잭션 사용법**
   - `@transaction.atomic` 데코레이터
   - `with transaction.atomic()` 컨텍스트 매니저
   - 데이터베이스별 트랜잭션 지정

3. **실전 응용 사례**
   - 전자상거래 주문 처리
   - 회원 가입 및 프로필 생성
   - 금융 거래 및 송금
   - 재고 관리
   - 파일 업로드와 DB 연동
   - 배치 작업

4. **고급 패턴**
   - 중첩 트랜잭션과 세이브포인트
   - `select_for_update()`로 동시성 제어
   - 낙관적 잠금
   - `transaction.on_commit()` 활용
   - 격리 수준 설정

5. **베스트 프랙티스**
   - 트랜잭션 범위 최소화
   - 올바른 예외 처리
   - 데드락 방지
   - 긴 트랜잭션 피하기
   - 충분한 테스트 작성

### 마지막 조언

트랜잭션은 강력한 도구이지만, 과도하게 사용하면 성능 문제를 일으킬 수 있습니다. 다음 원칙을 기억하세요:

- **필요한 곳에만 사용하기**: 모든 작업에 트랜잭션이 필요한 것은 아닙니다
- **범위를 최소화하기**: 꼭 필요한 작업만 트랜잭션으로 묶으세요
- **테스트하기**: 동시성 문제는 프로덕션에서 발견되기 전에 테스트로 찾아내세요
- **모니터링하기**: 긴 트랜잭션과 데드락을 지속적으로 모니터링하세요

Django의 트랜잭션 API를 제대로 이해하고 활용하면, 안정적이고 신뢰할 수 있는 애플리케이션을 만들 수 있습니다. 여러분의 프로젝트에서 데이터 일관성이 항상 보장되기를 바랍니다! 🚀

