---
layout: post
title: "AWS SQS + Lambda에서 Step Functions + Lambda로 지연 푸시 메시지 시스템 개선기"
date: 2025-07-23
categories: [AWS, Lambda, Step Functions, SQS, Push Notification]
tags: [aws, lambda, stepfunctions, sqs, python, boto3, delayed-messaging, push-notification]
image: "/assets/img/posts/2025-07-23-aws-sqs-to-stepfunctions-delayed-push-messaging.webp"
---

## 개요

사용자에게 특정 액션 후 300초(5분) 뒤에 푸시 메시지를 전송하는 기능을 구현하면서, 처음에는 AWS SQS + Lambda 조합으로 구현했지만 지연 시간의 정확성 문제로 인해 AWS Step Functions + Lambda 구조로 변경한 경험을 공유합니다.

## 기존 구조: SQS Delay Queue + Lambda

### 아키텍처

```
사용자 액션 → API Gateway → Lambda → SQS (DelaySeconds: 300) → Lambda → 푸시 메시지 전송
```

### 구현 코드

#### 1. 지연 메시지 큐 전송

```python
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    
    # 큐 URL
    queue_url = 'https://sqs.ap-northeast-2.amazonaws.com/123456789012/delayed-push-queue'
    
    # 메시지 데이터
    message_data = {
        'user_id': event['user_id'],
        'push_message': event['push_message'],
        'timestamp': datetime.now().isoformat()
    }
    
    # 300초 지연으로 메시지 전송
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_data),
        DelaySeconds=300
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Delayed push message queued',
            'messageId': response['MessageId']
        })
    }
```

#### 2. SQS 트리거 Lambda 함수

```python
import boto3
import json

def lambda_handler(event, context):
    # SQS에서 받은 메시지 처리
    for record in event['Records']:
        message_body = json.loads(record['body'])
        
        user_id = message_body['user_id']
        push_message = message_body['push_message']
        
        # 푸시 메시지 전송
        send_push_notification(user_id, push_message)
    
    return {'statusCode': 200}

def send_push_notification(user_id, message):
    # Firebase Cloud Messaging 또는 다른 푸시 서비스 호출
    fcm = boto3.client('sns')
    
    # 실제 푸시 메시지 전송 로직
    response = fcm.publish(
        TopicArn=f'arn:aws:sns:ap-northeast-2:123456789012:user-{user_id}',
        Message=message
    )
    
    print(f"Push sent to user {user_id}: {response['MessageId']}")
```

### 문제점 발견

1. **지연 시간 부정확성**: SQS의 DelaySeconds는 최대 15분까지 설정 가능하지만, 실제 지연 시간이 정확하지 않음
2. **지연 오차**: 설정한 300초보다 10-30초 정도 빨리 또는 늦게 메시지가 전달됨
3. **모니터링 어려움**: 메시지가 언제 실제로 처리될지 예측하기 어려움

## 개선 구조: Step Functions + Lambda

### 아키텍처

```
사용자 액션 → API Gateway → Lambda → Step Functions (Wait 300s) → Lambda → 푸시 메시지 전송
```

### Step Functions State Machine 정의

```json
{
  "Comment": "300초 후 푸시 메시지 전송 워크플로우",
  "StartAt": "WaitForDelay",
  "States": {
    "WaitForDelay": {
      "Type": "Wait",
      "Seconds": 300,
      "Next": "SendPushNotification"
    },
    "SendPushNotification": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:ap-northeast-2:123456789012:function:send-delayed-push",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleError"
        }
      ],
      "End": true
    },
    "HandleError": {
      "Type": "Pass",
      "Result": "Error occurred while sending push notification",
      "End": true
    }
  }
}
```

### 구현 코드

#### 1. Step Functions 실행 Lambda

```python
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    stepfunctions = boto3.client('stepfunctions')
    
    # Step Functions State Machine ARN
    state_machine_arn = 'arn:aws:states:ap-northeast-2:123456789012:stateMachine:DelayedPushWorkflow'
    
    # 실행 입력 데이터
    execution_input = {
        'user_id': event['user_id'],
        'push_message': event['push_message'],
        'timestamp': datetime.now().isoformat(),
        'execution_id': f"push-{event['user_id']}-{int(datetime.now().timestamp())}"
    }
    
    # Step Functions 실행 시작
    response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_input['execution_id'],
        input=json.dumps(execution_input)
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Delayed push workflow started',
            'executionArn': response['executionArn']
        })
    }
```

#### 2. 푸시 메시지 전송 Lambda

```python
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    
    user_id = event['user_id']
    push_message = event['push_message']
    original_timestamp = event['timestamp']
    
    # 실제 실행 시간과 예상 시간 비교 (모니터링용)
    current_time = datetime.now()
    original_time = datetime.fromisoformat(original_timestamp)
    actual_delay = (current_time - original_time).total_seconds()
    
    print(f"Expected delay: 300s, Actual delay: {actual_delay}s")
    
    try:
        # 푸시 메시지 전송
        result = send_push_notification(user_id, push_message)
        
        return {
            'statusCode': 200,
            'user_id': user_id,
            'message_sent': True,
            'actual_delay_seconds': actual_delay,
            'push_result': result
        }
        
    except Exception as e:
        print(f"Error sending push notification: {str(e)}")
        raise e

def send_push_notification(user_id, message):
    """실제 푸시 알림 전송 함수"""
    
    # Firebase Admin SDK 또는 AWS SNS 사용
    sns = boto3.client('sns')
    
    # 사용자별 엔드포인트 ARN 조회 (실제 구현에서는 DynamoDB 등에서 조회)
    endpoint_arn = get_user_push_endpoint(user_id)
    
    if not endpoint_arn:
        raise Exception(f"No push endpoint found for user {user_id}")
    
    # 푸시 메시지 페이로드 생성
    push_payload = {
        "GCM": json.dumps({
            "notification": {
                "title": "알림",
                "body": message
            },
            "data": {
                "user_id": str(user_id),
                "timestamp": datetime.now().isoformat()
            }
        })
    }
    
    # SNS를 통한 푸시 메시지 전송
    response = sns.publish(
        TargetArn=endpoint_arn,
        Message=json.dumps(push_payload),
        MessageStructure='json'
    )
    
    print(f"Push notification sent successfully: {response['MessageId']}")
    return response['MessageId']

def get_user_push_endpoint(user_id):
    """사용자의 푸시 알림 엔드포인트 조회 (실제 구현 필요)"""
    # DynamoDB에서 사용자의 디바이스 토큰/엔드포인트 조회
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('user_push_endpoints')
    
    try:
        response = table.get_item(Key={'user_id': str(user_id)})
        if 'Item' in response:
            return response['Item']['endpoint_arn']
    except Exception as e:
        print(f"Error retrieving push endpoint: {str(e)}")
    
    return None
```

#### 3. Step Functions State Machine 생성 스크립트

```python
import boto3
import json

def create_delayed_push_state_machine():
    stepfunctions = boto3.client('stepfunctions')
    iam = boto3.client('iam')
    
    # IAM 역할 ARN (사전에 생성되어 있어야 함)
    role_arn = 'arn:aws:iam::123456789012:role/StepFunctionsExecutionRole'
    
    # State Machine 정의
    definition = {
        "Comment": "300초 후 푸시 메시지 전송 워크플로우",
        "StartAt": "WaitForDelay",
        "States": {
            "WaitForDelay": {
                "Type": "Wait",
                "Seconds": 300,
                "Next": "SendPushNotification"
            },
            "SendPushNotification": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:ap-northeast-2:123456789012:function:send-delayed-push",
                "Retry": [
                    {
                        "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException"],
                        "IntervalSeconds": 2,
                        "MaxAttempts": 3,
                        "BackoffRate": 2.0
                    }
                ],
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "HandleError"
                    }
                ],
                "End": true
            },
            "HandleError": {
                "Type": "Pass",
                "Result": "Error occurred while sending push notification",
                "End": true
            }
        }
    }
    
    # State Machine 생성
    response = stepfunctions.create_state_machine(
        name='DelayedPushWorkflow',
        definition=json.dumps(definition),
        roleArn=role_arn,
        type='STANDARD'
    )
    
    print(f"State Machine created: {response['stateMachineArn']}")
    return response['stateMachineArn']

if __name__ == "__main__":
    create_delayed_push_state_machine()
```

## 개선 결과 비교

### 정확성

| 항목 | SQS + Lambda | Step Functions + Lambda |
|------|--------------|-------------------------|
| 지연 시간 정확도 | ±10-30초 오차 | ±1-2초 오차 |
| 예측 가능성 | 낮음 | 높음 |
| 모니터링 | 제한적 | 상세한 실행 기록 |

### 비용

```python
# 월 10,000건 기준 비용 계산 예시

# SQS + Lambda 비용
sqs_requests = 10000  # 메시지 전송 요청
sqs_cost = (sqs_requests / 1000000) * 0.40  # $0.40 per million requests

lambda_invocations = 20000  # 2개 Lambda 함수 × 10,000건
lambda_cost = (lambda_invocations / 1000000) * 0.20  # $0.20 per million requests

total_sqs_solution = sqs_cost + lambda_cost

# Step Functions + Lambda 비용
sf_transitions = 20000  # 2개 상태 전환 × 10,000건
sf_cost = (sf_transitions / 1000) * 0.025  # $0.025 per 1,000 state transitions

lambda_invocations_sf = 20000  # 2개 Lambda 함수 × 10,000건
lambda_cost_sf = (lambda_invocations_sf / 1000000) * 0.20

total_sf_solution = sf_cost + lambda_cost_sf

print(f"SQS 솔루션 월 비용: ${total_sqs_solution:.4f}")
print(f"Step Functions 솔루션 월 비용: ${total_sf_solution:.4f}")
```

### 모니터링 및 디버깅

```python
# Step Functions 실행 상태 모니터링
def monitor_delayed_push_executions():
    stepfunctions = boto3.client('stepfunctions')
    
    # 실행 중인 워크플로우 조회
    response = stepfunctions.list_executions(
        stateMachineArn='arn:aws:states:ap-northeast-2:123456789012:stateMachine:DelayedPushWorkflow',
        statusFilter='RUNNING',
        maxResults=100
    )
    
    running_executions = []
    for execution in response['executions']:
        execution_detail = stepfunctions.describe_execution(
            executionArn=execution['executionArn']
        )
        
        running_executions.append({
            'name': execution['name'],
            'status': execution['status'],
            'startDate': execution['startDate'],
            'input': json.loads(execution_detail['input'])
        })
    
    return running_executions

# 실행 결과 분석
def analyze_execution_accuracy():
    stepfunctions = boto3.client('stepfunctions')
    
    # 최근 완료된 실행들 조회
    response = stepfunctions.list_executions(
        stateMachineArn='arn:aws:states:ap-northeast-2:123456789012:stateMachine:DelayedPushWorkflow',
        statusFilter='SUCCEEDED',
        maxResults=100
    )
    
    accuracy_data = []
    for execution in response['executions']:
        execution_detail = stepfunctions.describe_execution(
            executionArn=execution['executionArn']
        )
        
        if execution_detail['output']:
            output = json.loads(execution_detail['output'])
            if 'actual_delay_seconds' in output:
                accuracy_data.append({
                    'expected_delay': 300,
                    'actual_delay': output['actual_delay_seconds'],
                    'error': abs(300 - output['actual_delay_seconds'])
                })
    
    # 정확도 통계 계산
    if accuracy_data:
        errors = [item['error'] for item in accuracy_data]
        avg_error = sum(errors) / len(errors)
        max_error = max(errors)
        
        print(f"평균 오차: {avg_error:.2f}초")
        print(f"최대 오차: {max_error:.2f}초")
        print(f"샘플 수: {len(accuracy_data)}개")
```

## 결론

### 장점

1. **높은 정확성**: Step Functions의 Wait 상태는 매우 정확한 지연 시간 제공
2. **향상된 모니터링**: 각 단계별 실행 상태와 결과를 상세히 추적 가능
3. **확장성**: 복잡한 워크플로우로 쉽게 확장 가능 (조건 분기, 병렬 처리 등)
4. **에러 핸들링**: 내장된 재시도 및 에러 처리 메커니즘

### 고려사항

1. **비용**: Step Functions는 상태 전환당 과금되어 대량 처리 시 비용 증가
2. **복잡성**: 간단한 지연 처리에는 과도할 수 있음
3. **실행 시간 제한**: 최대 1년까지 실행 가능하지만 장기간 실행 시 모니터링 필요

### 권장사항

- **정확한 지연 시간이 중요한 경우**: Step Functions 사용
- **대량의 단순 지연 처리**: SQS 사용 (비용 효율적)
- **복잡한 워크플로우가 예상되는 경우**: Step Functions로 시작하여 확장성 확보

AWS Step Functions를 활용한 지연 메시지 시스템은 정확성과 모니터링 측면에서 큰 개선을 가져왔으며, 향후 더 복잡한 알림 시스템으로 확장할 수 있는 견고한 기반을 제공했습니다.
