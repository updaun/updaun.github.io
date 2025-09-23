---
layout: post
title: "Django ORM vs Raw SQL: 언제, 왜, 어떻게 Raw SQL을 사용해야 할까?"
date: 2025-09-14 14:00:00 +0900
categories: [Django, ORM, Database, SQL]
tags: [Django, ORM, Raw SQL, Database Optimization, Performance, Complex Queries, SQL Injection, Database Management]
image: "/assets/img/posts/2025-09-14-django-raw-sql-when-why-how.webp"
---

Django ORM은 강력하고 편리한 도구이지만, 모든 상황에서 최적의 해답을 제공하지는 않습니다. 때로는 **Raw SQL**을 직접 사용해야 하는 상황이 발생합니다. 이 글에서는 언제 Raw SQL이 필요한지, 안전하게 사용하는 방법, 그리고 ORM과 Raw SQL을 효과적으로 조합하는 전략을 상세히 알아보겠습니다.

## 🤔 Raw SQL이 필요한 상황들

### 1. 복잡한 집계와 윈도우 함수

Django ORM으로는 표현하기 어려운 복잡한 SQL 기능들이 있습니다.

```python
# 복잡한 윈도우 함수 예제
from django.db import connection

def get_sales_ranking_with_trends():
    """매출 순위와 전월 대비 증감률을 계산"""
    
    raw_sql = """
    SELECT 
        p.id,
        p.name as product_name,
        current_sales.total_sales,
        ROW_NUMBER() OVER (ORDER BY current_sales.total_sales DESC) as sales_rank,
        LAG(prev_sales.total_sales) OVER (ORDER BY current_sales.total_sales DESC) as prev_month_sales,
        CASE 
            WHEN prev_sales.total_sales > 0 THEN
                ROUND(((current_sales.total_sales - prev_sales.total_sales) / prev_sales.total_sales::float) * 100, 2)
            ELSE NULL
        END as growth_rate,
        PERCENT_RANK() OVER (ORDER BY current_sales.total_sales) as percentile_rank
    FROM products p
    LEFT JOIN (
        SELECT 
            product_id,
            SUM(amount) as total_sales
        FROM sales 
        WHERE created_at >= date_trunc('month', CURRENT_DATE)
        GROUP BY product_id
    ) current_sales ON p.id = current_sales.product_id
    LEFT JOIN (
        SELECT 
            product_id,
            SUM(amount) as total_sales
        FROM sales 
        WHERE created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
            AND created_at < date_trunc('month', CURRENT_DATE)
        GROUP BY product_id
    ) prev_sales ON p.id = prev_sales.product_id
    WHERE current_sales.total_sales IS NOT NULL
    ORDER BY sales_rank;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Django ORM으로는 이런 복잡한 윈도우 함수를 표현하기 매우 어려움
```

### 2. 데이터베이스별 특화 기능

```python
# PostgreSQL의 고급 기능 활용
def search_products_with_full_text_search(query):
    """PostgreSQL의 전문 검색 기능 사용"""
    
    raw_sql = """
    SELECT 
        p.*,
        ts_rank(
            to_tsvector('english', p.name || ' ' || p.description),
            plainto_tsquery('english', %s)
        ) as relevance_score
    FROM products p
    WHERE to_tsvector('english', p.name || ' ' || p.description) 
          @@ plainto_tsquery('english', %s)
    ORDER BY relevance_score DESC, p.created_at DESC;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [query, query])
        return cursor.fetchall()

# JSON 필드의 고급 쿼리 (PostgreSQL)
def get_users_by_json_criteria():
    """JSON 필드 내의 복잡한 조건 검색"""
    
    raw_sql = """
    SELECT 
        u.*,
        u.metadata->>'last_login_ip' as last_ip,
        (u.metadata->'preferences'->>'theme') as preferred_theme
    FROM users u
    WHERE u.metadata ? 'preferences'
        AND u.metadata->'preferences'->>'notifications' = 'enabled'
        AND (u.metadata->'settings'->>'language')::text = ANY(%s)
        AND jsonb_array_length(u.metadata->'tags') > 2;
    """
    
    languages = ['ko', 'en', 'ja']
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [languages])
        return cursor.fetchall()
```

### 3. 성능 최적화가 중요한 대용량 데이터 처리

```python
# 배치 처리를 위한 최적화된 Raw SQL
def bulk_update_user_scores():
    """사용자 점수 일괄 업데이트 (수백만 건)"""
    
    raw_sql = """
    WITH score_calculation AS (
        SELECT 
            u.id,
            COALESCE(SUM(a.points), 0) as total_points,
            COUNT(a.id) as activity_count,
            CASE 
                WHEN COUNT(a.id) > 100 THEN 'premium'
                WHEN COUNT(a.id) > 50 THEN 'gold'
                WHEN COUNT(a.id) > 10 THEN 'silver'
                ELSE 'bronze'
            END as new_tier
        FROM users u
        LEFT JOIN activities a ON u.id = a.user_id 
            AND a.created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY u.id
    )
    UPDATE users 
    SET 
        score = sc.total_points,
        tier = sc.new_tier,
        last_calculated_at = CURRENT_TIMESTAMP
    FROM score_calculation sc
    WHERE users.id = sc.id;
    """
    
    with connection.cursor() as cursor:
        start_time = time.time()
        cursor.execute(raw_sql)
        affected_rows = cursor.rowcount
        execution_time = time.time() - start_time
        
        print(f"업데이트 완료: {affected_rows}행, {execution_time:.2f}초")
        return affected_rows

# Django ORM으로 동일한 작업 시 매우 느림
def bulk_update_user_scores_orm():
    """ORM 버전 (매우 느림)"""
    users = User.objects.all()
    
    for user in users:  # N+1 쿼리 문제
        activities = user.activities.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )
        total_points = activities.aggregate(Sum('points'))['points__sum'] or 0
        activity_count = activities.count()
        
        # 개별 업데이트 쿼리
        user.score = total_points
        user.tier = calculate_tier(activity_count)
        user.last_calculated_at = timezone.now()
        user.save()
```

### 4. 복잡한 리포팅과 분석 쿼리

```python
# 복잡한 비즈니스 리포트 생성
def generate_monthly_sales_report(year, month):
    """월별 매출 분석 리포트"""
    
    raw_sql = """
    WITH daily_sales AS (
        SELECT 
            DATE(s.created_at) as sale_date,
            SUM(s.amount) as daily_total,
            COUNT(DISTINCT s.customer_id) as unique_customers,
            COUNT(s.id) as transaction_count
        FROM sales s
        WHERE EXTRACT(YEAR FROM s.created_at) = %s
            AND EXTRACT(MONTH FROM s.created_at) = %s
        GROUP BY DATE(s.created_at)
    ),
    category_performance AS (
        SELECT 
            c.name as category_name,
            SUM(s.amount) as category_total,
            RANK() OVER (ORDER BY SUM(s.amount) DESC) as category_rank
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN categories c ON p.category_id = c.id
        WHERE EXTRACT(YEAR FROM s.created_at) = %s
            AND EXTRACT(MONTH FROM s.created_at) = %s
        GROUP BY c.id, c.name
    ),
    customer_segments AS (
        SELECT 
            CASE 
                WHEN customer_total >= 10000 THEN 'VIP'
                WHEN customer_total >= 5000 THEN 'Premium'
                WHEN customer_total >= 1000 THEN 'Regular'
                ELSE 'Basic'
            END as segment,
            COUNT(*) as customer_count,
            SUM(customer_total) as segment_revenue
        FROM (
            SELECT 
                customer_id,
                SUM(amount) as customer_total
            FROM sales
            WHERE EXTRACT(YEAR FROM created_at) = %s
                AND EXTRACT(MONTH FROM created_at) = %s
            GROUP BY customer_id
        ) customer_totals
        GROUP BY 1
    )
    SELECT 
        'daily_avg' as metric_type,
        AVG(daily_total) as value,
        NULL as category,
        NULL as segment
    FROM daily_sales
    
    UNION ALL
    
    SELECT 
        'category_performance' as metric_type,
        category_total as value,
        category_name as category,
        NULL as segment
    FROM category_performance
    WHERE category_rank <= 5
    
    UNION ALL
    
    SELECT 
        'customer_segment' as metric_type,
        segment_revenue as value,
        NULL as category,
        segment as segment
    FROM customer_segments
    
    ORDER BY metric_type, value DESC;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [year, month, year, month, year, month])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 결과 데이터 구조화
        report = {
            'daily_average': [],
            'top_categories': [],
            'customer_segments': []
        }
        
        for row in results:
            if row['metric_type'] == 'daily_avg':
                report['daily_average'] = row['value']
            elif row['metric_type'] == 'category_performance':
                report['top_categories'].append({
                    'category': row['category'],
                    'revenue': row['value']
                })
            elif row['metric_type'] == 'customer_segment':
                report['customer_segments'].append({
                    'segment': row['segment'],
                    'revenue': row['value']
                })
        
        return report
```

## 🛡️ Raw SQL 안전 사용법

### 1. SQL Injection 방지

```python
# ❌ 위험한 방법: SQL Injection 취약점
def unsafe_search(user_input):
    """절대 사용하지 말 것!"""
    raw_sql = f"SELECT * FROM products WHERE name LIKE '%{user_input}%'"
    # 악의적 입력: "'; DROP TABLE products; --"
    
# ✅ 안전한 방법 1: 매개변수 바인딩
def safe_search_with_params(search_term):
    """매개변수 바인딩 사용"""
    raw_sql = "SELECT * FROM products WHERE name ILIKE %s"
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [f'%{search_term}%'])
        return cursor.fetchall()

# ✅ 안전한 방법 2: 딕셔너리 매개변수
def safe_search_with_dict_params(search_term, category_id):
    """딕셔너리 매개변수 사용"""
    raw_sql = """
    SELECT p.*, c.name as category_name
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.name ILIKE %(search)s
        AND p.category_id = %(category)s
        AND p.is_active = true
    ORDER BY p.created_at DESC;
    """
    
    params = {
        'search': f'%{search_term}%',
        'category': category_id
    }
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, params)
        return cursor.fetchall()

# ✅ 안전한 방법 3: 입력 검증 + 화이트리스트
def safe_dynamic_sorting(sort_field, sort_direction='ASC'):
    """동적 정렬을 위한 안전한 방법"""
    
    # 화이트리스트로 허용된 필드만 사용
    allowed_fields = {
        'name': 'p.name',
        'price': 'p.price', 
        'created_at': 'p.created_at',
        'category': 'c.name'
    }
    
    allowed_directions = ['ASC', 'DESC']
    
    if sort_field not in allowed_fields:
        sort_field = 'created_at'  # 기본값
    
    if sort_direction.upper() not in allowed_directions:
        sort_direction = 'ASC'  # 기본값
    
    # SQL 문자열 조합 (검증된 값만 사용)
    raw_sql = f"""
    SELECT p.*, c.name as category_name
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.is_active = true
    ORDER BY {allowed_fields[sort_field]} {sort_direction.upper()};
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql)
        return cursor.fetchall()
```

### 2. 트랜잭션 관리

```python
from django.db import transaction

# 복잡한 트랜잭션 처리
@transaction.atomic
def complex_data_migration():
    """Raw SQL을 사용한 복잡한 데이터 마이그레이션"""
    
    try:
        with connection.cursor() as cursor:
            # 1단계: 임시 테이블 생성
            cursor.execute("""
                CREATE TEMP TABLE temp_user_stats AS
                SELECT 
                    user_id,
                    COUNT(*) as order_count,
                    SUM(total_amount) as total_spent,
                    MAX(created_at) as last_order_date
                FROM orders
                WHERE created_at >= '2024-01-01'
                GROUP BY user_id;
            """)
            
            # 2단계: 사용자 통계 업데이트
            cursor.execute("""
                UPDATE users 
                SET 
                    order_count = COALESCE(ts.order_count, 0),
                    total_spent = COALESCE(ts.total_spent, 0),
                    last_order_date = ts.last_order_date,
                    updated_at = CURRENT_TIMESTAMP
                FROM temp_user_stats ts
                WHERE users.id = ts.user_id;
            """)
            
            affected_rows = cursor.rowcount
            
            # 3단계: 로그 기록
            cursor.execute("""
                INSERT INTO migration_logs (operation, affected_rows, created_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP);
            """, ['user_stats_update', affected_rows])
            
            print(f"마이그레이션 완료: {affected_rows}명의 사용자 업데이트")
            
    except Exception as e:
        print(f"마이그레이션 실패: {e}")
        raise  # 트랜잭션 롤백
```

### 3. 연결 관리와 리소스 정리

```python
from contextlib import contextmanager

@contextmanager
def get_db_cursor():
    """안전한 커서 관리"""
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

# 대용량 데이터 처리를 위한 배치 커서
def process_large_dataset_with_cursor():
    """서버 사이드 커서 사용 (PostgreSQL)"""
    
    raw_sql = """
    SELECT id, name, email, created_at
    FROM users
    WHERE created_at >= %s
    ORDER BY id;
    """
    
    with connection.cursor() as cursor:
        # 서버 사이드 커서 생성 (PostgreSQL)
        cursor.execute("BEGIN")
        cursor.execute(f"DECLARE user_cursor CURSOR FOR {raw_sql}", 
                      [timezone.now() - timezone.timedelta(days=30)])
        
        batch_size = 1000
        processed_count = 0
        
        while True:
            cursor.execute(f"FETCH {batch_size} FROM user_cursor")
            batch = cursor.fetchall()
            
            if not batch:
                break
                
            # 배치 처리
            for row in batch:
                process_user_data(row)
                processed_count += 1
            
            print(f"처리 완료: {processed_count}명")
        
        cursor.execute("CLOSE user_cursor")
        cursor.execute("COMMIT")

# 연결 풀 관리
class DatabaseManager:
    def __init__(self):
        self.connection_pool = []
    
    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기"""
        conn = connection
        try:
            yield conn
        finally:
            # 연결 상태 확인 및 정리
            if conn.queries_logged:
                print(f"실행된 쿼리 수: {len(conn.queries)}")
```

## 🔄 ORM과 Raw SQL 조합 전략

### 1. 하이브리드 쿼리 방식

```python
# ORM + Raw SQL 조합
def get_user_analytics_hybrid(user_id):
    """ORM과 Raw SQL을 조합한 사용자 분석"""
    
    # 1. ORM으로 기본 사용자 정보 조회
    try:
        user = User.objects.select_related('profile').get(id=user_id)
    except User.DoesNotExist:
        return None
    
    # 2. Raw SQL로 복잡한 통계 계산
    raw_sql = """
    WITH monthly_stats AS (
        SELECT 
            DATE_TRUNC('month', created_at) as month,
            COUNT(*) as order_count,
            SUM(total_amount) as total_spent,
            AVG(total_amount) as avg_order_value
        FROM orders
        WHERE user_id = %s
            AND created_at >= CURRENT_DATE - INTERVAL '12 months'
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month DESC
    ),
    product_preferences AS (
        SELECT 
            c.name as category,
            COUNT(*) as purchase_count,
            SUM(oi.quantity * oi.price) as category_spent
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN categories c ON p.category_id = c.id
        WHERE o.user_id = %s
        GROUP BY c.id, c.name
        ORDER BY category_spent DESC
        LIMIT 5
    )
    SELECT 
        'monthly' as stat_type,
        month::date as period,
        order_count as value,
        total_spent as secondary_value
    FROM monthly_stats
    
    UNION ALL
    
    SELECT 
        'category' as stat_type,
        NULL as period,
        purchase_count as value,
        category_spent as secondary_value
    FROM product_preferences;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [user_id, user_id])
        stats = cursor.fetchall()
    
    # 3. 결과 조합
    return {
        'user_info': {
            'id': user.id,
            'name': user.username,
            'email': user.email,
            'joined_date': user.date_joined,
            'profile': {
                'birth_date': user.profile.birth_date if hasattr(user, 'profile') else None,
                'phone': user.profile.phone if hasattr(user, 'profile') else None,
            }
        },
        'analytics': process_analytics_data(stats)
    }

# Manager를 통한 Raw SQL 메서드 추가
class ProductManager(models.Manager):
    def get_trending_products(self, days=7):
        """트렌딩 상품 조회 (Raw SQL)"""
        
        raw_sql = """
        SELECT 
            p.*,
            trend_stats.sale_count,
            trend_stats.revenue,
            trend_stats.growth_rate
        FROM (
            SELECT 
                product_id,
                COUNT(*) as sale_count,
                SUM(quantity * price) as revenue,
                (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY product_id)) / 
                    NULLIF(LAG(COUNT(*)) OVER (ORDER BY product_id), 0) * 100 as growth_rate
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY product_id
            HAVING COUNT(*) >= 5
        ) trend_stats
        JOIN products p ON trend_stats.product_id = p.id
        ORDER BY trend_stats.growth_rate DESC, trend_stats.sale_count DESC;
        """
        
        return self.raw(raw_sql, [days])

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = ProductManager()

# 사용 예제
trending_products = Product.objects.get_trending_products(days=14)
for product in trending_products:
    print(f"{product.name}: {product.sale_count}회 판매")
```

### 2. 커스텀 QuerySet과 Raw SQL

```python
class AdvancedProductQuerySet(models.QuerySet):
    def with_sales_stats(self):
        """매출 통계를 포함한 상품 조회"""
        
        # ORM 기본 쿼리
        return self.select_related('category').annotate(
            basic_sales_count=Count('orderitem')
        )
    
    def get_complex_analytics(self):
        """복잡한 분석 데이터 (Raw SQL 사용)"""
        
        raw_sql = """
        SELECT 
            p.*,
            COALESCE(sales_stats.total_revenue, 0) as total_revenue,
            COALESCE(sales_stats.total_quantity, 0) as total_quantity,
            COALESCE(sales_stats.avg_rating, 0) as avg_rating,
            COALESCE(sales_stats.review_count, 0) as review_count,
            COALESCE(inventory_stats.current_stock, 0) as current_stock,
            COALESCE(inventory_stats.reserved_stock, 0) as reserved_stock
        FROM products p
        LEFT JOIN (
            SELECT 
                oi.product_id,
                SUM(oi.quantity * oi.price) as total_revenue,
                SUM(oi.quantity) as total_quantity,
                AVG(r.rating) as avg_rating,
                COUNT(r.id) as review_count
            FROM order_items oi
            LEFT JOIN reviews r ON oi.product_id = r.product_id
            GROUP BY oi.product_id
        ) sales_stats ON p.id = sales_stats.product_id
        LEFT JOIN (
            SELECT 
                product_id,
                SUM(CASE WHEN status = 'available' THEN quantity ELSE 0 END) as current_stock,
                SUM(CASE WHEN status = 'reserved' THEN quantity ELSE 0 END) as reserved_stock
            FROM inventory
            GROUP BY product_id
        ) inventory_stats ON p.id = inventory_stats.product_id
        WHERE p.id IN %s
        ORDER BY sales_stats.total_revenue DESC;
        """
        
        # 현재 QuerySet의 ID 목록 가져오기
        product_ids = list(self.values_list('id', flat=True))
        
        if not product_ids:
            return []
        
        with connection.cursor() as cursor:
            cursor.execute(raw_sql, [tuple(product_ids)])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    objects = AdvancedProductQuerySet.as_manager()

# 사용 예제
# ORM과 Raw SQL을 단계적으로 조합
electronics = Product.objects.filter(
    category__name='전자제품'
).with_sales_stats()

# 복잡한 분석은 Raw SQL로
analytics_data = electronics.get_complex_analytics()
```

### 3. 데이터베이스 뷰와 ORM 연동

```python
# 복잡한 뷰를 생성하고 ORM으로 접근
def create_sales_summary_view():
    """매출 요약 뷰 생성"""
    
    create_view_sql = """
    CREATE OR REPLACE VIEW sales_summary AS
    SELECT 
        p.id as product_id,
        p.name as product_name,
        c.name as category_name,
        COUNT(DISTINCT o.id) as order_count,
        SUM(oi.quantity) as total_quantity_sold,
        SUM(oi.quantity * oi.price) as total_revenue,
        AVG(oi.price) as avg_price,
        MIN(o.created_at) as first_sale_date,
        MAX(o.created_at) as last_sale_date,
        COUNT(DISTINCT o.user_id) as unique_customers
    FROM products p
    LEFT JOIN order_items oi ON p.id = oi.product_id
    LEFT JOIN orders o ON oi.order_id = o.id
    LEFT JOIN categories c ON p.category_id = c.id
    GROUP BY p.id, p.name, c.name;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(create_view_sql)

# 뷰를 위한 모델 생성 (읽기 전용)
class SalesSummary(models.Model):
    product_id = models.IntegerField(primary_key=True)
    product_name = models.CharField(max_length=200)
    category_name = models.CharField(max_length=100)
    order_count = models.IntegerField()
    total_quantity_sold = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)
    first_sale_date = models.DateTimeField()
    last_sale_date = models.DateTimeField()
    unique_customers = models.IntegerField()
    
    class Meta:
        managed = False  # Django가 테이블을 관리하지 않음
        db_table = 'sales_summary'

# ORM으로 뷰 데이터 조회
def get_top_selling_products():
    """뷰를 통한 베스트 셀러 조회"""
    
    return SalesSummary.objects.filter(
        total_revenue__gt=10000
    ).order_by('-total_revenue')[:10]
```

## 🎯 성능 최적화 전략

### 1. 쿼리 실행 계획 분석

```python
def analyze_query_performance(raw_sql, params=None):
    """쿼리 성능 분석"""
    
    with connection.cursor() as cursor:
        # EXPLAIN ANALYZE로 실행 계획 확인
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {raw_sql}"
        
        cursor.execute(explain_sql, params or [])
        execution_plan = cursor.fetchone()[0]
        
        # 실행 시간 및 비용 분석
        total_time = execution_plan[0]['Execution Time']
        planning_time = execution_plan[0]['Planning Time']
        
        print(f"실행 시간: {total_time:.2f}ms")
        print(f"계획 시간: {planning_time:.2f}ms")
        
        # 느린 노드 찾기
        def find_slow_nodes(node, threshold=10):
            slow_nodes = []
            
            if node.get('Actual Total Time', 0) > threshold:
                slow_nodes.append({
                    'type': node.get('Node Type'),
                    'time': node.get('Actual Total Time'),
                    'relation': node.get('Relation Name')
                })
            
            for child in node.get('Plans', []):
                slow_nodes.extend(find_slow_nodes(child, threshold))
            
            return slow_nodes
        
        slow_nodes = find_slow_nodes(execution_plan[0]['Plan'])
        
        if slow_nodes:
            print("성능 개선이 필요한 부분:")
            for node in slow_nodes:
                print(f"  - {node['type']}: {node['time']:.2f}ms")
        
        return execution_plan

# 사용 예제
query = """
SELECT p.*, COUNT(o.id) as order_count
FROM products p
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id
WHERE p.created_at >= %s
GROUP BY p.id
ORDER BY order_count DESC;
"""

analyze_query_performance(query, [timezone.now() - timezone.timedelta(days=30)])
```

### 2. 동적 쿼리 최적화

```python
class DynamicQueryBuilder:
    """동적 쿼리 빌더"""
    
    def __init__(self):
        self.base_query = """
        SELECT p.id, p.name, p.price, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        """
        self.conditions = []
        self.params = []
        self.order_by = []
    
    def filter_by_price_range(self, min_price=None, max_price=None):
        if min_price is not None:
            self.conditions.append("p.price >= %s")
            self.params.append(min_price)
        
        if max_price is not None:
            self.conditions.append("p.price <= %s")
            self.params.append(max_price)
        
        return self
    
    def filter_by_categories(self, category_ids):
        if category_ids:
            placeholders = ','.join(['%s'] * len(category_ids))
            self.conditions.append(f"p.category_id IN ({placeholders})")
            self.params.extend(category_ids)
        
        return self
    
    def filter_by_search_term(self, search_term):
        if search_term:
            self.conditions.append("(p.name ILIKE %s OR p.description ILIKE %s)")
            search_pattern = f'%{search_term}%'
            self.params.extend([search_pattern, search_pattern])
        
        return self
    
    def order_by_field(self, field, direction='ASC'):
        allowed_fields = {
            'name': 'p.name',
            'price': 'p.price',
            'created_at': 'p.created_at'
        }
        
        if field in allowed_fields and direction.upper() in ['ASC', 'DESC']:
            self.order_by.append(f"{allowed_fields[field]} {direction.upper()}")
        
        return self
    
    def build(self):
        query = self.base_query
        
        if self.conditions:
            query += " WHERE " + " AND ".join(self.conditions)
        
        if self.order_by:
            query += " ORDER BY " + ", ".join(self.order_by)
        
        return query, self.params
    
    def execute(self):
        query, params = self.build()
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

# 사용 예제
def search_products(filters):
    """동적 상품 검색"""
    
    builder = DynamicQueryBuilder()
    
    if filters.get('min_price'):
        builder.filter_by_price_range(min_price=filters['min_price'])
    
    if filters.get('max_price'):
        builder.filter_by_price_range(max_price=filters['max_price'])
    
    if filters.get('categories'):
        builder.filter_by_categories(filters['categories'])
    
    if filters.get('search'):
        builder.filter_by_search_term(filters['search'])
    
    if filters.get('sort_by'):
        builder.order_by_field(filters['sort_by'], filters.get('sort_direction', 'ASC'))
    
    return builder.execute()
```

### 3. 캐싱과 Raw SQL 조합

```python
from django.core.cache import cache
import hashlib

def cached_raw_query(cache_key, raw_sql, params=None, timeout=300):
    """Raw SQL 결과 캐싱"""
    
    # 캐시 키 생성 (SQL + 파라미터 기반)
    query_hash = hashlib.md5(
        f"{raw_sql}{str(params or [])}".encode()
    ).hexdigest()
    
    full_cache_key = f"{cache_key}:{query_hash}"
    
    # 캐시에서 확인
    cached_result = cache.get(full_cache_key)
    if cached_result is not None:
        return cached_result
    
    # 캐시 미스 시 쿼리 실행
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, params or [])
        columns = [col[0] for col in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # 결과 캐싱
    cache.set(full_cache_key, result, timeout)
    return result

# 사용 예제
def get_dashboard_stats():
    """대시보드 통계 (캐싱 적용)"""
    
    stats_sql = """
    SELECT 
        'total_users' as metric,
        COUNT(*) as value
    FROM users
    WHERE is_active = true
    
    UNION ALL
    
    SELECT 
        'total_orders' as metric,
        COUNT(*) as value
    FROM orders
    WHERE created_at >= CURRENT_DATE
    
    UNION ALL
    
    SELECT 
        'total_revenue' as metric,
        COALESCE(SUM(total_amount), 0) as value
    FROM orders
    WHERE created_at >= CURRENT_DATE;
    """
    
    return cached_raw_query(
        cache_key='dashboard_stats',
        raw_sql=stats_sql,
        timeout=300  # 5분 캐싱
    )
```

## ⚠️ Raw SQL 사용 시 주의사항

### 1. 데이터베이스 독립성 고려

```python
# 데이터베이스별 차이점 처리
def get_date_truncated_sales(period='month'):
    """데이터베이스별 날짜 함수 처리"""
    
    db_engine = connection.vendor
    
    if db_engine == 'postgresql':
        date_trunc_func = f"DATE_TRUNC('{period}', created_at)"
    elif db_engine == 'mysql':
        if period == 'month':
            date_trunc_func = "DATE_FORMAT(created_at, '%Y-%m-01')"
        elif period == 'day':
            date_trunc_func = "DATE(created_at)"
        else:
            date_trunc_func = "DATE(created_at)"
    elif db_engine == 'sqlite':
        if period == 'month':
            date_trunc_func = "DATE(created_at, 'start of month')"
        else:
            date_trunc_func = "DATE(created_at)"
    else:
        # 기본값
        date_trunc_func = "DATE(created_at)"
    
    raw_sql = f"""
    SELECT 
        {date_trunc_func} as period,
        SUM(total_amount) as total_sales,
        COUNT(*) as order_count
    FROM orders
    WHERE created_at >= %s
    GROUP BY {date_trunc_func}
    ORDER BY period DESC;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(raw_sql, [timezone.now() - timezone.timedelta(days=90)])
        return cursor.fetchall()
```

### 2. 마이그레이션과 스키마 변경

```python
# 마이그레이션에서 Raw SQL 사용
from django.db import migrations

def create_custom_indexes(apps, schema_editor):
    """커스텀 인덱스 생성"""
    
    if schema_editor.connection.vendor == 'postgresql':
        # PostgreSQL 특화 인덱스
        schema_editor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_date
            ON orders (user_id, created_at DESC)
            WHERE status = 'completed';
        """)
        
        # 부분 인덱스
        schema_editor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_active_name
            ON products (name)
            WHERE is_active = true;
        """)
        
        # GiST 인덱스 (전문 검색용)
        schema_editor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_fulltext
            ON products USING GiST (to_tsvector('english', name || ' ' || description));
        """)

def remove_custom_indexes(apps, schema_editor):
    """커스텀 인덱스 제거"""
    
    indexes = [
        'idx_orders_user_date',
        'idx_products_active_name', 
        'idx_products_fulltext'
    ]
    
    for index in indexes:
        schema_editor.execute(f"DROP INDEX IF EXISTS {index};")

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(
            create_custom_indexes,
            remove_custom_indexes
        ),
    ]
```

### 3. 테스트와 디버깅

```python
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings

class RawSQLTestCase(TransactionTestCase):
    """Raw SQL 테스트"""
    
    def setUp(self):
        # 테스트 데이터 생성
        self.create_test_data()
    
    def test_complex_sales_query(self):
        """복잡한 매출 쿼리 테스트"""
        
        # Raw SQL 실행
        result = self.execute_sales_analysis_query()
        
        # 결과 검증
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        # 데이터 정합성 확인
        total_from_raw = sum(row['total_sales'] for row in result)
        total_from_orm = Order.objects.aggregate(
            total=Sum('total_amount')
        )['total']
        
        self.assertAlmostEqual(
            float(total_from_raw), 
            float(total_from_orm or 0),
            places=2
        )
    
    @override_settings(DEBUG=True)
    def test_query_performance(self):
        """쿼리 성능 테스트"""
        
        from django.db import connection
        
        # 쿼리 실행 전 초기화
        connection.queries.clear()
        
        # Raw SQL 실행
        result = self.execute_complex_query()
        
        # 쿼리 수 확인
        query_count = len(connection.queries)
        self.assertLessEqual(query_count, 5, "쿼리가 너무 많이 실행됨")
        
        # 실행 시간 확인
        total_time = sum(
            float(query['time']) for query in connection.queries
        )
        self.assertLess(total_time, 1.0, "쿼리 실행 시간이 너무 김")

# 디버깅 도구
class SQLDebugger:
    """Raw SQL 디버깅 도구"""
    
    def __init__(self):
        self.queries = []
    
    def log_query(self, sql, params, execution_time):
        self.queries.append({
            'sql': sql,
            'params': params,
            'time': execution_time,
            'timestamp': timezone.now()
        })
    
    def execute_with_logging(self, sql, params=None):
        """로깅과 함께 쿼리 실행"""
        
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            result = cursor.fetchall()
        
        execution_time = time.time() - start_time
        self.log_query(sql, params, execution_time)
        
        return result
    
    def print_summary(self):
        """실행 요약 출력"""
        
        total_time = sum(q['time'] for q in self.queries)
        print(f"총 {len(self.queries)}개 쿼리, {total_time:.3f}초")
        
        # 느린 쿼리 표시
        slow_queries = [q for q in self.queries if q['time'] > 0.1]
        if slow_queries:
            print("\n느린 쿼리:")
            for q in slow_queries:
                print(f"  {q['time']:.3f}초: {q['sql'][:100]}...")
```

## 🎯 결론 및 모범 사례

### 언제 Raw SQL을 사용해야 할까?

| 상황 | ORM 사용 | Raw SQL 사용 | 이유 |
|------|----------|--------------|------|
| **CRUD 작업** | ✅ | ❌ | Django ORM이 최적화됨 |
| **단순 JOIN** | ✅ | ❌ | select_related/prefetch_related |
| **윈도우 함수** | ❌ | ✅ | ORM 지원 제한적 |
| **복잡한 집계** | △ | ✅ | 성능상 Raw SQL이 유리 |
| **DB 특화 기능** | ❌ | ✅ | ORM으로 불가능 |
| **대용량 배치** | ❌ | ✅ | 성능 최적화 필요 |
| **동적 쿼리** | △ | ✅ | 복잡한 조건부 로직 |

### 모범 사례 체크리스트

```python
# ✅ Raw SQL 모범 사례

class SafeRawSQLManager:
    """안전한 Raw SQL 관리 클래스"""
    
    def __init__(self):
        self.query_cache = {}
    
    def execute_safe_query(self, query_name, sql, params=None, cache_timeout=None):
        """안전한 쿼리 실행"""
        
        # 1. 매개변수 검증
        if params:
            self._validate_parameters(params)
        
        # 2. 캐시 확인
        if cache_timeout and query_name in self.query_cache:
            cached_result = cache.get(f"raw_sql:{query_name}")
            if cached_result:
                return cached_result
        
        # 3. 쿼리 실행
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params or [])
                result = self._format_result(cursor)
                
                # 4. 결과 캐싱
                if cache_timeout:
                    cache.set(f"raw_sql:{query_name}", result, cache_timeout)
                
                return result
                
        except Exception as e:
            logger.error(f"Raw SQL 실행 실패 - {query_name}: {e}")
            raise
    
    def _validate_parameters(self, params):
        """매개변수 검증"""
        if isinstance(params, dict):
            for key, value in params.items():
                if isinstance(value, str) and len(value) > 1000:
                    raise ValueError(f"매개변수 {key}가 너무 깁니다")
        elif isinstance(params, (list, tuple)):
            for i, value in enumerate(params):
                if isinstance(value, str) and len(value) > 1000:
                    raise ValueError(f"매개변수 {i}가 너무 깁니다")
    
    def _format_result(self, cursor):
        """결과 포맷팅"""
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# 사용 예제
sql_manager = SafeRawSQLManager()

def get_user_analytics_safe(user_id):
    """안전한 사용자 분석 조회"""
    
    sql = """
    SELECT 
        COUNT(*) as order_count,
        SUM(total_amount) as total_spent,
        AVG(total_amount) as avg_order_value
    FROM orders
    WHERE user_id = %s
        AND created_at >= %s;
    """
    
    return sql_manager.execute_safe_query(
        query_name='user_analytics',
        sql=sql,
        params=[user_id, timezone.now() - timezone.timedelta(days=365)],
        cache_timeout=300
    )
```

### 최종 권장사항

1. **ORM 우선 원칙**: 가능하면 Django ORM 사용
2. **점진적 최적화**: ORM → select_related/prefetch_related → Raw SQL
3. **보안 최우선**: 매개변수 바인딩 필수 사용
4. **성능 측정**: 실제 데이터로 벤치마크 테스트
5. **문서화**: Raw SQL 사용 이유와 방법 명확히 기록
6. **테스트 작성**: Raw SQL 로직에 대한 충분한 테스트
7. **모니터링**: 쿼리 성능 지속적 모니터링

Django ORM과 Raw SQL을 적절히 조합하면 **개발 생산성과 성능을 모두 확보**할 수 있습니다. 핵심은 각각의 장단점을 이해하고 **상황에 맞는 최적의 선택**을 하는 것입니다.

**다음 글에서는 Django의 캐싱 전략과 성능 최적화 고급 기법을 다루겠습니다. 🚀**
