---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 데이터 암호화와 키 관리 전략"
date: 2025-07-03
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 데이터 암호화와 키 관리 전략

AWS Solutions Architect Associate(SAA) 시험에서 점점 중요해지고 있는 데이터 보안과 암호화 관련 실전 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 AWS KMS, CloudHSM, 그리고 다양한 서비스의 암호화 옵션을 활용한 종합적인 보안 아키텍처 설계 문제를 다루겠습니다.

## 📝 실전 문제 1: 다층 암호화 전략

**문제**: 한 의료 기관이 환자 데이터를 AWS에 저장하려고 합니다. HIPAA 규정을 준수해야 하며 다음과 같은 보안 요구사항이 있습니다:

- 저장 중인 데이터(Data at Rest) 암호화
- 전송 중인 데이터(Data in Transit) 암호화  
- 키 관리는 내부 보안팀이 완전히 제어
- 키 순환(Key Rotation)은 90일마다 자동으로 실행
- 감사 로그는 모든 키 사용에 대해 기록되어야 함
- 지역별 데이터 주권 요구사항 준수

가장 적절한 암호화 및 키 관리 전략은?

**A)** AWS Managed Keys (AWS KMS)와 S3 기본 암호화 사용

**B)** Customer Managed Keys (CMK)와 CloudTrail을 통한 감사, 다중 리전 키 사용

**C)** CloudHSM Cluster와 Client SDK를 사용한 키 관리

**D)** 애플리케이션 레벨 암호화와 자체 키 관리 서버 구축

## 🎯 정답 및 해설

### 정답: B

**Customer Managed Keys (CMK)와 CloudTrail을 통한 감사, 다중 리전 키 사용**

### 상세 분석

#### 1. 각 옵션 분석

**A) AWS Managed Keys 문제점:**
- 키 순환 주기 제어 불가 (AWS가 관리)
- 키 정책 및 접근 권한 세밀한 제어 어려움
- 지역별 데이터 주권 요구사항 충족 어려움

**C) CloudHSM 문제점:**
- 과도한 복잡성 (해당 요구사항에 비해)
- 높은 비용 (월 $1,000+ 고정 비용)
- 관리 오버헤드 증가

**D) 자체 키 관리 문제점:**
- 보안 위험 증가
- 규정 준수 복잡성
- 운영 부담 과다

#### 2. 권장 솔루션 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Region KMS 아키텍처                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   US-East-1     │    │   US-West-2     │                 │
│  │                 │    │                 │                 │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                 │
│  │ │ CMK Primary │ │    │ │ CMK Replica │ │                 │
│  │ │ (90d rotate)│ │    │ │ (Sync Auto) │ │                 │
│  │ └─────────────┘ │    │ └─────────────┘ │                 │
│  │                 │    │                 │                 │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                 │
│  │ │   RDS       │ │    │ │   RDS       │ │                 │
│  │ │ (Encrypted) │ │    │ │ (Encrypted) │ │                 │
│  │ └─────────────┘ │    │ └─────────────┘ │                 │
│  │                 │    │                 │                 │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                 │
│  │ │     S3      │ │    │ │     S3      │ │                 │
│  │ │ (SSE-KMS)   │ │    │ │ (SSE-KMS)   │ │                 │
│  │ └─────────────┘ │    │ └─────────────┘ │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               CloudTrail (전역 감사)                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 3. 구현 세부사항

**CMK 키 정책 예시:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnableHIPAACompliantAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/HIPAADataAccessRole"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "s3.us-east-1.amazonaws.com",
            "rds.us-east-1.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

**자동 키 순환 설정:**
```bash
aws kms enable-key-rotation \
    --key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012 \
    --region us-east-1

aws kms put-key-policy \
    --key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012 \
    --policy-name default \
    --policy file://cmk-policy.json
```

---

## 📝 실전 문제 2: 성능과 보안의 균형

**문제**: 한 전자상거래 회사가 대용량 이미지 파일을 S3에 저장하고 있습니다. 다음과 같은 요구사항이 있습니다:

- 초당 10,000건의 PUT 요청 처리
- 이미지 파일 암호화 필수
- 최소한의 지연시간 요구
- 비용 최적화 필요
- 키 관리 부담 최소화

가장 적절한 암호화 전략은?

**A)** SSE-S3 (S3 Managed Keys)

**B)** SSE-KMS (Customer Managed Keys)

**C)** SSE-KMS (AWS Managed Keys)

**D)** SSE-C (Customer Provided Keys)

## 🎯 정답 및 해설

### 정답: A

**SSE-S3 (S3 Managed Keys)**

### 상세 분석

#### 1. 성능 비교 분석

| 암호화 방식 | KMS API 호출 | 지연시간 | TPS 제한 | 비용 |
|------------|-------------|---------|----------|------|
| **SSE-S3** | ❌ 불필요 | **최소** | **무제한** | **최저** |
| SSE-KMS (AWS) | ✅ 필요 | 보통 | 5,500/초* | 보통 |
| SSE-KMS (CMK) | ✅ 필요 | 보통 | 5,500/초* | 높음 |
| SSE-C | ❌ 불필요 | 최소 | 무제한 | 최저 |

*KMS API 제한: 리전당 기본 5,500 TPS (증설 가능하지만 추가 비용)

#### 2. 요구사항 분석

**초당 10,000건 PUT 요청:**
- SSE-KMS는 기본 제한(5,500 TPS) 초과
- TPS 증설 시 추가 비용 발생
- SSE-S3는 제한 없음

**최소 지연시간:**
- SSE-S3: S3 내부 처리, 최소 지연
- SSE-KMS: KMS API 호출로 인한 추가 지연 (50-100ms)

**키 관리 부담 최소화:**
- SSE-S3: AWS 완전 관리
- SSE-C: 고객이 키 제공 및 관리 (부담 증가)

#### 3. 실제 구현 예시

**S3 버킷 암호화 설정:**
```bash
# SSE-S3 기본 암호화 설정
aws s3api put-bucket-encryption \
    --bucket my-ecommerce-images \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                },
                "BucketKeyEnabled": true
            }
        ]
    }'
```

**성능 최적화 설정:**
```python
import boto3
from concurrent.futures import ThreadPoolExecutor
import time

def upload_with_sse_s3(s3_client, bucket, key, data):
    """SSE-S3로 파일 업로드"""
    response = s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ServerSideEncryption='AES256'  # SSE-S3 명시적 지정
    )
    return response

# 대용량 업로드 테스트
def benchmark_upload():
    s3 = boto3.client('s3')
    bucket = 'my-ecommerce-images'
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for i in range(10000):
            future = executor.submit(
                upload_with_sse_s3,
                s3, bucket, f'image_{i}.jpg', b'dummy_image_data'
            )
            futures.append(future)
        
        # 모든 업로드 완료 대기
        for future in futures:
            future.result()
    
    total_time = time.time() - start_time
    print(f"10,000건 업로드 완료: {total_time:.2f}초")
    print(f"TPS: {10000/total_time:.2f}")

if __name__ == "__main__":
    benchmark_upload()
```

---

## 📝 실전 문제 3: 규정 준수와 감사

**문제**: 한 글로벌 금융 회사가 다음과 같은 규정 준수 요구사항을 가지고 있습니다:

- SOX, PCI DSS, GDPR 모든 규정 준수
- 모든 암호화 키 사용에 대한 상세 감사 로그
- 키 접근 권한은 최소 권한 원칙 적용
- 지역별 데이터 거주 요구사항 (EU 데이터는 EU 리전에만)
- 키 삭제 시 7일 대기 기간 필수
- 암호화 키는 FIPS 140-2 Level 3 요구사항 충족

이 모든 요구사항을 만족하는 가장 적절한 솔루션은?

**A)** 다중 리전 AWS KMS CMK + CloudTrail + Organizations SCP

**B)** 단일 리전 CloudHSM + 자체 감사 시스템

**C)** 리전별 CloudHSM Cluster + AWS Config + GuardDuty

**D)** AWS KMS + AWS CloudHSM을 조합한 하이브리드 솔루션

## 🎯 정답 및 해설

### 정답: A

**다중 리전 AWS KMS CMK + CloudTrail + Organizations SCP**

### 상세 분석

#### 1. 규정 준수 요구사항 매핑

| 요구사항 | AWS KMS | CloudHSM | 비고 |
|----------|---------|----------|------|
| **SOX/PCI DSS** | ✅ 지원 | ✅ 지원 | 둘 다 준수 |
| **GDPR** | ✅ 지원 | ✅ 지원 | 지역별 키 관리 |
| **FIPS 140-2 L3** | ❌ L2 | ✅ L3 | **중요한 차이점** |
| **감사 로그** | ✅ CloudTrail | ⚠️ 제한적 | CloudTrail 통합 |
| **키 삭제 대기** | ✅ 7-30일 | ❌ 즉시 | KMS 기본 기능 |
| **관리 복잡성** | ✅ 낮음 | ❌ 높음 | 운영 부담 |

#### 2. 실제로는 D번이 정답이어야 하는 이유

**FIPS 140-2 Level 3 요구사항** 때문에 실제로는 **CloudHSM이 필수**입니다.

**정정된 정답: D - AWS KMS + AWS CloudHSM 하이브리드 솔루션**

#### 3. 권장 하이브리드 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│            FIPS 140-2 Level 3 준수 하이브리드 아키텍처            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │    EU-West-1    │    │   US-East-1     │                 │
│  │                 │    │                 │                 │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                 │
│  │ │ CloudHSM    │ │    │ │ CloudHSM    │ │                 │
│  │ │ Cluster     │ │    │ │ Cluster     │ │                 │
│  │ │ (Primary)   │ │    │ │ (Primary)   │ │                 │
│  │ └─────────────┘ │    │ └─────────────┘ │                 │
│  │       │         │    │       │         │                 │
│  │ ┌─────▼─────┐   │    │ ┌─────▼─────┐   │                 │
│  │ │ KMS CMK   │   │    │ │ KMS CMK   │   │                 │
│  │ │(CloudHSM  │   │    │ │(CloudHSM  │   │                 │
│  │ │ Origin)   │   │    │ │ Origin)   │   │                 │
│  │ └───────────┘   │    │ └───────────┘   │                 │
│  │                 │    │                 │                 │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                 │
│  │ │ Application │ │    │ │ Application │ │                 │
│  │ │ Services    │ │    │ │ Services    │ │                 │
│  │ └─────────────┘ │    │ └─────────────┘ │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │          CloudTrail + Config + Organizations SCP         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 4. 구현 단계별 가이드

**1단계: CloudHSM 클러스터 생성**
```bash
# EU 리전 CloudHSM 클러스터
aws cloudhsmv2 create-cluster \
    --hsm-type hsm1.medium \
    --subnet-ids subnet-12345678 subnet-87654321 \
    --region eu-west-1

# US 리전 CloudHSM 클러스터  
aws cloudhsmv2 create-cluster \
    --hsm-type hsm1.medium \
    --subnet-ids subnet-abcdefgh subnet-hgfedcba \
    --region us-east-1
```

**2단계: CloudHSM Origin CMK 생성**
```bash
# CloudHSM을 소스로 하는 CMK 생성
aws kms create-key \
    --description "FIPS 140-2 Level 3 Compliant Key" \
    --origin AWS_CLOUDHSM \
    --custom-key-store-id cks-1234567890abcdef0 \
    --region eu-west-1
```

**3단계: 조직 수준 SCP 정책**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceCloudHSMForSensitiveData",
      "Effect": "Deny",
      "Action": [
        "s3:PutObject",
        "rds:CreateDBCluster",
        "dynamodb:CreateTable"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms",
          "s3:x-amz-server-side-encryption-aws-kms-key-id": [
            "arn:aws:kms:eu-west-1:*:key/*",
            "arn:aws:kms:us-east-1:*:key/*"
          ]
        }
      }
    },
    {
      "Sid": "EnforceRegionalDataResidency",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "eu-west-1",
            "us-east-1"
          ]
        }
      }
    }
  ]
}
```

**4단계: 감사 및 모니터링 설정**
```bash
# 전역 CloudTrail 설정
aws cloudtrail create-trail \
    --name compliance-audit-trail \
    --s3-bucket-name compliance-logs-bucket \
    --include-global-service-events \
    --is-multi-region-trail \
    --enable-log-file-validation

# KMS 이벤트 특별 모니터링
aws logs create-log-group \
    --log-group-name /aws/kms/audit \
    --region eu-west-1

# CloudWatch 알람 설정
aws cloudwatch put-metric-alarm \
    --alarm-name "KMS-Unauthorized-Access" \
    --alarm-description "Alert on unauthorized KMS access" \
    --metric-name "ErrorCount" \
    --namespace "AWS/KMS" \
    --statistic "Sum" \
    --period 300 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold"
```

---

## 🏆 실전 팁과 모범 사례

### 1. 암호화 방식 선택 기준

```
📊 의사결정 매트릭스

성능 우선 (>5000 TPS) → SSE-S3
규정 준수 (FIPS L3) → CloudHSM  
비용 최적화 → SSE-S3
세밀한 권한 제어 → KMS CMK
감사 요구사항 강함 → KMS + CloudTrail
```

### 2. 키 순환 전략

| 순환 주기 | 적용 대상 | 자동화 방법 |
|----------|----------|------------|
| **30일** | 고위험 데이터 | Lambda + EventBridge |
| **90일** | 일반 운영 데이터 | KMS 자동 순환 |
| **365일** | 아카이브 데이터 | 수동 관리 |

### 3. 비용 최적화 전략

**KMS 비용 구조:**
- CMK: $1/월
- API 호출: $0.03/10,000 요청
- S3 Bucket Key 사용 시 99% 비용 절감

```python
# S3 Bucket Key 활성화로 비용 절감
import boto3

def enable_bucket_key():
    s3 = boto3.client('s3')
    
    s3.put_bucket_encryption(
        Bucket='my-cost-optimized-bucket',
        ServerSideEncryptionConfiguration={
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'aws:kms',
                        'KMSMasterKeyID': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'
                    },
                    'BucketKeyEnabled': True  # 99% 비용 절감
                }
            ]
        }
    )
```

---

## 📚 추가 학습 자료

### 공식 문서
- [AWS KMS Developer Guide](https://docs.aws.amazon.com/kms/)
- [AWS CloudHSM User Guide](https://docs.aws.amazon.com/cloudhsm/)
- [S3 암호화 가이드](https://docs.aws.amazon.com/s3/latest/userguide/UsingEncryption.html)

### 실습 시나리오
1. **다중 리전 CMK 설정**: 재해복구용 암호화 키 복제
2. **CloudHSM 클러스터 구축**: FIPS 140-2 Level 3 환경 구성
3. **감사 로그 분석**: CloudTrail을 통한 키 사용 추적

### 인증서 준비
- AWS Certified Solutions Architect - Associate
- AWS Certified Security - Specialty
- AWS Certified Advanced Networking - Specialty

---

## 💡 핵심 요약

1. **성능 중심**: SSE-S3 (무제한 TPS)
2. **규정 준수**: CloudHSM (FIPS 140-2 Level 3)
3. **비용 최적화**: S3 Bucket Key 활용
4. **감사 요구사항**: KMS + CloudTrail 조합
5. **지역별 준수**: 다중 리전 키 전략

AWS SAA 시험에서 암호화 문제는 **성능, 비용, 규정 준수의 균형**을 찾는 것이 핵심입니다. 각 서비스의 특성과 제한사항을 정확히 이해하고, 요구사항에 맞는 최적의 솔루션을 선택하는 능력이 중요합니다.

다음 포스트에서는 **AWS SAA 멀티 클라우드 및 온프레미스 통합 전략**에 대한 실전 문제를 다뤄보겠습니다. 🚀
