---
layout: post
title: "AWS SAA 실습 문제: Lambda와 API Gateway를 활용한 서버리스 API 아키텍처 설계"
categories: [aws-saa]
tags: [aws, lambda, api-gateway, serverless, dynamodb, cognito, cloudfront]
date: 2025-07-07
---

## 📋 문제 시나리오

당신은 한 스타트업의 클라우드 아키텍트로 근무하고 있습니다. 회사에서 새로운 모바일 앱을 위한 백엔드 API를 구축하려고 합니다. 다음 요구사항을 만족하는 서버리스 아키텍처를 설계해야 합니다:

### 비즈니스 요구사항
- **사용자 관리**: 회원가입, 로그인, 프로필 관리
- **데이터 저장**: 사용자 프로필과 앱 데이터를 NoSQL 데이터베이스에 저장
- **API 엔드포인트**: RESTful API 제공
- **인증/인가**: 안전한 사용자 인증 시스템
- **글로벌 배포**: 전 세계 사용자를 위한 빠른 응답 시간
- **비용 최적화**: 사용량 기반 과금으로 초기 비용 최소화

### 기술적 요구사항
- 서버리스 아키텍처 사용
- 99.9% 가용성 보장
- 자동 스케일링
- 보안 모범 사례 적용
- 모니터링 및 로깅

## 🎯 예상 답안

### 1. 아키텍처 구성요소

```
[Mobile App] 
    ↓
[CloudFront] 
    ↓
[API Gateway] 
    ↓
[Lambda Authorizer] ← [Cognito User Pool]
    ↓
[Lambda Functions]
    ↓
[DynamoDB] + [S3] + [CloudWatch]
```

### 2. 상세 설계

#### A. 인증 및 인가 계층
```yaml
Amazon Cognito User Pool:
  - 사용자 등록/로그인 관리
  - JWT 토큰 발급
  - MFA 지원
  - 사용자 속성 관리

Lambda Authorizer:
  - JWT 토큰 검증
  - 사용자 권한 확인
  - API Gateway와 통합
```

#### B. API 계층
```yaml
API Gateway (REST API):
  Endpoints:
    - POST /auth/signup
    - POST /auth/signin  
    - GET /user/profile
    - PUT /user/profile
    - GET /data/{userId}
    - POST /data
    
  Features:
    - Request/Response 변환
    - 요청 검증
    - Rate Limiting
    - CORS 설정
    - CloudWatch 로깅
```

#### C. 비즈니스 로직 계층
```python
# Lambda Function 예제 - 사용자 프로필 조회
import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('UserProfiles')

def lambda_handler(event, context):
    try:
        # JWT에서 사용자 ID 추출
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # DynamoDB에서 사용자 프로필 조회
        response = table.get_item(
            Key={'userId': user_id}
        )
        
        if 'Item' in response:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response['Item'])
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'User profile not found'})
            }
            
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### D. 데이터 계층
```yaml
DynamoDB Tables:
  UserProfiles:
    - Partition Key: userId (String)
    - Attributes: email, name, createdAt, updatedAt
    - GSI: email-index
    
  AppData:
    - Partition Key: userId (String)  
    - Sort Key: dataId (String)
    - Attributes: content, timestamp, category
    - LSI: timestamp-index

S3 Buckets:
  user-profile-images:
    - 사용자 프로필 이미지 저장
    - CloudFront 연동
    - 적절한 IAM 정책 적용
```

### 3. 보안 구성

#### A. IAM 역할 및 정책
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:region:account:table/UserProfiles",
        "arn:aws:dynamodb:region:account:table/AppData"
      ]
    },
    {
      "Effect": "Allow", 
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

#### B. API Gateway 보안 설정
```yaml
Resource Policy:
  - IP 화이트리스트 (필요시)
  - VPC 엔드포인트 사용 (내부 API용)

Request Validation:
  - JSON 스키마 검증
  - 파라미터 타입 체크
  - 필수 필드 검증

Rate Limiting:
  - 사용자별: 100 요청/분
  - IP별: 1000 요청/분
```

### 4. 모니터링 및 로깅

#### A. CloudWatch 메트릭
```yaml
Lambda 메트릭:
  - Duration (실행 시간)
  - Error Rate (오류율)
  - Invocation Count (호출 횟수)
  - Throttle Count (제한 횟수)

API Gateway 메트릭:
  - Request Count
  - Latency
  - Error Rate (4XX, 5XX)
  - Cache Hit/Miss

DynamoDB 메트릭:
  - Read/Write Capacity
  - Throttled Requests
  - System Errors
```

#### B. 알람 설정
```yaml
Critical Alarms:
  - Lambda Error Rate > 5%
  - API Gateway 5XX Error > 1%
  - DynamoDB Throttling > 0

Warning Alarms:
  - Lambda Duration > 5초
  - API Gateway Latency > 2초
  - DynamoDB Consumed Capacity > 80%
```

## 🚀 배포 및 운영

### 1. Infrastructure as Code
```yaml
# SAM Template 예제
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  # API Gateway
  UserAPI:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn

  # Lambda Functions
  GetUserProfileFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: get_user_profile.lambda_handler
      Runtime: python3.9
      Events:
        GetProfile:
          Type: Api
          Properties:
            RestApiId: !Ref UserAPI
            Path: /user/profile
            Method: get

  # DynamoDB Table
  UserProfilesTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: UserProfiles
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: userId
          AttributeType: S
      KeySchema:
        - AttributeName: userId
          KeyType: HASH
```

### 2. CI/CD 파이프라인
```yaml
# GitHub Actions 예제
name: Deploy Serverless API
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install pytest boto3 moto
          
      - name: Run tests
        run: pytest tests/
        
      - name: Deploy with SAM
        run: |
          sam build
          sam deploy --no-confirm-changeset
```

## 💡 모범 사례 및 최적화

### 1. 성능 최적화
- **Lambda Cold Start 최소화**: Provisioned Concurrency 사용
- **DynamoDB 최적화**: 적절한 파티션 키 설계, DAX 캐싱 고려
- **API Gateway 캐싱**: 자주 요청되는 데이터에 대해 캐싱 활성화

### 2. 비용 최적화
- **Lambda 메모리 최적화**: 적절한 메모리 크기 설정
- **DynamoDB On-Demand**: 예측 불가능한 워크로드에 적합
- **S3 Lifecycle 정책**: 오래된 파일 자동 아카이빙

### 3. 보안 강화
- **WAF 적용**: SQL Injection, XSS 공격 방어
- **VPC Lambda**: 민감한 데이터 처리시 VPC 내 배포
- **Secrets Manager**: 데이터베이스 자격 증명 관리

## 📊 예상 비용 분석

```yaml
월 사용량 기준 (10,000 MAU):
  API Gateway: $3.50/백만 요청
  Lambda: $0.20/백만 요청 + 컴퓨팅 시간
  DynamoDB: $1.25/백만 읽기, $6.25/백만 쓰기
  Cognito: $0.0055/MAU (10,000명 초과분)
  CloudFront: $0.085/GB
  
예상 월 비용: $100-300 (사용량에 따라)
```

## 🔍 문제 해결 가이드

### 일반적인 이슈들
1. **Lambda Timeout**: 복잡한 쿼리는 Step Functions로 분할
2. **DynamoDB Throttling**: Auto Scaling 활성화 또는 파티션 키 재설계
3. **CORS 오류**: API Gateway와 Lambda에서 적절한 헤더 설정
4. **Cold Start 지연**: Provisioned Concurrency 또는 warming 전략 사용

## 💻 실습 과제

1. **기본 구현**: SAM으로 기본 API 구조 구축
2. **인증 추가**: Cognito User Pool과 Lambda Authorizer 구현
3. **모니터링 설정**: CloudWatch 대시보드와 알람 구성
4. **성능 테스트**: Artillery.js로 부하 테스트 수행

이 아키텍처는 AWS SAA 시험에서 자주 출제되는 서버리스 패턴을 실제 비즈니스 요구사항과 연결하여 설계한 것입니다. 각 구성요소의 역할과 상호작용을 이해하고, 보안과 모니터링까지 고려한 완전한 솔루션을 제공합니다.

---

**관련 포스트:**
- [AWS SAA 서버리스 이벤트 기반 아키텍처](../25/aws-saa-serverless-event-driven-architecture)
- [AWS 보안 모범 사례와 사고 대응](../../07/01/aws-security-best-practices-incident-response)
