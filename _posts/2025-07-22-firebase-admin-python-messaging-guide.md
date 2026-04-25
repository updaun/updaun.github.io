---
layout: post
title: "Firebase Admin SDK Python으로 Cloud Messaging 구현하기"
date: 2025-07-22
categories: [Firebase, Python, Cloud Messaging]
tags: [firebase, python, fcm, push notification, messaging]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-07-22-firebase-admin-python-messaging-guide.webp"
---

Firebase Cloud Messaging(FCM)은 무료로 메시지를 안정적으로 전송할 수 있는 크로스 플랫폼 메시징 솔루션입니다. 이 포스트에서는 Firebase Admin SDK를 사용하여 Python에서 FCM 메시지를 전송하는 방법을 알아보겠습니다.

## 📋 목차

1. [Firebase Admin SDK 설정](#firebase-admin-sdk-설정)
2. [특정 기기에 메시지 전송](#특정-기기에-메시지-전송)
3. [여러 기기에 메시지 전송](#여러-기기에-메시지-전송)
4. [주제(Topic) 기반 메시지 전송](#주제topic-기반-메시지-전송)
5. [메시지 유형별 예제](#메시지-유형별-예제)
6. [플랫폼별 커스터마이징](#플랫폼별-커스터마이징)

---

## Firebase Admin SDK 설정

먼저 Firebase Admin SDK를 설치하고 초기화해야 합니다.

```bash
pip install firebase-admin
```

```python
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

# 서비스 계정 키 파일로 초기화
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
```

## 특정 기기에 메시지 전송

가장 기본적인 형태로, 특정 기기의 등록 토큰을 사용하여 메시지를 전송하는 방법입니다.

```python
# 클라이언트 앱에서 받은 등록 토큰
registration_token = 'YOUR_REGISTRATION_TOKEN'

# 메시지 구성
message = messaging.Message(
    data={
        'score': '850',
        'time': '2:45',
    },
    token=registration_token,
)

# 메시지 전송
response = messaging.send(message)
print('Successfully sent message:', response)
```

성공적으로 전송되면 메시지 ID가 `projects/{project_id}/messages/{message_id}` 형식으로 반환됩니다.

## 여러 기기에 메시지 전송

동일한 메시지를 여러 기기에 한 번에 전송할 수 있습니다. 한 번의 호출로 최대 500개의 기기에 전송 가능합니다.

```python
# 여러 등록 토큰
registration_tokens = [
    'YOUR_REGISTRATION_TOKEN_1',
    'YOUR_REGISTRATION_TOKEN_2',
    # ... 최대 500개
]

message = messaging.MulticastMessage(
    data={
        'score': '850',
        'time': '2:45'
    },
    tokens=registration_tokens,
)

response = messaging.send_multicast(message)
print(f'Successfully sent {response.success_count} messages')

# 실패한 토큰 확인
if response.failure_count > 0:
    failed_tokens = []
    for idx, resp in enumerate(response.responses):
        if not resp.success:
            failed_tokens.append(registration_tokens[idx])
    print('Failed tokens:', failed_tokens)
```

## 주제(Topic) 기반 메시지 전송

주제를 구독한 모든 기기에 메시지를 전송할 수 있습니다.

### 단일 주제로 전송

```python
# 주제 이름 (선택적으로 "/topics/" 접두사 사용 가능)
topic = 'highScores'

message = messaging.Message(
    data={
        'score': '850',
        'time': '2:45'
    },
    topic=topic
)

response = messaging.send(message)
print('Successfully sent message:', response)
```

### 조건부 주제 전송

여러 주제의 조합으로 메시지를 전송할 수 있습니다.

```python
# TopicA와 함께 TopicB 또는 TopicC를 구독하는 기기에 전송
condition = "'TopicA' in topics && ('TopicB' in topics || 'TopicC' in topics)"

message = messaging.Message(
    notification=messaging.Notification(
        title='주식 뉴스',
        body='FooCorp 주가가 1.43% 상승했습니다.'
    ),
    condition=condition
)

response = messaging.send(message)
print('Successfully sent message:', response)
```

## 메시지 유형별 예제

### 알림 메시지

```python
message = messaging.Message(
    notification=messaging.Notification(
        title='새로운 메시지',
        body='안읽은 메시지가 5개 있습니다.'
    ),
    token=registration_token
)
```

### 데이터 메시지

```python
message = messaging.Message(
    data={
        'action': 'new_message',
        'message_count': '5',
        'user_id': '12345'
    },
    token=registration_token
)
```

### 알림 + 데이터 메시지

```python
message = messaging.Message(
    notification=messaging.Notification(
        title='새로운 주문',
        body='주문이 접수되었습니다.'
    ),
    data={
        'order_id': '67890',
        'status': 'confirmed',
        'amount': '25000'
    },
    token=registration_token
)
```

## 플랫폼별 커스터마이징

플랫폼별로 메시지를 커스터마이징할 수 있습니다.

### Android 특화 설정

```python
message = messaging.Message(
    notification=messaging.Notification(
        title='주식 업데이트',
        body='FooCorp 주가가 상승했습니다.'
    ),
    android=messaging.AndroidConfig(
        ttl=datetime.timedelta(seconds=3600),
        priority='high',
        notification=messaging.AndroidNotification(
            icon='stock_ticker_update',
            color='#7e55c3',
            sound='default'
        )
    ),
    token=registration_token
)
```

### iOS(APNs) 특화 설정

```python
message = messaging.Message(
    notification=messaging.Notification(
        title='주식 업데이트',
        body='FooCorp 주가가 상승했습니다.'
    ),
    apns=messaging.APNSConfig(
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                badge=1,
                sound='default',
                category='STOCK_UPDATE'
            )
        )
    ),
    token=registration_token
)
```

### 웹 푸시 설정

```python
message = messaging.Message(
    notification=messaging.Notification(
        title='주식 업데이트',
        body='FooCorp 주가가 상승했습니다.'
    ),
    webpush=messaging.WebpushConfig(
        headers={
            'TTL': '300'
        },
        notification=messaging.WebpushNotification(
            title='주식 업데이트',
            body='FooCorp 주가가 상승했습니다.',
            icon='https://example.com/icon.png',
            badge='https://example.com/badge.png'
        )
    ),
    token=registration_token
)
```

## 실용적인 예제: 배치 메시지 전송

실제 프로덕션 환경에서 자주 사용되는 배치 메시지 전송 예제입니다.

```python
def send_bulk_notifications(user_tokens, title, body, data=None):
    """
    대량의 사용자에게 알림 전송
    """
    if not user_tokens:
        return
    
    # 500개씩 나누어서 전송 (FCM 제한)
    batch_size = 500
    
    for i in range(0, len(user_tokens), batch_size):
        batch_tokens = user_tokens[i:i + batch_size]
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            tokens=batch_tokens
        )
        
        try:
            response = messaging.send_multicast(message)
            print(f'Batch {i//batch_size + 1}: {response.success_count} 성공, {response.failure_count} 실패')
            
            # 실패한 토큰 로깅
            if response.failure_count > 0:
                failed_tokens = []
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(batch_tokens[idx])
                        print(f'Failed token: {batch_tokens[idx]}, Error: {resp.exception}')
                        
        except Exception as e:
            print(f'배치 전송 실패: {e}')

# 사용 예
user_tokens = ['token1', 'token2', 'token3', ...]
send_bulk_notifications(
    user_tokens=user_tokens,
    title='새로운 업데이트',
    body='앱이 업데이트되었습니다.',
    data={'update_version': '2.1.0'}
)
```

## 오류 처리

메시지 전송 시 발생할 수 있는 오류를 적절히 처리하는 것이 중요합니다.

```python
from firebase_admin import exceptions

def send_message_with_error_handling(message):
    try:
        response = messaging.send(message)
        print(f'메시지 전송 성공: {response}')
        return response
    except exceptions.InvalidArgumentError:
        print('잘못된 인수로 인해 전송 실패')
    except exceptions.UnavailableError:
        print('FCM 서비스를 일시적으로 사용할 수 없음')
    except Exception as e:
        print(f'메시지 전송 실패: {e}')
    
    return None
```

## 주의사항 및 베스트 프랙티스

1. **인증**: Firebase 프로젝트 설정에서 서비스 계정 키를 안전하게 관리하세요.
2. **토큰 관리**: 등록 토큰이 만료될 수 있으므로 정기적으로 갱신하세요.
3. **배치 크기**: 한 번에 최대 500개의 토큰까지만 전송 가능합니다.
4. **오류 처리**: 실패한 토큰을 추적하고 적절히 처리하세요.
5. **플랫폼별 최적화**: 각 플랫폼의 특성에 맞게 메시지를 커스터마이징하세요.

Firebase Admin SDK를 사용하면 Python에서 손쉽게 크로스 플랫폼 푸시 알림을 구현할 수 있습니다. 위의 예제들을 참고하여 애플리케이션에 맞는 메시징 기능을 구현해보세요.
