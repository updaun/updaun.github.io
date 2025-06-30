---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - Well-Architected Framework와 비용 최적화"
date: 2025-06-30 14:30:00 +0900
categories: [AWS, SAA]
tags: [AWS, SAA, WellArchitected, CostOptimization, FinOps, 비용최적화, 아키텍처설계]
---

# AWS SAA 실전 문제 풀이 및 분석 - Well-Architected Framework와 비용 최적화

AWS Solutions Architect Associate(SAA) 시험에서 점점 중요해지고 있는 Well-Architected Framework의 5가지 기둥 중 **비용 최적화(Cost Optimization)**에 중점을 둔 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 실제 기업 환경에서 자주 마주하는 비용 최적화 시나리오를 다루겠습니다.

## 📝 실전 문제

**상황**: 글로벌 스타트업 기업에서 AWS 클라우드 비용이 월 50,000달러에서 예상보다 빠르게 증가하고 있습니다. CTO는 성능과 가용성을 유지하면서 비용을 30% 절감하는 것을 목표로 하고 있습니다.

**현재 아키텍처**:
- 20개의 m5.2xlarge EC2 인스턴스 (24/7 운영)
- 100TB S3 스탠다드 스토리지 (50TB는 3개월 이상 미접근)
- RDS MySQL db.r5.2xlarge (Multi-AZ)
- CloudFront로 글로벌 콘텐츠 배포
- Application Load Balancer 3개
- EBS gp2 볼륨 총 50TB

**요구사항**:
- 성능 저하 없이 비용 30% 절감
- 고가용성 유지
- 확장성 보장
- 운영 복잡성 최소화

**가장 적절한 비용 최적화 전략은?**

**A)** 모든 EC2를 t3.large로 변경 + RDS를 단일 AZ로 변경 + S3를 Glacier로 이전

**B)** Reserved Instance 구매 + S3 Intelligent Tiering + RDS Aurora Serverless + Auto Scaling + EBS gp3 변환 + 사용량 모니터링 구현

**C)** 모든 서비스를 Spot Instance로 변경 + EFS 사용 + CloudFormation으로 자동화

**D)** Lambda + DynamoDB로 완전 서버리스 전환 + S3 Deep Archive 사용

---

## 🎯 정답 및 해설

### 정답: B

**Reserved Instance 구매 + S3 Intelligent Tiering + RDS Aurora Serverless + Auto Scaling + EBS gp3 변환 + 사용량 모니터링 구현**

### 상세 분석

#### 1. Well-Architected Cost Optimization 원칙

| 원칙 | 적용 방법 | 예상 절감 효과 |
|------|-----------|----------------|
| **적절한 사이징** | Auto Scaling, 사용량 분석 | 20-30% |
| **요금 모델 최적화** | Reserved Instance, Spot | 40-60% |
| **스토리지 최적화** | S3 Intelligent Tiering | 20-40% |
| **관리 오버헤드 최소화** | Aurora Serverless | 10-20% |
| **지속적 모니터링** | Cost Explorer, Budgets | 5-15% |

#### 2. 단계별 비용 최적화 전략

```
1단계: 즉시 적용 가능 (1주)
├── EBS gp2 → gp3 변환 (20% 절감)
├── Reserved Instance 구매 분석
└── S3 Intelligent Tiering 활성화

2단계: 아키텍처 변경 (2-4주)
├── Auto Scaling 구현
├── RDS Aurora Serverless 마이그레이션
└── 불필요한 리소스 정리

3단계: 지속적 최적화 (상시)
├── 비용 모니터링 자동화
├── 리소스 사용량 분석
└── 정기적 Right Sizing
```

## 🚀 상세 비용 최적화 구현

### 1. EC2 비용 최적화

#### Reserved Instance 전략
```json
{
  "ReservedInstanceStrategy": {
    "BaseCapacity": {
      "InstanceType": "m5.large",
      "Quantity": 10,
      "Term": "1year",
      "PaymentOption": "PartialUpfront",
      "EstimatedSavings": "40%"
    },
    "VariableCapacity": {
      "AutoScaling": true,
      "SpotInstances": {
        "MixedInstancesPolicy": {
          "InstanceTypes": ["m5.large", "m5.xlarge", "m4.large"],
          "SpotAllocationStrategy": "diversified",
          "OnDemandPercentage": 20
        }
      }
    }
  }
}
```

#### Auto Scaling 구성
```python
import boto3

def configure_auto_scaling():
    autoscaling = boto3.client('autoscaling')
    cloudwatch = boto3.client('cloudwatch')
    
    # 스케일링 정책 생성
    scale_up_policy = autoscaling.put_scaling_policy(
        AutoScalingGroupName='web-tier-asg',
        PolicyName='scale-up-policy',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            'TargetValue': 70.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ASGAverageCPUUtilization'
            },
            'ScaleOutCooldown': 300,
            'ScaleInCooldown': 300
        }
    )
    
    # 예측 스케일링 활성화
    autoscaling.put_scaling_policy(
        AutoScalingGroupName='web-tier-asg',
        PolicyName='predictive-scaling-policy',
        PolicyType='PredictiveScaling',
        PredictiveScalingConfiguration={
            'MetricSpecifications': [
                {
                    'TargetValue': 50.0,
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': 'ASGAverageCPUUtilization'
                    }
                }
            ],
            'Mode': 'ForecastAndScale',
            'SchedulingBufferTime': 300,
            'MaxCapacityBreachBehavior': 'HonorMaxCapacity'
        }
    )
    
    return scale_up_policy

configure_auto_scaling()
```

### 2. 스토리지 비용 최적화

#### S3 Intelligent Tiering 구성
```json
{
  "S3IntelligentTieringConfiguration": {
    "Id": "EntireBucketIntelligentTiering",
    "Status": "Enabled",
    "Filter": {
      "Prefix": ""
    },
    "Tierings": [
      {
        "Days": 90,
        "AccessTier": "ARCHIVE_ACCESS"
      },
      {
        "Days": 180, 
        "AccessTier": "DEEP_ARCHIVE_ACCESS"
      }
    ],
    "OptionalFields": [
      "BucketKeyStatus"
    ]
  }
}
```

#### S3 수명 주기 정책
```json
{
  "LifecycleConfiguration": {
    "Rules": [
      {
        "Id": "cost-optimization-rule",
        "Status": "Enabled",
        "Filter": {
          "Prefix": "logs/"
        },
        "Transitions": [
          {
            "Days": 30,
            "StorageClass": "STANDARD_IA"
          },
          {
            "Days": 90,
            "StorageClass": "GLACIER"
          },
          {
            "Days": 365,
            "StorageClass": "DEEP_ARCHIVE"
          }
        ],
        "Expiration": {
          "Days": 2555  // 7년 후 삭제
        }
      },
      {
        "Id": "incomplete-multipart-uploads-cleanup",
        "Status": "Enabled",
        "AbortIncompleteMultipartUpload": {
          "DaysAfterInitiation": 7
        }
      }
    ]
  }
}
```

### 3. 데이터베이스 비용 최적화

#### Aurora Serverless v2 구성
```json
{
  "AuroraServerlessConfiguration": {
    "Engine": "aurora-mysql",
    "EngineVersion": "8.0.mysql_aurora.3.02.0",
    "DatabaseName": "production",
    "ServerlessV2ScalingConfiguration": {
      "MinCapacity": 0.5,
      "MaxCapacity": 16,
      "AutoPause": false,
      "SecondsUntilAutoPause": 300
    },
    "BackupRetentionPeriod": 7,
    "PreferredBackupWindow": "03:00-04:00",
    "PreferredMaintenanceWindow": "sun:04:00-sun:05:00",
    "DeletionProtection": true,
    "StorageEncrypted": true
  }
}
```

#### 데이터베이스 성능 모니터링
```python
import boto3
import json

def setup_rds_monitoring():
    rds = boto3.client('rds')
    cloudwatch = boto3.client('cloudwatch')
    
    # Performance Insights 활성화
    rds.modify_db_cluster(
        DBClusterIdentifier='aurora-cluster',
        EnablePerformanceInsights=True,
        PerformanceInsightsRetentionPeriod=7  # 7일간 무료
    )
    
    # 비용 관련 알람 설정
    cloudwatch.put_metric_alarm(
        AlarmName='Aurora-High-ACU-Usage',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=3,
        MetricName='ACUUtilization',
        Namespace='AWS/RDS',
        Period=300,
        Statistic='Average',
        Threshold=80.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:region:account:aurora-cost-alerts'
        ],
        AlarmDescription='Aurora ACU usage is high - check for optimization opportunities'
    )

setup_rds_monitoring()
```

### 4. EBS 최적화

#### gp2에서 gp3로 변환
```python
import boto3

def migrate_ebs_gp2_to_gp3():
    ec2 = boto3.client('ec2')
    
    # 모든 gp2 볼륨 조회
    volumes = ec2.describe_volumes(
        Filters=[
            {
                'Name': 'volume-type',
                'Values': ['gp2']
            },
            {
                'Name': 'state',
                'Values': ['in-use', 'available']
            }
        ]
    )
    
    for volume in volumes['Volumes']:
        volume_id = volume['VolumeId']
        size = volume['Size']
        
        # 기본 gp3 설정 (3000 IOPS, 125 MB/s)
        # 대부분의 gp2 볼륨보다 성능이 좋고 20% 저렴
        try:
            response = ec2.modify_volume(
                VolumeId=volume_id,
                VolumeType='gp3',
                Iops=3000 if size >= 1 else size * 3000,  # 최소 3000 IOPS
                Throughput=125  # MB/s
            )
            
            print(f"Volume {volume_id} migration initiated")
            
        except Exception as e:
            print(f"Failed to migrate volume {volume_id}: {e}")

migrate_ebs_gp2_to_gp3()
```

### 5. 비용 모니터링 및 알림 시스템

#### Cost Anomaly Detection 설정
```json
{
  "CostAnomalyDetector": {
    "AnomalyDetectorName": "comprehensive-cost-monitor",
    "MonitorType": "DIMENSIONAL",
    "DimensionKey": "SERVICE",
    "MatchOptions": [
      "EQUALS"
    ],
    "MonitorSpecification": {
      "DimensionKey": "SERVICE",
      "MatchOptions": [
        "EQUALS"
      ],
      "Values": [
        "Amazon Elastic Compute Cloud - Compute",
        "Amazon Relational Database Service",
        "Amazon Simple Storage Service"
      ]
    }
  }
}
```

#### 비용 예산 및 알림
```python
import boto3

def setup_cost_budgets():
    budgets = boto3.client('budgets')
    
    # 월별 예산 설정
    monthly_budget = {
        'BudgetName': 'monthly-cost-budget',
        'BudgetLimit': {
            'Amount': '35000',  # 30% 절감 목표
            'Unit': 'USD'
        },
        'TimeUnit': 'MONTHLY',
        'BudgetType': 'COST',
        'CostFilters': {},
        'CalculatedSpend': {}
    }
    
    # 예산 알림 설정
    notification = {
        'Notification': {
            'NotificationType': 'ACTUAL',
            'ComparisonOperator': 'GREATER_THAN',
            'Threshold': 80,  # 80% 도달 시 알림
            'ThresholdType': 'PERCENTAGE'
        },
        'Subscribers': [
            {
                'SubscriptionType': 'EMAIL',
                'Address': 'cto@company.com'
            },
            {
                'SubscriptionType': 'SNS',
                'Address': 'arn:aws:sns:region:account:cost-alerts'
            }
        ]
    }
    
    budgets.create_budget(
        AccountId='123456789012',
        Budget=monthly_budget,
        NotificationsWithSubscribers=[notification]
    )
    
    return monthly_budget

setup_cost_budgets()
```

## 📊 비용 절감 효과 분석

### 1. 예상 월별 비용 비교

| 서비스 | 현재 비용 | 최적화 후 | 절감액 | 절감률 |
|--------|-----------|-----------|--------|--------|
| **EC2 (RI + Spot)** | $12,000 | $7,200 | $4,800 | 40% |
| **S3 (Intelligent Tiering)** | $2,300 | $1,380 | $920 | 40% |
| **RDS (Aurora Serverless)** | $8,500 | $5,100 | $3,400 | 40% |
| **EBS (gp3)** | $1,500 | $1,200 | $300 | 20% |
| **Data Transfer** | $3,200 | $2,880 | $320 | 10% |
| **기타** | $2,500 | $2,240 | $260 | 10% |
| **총합** | **$30,000** | **$20,000** | **$10,000** | **33%** |

### 2. ROI 계산

```python
def calculate_cost_optimization_roi():
    # 초기 구현 비용
    implementation_cost = {
        'engineering_time': 160,  # 시간
        'hourly_rate': 100,       # 달러/시간
        'tools_licenses': 2000,   # 달러
        'consulting': 5000        # 달러
    }
    
    total_implementation = (
        implementation_cost['engineering_time'] * 
        implementation_cost['hourly_rate'] + 
        implementation_cost['tools_licenses'] + 
        implementation_cost['consulting']
    )
    
    # 월별 절감액
    monthly_savings = 10000  # 달러
    
    # ROI 계산
    payback_period = total_implementation / monthly_savings
    annual_roi = ((monthly_savings * 12) - total_implementation) / total_implementation * 100
    
    print(f"Implementation Cost: ${total_implementation:,}")
    print(f"Monthly Savings: ${monthly_savings:,}")
    print(f"Payback Period: {payback_period:.1f} months")
    print(f"Annual ROI: {annual_roi:.1f}%")
    
    return {
        'implementation_cost': total_implementation,
        'monthly_savings': monthly_savings,
        'payback_months': payback_period,
        'annual_roi': annual_roi
    }

roi_analysis = calculate_cost_optimization_roi()
```

### 3. 지속적 최적화 프로세스

```python
import boto3
from datetime import datetime, timedelta

def automated_cost_optimization():
    """주간 비용 최적화 자동화"""
    
    # 1. 사용량이 낮은 인스턴스 식별
    def identify_underutilized_instances():
        cloudwatch = boto3.client('cloudwatch')
        ec2 = boto3.client('ec2')
        
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        underutilized = []
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                # 지난 14일간 평균 CPU 사용률 조회
                cpu_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[
                        {'Name': 'InstanceId', 'Value': instance_id}
                    ],
                    StartTime=datetime.utcnow() - timedelta(days=14),
                    EndTime=datetime.utcnow(),
                    Period=3600,  # 1시간
                    Statistics=['Average']
                )
                
                avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])
                
                if avg_cpu < 10:  # 10% 미만 사용률
                    underutilized.append({
                        'InstanceId': instance_id,
                        'InstanceType': instance['InstanceType'],
                        'AvgCPU': avg_cpu
                    })
        
        return underutilized
    
    # 2. 고아 리소스 식별
    def identify_orphaned_resources():
        ec2 = boto3.client('ec2')
        
        # 연결되지 않은 EBS 볼륨
        volumes = ec2.describe_volumes(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
        
        # 사용되지 않는 Elastic IP
        addresses = ec2.describe_addresses(
            Filters=[{'Name': 'association-id', 'Values': []}]
        )
        
        # 사용되지 않는 스냅샷 (6개월 이상)
        snapshots = ec2.describe_snapshots(
            OwnerIds=['self'],
            Filters=[
                {
                    'Name': 'start-time',
                    'Values': [
                        (datetime.utcnow() - timedelta(days=180)).strftime('%Y-%m-%d')
                    ]
                }
            ]
        )
        
        return {
            'orphaned_volumes': volumes['Volumes'],
            'unused_eips': addresses['Addresses'],
            'old_snapshots': snapshots['Snapshots']
        }
    
    # 3. 비용 최적화 권장사항 생성
    def generate_recommendations():
        underutilized = identify_underutilized_instances()
        orphaned = identify_orphaned_resources()
        
        recommendations = []
        
        # Right Sizing 권장사항
        for instance in underutilized:
            savings = estimate_rightsizing_savings(instance)
            recommendations.append({
                'type': 'rightsizing',
                'resource': instance['InstanceId'],
                'action': f"Downsize from {instance['InstanceType']}",
                'estimated_savings': savings
            })
        
        # 리소스 정리 권장사항
        for volume in orphaned['orphaned_volumes']:
            recommendations.append({
                'type': 'cleanup',
                'resource': volume['VolumeId'],
                'action': 'Delete orphaned EBS volume',
                'estimated_savings': calculate_ebs_cost(volume['Size'])
            })
        
        return recommendations
    
    return generate_recommendations()

def estimate_rightsizing_savings(instance):
    # 인스턴스 타입별 시간당 비용 (예시)
    pricing = {
        'm5.2xlarge': 0.384,
        'm5.xlarge': 0.192,
        'm5.large': 0.096,
        't3.xlarge': 0.166,
        't3.large': 0.083
    }
    
    current_cost = pricing.get(instance['InstanceType'], 0)
    recommended_cost = pricing.get('t3.large', 0)  # 기본 권장사항
    
    return (current_cost - recommended_cost) * 24 * 30  # 월별 절감액

# 주간 실행
weekly_recommendations = automated_cost_optimization()
```

## 🏗️ 완성된 비용 최적화 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                 Cost Governance                     │
├─────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│ │Cost Explorer│ │   Budgets   │ │ Anomaly Detection││
│ │  (분석)      │ │  (예산관리)  │ │   (이상탐지)     │ │
│ └─────────────┘ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│              Optimized Infrastructure               │
├─────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│ │EC2 (RI+Spot)│ │ S3 Intelli  │ │Aurora Serverless│ │
│ │Auto Scaling │ │ Tiering     │ │   (v2)          │ │
│ └─────────────┘ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│              Monitoring & Automation                │
├─────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│ │ CloudWatch  │ │   Lambda    │ │ Cost Optimization│
│ │ (메트릭수집) │ │ (자동화)     │ │ Recommendations │ │
│ └─────────────┘ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## ❌ 다른 선택지가 부적절한 이유

### A) 단순한 인스턴스 다운사이징
- **성능 저하 위험**: t3.large는 버스터블 성능으로 일관된 성능 보장 어려움
- **가용성 감소**: RDS 단일 AZ는 고가용성 요구사항 위배
- **접근성 문제**: 자주 접근하는 데이터를 Glacier로 이전하면 지연 발생

### C) Spot Instance 중심 전략
- **가용성 위험**: Spot Instance는 언제든 회수 가능하여 프로덕션에 부적합
- **복잡성 증가**: EFS 도입으로 아키텍처 복잡성 증가
- **일관성 없는 성능**: 예측 불가능한 중단으로 사용자 경험 저하

### D) 서버리스 전환
- **과도한 변경**: 기존 애플리케이션을 Lambda로 리팩토링하는 데 많은 시간과 비용 소요
- **제약사항**: DynamoDB는 관계형 데이터 모델에 적합하지 않을 수 있음
- **Deep Archive**: 매우 긴 복구 시간으로 운영 데이터에 부적합

## 🔧 구현 로드맵

### Phase 1: 즉시 적용 (1-2주)
1. **EBS gp3 마이그레이션**
   - 스크립트 실행으로 자동 변환
   - 즉시 20% 비용 절감

2. **S3 Intelligent Tiering 활성화**
   - 기존 데이터에 즉시 적용
   - 30-40% 스토리지 비용 절감

3. **Reserved Instance 분석 및 구매**
   - 1년 약정으로 40-60% 절감

### Phase 2: 아키텍처 최적화 (3-4주)
1. **Auto Scaling 구현**
   - 동적 스케일링으로 과도한 용량 제거
   - 예측 스케일링으로 성능 보장

2. **Aurora Serverless 마이그레이션**
   - 사용량 기반 과금으로 비용 절감
   - 자동 스케일링으로 성능 유지

### Phase 3: 지속적 최적화 (진행 중)
1. **비용 모니터링 자동화**
   - 이상 탐지 및 알림
   - 주간 최적화 권장사항

2. **Right Sizing 자동화**
   - 사용량 분석 기반 권장사항
   - 정기적 리소스 검토

## 🎓 핵심 학습 포인트

1. **Well-Architected 비용 최적화**: 성능과 가용성을 유지하면서 비용 절감
2. **다층 접근법**: 즉시 적용 가능한 것부터 장기적 최적화까지 단계적 접근
3. **자동화 중심**: 수동 작업 최소화로 지속적 최적화 보장
4. **데이터 기반 의사결정**: 실제 사용량 데이터를 기반으로 한 최적화
5. **ROI 중심 사고**: 구현 비용 대비 절감 효과 분석

## 💭 마무리

이번 포스트에서는 AWS Well-Architected Framework의 비용 최적화 원칙을 실제 시나리오에 적용하는 방법을 살펴봤습니다. 33%의 비용 절감을 달성하면서도 성능과 가용성을 유지하는 전략은 다음과 같습니다:

1. **즉시 적용**: RI 구매, EBS gp3 변환, S3 Intelligent Tiering
2. **아키텍처 최적화**: Auto Scaling, Aurora Serverless 도입
3. **지속적 개선**: 자동화된 모니터링과 권장사항 시스템

비용 최적화는 일회성이 아닌 지속적인 프로세스입니다. 정기적인 검토와 새로운 AWS 서비스의 도입을 통해 더 큰 절감 효과를 얻을 수 있습니다.

이로써 AWS SAA 실전 문제 풀이 시리즈가 완성되었습니다. **인프라, 보안, 데이터베이스, 서버리스, 빅데이터, 하이브리드, 컨테이너, 재해복구, 그리고 비용 최적화**까지 모든 주요 영역을 다뤘습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - 데이터베이스 성능 최적화]({% post_url 2025-06-24-aws-saa-database-performance-optimization %})
- [AWS SAA 실전 문제 풀이 - 서버리스 아키텍처]({% post_url 2025-06-25-aws-saa-serverless-event-driven-architecture %})
- [AWS SAA 실전 문제 풀이 - 빅데이터 분석 아키텍처]({% post_url 2025-06-26-aws-saa-bigdata-analytics-architecture %})
- [AWS SAA 실전 문제 풀이 - 하이브리드 클라우드 마이그레이션]({% post_url 2025-06-27-aws-saa-hybrid-cloud-migration-strategy %})
- [AWS SAA 실전 문제 풀이 - 컨테이너 오케스트레이션]({% post_url 2025-06-28-aws-saa-container-microservices-architecture %})
- [AWS SAA 실전 문제 풀이 - 재해 복구와 백업 전략]({% post_url 2025-06-29-aws-saa-disaster-recovery-backup-strategy %})

**태그**: #AWS #SAA #WellArchitected #CostOptimization #FinOps #ReservedInstance #AutoScaling #비용최적화 #아키텍처설계
