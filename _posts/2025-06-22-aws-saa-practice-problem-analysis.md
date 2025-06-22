---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - Auto Scaling과 Load Balancer 설계"
date: 2025-06-22
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - Auto Scaling과 Load Balancer 설계

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 실제 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 고가용성과 확장성을 고려한 웹 애플리케이션 아키텍처 설계 문제를 다루겠습니다.

## 📝 실전 문제

**문제**: 한 회사가 3-tier 웹 애플리케이션을 AWS에 배포하려고 합니다. 이 애플리케이션은 다음과 같은 요구사항을 가지고 있습니다:

- 트래픽 변동에 따라 자동으로 확장 및 축소되어야 함
- 단일 장애점(Single Point of Failure) 제거
- 데이터베이스는 읽기 성능 최적화가 필요
- 비용 효율적인 솔루션

다음 중 이 요구사항을 가장 잘 만족하는 아키텍처는?

**A)** 단일 가용 영역에 EC2 인스턴스와 RDS Multi-AZ 배포

**B)** 여러 가용 영역에 걸친 Application Load Balancer, Auto Scaling Group의 EC2 인스턴스, RDS with Read Replicas

**C)** CloudFront와 단일 EC2 인스턴스, RDS 단일 인스턴스

**D)** Elastic Beanstalk을 사용한 단일 가용 영역 배포

## 🎯 정답 및 해설

### 정답: B

**여러 가용 영역에 걸친 Application Load Balancer, Auto Scaling Group의 EC2 인스턴스, RDS with Read Replicas**

### 상세 분석

#### 1. 트래픽 변동에 따른 자동 확장/축소
- **Auto Scaling Group**: CPU 사용률, 네트워크 트래픽 등의 메트릭을 기반으로 EC2 인스턴스를 자동으로 추가하거나 제거
- **확장 정책 예시**:
  ```
  Scale Out: CPU > 70% for 2 consecutive periods
  Scale In: CPU < 30% for 5 consecutive periods
  ```

#### 2. 단일 장애점 제거
- **Application Load Balancer (ALB)**: 여러 가용 영역에 분산되어 고가용성 제공
- **Multi-AZ 배포**: EC2 인스턴스들이 여러 가용 영역에 분산 배치
- **RDS Multi-AZ**: 자동 장애 조치를 통한 데이터베이스 고가용성

#### 3. 읽기 성능 최적화
- **RDS Read Replicas**: 읽기 전용 복제본을 통해 읽기 워크로드 분산
- **읽기/쓰기 분리**: 애플리케이션에서 읽기와 쓰기 트래픽을 분리하여 성능 향상

#### 4. 비용 효율성
- **Auto Scaling**: 필요한 만큼만 리소스 사용으로 비용 최적화
- **Read Replicas**: 비싼 컴퓨팅 인스턴스 대신 읽기 성능 향상

## 🏗️ 권장 아키텍처 상세 설계

### 네트워크 계층
```
Internet Gateway
    ↓
Application Load Balancer (Public Subnets)
    ↓
EC2 Instances in Auto Scaling Group (Private Subnets)
    ↓
RDS Primary + Read Replicas (Private DB Subnets)
```

### 가용 영역별 구성
- **AZ-a**: ALB, EC2 인스턴스, RDS Primary
- **AZ-b**: ALB, EC2 인스턴스, RDS Read Replica
- **AZ-c**: ALB, EC2 인스턴스, RDS Read Replica

### Auto Scaling 설정 예시
```json
{
  "MinSize": 2,
  "MaxSize": 10,
  "DesiredCapacity": 4,
  "TargetGroupARNs": ["arn:aws:elasticloadbalancing:..."],
  "HealthCheckType": "ELB",
  "HealthCheckGracePeriod": 300
}
```

## ❌ 다른 선택지가 부적절한 이유

### A) 단일 가용 영역 배포
- **문제점**: 가용 영역 장애 시 전체 서비스 중단
- **확장성 부족**: Auto Scaling 없이 수동 확장만 가능

### C) CloudFront + 단일 EC2
- **문제점**: EC2 인스턴스가 단일 장애점
- **확장성 없음**: 트래픽 증가 시 대응 불가
- **데이터베이스 읽기 최적화 부족**

### D) Elastic Beanstalk 단일 AZ
- **문제점**: 단일 가용 영역으로 고가용성 부족
- **확장성 제한**: 기본 설정으로는 요구사항 미충족

## 💡 추가 최적화 방안

### 1. 성능 최적화
- **CloudFront CDN**: 정적 콘텐츠 캐싱으로 응답 속도 향상
- **ElastiCache**: 데이터베이스 캐싱으로 읽기 성능 향상
- **Aurora**: MySQL/PostgreSQL 호환성과 함께 자동 확장

### 2. 보안 강화
- **Security Groups**: 최소 권한 원칙 적용
- **WAF**: 웹 애플리케이션 방화벽으로 보안 위협 차단
- **VPC**: 네트워크 격리 및 보안 강화

### 3. 모니터링 및 운영
- **CloudWatch**: 메트릭 모니터링 및 알람 설정
- **ELB Health Checks**: 비정상 인스턴스 자동 교체
- **Auto Scaling Notifications**: 확장/축소 이벤트 알림

## 📊 비용 최적화 전략

### Reserved Instances
- 예측 가능한 베이스라인 용량을 위한 RI 구매
- 1년 또는 3년 약정으로 최대 75% 비용 절감

### Spot Instances
- 개발/테스트 환경에서 Spot 인스턴스 활용
- Auto Scaling에서 On-Demand와 Spot 인스턴스 혼합 사용

### 리소스 태깅
- 비용 추적을 위한 태깅 전략 수립
- AWS Cost Explorer를 통한 비용 분석

## 🎓 핵심 학습 포인트

1. **고가용성 설계**: 항상 여러 가용 영역 활용
2. **확장성 고려**: Auto Scaling Group과 Load Balancer 조합
3. **데이터베이스 성능**: Read Replicas로 읽기 성능 최적화
4. **비용 효율성**: 필요한 만큼만 사용하는 탄력적 아키텍처
5. **단일 장애점 제거**: 모든 계층에서 이중화 구성

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 전형적인 3-tier 아키텍처 설계 문제입니다. 고가용성, 확장성, 성능, 비용 효율성을 모두 고려해야 하는 실무 상황을 잘 반영하고 있습니다.

실제 시험에서는 이런 문제를 해결할 때 다음 순서로 접근하는 것이 좋습니다:

1. **요구사항 분석**: 고가용성, 확장성, 성능, 비용 등
2. **장애점 식별**: 단일 장애점이 될 수 있는 요소들 파악
3. **서비스 매칭**: 요구사항에 맞는 AWS 서비스 선택
4. **아키텍처 검증**: 모든 요구사항이 충족되는지 확인

다음 포스트에서는 보안과 관련된 SAA 문제를 다뤄보겠습니다. AWS 보안 모범 사례와 함께 IAM, VPC, 암호화 등을 활용한 보안 아키텍처 설계에 대해 알아보겠습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})

**태그**: #AWS #SAA #Solutions-Architect #Auto-Scaling #Load-Balancer #RDS #고가용성
