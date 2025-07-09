---
layout: post
title: "AWS SAA 실습 문제: EventBridge와 Step Functions를 활용한 이벤트 기반 워크플로우 아키텍처"
categories: [aws-saa]
tags: [aws, eventbridge, step-functions, lambda, sns, sqs, dynamodb, event-driven]
date: 2025-07-09
---

## 📋 문제 시나리오

당신은 글로벌 물류 회사의 시스템 아키텍트로 근무하고 있습니다. 회사에서는 기존의 모놀리식 주문 처리 시스템을 마이크로서비스 기반의 이벤트 기반 아키텍처로 전환하려고 합니다. 복잡한 비즈니스 워크플로우를 처리하면서도 각 서비스 간의 느슨한 결합을 유지해야 합니다.

### 비즈니스 프로세스
주문이 접수되면 다음과 같은 복잡한 워크플로우가 실행되어야 합니다:

1. **주문 검증** → 재고 확인 → 결제 처리
2. **배송 준비** → 창고 할당 → 포장 지시
3. **배송 시작** → 운송업체 선택 → 추적번호 생성
4. **고객 알림** → 이메일/SMS 발송 → 앱 푸시 알림

### 기술적 요구사항
- **이벤트 기반 아키텍처**: 서비스 간 비동기 통신
- **워크플로우 관리**: 복잡한 비즈니스 로직 처리
- **오류 처리**: 실패 시 재시도 및 복구 메커니즘
- **모니터링**: 실시간 워크플로우 상태 추적
- **확장성**: 주문량 증가에 따른 자동 확장
- **내구성**: 메시지 손실 방지 및 정확히 한 번 처리

### 제약 조건
- **처리 시간**: 주문 접수부터 배송 시작까지 30분 이내
- **가용성**: 99.9% 서비스 가용성 보장
- **일관성**: 분산 트랜잭션 처리
- **비용**: 기존 시스템 대비 30% 비용 절감

## 🎯 해결 방안

### 1. 전체 아키텍처 설계

```
[API Gateway] → [Lambda] → [EventBridge] → [Step Functions]
                                ↓              ↓
[DynamoDB] ← [Lambda] ← [SQS/SNS] ← [Multiple Services]
                ↓
[CloudWatch] → [X-Ray] → [Monitoring Dashboard]
```

### 2. 이벤트 기반 아키텍처 설계

#### A. EventBridge 이벤트 스키마
```json
{
  "source": "ecommerce.orders",
  "detail-type": "Order Placed",
  "detail": {
    "orderId": "ORD-2025-001234",
    "customerId": "CUST-567890",
    "items": [
      {
        "productId": "PROD-12345",
        "quantity": 2,
        "price": 29.99
      }
    ],
    "totalAmount": 59.98,
    "currency": "USD",
    "shippingAddress": {
      "street": "123 Main St",
      "city": "Seoul",
      "country": "KR",
      "zipCode": "12345"
    },
    "timestamp": "2025-07-09T10:30:00Z"
  }
}
```

#### B. 이벤트 라우팅 규칙
```yaml
EventBridge Rules:
  OrderValidationRule:
    EventPattern:
      source: ["ecommerce.orders"]
      detail-type: ["Order Placed"]
    Targets:
      - StepFunction: OrderProcessingWorkflow
      - Lambda: OrderValidationFunction
      - SQS: InventoryCheckQueue
  
  PaymentProcessedRule:
    EventPattern:
      source: ["payment.service"]
      detail-type: ["Payment Completed"]
    Targets:
      - StepFunction: FulfillmentWorkflow
      - SNS: OrderConfirmationTopic
  
  ShippingStartedRule:
    EventPattern:
      source: ["shipping.service"]
      detail-type: ["Shipment Created"]
    Targets:
      - Lambda: CustomerNotificationFunction
      - SQS: TrackingUpdateQueue
```

### 3. Step Functions 워크플로우 설계

#### A. 주문 처리 워크플로우
```json
{
  "Comment": "주문 처리 워크플로우",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "ValidateOrderFunction",
        "Payload.$": "$"
      },
      "Next": "CheckInventory",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "OrderValidationFailed"
        }
      ]
    },
    "CheckInventory": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "CheckInventoryFunction",
        "Payload.$": "$"
      },
      "Next": "InventoryAvailable?"
    },
    "InventoryAvailable?": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.inventoryStatus",
          "StringEquals": "AVAILABLE",
          "Next": "ProcessPayment"
        },
        {
          "Variable": "$.inventoryStatus",
          "StringEquals": "PARTIAL",
          "Next": "HandlePartialInventory"
        }
      ],
      "Default": "InventoryNotAvailable"
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "ProcessPaymentFunction",
        "Payload.$": "$"
      },
      "Next": "PaymentSuccessful?",
      "Retry": [
        {
          "ErrorEquals": ["PaymentDeclined"],
          "IntervalSeconds": 1,
          "MaxAttempts": 1
        }
      ]
    },
    "PaymentSuccessful?": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.paymentStatus",
          "StringEquals": "SUCCESS",
          "Next": "StartFulfillment"
        }
      ],
      "Default": "PaymentFailed"
    },
    "StartFulfillment": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "AllocateWarehouse",
          "States": {
            "AllocateWarehouse": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "AllocateWarehouseFunction",
                "Payload.$": "$"
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "GenerateShippingLabel",
          "States": {
            "GenerateShippingLabel": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "GenerateShippingLabelFunction",
                "Payload.$": "$"
              },
              "End": true
            }
          }
        }
      ],
      "Next": "NotifyCustomer"
    },
    "NotifyCustomer": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:region:account:customer-notifications",
        "Message.$": "$.notificationMessage",
        "MessageAttributes": {
          "customerId": {
            "DataType": "String",
            "StringValue.$": "$.customerId"
          }
        }
      },
      "End": true
    },
    "HandlePartialInventory": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "HandlePartialInventoryFunction",
        "Payload.$": "$"
      },
      "Next": "ProcessPayment"
    },
    "InventoryNotAvailable": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "HandleInventoryShortageFunction",
        "Payload.$": "$"
      },
      "End": true
    },
    "PaymentFailed": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "HandlePaymentFailureFunction",
        "Payload.$": "$"
      },
      "End": true
    },
    "OrderValidationFailed": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "HandleOrderValidationFailureFunction",
        "Payload.$": "$"
      },
      "End": true
    }
  }
}
```

### 4. Lambda 함수 구현 예제

#### A. 주문 검증 함수
```python
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')

def lambda_handler(event, context):
    try:
        # 주문 데이터 추출
        order_data = event['detail'] if 'detail' in event else event
        
        # 주문 검증 로직
        validation_result = validate_order(order_data)
        
        if validation_result['isValid']:
            # DynamoDB에 주문 저장
            save_order_to_db(order_data)
            
            # 검증 성공 이벤트 발행
            publish_event('order.validation', 'Order Validated', {
                'orderId': order_data['orderId'],
                'status': 'VALIDATED'
            })
            
            return {
                'statusCode': 200,
                'orderId': order_data['orderId'],
                'status': 'VALIDATED',
                'validationDetails': validation_result
            }
        else:
            # 검증 실패 이벤트 발행
            publish_event('order.validation', 'Order Validation Failed', {
                'orderId': order_data['orderId'],
                'status': 'VALIDATION_FAILED',
                'errors': validation_result['errors']
            })
            
            raise Exception(f"Order validation failed: {validation_result['errors']}")
            
    except Exception as e:
        print(f"Error processing order: {str(e)}")
        raise

def validate_order(order_data):
    errors = []
    
    # 필수 필드 검증
    required_fields = ['orderId', 'customerId', 'items', 'totalAmount']
    for field in required_fields:
        if field not in order_data or not order_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # 상품 검증
    if 'items' in order_data:
        for item in order_data['items']:
            if item['quantity'] <= 0:
                errors.append(f"Invalid quantity for product {item['productId']}")
            if item['price'] <= 0:
                errors.append(f"Invalid price for product {item['productId']}")
    
    # 총액 검증
    if 'items' in order_data and 'totalAmount' in order_data:
        calculated_total = sum(item['quantity'] * item['price'] for item in order_data['items'])
        if abs(calculated_total - order_data['totalAmount']) > 0.01:
            errors.append("Total amount mismatch")
    
    return {
        'isValid': len(errors) == 0,
        'errors': errors
    }

def save_order_to_db(order_data):
    table = dynamodb.Table('Orders')
    
    # Decimal 변환
    order_item = json.loads(json.dumps(order_data), parse_float=Decimal)
    order_item['status'] = 'VALIDATED'
    order_item['createdAt'] = order_data.get('timestamp')
    
    table.put_item(Item=order_item)

def publish_event(source, detail_type, detail):
    eventbridge.put_events(
        Entries=[
            {
                'Source': source,
                'DetailType': detail_type,
                'Detail': json.dumps(detail)
            }
        ]
    )
```

#### B. 재고 확인 함수
```python
import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    try:
        order_data = event['detail'] if 'detail' in event else event
        
        inventory_result = check_inventory_availability(order_data['items'])
        
        # 재고 상태에 따른 처리
        if inventory_result['status'] == 'AVAILABLE':
            # 재고 예약
            reserve_inventory(order_data['items'])
            
            return {
                'statusCode': 200,
                'orderId': order_data['orderId'],
                'inventoryStatus': 'AVAILABLE',
                'reservedItems': inventory_result['availableItems']
            }
        elif inventory_result['status'] == 'PARTIAL':
            # 부분 재고 처리를 위한 SQS 메시지 전송
            send_partial_inventory_message(order_data, inventory_result)
            
            return {
                'statusCode': 200,
                'orderId': order_data['orderId'],
                'inventoryStatus': 'PARTIAL',
                'availableItems': inventory_result['availableItems'],
                'unavailableItems': inventory_result['unavailableItems']
            }
        else:
            # 재고 부족 알림
            send_inventory_shortage_notification(order_data, inventory_result)
            
            return {
                'statusCode': 400,
                'orderId': order_data['orderId'],
                'inventoryStatus': 'UNAVAILABLE',
                'unavailableItems': inventory_result['unavailableItems']
            }
            
    except Exception as e:
        print(f"Error checking inventory: {str(e)}")
        raise

def check_inventory_availability(items):
    table = dynamodb.Table('Inventory')
    available_items = []
    unavailable_items = []
    
    for item in items:
        response = table.get_item(
            Key={'productId': item['productId']}
        )
        
        if 'Item' in response:
            inventory_item = response['Item']
            available_quantity = inventory_item['availableQuantity']
            
            if available_quantity >= item['quantity']:
                available_items.append(item)
            else:
                unavailable_items.append({
                    **item,
                    'availableQuantity': available_quantity,
                    'shortfall': item['quantity'] - available_quantity
                })
        else:
            unavailable_items.append({
                **item,
                'availableQuantity': 0,
                'shortfall': item['quantity']
            })
    
    if len(unavailable_items) == 0:
        status = 'AVAILABLE'
    elif len(available_items) > 0:
        status = 'PARTIAL'
    else:
        status = 'UNAVAILABLE'
    
    return {
        'status': status,
        'availableItems': available_items,
        'unavailableItems': unavailable_items
    }

def reserve_inventory(items):
    table = dynamodb.Table('Inventory')
    
    for item in items:
        table.update_item(
            Key={'productId': item['productId']},
            UpdateExpression='SET reservedQuantity = reservedQuantity + :qty, availableQuantity = availableQuantity - :qty',
            ExpressionAttributeValues={':qty': item['quantity']}
        )

def send_partial_inventory_message(order_data, inventory_result):
    queue_url = 'https://sqs.region.amazonaws.com/account/partial-inventory-queue'
    
    message = {
        'orderId': order_data['orderId'],
        'customerId': order_data['customerId'],
        'availableItems': inventory_result['availableItems'],
        'unavailableItems': inventory_result['unavailableItems']
    }
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
```

### 5. 메시징 및 알림 시스템

#### A. SQS 큐 구성
```yaml
SQS Queues:
  InventoryCheckQueue:
    VisibilityTimeout: 300
    MessageRetentionPeriod: 1209600  # 14 days
    DelaySeconds: 0
    ReceiveMessageWaitTimeSeconds: 20  # Long polling
    
  PartialInventoryQueue:
    VisibilityTimeout: 600
    MessageRetentionPeriod: 1209600
    ReddrivePolicy:
      deadLetterTargetArn: "arn:aws:sqs:region:account:partial-inventory-dlq"
      maxReceiveCount: 3
      
  PaymentProcessingQueue:
    VisibilityTimeout: 180
    MessageRetentionPeriod: 345600  # 4 days
    
  ShippingQueue:
    VisibilityTimeout: 900
    MessageRetentionPeriod: 1209600
```

#### B. SNS 토픽 구성
```yaml
SNS Topics:
  CustomerNotificationTopic:
    Subscriptions:
      - Protocol: email
        Endpoint: notifications@company.com
      - Protocol: sqs
        Endpoint: arn:aws:sqs:region:account:email-queue
      - Protocol: sqs  
        Endpoint: arn:aws:sqs:region:account:sms-queue
        
  OrderStatusTopic:
    Subscriptions:
      - Protocol: lambda
        Endpoint: arn:aws:lambda:region:account:function:UpdateOrderStatus
      - Protocol: sqs
        Endpoint: arn:aws:sqs:region:account:analytics-queue
        
  InventoryAlertTopic:
    Subscriptions:
      - Protocol: email
        Endpoint: inventory@company.com
      - Protocol: lambda
        Endpoint: arn:aws:lambda:region:account:function:AutoReorderFunction
```

### 6. 오류 처리 및 복구 메커니즘

#### A. Dead Letter Queue 설정
```python
# DLQ 메시지 처리 Lambda 함수
import json
import boto3

cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')

def lambda_handler(event, context):
    for record in event['Records']:
        try:
            # DLQ에서 받은 메시지 분석
            message_body = json.loads(record['body'])
            
            # 실패 유형 분석
            failure_type = analyze_failure(message_body)
            
            # CloudWatch 메트릭 전송
            send_failure_metric(failure_type)
            
            # 운영팀 알림
            if failure_type == 'CRITICAL':
                send_alert_notification(message_body)
            
            # 재처리 가능한 경우 재시도 큐로 전송
            if is_retryable(failure_type):
                schedule_retry(message_body)
                
        except Exception as e:
            print(f"Error processing DLQ message: {str(e)}")

def analyze_failure(message):
    # 실패 패턴 분석 로직
    error_patterns = {
        'PaymentTimeout': 'RETRYABLE',
        'InventoryServiceDown': 'RETRYABLE', 
        'InvalidOrderData': 'PERMANENT',
        'CustomerNotFound': 'PERMANENT'
    }
    
    return error_patterns.get(message.get('errorType'), 'UNKNOWN')
```

#### B. 회로 차단기 패턴
```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# 사용 예제
payment_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

def process_payment_with_circuit_breaker(payment_data):
    return payment_circuit_breaker.call(process_payment, payment_data)
```

### 7. 모니터링 및 관찰성

#### A. CloudWatch 대시보드
```yaml
Dashboard Widgets:
  WorkflowMetrics:
    - Step Functions Executions (Success/Failed)
    - Average Execution Duration
    - State Transition Counts
    
  EventMetrics:
    - EventBridge Rule Invocations
    - Failed Events
    - Event Processing Latency
    
  LambdaMetrics:
    - Function Duration
    - Error Rate
    - Throttles
    - Concurrent Executions
    
  QueueMetrics:
    - SQS Message Counts
    - DLQ Message Counts
    - Processing Time
    
  BusinessMetrics:
    - Orders per Hour
    - Order Success Rate
    - Average Order Processing Time
    - Revenue per Hour
```

#### B. X-Ray 트레이싱
```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# AWS 서비스 자동 트레이싱
patch_all()

@xray_recorder.capture('order_validation')
def validate_order(order_data):
    # 커스텀 메타데이터 추가
    xray_recorder.current_segment().put_metadata('order_info', {
        'orderId': order_data['orderId'],
        'itemCount': len(order_data['items']),
        'totalAmount': order_data['totalAmount']
    })
    
    # 검증 로직
    return perform_validation(order_data)

@xray_recorder.capture('inventory_check')  
def check_inventory(items):
    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation('item_count', len(items))
    
    # 재고 확인 로직
    return perform_inventory_check(items)
```

### 8. 성능 최적화

#### A. Lambda 최적화
```python
# 연결 풀링을 위한 전역 변수
import boto3

# 함수 외부에서 클라이언트 초기화 (재사용)
dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')

# Provisioned Concurrency 설정
PROVISIONED_CONCURRENCY = {
    'ValidateOrderFunction': 10,
    'CheckInventoryFunction': 15,
    'ProcessPaymentFunction': 20
}

# 메모리 최적화
MEMORY_CONFIGURATIONS = {
    'ValidateOrderFunction': 512,  # CPU 집약적
    'CheckInventoryFunction': 1024,  # 메모리 집약적  
    'ProcessPaymentFunction': 256   # 간단한 처리
}
```

#### B. EventBridge 최적화
```yaml
EventBridge Optimization:
  BatchSettings:
    MaximumBatchingWindowInSeconds: 5
    MaximumRecordAgeInSeconds: 300
    
  ArchiveSettings:
    ArchiveName: order-events-archive
    RetentionDays: 365
    
  ReplaySettings:
    ReplayName: failed-orders-replay
    EventSourceArn: arn:aws:events:region:account:event-bus/default
```

## 💡 고급 패턴 및 모범 사례

### 1. Saga 패턴 구현
```json
{
  "Comment": "Saga 패턴을 활용한 분산 트랜잭션",
  "StartAt": "BeginTransaction",
  "States": {
    "BeginTransaction": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "ReserveInventory",
          "States": {
            "ReserveInventory": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "ReserveInventoryFunction"
              },
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "Next": "CompensateInventory"
                }
              ],
              "Next": "InventoryReserved"
            },
            "InventoryReserved": {
              "Type": "Succeed"
            },
            "CompensateInventory": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "ReleaseInventoryFunction"
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "ProcessPayment",
          "States": {
            "ProcessPayment": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "ProcessPaymentFunction"
              },
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "Next": "RefundPayment"
                }
              ],
              "Next": "PaymentProcessed"
            },
            "PaymentProcessed": {
              "Type": "Succeed"
            },
            "RefundPayment": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "Parameters": {
                "FunctionName": "RefundPaymentFunction"
              },
              "End": true
            }
          }
        }
      ],
      "Next": "CommitTransaction",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "RollbackTransaction"
        }
      ]
    },
    "CommitTransaction": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "CommitTransactionFunction"
      },
      "End": true
    },
    "RollbackTransaction": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "RollbackTransactionFunction"
      },
      "End": true
    }
  }
}
```

### 2. CQRS 패턴 적용
```python
# Command 모델
class CreateOrderCommand:
    def __init__(self, customer_id, items, shipping_address):
        self.customer_id = customer_id
        self.items = items
        self.shipping_address = shipping_address
        self.timestamp = datetime.utcnow()

# Event 모델
class OrderCreatedEvent:
    def __init__(self, order_id, customer_id, items, total_amount):
        self.order_id = order_id
        self.customer_id = customer_id
        self.items = items
        self.total_amount = total_amount
        self.timestamp = datetime.utcnow()

# Command Handler
def handle_create_order_command(command):
    # 비즈니스 로직 실행
    order = create_order(command)
    
    # 이벤트 발행
    event = OrderCreatedEvent(
        order.id, 
        command.customer_id, 
        command.items,
        order.total_amount
    )
    
    publish_event(event)
    return order

# Query 모델 (읽기 전용)
def get_order_status(order_id):
    table = dynamodb.Table('OrderStatusView')
    response = table.get_item(Key={'orderId': order_id})
    return response.get('Item')
```

## 📊 비용 분석 및 최적화

### 1. 서비스별 비용 예상
```yaml
월간 예상 비용 (10,000 주문 기준):
  Step Functions:
    - State Transitions: $25 (25,000 transitions)
    - Express Workflows: $10 (추가 워크플로우)
    
  EventBridge:
    - Custom Events: $1 (1M events)
    - Cross-region Replication: $5
    
  Lambda:
    - Invocations: $20 (10M invocations)
    - Duration: $30 (GB-seconds)
    
  SQS/SNS:
    - SQS Messages: $5 (1M messages)
    - SNS Messages: $2 (200K messages)
    
  DynamoDB:
    - Read/Write Units: $50
    - Storage: $10
    
  CloudWatch/X-Ray:
    - Logs: $15
    - Metrics: $10
    - Tracing: $5

총 예상 비용: $188/월 (기존 시스템 대비 40% 절감)
```

### 2. 비용 최적화 전략
```yaml
Optimization Strategies:
  Lambda:
    - ARM-based Graviton2 프로세서 사용 (20% 비용 절감)
    - 적절한 메모리 크기 설정
    - Provisioned Concurrency 최적화
    
  Step Functions:
    - Express Workflows 활용 (짧은 워크플로우)
    - 불필요한 state transition 최소화
    
  DynamoDB:
    - On-Demand vs Provisioned 모드 선택
    - DynamoDB Accelerator (DAX) 적용
    - Auto Scaling 설정
```

## 🚀 실습 과제

### 1. 기본 구현 (1-2주)
1. **EventBridge 이벤트 버스 생성** 및 기본 라우팅 규칙 설정
2. **Step Functions 워크플로우** 구현 (주문 처리 플로우)
3. **Lambda 함수** 개발 (주문 검증, 재고 확인)
4. **DynamoDB 테이블** 설계 및 생성

### 2. 고급 기능 구현 (2-3주)
1. **오류 처리 및 재시도** 메커니즘 구현
2. **Dead Letter Queue** 처리 로직 개발
3. **회로 차단기 패턴** 적용
4. **Saga 패턴**을 활용한 분산 트랜잭션 처리

### 3. 모니터링 및 최적화 (1-2주)
1. **CloudWatch 대시보드** 구성
2. **X-Ray 트레이싱** 설정 및 분석
3. **성능 테스트** 수행 및 최적화
4. **비용 분석** 및 최적화 방안 도출

### 4. 고도화 작업 (2-3주)
1. **CQRS 패턴** 적용
2. **이벤트 소싱** 구현
3. **Multi-region 배포** 및 재해 복구
4. **보안 강화** (IAM, KMS, VPC)

이 아키텍처는 현대적인 이벤트 기반 시스템의 모범 사례를 보여주며, AWS SAA 시험에서 중요하게 다뤄지는 분산 시스템 설계, 오류 처리, 모니터링 등의 핵심 개념들을 실제 비즈니스 시나리오와 연결하여 제시합니다.

---

**관련 포스트:**
- [AWS SAA 서버리스 이벤트 기반 아키텍처](../25/aws-saa-serverless-event-driven-architecture)
- [AWS Lambda와 API Gateway를 활용한 서버리스 API](../../07/07/aws-saa-serverless-api-architecture-design)
