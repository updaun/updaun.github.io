---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - API Gateway와 Lambda 기반 마이크로서비스 아키텍처"
date: 2025-07-11
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - API Gateway와 Lambda 기반 마이크로서비스 아키텍처

AWS Solutions Architect Associate(SAA) 시험에서 최근 중요도가 높아지고 있는 서버리스 마이크로서비스 아키텍처 문제를 실전처럼 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 API Gateway, Lambda, DynamoDB, SQS 등을 활용한 확장 가능한 마이크로서비스 설계 문제를 다룹니다.

## 📝 실전 문제

**문제**: 한 온라인 쇼핑몰 회사가 기존 모놀리식 애플리케이션을 마이크로서비스로 전환하려고 합니다. 다음과 같은 요구사항이 있습니다:

- **높은 확장성**: 트래픽 급증 시 자동으로 확장되어야 함
- **비용 효율성**: 사용량에 따른 종량제 요금 체계 필요
- **고가용성**: 99.9% 이상의 가용성 보장
- **보안**: API 인증 및 권한 관리가 필요
- **빠른 응답**: 평균 응답 시간 500ms 이하
- **비동기 처리**: 주문 처리와 알림 발송은 비동기로 처리

다음 중 이 요구사항을 가장 잘 만족하는 아키텍처는?

**A)** Application Load Balancer + EC2 Auto Scaling + RDS Multi-AZ + ElastiCache

**B)** API Gateway + Lambda + DynamoDB + SQS + SNS + CloudWatch

**C)** CloudFront + EC2 + Aurora Serverless + EventBridge + Step Functions

**D)** Elastic Beanstalk + RDS Read Replicas + SQS + CloudFormation

## 🎯 정답 및 해설

### 정답: B

**API Gateway + Lambda + DynamoDB + SQS + SNS + CloudWatch**

### 상세 분석

#### 1. 각 옵션별 요구사항 충족도 분석

| 요구사항 | A (ALB+EC2) | B (API Gateway) | C (CloudFront) | D (Beanstalk) |
|----------|-------------|-----------------|----------------|---------------|
| 확장성 | ⚠️ 제한적 | ✅ 완전 자동 | ⚠️ 제한적 | ⚠️ 제한적 |
| 비용 효율성 | ❌ 고정 비용 | ✅ 종량제 | ❌ 고정 비용 | ❌ 고정 비용 |
| 고가용성 | ✅ Multi-AZ | ✅ 관리형 | ✅ Multi-AZ | ✅ Multi-AZ |
| 보안 | ⚠️ 직접 구현 | ✅ 내장 기능 | ⚠️ 직접 구현 | ⚠️ 직접 구현 |
| 응답 시간 | ⚠️ 가변적 | ✅ 콜드 스타트 | ✅ 캐싱 | ⚠️ 가변적 |
| 비동기 처리 | ❌ 추가 구현 | ✅ SQS/SNS | ⚠️ 복잡 | ⚠️ 복잡 |

#### 2. 권장 솔루션 아키텍처

```
Internet
    ↓
CloudFront (선택적)
    ↓
API Gateway
    ├── Lambda (인증/권한)
    ├── Lambda (상품 서비스)
    ├── Lambda (사용자 서비스)
    ├── Lambda (주문 서비스)
    └── Lambda (결제 서비스)
    ↓
DynamoDB (각 서비스별 테이블)
    ↓
SQS (비동기 작업 큐)
    ↓
Lambda (알림 처리)
    ↓
SNS (알림 발송)
```

#### 3. 세부 구성 요소별 분석

**🔐 API Gateway**
- **인증/권한**: Cognito User Pool, Lambda Authorizer
- **속도 제한**: 요청률 제한으로 DDoS 방어
- **캐싱**: 응답 캐싱으로 성능 향상
- **모니터링**: CloudWatch 통합 메트릭

**⚡ Lambda 함수**
- **자동 확장**: 동시 실행 수 자동 조정
- **비용 효율**: 실행 시간만 과금
- **고가용성**: 다중 AZ 자동 배포
- **성능 최적화**: 적절한 메모리/시간 제한 설정

**🗃️ DynamoDB**
- **무제한 확장**: 자동 파티셔닝
- **일관된 성능**: 예측 가능한 응답 시간
- **글로벌 테이블**: 다중 리전 복제
- **백업/복원**: 자동 백업 및 PITR

**📡 SQS & SNS**
- **비동기 처리**: 주문 처리 워크플로우
- **메시지 신뢰성**: 최소 한 번 전달 보장
- **확장성**: 무제한 메시지 처리
- **데드레터 큐**: 실패 메시지 관리

## 🏗️ 완성된 마이크로서비스 아키텍처

### 1. API 게이트웨이 설계

```yaml
# API Gateway OpenAPI 3.0 스펙
openapi: 3.0.0
info:
  title: E-commerce Microservices API
  version: 1.0.0
  
paths:
  /products:
    get:
      summary: 상품 목록 조회
      security:
        - CognitoAuth: []
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ProductServiceFunction.Arn}/invocations'
        
  /orders:
    post:
      summary: 주문 생성
      security:
        - CognitoAuth: []
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${OrderServiceFunction.Arn}/invocations'

securityDefinitions:
  CognitoAuth:
    type: apiKey
    name: Authorization
    in: header
    x-amazon-apigateway-authtype: cognito_user_pools
    x-amazon-apigateway-authorizer:
      type: cognito_user_pools
      providerARNs:
        - !GetAtt CognitoUserPool.Arn
```

### 2. Lambda 함수 구성

```python
# 주문 서비스 Lambda 함수
import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    try:
        # 요청 데이터 파싱
        body = json.loads(event['body'])
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # 주문 정보 저장
        order_id = str(uuid.uuid4())
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'items': body['items'],
            'total_amount': body['total_amount'],
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # DynamoDB에 주문 저장
        table = dynamodb.Table('Orders')
        table.put_item(Item=order_data)
        
        # SQS로 비동기 처리 요청
        queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/order-processing-queue'
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'order_id': order_id,
                'action': 'process_payment'
            })
        )
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'order_id': order_id,
                'status': 'created'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 3. DynamoDB 테이블 설계

```yaml
# CloudFormation 템플릿 (DynamoDB 테이블)
Resources:
  ProductsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: Products
      AttributeDefinitions:
        - AttributeName: product_id
          AttributeType: S
        - AttributeName: category
          AttributeType: S
      KeySchema:
        - AttributeName: product_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: CategoryIndex
          KeySchema:
            - AttributeName: category
              KeyType: HASH
          Projection:
            ProjectionType: ALL
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
      BillingMode: PAY_PER_REQUEST
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
        
  OrdersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: Orders
      AttributeDefinitions:
        - AttributeName: order_id
          AttributeType: S
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: created_at
          AttributeType: S
      KeySchema:
        - AttributeName: order_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: UserOrdersIndex
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
            - AttributeName: created_at
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      BillingMode: PAY_PER_REQUEST
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
```

### 4. 비동기 처리 워크플로우

```python
# SQS 메시지 처리 Lambda 함수
import json
import boto3

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    for record in event['Records']:
        try:
            # SQS 메시지 처리
            message = json.loads(record['body'])
            order_id = message['order_id']
            action = message['action']
            
            if action == 'process_payment':
                # 결제 처리 로직
                process_payment(order_id)
                
                # 주문 상태 업데이트
                update_order_status(order_id, 'payment_processed')
                
                # 알림 발송
                send_notification(order_id, 'payment_confirmed')
                
        except Exception as e:
            # 에러 처리 및 DLQ로 메시지 이동
            print(f"Error processing message: {str(e)}")
            raise

def process_payment(order_id):
    # 결제 처리 로직 구현
    # 외부 결제 API 호출 등
    pass

def update_order_status(order_id, status):
    table = dynamodb.Table('Orders')
    table.update_item(
        Key={'order_id': order_id},
        UpdateExpression='SET #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': status}
    )

def send_notification(order_id, message_type):
    # SNS를 통한 알림 발송
    topic_arn = 'arn:aws:sns:us-east-1:123456789012:order-notifications'
    sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps({
            'order_id': order_id,
            'message_type': message_type
        })
    )
```

## 🚀 성능 최적화 전략

### 1. Lambda 콜드 스타트 최적화

```python
# 전역 변수를 활용한 연결 재사용
import boto3
import json

# 전역 변수로 클라이언트 초기화
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Products')

def lambda_handler(event, context):
    # 매 요청마다 클라이언트를 새로 생성하지 않음
    response = table.get_item(
        Key={'product_id': event['pathParameters']['id']}
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(response.get('Item', {}))
    }
```

### 2. DynamoDB 성능 최적화

```yaml
# DynamoDB 자동 확장 설정
Resources:
  ProductsTableReadCapacityScalableTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      MaxCapacity: 1000
      MinCapacity: 5
      ResourceId: !Sub 'table/${ProductsTable}'
      RoleARN: !GetAtt DynamoDBAutoscalingRole.Arn
      ScalableDimension: dynamodb:table:ReadCapacityUnits
      ServiceNamespace: dynamodb
      
  ProductsTableReadScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: ReadAutoScalingPolicy
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ProductsTableReadCapacityScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        TargetValue: 70.0
        ScaleInCooldown: 60
        ScaleOutCooldown: 60
        PredefinedMetricSpecification:
          PredefinedMetricType: DynamoDBReadCapacityUtilization
```

### 3. API Gateway 캐싱 설정

```yaml
# API Gateway 캐싱 설정
Resources:
  ApiGatewayMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ApiGatewayRestApi
      ResourceId: !Ref ApiGatewayResource
      HttpMethod: GET
      AuthorizationType: COGNITO_USER_POOLS
      AuthorizerId: !Ref ApiGatewayAuthorizer
      RequestParameters:
        method.request.querystring.category: false
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ProductServiceFunction.Arn}/invocations'
        CacheKeyParameters:
          - method.request.querystring.category
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Cache-Control: false
      RequestValidatorId: !Ref ApiGatewayRequestValidator
  
  ApiGatewayStage:
    Type: AWS::ApiGateway::Stage
    Properties:
      RestApiId: !Ref ApiGatewayRestApi
      DeploymentId: !Ref ApiGatewayDeployment
      StageName: prod
      CacheClusterEnabled: true
      CacheClusterSize: 0.5
      CacheTtlInSeconds: 300
      CachingEnabled: true
      CacheKeyParameters:
        - method.request.querystring.category
```

## 🔒 보안 구현

### 1. Cognito 사용자 인증

```yaml
# Cognito User Pool 설정
Resources:
  CognitoUserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: EcommerceMicroservices
      AutoVerifiedAttributes:
        - email
      Policies:
        PasswordPolicy:
          MinimumLength: 8
          RequireUppercase: true
          RequireLowercase: true
          RequireNumbers: true
          RequireSymbols: true
      MfaConfiguration: OPTIONAL
      EnabledMfas:
        - SOFTWARE_TOKEN_MFA
      Schema:
        - Name: email
          AttributeDataType: String
          Required: true
          Mutable: true
        - Name: given_name
          AttributeDataType: String
          Required: true
          Mutable: true
        - Name: family_name
          AttributeDataType: String
          Required: true
          Mutable: true
          
  CognitoUserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      ClientName: EcommerceMicroservicesClient
      UserPoolId: !Ref CognitoUserPool
      GenerateSecret: false
      ExplicitAuthFlows:
        - ALLOW_USER_PASSWORD_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH
      ReadAttributes:
        - email
        - given_name
        - family_name
      WriteAttributes:
        - email
        - given_name
        - family_name
```

### 2. Lambda 함수 권한 관리

```yaml
# Lambda 실행 역할
Resources:
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: DynamoDBAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:Query
                  - dynamodb:Scan
                Resource: 
                  - !GetAtt ProductsTable.Arn
                  - !GetAtt OrdersTable.Arn
                  - !Sub '${ProductsTable.Arn}/index/*'
                  - !Sub '${OrdersTable.Arn}/index/*'
        - PolicyName: SQSAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - sqs:SendMessage
                  - sqs:ReceiveMessage
                  - sqs:DeleteMessage
                  - sqs:GetQueueAttributes
                Resource: 
                  - !GetAtt OrderProcessingQueue.Arn
                  - !GetAtt NotificationQueue.Arn
        - PolicyName: SNSAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - sns:Publish
                Resource: 
                  - !Ref OrderNotificationTopic
```

## 📊 모니터링 및 운영

### 1. CloudWatch 대시보드

```yaml
# CloudWatch 대시보드
Resources:
  MicroservicesDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: EcommerceMicroservices
      DashboardBody: !Sub |
        {
          "widgets": [
            {
              "type": "metric",
              "properties": {
                "metrics": [
                  ["AWS/ApiGateway", "Count", "ApiName", "${ApiGatewayRestApi}"],
                  ["AWS/ApiGateway", "Latency", "ApiName", "${ApiGatewayRestApi}"],
                  ["AWS/ApiGateway", "4XXError", "ApiName", "${ApiGatewayRestApi}"],
                  ["AWS/ApiGateway", "5XXError", "ApiName", "${ApiGatewayRestApi}"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "${AWS::Region}",
                "title": "API Gateway Metrics"
              }
            },
            {
              "type": "metric",
              "properties": {
                "metrics": [
                  ["AWS/Lambda", "Invocations", "FunctionName", "${ProductServiceFunction}"],
                  ["AWS/Lambda", "Duration", "FunctionName", "${ProductServiceFunction}"],
                  ["AWS/Lambda", "Errors", "FunctionName", "${ProductServiceFunction}"],
                  ["AWS/Lambda", "Throttles", "FunctionName", "${ProductServiceFunction}"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "${AWS::Region}",
                "title": "Lambda Metrics"
              }
            },
            {
              "type": "metric",
              "properties": {
                "metrics": [
                  ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${ProductsTable}"],
                  ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "${ProductsTable}"],
                  ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "${ProductsTable}", "Operation", "GetItem"],
                  ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "${ProductsTable}", "Operation", "PutItem"]
                ],
                "period": 300,
                "stat": "Average",
                "region": "${AWS::Region}",
                "title": "DynamoDB Metrics"
              }
            }
          ]
        }
```

### 2. CloudWatch 알람 설정

```yaml
# CloudWatch 알람
Resources:
  APIGatewayLatencyAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmDescription: API Gateway high latency
      MetricName: Latency
      Namespace: AWS/ApiGateway
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 1000
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: ApiName
          Value: !Ref ApiGatewayRestApi
      AlarmActions:
        - !Ref SNSAlarmTopic
        
  LambdaErrorAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmDescription: Lambda function errors
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: FunctionName
          Value: !Ref ProductServiceFunction
      AlarmActions:
        - !Ref SNSAlarmTopic
        
  DynamoDBThrottleAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmDescription: DynamoDB throttling
      MetricName: ThrottledRequests
      Namespace: AWS/DynamoDB
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
      Dimensions:
        - Name: TableName
          Value: !Ref ProductsTable
      AlarmActions:
        - !Ref SNSAlarmTopic
```

### 3. X-Ray 분산 추적

```python
# X-Ray 추적 설정
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# AWS 서비스 자동 패치
patch_all()

@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    
    @xray_recorder.capture('validate_input')
    def validate_input(data):
        # 입력 검증 로직
        pass
    
    @xray_recorder.capture('process_order')
    def process_order(order_data):
        # 주문 처리 로직
        pass
    
    @xray_recorder.capture('send_notification')
    def send_notification(order_id):
        # 알림 발송 로직
        pass
    
    try:
        body = json.loads(event['body'])
        validate_input(body)
        
        result = process_order(body)
        send_notification(result['order_id'])
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        xray_recorder.current_subsegment().add_exception(e)
        raise
```

## 💰 비용 최적화

### 1. Lambda 함수 메모리 최적화

```python
# Lambda 성능 테스트 및 최적화
import time
import boto3

def test_memory_performance():
    """
    다양한 메모리 설정에서 성능 테스트
    128MB: 평균 500ms, 비용 $0.0000166667
    256MB: 평균 250ms, 비용 $0.0000333333
    512MB: 평균 150ms, 비용 $0.0000666667
    
    최적점: 256MB (성능 대비 비용 효율성 고려)
    """
    pass

def optimize_lambda_configuration():
    """
    Lambda 함수 설정 최적화
    - 메모리: 256MB
    - 타임아웃: 30초
    - 프로비저닝된 동시성: 필요 시에만 사용
    """
    pass
```

### 2. DynamoDB 비용 최적화

```yaml
# DynamoDB 비용 최적화 설정
Resources:
  ProductsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: Products
      BillingMode: PAY_PER_REQUEST  # 온디맨드 요금제
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true  # TTL로 자동 삭제
      Tags:
        - Key: Environment
          Value: Production
        - Key: CostCenter
          Value: Ecommerce
```

### 3. API Gateway 비용 최적화

```yaml
# API Gateway 비용 최적화
Resources:
  ApiGatewayRestApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: EcommerceMicroservices
      Description: Cost-optimized API Gateway
      EndpointConfiguration:
        Types:
          - REGIONAL  # EDGE 대신 REGIONAL 사용
      Policy: !Sub |
        {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": "*",
              "Action": "execute-api:Invoke",
              "Resource": "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:*/*/GET/*"
            }
          ]
        }
```

## ❌ 다른 선택지가 부적절한 이유

### A) ALB + EC2 + RDS + ElastiCache
- **확장성 제한**: EC2 기반으로 완전 자동 확장 어려움
- **비용 비효율**: 고정 인스턴스 비용으로 사용량 기반 과금 불가
- **운영 복잡성**: 인프라 관리 부담 증가
- **응답 시간**: 인스턴스 부팅 시간으로 인한 지연

### C) CloudFront + EC2 + Aurora + EventBridge
- **서버리스 미적용**: EC2 기반으로 완전 서버리스 아님
- **비용 고정**: Aurora 최소 비용 발생
- **복잡성**: Step Functions 추가 복잡성
- **관리 부담**: 인프라 관리 필요

### D) Beanstalk + RDS + SQS + CloudFormation
- **플랫폼 종속**: Beanstalk 플랫폼 제약
- **확장성 제한**: 제한적인 자동 확장
- **비용 비효율**: 고정 인스턴스 비용
- **유연성 부족**: 마이크로서비스 아키텍처 구현 제약

## 🎓 핵심 학습 포인트

1. **서버리스 우선**: Lambda, API Gateway, DynamoDB 조합
2. **완전 관리형**: 인프라 관리 부담 최소화
3. **종량제 과금**: 사용량 기반 비용 구조
4. **자동 확장**: 트래픽에 따른 자동 스케일링
5. **비동기 처리**: SQS/SNS를 통한 디커플링
6. **모니터링**: CloudWatch, X-Ray 통합 운영

## 💡 실전 팁

### 1. 콜드 스타트 최소화
```python
# 연결 풀링 및 재사용
connection_pool = {}

def get_connection(service_name):
    if service_name not in connection_pool:
        connection_pool[service_name] = boto3.client(service_name)
    return connection_pool[service_name]
```

### 2. 에러 처리 패턴
```python
def robust_lambda_handler(event, context):
    try:
        # 비즈니스 로직
        return process_request(event)
    except ValidationError as e:
        return error_response(400, str(e))
    except AuthenticationError as e:
        return error_response(401, str(e))
    except Exception as e:
        # 로깅 및 알림
        logger.error(f"Unexpected error: {str(e)}")
        return error_response(500, "Internal server error")
```

### 3. 성능 모니터링
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        # CloudWatch 메트릭 전송
        cloudwatch.put_metric_data(
            Namespace='EcommerceMicroservices',
            MetricData=[
                {
                    'MetricName': 'FunctionDuration',
                    'Value': duration,
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': func.__name__
                        }
                    ]
                }
            ]
        )
        
        return result
    return wrapper
```

## 📚 추가 학습 자료

### 공식 문서
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/)
- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/)

### 실습 과제
1. **기본 API 구축**: SAM으로 CRUD API 생성
2. **인증 통합**: Cognito User Pool 연동
3. **모니터링 구성**: CloudWatch 대시보드 설정
4. **부하 테스트**: Artillery.js로 성능 측정

### 참고 아키텍처
- [AWS Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/)
- [Microservices on AWS](https://aws.amazon.com/microservices/)
- [Event-Driven Architecture](https://aws.amazon.com/event-driven-architecture/)

## 💭 마무리

이 문제는 AWS SAA 시험에서 점점 중요해지고 있는 **서버리스 마이크로서비스 아키텍처** 설계를 다룹니다. 모던 애플리케이션의 핵심 요구사항인 확장성, 비용 효율성, 운영 편의성을 모두 고려한 종합적인 설계 능력을 평가합니다.

실제 시험에서는 다음과 같은 접근 방식을 추천합니다:

1. **요구사항 우선순위**: 확장성 > 비용 > 성능 > 운영
2. **서버리스 우선**: 관리 부담 최소화
3. **완전 관리형**: AWS 관리형 서비스 활용
4. **모니터링**: CloudWatch 통합 고려

다음 포스트에서는 **AWS 멀티 리전 아키텍처와 글로벌 확장 전략**에 대한 실전 문제를 다뤄보겠습니다. 🚀

---

**관련 포스트:**
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 서버리스 이벤트 기반 아키텍처]({% post_url 2025-06-25-aws-saa-serverless-event-driven-architecture %})
- [AWS SAA 서버리스 API 아키텍처 설계]({% post_url 2025-07-07-aws-saa-serverless-api-architecture-design %})

**태그**: #AWS #SAA #API-Gateway #Lambda #DynamoDB #마이크로서비스 #서버리스 #아키텍처설계
