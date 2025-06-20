---
layout: post
title: "AWS SAA(Solutions Architect Associate) 자격증 공부 범위 총정리"
date: 2025-06-20
categories: aws-saa
author: updaun
---

# AWS SAA(Solutions Architect Associate) 자격증 공부 범위 총정리

AWS Solutions Architect Associate 자격증을 준비하시는 분들을 위해 시험 범위와 핵심 서비스에 대해 정리해보았습니다. 이 가이드를 통해 AWS SAA 자격증 공부의 방향을 잡으시는 데 도움이 되기를 바랍니다.

## AWS SAA 시험 개요

AWS Certified Solutions Architect – Associate 자격증은 AWS 클라우드 기반 애플리케이션의 설계와 배포에 대한 지식과 기술을 평가합니다. 시험은 다중 선택형과 다중 응답형 문항으로 구성되며, 총 130분 동안 65문항을 풀어야 합니다.

## 주요 시험 도메인 및 비중

AWS SAA 시험은 다음과 같은 4개의 도메인으로 나뉘어 평가됩니다:

1. **설계 보안 아키텍처(30%)**: 보안 제어, 데이터 보호, 권한 관리
2. **설계 복원력 있는 아키텍처(28%)**: 고가용성, 내결함성, 재해 복구
3. **설계 고성능 아키텍처(24%)**: 확장성, 탄력성, 효율적인 리소스 사용
4. **비용 최적화 아키텍처 설계(18%)**: 비용 효율적인 스토리지, 컴퓨팅 솔루션

## 핵심 서비스별 필수 학습 내용

### 1. 컴퓨팅 서비스

#### EC2(Elastic Compute Cloud)
- 인스턴스 유형 및 사용 사례
- 인스턴스 구매 옵션(온디맨드, 예약 인스턴스, 스팟 인스턴스)
- 오토 스케일링 그룹(ASG)
- 배치 그룹과 배포 전략

#### ECS(Elastic Container Service) & EKS(Elastic Kubernetes Service)
- 컨테이너 기반 애플리케이션 관리
- 클러스터 구성과 서비스 배포

#### Lambda
- 서버리스 컴퓨팅 아키텍처
- 트리거와 통합 서비스
- 함수 설계와 모범 사례

### 2. 스토리지 서비스

#### S3(Simple Storage Service)
- 스토리지 클래스 및 수명 주기 정책
- 버전 관리와 객체 잠금
- 액세스 제어 및 암호화 방법
- S3 Transfer Acceleration과 Multipart Upload

#### EBS(Elastic Block Store)
- 볼륨 유형과 성능 특성
- 스냅샷 및 복원 전략
- IOPS와 처리량 최적화

#### EFS(Elastic File System) & FSx
- 파일 시스템 사용 사례
- 성능과 확장성
- 마운트 대상 및 액세스 포인트

#### Storage Gateway
- 하이브리드 클라우드 스토리지 솔루션
- 볼륨 게이트웨이, 파일 게이트웨이, 테이프 게이트웨이 

### 3. 네트워킹 서비스

#### VPC(Virtual Private Cloud)
- 서브넷 설계 및 IP 주소 관리
- 라우팅 테이블과 인터넷 게이트웨이
- NAT 게이트웨이/인스턴스
- VPC Peering과 VPC Endpoints
- PrivateLink와 Transit Gateway

#### Route 53
- DNS 라우팅 정책
- 상태 확인과 장애 조치
- 지연 시간 기반 라우팅
- 지역 및 지오로케이션 라우팅

#### CloudFront
- CDN 아키텍처
- 오리진과 배포 설정
- 캐싱 전략과 TTL
- Lambda@Edge와 OAC(Origin Access Control)

### 4. 데이터베이스 서비스

#### RDS(Relational Database Service)
- DB 엔진 옵션(MySQL, PostgreSQL, SQL Server, Oracle, MariaDB)
- 다중 AZ 배포와 읽기 전용 복제본
- 백업 및 복원 전략
- 암호화 및 보안

#### Aurora
- 고가용성 및 성능 특성
- 글로벌 데이터베이스
- 서버리스 구성

#### DynamoDB
- NoSQL 설계 패턴
- 파티션 키와 정렬 키 선택
- 읽기/쓰기 처리량
- DAX(DynamoDB Accelerator)와 글로벌 테이블

#### ElastiCache
- Redis와 Memcached 비교
- 캐싱 전략
- 온라인 리샤딩

### 5. 애플리케이션 통합

#### SQS(Simple Queue Service)
- 표준 대기열과 FIFO 대기열
- 메시지 보존 및 가시성 제한 시간
- 데드레터 큐

#### SNS(Simple Notification Service)
- 주제와 구독
- 메시지 필터링
- 팬아웃 패턴

#### EventBridge(CloudWatch Events)
- 이벤트 버스 및 규칙
- 이벤트 필터링 패턴
- 스케줄링된 이벤트

### 6. 보안 및 자격 증명

#### IAM(Identity and Access Management)
- 사용자, 그룹, 역할, 정책
- 자격 증명 연동
- 권한 경계
- 최소 권한 원칙

#### AWS Organizations
- 다중 계정 관리
- SCP(서비스 제어 정책)
- 태그 정책

#### AWS WAF & Shield
- 웹 애플리케이션 보안
- DDoS 방어
- 보안 그룹과 NACL 설계

#### KMS(Key Management Service) & CloudHSM
- 암호화 키 관리
- 엔벨로프 암호화
- 데이터 암호화 전략

### 7. 모니터링 및 관찰성

#### CloudWatch
- 지표와 경보
- 로그 관리
- 대시보드 생성

#### CloudTrail
- 계정 활동 모니터링
- 이벤트 기록
- 규정 준수 감사

#### X-Ray
- 분산 애플리케이션 추적
- 서비스 맵
- 성능 병목 식별

## 효과적인 공부 전략

1. **AWS 공식 문서 활용**: 각 서비스의 개발자 안내서와 FAQ 섹션을 자세히 읽어보세요.

2. **실습 중심 학습**: 실제로 AWS 콘솔에서 서비스를 구성하고 실행해보는 것이 중요합니다. AWS Free Tier를 활용하세요.

3. **샘플 문제 풀이**: AWS에서 제공하는 샘플 문제와 연습 시험을 적극적으로 활용하세요.

4. **백서 및 아키텍처 센터 참고**: AWS의 Well-Architected Framework와 아키텍처 센터의 참조 아키텍처를 공부하세요.

5. **커뮤니티 참여**: AWS 커뮤니티 및 포럼을 통해 다른 사람들의 경험과 해결책을 배우세요.

## 결론

AWS SAA 시험은 AWS 클라우드 인프라를 설계하고 배포하는 능력을 평가합니다. 위에서 언급한 서비스들과 개념을 철저히 이해하고 실습을 통해 경험을 쌓는다면 시험에 충분히 대비할 수 있습니다.

AWS 서비스는 계속해서 발전하고 있으므로 최신 정보를 지속적으로 업데이트하는 것이 중요합니다. AWS의 새로운 기능과 서비스에 대해 관심을 가지고 학습하시기 바랍니다.

행운을 빕니다! AWS SAA 자격증 취득을 향한 여러분의 여정이 성공적이길 바랍니다.
