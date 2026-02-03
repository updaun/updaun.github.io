---
layout: post
title: "Django ORM 고급 활용법 - 성능 최적화를 위한 쿼리 엔지니어링"
date: 2026-02-03
categories: django
author: updaun
image: "/assets/img/posts/2026-02-03-django-orm-advanced-optimization.webp"
---

# Django ORM 고급 활용법 - 성능 최적화를 위한 쿼리 엔지니어링

Django ORM은 강력하고 표현력 있는 도구이지만, 무심코 사용하면 데이터베이스로 수백 개의 불필요한 쿼리를 날릴 수 있습니다. 이 글에서는 Django 개발자들이 반드시 알아야 할 ORM 최적화 기법을 실전 예제와 함께 소개합니다. N+1 문제 해결, 대량 데이터 처리, 집계 및 집합 연산, 인덱싱 전략까지 다루며, 각 기법마다 최적화 전후의 쿼리를 비교해 실제 성능 차이를 명확히 보여드립니다. 이 가이드를 따르면 같은 기능을 구현해도 데이터베이스 부하를 10배 이상 줄일 수 있습니다.

## 모델 설정 및 예제 데이터베이스 구조

이 글에서 사용할 예제를 위해 기본적인 모델 구조를 정의합니다. 전자상거래 플랫폼을 예로 들어 상품(Product), 주문(Order), 주문 항목(OrderItem), 리뷰(Review), 카테고리(Category) 모델을 만듭니다.

```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    """상품 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """상품"""
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Order(models.Model):
    """주문"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    """주문에 포함된 상품"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('order', 'product')
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

class Review(models.Model):
    """상품 리뷰"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"Review of {self.product.name} by {self.user.username}"
```

이 모델 구조를 바탕으로 이후의 모든 예제를 진행합니다. 테스트용 데이터는 다음과 같이 생성합니다.

```python
# manage.py shell
from django.contrib.auth.models import User
from myapp.models import Category, Product, Order, OrderItem, Review

# 사용자 생성
users = [User.objects.create_user(f"user{i}", f"user{i}@example.com", "password") for i in range(1, 101)]

# 카테고리 생성
categories = [Category.objects.create(name=f"Category {i}") for i in range(1, 11)]

# 상품 생성 (1000개)
products = [
    Product.objects.create(
        name=f"Product {i}",
        category=categories[i % 10],
        price=10 + (i % 100),
        stock=100
    ) for i in range(1, 1001)
]

# 주문 생성 (1000개)
orders = [
    Order.objects.create(
        user=users[i % 100],
        total_price=50 + i
    ) for i in range(1, 1001)
]

# 주문 항목 생성 (각 주문당 2~5개)
for order in orders:
    for _ in range(2 + (order.id % 4)):
        product = products[order.id % len(products)]
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1 + (order.id % 5),
            price=product.price
        )

# 리뷰 생성
for i, product in enumerate(products[:500]):  # 처음 500개 상품에만 리뷰
    for j in range(2):
        Review.objects.create(
            product=product,
            user=users[i % 100],
            rating=3 + (i % 3),
            text=f"Great product! {i}"
        )
```

## N+1 쿼리 문제와 select_related를 통한 최적화

Django 초보자들이 가장 자주 범하는 실수가 N+1 쿼리 문제입니다. 주문 목록과 함께 각 주문의 사용자 정보를 표시해야 한다고 가정해봅시다. 다음 코드를 보면 문제가 명확해집니다.

```python
# 최적화 되지 않은 쿼리 - N+1 문제 발생
def get_orders_unoptimized():
    """주문 목록 조회 (N+1 문제)"""
    orders = Order.objects.all()  # 1개 쿼리
    
    for order in orders:
        print(f"User: {order.user.username}")  # N개 쿼리 (각 주문마다 User 조회)
    
    # 총 N+1개 쿼리: 1 (주문 조회) + 1000 (각 주문의 사용자 조회)

# 최적화된 쿼리 - select_related 사용
def get_orders_optimized():
    """주문 목록 조회 (select_related로 최적화)"""
    orders = Order.objects.select_related('user').all()  # 1개 쿼리 (JOIN 포함)
    
    for order in orders:
        print(f"User: {order.user.username}")  # 추가 쿼리 없음
    
    # 총 1개 쿼리: JOIN으로 한 번에 조회
```

`select_related()`는 SQL의 `INNER JOIN`을 사용해 관련 객체를 미리 로드합니다. ForeignKey나 OneToOneField 관계에 효과적이며, 관계가 일대일이거나 다대일이므로 결과 행 수가 늘어나지 않습니다. 더 복잡한 예제를 봅시다.

```python
# 좀 더 복잡한 케이스: 주문 항목과 함께 상품, 카테고리 정보도 필요
def get_order_items_unoptimized():
    """주문 항목 조회 (여러 단계의 N+1 문제)"""
    order_items = OrderItem.objects.all()  # 1개 쿼리
    
    for item in order_items:
        print(f"Product: {item.product.name}")  # N개 쿼리
        print(f"Category: {item.product.category.name}")  # N개 추가 쿼리
    
    # 총 1 + N + N = 1 + 2N개 쿼리

def get_order_items_optimized():
    """주문 항목 조회 (select_related로 최적화)"""
    order_items = OrderItem.objects.select_related('product', 'product__category').all()
    
    for item in order_items:
        print(f"Product: {item.product.name}")  # 캐시된 데이터 사용
        print(f"Category: {item.product.category.name}")  # 캐시된 데이터 사용
    
    # 총 1개 쿼리 (JOIN으로 모두 조회)
```

위 코드에서 주목할 점은 `select_related('product', 'product__category')`의 이중 언더스코어(`__`) 문법입니다. 이를 통해 관계의 깊이를 마음대로 설정할 수 있습니다. Django ORM이 자동으로 필요한 JOIN을 구성합니다. 성능 측정을 위해 `django.test.utils.override_settings`와 `django.db.connection.queries`를 사용합시다.

```python
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase

@override_settings(DEBUG=True)
def test_query_count():
    """쿼리 카운트 비교"""
    # 최적화 전
    connection.queries_log.clear()
    orders_unopt = Order.objects.all()
    for order in orders_unopt:
        _ = order.user.username
    unoptimized_queries = len(connection.queries)
    
    # 최적화 후
    connection.queries_log.clear()
    orders_opt = Order.objects.select_related('user').all()
    for order in orders_opt:
        _ = order.user.username
    optimized_queries = len(connection.queries)
    
    print(f"Unoptimized: {unoptimized_queries} queries")  # 1001
    print(f"Optimized: {optimized_queries} queries")  # 1
    print(f"Improvement: {unoptimized_queries / optimized_queries:.0f}x")  # 1001x
```

실제로 이 코드를 실행하면 1001개 쿼리가 1개로 줄어드는 것을 확인할 수 있습니다.

## prefetch_related를 활용한 역방향 관계와 Many-to-Many 최적화

ForeignKey는 `select_related()`로 쉽게 최적화되지만, 역방향 관계(역참조)나 ManyToManyField는 다릅니다. 이들은 일대다 관계이므로 SQL JOIN만으로는 효율적이지 않습니다. 예를 들어 각 상품의 모든 리뷰를 가져와야 한다고 가정해봅시다.

```python
# 최적화 되지 않은 쿼리 - 각 상품마다 리뷰 조회
def get_products_with_reviews_unoptimized():
    """상품 목록과 리뷰 조회 (N+1 문제)"""
    products = Product.objects.all()  # 1개 쿼리
    
    for product in products:
        reviews = product.reviews.all()  # N개 쿼리 (각 상품마다 리뷰 조회)
        print(f"{product.name}: {reviews.count()} reviews")
    
    # 총 1 + N개 쿼리

# 최적화된 쿼리 - prefetch_related 사용
from django.db.models import Prefetch

def get_products_with_reviews_optimized():
    """상품 목록과 리뷰 조회 (prefetch_related로 최적화)"""
    products = Product.objects.prefetch_related('reviews').all()
    # 2개 쿼리: 1) 모든 상품 조회, 2) 모든 상품의 리뷰를 한 번에 조회
    
    for product in products:
        reviews = product.reviews.all()  # 추가 쿼리 없음 (이미 메모리에 있음)
        print(f"{product.name}: {reviews.count()} reviews")
    
    # 총 2개 쿼리
```

`prefetch_related()`는 별도의 쿼리로 관련 객체들을 메모리에 로드한 후 Python에서 연결합니다. 역방향 관계와 ManyToManyField에 필수적입니다. 더 세밀한 제어를 위해 `Prefetch` 객체를 사용할 수 있습니다.

```python
# Prefetch 객체로 더 정교한 제어
from django.db.models import Prefetch, Count

def get_products_with_top_reviews():
    """각 상품의 상위 3개 리뷰만 가져오기"""
    # reviews를 모두 가져오는 대신 필터링된 쿼리를 지정
    top_reviews = Review.objects.order_by('-rating')[:3]
    products = Product.objects.prefetch_related(
        Prefetch('reviews', queryset=top_reviews)
    ).all()
    
    for product in products:
        print(f"{product.name}:")
        for review in product.reviews.all():  # 이미 필터링된 리뷰만 있음
            print(f"  - Rating: {review.rating}")

# select_related와 prefetch_related 조합
def get_orders_with_all_details():
    """주문과 주문 항목, 상품, 사용자 정보를 모두 조회"""
    orders = Order.objects.select_related('user').prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('product')
        )
    ).all()
    
    for order in orders:
        print(f"Order #{order.id} by {order.user.username}")
        for item in order.items.all():
            print(f"  - {item.product.name}")
    
    # 총 3개 쿼리: 1) 주문 + 사용자, 2) 주문 항목 + 상품, 3) 각 상품의 카테고리
```

위 코드는 한 번에 모든 필요한 데이터를 미리 로드하므로 데이터베이스 왕복을 최소화합니다. 쿼리 카운트 비교를 다시 해보면:

```python
@override_settings(DEBUG=True)
def test_prefetch_vs_unoptimized():
    """prefetch_related의 효과 측정"""
    # 최적화 전: N+1 문제
    connection.queries_log.clear()
    products = Product.objects.all()
    for product in products:
        _ = list(product.reviews.all())
    unoptimized = len(connection.queries)
    
    # 최적화 후
    connection.queries_log.clear()
    products = Product.objects.prefetch_related('reviews').all()
    for product in products:
        _ = list(product.reviews.all())
    optimized = len(connection.queries)
    
    print(f"Unoptimized: {unoptimized} queries")  # 1001
    print(f"Optimized: {optimized} queries")  # 2
    print(f"Improvement: {unoptimized / optimized:.0f}x")  # 500.5x
```

## only()와 defer()로 불필요한 칼럼 제외하기

큰 TextField나 JSONField를 포함한 모델의 경우, 모든 칼럼을 조회하는 것이 비효율적일 수 있습니다. `only()`와 `defer()`를 사용해 필요한 칼럼만 선택적으로 로드할 수 있습니다.

```python
# 불필요한 칼럼까지 모두 로드
def get_products_unoptimized():
    """모든 칼럼 조회"""
    products = Product.objects.all()  # name, price, stock, created_at, description 등 모두 로드
    
    for product in products:
        print(f"{product.name}: ${product.price}")
        # description 칼럼은 사용하지 않지만 메모리에 로드됨

# only()로 필요한 칼럼만 로드
def get_products_optimized_only():
    """필요한 칼럼만 선택"""
    products = Product.objects.only('id', 'name', 'price').all()
    # SELECT id, name, price FROM ... (네트워크 트래픽 감소)
    
    for product in products:
        print(f"{product.name}: ${product.price}")

# defer()로 특정 칼럼만 제외
def get_products_optimized_defer():
    """특정 칼럼만 제외"""
    products = Product.objects.defer('description').all()
    # SELECT id, name, price, stock, created_at FROM ... (description만 제외)
    
    for product in products:
        print(f"{product.name}: ${product.price}")
    
    # 나중에 description이 필요하면 그때 별도 쿼리 발생
    for product in products:
        print(f"Description: {product.description}")  # 추가 쿼리 발생
```

실제 사용할 때의 차이를 봅시다:

```python
from django.db.models import functions
from django.db.models import F

# API 응답용 데이터 로드 (이름과 가격만 필요)
def api_product_list():
    """API 응답에 필요한 최소 데이터만 로드"""
    products = Product.objects.only('id', 'name', 'price', 'category_id').all()
    
    return [
        {
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
        }
        for p in products
    ]

# only()와 select_related 조합
def get_products_with_category():
    """상품과 카테고리 정보, 필요한 칼럼만"""
    products = Product.objects.select_related('category').only(
        'id', 'name', 'price', 'category__name'
    ).all()
    
    for product in products:
        print(f"{product.name} in {product.category.name}")

# 쿼리 비교
@override_settings(DEBUG=True)
def test_only_vs_all():
    """only의 효과 측정 (데이터 크기)"""
    connection.queries_log.clear()
    products = Product.objects.all()
    _ = list(products)
    all_columns = connection.queries[0]['sql']
    
    connection.queries_log.clear()
    products = Product.objects.only('id', 'name', 'price')
    _ = list(products)
    only_columns = connection.queries[0]['sql']
    
    print(f"All columns: {len(all_columns)} chars")
    print(f"Only columns: {len(only_columns)} chars")
    print(f"Data reduction: {(1 - len(only_columns) / len(all_columns)) * 100:.1f}%")
```

주의할 점은 `defer()`와 `only()`는 데이터 로드 방식을 바꾸므로, 이후에 해당 칼럼을 사용하면 추가 쿼리가 발생합니다. 또한 `model_to_dict()`나 serializer를 사용할 때도 영향을 미칩니다.

## F 객체와 Q 객체를 활용한 고급 필터링

데이터베이스 수준의 연산을 위해 `F` 객체를 사용하면 Python 메모리 사용을 줄이고 성능을 극대화할 수 있습니다.

```python
# 최적화 안 된 방법: Python에서 연산
def update_product_prices_unoptimized():
    """모든 상품의 가격을 10% 인상 (나쁜 방법)"""
    products = Product.objects.all()  # 1000개 행을 메모리에 로드
    
    for product in products:
        product.price = product.price * 1.1
        product.save()  # 각각 UPDATE 쿼리 발생 (1000개)
    
    # 총 1001개 쿼리, 메모리 사용량 많음

# F 객체를 사용한 최적화 방법
from django.db.models import F

def update_product_prices_optimized():
    """모든 상품의 가격을 10% 인상 (최적화된 방법)"""
    Product.objects.all().update(price=F('price') * 1.1)
    
    # 단 1개 쿼리: UPDATE product SET price = price * 1.1
```

`F` 객체는 데이터베이스에서 직접 필드 값을 연산합니다. 이는 Django로 모든 데이터를 로드해서 Python에서 연산하는 것보다 훨씬 빠릅니다. 더 복잡한 예제를 봅시다.

```python
from django.db.models import F, Q, Case, When, Value, CharField

# 복합 연산: 재고를 주문 수에 따라 감소
def decrease_stock_optimized():
    """주문 항목에 따라 상품 재고 감소 (최적화)"""
    from django.db.models import Sum, Subquery, OuterRef
    
    # OrderItem에서 각 상품별 총 수량 합계를 구해 stock에서 빼기
    subquery = OrderItem.objects.filter(
        product=OuterRef('pk')
    ).values('product').annotate(
        total=Sum('quantity')
    ).values('total')
    
    Product.objects.all().update(
        stock=F('stock') - Subquery(subquery)
    )

# Q 객체를 활용한 복잡한 필터링
def get_popular_products():
    """인기 상품 조회: 가격이 50 이상이고, 리뷰가 10개 이상이거나 판매량이 100 이상"""
    from django.db.models import Count
    
    products = Product.objects.annotate(
        review_count=Count('reviews'),
        sale_count=Count('orderitem')
    ).filter(
        Q(price__gte=50) & (
            Q(review_count__gte=10) | Q(sale_count__gte=100)
        )
    )
    
    return products

# F 객체로 서로 다른 필드 비교
def find_discrepancy_products():
    """실제 가격과 기록된 가격이 다른 상품 찾기"""
    # actual_price 필드가 있다고 가정
    products = Product.objects.exclude(
        price=F('actual_price')
    ).all()
    
    return products

# 조건부 업데이트: CASE-WHEN 사용
def update_product_categories():
    """가격에 따라 상품을 다른 카테고리로 이동"""
    Category.objects.filter(name='Premium').update(
        discount_percentage=Case(
            When(price__gte=100, then=Value(20)),  # 100 이상이면 20% 할인
            When(price__gte=50, then=Value(10)),   # 50 이상이면 10% 할인
            default=Value(5),                       # 나머지는 5% 할인
            output_field=CharField()
        )
    )
```

`F` 객체의 장점은:
- **성능**: 데이터베이스에서 연산하므로 네트워크 트래픽 최소화
- **원자성**: 여러 프로세스의 동시 업데이트에서 안전
- **간결성**: Python 루프 제거로 코드가 간단해짐

## bulk_create와 bulk_update로 대량 작업 처리

대량의 객체를 생성하거나 수정할 때 개별 `save()` 호출 대신 `bulk_create()`나 `bulk_update()`를 사용해야 합니다.

```python
# 최적화 안 된 방법: 개별 저장
def create_orders_unoptimized(order_data_list):
    """주문 1000개 생성 (나쁜 방법)"""
    orders = []
    for data in order_data_list:
        order = Order(
            user_id=data['user_id'],
            total_price=data['total_price']
        )
        order.save()  # 각각 INSERT 쿼리 (1000개)
    
    # 총 1000개 쿼리, 약 1000ms 소요

# bulk_create를 사용한 최적화
def create_orders_optimized(order_data_list):
    """주문 1000개 생성 (최적화)"""
    orders = [
        Order(
            user_id=data['user_id'],
            total_price=data['total_price']
        )
        for data in order_data_list
    ]
    Order.objects.bulk_create(orders, batch_size=100)
    
    # 단 10개 쿼리 (100개씩 배치), 약 50ms 소요 (20배 빠름)
```

`bulk_create()`는 여러 행을 한 번에 INSERT합니다. `batch_size` 파라미터로 배치 크기를 조정하면 메모리와 성능의 균형을 맞출 수 있습니다.

```python
from django.db.models import F, Case, When, Value

# bulk_update 예제
def update_product_reviews_optimized():
    """모든 상품의 평균 리뷰 점수를 업데이트 (한 번에)"""
    from django.db.models import Avg
    
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating')
    ).all()
    
    # 평균 점수를 avg_rating 필드에 저장한다고 가정
    for product in products:
        product.avg_rating = product.avg_rating or 0
    
    Product.objects.bulk_update(products, ['avg_rating'], batch_size=100)
    
    # 약 10개 쿼리로 1000개 상품 업데이트

# 더 효율적인 방법: bulk_create와 get_or_create 조합
def sync_external_products(external_data):
    """외부 API에서 받은 상품 데이터 동기화"""
    products_to_create = []
    
    for data in external_data:
        try:
            product = Product.objects.get(external_id=data['id'])
            # 이미 존재하면 업데이트 준비
            product.name = data['name']
            product.price = data['price']
            products_to_create.append(product)
        except Product.DoesNotExist:
            # 없으면 생성 준비
            products_to_create.append(
                Product(
                    external_id=data['id'],
                    name=data['name'],
                    price=data['price']
                )
            )
    
    # 한 번에 저장
    Product.objects.bulk_create(
        [p for p in products_to_create if p.id is None],
        ignore_conflicts=True
    )
```

주의할 점:
- `bulk_create()`는 각 인스턴스의 `id`를 반환하지 않음 (데이터베이스 설정에 따라 다름)
- 시그널이 발동하지 않음 (pre_save, post_save 등)
- 모델의 `save()` 메서드가 호출되지 않음

필요한 경우 `bulk_create()` 후에 따로 처리해야 합니다:

```python
def create_orders_with_signal(order_data_list):
    """bulk_create 후 추가 작업 수행"""
    orders = [
        Order(user_id=data['user_id'], total_price=data['total_price'])
        for data in order_data_list
    ]
    
    # bulk_create는 signal을 발동하지 않으므로 직접 호출
    created_orders = Order.objects.bulk_create(orders)
    
    # 추가 작업 (예: 로깅, 알림 전송 등)
    for order in created_orders:
        send_order_confirmation(order)
```

## aggregation과 annotation을 활용한 집계 쿼리

데이터를 그룹화하고 집계할 때 Python 루프 대신 데이터베이스의 집계 함수를 사용하면 훨씬 효율적입니다.

```python
from django.db.models import Count, Sum, Avg, Max, Min, F, Value
from django.db.models.functions import Coalesce

# 최적화 안 된 방법: Python에서 계산
def calculate_order_stats_unoptimized():
    """주문 통계 계산 (나쁜 방법)"""
    orders = Order.objects.all()
    
    total_orders = len(orders)
    total_revenue = sum(order.total_price for order in orders)  # 메모리에 로드 필요
    avg_revenue = total_revenue / total_orders if total_orders else 0
    
    return {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_revenue': avg_revenue
    }

# aggregate()를 사용한 최적화
def calculate_order_stats_optimized():
    """주문 통계 계산 (최적화)"""
    stats = Order.objects.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
        avg_revenue=Avg('total_price'),
        max_revenue=Max('total_price'),
        min_revenue=Min('total_price')
    )
    
    # 단 1개 쿼리: SELECT COUNT(*), SUM(...), AVG(...) FROM order
    return stats
```

`aggregate()`는 전체 데이터에 대한 하나의 결과를 반환합니다. 반면 `annotate()`는 각 행에 새 필드를 추가합니다.

```python
# annotate()를 사용한 그룹별 통계
def get_category_sales_stats():
    """카테고리별 판매 통계"""
    stats = Category.objects.annotate(
        product_count=Count('products'),
        total_revenue=Sum('products__orderitem__price'),
        avg_product_price=Avg('products__price'),
        max_product_price=Max('products__price')
    ).all()
    
    for category in stats:
        print(f"{category.name}: {category.product_count} products, ${category.total_revenue}")
    
    # 1개 쿼리로 모든 카테고리의 통계 계산

# filter()와 annotate() 조합
def get_popular_products_with_stats():
    """리뷰가 10개 이상이고 평균 점수가 4 이상인 상품"""
    products = Product.objects.annotate(
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
        total_sales=Sum('orderitem__quantity')
    ).filter(
        review_count__gte=10,
        avg_rating__gte=4
    ).order_by('-total_sales')
    
    return products

# 조건부 집계
def get_user_order_analysis():
    """사용자별 주문 분석"""
    from django.db.models import Q
    
    users = User.objects.annotate(
        total_orders=Count('orders'),
        total_spent=Sum('orders__total_price'),
        high_value_orders=Count(
            'orders',
            filter=Q(orders__total_price__gte=100)
        ),
        avg_order_value=Avg('orders__total_price')
    ).filter(total_orders__gt=0).order_by('-total_spent')
    
    return users

# 다중 레벨 annotate
def get_detailed_product_analysis():
    """상품의 상세 분석"""
    products = Product.objects.annotate(
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
        rating_distribution=Count(
            'reviews__rating',
            filter=Q(reviews__rating=5)
        ),  # 5점 리뷰 개수
        total_quantity_sold=Sum('orderitem__quantity'),
        revenue=Sum(
            F('orderitem__price') * F('orderitem__quantity'),
            output_field=models.DecimalField()
        )
    ).order_by('-revenue')
    
    return products

# aggregation 성능 비교
@override_settings(DEBUG=True)
def test_aggregate_performance():
    """aggregate의 성능 측정"""
    # Python에서 계산
    connection.queries_log.clear()
    orders = list(Order.objects.all())
    total = sum(o.total_price for o in orders)
    python_queries = len(connection.queries)
    
    # aggregate 사용
    connection.queries_log.clear()
    total = Order.objects.aggregate(Sum('total_price'))['total_price__sum']
    aggregate_queries = len(connection.queries)
    
    print(f"Python approach: {python_queries} queries")  # 2 (select all + count)
    print(f"Aggregate approach: {aggregate_queries} queries")  # 1
    print(f"Memory: Python loads all rows, Aggregate returns only result")
```

annotate의 강력한 점은 여러 집계를 한 번의 쿼리로 계산할 수 있다는 것입니다. 복잡한 비즈니스 로직도 단일 쿼리로 표현 가능합니다.

## values()와 values_list()를 활용한 최소 데이터 로드

ORM 모델 인스턴스를 생성하지 않고 딕셔너리나 튜플로 데이터를 받으면 메모리 사용을 줄일 수 있습니다.

```python
# 일반적인 방법: 모든 필드를 가진 모델 인스턴스 생성
def get_product_names_unoptimized():
    """상품 이름 목록 조회 (불필요한 객체 생성)"""
    products = Product.objects.all()
    names = [product.name for product in products]  # 1000개 Product 인스턴스 생성
    
    return names

# values()를 사용: 딕셔너리로 반환
def get_product_names_optimized():
    """상품 이름 목록 조회 (최적화)"""
    products = Product.objects.values('id', 'name')
    # 메모리에 딕셔너리만 생성
    
    names = [p['name'] for p in products]
    return names

# values_list()를 사용: 튜플로 반환
def get_product_names_flat():
    """상품 이름만 평탄화 리스트로"""
    names = Product.objects.values_list('name', flat=True)
    # SELECT name FROM product
    # ['Product 1', 'Product 2', ...]
    
    return names

# values()와 annotate() 조합
def get_category_stats_dict():
    """카테고리별 통계를 딕셔너리로"""
    stats = Category.objects.values('name').annotate(
        product_count=Count('products'),
        avg_price=Avg('products__price')
    )
    
    # [
    #   {'name': 'Electronics', 'product_count': 150, 'avg_price': 299.99},
    #   {'name': 'Books', 'product_count': 300, 'avg_price': 15.99}
    # ]
    
    return list(stats)

# JSON 응답용 데이터
def api_get_products_json():
    """API 응답용 상품 데이터"""
    products = Product.objects.values('id', 'name', 'price').all()
    
    # serializer 없이도 바로 JSON 변환 가능 (custom encoder 필요)
    return [
        {
            'id': p['id'],
            'name': p['name'],
            'price': float(p['price'])
        }
        for p in products
    ]

# 성능 비교
@override_settings(DEBUG=True)
def test_values_memory():
    """values()의 메모리 효율성"""
    import sys
    
    # 일반 쿼리: Product 인스턴스 생성
    products_obj = Product.objects.all()
    obj_size = sys.getsizeof(list(products_obj))
    
    # values() 사용
    products_dict = Product.objects.values('id', 'name', 'price')
    dict_size = sys.getsizeof(list(products_dict))
    
    print(f"Model instances: {obj_size / 1024:.1f} KB")
    print(f"Values dict: {dict_size / 1024:.1f} KB")
    print(f"Memory savings: {(1 - dict_size / obj_size) * 100:.1f}%")
    # 보통 50~70% 메모리 절약
```

주의할 점은 `values()`로 반환된 쿼리셋은 모델 메서드를 사용할 수 없다는 것입니다.

```python
# 잘못된 사용
products = Product.objects.values('id', 'name')
for p in products:
    p.save()  # AttributeError: 'dict' object has no attribute 'save'

# 올바른 사용
products = Product.objects.all()
for p in products:
    p.save()  # OK
```

## exists()와 count()의 올바른 사용

데이터 존재 여부 확인이나 개수 조회에도 최적화가 필요합니다.

```python
# 비효율적인 방법
def check_product_exists_bad():
    """상품이 존재하는지 확인 (나쁜 방법)"""
    # 모든 상품을 메모리에 로드 후 길이 확인
    if len(Product.objects.all()) > 0:
        print("Products exist")

def count_products_bad():
    """상품 개수 조회 (나쁜 방법)"""
    # 모든 상품을 메모리에 로드 후 길이 확인
    count = len(Product.objects.all())

# 효율적인 방법
def check_product_exists_good():
    """상품이 존재하는지 확인 (최적화)"""
    # SELECT 1 FROM product LIMIT 1 (첫 행만 확인)
    if Product.objects.exists():
        print("Products exist")

def count_products_good():
    """상품 개수 조회 (최적화)"""
    # SELECT COUNT(*) FROM product
    count = Product.objects.count()

# 필터링된 쿼리의 존재 여부
def get_active_orders():
    """활성 주문 확인"""
    if Order.objects.filter(status='pending').exists():
        return Order.objects.filter(status='pending').all()
    else:
        return []

# 더 효율적인 버전
def get_active_orders_optimized():
    """활성 주문 확인 (쿼리 1회)"""
    orders = Order.objects.filter(status='pending')
    if orders.exists():  # 이미 필터링된 쿼리셋 사용
        return orders
    else:
        return []

# 복합 조건의 효율성
def find_users_with_high_value_orders():
    """고가 주문이 있는 사용자 찾기"""
    from django.contrib.auth.models import User
    
    # 비효율적: 모든 사용자를 로드
    users = User.objects.all()
    result = []
    for user in users:
        if user.orders.filter(total_price__gte=1000).exists():
            result.append(user)
    
    # 효율적: 단일 쿼리로 필터링
    users = User.objects.filter(
        orders__total_price__gte=1000
    ).distinct()
    
    return users
```

## 인덱싱과 쿼리 플래닝

데이터베이스의 성능은 올바른 인덱싱에 따라 크게 달라집니다. Django 모델에서 인덱스를 설정하는 방법을 살펴봅시다.

```python
from django.db import models

class OptimizedProduct(models.Model):
    """인덱싱이 적용된 상품 모델"""
    name = models.CharField(max_length=200, db_index=True)  # 이름으로 자주 검색
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        related_name='products',
        db_index=True  # FK는 자동 인덱싱되지만 명시적으로 설정
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_index=True  # 가격 범위 검색에 사용
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True  # 최신 상품 조회 시 사용
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'price']),  # 복합 인덱스
            models.Index(fields=['created_at', '-price']),  # 정렬과 함께 사용
        ]
```

인덱스의 효과를 측정해봅시다:

```python
@override_settings(DEBUG=True)
def test_index_impact():
    """인덱스 사용 전후 성능 비교"""
    from django.db import connection
    from django.test.utils import override_settings
    
    # 인덱스 없는 필드로 검색
    connection.queries_log.clear()
    start = time.time()
    products = Product.objects.filter(description__startswith='Premium').all()
    unindexed_time = time.time() - start
    unindexed_query = connection.queries[0]['sql']
    
    # 인덱스 있는 필드로 검색
    connection.queries_log.clear()
    start = time.time()
    products = Product.objects.filter(name__startswith='Premium').all()
    indexed_time = time.time() - start
    indexed_query = connection.queries[0]['sql']
    
    print(f"Unindexed field: {unindexed_time*1000:.2f}ms")
    print(f"Indexed field: {indexed_time*1000:.2f}ms")
    print(f"Speed improvement: {unindexed_time / indexed_time:.1f}x")
    
    # 실행 계획 확인
    print("\nUnindexed query plan:")
    print(unindexed_query)
    print("\nIndexed query plan:")
    print(indexed_query)
```

쿼리 실행 계획을 분석하려면 데이터베이스 도구를 사용합니다:

```python
# PostgreSQL에서 EXPLAIN 사용
def analyze_query_plan():
    """쿼리 실행 계획 분석"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # EXPLAIN으로 쿼리 계획 조회
        cursor.execute("""
            EXPLAIN ANALYZE
            SELECT * FROM product WHERE price > 100 AND category_id = 5
        """)
        plan = cursor.fetchall()
        
        for row in plan:
            print(row)

# 느린 쿼리 찾기
def log_slow_queries():
    """느린 쿼리 감지"""
    from django.db import connection
    from django.db.models.signals import post_init
    import time
    
    def slow_query_check(sender, **kwargs):
        if len(connection.queries) > 0:
            last_query = connection.queries[-1]
            if float(last_query['time']) > 0.5:  # 500ms 이상
                print(f"Slow query detected: {last_query['sql']}")
    
    post_init.connect(slow_query_check)
```

## 트랜잭션과 데이터베이스 잠금

여러 쿼리를 하나의 트랜잭션으로 묶으면 일관성을 보장하고 성능을 최적화할 수 있습니다.

```python
from django.db import transaction

# 개별 저장 (각각 트랜잭션)
def create_order_items_without_transaction(order, items_data):
    """주문 항목 생성 (트랜잭션 없음)"""
    for data in items_data:
        OrderItem.objects.create(
            order=order,
            product_id=data['product_id'],
            quantity=data['quantity'],
            price=data['price']
        )
        # 각 저장이 별도 트랜잭션

# 트랜잭션으로 묶기
@transaction.atomic
def create_order_items_with_transaction(order, items_data):
    """주문 항목 생성 (트랜잭션으로 묶음)"""
    for data in items_data:
        OrderItem.objects.create(
            order=order,
            product_id=data['product_id'],
            quantity=data['quantity'],
            price=data['price']
        )
    
    # 모든 저장을 하나의 트랜잭션으로
    # 중간에 에러 발생 시 모두 롤백

# 명시적 트랜잭션
def process_refund(order):
    """환불 처리 (원자성 필요)"""
    with transaction.atomic():
        order.status = 'refunded'
        order.save()
        
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        # 하나라도 실패하면 전체 롤백

# savepoint로 부분 롤백
def complex_order_processing(order, items_data):
    """복잡한 주문 처리"""
    with transaction.atomic():
        order.status = 'processing'
        order.save()
        
        try:
            with transaction.atomic():
                for data in items_data:
                    OrderItem.objects.create(**data)
        except Exception as e:
            print(f"Item creation failed: {e}")
            # savepoint로 항목 생성만 롤백, 주문 상태는 유지

# 데이터베이스 잠금
def safe_stock_update(product_id, quantity):
    """재고 업데이트 (경합 방지)"""
    with transaction.atomic():
        # select_for_update로 해당 행을 잠금
        product = Product.objects.select_for_update().get(id=product_id)
        
        if product.stock >= quantity:
            product.stock -= quantity
            product.save()
            return True
        return False

# 타임아웃 설정
def update_with_timeout(order_id):
    """타임아웃이 있는 업데이트"""
    try:
        with transaction.atomic(durable=True):  # 더 엄격한 격리 수준
            order = Order.objects.select_for_update(
                timeout=5  # 5초 이내에 잠금 획득
            ).get(id=order_id)
            
            order.status = 'paid'
            order.save()
    except transaction.DatabaseError:
        print("Failed to acquire lock within timeout")
```

## 쿼리 최적화 실전 예제: 주문 관리 시스템

지금까지 배운 모든 기법을 종합한 실제 사용 사례를 봅시다.

```python
from django.db.models import (
    F, Q, Sum, Count, Avg, Max, Value, Case, When,
    Prefetch, OuterRef, Subquery
)
from django.db import transaction

class OrderManagementService:
    """주문 관리 시스템"""
    
    @staticmethod
    def get_order_summary():
        """모든 주문의 요약 통계 (1쿼리)"""
        return Order.objects.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price'),
            avg_order_value=Avg('total_price'),
            max_order_value=Max('total_price')
        )
    
    @staticmethod
    def get_user_order_history(user_id):
        """사용자의 주문 이력 (최적화)"""
        return Order.objects.filter(
            user_id=user_id
        ).select_related('user').prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('product')
            )
        ).annotate(
            item_count=Count('items'),
            product_count=Count('items__product')
        ).order_by('-created_at')
    
    @staticmethod
    def get_popular_products(limit=10):
        """인기 상품 조회"""
        return Product.objects.annotate(
            sale_count=Count('orderitem'),
            revenue=Sum(F('orderitem__price') * F('orderitem__quantity')),
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).filter(sale_count__gt=0).order_by('-revenue')[:limit]
    
    @staticmethod
    def get_category_performance():
        """카테고리별 성과"""
        return Category.objects.annotate(
            product_count=Count('products'),
            total_sales=Sum('products__orderitem__quantity'),
            total_revenue=Sum('products__orderitem__price'),
            avg_product_rating=Avg('products__reviews__rating')
        ).filter(product_count__gt=0).values(
            'name', 'product_count', 'total_sales', 
            'total_revenue', 'avg_product_rating'
        )
    
    @staticmethod
    @transaction.atomic
    def create_bulk_orders(orders_data):
        """대량 주문 생성"""
        orders = [
            Order(user_id=data['user_id'], total_price=data['total_price'])
            for data in orders_data
        ]
        Order.objects.bulk_create(orders, batch_size=100)
    
    @staticmethod
    def apply_discount_to_high_value_users():
        """고가치 사용자에게 할인 적용"""
        high_value_users = User.objects.annotate(
            total_spent=Sum('orders__total_price')
        ).filter(total_spent__gte=1000)
        
        # 선택적: 별도 할인 필드가 있다면
        for user in high_value_users:
            user.vip_discount = Case(
                When(total_spent__gte=5000, then=Value(20)),
                When(total_spent__gte=2000, then=Value(15)),
                default=Value(10)
            )
        
        # 또는 bulk_update로 한 번에
        # User.objects.bulk_update(high_value_users, ['vip_discount'])
    
    @staticmethod
    def find_low_stock_products():
        """재고 부족 상품 찾기"""
        return Product.objects.annotate(
            pending_orders=Count('orderitem')
        ).filter(
            Q(stock__lt=10) | Q(stock__lt=F('pending_orders'))
        ).values('name', 'stock', 'pending_orders')
    
    @staticmethod
    def get_user_recommendations(user_id, limit=5):
        """사용자 추천 상품 (구매하지 않은 카테고리)"""
        purchased_categories = User.objects.filter(
            id=user_id
        ).values_list('orders__items__product__category_id', flat=True).distinct()
        
        return Product.objects.exclude(
            category_id__in=purchased_categories
        ).annotate(
            popularity=Count('orderitem'),
            avg_rating=Avg('reviews__rating')
        ).filter(
            popularity__gt=0,
            avg_rating__gte=4
        ).order_by('-popularity')[:limit]

# API 엔드포인트에서 사용
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def api_order_summary(request):
    """주문 통계 API"""
    stats = OrderManagementService.get_order_summary()
    return JsonResponse({
        'total_orders': stats['total_orders'],
        'total_revenue': float(stats['total_revenue']),
        'avg_order_value': float(stats['avg_order_value']),
    })

@require_http_methods(["GET"])
def api_popular_products(request):
    """인기 상품 API"""
    products = OrderManagementService.get_popular_products(limit=10)
    
    return JsonResponse({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'sales': p.sale_count,
                'revenue': float(p.revenue),
                'rating': float(p.avg_rating) if p.avg_rating else 0,
            }
            for p in products
        ]
    })
```

이 서비스 클래스는 모든 최적화 기법을 실제로 적용한 예제입니다. 각 메서드는 최소한의 데이터베이스 쿼리로 필요한 정보를 제공합니다.

## django-debug-toolbar로 쿼리 분석

실제 프로젝트에서는 `django-debug-toolbar`를 사용해 쿼리 성능을 모니터링합니다.

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django.contrib.staticfiles',
    'debug_toolbar',
]

MIDDLEWARE = [
    # ...
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']

# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
```

Django Debug Toolbar는 다음을 제공합니다:
- 쿼리 목록 및 실행 시간
- 중복 쿼리 감지
- 쿼리 실행 계획
- 템플릿 렌더링 시간
- 캐시 히트율

## 정리 및 최적화 체크리스트

```python
# 쿼리 최적화 체크리스트
class QueryOptimizationChecklist:
    """매 프로젝트마다 확인해야 할 사항들"""
    
    CHECKLIST = [
        "N+1 쿼리 확인 - select_related와 prefetch_related 사용",
        "불필요한 필드 제외 - only()와 defer() 사용",
        "대량 작업 최적화 - bulk_create()와 bulk_update() 사용",
        "집계 쿼리 최적화 - aggregate()와 annotate() 사용",
        "복잡한 필터링 - Q 객체와 F 객체 활용",
        "인덱싱 전략 - 자주 검색하는 필드에 인덱스 설정",
        "트랜잭션 관리 - atomic()으로 일관성 보장",
        "쿼리 모니터링 - django-debug-toolbar 설정",
        "읽기 전용 쿼리셋 - values()와 values_list() 활용",
        "데이터베이스 연결 설정 - conn_max_age, AUTOCOMMIT 등",
    ]
    
    @staticmethod
    def verify_all():
        for item in QueryOptimizationChecklist.CHECKLIST:
            print(f"[ ] {item}")
```

이 글에서 다룬 모든 기법을 종합하면, 초급자 수준의 Django ORM 코드를 프로덕션 준비 상태의 효율적인 코드로 변환할 수 있습니다. 데이터 규모가 커질수록 이러한 최적화의 중요성은 더욱 커집니다. 매번 새 기능을 추가할 때마다 이 체크리스트를 참고해 최적화된 쿼리를 작성하는 습관을 들이기 바랍니다.

