---
layout: post
title: "Django + FastAPI YOLO 추론 성능 최적화: 10초 응답시간 개선 전략"
date: 2025-08-10
categories: [Backend, Performance, AI]
tags: [Django, FastAPI, YOLO, MSA, Performance, Optimization, AI, Deep Learning]
---

## 문제 상황 분석

Django 백엔드 서버와 FastAPI를 이용한 MSA 구조에서 YOLO 모델 추론 API가 10초나 걸리는 상황입니다. 이는 사용자 경험을 크게 해치는 수준으로, 즉시 개선이 필요한 성능 이슈입니다.

### 성능 병목 지점 분석

10초라는 긴 응답시간의 원인을 파악하기 위해 다음 지점들을 점검해야 합니다:

1. **모델 로딩 시간**: YOLO 모델을 매번 새로 로딩하는지
2. **이미지 전처리 시간**: 이미지 크기 조정, 정규화 등
3. **추론 연산 시간**: GPU/CPU 리소스 활용도
4. **네트워크 지연**: Django ↔ FastAPI 간 통신
5. **후처리 시간**: 결과 데이터 변환 및 직렬화

## AWS SQS vs Celery/Redis 비교

### AWS SQS 장점
- **완전 관리형 서비스**: 인프라 관리 불필요
- **높은 가용성**: AWS의 99.9% SLA 보장
- **자동 스케일링**: 트래픽에 따른 자동 확장
- **우선순위 큐**: Message attributes를 통한 작업 우선순위 설정
- **데드 레터 큐**: 실패한 메시지 자동 처리
- **비용 효율성**: 사용한 만큼만 과금

### Celery/Redis 장점
- **낮은 지연시간**: 로컬 네트워크 통신
- **복잡한 워크플로우**: 체인, 그룹 등 고급 기능
- **실시간 모니터링**: Flower 등 모니터링 도구
- **개발 편의성**: Django와의 긴밀한 통합

### 추천 시나리오

#### AWS SQS 추천 상황
- 대용량 트래픽 처리가 필요한 경우
- 다중 지역 배포 시스템
- 인프라 관리 리소스가 부족한 경우
- 높은 가용성이 필수인 서비스

#### Celery/Redis 추천 상황
- 실시간 응답이 중요한 경우
- 복잡한 작업 플로우가 필요한 경우
- 온프레미스 환경
- 기존 Redis 인프라가 있는 경우

## 하이브리드 아키텍처 구성

### AWS SQS + 로컬 캐시 조합
```python
# 하이브리드 큐 매니저
class HybridQueueManager:
    def __init__(self):
        self.sqs_manager = SQSManager()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=2)
        self.local_queue_threshold = 100  # 로컬 큐 임계값
    
    async def submit_task(self, image_data, task_id, priority='normal'):
        # 현재 로컬 큐 크기 확인
        local_queue_size = self.redis_client.llen('local_inference_queue')
        
        if local_queue_size < self.local_queue_threshold and priority == 'high':
            # 고우선순위 작업은 로컬 큐에서 빠르게 처리
            await self.submit_to_local_queue(image_data, task_id, priority)
        else:
            # 일반 작업이나 큐가 가득찬 경우 AWS SQS 사용
            await self.sqs_manager.send_inference_task(image_data, task_id, priority)
    
    async def submit_to_local_queue(self, image_data, task_id, priority):
        task_data = {
            'task_id': task_id,
            'image_data': image_data,
            'priority': priority,
            'timestamp': time.time()
        }
        
        if priority == 'high':
            # 고우선순위는 앞쪽에 삽입
            self.redis_client.lpush('local_inference_queue', json.dumps(task_data))
        else:
            # 일반 우선순위는 뒤쪽에 삽입
            self.redis_client.rpush('local_inference_queue', json.dumps(task_data))
```

## 성능 최적화 전략

### 1. 모델 최적화 및 캐싱

#### 모델 사전 로딩 및 싱글톤 패턴
```python
# FastAPI YOLO 서비스
import torch
from ultralytics import YOLO
from functools import lru_cache

class YOLOModelManager:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self):
        if self._model is None:
            self._model = YOLO('yolov8n.pt')  # 또는 사용 중인 모델
            # GPU 사용 가능시 설정
            if torch.cuda.is_available():
                self._model.to('cuda')
        return self._model

@lru_cache(maxsize=1)
def get_yolo_model():
    return YOLOModelManager().get_model()
```

#### 모델 경량화
```python
# 모델 양자화 적용
import torch.quantization as quantization

def optimize_model(model):
    # 동적 양자화 적용 (추론 속도 향상)
    quantized_model = torch.quantization.quantize_dynamic(
        model, {torch.nn.Linear}, dtype=torch.qint8
    )
    return quantized_model
```

### 2. 비동기 처리 및 큐 시스템

#### AWS SQS를 이용한 분산 큐 시스템
```python
# Django settings.py
import boto3

AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_REGION = 'ap-northeast-2'
SQS_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/your-account/yolo-inference-queue'

# utils/sqs_manager.py
import boto3
import json
import uuid
from django.conf import settings

class SQSManager:
    def __init__(self):
        self.sqs = boto3.client(
            'sqs',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.queue_url = settings.SQS_QUEUE_URL
    
    def send_inference_task(self, image_data, task_id, priority='normal'):
        """추론 작업을 SQS 큐에 전송"""
        message_body = {
            'task_id': task_id,
            'image_data': image_data,  # Base64 인코딩된 이미지
            'timestamp': time.time(),
            'priority': priority
        }
        
        # 우선순위에 따른 message attributes 설정
        message_attributes = {
            'Priority': {
                'StringValue': priority,
                'DataType': 'String'
            },
            'TaskType': {
                'StringValue': 'yolo_inference',
                'DataType': 'String'
            }
        }
        
        response = self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes=message_attributes,
            # 중복 제거를 위한 deduplication ID (FIFO 큐 사용시)
            MessageDeduplicationId=task_id
        )
        
        return response['MessageId']
    
    def receive_inference_tasks(self, max_messages=10):
        """SQS에서 추론 작업 수신"""
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20,  # Long polling 활용
            MessageAttributeNames=['All']
        )
        
        return response.get('Messages', [])
    
    def delete_message(self, receipt_handle):
        """처리 완료된 메시지 삭제"""
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )

# Django View
from django.http import JsonResponse
from .utils.sqs_manager import SQSManager
import base64
import uuid

sqs_manager = SQSManager()

def submit_inference(request):
    task_id = str(uuid.uuid4())
    image_file = request.FILES['image']
    
    # 이미지를 Base64로 인코딩
    image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # 우선순위 결정 (VIP 사용자, 긴급도 등에 따라)
    priority = request.GET.get('priority', 'normal')
    
    # SQS에 작업 전송
    message_id = sqs_manager.send_inference_task(image_data, task_id, priority)
    
    return JsonResponse({
        'task_id': task_id,
        'message_id': message_id,
        'status': 'queued',
        'message': '추론 작업이 큐에 등록되었습니다.'
    })

def get_inference_result(request, task_id):
    # DynamoDB나 RDS에서 결과 조회
    result = get_task_result_from_db(task_id)
    if result:
        return JsonResponse(result)
    else:
        return JsonResponse({
            'task_id': task_id,
            'status': 'processing',
            'message': '아직 처리 중입니다.'
        })
```

#### FastAPI Worker 서비스 (SQS Consumer)
```python
# worker.py - FastAPI YOLO 추론 워커
import asyncio
import json
import base64
import boto3
from io import BytesIO
from PIL import Image
import numpy as np

class YOLOWorker:
    def __init__(self):
        self.sqs_manager = SQSManager()
        self.model = get_yolo_model()
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
        self.results_table = self.dynamodb.Table('yolo-inference-results')
    
    async def process_messages(self):
        """SQS 메시지를 지속적으로 처리"""
        while True:
            try:
                messages = self.sqs_manager.receive_inference_tasks()
                
                if messages:
                    # 병렬 처리로 여러 메시지 동시 처리
                    tasks = [self.process_single_message(msg) for msg in messages]
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # 메시지가 없으면 잠시 대기
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"메시지 처리 중 오류: {e}")
                await asyncio.sleep(5)
    
    async def process_single_message(self, message):
        """개별 메시지 처리"""
        try:
            # 메시지 파싱
            body = json.loads(message['Body'])
            task_id = body['task_id']
            image_data = body['image_data']
            priority = body.get('priority', 'normal')
            
            # Base64 이미지 디코딩
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # YOLO 추론 실행
            results = self.model(np.array(image))
            
            # 결과 처리
            processed_results = self.process_yolo_results(results)
            
            # DynamoDB에 결과 저장
            await self.save_result_to_db(task_id, processed_results, 'completed')
            
            # SQS에서 메시지 삭제
            self.sqs_manager.delete_message(message['ReceiptHandle'])
            
            print(f"작업 {task_id} 처리 완료 (우선순위: {priority})")
            
        except Exception as e:
            # 실패한 작업 처리
            await self.save_result_to_db(task_id, {'error': str(e)}, 'failed')
            print(f"작업 {task_id} 처리 실패: {e}")
    
    async def save_result_to_db(self, task_id, result, status):
        """DynamoDB에 결과 저장"""
        self.results_table.put_item(
            Item={
                'task_id': task_id,
                'result': result,
                'status': status,
                'timestamp': int(time.time()),
                'ttl': int(time.time()) + 3600  # 1시간 후 자동 삭제
            }
        )
    
    def process_yolo_results(self, results):
        """YOLO 결과 후처리"""
        processed = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    processed.append({
                        'class': int(box.cls[0]),
                        'confidence': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist()
                    })
        return processed

# 워커 실행
if __name__ == "__main__":
    worker = YOLOWorker()
    asyncio.run(worker.process_messages())
```

#### Celery를 이용한 비동기 작업 처리 (기존 방식)
```python
# Django settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# tasks.py
from celery import Celery
import requests

app = Celery('yolo_inference')

@app.task
def process_yolo_inference(image_data, task_id):
    # FastAPI YOLO 서비스 호출
    response = requests.post(
        'http://fastapi-service:8000/inference',
        files={'image': image_data}
    )
    
    # 결과를 Redis나 DB에 저장
    save_inference_result(task_id, response.json())
    return response.json()

# Django View
from django.http import JsonResponse
from .tasks import process_yolo_inference
import uuid

def submit_inference(request):
    task_id = str(uuid.uuid4())
    image_data = request.FILES['image'].read()
    
    # 비동기 작업 시작
    process_yolo_inference.delay(image_data, task_id)
    
    return JsonResponse({
        'task_id': task_id,
        'status': 'processing',
        'message': '추론 작업이 시작되었습니다.'
    })

def get_inference_result(request, task_id):
    result = get_cached_result(task_id)
    if result:
        return JsonResponse(result)
    else:
        return JsonResponse({
            'status': 'processing',
            'message': '아직 처리 중입니다.'
        })
```

### 3. 이미지 전처리 최적화

#### OpenCV 및 NumPy 최적화
```python
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def optimize_image_preprocessing(image_path, target_size=(640, 640)):
    # 이미지 로딩 최적화
    img = cv2.imread(image_path)
    
    # 리사이징 최적화 (INTER_LINEAR 대신 INTER_AREA 사용)
    img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
    
    # 정규화를 vectorized operation으로 처리
    img_normalized = (img_resized.astype(np.float32) / 255.0)
    
    # 채널 순서 변경 (HWC -> CHW)
    img_final = np.transpose(img_normalized, (2, 0, 1))
    
    return img_final

# 배치 처리를 통한 최적화
def process_batch_images(image_list, batch_size=4):
    with ThreadPoolExecutor(max_workers=4) as executor:
        processed_images = list(executor.map(optimize_image_preprocessing, image_list))
    return processed_images
```

### 4. FastAPI 서비스 최적화

#### 배치 추론 구현
```python
from fastapi import FastAPI, File, UploadFile
from typing import List
import asyncio

app = FastAPI()

class BatchInferenceManager:
    def __init__(self, batch_size=4, max_wait_time=1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self.model = get_yolo_model()
    
    async def add_request(self, image_data):
        future = asyncio.Future()
        self.pending_requests.append((image_data, future))
        
        # 배치가 찰 때까지 대기하거나 최대 대기시간 초과시 처리
        if len(self.pending_requests) >= self.batch_size:
            await self.process_batch()
        else:
            asyncio.create_task(self.wait_and_process())
        
        return await future
    
    async def process_batch(self):
        if not self.pending_requests:
            return
            
        batch_data = []
        futures = []
        
        # 현재 배치 추출
        current_batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]
        
        for image_data, future in current_batch:
            batch_data.append(image_data)
            futures.append(future)
        
        # 배치 추론 실행
        results = self.model(batch_data)
        
        # 결과 분배
        for future, result in zip(futures, results):
            future.set_result(result)
    
    async def wait_and_process(self):
        await asyncio.sleep(self.max_wait_time)
        await self.process_batch()

batch_manager = BatchInferenceManager()

@app.post("/inference")
async def inference(file: UploadFile = File(...)):
    image_data = await file.read()
    result = await batch_manager.add_request(image_data)
    return {"result": result}
```

### 5. 캐싱 전략

#### Redis를 이용한 결과 캐싱
```python
import redis
import hashlib
import json
import pickle

redis_client = redis.Redis(host='localhost', port=6379, db=1)

def get_image_hash(image_data):
    return hashlib.md5(image_data).hexdigest()

def cache_inference_result(image_data, result, expire_time=3600):
    image_hash = get_image_hash(image_data)
    cache_key = f"yolo_inference:{image_hash}"
    
    # 결과를 pickle로 직렬화하여 저장
    serialized_result = pickle.dumps(result)
    redis_client.setex(cache_key, expire_time, serialized_result)

def get_cached_result(image_data):
    image_hash = get_image_hash(image_data)
    cache_key = f"yolo_inference:{image_hash}"
    
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return pickle.loads(cached_result)
    return None

@app.post("/inference_with_cache")
async def inference_with_cache(file: UploadFile = File(...)):
    image_data = await file.read()
    
    # 캐시 확인
    cached_result = get_cached_result(image_data)
    if cached_result:
        return {"result": cached_result, "from_cache": True}
    
    # 추론 실행
    result = await batch_manager.add_request(image_data)
    
    # 결과 캐싱
    cache_inference_result(image_data, result)
    
    return {"result": result, "from_cache": False}
```

### 6. 인프라 최적화

#### GPU 메모리 관리
```python
import torch

def optimize_gpu_memory():
    if torch.cuda.is_available():
        # GPU 메모리 캐시 정리
        torch.cuda.empty_cache()
        
        # 메모리 할당 전략 최적화
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False

# 모델 로딩시 메모리 최적화 적용
def load_optimized_model():
    optimize_gpu_memory()
    model = YOLO('yolov8n.pt')
    
    if torch.cuda.is_available():
        model.to('cuda')
        # 반정밀도 추론으로 메모리 사용량 감소 및 속도 향상
        model.half()
    
    return model
```

#### AWS 인프라 구성
```yaml
# docker-compose.yml
version: '3.8'
services:
  django-api:
    build: ./django
    ports:
      - "8000:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - redis
  
  yolo-worker:
    build: ./fastapi
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    deploy:
      replicas: 3  # 워커 인스턴스 수 조정
    volumes:
      - /dev/shm:/dev/shm  # GPU 메모리 공유
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

# AWS CloudFormation 템플릿 (infrastructure.yaml)
Resources:
  YOLOInferenceQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: yolo-inference-queue
      VisibilityTimeoutSeconds: 300
      MessageRetentionPeriod: 1209600  # 14일
      ReceiveMessageWaitTimeSeconds: 20  # Long polling
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue.Arn
        maxReceiveCount: 3
  
  DeadLetterQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: yolo-inference-dlq
      MessageRetentionPeriod: 1209600
  
  YOLOResultsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: yolo-inference-results
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: task_id
          AttributeType: S
      KeySchema:
        - AttributeName: task_id
          KeyType: HASH
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
```

#### Docker 컨테이너 최적화
```dockerfile
# FastAPI YOLO 서비스 Dockerfile
FROM nvidia/cuda:11.8-runtime-ubuntu20.04

# 멀티스테이지 빌드로 이미지 크기 최적화
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 필요한 패키지만 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 모델 파일 사전 다운로드
RUN python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY . .

# 컨테이너 리소스 최적화
ENV CUDA_VISIBLE_DEVICES=0
ENV OMP_NUM_THREADS=4

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 7. 모니터링 및 성능 측정

#### 성능 프로파일링
```python
import time
import functools
from contextlib import contextmanager

@contextmanager
def timer(description):
    start = time.time()
    yield
    elapsed = time.time() - start
    print(f"{description}: {elapsed:.3f}초")

def profile_inference_pipeline(image_data):
    with timer("전체 추론 파이프라인"):
        with timer("이미지 전처리"):
            preprocessed = optimize_image_preprocessing(image_data)
        
        with timer("모델 추론"):
            model = get_yolo_model()
            results = model(preprocessed)
        
        with timer("후처리"):
            processed_results = post_process_results(results)
    
    return processed_results
```

## 단계별 구현 로드맵

### Phase 1: 즉시 적용 가능한 최적화 (1-2일)
1. 모델 사전 로딩 및 싱글톤 패턴 적용
2. 이미지 전처리 최적화
3. GPU 메모리 관리 개선

### Phase 2: 아키텍처 개선 (1주)
1. Redis 캐싱 시스템 구축
2. 비동기 처리 시스템 도입
3. 배치 추론 구현

### Phase 3: 고도화 최적화 (2-3주)
1. 모델 양자화 및 경량화
2. 멀티프로세싱 및 로드 밸런싱
3. 모니터링 시스템 구축

## 예상 성능 개선 효과

| 최적화 방법 | 예상 개선 효과 | 구현 난이도 | 비용 |
|------------|---------------|------------|------|
| 모델 사전 로딩 | 2-3초 단축 | 쉬움 | 무료 |
| 이미지 전처리 최적화 | 1-2초 단축 | 중간 | 무료 |
| 배치 추론 | 30-50% 향상 | 중간 | 무료 |
| 결과 캐싱 | 90% 단축 (캐시 히트시) | 중간 | 저비용 |
| AWS SQS 큐 시스템 | 확장성 무제한 | 중간 | 사용량 기반 |
| 모델 양자화 | 20-30% 향상 | 어려움 | 무료 |

### AWS SQS 비용 분석
- **요청 비용**: 100만 건당 $0.40
- **데이터 전송**: 첫 1GB 무료, 이후 GB당 $0.09
- **예상 월 비용** (10만 건 추론): 약 $5-10

### 트래픽별 권장 아키텍처
- **일 1,000건 미만**: Celery + Redis
- **일 1,000-10,000건**: AWS SQS + 로컬 캐시 하이브리드
- **일 10,000건 이상**: AWS SQS + DynamoDB + 다중 워커

## 결론

YOLO 추론 성능 최적화는 단순히 하나의 방법으로 해결되지 않습니다. **모델 최적화**, **아키텍처 개선**, **캐싱 전략**, **인프라 최적화**를 종합적으로 적용해야 합니다.

### 큐 시스템 선택 가이드
- **소규모 프로젝트**: Celery + Redis로 시작
- **중규모 이상**: AWS SQS + DynamoDB 조합 권장
- **하이브리드**: 긴급 작업은 로컬, 일반 작업은 SQS 분산 처리

특히 10초라는 긴 응답시간의 경우, 모델이 매번 새로 로딩되거나 단일 요청 처리 방식일 가능성이 높습니다. 우선적으로 **모델 사전 로딩**과 **AWS SQS 비동기 처리**를 적용하면 상당한 성능 개선을 경험할 수 있을 것입니다.

AWS SQS를 활용하면 확장성과 안정성을 동시에 확보할 수 있으며, 트래픽 급증 상황에서도 안정적인 서비스 제공이 가능합니다. 사용자 경험을 위해서는 2-3초 내의 응답시간을 목표로 하되, 실시간성이 중요하지 않은 경우 비동기 처리로 즉시 응답하고 결과를 폴링하는 방식을 권장합니다.
