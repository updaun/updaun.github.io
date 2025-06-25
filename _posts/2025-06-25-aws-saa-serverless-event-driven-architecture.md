---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 서버리스 아키텍처와 이벤트 드리븐 시스템"
date: 2025-06-25
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 서버리스 아키텍처와 이벤트 드리븐 시스템

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 서버리스 아키텍처 설계 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 Lambda, API Gateway, Step Functions를 활용한 이벤트 드리븐 시스템 구축 문제를 다루겠습니다.

## 📝 실전 문제

**문제**: 한 미디어 회사가 동영상 콘텐츠 처리 시스템을 AWS에 구축하려고 합니다. 시스템 요구사항은 다음과 같습니다:

- **동영상 업로드**: 사용자가 웹/모바일에서 동영상 업로드
- **자동 처리 워크플로우**: 업로드 → 인코딩 → 썸네일 생성 → 품질 검사 → 배포
- **비동기 처리**: 긴 처리 시간, 단계별 상태 추적 필요
- **비용 최적화**: 처리 중에만 리소스 사용
- **확장성**: 동시 업로드 수에 따른 자동 확장
- **알림**: 처리 완료 시 사용자에게 이메일/SMS 알림
- **오류 처리**: 실패 시 재시도 및 데드레터 큐 처리

이 요구사항을 만족하는 가장 적절한 서버리스 아키텍처는?

**A)** EC2 Auto Scaling Group + SQS + CloudWatch Events

**B)** Lambda + API Gateway + Step Functions + S3 + SNS + SQS

**C)** ECS Fargate + ALB + RDS + CloudFormation

**D)** Elastic Beanstalk + SWF + SimpleDB + SES

## 🎯 정답 및 해설

### 정답: B

**Lambda + API Gateway + Step Functions + S3 + SNS + SQS**

### 상세 분석

#### 1. 서버리스 아키텍처 구성 요소

| 컴포넌트 | AWS 서비스 | 역할 |
|---------|------------|------|
| **API 엔드포인트** | **API Gateway** | RESTful API, 인증/권한 |
| **비즈니스 로직** | **Lambda** | 이벤트 기반 처리 |
| **워크플로우 관리** | **Step Functions** | 상태 기계, 단계별 처리 |
| **파일 저장소** | **S3** | 동영상/썸네일 저장 |
| **메시징** | **SNS/SQS** | 알림 및 큐잉 |
| **모니터링** | **CloudWatch** | 로그 및 메트릭 |

#### 2. 이벤트 드리븐 워크플로우

```
사용자 업로드 → API Gateway → Lambda (업로드 처리)
                                    ↓
                               Step Functions 시작
                                    ↓
    인코딩 Lambda ← 썸네일 생성 Lambda ← 품질 검사 Lambda
         ↓              ↓                 ↓
    S3 저장        S3 저장           배포 완료
         ↓              ↓                 ↓
                   SNS 알림 발송
```

## 🚀 상세 아키텍처 설계

### 1. API Gateway 설정

#### REST API 구성
```json
{
  "swagger": "2.0",
  "info": {
    "title": "Video Processing API",
    "version": "1.0.0"
  },
  "paths": {
    "/upload": {
      "post": {
        "summary": "동영상 업로드 시작",
        "parameters": [
          {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": true
          }
        ],
        "x-amazon-apigateway-integration": {
          "type": "aws_proxy",
          "httpMethod": "POST",
          "uri": "arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:VideoUploadHandler/invocations"
        }
      }
    },
    "/status/{jobId}": {
      "get": {
        "summary": "처리 상태 조회",
        "parameters": [
          {
            "name": "jobId",
            "in": "path",
            "type": "string",
            "required": true
          }
        ],
        "x-amazon-apigateway-integration": {
          "type": "aws_proxy",
          "httpMethod": "POST",
          "uri": "arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:StatusChecker/invocations"
        }
      }
    }
  }
}
```

#### API Gateway 인증 설정
```json
{
  "securityDefinitions": {
    "CognitoUserPool": {
      "type": "apiKey",
      "name": "Authorization",
      "in": "header",
      "x-amazon-apigateway-authtype": "cognito_user_pools",
      "x-amazon-apigateway-authorizer": {
        "type": "cognito_user_pools",
        "providerARNs": [
          "arn:aws:cognito-idp:region:account:userpool/us-east-1_example"
        ]
      }
    }
  }
}
```

### 2. Lambda 함수 구현

#### 동영상 업로드 핸들러
```python
import json
import boto3
import uuid
from datetime import datetime

def lambda_handler(event, context):
    # S3 및 Step Functions 클라이언트 초기화
    s3 = boto3.client('s3')
    stepfunctions = boto3.client('stepfunctions')
    
    try:
        # 요청 파싱
        body = json.loads(event['body'])
        file_name = body['fileName']
        content_type = body['contentType']
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # 고유 Job ID 생성
        job_id = str(uuid.uuid4())
        
        # S3 Pre-signed URL 생성
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': 'video-processing-bucket',
                'Key': f'uploads/{job_id}/{file_name}',
                'ContentType': content_type
            },
            ExpiresIn=3600
        )
        
        # DynamoDB에 작업 정보 저장
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('VideoProcessingJobs')
        
        table.put_item(
            Item={
                'jobId': job_id,
                'userId': user_id,
                'fileName': file_name,
                'status': 'UPLOAD_PENDING',
                'createdAt': datetime.utcnow().isoformat(),
                'updatedAt': datetime.utcnow().isoformat()
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'jobId': job_id,
                'uploadUrl': presigned_url,
                'message': 'Upload URL generated successfully'
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }
```

#### S3 이벤트 트리거 함수
```python
import json
import boto3

def lambda_handler(event, context):
    stepfunctions = boto3.client('stepfunctions')
    
    for record in event['Records']:
        # S3 이벤트에서 정보 추출
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Job ID 추출 (uploads/{job_id}/{filename} 형태)
        job_id = key.split('/')[1]
        
        # Step Functions 실행 시작
        response = stepfunctions.start_execution(
            stateMachineArn='arn:aws:states:region:account:stateMachine:VideoProcessingWorkflow',
            name=f'execution-{job_id}',
            input=json.dumps({
                'jobId': job_id,
                'inputBucket': bucket,
                'inputKey': key,
                'outputBucket': 'video-processing-output'
            })
        )
        
        print(f"Started Step Functions execution: {response['executionArn']}")
    
    return {'statusCode': 200}
```

### 3. Step Functions 상태 기계

#### 워크플로우 정의
```json
{
  "Comment": "동영상 처리 워크플로우",
  "StartAt": "UpdateStatus",
  "States": {
    "UpdateStatus": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "VideoProcessingJobs",
        "Key": {
          "jobId": {"S.$": "$.jobId"}
        },
        "UpdateExpression": "SET #status = :status, #updatedAt = :updatedAt",
        "ExpressionAttributeNames": {
          "#status": "status",
          "#updatedAt": "updatedAt"
        },
        "ExpressionAttributeValues": {
          ":status": {"S": "PROCESSING"},
          ":updatedAt": {"S.$": "$$.State.EnteredTime"}
        }
      },
      "Next": "ParallelProcessing"
    },
    "ParallelProcessing": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "VideoEncoding",
          "States": {
            "VideoEncoding": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "VideoEncodingFunction",
                "Payload.$": "$"
              },
              "End": true,
              "Retry": [
                {
                  "ErrorEquals": ["States.TaskFailed"],
                  "IntervalSeconds": 30,
                  "MaxAttempts": 3,
                  "BackoffRate": 2.0
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "Next": "EncodingFailed"
                }
              ]
            },
            "EncodingFailed": {
              "Type": "Fail",
              "Cause": "Video encoding failed"
            }
          }
        },
        {
          "StartAt": "ThumbnailGeneration",
          "States": {
            "ThumbnailGeneration": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "ThumbnailGenerationFunction",
                "Payload.$": "$"
              },
              "End": true,
              "Retry": [
                {
                  "ErrorEquals": ["States.TaskFailed"],
                  "IntervalSeconds": 15,
                  "MaxAttempts": 2
                }
              ]
            }
          }
        }
      ],
      "Next": "QualityCheck"
    },
    "QualityCheck": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "QualityCheckFunction",
        "Payload.$": "$"
      },
      "Next": "QualityCheckResult"
    },
    "QualityCheckResult": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.qualityScore",
          "NumericGreaterThan": 80,
          "Next": "PublishContent"
        }
      ],
      "Default": "QualityCheckFailed"
    },
    "PublishContent": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "PublishContentFunction",
        "Payload.$": "$"
      },
      "Next": "SendNotification"
    },
    "SendNotification": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:region:account:video-processing-notifications",
        "Message.$": "$.notificationMessage",
        "Subject": "동영상 처리 완료"
      },
      "Next": "UpdateFinalStatus"
    },
    "UpdateFinalStatus": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "VideoProcessingJobs",
        "Key": {
          "jobId": {"S.$": "$.jobId"}
        },
        "UpdateExpression": "SET #status = :status, #completedAt = :completedAt",
        "ExpressionAttributeNames": {
          "#status": "status",
          "#completedAt": "completedAt"
        },
        "ExpressionAttributeValues": {
          ":status": {"S": "COMPLETED"},
          ":completedAt": {"S.$": "$$.State.EnteredTime"}
        }
      },
      "End": true
    },
    "QualityCheckFailed": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:region:account:video-processing-notifications",
        "Message": "동영상 품질 검사 실패",
        "Subject": "동영상 처리 실패"
      },
      "Next": "UpdateFailedStatus"
    },
    "UpdateFailedStatus": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "VideoProcessingJobs",
        "Key": {
          "jobId": {"S.$": "$.jobId"}
        },
        "UpdateExpression": "SET #status = :status, #failedAt = :failedAt",
        "ExpressionAttributeNames": {
          "#status": "status",
          "#failedAt": "failedAt"
        },
        "ExpressionAttributeValues": {
          ":status": {"S": "FAILED"},
          ":failedAt": {"S.$": "$$.State.EnteredTime"}
        }
      },
      "End": true
    }
  }
}
```

### 4. 개별 처리 Lambda 함수들

#### 동영상 인코딩 함수
```python
import json
import boto3
import subprocess
import os

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    try:
        job_id = event['jobId']
        input_bucket = event['inputBucket']
        input_key = event['inputKey']
        output_bucket = event['outputBucket']
        
        # 입력 파일 다운로드
        local_input = f'/tmp/{job_id}_input.mp4'
        s3.download_file(input_bucket, input_key, local_input)
        
        # FFmpeg를 사용한 인코딩 (Lambda Layer에 포함)
        output_formats = ['720p', '1080p']
        encoded_files = []
        
        for format in output_formats:
            local_output = f'/tmp/{job_id}_{format}.mp4'
            
            # FFmpeg 명령어 실행
            if format == '720p':
                cmd = f'ffmpeg -i {local_input} -vf scale=1280:720 -c:v libx264 -crf 23 {local_output}'
            else:
                cmd = f'ffmpeg -i {local_input} -vf scale=1920:1080 -c:v libx264 -crf 23 {local_output}'
            
            subprocess.run(cmd, shell=True, check=True)
            
            # S3에 업로드
            output_key = f'encoded/{job_id}/{format}.mp4'
            s3.upload_file(local_output, output_bucket, output_key)
            
            encoded_files.append({
                'format': format,
                'key': output_key,
                'size': os.path.getsize(local_output)
            })
            
            # 임시 파일 정리
            os.remove(local_output)
        
        os.remove(local_input)
        
        return {
            'jobId': job_id,
            'encodedFiles': encoded_files,
            'status': 'ENCODING_COMPLETE'
        }
        
    except Exception as e:
        print(f"Encoding error: {str(e)}")
        raise e
```

#### 썸네일 생성 함수
```python
import json
import boto3
import subprocess
import os

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    try:
        job_id = event['jobId']
        input_bucket = event['inputBucket']
        input_key = event['inputKey']
        output_bucket = event['outputBucket']
        
        # 입력 파일 다운로드
        local_input = f'/tmp/{job_id}_input.mp4'
        s3.download_file(input_bucket, input_key, local_input)
        
        # 썸네일 생성 (3개 시점에서)
        timestamps = ['00:00:05', '00:00:15', '00:00:30']
        thumbnails = []
        
        for i, timestamp in enumerate(timestamps):
            local_thumbnail = f'/tmp/{job_id}_thumb_{i}.jpg'
            
            # FFmpeg로 썸네일 추출
            cmd = f'ffmpeg -i {local_input} -ss {timestamp} -vframes 1 -q:v 2 {local_thumbnail}'
            subprocess.run(cmd, shell=True, check=True)
            
            # S3에 업로드
            thumbnail_key = f'thumbnails/{job_id}/thumb_{i}.jpg'
            s3.upload_file(local_thumbnail, output_bucket, thumbnail_key)
            
            thumbnails.append({
                'timestamp': timestamp,
                'key': thumbnail_key,
                'size': os.path.getsize(local_thumbnail)
            })
            
            os.remove(local_thumbnail)
        
        os.remove(local_input)
        
        return {
            'jobId': job_id,
            'thumbnails': thumbnails,
            'status': 'THUMBNAIL_COMPLETE'
        }
        
    except Exception as e:
        print(f"Thumbnail generation error: {str(e)}")
        raise e
```

### 5. 알림 시스템 구성

#### SNS 토픽 설정
```json
{
  "TopicArn": "arn:aws:sns:region:account:video-processing-notifications",
  "DisplayName": "동영상 처리 알림",
  "Subscriptions": [
    {
      "Protocol": "email",
      "Endpoint": "admin@company.com"
    },
    {
      "Protocol": "sms",
      "Endpoint": "+82-10-1234-5678"
    },
    {
      "Protocol": "sqs",
      "Endpoint": "arn:aws:sqs:region:account:notification-queue"
    }
  ]
}
```

#### 사용자별 개인화 알림
```python
import json
import boto3

def send_personalized_notification(event, context):
    sns = boto3.client('sns')
    dynamodb = boto3.resource('dynamodb')
    
    table = dynamodb.Table('VideoProcessingJobs')
    
    for record in event['Records']:
        message = json.loads(record['body'])
        job_id = message['jobId']
        
        # 작업 정보 조회
        response = table.get_item(Key={'jobId': job_id})
        job_data = response['Item']
        
        # 사용자별 알림 설정 조회
        user_prefs = get_user_notification_preferences(job_data['userId'])
        
        # 개인화된 메시지 생성
        notification_message = create_personalized_message(job_data, user_prefs)
        
        # 알림 발송
        if user_prefs.get('email_enabled'):
            send_email_notification(job_data['userEmail'], notification_message)
        
        if user_prefs.get('sms_enabled'):
            send_sms_notification(job_data['userPhone'], notification_message)
```

## ❌ 다른 선택지가 부적절한 이유

### A) EC2 Auto Scaling + SQS + CloudWatch Events
- **서버 관리 필요**: 인스턴스 패치, 보안 업데이트 등
- **비용 비효율**: 처리 중이 아닐 때도 최소 인스턴스 유지
- **복잡한 워크플로우**: 단계별 상태 관리 어려움

### C) ECS Fargate + ALB + RDS
- **컨테이너 오케스트레이션 복잡성**: 불필요한 복잡도
- **데이터베이스 오버헤드**: 간단한 상태 관리에 RDS 과사용
- **비용**: 지속적인 컨테이너 실행 비용

### D) Elastic Beanstalk + SWF + SimpleDB
- **레거시 서비스**: SWF는 Step Functions로 대체
- **제한된 확장성**: SimpleDB 성능 한계
- **관리 복잡성**: Elastic Beanstalk 플랫폼 관리

## 🏗️ 완성된 서버리스 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                   사용자                             │
└─────────────────┬───────────────────────────────────┘
                  │ HTTPS
┌─────────────────▼───────────────────────────────────┐
│              API Gateway                            │
│         (인증, 권한, 요청 라우팅)                      │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│            Lambda (업로드 핸들러)                      │
│         Pre-signed URL 생성 및 작업 등록              │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                  S3                                 │
│           (동영상 파일 저장)                          │
└─────────────────┬───────────────────────────────────┘
                  │ S3 Event
┌─────────────────▼───────────────────────────────────┐
│         Lambda (이벤트 트리거)                        │
│         Step Functions 실행 시작                     │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              Step Functions                         │
│            (워크플로우 오케스트레이션)                  │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   인코딩     │  │  썸네일 생성  │  │   품질 검사   │ │
│  │   Lambda    │  │   Lambda    │  │   Lambda    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                SNS + SQS                            │
│            (알림 및 메시지 큐)                        │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              CloudWatch                             │
│            (모니터링 및 로깅)                         │
└─────────────────────────────────────────────────────┘
```

## 📊 성능 및 비용 최적화

### 1. Lambda 최적화
```python
# 메모리 설정 최적화
LAMBDA_CONFIGURATIONS = {
    'upload_handler': {
        'memory': 256,  # MB
        'timeout': 30   # seconds
    },
    'video_encoding': {
        'memory': 3008,  # 최대 메모리로 CPU 성능 향상
        'timeout': 900   # 15분
    },
    'thumbnail_generation': {
        'memory': 1024,
        'timeout': 300   # 5분
    },
    'quality_check': {
        'memory': 512,
        'timeout': 120   # 2분
    }
}

# 동시 실행 제한 설정
CONCURRENCY_LIMITS = {
    'video_encoding': 10,  # 비용 제어
    'thumbnail_generation': 20,
    'default': 100
}
```

### 2. S3 비용 최적화
```json
{
  "LifecycleConfiguration": {
    "Rules": [
      {
        "Id": "VideoProcessingLifecycle",
        "Status": "Enabled",
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
        ]
      },
      {
        "Id": "TempFileCleanup",
        "Status": "Enabled",
        "Filter": {
          "Prefix": "temp/"
        },
        "Expiration": {
          "Days": 1
        }
      }
    ]
  }
}
```

### 3. 모니터링 및 알람
```json
{
  "CloudWatchAlarms": [
    {
      "AlarmName": "Lambda-HighErrorRate",
      "MetricName": "Errors",
      "Namespace": "AWS/Lambda",
      "Statistic": "Sum",
      "Threshold": 10,
      "ComparisonOperator": "GreaterThanThreshold",
      "EvaluationPeriods": 2
    },
    {
      "AlarmName": "StepFunctions-LongExecution",
      "MetricName": "ExecutionTime",
      "Namespace": "AWS/States",
      "Statistic": "Average",
      "Threshold": 3600000,  # 1시간 (밀리초)
      "ComparisonOperator": "GreaterThanThreshold"
    },
    {
      "AlarmName": "S3-HighRequestRate",
      "MetricName": "NumberOfObjects",
      "Namespace": "AWS/S3",
      "Statistic": "Average",
      "Threshold": 1000,
      "ComparisonOperator": "GreaterThanThreshold"
    }
  ]
}
```

## 🔧 오류 처리 및 복구 전략

### 1. 데드레터 큐 (DLQ) 설정
```json
{
  "DeadLetterQueue": {
    "QueueName": "video-processing-dlq",
    "MessageRetentionPeriod": 1209600,  # 14일
    "VisibilityTimeoutSeconds": 60,
    "ReddrivePolicy": {
      "deadLetterTargetArn": "arn:aws:sqs:region:account:video-processing-dlq",
      "maxReceiveCount": 3
    }
  }
}
```

### 2. 재시도 로직
```python
import boto3
from botocore.exceptions import ClientError
import time
import random

def retry_with_exponential_backoff(func, max_retries=3):
    """지수 백오프를 사용한 재시도 데코레이터"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                if attempt == max_retries - 1:
                    raise e
                
                # 지수 백오프 + 지터
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s")
        
        return None
    return wrapper

@retry_with_exponential_backoff
def upload_to_s3(s3_client, bucket, key, file_path):
    """S3 업로드 with 재시도"""
    return s3_client.upload_file(file_path, bucket, key)
```

## 🎓 핵심 학습 포인트

1. **서버리스 First**: 관리 오버헤드 최소화, 사용한 만큼만 비용 지불
2. **이벤트 드리븐**: 느슨한 결합, 확장성, 장애 격리
3. **워크플로우 오케스트레이션**: Step Functions로 복잡한 비즈니스 로직 관리
4. **비동기 처리**: 긴 처리 시간, 사용자 경험 개선
5. **관찰 가능성**: CloudWatch 로그, 메트릭, 분산 추적

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 서버리스 아키텍처 설계 문제의 전형적인 예시입니다. 특히 이벤트 드리븐 시스템과 워크플로우 관리가 핵심 포인트입니다.

서버리스 아키텍처 설계 시 고려사항:

1. **적절한 서비스 선택**: 각 AWS 서비스의 특성과 제약사항 이해
2. **비동기 처리**: 긴 처리 시간과 사용자 경험의 균형
3. **오류 처리**: 재시도, 데드레터 큐, 회로 차단기 패턴
4. **비용 최적화**: 메모리 설정, 동시 실행 제한, 스토리지 생명주기
5. **모니터링**: 분산 시스템의 가시성 확보

다음 포스트에서는 AWS의 데이터 분석 서비스들(Kinesis, EMR, Athena, QuickSight)을 활용한 빅데이터 처리 아키텍처 설계 문제를 다뤄보겠습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - 데이터베이스 성능 최적화]({% post_url 2025-06-24-aws-saa-database-performance-optimization %})

**태그**: #AWS #SAA #Serverless #Lambda #StepFunctions #APIGateway #이벤트드리븐 #워크플로우
