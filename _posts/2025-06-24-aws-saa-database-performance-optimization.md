---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 데이터베이스 성능 최적화와 스토리지 선택"
date: 2025-06-24
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 데이터베이스 성능 최적화와 스토리지 선택

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 데이터베이스 성능 최적화 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 다양한 AWS 데이터베이스 서비스의 특성과 성능 요구사항에 맞는 최적의 솔루션 선택 문제를 다루겠습니다.

## 📝 실전 문제

**문제**: 한 전자상거래 회사가 다음과 같은 데이터베이스 요구사항을 가진 시스템을 AWS에 구축하려고 합니다:

- **주문 시스템**: 높은 트랜잭션 처리량 (초당 10,000 건 이상)
- **상품 카탈로그**: 빠른 읽기 성능 필요 (밀리초 단위 응답)
- **고객 행동 분석**: 대용량 데이터 분석 및 복잡한 쿼리
- **세션 데이터**: 빠른 읽기/쓰기, 자동 만료 기능
- **이미지/동영상**: 글로벌 콘텐츠 배포 및 비용 최적화

각 요구사항에 가장 적합한 AWS 서비스 조합은?

**A)** 모든 데이터를 RDS MySQL Multi-AZ로 구성

**B)** DynamoDB + ElastiCache + Redshift + S3 + CloudFront

**C)** RDS Aurora + DocumentDB + Neptune + EFS + CloudFormation

**D)** EC2의 자체 관리형 데이터베이스 + EBS + CloudWatch

## 🎯 정답 및 해설

### 정답: B

**DynamoDB + ElastiCache + Redshift + S3 + CloudFront**

### 상세 분석

#### 1. 요구사항별 최적 서비스 매칭

| 요구사항 | 선택된 서비스 | 이유 |
|---------|-------------|------|
| 주문 시스템 | **DynamoDB** | NoSQL, 높은 처리량, 자동 확장 |
| 상품 카탈로그 | **ElastiCache** | 인메모리 캐싱, 밀리초 응답 |
| 고객 행동 분석 | **Redshift** | 데이터 웨어하우스, 복잡한 분석 쿼리 |
| 세션 데이터 | **ElastiCache** | 인메모리, TTL 지원, 빠른 R/W |
| 이미지/동영상 | **S3 + CloudFront** | 객체 스토리지, 글로벌 CDN |

## 🚀 각 서비스별 상세 설계

### 1. 주문 시스템 - Amazon DynamoDB

#### DynamoDB 테이블 설계
```json
{
  "TableName": "Orders",
  "KeySchema": [
    {
      "AttributeName": "OrderId",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "Timestamp",
      "KeyType": "RANGE"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "OrderId",
      "AttributeType": "S"
    },
    {
      "AttributeName": "Timestamp",
      "AttributeType": "N"
    },
    {
      "AttributeName": "CustomerId",
      "AttributeType": "S"
    }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "CustomerIdIndex",
      "KeySchema": [
        {
          "AttributeName": "CustomerId",
          "KeyType": "HASH"
        },
        {
          "AttributeName": "Timestamp",
          "KeyType": "RANGE"
        }
      ]
    }
  ],
  "BillingMode": "ON_DEMAND"
}
```

#### DynamoDB 성능 최적화
- **On-Demand 모드**: 트래픽 패턴이 예측 불가능한 전자상거래
- **글로벌 테이블**: 다중 리전 복제로 지연 시간 최소화
- **DAX (DynamoDB Accelerator)**: 마이크로초 단위 캐싱

### 2. 상품 카탈로그 - Amazon ElastiCache

#### Redis 클러스터 구성
```json
{
  "CacheClusterConfig": {
    "CacheClusterId": "product-catalog-cache",
    "Engine": "redis",
    "CacheNodeType": "cache.r6g.xlarge",
    "NumCacheNodes": 3,
    "CacheSubnetGroupName": "cache-subnet-group",
    "SecurityGroupIds": ["sg-cache-security-group"],
    "ReplicationGroupDescription": "Product catalog cache",
    "AutomaticFailoverEnabled": true,
    "MultiAZEnabled": true
  }
}
```

#### 캐싱 전략
```python
import redis
import json

class ProductCacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='product-catalog-cache.cache.amazonaws.com',
            port=6379,
            decode_responses=True
        )
    
    def get_product(self, product_id):
        # Cache Hit 확인
        cached_product = self.redis_client.get(f"product:{product_id}")
        if cached_product:
            return json.loads(cached_product)
        
        # Cache Miss - DB에서 조회 후 캐시 저장
        product = self.fetch_from_database(product_id)
        self.redis_client.setex(
            f"product:{product_id}", 
            3600,  # 1시간 TTL
            json.dumps(product)
        )
        return product
    
    def invalidate_product(self, product_id):
        self.redis_client.delete(f"product:{product_id}")
```

### 3. 고객 행동 분석 - Amazon Redshift

#### Redshift 클러스터 설계
```json
{
  "ClusterIdentifier": "customer-analytics-cluster",
  "ClusterType": "multi-node", 
  "NodeType": "dc2.large",
  "NumberOfNodes": 4,
  "DBName": "analytics",
  "MasterUsername": "admin",
  "VpcSecurityGroupIds": ["sg-redshift-security-group"],
  "ClusterSubnetGroupName": "redshift-subnet-group",
  "PubliclyAccessible": false,
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:region:account:key/key-id"
}
```

#### 데이터 파이프라인 구성
```sql
-- 고객 행동 분석 테이블
CREATE TABLE customer_behavior (
    customer_id VARCHAR(50),
    event_type VARCHAR(50),
    product_id VARCHAR(50),
    timestamp TIMESTAMP,
    session_id VARCHAR(100),
    page_url VARCHAR(500),
    user_agent VARCHAR(500)
)
DISTKEY(customer_id)
SORTKEY(timestamp);

-- 일별 고객 활동 집계
CREATE VIEW daily_customer_activity AS
SELECT 
    DATE(timestamp) as activity_date,
    customer_id,
    COUNT(*) as total_events,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as purchases
FROM customer_behavior
GROUP BY DATE(timestamp), customer_id;
```

### 4. 세션 데이터 - ElastiCache (Redis)

#### 세션 관리 구성
```python
class SessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='session-cache.cache.amazonaws.com',
            port=6379,
            decode_responses=True
        )
    
    def create_session(self, user_id, session_data, ttl=3600):
        session_id = self.generate_session_id()
        session_key = f"session:{session_id}"
        
        session_info = {
            'user_id': user_id,
            'created_at': time.time(),
            'data': session_data
        }
        
        # TTL 설정으로 자동 만료
        self.redis_client.setex(
            session_key,
            ttl,
            json.dumps(session_info)
        )
        return session_id
    
    def get_session(self, session_id):
        session_key = f"session:{session_id}"
        session_data = self.redis_client.get(session_key)
        if session_data:
            return json.loads(session_data)
        return None
    
    def update_session_ttl(self, session_id, ttl=3600):
        session_key = f"session:{session_id}"
        self.redis_client.expire(session_key, ttl)
```

### 5. 미디어 콘텐츠 - S3 + CloudFront

#### S3 버킷 구성
```json
{
  "BucketConfiguration": {
    "BucketName": "ecommerce-media-content",
    "Region": "us-east-1",
    "StorageClasses": {
      "Images": "S3 Standard",
      "Videos": "S3 Standard-IA",
      "Archives": "S3 Glacier"
    },
    "LifecyclePolicy": {
      "Rules": [
        {
          "Id": "MediaLifecycle",
          "Status": "Enabled",
          "Transitions": [
            {
              "Days": 30,
              "StorageClass": "STANDARD_IA"
            },
            {
              "Days": 90,
              "StorageClass": "GLACIER"
            }
          ]
        }
      ]
    }
  }
}
```

#### CloudFront 배포 설정
```json
{
  "DistributionConfig": {
    "CallerReference": "ecommerce-media-distribution",
    "Comment": "Global content delivery for e-commerce media",
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3-ecommerce-media-content",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "managed-caching-optimized",
      "Compress": true
    },
    "Origins": [
      {
        "Id": "S3-ecommerce-media-content",
        "DomainName": "ecommerce-media-content.s3.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": "origin-access-identity/cloudfront/ABCDEFG1234567"
        }
      }
    ],
    "Enabled": true,
    "PriceClass": "PriceClass_All"
  }
}
```

## ❌ 다른 선택지가 부적절한 이유

### A) RDS MySQL Multi-AZ만 사용
- **성능 한계**: 초당 10,000건 트랜잭션 처리 어려움
- **확장성 부족**: 수직 확장만 가능, 비용 증가
- **캐싱 부재**: 밀리초 응답 시간 달성 어려움
- **분석 성능**: 복잡한 분석 쿼리에 부적합

### C) Aurora + DocumentDB + Neptune + EFS
- **과도한 복잡성**: 불필요한 서비스들 (Neptune - 그래프 DB)
- **비용 비효율**: 요구사항에 맞지 않는 서비스들
- **성능 미달**: 캐싱 계층 부재로 응답 시간 목표 달성 어려움

### D) 자체 관리형 데이터베이스
- **운영 부담**: 데이터베이스 관리 오버헤드
- **확장성 제한**: 수동 확장, 복잡한 구성
- **가용성 위험**: Single Point of Failure
- **비용 증가**: 관리 인력 및 인프라 비용

## 🏗️ 완성된 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────┐
│                  Global Users                       │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                CloudFront                           │
│            (Global CDN)                             │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                    S3                               │
│           (Media Storage)                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Application Layer                      │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Web Server │  │  Web Server │  │  Web Server │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────┬────────────────┬────────────────┬───────────┘
       │                │                │
┌──────▼────────┐ ┌─────▼─────┐ ┌────────▼─────────┐
│   DynamoDB    │ │ElastiCache│ │    Redshift      │
│ (Orders DB)   │ │(Cache+    │ │  (Analytics)     │
│               │ │ Session)  │ │                  │
└───────────────┘ └───────────┘ └──────────────────┘
```

## 📊 성능 최적화 전략

### 1. DynamoDB 최적화
```json
{
  "PerformanceOptimization": {
    "ReadCapacity": {
      "AutoScaling": true,
      "TargetUtilization": 70,
      "MinCapacity": 5,
      "MaxCapacity": 40000
    },
    "WriteCapacity": {
      "AutoScaling": true, 
      "TargetUtilization": 70,
      "MinCapacity": 5,
      "MaxCapacity": 40000
    },
    "GlobalTables": true,
    "DaxCluster": {
      "NodeType": "dax.r4.large",
      "ReplicationFactor": 3
    }
  }
}
```

### 2. ElastiCache 최적화
- **메모리 최적화**: 적절한 노드 타입 선택 (R6G 인스턴스)
- **클러스터 모드**: Redis 클러스터로 수평 확장
- **데이터 파티셔닝**: 일관된 해싱으로 부하 분산

### 3. Redshift 최적화
```sql
-- 컬럼형 압축
ALTER TABLE customer_behavior 
ALTER COLUMN event_type SET ENCODE LZO;

-- 정렬 키 최적화
ALTER TABLE customer_behavior 
ALTER SORTKEY (timestamp, customer_id);

-- 분산 키 최적화  
ALTER TABLE customer_behavior
ALTER DISTKEY customer_id;
```

## 💰 비용 최적화 방안

### 1. DynamoDB 비용 최적화
- **On-Demand vs Provisioned**: 트래픽 패턴에 따른 선택
- **Global Tables**: 꼭 필요한 리전만 복제
- **TTL 활용**: 불필요한 데이터 자동 삭제

### 2. ElastiCache 비용 최적화
- **Reserved Instances**: 예측 가능한 워크로드에 적용
- **적절한 노드 크기**: 메모리 사용량 모니터링 후 조정

### 3. Redshift 비용 최적화
```json
{
  "CostOptimization": {
    "ReservedNodes": {
      "NodeType": "dc2.large",
      "NodeCount": 4,
      "Duration": "1year",
      "PaymentOption": "All Upfront"
    },
    "AutomaticSnapshots": {
      "RetentionPeriod": 7,
      "Schedule": "daily"
    },
    "WLM": {
      "QueryQueues": 3,
      "ConcurrencyLevel": 15
    }
  }
}
```

### 4. S3 + CloudFront 비용 최적화
- **Intelligent Tiering**: 자동 스토리지 클래스 변경
- **CloudFront 캐싱**: 적절한 TTL 설정으로 오리진 요청 감소
- **압축**: Gzip 압축으로 전송 데이터량 감소

## 🔧 모니터링 및 운영

### CloudWatch 메트릭 설정
```json
{
  "MonitoringConfig": {
    "DynamoDB": [
      "ConsumedReadCapacityUnits",
      "ConsumedWriteCapacityUnits", 
      "ThrottledRequests",
      "SystemErrors"
    ],
    "ElastiCache": [
      "CPUUtilization",
      "DatabaseMemoryUsagePercentage",
      "CacheMisses",
      "CacheHits"
    ],
    "Redshift": [
      "CPUUtilization",
      "DatabaseConnections",
      "HealthStatus",
      "MaintenanceMode"
    ]
  }
}
```

### 알람 설정 예시
```json
{
  "Alarms": [
    {
      "AlarmName": "DynamoDB-HighThrottle",
      "MetricName": "ThrottledRequests",
      "Threshold": 10,
      "ComparisonOperator": "GreaterThanThreshold",
      "EvaluationPeriods": 2
    },
    {
      "AlarmName": "ElastiCache-HighCPU",
      "MetricName": "CPUUtilization", 
      "Threshold": 80,
      "ComparisonOperator": "GreaterThanThreshold",
      "EvaluationPeriods": 3
    }
  ]
}
```

## 🎓 핵심 학습 포인트

1. **서비스별 특성 이해**: 각 데이터베이스 서비스의 강점과 용도
2. **성능 요구사항 매칭**: 요구사항에 맞는 최적 서비스 선택
3. **비용 효율성**: 성능과 비용의 균형점 찾기
4. **확장성 고려**: 미래 성장을 고려한 아키텍처 설계
5. **운영 복잡성**: 관리 부담과 성능 트레이드오프

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 다중 데이터베이스 서비스 선택 문제의 전형적인 예시입니다. 실제 전자상거래 환경에서는 각기 다른 성능 요구사항을 가진 데이터들을 적절한 서비스에 배치하는 것이 중요합니다.

데이터베이스 서비스 선택 시 고려사항:

1. **성능 요구사항**: 처리량, 지연시간, 동시성
2. **데이터 특성**: 구조화/비구조화, 관계형/NoSQL  
3. **확장성**: 수평/수직 확장, 자동 스케일링
4. **비용**: 초기 비용, 운영 비용, 확장 비용
5. **운영 복잡성**: 관리형 vs 자체 관리, 백업, 모니터링

다음 포스트에서는 AWS의 서버리스 아키텍처(Lambda, API Gateway, Step Functions)를 활용한 이벤트 드리븐 시스템 설계 문제를 다뤄보겠습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})

**태그**: #AWS #SAA #Database #DynamoDB #ElastiCache #Redshift #S3 #CloudFront #성능최적화
