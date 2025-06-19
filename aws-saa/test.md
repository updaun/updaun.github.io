---
layout: post
title: "AWS IAM(Identity and Access Management) 소개"
date: 2025-06-19
categories: aws-saa
author: updaun
---

# AWS IAM(Identity and Access Management) 소개

AWS IAM(Identity and Access Management)은 AWS 리소스에 대한 액세스를 안전하게 제어할 수 있는 웹 서비스입니다. IAM을 사용하면 누가 인증(로그인)되고 권한을 부여(권한 있음)받아 리소스를 사용할 수 있는지 제어할 수 있습니다.

## IAM의 주요 구성 요소

### 1. 사용자(User)
- AWS 서비스와 상호 작용하는 개인 또는 애플리케이션
- 각 사용자는 고유한 보안 자격 증명을 가짐
- 장기 자격 증명(액세스 키, 비밀 키)을 사용

### 2. 그룹(Group)
- IAM 사용자의 컬렉션
- 그룹에 정책을 적용하면 그룹의 모든 사용자에게 적용됨
- 사용자 권한 관리 단순화

### 3. 역할(Role)
- 특정 권한을 가진 IAM 자격 증명
- 사용자와 유사하지만 특정 사용자에게 할당되지 않음
- 임시 자격 증명 사용

### 4. 정책(Policy)
- JSON 형식의 문서
- 자격 증명이나 리소스와 연결하여 권한을 정의
- AWS 리소스에 대한 액세스 제어 방법을 명시

## IAM 사용의 모범 사례

1. **루트 사용자 보호**
   - 루트 계정에 MFA(다중 인증) 활성화
   - 일상적인 작업에 루트 계정 사용 자제

2. **최소 권한 원칙**
   - 필요한 권한만 부여
   - 과도한 권한 부여 지양

3. **그룹 활용**
   - 사용자를 그룹에 배치하고 그룹에 권한 할당
   - 권한 관리 효율성 증대

4. **IAM 역할 사용**
   - EC2 인스턴스나 Lambda 함수에 권한 부여 시 역할 사용
   - 액세스 키 직접 관리 필요 없음

5. **정기적인 자격 증명 교체**
   - 액세스 키 주기적 변경
   - 미사용 자격 증명 및 권한 제거

## IAM의 글로벌 특성

IAM은 글로벌 서비스로, 특정 리전에 국한되지 않습니다. 이는 사용자가 어떤 리전에서든 동일한 IAM 사용자, 그룹, 역할 및 정책을 사용할 수 있음을 의미합니다.

## 정책 문서 예시

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example-bucket"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::example-bucket/*"
    }
  ]
}
```

위 정책은 'example-bucket'이라는 S3 버킷의 내용을 나열하고, 객체를 가져오고 업로드할 수 있는 권한을 부여합니다.

## 마치며

AWS IAM은 AWS 환경에서 보안의 핵심 요소입니다. 적절한 IAM 정책과 사용자 관리를 통해 AWS 리소스에 대한 액세스를 안전하게 제어할 수 있습니다. 다음 포스트에서는 IAM 정책 작성과 권한 관리에 대해 더 자세히 알아보겠습니다.