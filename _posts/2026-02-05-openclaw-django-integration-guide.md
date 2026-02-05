---
layout: post
title: "OpenClaw로 Django 프로젝트에 AI 비서 통합하기 - 멀티채널 챗봇 시스템 구축"
date: 2026-02-05
categories: django python ai
author: updaun
image: "/assets/img/posts/2026-02-05-openclaw-django-integration-guide.webp"
---

# OpenClaw로 Django 프로젝트에 AI 비서 통합하기

최근 AI 개발자 커뮤니티에서 [OpenClaw](https://github.com/openclaw/openclaw)가 화제입니다. OpenClaw는 WhatsApp, Telegram, Slack, Discord 등 여러 메시징 플랫폼을 통해 AI 에이전트와 상호작용할 수 있게 해주는 오픈소스 게이트웨이 시스템입니다. 이 글에서는 Django 개발자 관점에서 OpenClaw를 실무 프로젝트에 어떻게 통합하고 활용할 수 있는지 실전 예제와 함께 살펴봅니다.

## OpenClaw란 무엇인가?

OpenClaw는 로컬 우선(local-first) AI 비서 게이트웨이로, 다음과 같은 핵심 기능을 제공합니다:

### 주요 특징

1. **멀티채널 지원**: WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, Matrix 등
2. **브라우저 자동화**: Playwright 기반의 웹 스크래핑 및 자동화
3. **음성 인터페이스**: Voice Wake와 Talk Mode를 통한 음성 명령
4. **멀티 에이전트 라우팅**: 사용자별, 워크스페이스별 세션 격리
5. **Webhook 통합**: Django 프로젝트와의 양방향 통신
6. **AI 모델 유연성**: Claude, GPT, Gemini 등 다양한 모델 지원

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
openclaw channels login
openclaw gateway --port 18789
```

## Django 개발자가 OpenClaw를 써야 하는 이유

### 1. 고객 지원 자동화

전통적인 Django 기반 웹 애플리케이션에 고객 문의 채널을 추가하려면 각 플랫폼의 API를 개별적으로 통합해야 했습니다. OpenClaw는 이를 하나의 게이트웨이로 통합합니다.

```python
# 기존 방식: 각 플랫폼마다 별도 봇 구현
# - Telegram Bot API
# - WhatsApp Business API (비용 발생)
# - Slack Bolt
# - Discord.py
# 각각 다른 인증, 다른 이벤트 핸들러...

# OpenClaw 방식: 단일 Webhook 엔드포인트
# Django view가 모든 채널의 메시지를 받음
```

### 2. 내부 운영 도구 구축

개발팀의 운영 작업을 채팅 명령으로 자동화할 수 있습니다.

```python
# Slack에서 "/deploy production" 입력
# → OpenClaw webhook → Django view → Celery 작업 트리거
# → 배포 스크립트 실행 → 결과를 Slack으로 회신
```

### 3. 데이터 수집 및 모니터링

사용자와의 대화를 통해 피드백, 버그 리포트, 사용 패턴을 자동으로 수집하고 Django 모델에 저장할 수 있습니다.

## OpenClaw 설치 및 기본 설정

### 시스템 요구사항

```bash
# Node.js 18+ 필요
node --version  # v18.0.0 이상

# OpenClaw 설치
npm install -g openclaw@latest

# 초기 설정 (대화형 마법사)
openclaw onboard

# 설정 파일 생성
mkdir -p ~/.openclaw
```

### 기본 구성 파일

OpenClaw의 설정은 `~/.openclaw/openclaw.json`에 저장됩니다. Django 프로젝트와 통합하기 위한 기본 설정:

```json5
// ~/.openclaw/openclaw.json
{
  // Gateway 기본 설정
  gateway: {
    mode: "local",
    port: 18789,
    bind: "127.0.0.1",
    auth: {
      mode: "token",
      token: process.env.OPENCLAW_GATEWAY_TOKEN || "your-secret-token",
    },
  },

  // Webhook 설정 (Django로 전달)
  automation: {
    webhook: {
      enabled: true,
      url: "http://localhost:8000/api/openclaw/webhook/",
      secret: process.env.OPENCLAW_WEBHOOK_SECRET,
      events: ["message", "status", "media"],
    },
  },

  // 채널 설정
  channels: {
    telegram: {
      enabled: true,
      botToken: process.env.TELEGRAM_BOT_TOKEN,
    },
    slack: {
      enabled: true,
      botToken: process.env.SLACK_BOT_TOKEN,
      appToken: process.env.SLACK_APP_TOKEN,
    },
  },

  // AI 모델 설정
  pi: {
    profiles: [
      {
        id: "anthropic-main",
        provider: "anthropic",
        model: "claude-opus-4-5",
        apiKey: process.env.ANTHROPIC_API_KEY,
      },
    ],
  },
}
```

## Django 프로젝트 통합 - 실전 예제

### 1. Django 모델 설계

OpenClaw에서 받은 메시지와 대화 세션을 저장할 모델을 정의합니다.

```python
# chatbot/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ChatPlatform(models.TextChoices):
    """지원하는 메시징 플랫폼"""
    TELEGRAM = "telegram", "Telegram"
    WHATSAPP = "whatsapp", "WhatsApp"
    SLACK = "slack", "Slack"
    DISCORD = "discord", "Discord"
    WEBCHAT = "webchat", "WebChat"

class ConversationSession(models.Model):
    """OpenClaw 대화 세션"""
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    platform = models.CharField(
        max_length=20,
        choices=ChatPlatform.choices,
        db_index=True
    )
    user_id = models.CharField(max_length=255, db_index=True)  # 플랫폼별 사용자 ID
    django_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_sessions'
    )
    
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    message_count = models.IntegerField(default=0)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['platform', 'user_id']),
            models.Index(fields=['is_active', 'last_activity']),
        ]
    
    def __str__(self):
        return f"{self.platform} - {self.user_id} ({self.session_id})"

class ChatMessage(models.Model):
    """OpenClaw를 통해 주고받은 메시지"""
    
    class MessageDirection(models.TextChoices):
        INBOUND = "inbound", "수신"
        OUTBOUND = "outbound", "발신"
    
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    message_id = models.CharField(max_length=255, unique=True, db_index=True)
    direction = models.CharField(
        max_length=10,
        choices=MessageDirection.choices,
        default=MessageDirection.INBOUND
    )
    
    # 메시지 내용
    text = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)  # 미디어 파일 정보
    
    # AI 응답 관련
    ai_model = models.CharField(max_length=100, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        preview = self.text[:50] if self.text else "[미디어]"
        return f"{self.direction} - {preview}"

class AutomationTrigger(models.Model):
    """자동화 트리거 설정"""
    name = models.CharField(max_length=255)
    platform = models.CharField(
        max_length=20,
        choices=ChatPlatform.choices,
        blank=True  # 빈 값이면 모든 플랫폼
    )
    
    # 트리거 조건
    keyword_patterns = models.JSONField(
        default=list,
        help_text="정규식 패턴 목록"
    )
    
    # 액션 설정
    action_type = models.CharField(
        max_length=50,
        choices=[
            ('send_message', '메시지 전송'),
            ('trigger_task', 'Celery 작업 실행'),
            ('call_webhook', 'Webhook 호출'),
            ('create_ticket', '티켓 생성'),
        ]
    )
    action_config = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.action_type})"

class WebhookLog(models.Model):
    """OpenClaw Webhook 로그"""
    event_type = models.CharField(max_length=50, db_index=True)
    payload = models.JSONField()
    
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_type', 'processed']),
        ]
```

### 2. Webhook 뷰 구현

OpenClaw에서 보내는 이벤트를 처리하는 Django 뷰를 작성합니다.

```python
# chatbot/views.py
import hmac
import hashlib
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from .models import (
    ConversationSession, ChatMessage, AutomationTrigger,
    WebhookLog, ChatPlatform
)
from .tasks import process_chat_message, trigger_automation

logger = logging.getLogger(__name__)

def verify_webhook_signature(request):
    """OpenClaw webhook 서명 검증"""
    signature = request.headers.get('X-OpenClaw-Signature')
    if not signature:
        return False
    
    secret = settings.OPENCLAW_WEBHOOK_SECRET.encode('utf-8')
    body = request.body
    
    expected_signature = hmac.new(
        secret,
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@csrf_exempt
@require_http_methods(["POST"])
def openclaw_webhook(request):
    """
    OpenClaw Gateway에서 보내는 이벤트를 처리
    
    이벤트 타입:
    - message: 사용자가 메시지 전송
    - status: 세션 상태 변경
    - media: 미디어 파일 수신
    - error: 오류 발생
    """
    # 서명 검증
    if not verify_webhook_signature(request):
        logger.warning("Invalid webhook signature")
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    try:
        payload = json.loads(request.body)
        event_type = payload.get('event')
        
        # Webhook 로그 저장
        webhook_log = WebhookLog.objects.create(
            event_type=event_type,
            payload=payload
        )
        
        # 이벤트 타입별 처리
        if event_type == 'message':
            handle_message_event(payload, webhook_log)
        elif event_type == 'status':
            handle_status_event(payload, webhook_log)
        elif event_type == 'media':
            handle_media_event(payload, webhook_log)
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        # 처리 완료 표시
        webhook_log.processed = True
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        logger.exception("Error processing webhook")
        if 'webhook_log' in locals():
            webhook_log.processing_error = str(e)
            webhook_log.save()
        
        return JsonResponse(
            {'error': str(e)},
            status=500
        )

def handle_message_event(payload, webhook_log):
    """사용자 메시지 이벤트 처리"""
    data = payload.get('data', {})
    
    # 세션 정보
    session_id = data.get('sessionId')
    platform = data.get('channel', 'unknown')
    user_id = data.get('senderId')
    
    # 메시지 정보
    message_id = data.get('messageId')
    text = data.get('text', '')
    attachments = data.get('attachments', [])
    
    # 세션 가져오기 또는 생성
    session, created = ConversationSession.objects.get_or_create(
        session_id=session_id,
        defaults={
            'platform': platform,
            'user_id': user_id,
            'metadata': {
                'channel_info': data.get('channelInfo', {}),
            }
        }
    )
    
    # 메시지 저장
    message = ChatMessage.objects.create(
        session=session,
        message_id=message_id,
        direction=ChatMessage.MessageDirection.INBOUND,
        text=text,
        attachments=attachments,
        metadata={
            'raw_payload': data,
        }
    )
    
    # 세션 업데이트
    session.message_count += 1
    session.last_activity = timezone.now()
    session.save()
    
    # 자동화 트리거 확인
    check_automation_triggers(message)
    
    # 비동기 처리 (Celery)
    process_chat_message.delay(message.id)
    
    logger.info(
        f"Message received: {message_id} from {user_id} on {platform}"
    )

def handle_status_event(payload, webhook_log):
    """세션 상태 변경 이벤트 처리"""
    data = payload.get('data', {})
    session_id = data.get('sessionId')
    status = data.get('status')
    
    try:
        session = ConversationSession.objects.get(session_id=session_id)
        
        if status == 'ended':
            session.is_active = False
            session.save()
            logger.info(f"Session ended: {session_id}")
        elif status == 'reset':
            # 세션 초기화
            session.message_count = 0
            session.save()
            logger.info(f"Session reset: {session_id}")
    
    except ConversationSession.DoesNotExist:
        logger.warning(f"Session not found: {session_id}")

def handle_media_event(payload, webhook_log):
    """미디어 파일 수신 이벤트 처리"""
    data = payload.get('data', {})
    message_id = data.get('messageId')
    media_url = data.get('mediaUrl')
    media_type = data.get('mediaType')
    
    try:
        message = ChatMessage.objects.get(message_id=message_id)
        
        # 미디어 정보 추가
        message.attachments.append({
            'url': media_url,
            'type': media_type,
            'timestamp': timezone.now().isoformat(),
        })
        message.save()
        
        logger.info(f"Media received for message {message_id}: {media_type}")
    
    except ChatMessage.DoesNotExist:
        logger.warning(f"Message not found: {message_id}")

def check_automation_triggers(message):
    """자동화 트리거 확인 및 실행"""
    import re
    
    triggers = AutomationTrigger.objects.filter(
        is_active=True
    ).filter(
        models.Q(platform='') | models.Q(platform=message.session.platform)
    )
    
    for trigger in triggers:
        # 키워드 패턴 매칭
        for pattern in trigger.keyword_patterns:
            if re.search(pattern, message.text, re.IGNORECASE):
                logger.info(f"Trigger matched: {trigger.name}")
                trigger_automation.delay(trigger.id, message.id)
                break
```

### 3. OpenClaw API 클라이언트

Django에서 OpenClaw Gateway로 메시지를 보내는 클라이언트를 구현합니다.

```python
# chatbot/openclaw_client.py
import requests
import logging
from typing import Optional, Dict, List
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenClawClient:
    """OpenClaw Gateway API 클라이언트"""
    
    def __init__(self, gateway_url: str = None, token: str = None):
        self.gateway_url = gateway_url or settings.OPENCLAW_GATEWAY_URL
        self.token = token or settings.OPENCLAW_GATEWAY_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        })
    
    def send_message(
        self,
        session_id: str,
        text: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        특정 세션에 메시지 전송
        
        Args:
            session_id: 대화 세션 ID
            text: 메시지 텍스트
            attachments: 첨부 파일 목록
        
        Returns:
            API 응답 딕셔너리
        """
        url = f"{self.gateway_url}/api/messages/send"
        
        payload = {
            'sessionId': session_id,
            'text': text,
        }
        
        if attachments:
            payload['attachments'] = attachments
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Message sent to session {session_id}")
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    def broadcast_message(
        self,
        platform: str,
        user_ids: List[str],
        text: str
    ) -> Dict:
        """
        여러 사용자에게 동시에 메시지 전송
        
        Args:
            platform: 플랫폼 이름 (telegram, whatsapp 등)
            user_ids: 수신자 ID 목록
            text: 메시지 텍스트
        
        Returns:
            전송 결과
        """
        url = f"{self.gateway_url}/api/messages/broadcast"
        
        payload = {
            'platform': platform,
            'recipients': user_ids,
            'text': text,
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Broadcast sent to {len(user_ids)} users on {platform}")
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to broadcast: {e}")
            raise
    
    def get_session_info(self, session_id: str) -> Dict:
        """세션 정보 조회"""
        url = f"{self.gateway_url}/api/sessions/{session_id}"
        
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get session info: {e}")
            raise
    
    def reset_session(self, session_id: str) -> Dict:
        """세션 초기화 (대화 컨텍스트 리셋)"""
        url = f"{self.gateway_url}/api/sessions/{session_id}/reset"
        
        try:
            response = self.session.post(url, timeout=5)
            response.raise_for_status()
            
            logger.info(f"Session reset: {session_id}")
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to reset session: {e}")
            raise
    
    def invoke_browser_tool(
        self,
        action: str,
        params: Dict
    ) -> Dict:
        """
        OpenClaw 브라우저 도구 호출
        
        Args:
            action: snapshot, screenshot, navigate, click 등
            params: 액션별 파라미터
        
        Returns:
            실행 결과
        """
        url = f"{self.gateway_url}/api/tools/browser"
        
        payload = {
            'action': action,
            'params': params,
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Browser tool invoked: {action}")
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to invoke browser tool: {e}")
            raise
    
    def get_health(self) -> Dict:
        """Gateway 상태 확인"""
        url = f"{self.gateway_url}/api/health"
        
        try:
            response = self.session.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {'status': 'error', 'message': str(e)}
```

### 4. Celery 작업 정의

메시지 처리와 자동화를 비동기로 실행하기 위한 Celery 태스크를 정의합니다.

```python
# chatbot/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
import re

from .models import ChatMessage, AutomationTrigger, ConversationSession
from .openclaw_client import OpenClawClient
from .services import (
    analyze_sentiment,
    extract_intent,
    fetch_faq_answer,
    create_support_ticket,
)

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_chat_message(self, message_id):
    """
    수신한 메시지를 처리하고 적절한 응답 생성
    
    1. 메시지 분석 (감정, 의도)
    2. 자동 응답 확인
    3. 필요시 AI 에이전트에게 전달
    """
    try:
        message = ChatMessage.objects.select_related('session').get(id=message_id)
        
        # 감정 분석
        sentiment = analyze_sentiment(message.text)
        message.metadata['sentiment'] = sentiment
        
        # 의도 추출
        intent = extract_intent(message.text)
        message.metadata['intent'] = intent
        
        message.save()
        
        # FAQ 자동 응답
        if intent in ['question', 'help']:
            faq_answer = fetch_faq_answer(message.text)
            if faq_answer:
                send_reply(message.session.session_id, faq_answer)
                return
        
        # 부정적 감정 감지 시 에스컬레이션
        if sentiment == 'negative':
            escalate_to_human(message)
        
        logger.info(f"Message processed: {message_id}")
    
    except ChatMessage.DoesNotExist:
        logger.error(f"Message not found: {message_id}")
    except Exception as e:
        logger.exception(f"Error processing message {message_id}")
        # 재시도
        raise self.retry(exc=e, countdown=60)

@shared_task
def trigger_automation(trigger_id, message_id):
    """자동화 트리거 실행"""
    try:
        trigger = AutomationTrigger.objects.get(id=trigger_id)
        message = ChatMessage.objects.select_related('session').get(id=message_id)
        
        action_type = trigger.action_type
        config = trigger.action_config
        
        if action_type == 'send_message':
            # 자동 응답 전송
            response_text = config.get('message', '')
            send_reply(message.session.session_id, response_text)
        
        elif action_type == 'create_ticket':
            # 지원 티켓 생성
            ticket = create_support_ticket(
                subject=f"Chat from {message.session.user_id}",
                description=message.text,
                metadata={
                    'session_id': message.session.session_id,
                    'platform': message.session.platform,
                }
            )
            
            # 티켓 생성 확인 메시지 전송
            send_reply(
                message.session.session_id,
                f"지원 티켓이 생성되었습니다. 티켓 번호: {ticket.id}"
            )
        
        elif action_type == 'call_webhook':
            # 외부 Webhook 호출
            import requests
            webhook_url = config.get('url')
            if webhook_url:
                requests.post(webhook_url, json={
                    'message_id': message.id,
                    'text': message.text,
                    'session': message.session.session_id,
                }, timeout=10)
        
        logger.info(f"Automation triggered: {trigger.name}")
    
    except Exception as e:
        logger.exception(f"Error triggering automation {trigger_id}")

@shared_task
def send_daily_digest():
    """일일 대화 요약 전송"""
    from django.db.models import Count, Q
    from datetime import timedelta
    
    yesterday = timezone.now() - timedelta(days=1)
    
    # 어제의 통계 수집
    stats = ConversationSession.objects.filter(
        last_activity__gte=yesterday
    ).aggregate(
        total_sessions=Count('id'),
        active_sessions=Count('id', filter=Q(is_active=True)),
        total_messages=Count('messages'),
    )
    
    # 플랫폼별 통계
    platform_stats = ConversationSession.objects.filter(
        last_activity__gte=yesterday
    ).values('platform').annotate(
        count=Count('id')
    )
    
    # Slack으로 요약 전송
    client = OpenClawClient()
    digest_text = f"""📊 일일 채팅 통계 ({yesterday.date()})
    
총 세션: {stats['total_sessions']}
활성 세션: {stats['active_sessions']}
총 메시지: {stats['total_messages']}

플랫폼별:
"""
    
    for platform_stat in platform_stats:
        digest_text += f"- {platform_stat['platform']}: {platform_stat['count']}개 세션\n"
    
    # 관리자 Slack 채널로 전송 (설정에서 지정)
    client.send_message(
        session_id='admin-slack-channel',
        text=digest_text
    )

def send_reply(session_id: str, text: str):
    """세션에 응답 메시지 전송"""
    client = OpenClawClient()
    client.send_message(session_id, text)

def escalate_to_human(message: ChatMessage):
    """인간 상담원에게 에스컬레이션"""
    # 관리자에게 알림
    send_reply(
        'admin-notification-channel',
        f"⚠️ 에스컬레이션 필요\n"
        f"세션: {message.session.session_id}\n"
        f"플랫폼: {message.session.platform}\n"
        f"메시지: {message.text[:100]}"
    )
```

### 5. Django Admin 인터페이스

```python
# chatbot/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    ConversationSession, ChatMessage,
    AutomationTrigger, WebhookLog
)

@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'platform', 'user_id',
        'message_count', 'is_active', 'last_activity'
    ]
    list_filter = ['platform', 'is_active', 'started_at']
    search_fields = ['session_id', 'user_id']
    readonly_fields = ['started_at', 'last_activity', 'message_count']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('session_id', 'platform', 'user_id', 'django_user')
        }),
        ('통계', {
            'fields': ('message_count', 'started_at', 'last_activity')
        }),
        ('상태', {
            'fields': ('is_active', 'metadata')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(msg_count=Count('messages'))

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'message_id', 'session', 'direction',
        'text_preview', 'ai_model', 'created_at'
    ]
    list_filter = ['direction', 'session__platform', 'created_at']
    search_fields = ['message_id', 'text', 'session__session_id']
    readonly_fields = ['created_at', 'delivered_at']
    
    def text_preview(self, obj):
        if obj.text:
            preview = obj.text[:50]
            return f"{preview}..." if len(obj.text) > 50 else preview
        return "[미디어]"
    text_preview.short_description = "메시지 미리보기"

@admin.register(AutomationTrigger)
class AutomationTriggerAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'platform', 'action_type',
        'is_active', 'created_at'
    ]
    list_filter = ['platform', 'action_type', 'is_active']
    search_fields = ['name']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'platform', 'is_active')
        }),
        ('트리거 조건', {
            'fields': ('keyword_patterns',),
            'description': '정규식 패턴 목록 (JSON 배열)'
        }),
        ('액션 설정', {
            'fields': ('action_type', 'action_config'),
            'description': 'action_config는 action_type에 따라 다른 구조'
        }),
    )

@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'event_type', 'processed',
        'received_at', 'processing_time'
    ]
    list_filter = ['event_type', 'processed', 'received_at']
    search_fields = ['event_type']
    readonly_fields = ['received_at', 'processed_at', 'payload']
    
    def processing_time(self, obj):
        if obj.processed_at and obj.received_at:
            delta = obj.processed_at - obj.received_at
            return f"{delta.total_seconds():.2f}초"
        return "-"
    processing_time.short_description = "처리 시간"
    
    def has_add_permission(self, request):
        return False  # Webhook 로그는 자동으로만 생성
```

## 실전 활용 사례

### 1. 고객 지원 자동화

```python
# chatbot/services.py
def analyze_sentiment(text: str) -> str:
    """간단한 감정 분석 (실제로는 ML 모델 사용)"""
    negative_words = ['불만', '화나', '최악', '실망', '환불']
    positive_words = ['감사', '좋아', '만족', '훌륭', '최고']
    
    text_lower = text.lower()
    
    negative_count = sum(1 for word in negative_words if word in text_lower)
    positive_count = sum(1 for word in positive_words if word in text_lower)
    
    if negative_count > positive_count:
        return 'negative'
    elif positive_count > negative_count:
        return 'positive'
    return 'neutral'

def extract_intent(text: str) -> str:
    """의도 추출"""
    if any(word in text for word in ['?', '어떻게', '무엇', '언제']):
        return 'question'
    elif any(word in text for word in ['주문', '구매', '결제']):
        return 'order'
    elif any(word in text for word in ['환불', '취소', '반품']):
        return 'refund'
    elif any(word in text for word in ['도와', '문의', '문제']):
        return 'help'
    return 'unknown'

def fetch_faq_answer(question: str) -> Optional[str]:
    """FAQ에서 답변 검색"""
    # 실제로는 벡터 DB나 Elasticsearch 사용
    faqs = {
        '배송': '배송은 주문 후 2-3일 소요됩니다.',
        '환불': '구매일로부터 7일 이내 환불 가능합니다.',
        '결제': '신용카드, 체크카드, 계좌이체를 지원합니다.',
    }
    
    for keyword, answer in faqs.items():
        if keyword in question:
            return answer
    
    return None
```

### 2. 내부 운영 도구

```python
# chatbot/operations.py
from .openclaw_client import OpenClawClient
from django.core.management import call_command
import subprocess

def handle_ops_command(session_id: str, command: str, args: list):
    """운영 명령 처리"""
    client = OpenClawClient()
    
    if command == 'deploy':
        environment = args[0] if args else 'staging'
        
        if environment not in ['staging', 'production']:
            client.send_message(
                session_id,
                "❌ 잘못된 환경입니다. staging 또는 production을 선택하세요."
            )
            return
        
        # 배포 시작 알림
        client.send_message(
            session_id,
            f"🚀 {environment} 배포를 시작합니다..."
        )
        
        try:
            # Celery 작업으로 배포 실행
            from .tasks import deploy_application
            result = deploy_application.delay(environment)
            
            client.send_message(
                session_id,
                f"✅ 배포가 완료되었습니다. (작업 ID: {result.id})"
            )
        except Exception as e:
            client.send_message(
                session_id,
                f"❌ 배포 실패: {str(e)}"
            )
    
    elif command == 'status':
        # 시스템 상태 확인
        from django.db import connection
        from django.core.cache import cache
        
        db_status = "✅" if connection.ensure_connection() else "❌"
        cache_status = "✅" if cache.get('health_check') is not None else "❌"
        
        client.send_message(
            session_id,
            f"""📊 시스템 상태
            
데이터베이스: {db_status}
캐시: {cache_status}
OpenClaw Gateway: ✅
"""
        )
    
    elif command == 'logs':
        # 최근 로그 조회
        log_lines = args[0] if args else 50
        
        try:
            logs = subprocess.check_output(
                ['tail', '-n', str(log_lines), '/var/log/django/app.log'],
                text=True
            )
            
            # 로그가 너무 길면 파일로 전송
            if len(logs) > 2000:
                client.send_message(
                    session_id,
                    "로그가 너무 깁니다. 파일로 전송합니다.",
                    attachments=[{'type': 'file', 'content': logs}]
                )
            else:
                client.send_message(session_id, f"```\n{logs}\n```")
        
        except Exception as e:
            client.send_message(
                session_id,
                f"❌ 로그 조회 실패: {str(e)}"
            )
```

### 3. 웹 스크래핑 자동화

OpenClaw의 브라우저 도구를 활용한 웹 스크래핑:

```python
# chatbot/scraping.py
from .openclaw_client import OpenClawClient
import logging

logger = logging.getLogger(__name__)

def scrape_competitor_prices(session_id: str):
    """경쟁사 가격 모니터링"""
    client = OpenClawClient()
    
    competitors = [
        {'name': '경쟁사A', 'url': 'https://competitor-a.com/products'},
        {'name': '경쟁사B', 'url': 'https://competitor-b.com/items'},
    ]
    
    results = []
    
    for competitor in competitors:
        try:
            # 브라우저로 페이지 이동
            client.invoke_browser_tool('navigate', {
                'url': competitor['url']
            })
            
            # 페이지 스냅샷 (DOM 구조)
            snapshot = client.invoke_browser_tool('snapshot', {
                'format': 'aria',
                'selector': '.product-list'
            })
            
            # 가격 정보 추출 (실제로는 더 정교한 파싱 필요)
            # ... 파싱 로직 ...
            
            results.append({
                'competitor': competitor['name'],
                'prices': [/* 추출된 가격 */],
            })
        
        except Exception as e:
            logger.error(f"Failed to scrape {competitor['name']}: {e}")
    
    # 결과를 세션으로 전송
    summary = format_price_comparison(results)
    client.send_message(session_id, summary)

def monitor_website_changes(url: str, selector: str):
    """웹사이트 변경사항 모니터링"""
    client = OpenClawClient()
    
    try:
        # 현재 상태 캡처
        response = client.invoke_browser_tool('snapshot', {
            'url': url,
            'selector': selector,
        })
        
        current_content = response['data']['content']
        
        # 이전 상태와 비교
        from .models import WebsiteSnapshot
        previous = WebsiteSnapshot.objects.filter(
            url=url,
            selector=selector
        ).order_by('-created_at').first()
        
        if previous and previous.content != current_content:
            # 변경 감지
            logger.info(f"Website changed: {url}")
            
            # 알림 전송
            client.broadcast_message(
                platform='slack',
                user_ids=['admin-channel'],
                text=f"🔔 웹사이트 변경 감지: {url}\n\n"
                     f"셀렉터: {selector}"
            )
        
        # 현재 상태 저장
        WebsiteSnapshot.objects.create(
            url=url,
            selector=selector,
            content=current_content
        )
    
    except Exception as e:
        logger.exception(f"Failed to monitor {url}")
```

## 설정 및 배포

### Django settings.py

```python
# settings.py

# OpenClaw 설정
OPENCLAW_GATEWAY_URL = env('OPENCLAW_GATEWAY_URL', default='http://localhost:18789')
OPENCLAW_GATEWAY_TOKEN = env('OPENCLAW_GATEWAY_TOKEN')
OPENCLAW_WEBHOOK_SECRET = env('OPENCLAW_WEBHOOK_SECRET')

# Celery 설정
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_BEAT_SCHEDULE = {
    'send-daily-digest': {
        'task': 'chatbot.tasks.send_daily_digest',
        'schedule': crontab(hour=9, minute=0),  # 매일 오전 9시
    },
}

# 로깅
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/openclaw.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'chatbot': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### URLs 구성

```python
# urls.py
from django.urls import path
from chatbot import views

urlpatterns = [
    # OpenClaw Webhook
    path('api/openclaw/webhook/', views.openclaw_webhook, name='openclaw_webhook'),
    
    # Admin
    path('admin/', admin.site.urls),
]
```

### Docker Compose 예제

```yaml
# docker-compose.yml
version: '3.8'

services:
  django:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENCLAW_GATEWAY_URL=http://openclaw:18789
      - OPENCLAW_GATEWAY_TOKEN=${OPENCLAW_TOKEN}
      - OPENCLAW_WEBHOOK_SECRET=${WEBHOOK_SECRET}
    depends_on:
      - postgres
      - redis
      - openclaw

  openclaw:
    image: node:18
    working_dir: /app
    ports:
      - "18789:18789"
    volumes:
      - ~/.openclaw:/root/.openclaw
    command: >
      sh -c "npm install -g openclaw@latest &&
             openclaw gateway --port 18789 --bind 0.0.0.0"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

  celery:
    build: .
    command: celery -A config worker -l info
    depends_on:
      - redis
      - django

  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on:
      - redis
      - django

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=openclaw_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## 성능 최적화 팁

### 1. Webhook 처리 최적화

```python
# 대량 메시지 처리 시 bulk operation 활용
@transaction.atomic
def bulk_create_messages(messages_data):
    """여러 메시지 한 번에 저장"""
    messages = [
        ChatMessage(
            session_id=data['session_id'],
            message_id=data['message_id'],
            text=data['text'],
            # ...
        )
        for data in messages_data
    ]
    
    ChatMessage.objects.bulk_create(messages, batch_size=100)
```

### 2. 캐싱 전략

```python
from django.core.cache import cache

def get_session_cached(session_id: str):
    """세션 정보 캐싱"""
    cache_key = f"session:{session_id}"
    
    session = cache.get(cache_key)
    if session is None:
        session = ConversationSession.objects.get(session_id=session_id)
        cache.set(cache_key, session, timeout=300)  # 5분
    
    return session
```

### 3. 데이터베이스 인덱싱

```python
# 자주 조회하는 필드에 인덱스 추가
class ConversationSession(models.Model):
    # ...
    
    class Meta:
        indexes = [
            models.Index(fields=['platform', 'user_id']),
            models.Index(fields=['is_active', 'last_activity']),
            models.Index(fields=['-created_at']),  # 최신 세션 조회 최적화
        ]
```

## 보안 고려사항

### 1. Webhook 서명 검증

```python
def verify_webhook_signature(request):
    """HMAC 서명 검증"""
    signature = request.headers.get('X-OpenClaw-Signature')
    secret = settings.OPENCLAW_WEBHOOK_SECRET.encode('utf-8')
    
    expected = hmac.new(
        secret,
        request.body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
```

### 2. Rate Limiting

```python
from django.core.cache import cache
from django.http import HttpResponse

def rate_limit(request, key_prefix, max_requests=100, window=60):
    """간단한 rate limiting"""
    key = f"{key_prefix}:{request.META.get('REMOTE_ADDR')}"
    
    count = cache.get(key, 0)
    if count >= max_requests:
        return HttpResponse('Rate limit exceeded', status=429)
    
    cache.set(key, count + 1, window)
    return None
```

### 3. 민감 데이터 처리

```python
# 메시지에서 개인정보 마스킹
import re

def mask_sensitive_data(text: str) -> str:
    """개인정보 마스킹"""
    # 이메일
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        text
    )
    
    # 전화번호
    text = re.sub(
        r'\b\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b',
        '[PHONE]',
        text
    )
    
    # 신용카드 번호
    text = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        '[CARD]',
        text
    )
    
    return text
```

## 모니터링 및 디버깅

### 1. 프로메테우스 메트릭

```python
# chatbot/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
messages_received = Counter(
    'openclaw_messages_received_total',
    'Total messages received from OpenClaw',
    ['platform', 'direction']
)

message_processing_time = Histogram(
    'openclaw_message_processing_seconds',
    'Time spent processing messages',
    ['platform']
)

active_sessions = Gauge(
    'openclaw_active_sessions',
    'Number of active chat sessions',
    ['platform']
)

# 사용 예
def handle_message_event(payload, webhook_log):
    platform = payload.get('data', {}).get('channel', 'unknown')
    
    messages_received.labels(platform=platform, direction='inbound').inc()
    
    with message_processing_time.labels(platform=platform).time():
        # 메시지 처리 로직
        pass
```

### 2. 디버그 엔드포인트

```python
# chatbot/debug_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import ConversationSession, ChatMessage
from .openclaw_client import OpenClawClient

@require_http_methods(["GET"])
def debug_gateway_health(request):
    """OpenClaw Gateway 상태 확인"""
    client = OpenClawClient()
    health = client.get_health()
    
    return JsonResponse(health)

@require_http_methods(["GET"])
def debug_session_info(request, session_id):
    """세션 디버그 정보"""
    try:
        session = ConversationSession.objects.prefetch_related('messages').get(
            session_id=session_id
        )
        
        return JsonResponse({
            'session_id': session.session_id,
            'platform': session.platform,
            'message_count': session.message_count,
            'is_active': session.is_active,
            'recent_messages': [
                {
                    'text': msg.text,
                    'direction': msg.direction,
                    'created_at': msg.created_at.isoformat(),
                }
                for msg in session.messages.order_by('-created_at')[:10]
            ]
        })
    
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
```

## 결론

OpenClaw는 Django 프로젝트에 강력한 멀티채널 AI 비서 기능을 추가할 수 있는 훌륭한 도구입니다. 이 가이드에서 다룬 내용:

1. **통합 아키텍처**: Django와 OpenClaw Gateway 간의 Webhook 기반 통신
2. **데이터 모델**: 대화 세션, 메시지, 자동화 트리거 관리
3. **비동기 처리**: Celery를 활용한 성능 최적화
4. **실전 사례**: 고객 지원, 운영 자동화, 웹 스크래핑
5. **보안**: 서명 검증, Rate limiting, 민감 데이터 처리

### 다음 단계

- **AI 모델 파인튜닝**: 비즈니스 도메인에 특화된 응답 생성
- **다국어 지원**: 여러 언어로 고객과 소통
- **고급 분석**: 대화 데이터 분석 및 인사이트 추출
- **A/B 테스팅**: 다양한 응답 전략 실험

OpenClaw와 Django의 조합으로 차세대 대화형 애플리케이션을 구축해보세요!

## 참고 자료

- [OpenClaw 공식 문서](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Django Celery 문서](https://docs.celeryproject.org/en/stable/django/)
- [Webhook 보안 베스트 프랙티스](https://webhook.site/docs)
