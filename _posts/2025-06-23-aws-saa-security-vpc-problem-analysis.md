---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - VPC 보안과 네트워크 ACL 설계"
date: 2025-06-23
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - VPC 보안과 네트워크 ACL 설계

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 보안 및 네트워킹 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 VPC 보안 그룹과 네트워크 ACL을 활용한 다층 보안 아키텍처 설계 문제를 다루겠습니다.

## 📝 실전 문제

**문제**: 한 금융 회사가 AWS VPC에 3-tier 웹 애플리케이션을 배포하려고 합니다. 보안 요구사항은 다음과 같습니다:

- 웹 서버는 인터넷에서 HTTP(80), HTTPS(443) 트래픽만 허용
- 애플리케이션 서버는 웹 서버에서만 접근 가능 (포트 8080)
- 데이터베이스 서버는 애플리케이션 서버에서만 접근 가능 (포트 3306)
- 모든 아웃바운드 트래픽은 관리자가 승인한 특정 포트와 대상만 허용
- 네트워크 레벨과 인스턴스 레벨에서 이중 보안 적용

이 요구사항을 만족하는 가장 적절한 보안 구성은?

**A)** Security Groups만 사용하여 각 계층별로 구성

**B)** Network ACLs만 사용하여 서브넷 레벨에서 제어

**C)** Security Groups와 Network ACLs를 조합하여 다층 보안 구성

**D)** WAF와 Security Groups 조합으로 구성

## 🎯 정답 및 해설

### 정답: C

**Security Groups와 Network ACLs를 조합하여 다층 보안 구성**

### 상세 분석

#### 1. Security Groups vs Network ACLs 비교

| 특성 | Security Groups | Network ACLs |
|------|----------------|--------------|
| 적용 레벨 | 인스턴스 레벨 | 서브넷 레벨 |
| 규칙 타입 | Allow 규칙만 | Allow/Deny 규칙 |
| 상태 관리 | Stateful | Stateless |
| 기본 정책 | 모든 트래픽 차단 | 모든 트래픽 허용 |
| 적용 순서 | 모든 규칙 평가 | 규칙 번호 순서대로 |

#### 2. 다층 보안 아키텍처 설계

```
Internet Gateway
    ↓
Public Subnet (Web Tier)
├── Network ACL: 80,443 허용
└── Security Group: 80,443 허용
    ↓
Private Subnet (App Tier)  
├── Network ACL: 8080 허용 (Web Subnet에서만)
└── Security Group: 8080 허용 (Web SG에서만)
    ↓
Private Subnet (DB Tier)
├── Network ACL: 3306 허용 (App Subnet에서만)
└── Security Group: 3306 허용 (App SG에서만)
```

## 🛡️ 보안 구성 상세 설계

### Web Tier 보안 설정

#### Network ACL (Public Subnet)
```json
{
  "NetworkAclEntries": [
    {
      "RuleNumber": 100,
      "Protocol": "6",
      "RuleAction": "allow",
      "PortRange": {"From": 80, "To": 80},
      "CidrBlock": "0.0.0.0/0"
    },
    {
      "RuleNumber": 110,
      "Protocol": "6", 
      "RuleAction": "allow",
      "PortRange": {"From": 443, "To": 443},
      "CidrBlock": "0.0.0.0/0"
    },
    {
      "RuleNumber": 120,
      "Protocol": "6",
      "RuleAction": "allow", 
      "PortRange": {"From": 1024, "To": 65535},
      "CidrBlock": "0.0.0.0/0"
    }
  ]
}
```

#### Security Group (Web Servers)
```json
{
  "SecurityGroupRules": [
    {
      "IpProtocol": "tcp",
      "FromPort": 80,
      "ToPort": 80,
      "CidrIp": "0.0.0.0/0"
    },
    {
      "IpProtocol": "tcp",
      "FromPort": 443, 
      "ToPort": 443,
      "CidrIp": "0.0.0.0/0"
    }
  ]
}
```

### App Tier 보안 설정

#### Network ACL (Private Subnet - App)
```json
{
  "NetworkAclEntries": [
    {
      "RuleNumber": 100,
      "Protocol": "6",
      "RuleAction": "allow",
      "PortRange": {"From": 8080, "To": 8080},
      "CidrBlock": "10.0.1.0/24"
    },
    {
      "RuleNumber": 110,
      "Protocol": "6",
      "RuleAction": "allow",
      "PortRange": {"From": 1024, "To": 65535}, 
      "CidrBlock": "0.0.0.0/0"
    }
  ]
}
```

#### Security Group (App Servers)
```json
{
  "SecurityGroupRules": [
    {
      "IpProtocol": "tcp",
      "FromPort": 8080,
      "ToPort": 8080,
      "SourceSecurityGroupId": "sg-web-servers"
    }
  ]
}
```

### DB Tier 보안 설정

#### Network ACL (Private Subnet - DB)
```json
{
  "NetworkAclEntries": [
    {
      "RuleNumber": 100,
      "Protocol": "6", 
      "RuleAction": "allow",
      "PortRange": {"From": 3306, "To": 3306},
      "CidrBlock": "10.0.2.0/24"
    },
    {
      "RuleNumber": 110,
      "Protocol": "6",
      "RuleAction": "allow",
      "PortRange": {"From": 1024, "To": 65535},
      "CidrBlock": "10.0.2.0/24"
    }
  ]
}
```

#### Security Group (DB Servers)
```json
{
  "SecurityGroupRules": [
    {
      "IpProtocol": "tcp",
      "FromPort": 3306,
      "ToPort": 3306,
      "SourceSecurityGroupId": "sg-app-servers"
    }
  ]
}
```

## ❌ 다른 선택지가 부적절한 이유

### A) Security Groups만 사용
- **문제점**: 인스턴스 레벨 보안만 제공
- **부족한 점**: 네트워크 레벨 추가 보안층 없음
- **위험성**: 인스턴스 침해 시 네트워크 레벨 방어 부재

### B) Network ACLs만 사용  
- **문제점**: Stateless 특성으로 복잡한 구성 필요
- **부족한 점**: 세밀한 인스턴스별 제어 어려움
- **관리 복잡성**: 응답 트래픽 허용을 위한 추가 규칙 필요

### D) WAF + Security Groups
- **적용 범위**: WAF는 웹 애플리케이션 계층 보안에 특화
- **부족한 점**: 네트워크 계층 보안 부재
- **비용**: 불필요한 WAF 비용 발생

## 🔐 추가 보안 강화 방안

### 1. VPC Flow Logs
```json
{
  "VpcFlowLogConfig": {
    "ResourceType": "VPC",
    "TrafficType": "ALL",
    "LogDestination": "arn:aws:logs:region:account:log-group:VPCFlowLogs",
    "DeliverLogsPermissionArn": "arn:aws:iam::account:role/flowlogsRole"
  }
}
```

### 2. Systems Manager Session Manager
- EC2 인스턴스 SSH 접근 대신 Session Manager 사용
- 감사 로그 자동 기록
- 포트 22 완전 차단 가능

### 3. AWS Config Rules
```json
{
  "ConfigRules": [
    {
      "ConfigRuleName": "security-group-ssh-check",
      "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "INCOMING_SSH_DISABLED"
      }
    },
    {
      "ConfigRuleName": "vpc-sg-open-only-to-authorized-ports", 
      "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS"
      }
    }
  ]
}
```

### 4. AWS GuardDuty
- 네트워크 트래픽 이상 징후 탐지
- 악성 IP 주소 접근 탐지
- 데이터 유출 시도 탐지

## 🏗️ 완성된 보안 아키텍처

### VPC 구성도
```
┌─────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                │
├─────────────────────────────────────────────────────┤
│  Public Subnet (10.0.1.0/24)                       │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │   Web Server    │  │   Web Server    │          │
│  │  (SG: Web-SG)   │  │  (SG: Web-SG)   │          │
│  └─────────────────┘  └─────────────────┘          │
│           │                    │                    │
│  ┌────────┴────────────────────┴──────────┐        │
│  │         Network ACL (Web)             │        │
│  └───────────────────────────────────────┘        │
├─────────────────────────────────────────────────────┤
│  Private Subnet (10.0.2.0/24)                      │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │   App Server    │  │   App Server    │          │
│  │  (SG: App-SG)   │  │  (SG: App-SG)   │          │
│  └─────────────────┘  └─────────────────┘          │
│           │                    │                    │
│  ┌────────┴────────────────────┴──────────┐        │
│  │         Network ACL (App)             │        │
│  └───────────────────────────────────────┘        │
├─────────────────────────────────────────────────────┤
│  Private Subnet (10.0.3.0/24)                      │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │   DB Primary    │  │   DB Replica    │          │
│  │  (SG: DB-SG)    │  │  (SG: DB-SG)    │          │
│  └─────────────────┘  └─────────────────┘          │
│           │                    │                    │
│  ┌────────┴────────────────────┴──────────┐        │
│  │         Network ACL (DB)              │        │
│  └───────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

### 보안 레이어별 역할

1. **Internet Gateway**: 외부 인터넷 연결 제어
2. **Public Subnet NACL**: 네트워크 레벨 첫 번째 방어선
3. **Web Security Group**: 웹 서버 인스턴스별 세밀한 제어
4. **Private Subnet NACL**: 내부 네트워크 간 통신 제어  
5. **App/DB Security Group**: 애플리케이션 레벨 접근 제어

## 📊 보안 모니터링 및 알람

### CloudWatch 알람 설정
```json
{
  "MetricAlarms": [
    {
      "AlarmName": "UnauthorizedSSHAttempts",
      "MetricName": "UnauthorizedSSHCalls",
      "Namespace": "VPCFlowLogs",
      "Statistic": "Sum",
      "Threshold": 5,
      "ComparisonOperator": "GreaterThanThreshold"
    },
    {
      "AlarmName": "UnusualNetworkTraffic",
      "MetricName": "NetworkPacketsIn", 
      "Namespace": "AWS/EC2",
      "Statistic": "Average",
      "Threshold": 1000000,
      "ComparisonOperator": "GreaterThanThreshold"
    }
  ]
}
```

### AWS Config 컴플라이언스 모니터링
- 보안 그룹 설정 변경 감지
- 네트워크 ACL 수정 알림
- 비승인 포트 개방 탐지

## 💡 보안 모범 사례

### 1. 최소 권한 원칙 (Principle of Least Privilege)
- 필요한 최소한의 포트와 프로토콜만 허용
- 소스 IP 범위를 가능한 한 제한적으로 설정
- 정기적인 보안 그룹 규칙 검토

### 2. 계층별 보안 (Defense in Depth)
- 네트워크 레벨: Network ACLs
- 인스턴스 레벨: Security Groups
- 애플리케이션 레벨: WAF, 암호화
- 데이터 레벨: 암호화, 백업

### 3. 모니터링 및 로깅
- VPC Flow Logs 활성화
- CloudTrail API 호출 기록
- GuardDuty 위협 탐지
- Config 컴플라이언스 모니터링

### 4. 자동화된 보안 대응
- Lambda 함수를 통한 자동 차단
- Systems Manager를 통한 패치 관리
- AWS Security Hub 중앙 집중 보안 관리

## 🎓 핵심 학습 포인트

1. **다층 보안**: Network ACLs + Security Groups 조합
2. **Stateful vs Stateless**: 각각의 특성을 이해하고 적절히 활용
3. **최소 권한**: 필요한 최소한의 접근만 허용
4. **모니터링**: 보안 이벤트 실시간 감지 및 대응
5. **자동화**: 수동 설정 오류를 줄이기 위한 Infrastructure as Code

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 VPC 보안 설계 문제의 전형적인 예시입니다. 실제 기업 환경에서는 이런 다층 보안 아키텍처가 필수적이며, 각 보안 도구의 특성을 정확히 이해하는 것이 중요합니다.

보안 설계 시 고려해야 할 핵심 원칙:

1. **네트워크 세분화**: 각 계층별로 별도 서브넷 구성
2. **접근 제어**: Security Groups와 NACLs 이중 보안
3. **최소 노출**: 필요한 포트와 프로토콜만 허용
4. **지속적 모니터링**: 실시간 위협 탐지 및 대응
5. **컴플라이언스**: 보안 정책 준수 자동 확인

다음 포스트에서는 AWS의 데이터베이스 서비스들(RDS, DynamoDB, ElastiCache)을 활용한 성능 최적화 문제를 다뤄보겠습니다. 데이터베이스 선택 기준과 성능 튜닝 전략에 대해 자세히 알아보겠습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})

**태그**: #AWS #SAA #Security #VPC #Network-ACL #Security-Groups #다층보안 #네트워크보안
