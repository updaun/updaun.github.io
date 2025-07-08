---
layout: post
title: "AWS SAA 실습 문제: ECS Fargate와 RDS를 활용한 컨테이너 기반 웹 애플리케이션 아키텍처"
categories: [aws-saa]
tags: [aws, ecs, fargate, rds, alb, vpc, cloudwatch, auto-scaling]
date: 2025-07-08
---

## 📋 문제 시나리오

당신은 중견 e-커머스 회사의 DevOps 엔지니어로 근무하고 있습니다. 기존 온프레미스 환경에서 운영되던 웹 애플리케이션을 AWS 클라우드로 마이그레이션하면서 컨테이너 기반 아키텍처로 현대화해야 합니다.

### 현재 상황
- **기존 환경**: 온프레미스 VM에서 운영되는 Java Spring Boot 애플리케이션
- **데이터베이스**: MySQL 5.7 (약 500GB 데이터)
- **트래픽 패턴**: 평상시 1,000 RPS, 이벤트 시즌 5,000 RPS
- **가용성 요구사항**: 99.9% 업타임
- **지역**: 아시아 태평양 지역 사용자 대상

### 비즈니스 요구사항
1. **높은 가용성**: Multi-AZ 배포로 장애 대응
2. **자동 스케일링**: 트래픽 증가에 따른 자동 확장
3. **보안 강화**: 네트워크 격리 및 암호화
4. **모니터링**: 실시간 애플리케이션 상태 모니터링
5. **비용 효율성**: 리소스 사용량 최적화
6. **배포 자동화**: CI/CD 파이프라인 구축

## 🎯 해결 방안

### 1. 전체 아키텍처 설계

```
[Route 53] → [CloudFront] → [ALB] → [ECS Fargate] → [RDS Multi-AZ]
                                         ↓
[Auto Scaling] ← [CloudWatch] ← [Container Insights]
```

### 2. 네트워크 아키텍처

#### A. VPC 설계
```yaml
VPC Configuration:
  CIDR: 10.0.0.0/16
  
  Public Subnets:
    - 10.0.1.0/24 (ap-northeast-2a) - ALB
    - 10.0.2.0/24 (ap-northeast-2b) - ALB
    - 10.0.3.0/24 (ap-northeast-2c) - ALB
  
  Private Subnets:
    - 10.0.11.0/24 (ap-northeast-2a) - ECS Tasks
    - 10.0.12.0/24 (ap-northeast-2b) - ECS Tasks
    - 10.0.13.0/24 (ap-northeast-2c) - ECS Tasks
  
  Database Subnets:
    - 10.0.21.0/24 (ap-northeast-2a) - RDS Primary
    - 10.0.22.0/24 (ap-northeast-2b) - RDS Standby
    - 10.0.23.0/24 (ap-northeast-2c) - RDS Reserved
```

#### B. 보안 그룹 설정
```yaml
ALB Security Group:
  Inbound:
    - Port 80: 0.0.0.0/0 (HTTP)
    - Port 443: 0.0.0.0/0 (HTTPS)
  Outbound:
    - Port 8080: ECS Security Group

ECS Security Group:
  Inbound:
    - Port 8080: ALB Security Group
  Outbound:
    - Port 3306: RDS Security Group
    - Port 443: 0.0.0.0/0 (HTTPS)

RDS Security Group:
  Inbound:
    - Port 3306: ECS Security Group
  Outbound: None
```

### 3. 컨테이너 환경 구성

#### A. ECS 클러스터 설정
```yaml
ECS Cluster:
  Name: ecommerce-cluster
  Type: Fargate
  
  Service Configuration:
    Service Name: ecommerce-service
    Task Definition: ecommerce-task
    Desired Count: 3
    Minimum: 2
    Maximum: 20
    
  Network Configuration:
    VPC: ecommerce-vpc
    Subnets: [private-subnet-1, private-subnet-2, private-subnet-3]
    Security Groups: [ecs-sg]
    Public IP: Disabled
```

#### B. Task Definition 예제
```json
{
  "family": "ecommerce-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "ecommerce-app",
      "image": "account.dkr.ecr.region.amazonaws.com/ecommerce:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "SPRING_PROFILES_ACTIVE",
          "value": "prod"
        },
        {
          "name": "DB_HOST",
          "value": "ecommerce-db.cluster-xxx.region.rds.amazonaws.com"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:rds-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ecommerce",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### 4. 데이터베이스 설계

#### A. RDS 구성
```yaml
RDS Configuration:
  Engine: MySQL 8.0
  Instance Class: db.r5.xlarge
  Storage: 500GB GP2 (Auto Scaling enabled)
  Multi-AZ: Yes
  
  Backup:
    Retention Period: 7 days
    Backup Window: 03:00-04:00 UTC
    Maintenance Window: Sun:04:00-Sun:05:00 UTC
  
  Security:
    Encryption at Rest: Yes (KMS)
    SSL/TLS: Required
    
  Parameter Group:
    innodb_buffer_pool_size: 75% of RAM
    max_connections: 1000
    slow_query_log: 1
```

#### B. 읽기 전용 복제본 설정
```yaml
Read Replica:
  Count: 2
  Instance Class: db.r5.large
  Regions: Same region, different AZ
  
  Use Cases:
    - Analytics queries
    - Reporting
    - Read-heavy operations
```

### 5. 로드 밸런싱 구성

#### A. Application Load Balancer
```yaml
ALB Configuration:
  Type: Application Load Balancer
  Scheme: Internet-facing
  Subnets: [public-subnet-1, public-subnet-2, public-subnet-3]
  
  Target Groups:
    - Name: ecommerce-tg
    - Protocol: HTTP
    - Port: 8080
    - Health Check Path: /health
    - Health Check Interval: 30s
    - Healthy Threshold: 2
    - Unhealthy Threshold: 3
    
  Listeners:
    - Port 80: Redirect to HTTPS
    - Port 443: Forward to ecommerce-tg
    
  SSL Certificate: ACM Certificate
```

#### B. 고급 라우팅 규칙
```yaml
Routing Rules:
  - Priority: 1
    Condition: Path Pattern = /api/*
    Action: Forward to api-target-group
    
  - Priority: 2  
    Condition: Path Pattern = /admin/*
    Action: Forward to admin-target-group
    
  - Priority: 3
    Condition: Header "User-Agent" contains "mobile"
    Action: Forward to mobile-target-group
```

### 6. 자동 스케일링 설정

#### A. ECS Service Auto Scaling
```yaml
Auto Scaling Configuration:
  Target Tracking Policies:
    - Metric: ECSServiceAverageCPUUtilization
      Target Value: 70%
      
    - Metric: ECSServiceAverageMemoryUtilization  
      Target Value: 80%
      
    - Metric: ALBRequestCountPerTarget
      Target Value: 100
      
  Step Scaling Policy:
    - Scale Out: +50% when CPU > 85%
    - Scale In: -25% when CPU < 40%
    
  Scaling Cooldown:
    Scale Out: 300 seconds
    Scale In: 300 seconds
```

#### B. 예측 스케일링 설정
```python
# CloudFormation 템플릿 예제
ScalingPolicy:
  Type: AWS::ApplicationAutoScaling::ScalingPolicy
  Properties:
    PolicyName: ECSPredictiveScaling
    PolicyType: TargetTrackingScaling
    ScalingTargetId: !Ref ScalableTarget
    TargetTrackingScalingPolicyConfiguration:
      TargetValue: 70.0
      PredefinedMetricSpecification:
        PredefinedMetricType: ECSServiceAverageCPUUtilization
      ScaleOutCooldown: 300
      ScaleInCooldown: 300
```

### 7. 모니터링 및 로깅

#### A. CloudWatch 메트릭
```yaml
Container Insights:
  Enabled: true
  Metrics:
    - CPU Utilization
    - Memory Utilization
    - Network I/O
    - Task Count
    - Service Events

Custom Metrics:
  - Application Response Time
  - Database Connection Pool
  - Business KPIs (Orders/minute)
  - Error Rate by Endpoint
```

#### B. 로깅 전략
```yaml
Log Groups:
  - /ecs/ecommerce-app
  - /aws/rds/instance/ecommerce-db/error
  - /aws/applicationelb/ecommerce-alb
  
Log Retention: 30 days

Log Insights Queries:
  - Error Rate: "ERROR" | stats count() by bin(5m)
  - Response Time: "responseTime" | avg(responseTime) by bin(1m)
  - Database Queries: "SELECT" | count() by bin(5m)
```

### 8. 보안 구성

#### A. IAM 역할 설정
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:ecommerce/*"
    }
  ]
}
```

#### B. Secrets Manager 구성
```yaml
Database Credentials:
  Secret Name: ecommerce/db/credentials
  Description: RDS database credentials
  Values:
    username: admin
    password: <auto-generated>
    endpoint: ecommerce-db.cluster-xxx.region.rds.amazonaws.com
    port: 3306
    
Rotation:
  Enabled: true
  Schedule: 30 days
  Lambda Function: SecretsManagerRDSMySQLRotationSingleUser
```

### 9. 배포 전략

#### A. Blue/Green 배포
```yaml
CodeDeploy Configuration:
  Application: ecommerce-app
  Deployment Group: ecommerce-dg
  
  Deployment Strategy:
    Type: Blue/Green
    Termination Wait Time: 5 minutes
    
  Traffic Shifting:
    - 10% immediately
    - 50% after 5 minutes
    - 100% after 10 minutes
    
  Auto Rollback:
    - On deployment failure
    - On alarm thresholds
    - On CloudWatch metrics
```

#### B. CI/CD 파이프라인
```yaml
# CodePipeline 구성
Pipeline Stages:
  1. Source:
     - GitHub Repository
     - Branch: main
     
  2. Build:
     - CodeBuild Project
     - Docker Image Build
     - Push to ECR
     
  3. Deploy:
     - Update ECS Service
     - Blue/Green Deployment
     - Health Check Validation
     
  4. Post-Deploy:
     - Integration Tests
     - Performance Tests
     - Notification
```

### 10. 재해 복구 계획

#### A. 백업 전략
```yaml
RDS Automated Backup:
  Retention: 7 days
  Point-in-Time Recovery: Enabled
  
Manual Snapshots:
  Schedule: Weekly
  Cross-Region Copy: Enabled
  Retention: 30 days
  
ECS Configuration Backup:
  Task Definitions: Version controlled
  Service Configurations: CloudFormation
  ECR Images: Multi-region replication
```

#### B. 복구 절차
```yaml
RTO/RPO Targets:
  RTO: 1 hour
  RPO: 15 minutes
  
Disaster Recovery Steps:
  1. Assess failure scope
  2. Activate standby region (if needed)
  3. Restore database from backup
  4. Deploy ECS services
  5. Update Route 53 records
  6. Validate application functionality
```

## 💡 성능 최적화 팁

### 1. 컨테이너 최적화
```dockerfile
# Multi-stage build 예제
FROM maven:3.8-openjdk-11 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn clean package -DskipTests

FROM openjdk:11-jre-slim
RUN addgroup --system appgroup && adduser --system appuser --ingroup appgroup
WORKDIR /app
COPY --from=build /app/target/ecommerce-*.jar app.jar
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-jar", "app.jar"]
```

### 2. 데이터베이스 최적화
```sql
-- 인덱스 최적화
CREATE INDEX idx_order_date ON orders(order_date);
CREATE INDEX idx_customer_email ON customers(email);
CREATE INDEX idx_product_category ON products(category_id);

-- 파티셔닝 예제
CREATE TABLE orders_2025 PARTITION OF orders
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

### 3. 캐싱 전략
```yaml
ElastiCache Redis:
  Node Type: cache.r6g.large
  Num Nodes: 3
  Multi-AZ: Yes
  
  Use Cases:
    - Session Store
    - Application Cache
    - Database Query Cache
```

## 📊 비용 최적화

### 1. 리소스 사이징
```yaml
Cost Optimization:
  ECS Tasks:
    - CPU: 1 vCPU (기본)
    - Memory: 2 GB (기본)
    - Auto Scaling으로 동적 조정
    
  RDS:
    - Reserved Instance (1년)
    - Storage Auto Scaling
    - Read Replica 최적화
    
  ALB:
    - 불필요한 타겟 그룹 정리
    - Health Check 최적화
```

### 2. 모니터링 비용
```yaml
예상 월 비용 (트래픽 기준):
  ECS Fargate (평균 5 tasks): $150
  RDS Multi-AZ (db.r5.xlarge): $400
  ALB: $25
  CloudWatch: $50
  Data Transfer: $100
  
총 예상 비용: $725/월
```

## 🚀 실습 과제

### 1. 기본 구축
1. VPC 및 서브넷 생성
2. ECS 클러스터 구성
3. RDS 인스턴스 배포
4. ALB 설정

### 2. 고급 구성
1. Auto Scaling 정책 구현
2. CI/CD 파이프라인 구축
3. 모니터링 대시보드 생성
4. 보안 감사 수행

### 3. 성능 테스트
1. 부하 테스트 시나리오 작성
2. 스케일링 동작 검증
3. 장애 복구 테스트
4. 성능 메트릭 분석

이 아키텍처는 실제 프로덕션 환경에서 사용할 수 있는 견고하고 확장 가능한 컨테이너 기반 웹 애플리케이션 구조를 제공합니다. AWS SAA 시험에서 요구하는 다양한 서비스 통합과 모범 사례를 모두 포함하고 있습니다.

---

**관련 포스트:**
- [AWS SAA 컨테이너 마이크로서비스 아키텍처](../28/aws-saa-container-microservices-architecture)
- [AWS SAA 데이터베이스 성능 최적화](../24/aws-saa-database-performance-optimization)
